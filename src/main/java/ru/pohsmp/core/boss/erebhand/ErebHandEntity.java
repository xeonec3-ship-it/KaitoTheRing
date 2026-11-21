package ru.pohsmp.core.boss.erebhand;

import java.util.EnumSet;
import java.util.List;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.PathfinderMob;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.ai.goal.FloatGoal;
import net.minecraft.world.entity.ai.goal.Goal;
import net.minecraft.world.entity.ai.goal.LookAtPlayerGoal;
import net.minecraft.world.entity.ai.goal.target.HurtByTargetGoal;
import net.minecraft.world.entity.ai.goal.target.NearestAttackableTargetGoal;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.boss.BossConfig;
import ru.pohsmp.core.boss.BossCore;
import ru.pohsmp.core.boss.BossDef;
import ru.pohsmp.core.boss.BossNet;
import ru.pohsmp.core.boss.BossReplica;
import ru.pohsmp.core.boss.BossTimeline;
import ru.pohsmp.core.boss.PohBoss;
import ru.pohsmp.core.fx.Fx;

/**
 * T31 «Эреб, Длань Лжи»: the framework glue (BossCore: phases, bar, specials, scenes, the LEAVE finale = the false death, the Replica,
 * the finisher), the intro, the illusion immunity; the fight itself is {@link ErebHandFight}.
 */
public class ErebHandEntity extends ErebHandBody implements PohBoss {
    private final BossCore core = new BossCore(this, ErebHand.DEF);
    final ErebHandFight fight = new ErebHandFight(this);

    public ErebHandEntity(EntityType<? extends PathfinderMob> type, Level level) {
        super(type, level);
        xpReward = 0;   // the false death gives nothing (no loot, owner): he never really dies
        giveRapier();
    }

    public static AttributeSupplier.Builder attributes() {
        return PathfinderMob.createMobAttributes().add(Attributes.MAX_HEALTH, 5200).add(Attributes.ATTACK_DAMAGE, 23).add(Attributes.ARMOR, 12)
                .add(Attributes.MOVEMENT_SPEED, 0.28).add(Attributes.FOLLOW_RANGE, 48).add(Attributes.KNOCKBACK_RESISTANCE, 1.0)
                .add(Attributes.ATTACK_KNOCKBACK, 0.2);
    }

    @Override
    public BossCore bossCore() {
        return core;
    }

    // ---------------------------------------------------------------- AI: he walks at his target; ErebHandFight decides what he does

    @Override
    protected void registerGoals() {
        goalSelector.addGoal(0, new FloatGoal(this));
        goalSelector.addGoal(2, new Chase());
        goalSelector.addGoal(8, new LookAtPlayerGoal(this, Player.class, 24));
        targetSelector.addGoal(1, new HurtByTargetGoal(this, ErebHandReflection.class));
        targetSelector.addGoal(2, new NearestAttackableTargetGoal<>(this, Player.class, 10, true, false,
                e -> e instanceof Player p && !p.isCreative() && !p.isSpectator()));
    }

    /** Close in to rapier / hand reach. */
    private final class Chase extends Goal {
        Chase() {
            setFlags(EnumSet.of(Flag.MOVE, Flag.LOOK));
        }

        @Override
        public boolean canUse() {
            LivingEntity t = getTarget();
            return t != null && t.isAlive();
        }

        @Override
        public void tick() {
            LivingEntity t = getTarget();
            if (t == null) return;
            getLookControl().setLookAt(t, 30, 30);
            double d = distanceTo(t);
            boolean repath = tickCount % 5 == 0 || getNavigation().isDone();
            if (d > 2.6) {
                if (repath) getNavigation().moveTo(t, 1.0);
            } else getNavigation().stop();
        }

        @Override
        public boolean requiresUpdateEveryTick() {
            return true;
        }
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
            if (isAlive()) {
                fight.tick(sl);
                if (tickCount % 5 == 0 && ErebHandConfig.b(ErebHandConfig.ILLUSION_IMMUNE)) shakeOffIllusions();
            }
        }
    }

    /** Immune to illusions (as T30): no T22 marks stay on him. */
    private void shakeOffIllusions() {
        removeEffect(Reg.PHANTOM_PAIN.get());
        removeEffect(Reg.WAKING_NIGHTMARE.get());
        removeEffect(Reg.BUTTERFLY_DREAM.get());
    }

    @Override
    public boolean hurt(DamageSource src, float amount) {
        if (level().isClientSide) return false;
        if (src.getEntity() instanceof ErebHandBody) return false;
        if (src.is(Reg.ILLUSION_DAMAGE) && ErebHandConfig.b(ErebHandConfig.ILLUSION_IMMUNE)) return false;
        float a = core.filterDamage(src, amount);
        if (a <= 0) return false;
        a = fight.onHurt(src, a);
        if (a <= 0) return false;
        return super.hurt(src, a);
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
    public boolean isAlliedTo(Entity e) {
        return e instanceof ErebHandBody || e instanceof ErebHandGiant || super.isAlliedTo(e);
    }

    /** No loot (owner); he does not die anyway (the false death is a LEAVE finale). */
    @Override
    protected void dropAllDeathLoot(DamageSource src) {}

    /** Boss sounds 21.11: glass and gold (sounds.json ereb_hand.hurt). */
    @Override
    protected net.minecraft.sounds.SoundEvent getHurtSound(DamageSource src) {
        return ru.pohsmp.core.boss.BossCore.sound("ereb_hand.hurt");
    }

    @Override
    public void die(DamageSource src) {   // only /kill and the like: no scene
        super.die(src);
        if (level() instanceof ServerLevel sl && isDeadOrDying()) {
            core.onDeath();
            fight.cleanup(sl, true);
        }
    }

    @Override
    public void remove(RemovalReason why) {
        if (level() instanceof ServerLevel sl) fight.cleanup(sl, true);
        super.remove(why);
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
        setMaskOff(false);
        setHandOnly(false);
        setFalseArena(null);
        giveRapier();
        if (core.phase() >= 2) setMask(2);
    }

    // ---------------------------------------------------------------- intro «Появление» (5.5 s)

    @Override
    public void onBossIntro() {
        if (!(level() instanceof ServerLevel sl)) return;
        BossConfig.PerBoss cfg = BossConfig.of(ErebHand.ID);
        var atk = getAttribute(Attributes.ATTACK_DAMAGE);
        if (cfg != null && atk != null) atk.setBaseValue(BossConfig.get(cfg.attack) + ErebHandConfig.d(ErebHandConfig.RAPIER_DAMAGE));   // + the rapier
        dropRapier();   // the hand forms first; the rest of him (and the blade) at `form`
        core.lock(ErebHandMath.INTRO + 2, true, true);
        core.lookFlag(BossNet.LOOK_HIDDEN, true);
        List<ServerPlayer> who = core.scene("ereb_hand.intro", ErebHandMath.INTRO, BossNet.SCENE_LOCK_INPUT | BossNet.SCENE_BARS | BossNet.SCENE_NO_HUD,
                BossConfig.get(BossConfig.INTRO_RADIUS), position(), getYRot(), -1);
        serverTriggerAnimation("ereb_hand_spawn");
        Fx.play(sl, Fx.fx("ereb_hand_intro").caster(this).at(position()).yaw(getYRot()));
        core.play(new BossTimeline("scene:intro", ErebHandMath.INTRO)
                .at(0, () -> core.sound("ereb.spawn", 4, 0.9f))
                .at(ErebHandMath.INTRO_HAND, () -> {   // the glass and butterflies over his shoulder become the hand
                    setHandOnly(true);
                    core.lookFlag(BossNet.LOOK_HIDDEN, false);
                    core.sound("ereb_hand.grab", 2, 1.2f);
                })
                .at(ErebHandMath.INTRO_FORM, () -> {
                    setHandOnly(false);
                    giveRapier();
                    core.sound("ereb.appear", 4, 0.9f);
                })
                .at(ErebHandMath.INTRO_TITLE, () -> {
                    core.title(who, ErebHand.ID, ErebHandMath.INTRO_TITLE_HOLD, ErebHand.DEF.epithetKey());
                    core.music(true);
                    core.sound("ereb.thrust", 1.5f, 1.2f);   // the glint on the blade (salute)
                })
                .at(ErebHandMath.INTRO_SPEAK, () -> core.say("ui.pohsmp_core.ereb_hand.spawn", BossConfig.get(BossConfig.INTRO_RADIUS), 60, getBbHeight() + 1.2))
                .then(() -> {
                    core.startFight();
                    fight.begin();
                }));
    }

    // ---------------------------------------------------------------- phases, specials, the false death

    @Override
    public void onBossPhase(int from, int to) {
        fight.onPhase(from, to);
    }

    @Override
    public boolean onBossSpecial(BossDef.Special s) {
        return fight.special(s.id());
    }

    @Override
    public void onBossFinale() {
        fight.falseDeath();
    }

    // ---------------------------------------------------------------- finisher «%1$s раздавлен Дланью Лжи» (3.6 s)

    @Override
    public int finisherTicks() {
        return ErebHandMath.FINISHER;
    }

    @Override
    public int finisherKillTick() {
        return ErebHandMath.FIN_KILL;
    }

    @Override
    public String finisherVictimAnim() {
        return "irons_spellbooks:pohsmp_cult_finisher_victim";   // the shared pose
    }

    @Override
    public void onFinisherStart(ServerPlayer victim) {
        if (level() instanceof ServerLevel sl) fight.finisher(sl, victim);
    }

    /** The hand takes the victim by the torso and lifts it before him (the visual letter: feet (0.5 right, +1.45, 1.38 forward)). */
    @Override
    public Vec3 finisherVictimPos(ServerPlayer victim, int t, Vec3 from) {
        double[] o = ErebHandMath.local(getYRot(), ErebHandMath.FIN_RIGHT, ErebHandMath.FIN_FWD);
        Vec3 hold = new Vec3(getX() + o[0], getY() + ErebHandMath.FIN_UP, getZ() + o[1]);
        double k = ErebHandMath.finisherLift(t);
        return from.add(hold.subtract(from).scale(k));
    }

    @Override
    public void onFinisherTick(ServerPlayer victim, int t) {
        if (level() instanceof ServerLevel sl) fight.finisherTick(sl, victim, t);
    }

    // ---------------------------------------------------------------- «Дезинтеграция: Реплика»

    // ---------------------------------------------------------------- T32 «Сломать блок» (framework BossGuardBreak): ereb_hand_guard_break

    @Override
    public boolean guardBreakFree() {
        return fight.guardBreakFree();
    }

    @Override
    public double guardBreakDamage() {
        return fight.guardBreakDamage();
    }

    /** ereb_hand_replica_break 2.3 s: snap 0.55, break 0.95, speak 1.55; «Ложь во лжи - Становится правдой сама по себе». The fx is
     * T30's ereb_replica_break (the visual assistant: the same timing, no T31 one). */
    @Override
    public BossReplica.Reaction replicaReaction() {
        return new BossReplica.Reaction("ereb_hand_replica_break", "ereb_replica_break", "ui.pohsmp_core.ereb_hand.replica",
                ErebHandMath.REPLICA_DELAY, ErebHandMath.REPLICA_BREAK, ErebHandMath.REPLICA_SPEAK, ErebHandMath.REPLICA_ANIM, getBbHeight() + 1.2);
    }

    @Override
    public void onReplicaBreak(LivingEntity caster) {
        core.sound("ereb.cast", 2, 1.1f);
    }
}
