package ru.pohsmp.core.boss.irina;

import io.redspace.ironsspellbooks.entity.mobs.IAnimatedAttacker;
import io.redspace.ironsspellbooks.entity.mobs.abstract_spell_casting_mob.AbstractSpellCastingMob;
import java.util.List;
import java.util.Map;
import java.util.Set;
import javax.annotation.Nullable;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.syncher.EntityDataAccessor;
import net.minecraft.network.syncher.EntityDataSerializers;
import net.minecraft.network.syncher.SynchedEntityData;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.tags.DamageTypeTags;
import net.minecraft.util.Mth;
import net.minecraft.world.DifficultyInstance;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.damagesource.DamageTypes;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.MobSpawnType;
import net.minecraft.world.entity.SpawnGroupData;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.ai.goal.FloatGoal;
import net.minecraft.world.entity.ai.goal.LookAtPlayerGoal;
import net.minecraft.world.entity.ai.goal.RandomLookAroundGoal;
import net.minecraft.world.entity.ai.goal.target.HurtByTargetGoal;
import net.minecraft.world.entity.ai.goal.target.NearestAttackableTargetGoal;
import net.minecraft.world.entity.monster.Monster;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.ServerLevelAccessor;
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.boss.BossConfig;
import ru.pohsmp.core.boss.BossCore;
import ru.pohsmp.core.boss.BossDef;
import ru.pohsmp.core.boss.BossNet;
import ru.pohsmp.core.boss.BossReplica;
import ru.pohsmp.core.boss.BossTimeline;
import ru.pohsmp.core.boss.PohBoss;
import ru.pohsmp.core.fx.Fx;
import software.bernie.geckolib.core.animation.AnimatableManager;
import software.bernie.geckolib.core.animation.AnimationController;
import software.bernie.geckolib.core.animation.AnimationState;
import software.bernie.geckolib.core.animation.RawAnimation;
import software.bernie.geckolib.core.object.PlayState;

/**
 * T27 «Ирина, Ведьма Ревности». Iron's casting mob (GeckoLib; bones of Iron's mage, so its casting animations fit) with her own
 * model (geo/entity/irina.geo.json), staff and TWO animation controllers of her own: the body (irina_*: idle / walk and every action
 * sent with {@link #serverTriggerAnimation}) and the cloth (irina_cloth_*: the ribbons, sleeves, hat tip and threads — their bones
 * never overlap the body's). She does not cast Iron's spells: her magic is the red threads ({@link IrinaFight}).
 */
public class IrinaEntity extends AbstractSpellCastingMob implements PohBoss, IAnimatedAttacker {
    private static final EntityDataAccessor<Boolean> FURY = SynchedEntityData.defineId(IrinaEntity.class, EntityDataSerializers.BOOLEAN);

    private final BossCore core = new BossCore(this, Irina.DEF);
    final IrinaFight fight = new IrinaFight(this);

    public IrinaEntity(EntityType<? extends AbstractSpellCastingMob> type, Level level) {
        super(type, level);
        BossConfig.PerBoss cfg = BossConfig.of(Irina.ID);
        xpReward = cfg != null ? BossConfig.get(cfg.xp) : 60;
    }

    public static AttributeSupplier.Builder attributes() {
        return Monster.createMonsterAttributes()
                .add(Attributes.MAX_HEALTH, 4400)
                .add(Attributes.ATTACK_DAMAGE, 22)
                .add(Attributes.ARMOR, 8)
                .add(Attributes.KNOCKBACK_RESISTANCE, 1.0)
                .add(Attributes.MOVEMENT_SPEED, 0.26)
                .add(Attributes.FOLLOW_RANGE, 48);
    }

    @Override
    public BossCore bossCore() {
        return core;
    }

    @Override
    protected void defineSynchedData() {
        super.defineSynchedData();
        entityData.define(FURY, false);
    }

    /** Phase 3: the cloth plays the storm all the time (client). */
    public boolean fury() {
        return entityData.get(FURY);
    }

    void setFury(boolean on) {
        entityData.set(FURY, on);
    }

    @Override
    protected void registerGoals() {
        goalSelector.addGoal(0, new FloatGoal(this));
        goalSelector.addGoal(8, new LookAtPlayerGoal(this, Player.class, 16));
        goalSelector.addGoal(9, new RandomLookAroundGoal(this));
        targetSelector.addGoal(1, new HurtByTargetGoal(this));
        targetSelector.addGoal(2, new NearestAttackableTargetGoal<>(this, Player.class, true));
    }

    // ---------------------------------------------------------------- spawn, loot, immunities

    @Override
    public SpawnGroupData finalizeSpawn(ServerLevelAccessor l, DifficultyInstance d, MobSpawnType why, @Nullable SpawnGroupData data, @Nullable CompoundTag tag) {
        SpawnGroupData out = super.finalizeSpawn(l, d, why, data, tag);
        setItemSlot(EquipmentSlot.MAINHAND, new ItemStack(Irina.STAFF.get()));
        setDropChance(EquipmentSlot.MAINHAND, 0);
        return out;
    }

    /** No loot (owner 20.11), only experience. */
    @Override
    protected void dropAllDeathLoot(DamageSource src) {
        dropExperience();
    }

    @Override
    public boolean removeWhenFarAway(double d) {
        return false;
    }

    @Override
    public boolean causeFallDamage(float dist, float mult, DamageSource src) {
        return false;
    }

    /**
     * Bosses.boss registers every boss fireImmune (all fire damage ignored); her threads burn (balance: fire_resist 0.85), so fire
     * spells and fire-aspect hits do reach her. World fire (lava, fire blocks, burning) is still ignored in {@link #hurt}.
     */
    @Override
    public boolean fireImmune() {
        return false;
    }

    @Override
    public boolean canChangeDimensions() {
        return false;
    }

    // ---------------------------------------------------------------- framework glue

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
        if (src.getEntity() == this) return false;
        // world hazards (balance 1.3): no suffocation, drowning, fall; no world fire (lava / fire blocks)
        if (src.is(DamageTypes.IN_WALL) || src.is(DamageTypes.DROWN) || src.is(DamageTypeTags.IS_FALL)
                || src.getEntity() == null && src.is(DamageTypeTags.IS_FIRE)) return false;
        float a = fight.incoming(src, amount);
        a = core.filterDamage(src, a);
        if (a <= 0) return false;
        boolean hurt = super.hurt(src, a);
        if (hurt) fight.onDamaged(src, a);
        return hurt;
    }

    @Override
    public void setBossAi(boolean on) {
        setNoAi(!on);
        if (!on) {
            getNavigation().stop();
            setDeltaMovement(Vec3.ZERO);
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
        if (core.phase() >= IrinaMath.FURY) setFury(true);
    }

    @Override
    public void remove(RemovalReason why) {
        if (level() instanceof ServerLevel sl && !isDeadOrDying()) fight.cleanup(sl);   // unloaded / discarded mid-fight
        super.remove(why);
    }

    // ---------------------------------------------------------------- intro (7 s, the plan «Появление»)

    @Override
    public void onBossIntro() {
        if (!(level() instanceof ServerLevel sl)) return;
        core.lock(IrinaMath.INTRO + 2, true, true);
        List<ServerPlayer> who = core.scene("irina.intro", IrinaMath.INTRO, BossNet.SCENE_LOCK_INPUT | BossNet.SCENE_BARS | BossNet.SCENE_NO_HUD,
                BossConfig.get(BossConfig.INTRO_RADIUS), position(), getYRot(), -1);
        Fx.play(sl, Fx.fx("irina_intro").caster(this).at(position()).yaw(getYRot()));
        core.play(new BossTimeline("scene:intro", IrinaMath.INTRO)
                .at(1, () -> {   // tick 1: the clients track her by now
                    serverTriggerAnimation("irina_spawn");
                    core.sound("irina.spawn", 4, 1);
                })
                .at(IrinaMath.INTRO_UNRAVEL, () -> core.sound("irina.snap", 3, 1))
                .at(IrinaMath.INTRO_POSE, () -> {
                    core.title(who, "irina", IrinaMath.INTRO_TITLE_HOLD, "ui.pohsmp_core.irina.subtitle");
                    core.music(true);
                })
                .at(IrinaMath.INTRO_FLOURISH, () -> core.sound("irina.staff", 3, 1))
                .then(core::startFight));
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

    // ---------------------------------------------------------------- death (5 s, «Смерть»: no corpse, she unravels and is gone)

    /** Boss sounds 21.11: her own hurt sound (sounds.json irina.hurt). */
    @Override
    protected net.minecraft.sounds.SoundEvent getHurtSound(DamageSource src) {
        return ru.pohsmp.core.boss.BossCore.sound("irina.hurt");
    }

    @Override
    public void die(DamageSource src) {
        super.die(src);
        if (!(level() instanceof ServerLevel sl) || !isDeadOrDying()) return;
        core.onDeath();
        fight.cleanup(sl);
        List<ServerPlayer> who = core.scene("irina.death", IrinaMath.DEATH, BossNet.SCENE_LOCK_INPUT | BossNet.SCENE_BARS | BossNet.SCENE_NO_HUD,
                BossConfig.get(BossConfig.INTRO_RADIUS), position(), getYRot(), -1);
        Fx.play(sl, Fx.fx("irina_death").caster(this).at(position()).yaw(getYRot()));
        core.sound("irina.death", 4, 1);
        core.play(new BossTimeline("scene:death", IrinaMath.DEATH)
                .at(IrinaMath.DEATH_UNRAVEL, () -> core.sound("irina.death_final", 4, 1))
                .then(() -> {
                    core.sceneStop(who, "irina.death");
                    remove(RemovalReason.KILLED);
                }));
    }

    /** Vanilla removes the dead after 20 ticks: she stays for her 5 s scene (removed by the scene's end; a safety net after). */
    @Override
    protected void tickDeath() {
        ++deathTime;
        if (!level().isClientSide && deathTime >= IrinaMath.DEATH + 40 && !isRemoved()) remove(RemovalReason.KILLED);
    }

    // ---------------------------------------------------------------- finisher (2.6 s; victim 1.6 before her)

    @Override
    public int finisherTicks() {
        return IrinaMath.FINISHER;
    }

    @Override
    public int finisherKillTick() {
        return IrinaMath.FINISHER_KILL;
    }

    /** No pose of her own for PlayerAnimator yet: the cult finisher's victim pose (pulled in, pierced — same sense, visual letter). */
    @Override
    public String finisherVictimAnim() {
        return "irons_spellbooks:pohsmp_cult_finisher_victim";
    }

    private Vec3 holdPoint;

    @Override
    public void onFinisherStart(ServerPlayer victim) {
        if (!(level() instanceof ServerLevel sl)) return;
        float yaw = (float) (Mth.atan2(victim.getZ() - getZ(), victim.getX() - getX()) * Mth.RAD_TO_DEG) - 90;
        setYRot(yaw);
        setYHeadRot(yaw);
        setYBodyRot(yaw);
        holdPoint = position().add(Vec3.directionFromRotation(0, yaw).scale(IrinaMath.FINISHER_DIST));
        serverTriggerAnimation("irina_finisher");
        core.sound("irina.finisher", 3, 1);
        Fx.play(sl, Fx.fx("irina_finisher").caster(this).at(position()).yaw(yaw).target(victim));
        core.play(new BossTimeline("finisher_cam", IrinaMath.FINISHER_CAM_FROM + 1)
                .at(IrinaMath.FINISHER_CAM_FROM, () -> core.sceneFor(victim, "irina.finisher", IrinaMath.FINISHER_CAM,
                        BossNet.SCENE_LOCK_INPUT | BossNet.SCENE_NO_HUD, holdPoint, yaw, victim.getId())));
    }

    @Override
    public Vec3 finisherVictimPos(ServerPlayer victim, int t, Vec3 from) {
        if (holdPoint == null) return from;
        Vec3 p = from.lerp(holdPoint, IrinaMath.finisherPull(t));
        return new Vec3(p.x, Mth.lerp(IrinaMath.finisherPull(t), from.y, holdPoint.y), p.z);
    }

    @Override
    public void onFinisherTick(ServerPlayer victim, int t) {
        if (t == IrinaMath.FINISHER_PIERCE) core.sound("irina.staff", 2, 0.8f);
        if (t == IrinaMath.FINISHER_WHISPER) subtitle("ui.pohsmp_core.irina.finisher_whisper", 40);   // only over her head, 2 s
    }

    /** A line over her head only (no chat): everyone within 32. */
    void subtitle(String key, int ticks) {
        for (ServerPlayer p : core.playersNear(32)) {
            BossNet.Msg m = new BossNet.Msg(BossNet.SUBTITLE).ints(getId(), ticks, Irina.COLOR, 0).str(key, "");
            m.f = 3.0f;
            BossNet.to(p, m);
        }
    }

    // ---------------------------------------------------------------- «Дезинтеграция: Реплика» (framework BossReplica)

    /** Her break: irina_replica_break (2.2 s, break 1.0, speak 1.25); «Какая милая вещица, но увы фальшивая». */
    @Override
    public BossReplica.Reaction replicaReaction() {
        return new BossReplica.Reaction("irina_replica_break", "irina_replica_break", "ui.pohsmp_core.irina.replica",
                IrinaMath.REPLICA_DELAY, IrinaMath.REPLICA_BREAK, IrinaMath.REPLICA_SPEAK, IrinaMath.REPLICA_ANIM, 3.0);
    }

    // ---------------------------------------------------------------- animations (two controllers; client)

    /** Body animations that loop until replaced (or until "-" is sent). */
    private static final Set<String> LOOPS = Set.of("irina_cast_long", "irina_puppet_hold");
    /** Body action → the cloth animation it brings (the rest of the actions: the storm while they play). */
    private static final Map<String, String> CLOTH = Map.of("irina_spawn", "irina_cloth_spawn", "irina_only_mine", "irina_cloth_cocoon",
            "irina_others_happiness", "irina_cloth_storm", "irina_replica_break", "irina_cloth_idle");
    private static final Set<String> CLOTH_ONCE = Set.of("irina_cloth_spawn", "irina_cloth_cocoon");

    private volatile String pendingBody;
    private volatile boolean newBody;
    private String bodyAction, bodyNow, clothNow;

    /** Client side, from Iron's animation packet (serverTriggerAnimation). "-" stops a looping action. */
    @Override
    public void playAnimation(String name) {
        pendingBody = name;
        newBody = true;
    }

    @Override
    public void registerControllers(AnimatableManager.ControllerRegistrar r) {
        super.registerControllers(r);   // Iron's three casting controllers (idle unless she casts an Iron's spell)
        r.add(new AnimationController<>(this, "irina_body", 3, this::bodyState));
        r.add(new AnimationController<>(this, "irina_cloth", 5, this::clothState));
    }

    private PlayState bodyState(AnimationState<IrinaEntity> s) {
        AnimationController<IrinaEntity> c = s.getController();
        if (isDeadOrDying()) {
            if (!"irina_death".equals(bodyNow)) {
                bodyNow = bodyAction = "irina_death";
                c.forceAnimationReset();
                c.setAnimation(RawAnimation.begin().thenPlayAndHold("irina_death"));
            }
            return PlayState.CONTINUE;
        }
        if (newBody) {
            newBody = false;
            String n = pendingBody;
            if (n == null || "-".equals(n)) bodyAction = null;
            else {
                bodyAction = bodyNow = n;
                c.forceAnimationReset();
                c.setAnimation(LOOPS.contains(n) ? RawAnimation.begin().thenLoop(n) : RawAnimation.begin().thenPlay(n));
                return PlayState.CONTINUE;
            }
        }
        if (bodyAction != null && !c.hasAnimationFinished()) return PlayState.CONTINUE;
        bodyAction = null;
        String base = s.isMoving() ? "irina_walk" : "irina_idle";
        if (!base.equals(bodyNow)) {
            bodyNow = base;
            c.setAnimation(RawAnimation.begin().thenLoop(base));
        }
        return PlayState.CONTINUE;
    }

    private PlayState clothState(AnimationState<IrinaEntity> s) {
        AnimationController<IrinaEntity> c = s.getController();
        String want;
        if (isDeadOrDying()) want = "irina_cloth_death";
        else if (bodyAction != null) want = CLOTH.getOrDefault(bodyAction, "irina_cloth_storm");
        else if (fury()) want = "irina_cloth_storm";
        else want = s.isMoving() ? "irina_cloth_walk" : "irina_cloth_idle";
        if (!want.equals(clothNow)) {
            clothNow = want;
            c.forceAnimationReset();
            if (want.equals("irina_cloth_death")) c.setAnimation(RawAnimation.begin().thenPlayAndHold(want));
            else if (CLOTH_ONCE.contains(want)) c.setAnimation(RawAnimation.begin().thenPlay(want));
            else c.setAnimation(RawAnimation.begin().thenLoop(want));
        }
        return PlayState.CONTINUE;
    }

    /** Iron's procedural arm / leg swing stays off on the client: her own walk and idle move the limbs (the head still follows the look). */
    @Override
    public boolean isAnimating() {
        return level().isClientSide || super.isAnimating();
    }

    @Override
    public boolean shouldAlwaysAnimateLegs() {
        return false;
    }

    @Override
    public boolean bobBodyWhileWalking() {
        return false;
    }
}
