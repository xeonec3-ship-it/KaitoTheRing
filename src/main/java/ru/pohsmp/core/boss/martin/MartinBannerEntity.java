package ru.pohsmp.core.boss.martin;

import io.redspace.ironsspellbooks.entity.mobs.IAnimatedAttacker;
import java.util.UUID;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.syncher.EntityDataAccessor;
import net.minecraft.network.syncher.EntityDataSerializers;
import net.minecraft.network.syncher.SynchedEntityData;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.boss.BossCore;
import ru.pohsmp.core.fx.Fx;
import software.bernie.geckolib.animatable.GeoEntity;
import software.bernie.geckolib.core.animatable.instance.AnimatableInstanceCache;
import software.bernie.geckolib.core.animation.AnimatableManager;
import software.bernie.geckolib.core.animation.AnimationController;
import software.bernie.geckolib.core.animation.AnimationState;
import software.bernie.geckolib.core.animation.RawAnimation;
import software.bernie.geckolib.core.object.PlayState;
import software.bernie.geckolib.util.GeckoLibUtil;

/**
 * Martin's war banner (phase 2 «Знамя»): an entity with a hitbox (0.6×3.9) that does not move; while it stands, soldiers in its aura
 * (r8, fx martin_banner_aura) are stronger. Each hit: martin_banner_hit; health gone → it is cut (martin_banner_cut: the top snaps and
 * falls, fx, removed 2 s later), not killed. Damage from Martin's side is ignored.
 */
public class MartinBannerEntity extends Mob implements GeoEntity, IAnimatedAttacker {
    private static final EntityDataAccessor<Boolean> CUT = SynchedEntityData.defineId(MartinBannerEntity.class, EntityDataSerializers.BOOLEAN);

    UUID leader;
    int auraFx = -1, goneIn = -1;
    private final AnimatableInstanceCache cache = GeckoLibUtil.createInstanceCache(this);

    public MartinBannerEntity(EntityType<? extends Mob> type, Level level) {
        super(type, level);
        xpReward = 0;
        setPersistenceRequired();
        setNoAi(true);
    }

    public static AttributeSupplier.Builder attributes() {
        return Mob.createMobAttributes().add(Attributes.MAX_HEALTH, 120).add(Attributes.KNOCKBACK_RESISTANCE, 1).add(Attributes.MOVEMENT_SPEED, 0);
    }

    @Override
    protected void defineSynchedData() {
        super.defineSynchedData();
        entityData.define(CUT, false);
    }

    void setup(UUID leader, double hp) {
        this.leader = leader;
        var i = getAttribute(Attributes.MAX_HEALTH);
        if (i != null) i.setBaseValue(hp);
        setHealth(getMaxHealth());
    }

    public boolean standing() {
        return isAlive() && !entityData.get(CUT);
    }

    void plantFx(ServerLevel sl) {
        serverTriggerAnimation("martin_banner_plant");
        Fx.play(sl, Fx.fx("martin_banner_plant").at(position()).yaw(getYRot()));
        auraFx = Fx.play(sl, Fx.fx("martin_banner_aura").caster(this).at(position()).attach(this));
    }

    /** The top snaps and falls; removed 2 s later. */
    void cut(ServerLevel sl) {
        if (!standing()) return;
        entityData.set(CUT, true);
        serverTriggerAnimation("martin_banner_cut");
        Fx.play(sl, Fx.fx("martin_banner_cut").at(position()).yaw(getYRot()));
        sl.playSound(null, getX(), getY() + 1.25, getZ(), BossCore.sound("martin.banner_cut"), net.minecraft.sounds.SoundSource.HOSTILE, 3, 1);
        if (auraFx > 0) Fx.stop(sl, auraFx, "");
        auraFx = -1;
        goneIn = MartinMath.BANNER_GONE;
    }

    @Override
    public void tick() {
        super.tick();
        if (!(level() instanceof ServerLevel sl)) return;
        setDeltaMovement(0, getDeltaMovement().y, 0);
        if (goneIn >= 0 && goneIn-- == 0) {
            discard();
            return;
        }
        if (tickCount % 20 == 0 && standing() && !(leader != null && sl.getEntity(leader) instanceof MartinEntity m && m.isAlive())) cut(sl);
    }

    @Override
    public boolean hurt(DamageSource src, float amount) {
        if (level().isClientSide || !standing()) return false;
        Entity by = src.getEntity();
        if (by instanceof MartinEntity || by instanceof MartinSoldierEntity) return false;
        if (!(level() instanceof ServerLevel sl)) return false;
        Vec3 from = src.getSourcePosition();
        Vec3 at = position().add(0, 1.8, 0);
        if (from != null) at = at.add(from.subtract(at).multiply(1, 0, 1).normalize().scale(0.3));
        Fx.play(sl, Fx.fx("martin_banner_hit").at(at));
        serverTriggerAnimation("martin_banner_hit");
        if (amount >= getHealth() || src.is(net.minecraft.tags.DamageTypeTags.BYPASSES_INVULNERABILITY)) {
            setHealth(1);
            cut(sl);
            if (leader != null && sl.getEntity(leader) instanceof MartinEntity m) m.fight.onBannerCut(sl);
            return true;
        }
        setHealth(getHealth() - amount);
        hurtTime = hurtDuration = 6;
        return true;
    }

    @Override
    public boolean isPushable() {
        return false;
    }

    @Override
    public void push(Entity e) {}

    @Override
    public boolean isPickable() {
        return standing();
    }

    @Override
    protected boolean shouldDropLoot() {
        return false;
    }

    @Override
    public boolean removeWhenFarAway(double d) {
        return false;
    }

    @Override
    public boolean causeFallDamage(float d, float m, DamageSource s) {
        return false;
    }

    @Override
    public void addAdditionalSaveData(CompoundTag tag) {
        super.addAdditionalSaveData(tag);
        if (leader != null) tag.putUUID("martin", leader);
    }

    @Override
    public void readAdditionalSaveData(CompoundTag tag) {
        super.readAdditionalSaveData(tag);
        if (tag.hasUUID("martin")) leader = tag.getUUID("martin");
        setNoAi(true);
    }

    // ---------------------------------------------------------------- animations

    private final AnimationController<MartinBannerEntity> action = new AnimationController<>(this, "action", 0, this::actionPredicate);
    private RawAnimation toPlay;

    @Override
    public void playAnimation(String name) {
        toPlay = RawAnimation.begin().thenPlay(name);
    }

    private PlayState actionPredicate(AnimationState<MartinBannerEntity> s) {
        AnimationController<MartinBannerEntity> c = s.getController();
        if (toPlay != null) {
            c.forceAnimationReset();
            c.setAnimation(toPlay);
            toPlay = null;
        }
        return c.getAnimationState() == AnimationController.State.STOPPED ? PlayState.STOP : PlayState.CONTINUE;
    }

    private static final RawAnimation IDLE = RawAnimation.begin().thenLoop("martin_banner_idle"),
            CUT_HOLD = RawAnimation.begin().thenPlay("martin_banner_cut");

    @Override
    public void registerControllers(AnimatableManager.ControllerRegistrar r) {
        r.add(new AnimationController<>(this, "cloth", 4, s -> {
            if (action.getAnimationState() != AnimationController.State.STOPPED) return PlayState.STOP;
            return s.setAndContinue(entityData.get(CUT) ? CUT_HOLD : IDLE);   // a late viewer of a cut banner sees it broken
        }));
        r.add(action);
    }

    @Override
    public AnimatableInstanceCache getAnimatableInstanceCache() {
        return cache;
    }
}
