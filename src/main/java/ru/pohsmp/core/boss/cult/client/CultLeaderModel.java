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
import software.bernie.geckolib.core.animatable.model.CoreGeoBone;
import software.bernie.geckolib.core.animation.AnimationState;

/**
 * The Head of the Cult: geo/entity/cult_leader.geo.json (Tyros's bones and names, our cubes and the cape), our textures (the soul form
 * cult_leader_soul_mode), our animation file (all of Iron's casting animations under their names + cult_leader_*). The scythe arm
 * pose of Iron's FireBossModel, for our cult_scythe; the cape swings a little with the legs.
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
            boss.isAnimatingDampener = entity.isAnimating() ? Mth.lerp(0.15f * pt, boss.isAnimatingDampener, 0) : Mth.lerp(0.05f * pt, boss.isAnimatingDampener, 1);
            if (entity.getMainHandItem().is(CultLeader.SCYTHE.get())) {   // Iron's scythe hold (FireBossModel)
                CoreGeoBone arm = getAnimationProcessor().getBone("right_arm"), hand = getAnimationProcessor().getBone("bipedHandRight");
                if (arm != null && hand != null) {
                    Vector3f armPose = new Vector3f(-30, -30, 10).mul(Mth.DEG_TO_RAD * boss.isAnimatingDampener);
                    transformStack.pushRotation(arm, armPose);
                    transformStack.pushRotation(hand, new Vector3f(-5, 0, -48).mul(Mth.DEG_TO_RAD * boss.isAnimatingDampener));
                    if (!entity.isAnimating()) {
                        float walk = Mth.cos(limb.y() * 0.6662f + Mth.PI) * 2f * limb.x() * 0.5f * -0.75f;
                        transformStack.pushRotation(arm, walk, 0, 0);
                    }
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
