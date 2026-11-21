package ru.pohsmp.core.boss.aris;

import java.util.EnumSet;
import java.util.List;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.syncher.EntityDataAccessor;
import net.minecraft.network.syncher.EntityDataSerializers;
import net.minecraft.network.syncher.SynchedEntityData;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.ai.goal.FloatGoal;
import net.minecraft.world.entity.ai.goal.Goal;
import net.minecraft.world.entity.ai.goal.LookAtPlayerGoal;
import net.minecraft.world.entity.ai.goal.RandomLookAroundGoal;
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
import software.bernie.geckolib.core.animation.RawAnimation;
import software.bernie.geckolib.util.GeckoLibUtil;

/**
 * T28 «Арис, Мифический Кузнец»: a GeckoLib body of her own (not Iron's — its procedural walk would fight our idle/walk), the
 * hammer is part of the model. Her animation and texture state (horns / eyes: aris, aris_dim, aris_spent, aris_mythic) are synced
 * data set by the server on the ticks of the scripts; the client only draws them. The fight itself is {@link ArisFight}.
 */
public class ArisEntity extends Monster implements GeoEntity, PohBoss {
    private static final EntityDataAccessor<Integer> TEX = SynchedEntityData.defineId(ArisEntity.class, EntityDataSerializers.INT);
    private static final EntityDataAccessor<Integer> ACTION = SynchedEntityData.defineId(ArisEntity.class, EntityDataSerializers.INT);
    private static final EntityDataAccessor<Integer> ACTION_SEQ = SynchedEntityData.defineId(ArisEntity.class, EntityDataSerializers.INT);

    private final BossCore core = new BossCore(this, Aris.DEF);
    final ArisFight fight = new ArisFight(this);
    private final AnimatableInstanceCache cache = GeckoLibUtil.createInstanceCache(this);
    private int actionEnd;
    /** Client: the last action sequence the controller started. */
    private int seenSeq = -1;

    public ArisEntity(EntityType<? extends Monster> type, Level level) {
        super(type, level);
        BossConfig.PerBoss cfg = BossConfig.of(Aris.ID);
        xpReward = cfg != null ? BossConfig.get(cfg.xp) : 60;
        setPersistenceRequired();
        setMaxUpStep(1.0f);
    }

    public static AttributeSupplier.Builder attributes() {
        return Monster.createMonsterAttributes().add(Attributes.MAX_HEALTH, 4400).add(Attributes.ATTACK_DAMAGE, 18).add(Attributes.ARMOR, 18)
                .add(Attributes.ARMOR_TOUGHNESS, 3).add(Attributes.KNOCKBACK_RESISTANCE, 1).add(Attributes.MOVEMENT_SPEED, 0.22)
                .add(Attributes.FOLLOW_RANGE, 48);
    }

    @Override
    public BossCore bossCore() {
        return core;
    }

    // ---------------------------------------------------------------- synced state

    @Override
    protected void defineSynchedData() {
        super.defineSynchedData();
        entityData.define(TEX, ArisMath.TEX_BASE);
        entityData.define(ACTION, 0);
        entityData.define(ACTION_SEQ, 0);
    }

    public int tex() {
        return entityData.get(TEX);
    }

    void setTex(int t) {
        entityData.set(TEX, t);
    }

    /** The current one-shot animation (ArisMath.ANIMS index) or 0. */
    public int action() {
        return entityData.get(ACTION);
    }

    /** Server: plays animation.aris.<name> from its start (synced; the controller restarts it even if it is the same one). */
    void play(String name) {
        int a = ArisMath.anim(name);
        entityData.set(ACTION, a);
        entityData.set(ACTION_SEQ, entityData.get(ACTION_SEQ) + 1);
        actionEnd = tickCount + ArisMath.ANIM_TICKS[a];
    }

    void stopAction() {
        entityData.set(ACTION, 0);
    }

    // ---------------------------------------------------------------- AI

    @Override
    protected void registerGoals() {
        goalSelector.addGoal(0, new FloatGoal(this));
        goalSelector.addGoal(2, new HammerGoal());
        goalSelector.addGoal(7, new LookAtPlayerGoal(this, Player.class, 16f));
        goalSelector.addGoal(8, new RandomLookAroundGoal(this));
        targetSelector.addGoal(1, new HurtByTargetGoal(this));
        targetSelector.addGoal(2, new NearestAttackableTargetGoal<>(this, Player.class, false));
    }

    /** Walks up to her target and swings the hammer every melee_interval ticks (×0.85 in phase 3); stands while she acts. */
    private final class HammerGoal extends Goal {
        private int repath, cooldown = 20;

        HammerGoal() {
            setFlags(EnumSet.of(Flag.MOVE, Flag.LOOK));
        }

        @Override
        public boolean canUse() {
            LivingEntity t = getTarget();
            return t != null && t.isAlive() && core.started() && !core.inFinale();
        }

        @Override
        public boolean requiresUpdateEveryTick() {
            return true;
        }

        @Override
        public void stop() {
            getNavigation().stop();
        }

        @Override
        public void tick() {
            LivingEntity t = getTarget();
            if (t == null) return;
            if (cooldown > 0) cooldown--;
            if (fight.acting()) {
                getNavigation().stop();
                return;
            }
            getLookControl().setLookAt(t, 30, 30);
            double d = distanceTo(t);
            if (d > ArisMath.SWING_REACH - 0.6) {
                if (--repath <= 0) {
                    repath = 10;
                    getNavigation().moveTo(t, 1.0);
                }
            } else getNavigation().stop();
            if (d <= ArisMath.SWING_REACH && cooldown <= 0 && fight.swing(t)) {
                double mult = core.phase() >= 2 ? ArisConfig.get(ArisConfig.MYTHIC_INTERVAL) : 1;
                int min = ArisConfig.get(ArisConfig.MELEE_MIN), max = Math.max(min, ArisConfig.get(ArisConfig.MELEE_MAX));
                cooldown = ArisMath.SWING + (int) Math.round((min + getRandom().nextInt(max - min + 1)) * mult);
            }
        }
    }

    @Override
    public void setBossAi(boolean on) {
        setNoAi(!on);
        if (!on) {
            getNavigation().stop();
            setDeltaMovement(0, getDeltaMovement().y, 0);
        }
    }

    // ---------------------------------------------------------------- framework glue

    @Override
    public void tick() {
        super.tick();
        if (level() instanceof ServerLevel sl) {
            if (action() != 0 && tickCount >= actionEnd && action() != ArisMath.anim("surrender")) stopAction();
            core.tick();
            if (isAlive()) fight.tick(sl);
        }
    }

    @Override
    public boolean hurt(DamageSource src, float amount) {
        if (level().isClientSide) return false;
        Entity by = src.getEntity();
        if (by == this || by instanceof ArisBladeEntity || src.getDirectEntity() instanceof ArisBladeEntity) return false;
        if (src.is(net.minecraft.tags.DamageTypeTags.IS_FALL)) return false;
        amount = fight.filterDamage(amount);
        float a = core.filterDamage(src, amount);
        if (a <= 0) return false;
        return super.hurt(src, a);
    }

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

    @Override
    public void addAdditionalSaveData(CompoundTag tag) {
        super.addAdditionalSaveData(tag);
        core.save(tag);
        tag.putInt("aris_tex", tex());
    }

    @Override
    public void readAdditionalSaveData(CompoundTag tag) {
        super.readAdditionalSaveData(tag);
        core.load(tag);
        setTex(tag.getInt("aris_tex") == ArisMath.TEX_SPENT ? ArisMath.TEX_BASE : tag.getInt("aris_tex"));
        setNoAi(false);
        fight.afterLoad();
    }

    @Override
    public boolean removeWhenFarAway(double d) {
        return false;
    }

    @Override
    public boolean causeFallDamage(float dist, float mult, DamageSource src) {
        return false;
    }

    @Override
    protected void dropAllDeathLoot(DamageSource src) {}   // no loot (owner)

    @Override
    public boolean isAlliedTo(Entity e) {
        return e instanceof ArisBladeEntity || super.isAlliedTo(e);
    }

    /** Boss sounds 21.11: plate clang (sounds.json aris.hurt). */
    @Override
    protected net.minecraft.sounds.SoundEvent getHurtSound(DamageSource src) {
        return BossCore.sound("aris.hurt");
    }

    @Override
    public void remove(RemovalReason r) {
        if (r == RemovalReason.UNLOADED_TO_CHUNK && level() instanceof ServerLevel sl) fight.unloadFx(sl);   // FX audit 21.11
        super.remove(r);
    }

    @Override
    public void die(DamageSource src) {   // only /kill reaches this (she surrenders at 5%)
        super.die(src);
        if (level() instanceof ServerLevel sl && isDeadOrDying()) {
            core.onDeath();
            fight.cleanup(sl);
        }
    }

    // ---------------------------------------------------------------- intro (9.0 s, «Появление»)

    @Override
    public void onBossIntro() {
        if (!(level() instanceof ServerLevel sl)) return;
        BossConfig.PerBoss cfg = BossConfig.of(Aris.ID);
        var atk = getAttribute(Attributes.ATTACK_DAMAGE);
        if (cfg != null && atk != null) atk.setBaseValue(BossConfig.get(cfg.attack) + ArisConfig.get(ArisConfig.HAMMER));   // + the hammer
        core.lock(ArisMath.INTRO + 2, true, true);
        setTex(ArisMath.TEX_SPENT);
        play("spawn");
        List<ServerPlayer> who = core.scene("aris.intro", ArisMath.INTRO, BossNet.SCENE_LOCK_INPUT | BossNet.SCENE_BARS | BossNet.SCENE_NO_HUD,
                BossConfig.get(BossConfig.INTRO_RADIUS), position(), getYRot(), -1);
        Fx.play(sl, Fx.fx("aris_intro").at(position()).yaw(getYRot()));
        BossTimeline t = new BossTimeline("scene:intro", ArisMath.INTRO);
        for (int k : ArisMath.INTRO_KNOCKS) t.at(k, () -> core.sound("aris.slam", 0.8f, 0.8f));
        core.play(t.at(ArisMath.INTRO_SPAWN_SOUND, () -> core.sound("aris.spawn", 4, 1))
                .at(ArisMath.INTRO_DIM, () -> setTex(ArisMath.TEX_DIM))
                .at(ArisMath.INTRO_HORNS, () -> setTex(ArisMath.TEX_BASE))
                .at(ArisMath.INTRO_IMPACT, () -> {
                    core.sound("aris.slam", 4, 1);
                    core.sound("aris.phase", 3, 1);
                })
                .at(ArisMath.INTRO_TITLE, () -> {
                    core.title(who, "aris", ArisMath.INTRO_TITLE_HOLD, "ui.pohsmp_core.aris.subtitle");
                    core.music(true);
                })
                .then(() -> {
                    setTex(ArisMath.TEX_BASE);
                    core.startFight();
                    core.actionbar(core.arenaRadius() + 8, ArisFight.ui("phase1"));
                }));
    }

    // ---------------------------------------------------------------- phases, specials

    @Override
    public void onBossPhase(int from, int to) {
        fight.onPhase(from, to);
    }

    @Override
    public boolean onBossSpecial(BossDef.Special s) {
        return fight.special(s.id());
    }

    // ---------------------------------------------------------------- surrender (5.0 s scene, then the NPC)

    @Override
    public void onBossFinale() {
        if (!(level() instanceof ServerLevel sl)) {
            core.endFinale();
            return;
        }
        fight.cleanup(sl);
        getNavigation().stop();
        setTarget(null);
        int before = tex();
        play("surrender");
        Fx.play(sl, Fx.fx("aris_surrender").at(position()).yaw(getYRot()));
        List<ServerPlayer> who = core.scene("aris.surrender", ArisMath.SURRENDER, BossNet.SCENE_LOCK_INPUT | BossNet.SCENE_BARS | BossNet.SCENE_NO_HUD,
                48, position(), getYRot(), -1);
        core.play(new BossTimeline("scene:surrender", ArisMath.SURRENDER)
                .during(0, ArisMath.SURRENDER - 1, t -> {
                    int s = ArisMath.surrenderTexture(t, before);
                    if (s != tex()) setTex(s);
                })
                .at(ArisMath.SURRENDER_STAGGER, () -> core.sound("aris.swing", 1, 0.6f))
                .at(ArisMath.SURRENDER_PLANT, () -> core.sound("aris.slam", 1.5f, 0.7f))
                .at(ArisMath.SURRENDER_HAMMER_DROP, () -> core.sound("aris.hammer_drop", 2, 1))
                .at(ArisMath.SURRENDER_SPEAK, () -> {
                    core.say("ui.pohsmp_core.aris.surrender", 48, ArisMath.SURRENDER_SUBTITLE, 2.4);
                    core.sound("aris.surrender", 2, 1);
                })
                .then(() -> {
                    core.sceneStop(who, "aris.surrender");
                    core.actionbar(48, ArisFight.ui("surrendered"));
                    core.endFinale();
                }));
    }

    // ---------------------------------------------------------------- finisher (framework BossFinisher; T28 «Добивание»)

    private Vec3 holdPoint;

    @Override
    public int finisherTicks() {
        return ArisMath.FINISHER;
    }

    @Override
    public int finisherKillTick() {
        return ArisMath.FINISHER_KILL;
    }

    /** Her own victim pose: kneels, then lies flat on its face, head to her (48 ticks). */
    @Override
    public String finisherVictimAnim() {
        return "irons_spellbooks:pohsmp_aris_finisher_victim";
    }

    @Override
    public void onFinisherStart(ServerPlayer victim) {
        if (!(level() instanceof ServerLevel sl)) return;
        fight.onFinisher();
        getNavigation().stop();
        float yaw = (float) (Math.atan2(victim.getZ() - getZ(), victim.getX() - getX()) * 180 / Math.PI) - 90;
        fight.face(yaw);
        holdPoint = ArisFight.ground(sl, position().add(Vec3.directionFromRotation(0, yaw).scale(ArisMath.FINISHER_DIST)));
        // the pose is made for «head to Aris»: the victim faces her (body and head), its feet stay where they are until the pull
        float back = yaw + 180;
        victim.connection.teleport(victim.getX(), victim.getY(), victim.getZ(), back, 0);
        victim.setYRot(back);
        victim.setYHeadRot(back);
        victim.setYBodyRot(back);
        play("finisher");
        core.sound("aris.swing", 1.5f, 0.7f);
        Fx.play(sl, Fx.fx("aris_finisher").at(position()).yaw(yaw).target(victim));
        core.play(new BossTimeline("finisher_cam", ArisMath.FINISHER_CAM_FROM + 1)
                .at(ArisMath.FINISHER_CAM_FROM, () -> core.sceneFor(victim, "aris.finisher", ArisMath.FINISHER_CAM,
                        BossNet.SCENE_LOCK_INPUT | BossNet.SCENE_NO_HUD, holdPoint, yaw, victim.getId())));
    }

    /** Pulled 1.6 before her (body forward) and held on the ground. */
    @Override
    public Vec3 finisherVictimPos(ServerPlayer victim, int t, Vec3 from) {
        if (holdPoint == null) return from;
        return from.lerp(holdPoint, ArisMath.finisherPull(t));
    }

    @Override
    public void onFinisherTick(ServerPlayer victim, int t) {
        if (t == ArisMath.FINISHER_SLAM && level() instanceof ServerLevel sl && holdPoint != null) {
            core.sound(holdPoint, "aris.slam", 3, 0.9f);
            core.sound(holdPoint, "aris.anvil_ring", 2, 0.8f);   // the flash, sparks and heat ring are in aris_finisher
        }
    }

    // ---------------------------------------------------------------- T32 «Сломать блок» (framework BossGuardBreak)

    /** Not in the middle of her own swing / cast (actingUntil) or a lock. */
    @Override
    public boolean guardBreakFree() {
        return !fight.acting();
    }

    @Override
    public double guardBreakDamage() {
        return fight.guardBreakDamage();
    }

    /** animation.aris.guard_break (her file's rule), through the synced action id. */
    @Override
    public String guardBreakAnimation() {
        return "animation.aris.guard_break";
    }

    @Override
    public void playGuardBreak(String animation) {
        play("guard_break");
    }

    // ---------------------------------------------------------------- «Дезинтеграция: Реплика»

    /** animation.aris.replica_break (2.0 s, strike 0.65, break 1.15, speak 1.4) + fx aris_replica_break; the phrase on speak. */
    @Override
    public BossReplica.Reaction replicaReaction() {
        return new BossReplica.Reaction(null, "aris_replica_break", "ui.pohsmp_core.aris.replica", ArisMath.REPLICA_DELAY, ArisMath.REPLICA_BREAK,
                ArisMath.REPLICA_SPEAK, ArisMath.REPLICA, ArisMath.REPLICA_SUBTITLE_H);
    }

    @Override
    public void onReplicaBreak(LivingEntity caster) {
        getNavigation().stop();
        Vec3 d = caster.position().subtract(position());
        if (d.horizontalDistanceSqr() > 1e-4) fight.face((float) (Math.atan2(d.z, d.x) * 180 / Math.PI) - 90);
        play("replica_break");
        core.play(new BossTimeline("replica_sounds", ArisMath.REPLICA_BREAK + 1)
                .at(ArisMath.REPLICA_STRIKE, () -> core.sound("aris.anvil_ring", 2, 1))
                .at(ArisMath.REPLICA_BREAK, () -> core.sound("aris.hiss", 2, 0.9f)));
    }

    void vanilla(net.minecraft.sounds.SoundEvent e, float vol, float pitch) {
        level().playSound(null, getX(), getY(), getZ(), e, net.minecraft.sounds.SoundSource.HOSTILE, vol, pitch);
    }

    // ---------------------------------------------------------------- GeckoLib

    private static final RawAnimation IDLE = RawAnimation.begin().thenLoop("animation.aris.idle");
    private static final RawAnimation WALK = RawAnimation.begin().thenLoop("animation.aris.walk");

    @Override
    public void registerControllers(AnimatableManager.ControllerRegistrar r) {
        r.add(new AnimationController<>(this, "main", 4, s -> {
            int a = action();
            if (a > 0) {
                int seq = entityData.get(ACTION_SEQ);
                if (seq != seenSeq) {
                    seenSeq = seq;
                    s.getController().forceAnimationReset();
                }
                return s.setAndContinue(RawAnimation.begin().thenPlay("animation.aris." + ArisMath.ANIMS[a]));
            }
            seenSeq = entityData.get(ACTION_SEQ);
            return s.setAndContinue(s.isMoving() ? WALK : IDLE);
        }));
    }

    @Override
    public AnimatableInstanceCache getAnimatableInstanceCache() {
        return cache;
    }

    /** Client: the dropped hammer (bone hammer_ground) is shown only in the surrender. */
    public boolean hammerOnGround() {
        return action() == ArisMath.anim("surrender");
    }
}
