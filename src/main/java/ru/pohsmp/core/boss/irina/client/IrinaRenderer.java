package ru.pohsmp.core.boss.irina.client;

import io.redspace.ironsspellbooks.entity.mobs.abstract_spell_casting_mob.AbstractSpellCastingMob;
import io.redspace.ironsspellbooks.entity.mobs.abstract_spell_casting_mob.AbstractSpellCastingMobRenderer;
import javax.annotation.Nullable;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.util.Mth;
import ru.pohsmp.core.boss.irina.IrinaMath;
import software.bernie.geckolib.core.object.Color;
import software.bernie.geckolib.renderer.layer.AutoGlowingGeoLayer;

/**
 * Irina's renderer: Iron's casting mob renderer (the staff in the right hand bone), her glow mask (threads, the cross on the hat),
 * no red hurt flash, no vanilla death tip-over (her own irina_death plays); she fades out with her threads at 4.2–5.0 s of the death.
 */
public class IrinaRenderer extends AbstractSpellCastingMobRenderer {
    public IrinaRenderer(EntityRendererProvider.Context ctx) {
        super(ctx, new IrinaModel());
        shadowRadius = 0.5f;
        addRenderLayer(new AutoGlowingGeoLayer<>(this));
    }

    private static float alpha(AbstractSpellCastingMob e, float pt) {
        if (!e.isDeadOrDying()) return 1;
        return Mth.clamp((IrinaMath.DEATH - (e.deathTime + pt)) / (IrinaMath.DEATH - IrinaMath.DEATH_UNRAVEL), 0, 1);
    }

    @Override
    public int getPackedOverlay(AbstractSpellCastingMob e, float u, float pt) {
        return OverlayTexture.NO_OVERLAY;
    }

    @Override
    public Color getRenderColor(AbstractSpellCastingMob e, float pt, int light) {
        Color c = super.getRenderColor(e, pt, light);
        float a = alpha(e, pt);
        return a < 1 && !e.isInvisible() ? Color.ofRGBA(1f, 1f, 1f, a) : c;
    }

    @Override
    public RenderType getRenderType(AbstractSpellCastingMob e, ResourceLocation tex, @Nullable MultiBufferSource buf, float pt) {
        if (e.isDeadOrDying()) return RenderType.entityTranslucent(tex);
        return super.getRenderType(e, tex, buf, pt);
    }

    @Override
    protected float getDeathMaxRotation(AbstractSpellCastingMob e) {
        return 0;
    }
}
