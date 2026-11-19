package ru.pohsmp.core.client.nightmare;

import com.mojang.blaze3d.platform.NativeImage;
import com.mojang.blaze3d.systems.RenderSystem;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import java.io.InputStream;
import java.util.EnumMap;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.PlayerInfo;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.client.renderer.texture.AbstractTexture;
import net.minecraft.client.renderer.texture.DynamicTexture;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.client.resources.DefaultPlayerSkin;
import net.minecraft.resources.ResourceLocation;
import net.minecraftforge.client.event.EntityRenderersEvent;
import org.lwjgl.opengl.GL11;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.nightmare.Bestiary;
import ru.pohsmp.core.nightmare.NightmareMob;
import software.bernie.geckolib.cache.object.BakedGeoModel;
import software.bernie.geckolib.model.GeoModel;
import software.bernie.geckolib.renderer.GeoEntityRenderer;
import software.bernie.geckolib.renderer.GeoRenderer;
import software.bernie.geckolib.renderer.layer.GeoRenderLayer;

/**
 * T25: the nightmares on the clients that get them at all (only the immersed) - the helper's GeckoLib models (visual letter 19.11):
 * geo/entity/nm_<id>.geo.json, textures/entity/nightmare/nm_<id>.png (cutout), the glowing parts from nm_<id>_glowmask.png,
 * animations/entity/nm_<id>.animation.json. The ink pool under the feet only while it comes or goes. The Mimic wears a player's skin:
 * the skin (64x64) is copied x4 into the empty left half of its 512x256 template.
 */
public final class NightmareRender {
    private NightmareRender() {}

    public static void register(EntityRenderersEvent.RegisterRenderers e) {
        for (var t : Bestiary.TYPES.values()) e.registerEntityRenderer(t.get(), Renderer::new);
    }

    private static ResourceLocation rl(String path) {
        return new ResourceLocation(PohCore.MODID, path);
    }

    private static boolean exists(ResourceLocation r) {
        return Minecraft.getInstance().getResourceManager().getResource(r).isPresent();
    }

    // ---------------------------------------------------------------- model

    static final class Model extends GeoModel<NightmareMob> {
        @Override
        public ResourceLocation getModelResource(NightmareMob m) {
            if (m.kind == NightmareMob.Kind.MIMIC && Mimic.slim(m)) return rl("geo/entity/nm_mimic_slim.geo.json");
            return rl("geo/entity/" + m.kind.id + ".geo.json");
        }

        @Override
        public ResourceLocation getTextureResource(NightmareMob m) {
            if (m.kind == NightmareMob.Kind.MIMIC) return Mimic.texture(m);
            return rl("textures/entity/nightmare/" + m.kind.id + ".png");
        }

        @Override
        public ResourceLocation getAnimationResource(NightmareMob m) {
            return rl("animations/entity/" + m.kind.id + ".animation.json");
        }

        @Override
        public boolean crashIfBoneMissing() {
            return false;
        }
    }

    // ---------------------------------------------------------------- renderer

    static final class Renderer extends GeoEntityRenderer<NightmareMob> {
        Renderer(EntityRendererProvider.Context ctx) {
            super(ctx, new Model());
            shadowRadius = 0;
            addRenderLayer(new Glow(this));
        }

        @Override
        public void preRender(PoseStack ps, NightmareMob m, BakedGeoModel model, MultiBufferSource buf, VertexConsumer vc, boolean reRender,
                              float pt, int light, int overlay, float r, float g, float b, float a) {
            boolean pool = m.going() || m.appearing();
            model.getBone("pool").ifPresent(bone -> bone.setHidden(!pool));
            super.preRender(ps, m, model, buf, vc, reRender, pt, light, overlay, r, g, b, a);
        }

        @Override
        protected void applyRotations(NightmareMob m, PoseStack ps, float age, float yaw, float pt) {
            super.applyRotations(m, ps, age, yaw, pt);
            if (m.onCeiling()) {   // the Crawler upside down, its feet on the ceiling
                ps.translate(0, m.getBbHeight(), 0);
                ps.mulPose(com.mojang.math.Axis.ZP.rotationDegrees(180));
            }
        }

        @Override
        public RenderType getRenderType(NightmareMob m, ResourceLocation tex, MultiBufferSource buf, float pt) {
            return RenderType.entityCutoutNoCull(tex);
        }
    }

    /** The eyes, throats and tears that glow in the dark: the glowmask drawn again at full light. */
    static final class Glow extends GeoRenderLayer<NightmareMob> {
        private static final Map<NightmareMob.Kind, ResourceLocation> MASK = new EnumMap<>(NightmareMob.Kind.class);
        private static final ResourceLocation NONE = rl("none");

        Glow(GeoRenderer<NightmareMob> r) {
            super(r);
        }

        @Override
        public void render(PoseStack ps, NightmareMob m, BakedGeoModel model, RenderType type, MultiBufferSource buf, VertexConsumer vc,
                           float pt, int light, int overlay) {
            ResourceLocation mask = MASK.computeIfAbsent(m.kind, k -> {
                String id = k == NightmareMob.Kind.MIMIC ? "nm_mimic_template" : k.id;
                ResourceLocation r = rl("textures/entity/nightmare/" + id + "_glowmask.png");
                return exists(r) ? r : NONE;
            });
            if (mask == NONE) return;
            RenderType eyes = RenderType.eyes(mask);
            getRenderer().reRender(model, ps, buf, m, eyes, buf.getBuffer(eyes), pt, 0xF000F0, OverlayTexture.NO_OVERLAY, 1, 1, 1, 1);
        }
    }

    // ---------------------------------------------------------------- the Mimic's borrowed skin

    static final class Mimic {
        private static final ResourceLocation TEMPLATE = rl("textures/entity/nightmare/nm_mimic_template.png");
        /** per worn player: the skin it was made from and the texture made */
        private static final Map<UUID, ResourceLocation[]> MADE = new HashMap<>();

        static boolean slim(NightmareMob m) {
            UUID u = m.face().orElse(null);
            if (u == null) return false;
            PlayerInfo pi = info(u);
            return "slim".equals(pi != null ? pi.getModelName() : DefaultPlayerSkin.getSkinModelName(u));
        }

        private static PlayerInfo info(UUID u) {
            var c = Minecraft.getInstance().getConnection();
            return c == null ? null : c.getPlayerInfo(u);
        }

        static ResourceLocation texture(NightmareMob m) {
            UUID u = m.face().orElse(null);
            if (u == null) return TEMPLATE;
            PlayerInfo pi = info(u);
            ResourceLocation skin = pi != null ? pi.getSkinLocation() : DefaultPlayerSkin.getDefaultSkin(u);
            ResourceLocation[] had = MADE.get(u);
            if (had != null && had[0].equals(skin)) return had[1];
            ResourceLocation made = make(u, skin);
            if (made == null) return TEMPLATE;
            if (had != null) Minecraft.getInstance().getTextureManager().release(had[1]);
            MADE.put(u, new ResourceLocation[] {skin, made});
            return made;
        }

        /** Reads the skin back from its GL texture (it may be a downloaded one with no file) and pastes it x4 into the template. */
        private static ResourceLocation make(UUID u, ResourceLocation skinLoc) {
            Minecraft mc = Minecraft.getInstance();
            AbstractTexture skinTex = mc.getTextureManager().getTexture(skinLoc);
            NativeImage tpl;
            try (InputStream in = mc.getResourceManager().open(TEMPLATE)) {
                tpl = NativeImage.read(in);
            } catch (Exception ex) {
                return null;
            }
            RenderSystem.bindTexture(skinTex.getId());
            int w = GL11.glGetTexLevelParameteri(GL11.GL_TEXTURE_2D, 0, GL11.GL_TEXTURE_WIDTH);
            int h = GL11.glGetTexLevelParameteri(GL11.GL_TEXTURE_2D, 0, GL11.GL_TEXTURE_HEIGHT);
            if (w < 64 || h < 32) {
                tpl.close();
                return null;
            }
            try (NativeImage skin = new NativeImage(w, h, false)) {
                skin.downloadTexture(0, false);
                int k = w / 64, sh = Math.min(64, h / k);
                for (int y = 0; y < sh; y++)
                    for (int x = 0; x < 64; x++) {
                        int c = skin.getPixelRGBA(x * k, y * k);
                        for (int dy = 0; dy < 4; dy++)
                            for (int dx = 0; dx < 4; dx++)
                                if (y * 4 + dy < tpl.getHeight() && x * 4 + dx < tpl.getWidth()) tpl.setPixelRGBA(x * 4 + dx, y * 4 + dy, c);
                    }
            }
            return mc.getTextureManager().register("pohsmp_mimic_" + u.toString().substring(0, 8), new DynamicTexture(tpl));
        }

        static void clear() {
            for (ResourceLocation[] r : MADE.values()) Minecraft.getInstance().getTextureManager().release(r[1]);
            MADE.clear();
        }
    }
}
