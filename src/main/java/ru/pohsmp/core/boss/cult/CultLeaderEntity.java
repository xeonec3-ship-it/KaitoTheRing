package ru.pohsmp.core.boss.cult;

import io.redspace.ironsspellbooks.entity.mobs.abstract_spell_casting_mob.AbstractSpellCastingMob;
import io.redspace.ironsspellbooks.entity.mobs.wizards.fire_boss.FireBossEntity;
import java.util.List;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.util.Mth;
import net.minecraft.util.RandomSource;
import net.minecraft.world.DifficultyInstance;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.item.ItemStack;
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

/**
 * T26 «Tyros, First Flamebearer» / «Глава Культа Меллисто». Iron's FireBossEntity as it is (moves, scythe combos, fireballs, stance
 * breaks, the soul form as the fury of phase 3, the half-health attack), with: our model and scythe, our bar / music / scenes
 * (instead of tyros_bossbar and Iron's music), no keepers, no loot, the cult mechanics ({@link CultFight}), the finisher, the answer
 * to «Дезинтеграция: Реплика».
 */
public class CultLeaderEntity extends FireBossEntity implements PohBoss {
    private final BossCore core = new BossCore(this, CultLeader.DEF);
    final CultFight fight = new CultFight(this);

    public CultLeaderEntity(EntityType<? extends AbstractSpellCastingMob> type, Level level) {
        super(type, level);
        BossConfig.PerBoss cfg = BossConfig.of(CultLeader.ID);
        xpReward = cfg != null ? BossConfig.get(cfg.xp) : 60;
    }

    @Override
    public BossCore bossCore() {
        return core;
    }

    // ---------------------------------------------------------------- Iron's bits we replace

    /** Iron's events 1/4 start its music and its tyros bar on the client: ours instead (BossMusicClient, BossBarClient). */
    @Override
    public void handleClientEvent(byte id) {
        if (id == 4) return;
        super.handleClientEvent(id);
        if (id == 1) {
            io.redspace.ironsspellbooks.api.util.MusicManager.stopEvent(getUUID());
            io.redspace.ironsspellbooks.api.util.BossbarManager.stopTracking(getUUID());
        }
    }

    /** No keepers: the cult has its own servants (phase 3). */
    @Override
    public void spawnKnight(boolean left) {}

    @Override
    protected void populateDefaultEquipmentSlots(RandomSource r, DifficultyInstance d) {
        setItemSlot(EquipmentSlot.MAINHAND, new ItemStack(CultLeader.SCYTHE.get()));
        setDropChance(EquipmentSlot.MAINHAND, 0);
    }

    /** Iron's scales Tyros's health by players itself: dropped here, [bosses_common] does it (BossCore.begin). */
    @Override
    public net.minecraft.world.entity.SpawnGroupData finalizeSpawn(net.minecraft.world.level.ServerLevelAccessor l, DifficultyInstance d,
                                                                   net.minecraft.world.entity.MobSpawnType why,
                                                                   @javax.annotation.Nullable net.minecraft.world.entity.SpawnGroupData data,
                                                                   @javax.annotation.Nullable CompoundTag tag) {
        var out = super.finalizeSpawn(l, d, why, data, tag);
        var hp = getAttribute(net.minecraft.world.entity.ai.attributes.Attributes.MAX_HEALTH);
        if (hp != null) hp.removeModifiers();
        setHealth(getMaxHealth());
        return out;
    }

    /** No loot (owner 20.11), only a little experience. */
    @Override
    protected void dropAllDeathLoot(DamageSource src) {
        dropExperience();
    }

    @Override
    public boolean canTriggerOminous() {
        return false;
    }

    @Override
    public boolean isAlliedTo(Entity e) {
        return e instanceof FireCultistEntity || super.isAlliedTo(e);
    }

    @Override
    public boolean removeWhenFarAway(double d) {
        return false;
    }

    /** Client: ticks since the intro walk began (0..175), for the renderer (the model is not drawn for the first 30). */
    public float introAge(float pt) {
        return isSpawning() ? getSpawnWalkPercent(pt) * CultMath.INTRO : CultMath.INTRO;
    }

    // ---------------------------------------------------------------- framework glue

    /** The bar row: Iron's FireBossEntity already has a boss event with this entity's UUID (BossBarClient draws over it). */
    @Override
    public boolean coreBossEvent() {
        return false;
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
    public void tick() {
        super.tick();
        if (level() instanceof ServerLevel sl) {
            core.tick();
            if (isAlive()) {
                fight.tick(sl);
            }
        }
    }

    @Override
    public boolean hurt(DamageSource src, float amount) {
        if (level().isClientSide) return false;
        if (src.getEntity() instanceof FireCultistEntity || src.getEntity() == this) return false;
        float a = core.filterDamage(src, amount);
        if (a <= 0) return false;
        return super.hurt(src, a);
    }

    @Override
    public void setBossAi(boolean on) {
        setNoAi(!on);
        if (!on) {
            setTarget(null);
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
    }

    // ---------------------------------------------------------------- intro (8.75 s, the plan «Появление»)

    /** The spawn walk of Iron's (fire_boss_spawn, 175 ticks) starts on the first tick, not after its 40-tick delay. */
    @Override
    public void onBossPreSpawn() {
        try {
            java.lang.reflect.Field f = FireBossEntity.class.getDeclaredField("spawnTimer");
            f.setAccessible(true);
            f.setInt(this, CultMath.INTRO + 1);
        } catch (ReflectiveOperationException | RuntimeException e) {
            triggerSpawnAnim();   // Iron's own: 40 ticks of nothing first
        }
        setSpawnPos(position());
    }

    /** Melee attacks every melee_interval_min..max ticks (Tyros 10-30), x mult (the fury of phase 3: 0.75). */
    void meleeInterval(double mult) {
        if (attackGoal == null) return;
        int min = Math.max(1, (int) Math.round(BossConfig.get(BossConfig.CL_MELEE_MIN) * mult));
        attackGoal.setMeleeAttackInverval(min, Math.max(min, (int) Math.round(BossConfig.get(BossConfig.CL_MELEE_MAX) * mult)));
    }

    @Override
    public void onBossIntro() {
        if (!(level() instanceof ServerLevel sl)) return;
        BossConfig.PerBoss cfg = BossConfig.of(CultLeader.ID);
        var atk = getAttribute(net.minecraft.world.entity.ai.attributes.Attributes.ATTACK_DAMAGE);
        if (cfg != null && atk != null) atk.setBaseValue(BossConfig.get(cfg.attack) + BossConfig.get(BossConfig.CL_SCYTHE));   // + the scythe
        meleeInterval(1);
        core.lock(CultMath.INTRO + 2, true, true);
        double r = BossConfig.get(BossConfig.INTRO_RADIUS);
        List<ServerPlayer> who = core.scene("cult_leader.intro", CultMath.INTRO, BossNet.SCENE_LOCK_INPUT | BossNet.SCENE_BARS | BossNet.SCENE_NO_HUD,
                r, position(), getYRot(), -1);
        Fx.play(sl, Fx.fx("cult_leader_intro").caster(this).at(position()).yaw(getYRot()));
        core.play(new BossTimeline("scene:intro", CultMath.INTRO)
                .at(0, () -> core.sound("cult_leader.spawn", 4, 1))
                .at(22, () -> core.sound("cult_leader.firewall", 1, 1))
                .at(120, () -> core.sound("cult_leader.phase", 4, 1))
                .at(CultMath.INTRO_TITLE, () -> core.title(who, "cult_leader", CultMath.INTRO_TITLE_HOLD, "ui.pohsmp_core.cult_leader.subtitle"))
                .at(CultMath.INTRO_MUSIC, () -> core.music(true))
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

    // ---------------------------------------------------------------- death (3.5 s scene, «Смерть»)

    @Override
    public void die(DamageSource src) {
        super.die(src);
        if (!(level() instanceof ServerLevel sl) || !isDeadOrDying()) return;
        core.onDeath();
        fight.onDeath(sl);
        List<ServerPlayer> who = core.scene("cult_leader.death", CultMath.DEATH, BossNet.SCENE_LOCK_INPUT | BossNet.SCENE_BARS | BossNet.SCENE_NO_HUD,
                BossConfig.get(BossConfig.INTRO_RADIUS), position(), getYRot(), -1);
        Fx.play(sl, Fx.fx("cult_leader_death").caster(this).at(position()).yaw(getYRot()));
        core.play(new BossTimeline("scene:death", CultMath.DEATH)
                .at(CultMath.DEATH_FLAME_OUT, () -> {
                    core.lookFlag(BossNet.LOOK_FLAME_OUT, true);
                    fight.stopFires(sl);
                    core.sound("cult_leader.death_final", 4, 1);
                })
                .then(() -> core.sceneStop(who, "cult_leader.death")));
    }

    // ---------------------------------------------------------------- finisher (2.4 s; victim 3.0 before him, lifted 2.3)

    @Override
    public int finisherTicks() {
        return CultMath.FINISHER;
    }

    @Override
    public int finisherKillTick() {
        return CultMath.FINISHER_KILL;
    }

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
        holdPoint = position().add(Vec3.directionFromRotation(0, yaw).scale(CultMath.FINISHER_DIST));
        serverTriggerAnimation("cult_leader_finisher");
        core.sound("cult_leader.finisher", 3, 1);
        Fx.play(sl, Fx.fx("cult_leader_finisher").caster(this).at(position()).yaw(yaw).target(victim));
        core.play(new BossTimeline("finisher_cam", CultMath.FINISHER_CAM_FROM + 1)
                .at(CultMath.FINISHER_CAM_FROM, () -> core.sceneFor(victim, "cult_leader.finisher", CultMath.FINISHER_CAM,
                        BossNet.SCENE_LOCK_INPUT | BossNet.SCENE_NO_HUD, holdPoint, yaw, victim.getId())));
    }

    @Override
    public Vec3 finisherVictimPos(ServerPlayer victim, int t, Vec3 from) {
        if (holdPoint == null) return from;
        double[] h = CultMath.finisherHold(t);
        Vec3 p = from.lerp(holdPoint, h[0]);
        return new Vec3(p.x, Mth.lerp(h[0], from.y, holdPoint.y) + h[1], p.z);
    }

    // ---------------------------------------------------------------- T32 «Сломать блок» (framework BossGuardBreak)

    /** Not during Tyros's own swing / cast / broken stance (his melee is Tyros's AI: the heavy hit is attack_damage, the default). */
    @Override
    public boolean guardBreakFree() {
        return !core.locked() && !isAnimating() && !isCasting() && !isStanceBroken() && !isHalfHealthAttacking();
    }

    /** TEMP_GUARD_BREAK: cult_leader_guard_break comes after the scythe grip letter (planned hit 14, length 36). */
    @Override
    public ru.pohsmp.core.boss.BossGuardBreak.Timing guardBreakTiming() {
        return ru.pohsmp.core.boss.BossGuardBreak.Timing.TEMP;
    }

    @Override
    public void playGuardBreak(String animation) {
        serverTriggerAnimation(animation);
    }

    // ---------------------------------------------------------------- «Дезинтеграция: Реплика» (framework BossReplica)

    /** His break: cult_leader_replica_break (2.6 s, crush 0.9, speak 1.9), «Эта фальшивка на меня не сработает» on +4.2. */
    @Override
    public BossReplica.Reaction replicaReaction() {
        return new BossReplica.Reaction("cult_leader_replica_break", "cult_leader_replica_break", "ui.pohsmp_core.cult_leader.replica_taunt",
                CultMath.REPLICA_DELAY, CultMath.REPLICA_CRUSH, CultMath.REPLICA_SPEAK, CultMath.REPLICA_ANIM, 4.2);
    }
}
