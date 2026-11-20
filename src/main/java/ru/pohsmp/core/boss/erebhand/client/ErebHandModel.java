package ru.pohsmp.core.boss.erebhand.client;

import io.redspace.ironsspellbooks.entity.mobs.abstract_spell_casting_mob.AbstractSpellCastingMob;
import io.redspace.ironsspellbooks.entity.mobs.abstract_spell_casting_mob.AbstractSpellCastingMobModel;
import net.minecraft.client.Minecraft;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.util.Mth;
import org.joml.Vector2f;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.boss.erebhand.ErebHandBody;
import software.bernie.geckolib.core.animatable.model.CoreGeoBone;
import software.bernie.geckolib.core.animation.AnimationState;

/**
 * Ereb, the Hand of Lies (and his reflections): geo/entity/ereb_hand.geo.json, textures/entity/ereb_hand/ereb_hand.png — _mended after
 * «Падение маски», _cracked from phase 3 (each with its own _glowmask) — and animations/entity/ereb_hand.animation.json (Iron's casting
 * animations + ereb_hand_*). Every frame: the mask bone hidden while the mask is torn off, everything but the ghost hand hidden while it
 * forms first (the intro); outside our animations the coat tails and the three cape bones follow Iron's procedural walk (the visual
 * letter's formulas) and the ghost hand floats a little.
 */
public class ErebHandModel extends AbstractSpellCastingMobModel {
    public static final ResourceLocation MODEL = new ResourceLocation(PohCore.MODID, "geo/entity/ereb_hand.geo.json");
    public static final ResourceLocation[] TEXTURES = {
            new ResourceLocation(PohCore.MODID, "textures/entity/ereb_hand/ereb_hand.png"),
            new ResourceLocation(PohCore.MODID, "textures/entity/ereb_hand/ereb_hand_mended.png"),
            new ResourceLocation(PohCore.MODID, "textures/entity/ereb_hand/ereb_hand_cracked.png")};
    public static final ResourceLocation ANIMATIONS = new ResourceLocation(PohCore.MODID, "animations/entity/ereb_hand.animation.json");
    /** Hidden while only the hand is there (the intro, form_hand → form). */
    private static final String[] BODY = {"torso", "head", "coat_front_r", "coat_front_l", "coat_back_r", "coat_back_l", "right_leg", "left_leg",
            "right_arm", "left_arm"};

    @Override
    public ResourceLocation getModelResource(AbstractSpellCastingMob e) {
        return MODEL;
    }

    public static ResourceLocation texture(AbstractSpellCastingMob e) {
        return e instanceof ErebHandBody b ? TEXTURES[Math.max(0, Math.min(2, b.mask()))] : TEXTURES[0];
    }

    @Override
    public ResourceLocation getTextureResource(AbstractSpellCastingMob e) {
        return texture(e);
    }

    @Override
    public ResourceLocation getAnimationResource(AbstractSpellCastingMob e) {
        return ANIMATIONS;
    }

    @Override
    public void setCustomAnimations(AbstractSpellCastingMob entity, long instanceId, AnimationState<AbstractSpellCastingMob> state) {
        super.setCustomAnimations(entity, instanceId, state);
        if (!(entity instanceof ErebHandBody b)) return;
        boolean handOnly = b.handOnly();
        CoreGeoBone body = bone("body");
        if (body != null) {   // its own cubes only: the children decide for themselves
            body.setHidden(handOnly);
            body.setChildrenHidden(false);
        }
        for (String n : BODY) {
            CoreGeoBone x = bone(n);
            if (x != null) x.setHidden(handOnly);
        }
        CoreGeoBone mask = bone("mask");
        if (mask != null && !handOnly) mask.setHidden(b.maskOff());
        if (Minecraft.getInstance().isPaused() || b.playingAction()) return;
        Vector2f limb = getLimbSwing(entity, entity.walkAnimation, state.getPartialTick());
        float right = Mth.cos(limb.y() * 0.6662f) * 1.4f * limb.x(), left = Mth.cos(limb.y() * 0.6662f + Mth.PI) * 1.4f * limb.x();
        add("coat_front_r", -3 * Mth.DEG_TO_RAD + Math.min(0, right) * 0.55f);
        add("coat_front_l", -3 * Mth.DEG_TO_RAD + Math.min(0, left) * 0.55f);
        add("coat_back_r", 5 * Mth.DEG_TO_RAD + Math.max(0, right) * 0.4f);
        add("coat_back_l", 5 * Mth.DEG_TO_RAD + Math.max(0, left) * 0.4f);
        float legs = Math.max(right, left);
        add("cape", 3 * Mth.DEG_TO_RAD + Math.max(0, legs) * 0.25f);
        add("cape_mid", 2 * Mth.DEG_TO_RAD + Math.max(0, legs) * 0.15f);
        add("cape_low", 1 * Mth.DEG_TO_RAD);
        CoreGeoBone hand = bone("ghost_hand");   // it floats ±0.6 px over his shoulder (ereb_hand_idle, while ours are not playing)
        if (hand != null) hand.setPosY(hand.getPosY() + 0.6f * Mth.sin((entity.tickCount + state.getPartialTick()) * 0.08f));
    }

    private CoreGeoBone bone(String name) {
        return getAnimationProcessor().getBone(name);
    }

    private void add(String name, float rotX) {
        CoreGeoBone b = bone(name);
        if (b != null) b.setRotX(b.getRotX() + rotX);
    }
}
