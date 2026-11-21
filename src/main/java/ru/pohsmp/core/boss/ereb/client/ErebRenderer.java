package ru.pohsmp.core.boss.ereb.client;

import com.mojang.blaze3d.vertex.PoseStack;
import io.redspace.ironsspellbooks.entity.mobs.abstract_spell_casting_mob.AbstractSpellCastingMob;
import io.redspace.ironsspellbooks.entity.mobs.abstract_spell_casting_mob.AbstractSpellCastingMobRenderer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.ItemStack;
import ru.pohsmp.core.boss.BossNet;
import ru.pohsmp.core.boss.client.BossClient;
import ru.pohsmp.core.boss.client.SheathPoses;
import ru.pohsmp.core.boss.ereb.ErebBody;
import ru.pohsmp.core.boss.ereb.ErebEntity;
import software.bernie.geckolib.renderer.layer.AutoGlowingGeoLayer;

/**
 * Ereb and his reflections (they must not be told apart): our model, the glow mask (ereb_glowmask.png for both faces), the rapier
 * Iron's draws in the right hand. Not drawn while hidden (LOOK_HIDDEN of the boss: the intro swarm, vanishing in a ripple, «Ложный
 * шаг», the veil's flicker, after the finale's dissolve); drawn as a participant while he wears its face («Чужое лицо», «Ложный
 * союзник»: {@link ErebDisguise}).
 */
public class ErebRenderer extends AbstractSpellCastingMobRenderer {
    public ErebRenderer(EntityRendererProvider.Context ctx) {
        super(ctx, new ErebModel());
        shadowRadius = 0.5f;
        addRenderLayer(new AutoGlowingGeoLayer<>(this) {
            @Override
            protected ResourceLocation getTextureResource(AbstractSpellCastingMob e) {
                return ErebModel.TEXTURE;   // one mask for both faces: ereb_glowmask.png
            }
        });
    }

    @Override
    public void render(AbstractSpellCastingMob e, float yaw, float pt, PoseStack ps, MultiBufferSource buf, int light) {
        if (e instanceof ErebEntity && BossClient.look(e.getId(), BossNet.LOOK_HIDDEN)) return;
        if (e instanceof ErebBody b && b.face() != null && ErebDisguise.render(b, yaw, pt, ps, buf, light)) return;
        super.render(e, yaw, pt, ps, buf, light);
    }

    /** In Iron's poses with folded / both hands the rapier shrinks into the fist and grows back after ({@link SheathPoses}). */
    @Override
    protected void adjustHandItemRendering(PoseStack ps, ItemStack stack, AbstractSpellCastingMob e, float pt, boolean offhand) {
        super.adjustHandItemRendering(ps, stack, e, pt, offhand);
        if (!offhand) SheathPoses.apply(ps, e, pt);
    }

    @Override
    public boolean shouldShowName(AbstractSpellCastingMob e) {
        return false;
    }
}
