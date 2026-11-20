package ru.pohsmp.core.boss.erebhand;

import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.protocol.Packet;
import net.minecraft.network.protocol.game.ClientGamePacketListener;
import net.minecraft.network.syncher.EntityDataAccessor;
import net.minecraft.network.syncher.EntityDataSerializers;
import net.minecraft.network.syncher.SynchedEntityData;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.level.Level;
import net.minecraftforge.network.NetworkHooks;
import software.bernie.geckolib.animatable.GeoEntity;
import software.bernie.geckolib.core.animatable.instance.AnimatableInstanceCache;
import software.bernie.geckolib.core.animation.AnimatableManager;
import software.bernie.geckolib.core.animation.AnimationController;
import software.bernie.geckolib.core.animation.RawAnimation;
import software.bernie.geckolib.core.object.PlayState;
import software.bernie.geckolib.util.GeckoLibUtil;

/**
 * The giant hand — his own ghost hand, big (geo/entity/ereb_hand_giant.geo.json, ×5 for «Длань Лжи», drawn by the client renderer with
 * the synced scale; the wrist is the entity's position). No body, no hitbox, never saved: the fight moves it and sets its pose
 * (DESCEND → GRAB (then the fist loop) → RELEASE; HOVER, SLAM). Removes itself if nobody drives it for a while.
 */
public class ErebHandGiant extends Entity implements GeoEntity {
    public static final int DESCEND = 0, GRAB = 1, RELEASE = 2, HOVER = 3, SLAM = 4;
    private static final EntityDataAccessor<Integer> POSE = SynchedEntityData.defineId(ErebHandGiant.class, EntityDataSerializers.INT);
    private static final EntityDataAccessor<Float> SCALE = SynchedEntityData.defineId(ErebHandGiant.class, EntityDataSerializers.FLOAT);
    private final AnimatableInstanceCache cache = GeckoLibUtil.createInstanceCache(this);
    private int life = 20 * 30;
    private int shownPose = -1;

    public ErebHandGiant(EntityType<? extends ErebHandGiant> type, Level level) {
        super(type, level);
        noPhysics = true;
        setNoGravity(true);
    }

    @Override
    protected void defineSynchedData() {
        entityData.define(POSE, DESCEND);
        entityData.define(SCALE, (float) ErebHandMath.GIANT_SCALE);
    }

    public int pose() {
        return entityData.get(POSE);
    }

    public void setPose(int pose) {
        entityData.set(POSE, pose);
    }

    public float scale() {
        return entityData.get(SCALE);
    }

    public void setScale(float s) {
        entityData.set(SCALE, s);
    }

    /** It lives this many ticks more (the fight keeps calling it while it drives the hand). */
    public void lifeTicks(int ticks) {
        life = ticks;
    }

    @Override
    public void tick() {
        super.tick();
        if (!level().isClientSide && --life <= 0) discard();
    }

    // ---------------------------------------------------------------- GeckoLib: the pose → its animation

    @Override
    public void registerControllers(AnimatableManager.ControllerRegistrar controllers) {
        controllers.add(new AnimationController<>(this, "giant", 3, state -> {
            int p = pose();
            if (p != shownPose) {
                shownPose = p;
                state.getController().forceAnimationReset();
                state.getController().setAnimation(switch (p) {
                    case GRAB -> RawAnimation.begin().thenPlay("ereb_hand_giant_grab").thenLoop("ereb_hand_giant_fist");
                    case RELEASE -> RawAnimation.begin().thenPlay("ereb_hand_giant_release");
                    case HOVER -> RawAnimation.begin().thenLoop("ereb_hand_giant_hover");
                    case SLAM -> RawAnimation.begin().thenPlay("ereb_hand_giant_slam").thenLoop("ereb_hand_giant_hover");
                    default -> RawAnimation.begin().thenLoop("ereb_hand_giant_descend");
                });
            }
            return PlayState.CONTINUE;
        }));
    }

    @Override
    public AnimatableInstanceCache getAnimatableInstanceCache() {
        return cache;
    }

    // ---------------------------------------------------------------- not a body

    @Override
    public boolean hurt(DamageSource src, float amount) {
        return false;
    }

    @Override
    public boolean isPickable() {
        return false;
    }

    @Override
    public boolean isPushable() {
        return false;
    }

    @Override
    public boolean shouldBeSaved() {
        return false;
    }

    @Override
    public boolean shouldRenderAtSqrDistance(double d) {
        return d < 128 * 128;
    }

    @Override
    protected void readAdditionalSaveData(CompoundTag tag) {}

    @Override
    protected void addAdditionalSaveData(CompoundTag tag) {}

    @Override
    public Packet<ClientGamePacketListener> getAddEntityPacket() {
        return NetworkHooks.getEntitySpawningPacket(this);
    }
}
