package ru.pohsmp.core.boss.ereb.client;

import io.redspace.ironsspellbooks.entity.mobs.abstract_spell_casting_mob.AbstractSpellCastingMob;
import io.redspace.ironsspellbooks.entity.mobs.abstract_spell_casting_mob.AbstractSpellCastingMobModel;
import net.minecraft.client.Minecraft;
import net.minecraft.resources.ResourceLocation;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.boss.ereb.ErebBody;
import software.bernie.geckolib.core.animatable.model.CoreGeoBone;
import software.bernie.geckolib.core.animation.AnimationState;

/**
 * Ereb (and his reflections): geo/entity/ereb.geo.json (Iron's casting-mob bones + the four coat tails), textures/entity/ereb/ereb.png
 * (ereb_smile.png while he smiles in the finale), animations/entity/ereb.animation.json (Iron's casting animations + ereb_*). The coat
 * tails follow the legs of Iron's procedural walk (the visual assistant's formula; our ereb_* animations do not touch them).
 */
public class ErebModel extends AbstractSpellCastingMobModel {
    public static final ResourceLocation MODEL = new ResourceLocation(PohCore.MODID, "geo/entity/ereb.geo.json");
    public static final ResourceLocation TEXTURE = new ResourceLocation(PohCore.MODID, "textures/entity/ereb/ereb.png");
    public static final ResourceLocation TEXTURE_SMILE = new ResourceLocation(PohCore.MODID, "textures/entity/ereb/ereb_smile.png");
    public static final ResourceLocation ANIMATIONS = new ResourceLocation(PohCore.MODID, "animations/entity/ereb.animation.json");

    @Override
    public ResourceLocation getModelResource(AbstractSpellCastingMob e) {
        return MODEL;
    }

    @Override
    public ResourceLocation getTextureResource(AbstractSpellCastingMob e) {
        return e instanceof ErebBody b && b.smiling() ? TEXTURE_SMILE : TEXTURE;
    }

    @Override
    public ResourceLocation getAnimationResource(AbstractSpellCastingMob e) {
        return ANIMATIONS;
    }

    @Override
    public void setCustomAnimations(AbstractSpellCastingMob entity, long instanceId, AnimationState<AbstractSpellCastingMob> state) {
        super.setCustomAnimations(entity, instanceId, state);
        if (Minecraft.getInstance().isPaused() || !(entity instanceof ErebBody b) || b.playingAction()) return;
        // GeckoLib axes (mgr_anim_check_T26_T30, 4.2): the back tails follow a leg going back (rotX < 0), the front ones only a leg
        // going forward (rotX > 0) — never through it; their rest angles are in the model
        float right = rot("right_leg"), left = rot("left_leg");
        coat("coat_back_r", Math.min(0, right) * 0.4f);
        coat("coat_back_l", Math.min(0, left) * 0.4f);
        coat("coat_front_r", Math.max(0, right) * 0.55f);
        coat("coat_front_l", Math.max(0, left) * 0.55f);
    }

    private float rot(String bone) {
        CoreGeoBone b = getAnimationProcessor().getBone(bone);
        return b == null ? 0 : b.getRotX();
    }

    private void coat(String bone, float rotX) {
        CoreGeoBone b = getAnimationProcessor().getBone(bone);
        if (b != null) b.setRotX(b.getRotX() + rotX);
    }
}
