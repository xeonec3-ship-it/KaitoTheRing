package ru.pohsmp.core.boss.martin;

import io.redspace.ironsspellbooks.entity.mobs.IAnimatedAttacker;
import java.util.List;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.Mth;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityDimensions;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Pose;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.ai.goal.FloatGoal;
import net.minecraft.world.entity.ai.goal.target.HurtByTargetGoal;
import net.minecraft.world.entity.ai.goal.target.NearestAttackableTargetGoal;
import net.minecraft.world.entity.monster.Monster;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.boss.BossConfig;
import ru.pohsmp.core.boss.BossCore;
import ru.pohsmp.core.boss.BossDef;
import ru.pohsmp.core.boss.BossNet;
import ru.pohsmp.core.boss.BossReplica;
import ru.pohsmp.core.boss.BossTimeline;
import ru.pohsmp.core.boss.PohBoss;
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
 * T29 «Мартин, Последний Полководец»: a GeckoLib monster of our own (geo/entity/martin.geo.json, drawn ×2; the sword and the shields
 * are bones of the model, their visibility is keyed in the animations — no item layer), the framework glue ({@link BossCore}), the
 * intro, the surrender through a block and the answer to «Дезинтеграция: Реплика». The fight itself: {@link MartinFight}.
 */
public class MartinEntity extends Monster implements GeoEntity, IAnimatedAttacker, PohBoss {
    private final BossCore core = new BossCore(this, Martin.DEF);
    final MartinFight fight = new MartinFight(this);
    private final AnimatableInstanceCache cache = GeckoLibUtil.createInstanceCache(this);

    public MartinEntity(EntityType<? extends Monster> type, Level level) {
        super(type, level);
        BossConfig.PerBoss cfg = BossConfig.of(Martin.ID);
        xpReward = cfg != null ? BossConfig.get(cfg.xp) : 100;
        setMaxUpStep(1.5f);
        setPersistenceRequired();
    }

    public static AttributeSupplier.Builder attributes() {
        return Monster.createMonsterAttributes().add(Attributes.MAX_HEALTH, 4000).add(Attributes.ATTACK_DAMAGE, 20).add(Attributes.ARMOR, 18)
                .add(Attributes.ARMOR_TOUGHNESS, 4).add(Attributes.KNOCKBACK_RESISTANCE, 1).add(Attributes.MOVEMENT_SPEED, 0.23)
                .add(Attributes.FOLLOW_RANGE, 48);
    }

    @Override
    public BossCore bossCore() {
        return core;
    }

    @Override
    protected void registerGoals() {
        goalSelector.addGoal(0, new FloatGoal(this));
        targetSelector.addGoal(1, new HurtByTargetGoal(this, MartinSoldierEntity.class));
        targetSelector.addGoal(2, new NearestAttackableTargetGoal<>(this, Player.class, false));
    }

    @Override
    protected float getStandingEyeHeight(Pose pose, EntityDimensions dim) {
        return 3.5f;
    }

    @Override
    public boolean removeWhenFarAway(double d) {
        return false;
    }

    @Override
    protected boolean shouldDespawnInPeaceful() {
        return false;   // summoned by an admin: stays on Peaceful too
    }

    @Override
    protected boolean shouldDropLoot() {
        return false;   // no loot (owner), only experience
    }

    @Override
    public boolean isAlliedTo(Entity e) {
        return e instanceof MartinSoldierEntity || e instanceof MartinBannerEntity || super.isAlliedTo(e);
    }

    @Override
    public boolean causeFallDamage(float d, float m, DamageSource s) {
        return false;
    }

    @Override
    public boolean isPushable() {
        return false;
    }

    // the bar: BossCore's vanilla boss event with the entity's UUID (PohBoss.coreBossEvent), drawn over by BossBarClient

    @Override
    public void startSeenByPlayer(ServerPlayer p) {
        super.startSeenByPlayer(p);
        core.onSeen(p);
    }

    @Override
    public void stopSeenByPlayer(ServerPlayer p) {
        super.stopSeenByPlayer(p);
        core.onUnseen(p);
    }

    // ---------------------------------------------------------------- framework glue

    @Override
    public void tick() {
        super.tick();
        if (level() instanceof ServerLevel sl) {
            core.tick();
            if (isAlive()) fight.tick(sl);
        }
    }

    @Override
    public boolean hurt(DamageSource src, float amount) {
        if (level().isClientSide) return false;
        Entity by = src.getEntity();
        if (by == this || by instanceof MartinSoldierEntity) return false;
        if (core.inFinale()) {
            fight.onHitInFinale(src);
            return false;
        }
        amount = fight.filterHit(src, amount);
        if (amount <= 0) return false;
        float a = core.filterDamage(src, amount);
        if (a <= 0) return false;
        return super.hurt(src, a);
    }

    @Override
    public void setBossAi(boolean on) {
        setNoAi(!on);
        if (!on) {
            getNavigation().stop();
            setDeltaMovement(getDeltaMovement().multiply(0, 1, 0));
        }
    }

    @Override
    public void addAdditionalSaveData(CompoundTag tag) {
        super.addAdditionalSaveData(tag);
        core.save(tag);
    }

    @Override
    public void readAdditionalSaveData(CompoundTag tag) {
        super.readAdditionalSaveData(tag);
        core.load(tag);
        setNoAi(false);
        fight.afterLoad();
    }

    @Override
    public void remove(RemovalReason r) {
        if (level() instanceof ServerLevel sl && r.shouldDestroy()) fight.cleanup(sl);
        else if (level() instanceof ServerLevel sl && r == RemovalReason.UNLOADED_TO_CHUNK) fight.unloadFx(sl);   // FX audit 21.11
        super.remove(r);
    }

    /** Never dies here (it surrenders at 5%); /kill still works: the army goes with it. */
    /** Boss sounds 21.11: plate and shield (sounds.json martin.hurt). */
    @Override
    protected net.minecraft.sounds.SoundEvent getHurtSound(DamageSource src) {
        return BossCore.sound("martin.hurt");
    }

    @Override
    public void die(DamageSource src) {
        super.die(src);
        if (level() instanceof ServerLevel sl) {
            core.onDeath();
            fight.cleanup(sl);
        }
    }

    // ---------------------------------------------------------------- animations (GeckoLib; Iron's SyncAnimationPacket → playAnimation)

    private final AnimationController<MartinEntity> action = new AnimationController<>(this, "action", 3, this::actionPredicate);
    private RawAnimation toPlay;

    @Override
    public void playAnimation(String name) {
        toPlay = RawAnimation.begin().thenPlay(name);
    }

    /** Server: an animation on the clients now (lands a tick or two later for an entity that was just added). */
    void anim(String name) {
        serverTriggerAnimation(name);
    }

    private PlayState actionPredicate(AnimationState<MartinEntity> s) {
        AnimationController<MartinEntity> c = s.getController();
        if (toPlay != null) {
            c.forceAnimationReset();
            c.setAnimation(toPlay);
            toPlay = null;
        }
        return c.getAnimationState() == AnimationController.State.STOPPED ? PlayState.STOP : PlayState.CONTINUE;
    }

    /** Client: an action (attack, special, scene) is playing — the idle / walk loop and the head turn stand aside. */
    public boolean actionPlaying() {
        return action.getAnimationState() != AnimationController.State.STOPPED;
    }

    private static final RawAnimation IDLE = RawAnimation.begin().thenLoop("martin_idle"), WALK = RawAnimation.begin().thenLoop("martin_walk");

    @Override
    public void registerControllers(AnimatableManager.ControllerRegistrar r) {
        r.add(new AnimationController<>(this, "body", 6, s -> {
            if (actionPlaying()) return PlayState.STOP;
            return s.setAndContinue(s.isMoving() ? WALK : IDLE);
        }));
        r.add(action);
    }

    @Override
    public AnimatableInstanceCache getAnimatableInstanceCache() {
        return cache;
    }

    // ---------------------------------------------------------------- facing

    float yawTo(Vec3 p) {
        return (float) (Mth.atan2(p.z - getZ(), p.x - getX()) * Mth.RAD_TO_DEG) - 90;
    }

    void face(float yaw) {
        setYRot(yaw);
        setYHeadRot(yaw);
        setYBodyRot(yaw);
        yRotO = yaw;
        yBodyRotO = yaw;
    }

    // ---------------------------------------------------------------- intro (6.5 s, plan «Появление»)

    @Override
    public void onBossIntro() {
        if (!(level() instanceof ServerLevel sl)) return;
        BossConfig.PerBoss cfg = BossConfig.of(Martin.ID);
        var atk = getAttribute(Attributes.ATTACK_DAMAGE);
        if (cfg != null && atk != null) atk.setBaseValue(BossConfig.get(cfg.attack));
        core.lock(MartinMath.INTRO + 2, true, true);
        List<ServerPlayer> who = core.scene("martin.intro", MartinMath.INTRO, BossNet.SCENE_LOCK_INPUT | BossNet.SCENE_BARS | BossNet.SCENE_NO_HUD,
                BossConfig.get(BossConfig.INTRO_RADIUS), position(), getYRot(), -1);
        Fx.play(sl, Fx.fx("martin_intro").caster(this).at(position()).yaw(getYRot()));
        core.play(new BossTimeline("scene:intro", MartinMath.INTRO)
                .at(0, () -> core.sound("martin.spawn", 4, 1))
                .at(1, () -> anim("martin_spawn"))   // a tick after the spawn packet: the clients track it by now
                .at(MartinMath.INTRO_RISE, () -> core.sound("martin.step", 3, 0.8f))
                .at(MartinMath.INTRO_PULL, () -> core.sound("martin.slam", 1.5f, 1))
                .at(MartinMath.INTRO_SALUTE, () -> core.sound("martin.command", 3, 1))
                .at(MartinMath.INTRO_TITLE, () -> {
                    core.title(who, "martin", MartinMath.INTRO_TITLE_HOLD, "ui.pohsmp_core.martin.subtitle");
                    core.music(true);
                })
                .then(() -> {
                    core.startFight();
                    fight.onFightStart(sl);
                }));
    }

    // ---------------------------------------------------------------- phases and specials

    @Override
    public void onBossPhase(int from, int to) {
        fight.onPhase(from, to);
    }

    @Override
    public boolean onBossSpecial(BossDef.Special s) {
        return fight.special(s.id());
    }

    // ---------------------------------------------------------------- surrender: the next blow is blocked (plan «Блок-сдача»)

    @Override
    public void onBossFinale() {
        fight.startYield();
    }

    // ---------------------------------------------------------------- finisher (framework BossFinisher; ТЗ «Добивание»)

    private Vec3 holdBase;
    private float holdYaw;

    @Override
    public int finisherTicks() {
        return MartinMath.FINISHER;
    }

    @Override
    public int finisherKillTick() {
        return MartinMath.FINISHER_KILL;
    }

    @Override
    public String finisherVictimAnim() {
        return "irons_spellbooks:pohsmp_martin_finisher_victim";   // his own pose (visual assistant), on the martin_finisher clock
    }

    /** Faces the victim, martin_finisher + fx; the victim's own camera on him from 0.2 s. */
    @Override
    public void onFinisherStart(ServerPlayer victim) {
        if (!(level() instanceof ServerLevel sl)) return;
        holdYaw = yawTo(victim.position());
        face(holdYaw);
        holdBase = position();
        anim("martin_finisher");
        core.sound("martin.swing", 3, 0.9f);
        Fx.play(sl, Fx.fx("martin_finisher").caster(this).at(position()).yaw(holdYaw).target(victim));
        core.play(new BossTimeline("finisher_cam", MartinMath.FINISHER_CAM_FROM + 1)
                .at(MartinMath.FINISHER_CAM_FROM, () -> core.sceneFor(victim, "martin.finisher", MartinMath.FINISHER_CAM,
                        BossNet.SCENE_LOCK_INPUT | BossNet.SCENE_NO_HUD, holdBase, holdYaw, victim.getId())));
    }

    @Override
    public Vec3 finisherVictimPos(ServerPlayer victim, int t, Vec3 from) {
        if (holdBase == null) return from;
        double[] h = MartinMath.finisherHold(t);
        Vec3 line = holdBase.add(Vec3.directionFromRotation(0, holdYaw).scale(h[1]));
        Vec3 p = from.lerp(line, h[0]);
        return new Vec3(p.x, Mth.lerp(h[0], from.y, holdBase.y) + h[2] * h[0], p.z);
    }

    /** Pierce, the throw to his feet; the soldiers slam their shields on the ground. */
    @Override
    public void onFinisherTick(ServerPlayer victim, int t) {
        if (t == MartinMath.FINISHER_PIERCE) core.sound(victim.position(), "martin.pierce", 2, 1);
        if (t == MartinMath.FINISHER_THROW) core.sound("martin.swing", 3, 0.8f);
        if (t == MartinMath.FINISHER_SLAM) {
            core.sound(victim.position(), "martin.slam", 3, 1);
            fight.braceAll(20);
            core.sound("martin.shield_hit", 2, 0.8f);
        }
    }

    // ---------------------------------------------------------------- «Дезинтеграция: Реплика»

    /** T32 «Сломать блок»: martin_guard_break 40 ticks (warn 2, hit 14, the shield push ~20 is only visual). */
    @Override
    public ru.pohsmp.core.boss.BossGuardBreak.Timing guardBreakTiming() {
        return new ru.pohsmp.core.boss.BossGuardBreak.Timing(14, 40);
    }

    /** T32 «Сломать блок»: the heavy hit from his melee table (MartinFight). */
    @Override
    public double guardBreakDamage() {
        return fight.guardBreakDamage();
    }

    /** martin_replica_break 2.4 s: block 0.4, slash 0.9, break 1.35, speak 1.7; the phrase over the helmet (+4.6). */
    @Override
    public BossReplica.Reaction replicaReaction() {
        return new BossReplica.Reaction("martin_replica_break", "martin_replica_break", "ui.pohsmp_core.martin.replica",
                MartinMath.REPLICA_DELAY, MartinMath.REPLICA_BREAK, MartinMath.REPLICA_SPEAK, MartinMath.REPLICA_ANIM, 4.6);
    }

    /** The visual assistant's vanilla sounds on block / slash / break; the soldiers raise their shields in time (brace). */
    @Override
    public void onReplicaBreak(LivingEntity caster) {
        core.play(new BossTimeline("replica_extra", MartinMath.REPLICA_BREAK + 1)
                .at(MartinMath.REPLICA_BLOCK, () -> {
                    core.sound("martin.shield_hit", 2, 1);
                    fight.braceAll(30);
                })
                .at(MartinMath.REPLICA_SLASH, () -> core.sound("martin.swing", 2, 0.9f)));   // the break itself: martin.replica_break (BossReplica)
    }

    void vanilla(net.minecraft.sounds.SoundEvent e, float pitch) {
        level().playSound(null, getX(), getY() + 2, getZ(), e, SoundSource.HOSTILE, 2, pitch);
    }
}
