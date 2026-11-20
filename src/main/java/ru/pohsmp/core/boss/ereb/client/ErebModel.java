package ru.pohsmp.core.boss.ereb.client;

import io.redspace.ironsspellbooks.entity.mobs.abstract_spell_casting_mob.AbstractSpellCastingMob;
import io.redspace.ironsspellbooks.entity.mobs.abstract_spell_casting_mob.AbstractSpellCastingMobModel;
import net.minecraft.client.Minecraft;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.util.Mth;
import org.joml.Vector2f;
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
        Vector2f limb = getLimbSwing(entity, entity.walkAnimation, state.getPartialTick());
        float right = Mth.cos(limb.y() * 0.6662f) * 1.4f * limb.x(), left = Mth.cos(limb.y() * 0.6662f + Mth.PI) * 1.4f * limb.x();
        coat("coat_front_r", -3 * Mth.DEG_TO_RAD + Math.min(0, right) * 0.55f);
        coat("coat_front_l", -3 * Mth.DEG_TO_RAD + Math.min(0, left) * 0.55f);
        coat("coat_back_r", 5 * Mth.DEG_TO_RAD + Math.max(0, right) * 0.4f);
        coat("coat_back_l", 5 * Mth.DEG_TO_RAD + Math.max(0, left) * 0.4f);
    }

    private void coat(String bone, float rotX) {
        CoreGeoBone b = getAnimationProcessor().getBone(bone);
        if (b != null) b.setRotX(b.getRotX() + rotX);
    }
}
