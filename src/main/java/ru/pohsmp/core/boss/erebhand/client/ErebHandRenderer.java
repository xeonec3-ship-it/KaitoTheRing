package ru.pohsmp.core.boss.erebhand.client;

import com.mojang.blaze3d.vertex.PoseStack;
import io.redspace.ironsspellbooks.entity.mobs.abstract_spell_casting_mob.AbstractSpellCastingMob;
import io.redspace.ironsspellbooks.entity.mobs.abstract_spell_casting_mob.AbstractSpellCastingMobRenderer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.ItemStack;
import ru.pohsmp.core.boss.BossNet;
import ru.pohsmp.core.boss.client.BossClient;
import ru.pohsmp.core.boss.client.SheathPoses;
import ru.pohsmp.core.boss.erebhand.ErebHandBody;
import ru.pohsmp.core.boss.erebhand.ErebHandEntity;
import software.bernie.geckolib.core.object.Color;
import software.bernie.geckolib.renderer.layer.AutoGlowingGeoLayer;

/**
 * Ereb, the Hand of Lies and his reflections: our model, RenderType.entityTranslucent (else the glass of the ghost hand turns opaque —
 * the visual letter), the glow mask that goes with the current texture (ereb_hand / _mended / _cracked + _glowmask), the glass rapier
 * Iron's draws in the right hand. Not drawn while hidden (LOOK_HIDDEN: the intro, the end of the false death); a «ghost» reflection
 * («Тысяча отражений») is see-through.
 */
public class ErebHandRenderer extends AbstractSpellCastingMobRenderer {
    public ErebHandRenderer(EntityRendererProvider.Context ctx) {
        super(ctx, new ErebHandModel());
        shadowRadius = 0.55f;
        addRenderLayer(new AutoGlowingGeoLayer<>(this) {
            @Override
            protected ResourceLocation getTextureResource(AbstractSpellCastingMob e) {
                return ErebHandModel.texture(e);
            }
        });
    }

    @Override
    public void render(AbstractSpellCastingMob e, float yaw, float pt, PoseStack ps, MultiBufferSource buf, int light) {
        boolean hidden = e instanceof ErebHandEntity && BossClient.look(e.getId(), BossNet.LOOK_HIDDEN);
        // the dispatcher draws the shadow after render(): none while he is unseen, none under the double of «Ложное отступление»
        shadowRadius = hidden || e instanceof ErebHandBody b && b.noShadow() ? 0 : 0.55f;
        if (hidden) return;
        super.render(e, yaw, pt, ps, buf, light);
    }

    @Override
    public RenderType getRenderType(AbstractSpellCastingMob e, ResourceLocation texture, MultiBufferSource buf, float pt) {
        return RenderType.entityTranslucent(texture);
    }

    @Override
    public Color getRenderColor(AbstractSpellCastingMob e, float pt, int light) {
        if (e instanceof ErebHandBody b && b.ghost()) return Color.ofRGBA(1f, 1f, 1f, 0.55f);
        return super.getRenderColor(e, pt, light);
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
