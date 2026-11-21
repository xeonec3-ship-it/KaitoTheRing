package ru.pohsmp.core.boss.cult.client;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import io.redspace.ironsspellbooks.entity.mobs.abstract_spell_casting_mob.AbstractSpellCastingMob;
import io.redspace.ironsspellbooks.entity.mobs.abstract_spell_casting_mob.AbstractSpellCastingMobRenderer;
import io.redspace.ironsspellbooks.entity.mobs.wizards.fire_boss.FireBossFireballChargeLayer;
import io.redspace.ironsspellbooks.entity.mobs.wizards.fire_boss.FireBossSoulLayer;
import javax.annotation.Nullable;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.util.Mth;
import ru.pohsmp.core.boss.BossNet;
import ru.pohsmp.core.boss.client.BossClient;
import ru.pohsmp.core.boss.cult.CultLeaderEntity;
import ru.pohsmp.core.boss.cult.CultMath;
import software.bernie.geckolib.cache.object.BakedGeoModel;
import software.bernie.geckolib.core.object.Color;
import software.bernie.geckolib.renderer.layer.AutoGlowingGeoLayer;

/**
 * FireBossRenderer's behaviour for the Head of the Cult (size as the original Tyros: ×1.75, soul form ×2.0125, shadow 0.65) with our
 * model, the glow masks (scaled once: see preRender), our head flame in both forms (goes out at 2.6 s of the death scene), not drawn while it is ash (LOOK_HIDDEN) and for the
 * first 30 ticks of the intro (it is still inside the fire).
 */
public class CultLeaderRenderer extends AbstractSpellCastingMobRenderer {
    public CultLeaderRenderer(EntityRendererProvider.Context ctx) {
        super(ctx, new CultLeaderModel());
        shadowRadius = 0.65f;
        addRenderLayer(new FireBossSoulLayer(this));
        addRenderLayer(new CultFlameLayer(this));
        addRenderLayer(new FireBossFireballChargeLayer(this, ctx));
        addRenderLayer(new AutoGlowingGeoLayer<>(this));
    }

    private static boolean hidden(AbstractSpellCastingMob e, float pt) {
        if (!(e instanceof CultLeaderEntity c)) return false;
        return BossClient.look(c.getId(), BossNet.LOOK_HIDDEN) || c.isSpawning() && c.introAge(pt) < CultMath.INTRO_HIDE;
    }

    @Override
    public void preRender(PoseStack ps, AbstractSpellCastingMob e, BakedGeoModel model, MultiBufferSource buf, VertexConsumer vc, boolean reRender,
                          float pt, int light, int overlay, float r, float g, float b, float a) {
        super.preRender(ps, e, model, buf, vc, reRender, pt, light, overlay, r, g, b, a);
        // Only on the main pass: AutoGlowingGeoLayer draws the glow mask with GeoRenderer.reRender, which calls preRender again on
        // the already scaled pose stack - scaled here a second time the glowing parts (eyes, crown tips, medallion; in the soul form
        // the whole golden armour) were drawn x3.06 / x4.05 from the feet, 2-3 heights over his head (owner's screenshots 21.11).
        if (reRender) return;
        float s = e instanceof CultLeaderEntity c && c.isSoulMode() ? 2.0125f : 1.75f;
        ps.scale(s, s, s);
    }

    @Override
    public void render(AbstractSpellCastingMob e, float yaw, float pt, PoseStack ps, MultiBufferSource buf, int light) {
        if (hidden(e, pt)) return;
        if (e instanceof CultLeaderEntity c && c.isSpawning()) {
            float f = c.introAge(pt) / CultMath.INTRO;
            shadowRadius = Mth.lerp(f, 2.0f, 0.65f);
            shadowStrength = f;
        } else {
            shadowStrength = 1;
            shadowRadius = 0.65f;
        }
        super.render(e, yaw, pt, ps, buf, Mth.clamp(light + 100, 0, 240));
    }

    @Override
    public int getPackedOverlay(AbstractSpellCastingMob e, float u, float pt) {
        return OverlayTexture.NO_OVERLAY;
    }

    @Override
    public Color getRenderColor(AbstractSpellCastingMob e, float pt, int light) {
        Color c = super.getRenderColor(e, pt, light);
        float f = 1;
        if (e.deathTime > 40) f = Mth.clamp((160 - e.deathTime) / 120f, 0, 1);
        else if (e instanceof CultLeaderEntity b && b.isSpawning()) f = Mth.clamp((b.introAge(pt) - CultMath.INTRO_HIDE) / 30f, 0, 1);
        if (!e.isInvisible() && f != 1) c = Color.ofRGBA(1f, 1f, 1f, f);
        return c;
    }

    @Override
    public RenderType getRenderType(AbstractSpellCastingMob e, ResourceLocation tex, @Nullable MultiBufferSource buf, float pt) {
        if (e.isDeadOrDying() || e instanceof CultLeaderEntity b && (b.isSpawning() || b.isDespawning())) return RenderType.entityTranslucent(tex);
        return super.getRenderType(e, tex, buf, pt);
    }

    @Override
    protected float getDeathMaxRotation(AbstractSpellCastingMob e) {
        return 0;
    }
}
