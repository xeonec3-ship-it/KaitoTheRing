package ru.pohsmp.core.boss.erebhand.client;

import io.redspace.ironsspellbooks.entity.mobs.abstract_spell_casting_mob.AbstractSpellCastingMob;
import io.redspace.ironsspellbooks.entity.mobs.abstract_spell_casting_mob.AbstractSpellCastingMobModel;
import net.minecraft.client.Minecraft;
import net.minecraft.resources.ResourceLocation;
import org.joml.Vector2f;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.boss.ClothSway;
import ru.pohsmp.core.boss.client.ClothClient;
import ru.pohsmp.core.boss.erebhand.ErebHandBody;
import software.bernie.geckolib.core.animatable.model.CoreGeoBone;
import software.bernie.geckolib.core.animation.AnimationState;

/**
 * Ereb, the Hand of Lies (and his reflections): geo/entity/ereb_hand.geo.json, textures/entity/ereb_hand/ereb_hand.png — _mended after
 * «Падение маски», _cracked from phase 3 (each with its own _glowmask) — and animations/entity/ereb_hand.animation.json (Iron's casting
 * animations + ereb_hand_*). Every frame: the mask bone hidden while the mask is torn off, everything but the ghost hand hidden while it
 * forms first (the intro); outside our animations the coat tails and the three cape bones follow Iron's procedural walk (ClothSway:
 * the visual letter's formulas in GeckoLib axes, clamped, pushed through Iron's transformStack) and the ghost hand floats a little.
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
        // Only deltas from the rest pose (ClothSway: GeckoLib axes, clamped) and only through Iron's transformStack: it sets the bones
        // back to rest before the next frame. bone.setRotX(bone.getRotX() + …) piled up instead (GeckoLib skips its own reset for a bone
        // marked changed after its tick) — the tails and the cape spun round, the ghost hand drifted blocks up (the owner's screenshot).
        Vector2f limb = getLimbSwing(entity, entity.walkAnimation, state.getPartialTick());
        ClothClient.push(transformStack, this::bone, ClothSway.solve(ClothClient.leg(entity, bone("right_leg"), limb, true),
                ClothClient.leg(entity, bone("left_leg"), limb, false)));
        CoreGeoBone hand = bone("ghost_hand");   // it floats ±0.6 px over his shoulder (ereb_hand_idle, while ours are not playing)
        if (hand != null) transformStack.pushPosition(hand, 0, ClothSway.handFloat(entity.tickCount + state.getPartialTick()), 0);
    }

    private CoreGeoBone bone(String name) {
        return getAnimationProcessor().getBone(name);
    }

}
