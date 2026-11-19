package ru.pohsmp.core.client.fx;

import com.mojang.blaze3d.platform.GlStateManager;
import com.mojang.blaze3d.systems.RenderSystem;
import com.mojang.blaze3d.vertex.DefaultVertexFormat;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.mojang.blaze3d.vertex.VertexFormat;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import net.minecraft.client.Camera;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.phys.Vec3;
import org.joml.Matrix3f;
import org.joml.Matrix4f;
import org.joml.Vector3f;
import ru.pohsmp.core.PohCore;

/**
 * Drawing helpers of the data-driven effects: render types (full-bright, no depth write, both sides; additive light that
 * respects texture alpha, or plain translucent for dark parts), texture lookup and camera-facing primitives.
 * Colours are 0xRRGGBB; alpha above 1 brightens (additive only).
 */
public final class FxDraw extends RenderType {
    private FxDraw() {
        super("pohsmp_fx_dummy", DefaultVertexFormat.NEW_ENTITY, VertexFormat.Mode.QUADS, 256, false, true, () -> {}, () -> {});
    }

    private static final TransparencyStateShard ADD_ALPHA = new TransparencyStateShard("pohsmp_fx_additive", () -> {
        RenderSystem.enableBlend();
        RenderSystem.blendFunc(GlStateManager.SourceFactor.SRC_ALPHA, GlStateManager.DestFactor.ONE);
    }, () -> {
        RenderSystem.disableBlend();
        RenderSystem.defaultBlendFunc();
    });

    private static final Map<ResourceLocation, RenderType> ADD = new HashMap<>(), TRANS = new HashMap<>();

    private static RenderType make(String name, ResourceLocation tex, TransparencyStateShard tr) {
        return create(name, DefaultVertexFormat.NEW_ENTITY, VertexFormat.Mode.QUADS, 1 << 16, false, true,
                CompositeState.builder()
                        .setShaderState(RENDERTYPE_ENTITY_TRANSLUCENT_EMISSIVE_SHADER)
                        .setTextureState(new TextureStateShard(tex, false, false))
                        .setTransparencyState(tr)
                        .setCullState(NO_CULL)
                        .setWriteMaskState(COLOR_WRITE)
                        .setOverlayState(OVERLAY)
                        .createCompositeState(false));
    }

    public static RenderType additive(ResourceLocation tex) {
        return ADD.computeIfAbsent(tex, t -> make("pohsmp_fx_add", t, ADD_ALPHA));
    }

    public static RenderType translucent(ResourceLocation tex) {
        return TRANS.computeIfAbsent(tex, t -> make("pohsmp_fx_trans", t, TRANSLUCENT_TRANSPARENCY));
    }

    // ---------------------------------------------------------------- textures

    private static final Map<String, ResourceLocation> TEX = new HashMap<>();
    public static final ResourceLocation WHITE = new ResourceLocation(PohCore.MODID, "textures/fx/white.png");

    /** Texture by bare name: textures/sigil/&lt;name&gt;.png first, then textures/fx/&lt;name&gt;.png; unknown -> white. */
    public static ResourceLocation tex(String name) {
        if (name == null || name.isEmpty()) return WHITE;
        return TEX.computeIfAbsent(name, n -> {
            var rm = Minecraft.getInstance().getResourceManager();
            for (String folder : new String[] {"sigil", "fx"}) {
                ResourceLocation rl = new ResourceLocation(PohCore.MODID, "textures/" + folder + "/" + n + ".png");
                if (rm.getResource(rl).isPresent()) return rl;
            }
            return WHITE;
        });
    }

    public static void clearTextures() {
        TEX.clear();
    }

    // ---------------------------------------------------------------- frame

    /** One render pass: pose (already moved by -camera), buffers, camera, absolute time in ticks with partial tick. */
    public record Frame(PoseStack.Pose pose, MultiBufferSource buf, Camera cam, Vec3 camPos, double time, float pt, boolean low) {
        public VertexConsumer add(ResourceLocation t) {
            return buf.getBuffer(additive(t));
        }

        public VertexConsumer trans(ResourceLocation t) {
            return buf.getBuffer(translucent(t));
        }

        public Vec3 left() {
            Vector3f l = cam.getLeftVector();
            return new Vec3(l.x(), l.y(), l.z());
        }

        public Vec3 up() {
            Vector3f u = cam.getUpVector();
            return new Vec3(u.x(), u.y(), u.z());
        }
    }

    // ---------------------------------------------------------------- vertices

    public static float r(int rgb) {
        return ((rgb >> 16) & 255) / 255f;
    }

    public static float g(int rgb) {
        return ((rgb >> 8) & 255) / 255f;
    }

    public static float b(int rgb) {
        return (rgb & 255) / 255f;
    }

    /** One vertex; brightness above 1 lifts the colour (clamped), alpha is clamped to 0..1. */
    public static void vert(VertexConsumer vc, Frame f, double x, double y, double z, float u, float v, int rgb, double a) {
        Matrix4f m = f.pose().pose();
        Matrix3f n = f.pose().normal();
        float k = (float) Math.max(1, a), al = (float) Math.max(0, Math.min(1, a));
        vc.vertex(m, (float) x, (float) y, (float) z).color(Math.min(1, r(rgb) * k), Math.min(1, g(rgb) * k), Math.min(1, b(rgb) * k), al)
                .uv(u, v).overlayCoords(OverlayTexture.NO_OVERLAY).uv2(LightTexture.FULL_BRIGHT).normal(n, 0, 1, 0).endVertex();
    }

    public static void vert(VertexConsumer vc, Frame f, Vec3 p, float u, float v, int rgb, double a) {
        vert(vc, f, p.x, p.y, p.z, u, v, rgb, a);
    }

    /** Quad p0..p3 with uv (0,0) (0,1) (1,1) (1,0). */
    public static void quad(VertexConsumer vc, Frame f, Vec3 p0, Vec3 p1, Vec3 p2, Vec3 p3, int rgb, double a) {
        vert(vc, f, p0, 0, 0, rgb, a);
        vert(vc, f, p1, 0, 1, rgb, a);
        vert(vc, f, p2, 1, 1, rgb, a);
        vert(vc, f, p3, 1, 0, rgb, a);
    }

    public static void tri(VertexConsumer vc, Frame f, Vec3 p0, Vec3 p1, Vec3 p2, int rgb, double a) {
        vert(vc, f, p0, 0.5f, 0.5f, rgb, a);
        vert(vc, f, p0, 0.5f, 0.5f, rgb, a);
        vert(vc, f, p1, 0.5f, 0.5f, rgb, a);
        vert(vc, f, p2, 0.5f, 0.5f, rgb, a);
    }

    /** Camera-facing square of half-size s, rotated by rot degrees in the screen plane. */
    public static void billboard(VertexConsumer vc, Frame f, Vec3 c, double s, double rot, int rgb, double a) {
        billboard(vc, f, c, s, s, rot, rgb, a);
    }

    public static void billboard(VertexConsumer vc, Frame f, Vec3 c, double sx, double sy, double rot, int rgb, double a) {
        Vec3 l = f.left(), u = f.up();
        double cr = Math.cos(Math.toRadians(rot)), sr = Math.sin(Math.toRadians(rot));
        Vec3 ax = l.scale(cr).add(u.scale(sr)).scale(sx), ay = u.scale(cr).subtract(l.scale(sr)).scale(sy);
        quad(vc, f, c.add(ax).add(ay), c.add(ax).subtract(ay), c.subtract(ax).subtract(ay), c.subtract(ax).add(ay), rgb, a);
    }

    /** Camera-facing strip from a to b, width w; texture u across, v along (0 at a). */
    public static void line(VertexConsumer vc, Frame f, Vec3 a, Vec3 b, double w, int rgb, double al) {
        line(vc, f, a, b, w, w, rgb, al, al, 0, 1);
    }

    public static void line(VertexConsumer vc, Frame f, Vec3 a, Vec3 b, double wa, double wb, int rgb, double aa, double ab, float va, float vb) {
        Vec3 d = b.subtract(a);
        Vec3 mid = a.add(b).scale(0.5);
        Vec3 side = d.cross(mid.subtract(f.camPos()));
        if (side.lengthSqr() < 1e-9) side = f.left();
        side = side.normalize();
        Vec3 sa = side.scale(wa / 2), sb = side.scale(wb / 2);
        vert(vc, f, a.subtract(sa), 0, va, rgb, aa);
        vert(vc, f, a.add(sa), 1, va, rgb, aa);
        vert(vc, f, b.add(sb), 1, vb, rgb, ab);
        vert(vc, f, b.subtract(sb), 0, vb, rgb, ab);
    }

    /** Vertical strip from base up by h that turns around Y to face the camera. */
    public static void pillar(VertexConsumer vc, Frame f, Vec3 base, double h, double w, int rgb, double aBottom, double aTop, float vBottom, float vTop) {
        Vec3 to = f.camPos().subtract(base);
        Vec3 side = new Vec3(to.z, 0, -to.x);
        side = side.lengthSqr() < 1e-6 ? new Vec3(1, 0, 0) : side.normalize();
        side = side.scale(w / 2);
        Vec3 top = base.add(0, h, 0);
        vert(vc, f, base.subtract(side), 0, vBottom, rgb, aBottom);
        vert(vc, f, base.add(side), 1, vBottom, rgb, aBottom);
        vert(vc, f, top.add(side), 1, vTop, rgb, aTop);
        vert(vc, f, top.subtract(side), 0, vTop, rgb, aTop);
    }

    /** Flat textured disc in the plane (u, v) around c, radius r, texture turned by rot degrees. */
    public static void disc(VertexConsumer vc, Frame f, Vec3 c, Vec3 u, Vec3 v, double r, double rot, int rgb, double a) {
        double k = Math.toRadians(rot + 45);
        Vec3 p[] = new Vec3[4];
        for (int i = 0; i < 4; i++) {
            double ang = k + i * Math.PI / 2, rr = r * Math.sqrt(2);
            p[i] = c.add(u.scale(Math.cos(ang) * rr)).add(v.scale(Math.sin(ang) * rr));
        }
        // corners at +45,+135,+225,+315 of the texture: uv (1,0) (0,0) (0,1) (1,1)
        vert(vc, f, p[0], 1, 0, rgb, a);
        vert(vc, f, p[1], 0, 0, rgb, a);
        vert(vc, f, p[2], 0, 1, rgb, a);
        vert(vc, f, p[3], 1, 1, rgb, a);
    }

    /**
     * Ribbon through pts (at least 2): per-point width w and alpha a, v runs 0 at pts[0] to 1 at the end, u across.
     * sides == null: each point turns to face the camera (a glowing line); else sides[i] is the unit direction across.
     */
    public static void strip(VertexConsumer vc, Frame f, List<Vec3> pts, double[] w, double[] a, int rgb, Vec3[] sides) {
        int n = pts.size();
        if (n < 2) return;
        Vec3[] l = new Vec3[n], r = new Vec3[n];
        for (int i = 0; i < n; i++) {
            Vec3 p = pts.get(i);
            Vec3 side;
            if (sides != null) side = sides[i];
            else {
                Vec3 tan = pts.get(Math.min(n - 1, i + 1)).subtract(pts.get(Math.max(0, i - 1)));
                side = tan.cross(p.subtract(f.camPos()));
                side = side.lengthSqr() < 1e-12 ? f.left() : side.normalize();
            }
            Vec3 h = side.scale(w[i] / 2);
            l[i] = p.subtract(h);
            r[i] = p.add(h);
        }
        for (int i = 0; i + 1 < n; i++) {
            if (a[i] <= 0.002 && a[i + 1] <= 0.002) continue;
            float v0 = (float) i / (n - 1), v1 = (float) (i + 1) / (n - 1);
            vert(vc, f, l[i], 0, v0, rgb, a[i]);
            vert(vc, f, r[i], 1, v0, rgb, a[i]);
            vert(vc, f, r[i + 1], 1, v1, rgb, a[i + 1]);
            vert(vc, f, l[i + 1], 0, v1, rgb, a[i + 1]);
        }
    }

    /** Two-layer glowing line: a wide soft halo in the colour and a narrow hot core whitened toward `core` share. */
    public static void glowStrip(Frame f, List<Vec3> pts, double[] w, double[] a, int rgb, Vec3[] sides, double halo) {
        VertexConsumer vc = f.add(tex("strip_soft"));
        int n = pts.size();
        double[] wh = new double[n], ah = new double[n], wc = new double[n];
        for (int i = 0; i < n; i++) {
            wh[i] = w[i] * halo;
            ah[i] = a[i] * 0.45;
            wc[i] = w[i];
        }
        strip(vc, f, pts, wh, ah, rgb, null);
        strip(vc, f, pts, wc, a, mix(rgb, 0xFFFFFF, 0.55), sides);
    }

    /** Colour between a and b (t = 0 -> a). */
    public static int mix(int a, int b, double t) {
        int r = (int) Math.round(((a >> 16) & 255) + ((((b >> 16) & 255) - ((a >> 16) & 255)) * t));
        int g = (int) Math.round(((a >> 8) & 255) + ((((b >> 8) & 255) - ((a >> 8) & 255)) * t));
        int bl = (int) Math.round((a & 255) + (((b & 255) - (a & 255)) * t));
        return (r & 255) << 16 | (g & 255) << 8 | (bl & 255);
    }

    public static Vec3 lerp(Vec3 a, Vec3 b, double t) {
        return a.add(b.subtract(a).scale(t));
    }

    public static double clamp01(double x) {
        return Math.max(0, Math.min(1, x));
    }
}
