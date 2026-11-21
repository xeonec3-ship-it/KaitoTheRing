package ru.pohsmp.core.boss.cult.client;

import io.redspace.ironsspellbooks.entity.mobs.abstract_spell_casting_mob.AbstractSpellCastingMob;
import io.redspace.ironsspellbooks.entity.mobs.abstract_spell_casting_mob.AbstractSpellCastingMobModel;
import net.minecraft.client.Minecraft;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.util.Mth;
import org.joml.Vector2f;
import org.joml.Vector3f;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.boss.cult.CultLeader;
import ru.pohsmp.core.boss.cult.CultLeaderEntity;
import ru.pohsmp.core.boss.cult.CultMath;
import software.bernie.geckolib.core.animatable.model.CoreGeoBone;
import software.bernie.geckolib.core.animation.AnimationState;

/**
 * The Head of the Cult: geo/entity/cult_leader.geo.json (Tyros's bones and names, our cubes and the cape), our textures (the soul form
 * cult_leader_soul_mode), our animation file (all of Iron's casting animations under their names + cult_leader_*). Outside animations
 * the arm holds our cult_scythe as Tyros holds his (the animations begin and end in that pose); the cape swings a little with the legs.
 */
public class CultLeaderModel extends AbstractSpellCastingMobModel {
    public static final ResourceLocation MODEL = new ResourceLocation(PohCore.MODID, "geo/entity/cult_leader.geo.json");
    public static final ResourceLocation TEXTURE = new ResourceLocation(PohCore.MODID, "textures/entity/cult_leader/cult_leader.png");
    public static final ResourceLocation TEXTURE_SOUL = new ResourceLocation(PohCore.MODID, "textures/entity/cult_leader/cult_leader_soul_mode.png");
    public static final ResourceLocation ANIMATIONS = new ResourceLocation(PohCore.MODID, "animations/entity/cult_leader.animation.json");

    @Override
    public ResourceLocation getModelResource(AbstractSpellCastingMob e) {
        return MODEL;
    }

    @Override
    public ResourceLocation getTextureResource(AbstractSpellCastingMob e) {
        return e instanceof CultLeaderEntity c && c.isSoulMode() ? TEXTURE_SOUL : TEXTURE;
    }

    @Override
    public ResourceLocation getAnimationResource(AbstractSpellCastingMob e) {
        return ANIMATIONS;
    }

    @Override
    public void setCustomAnimations(AbstractSpellCastingMob entity, long instanceId, AnimationState<AbstractSpellCastingMob> state) {
        if (Minecraft.getInstance().isPaused()) return;
        if (entity instanceof CultLeaderEntity boss) {
            float pt = state.getPartialTick();
            Vector2f limb = getLimbSwing(entity, entity.walkAnimation, pt);
            // Scythe hold outside animations = Tyros's (owner 21.11): FireBossModel's numbers (CultMath.HOLD_*). The animations of the
            // Head start and end in this pose themselves (tools/anim_cloth.hold_additive), so no damped blend: it would add the pose
            // twice. The scythe slides 3 px along its shaft in the fist and the scythe arm does not swing while walking (base swing
            // cancelled) - with Tyros's swing the blade went 3.4 px into the ground.
            boolean anim = entity.isAnimating();
            boss.isAnimatingDampener = anim ? 0 : 1;
            if (!anim && entity.getMainHandItem().is(CultLeader.SCYTHE.get())) {
                CoreGeoBone arm = getAnimationProcessor().getBone("right_arm"), hand = getAnimationProcessor().getBone("bipedHandRight");
                if (arm != null && hand != null) {
                    transformStack.pushRotation(arm, deg(CultMath.HOLD_ARM));
                    transformStack.pushRotation(hand, deg(CultMath.HOLD_HAND));
                    transformStack.pushPosition(hand, new Vector3f(CultMath.HOLD_SLIDE[0], CultMath.HOLD_SLIDE[1], CultMath.HOLD_SLIDE[2]));
                    transformStack.pushRotation(arm, CultMath.holdArmWalk(limb.x(), limb.y()), 0, 0);
                }
            }
            CoreGeoBone cape = getAnimationProcessor().getBone("cape");   // 6° + max(0, ±leg swing)·0.6 (the visual assistant's note)
            if (cape != null) {
                float swing = Math.abs(Mth.cos(limb.y() * 0.6662f) * 1.4f * limb.x());
                transformStack.pushRotation(cape, (6 * Mth.DEG_TO_RAD + swing * 0.6f), 0, 0);
            }
            if (boss.isHalfHealthAttacking()) {
                float f = boss.tickCount + pt;
                bob("right_arm", f * 3, -4);
                bob("left_arm", f * 3, 4);
                bob("right_leg", f, -1.5f);
                bob("left_leg", f + 90, 1.5f);
            }
        }
        super.setCustomAnimations(entity, instanceId, state);
    }

    private static Vector3f deg(float[] v) {
        return new Vector3f(v[0], v[1], v[2]).mul(Mth.DEG_TO_RAD);
    }

    private void bob(String bone, float offset, float mult) {
        CoreGeoBone b = getAnimationProcessor().getBone(bone);
        if (b != null) bobBone(b, offset, mult);
    }

    @Override
    protected Vector2f getLimbSwing(AbstractSpellCastingMob entity, net.minecraft.world.entity.WalkAnimationState walk, float pt) {
        Vector2f swing = super.getLimbSwing(entity, walk, pt);
        swing.mul(0.6f, 1);
        return swing;
    }
}
