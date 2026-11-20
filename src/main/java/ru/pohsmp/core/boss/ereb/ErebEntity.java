package ru.pohsmp.core.boss.ereb;

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
 * T30 «Эреб, Первый Предатель». The framework glue (BossCore: phases, bar, specials, scenes, the LEAVE finale, the Replica), the intro,
 * the illusion immunity; the fight itself is {@link ErebFight}.
 */
public class ErebEntity extends ErebBody implements PohBoss {
    private final BossCore core = new BossCore(this, Ereb.DEF);
    final ErebFight fight = new ErebFight(this);

    public ErebEntity(EntityType<? extends PathfinderMob> type, Level level) {
        super(type, level);
        BossConfig.PerBoss cfg = BossConfig.of(Ereb.ID);
        xpReward = cfg != null ? BossConfig.get(cfg.xp) : 60;
        giveRapier();
    }

    public static AttributeSupplier.Builder attributes() {
        return PathfinderMob.createMobAttributes().add(Attributes.MAX_HEALTH, 4000).add(Attributes.ATTACK_DAMAGE, 18).add(Attributes.ARMOR, 10)
                .add(Attributes.MOVEMENT_SPEED, 0.28).add(Attributes.FOLLOW_RANGE, 48).add(Attributes.KNOCKBACK_RESISTANCE, 1.0)
                .add(Attributes.ATTACK_KNOCKBACK, 0.2);
    }

    @Override
    public BossCore bossCore() {
        return core;
    }

    // ---------------------------------------------------------------- AI: he walks at his target; ErebFight decides what he does

    @Override
    protected void registerGoals() {
        goalSelector.addGoal(0, new FloatGoal(this));
        goalSelector.addGoal(2, new Chase());
        goalSelector.addGoal(8, new LookAtPlayerGoal(this, Player.class, 24));
        targetSelector.addGoal(1, new HurtByTargetGoal(this, ErebReflection.class));
        targetSelector.addGoal(2, new NearestAttackableTargetGoal<>(this, Player.class, 10, true, false,
                e -> e instanceof Player p && !p.isCreative() && !p.isSpectator()));
    }

    /** Close in to rapier reach (a mage keeps a little more room while his shards are ready). */
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
            double want = fight.wantsRange() ? 6 : 2.2;
            boolean repath = tickCount % 5 == 0 || getNavigation().isDone();
            if (d > want + 0.6) {
                if (repath) getNavigation().moveTo(t, 1.0);
            } else if (d < want - 2.5 && fight.wantsRange()) {   // step back a little from someone in his face
                Vec3 away = position().subtract(t.position()).multiply(1, 0, 1).normalize().scale(3);
                if (repath) getNavigation().moveTo(getX() + away.x, getY(), getZ() + away.z, 1.0);
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
                if (tickCount % 5 == 0 && ErebConfig.b(ErebConfig.ILLUSION_IMMUNE)) shakeOffIllusions();
            }
        }
    }

    /** Immune to illusions (ТЗ, balance): no T22 / T25 marks stay on him. */
    private void shakeOffIllusions() {
        removeEffect(Reg.PHANTOM_PAIN.get());
        removeEffect(Reg.WAKING_NIGHTMARE.get());
        removeEffect(Reg.BUTTERFLY_DREAM.get());
    }

    static boolean illusionDamage(DamageSource src) {
        return src.is(Reg.ILLUSION_DAMAGE);
    }

    @Override
    public boolean hurt(DamageSource src, float amount) {
        if (level().isClientSide) return false;
        if (src.getEntity() instanceof ErebBody || src.getDirectEntity() instanceof ErebShard) return false;
        if (illusionDamage(src) && ErebConfig.b(ErebConfig.ILLUSION_IMMUNE)) return false;
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
        return e instanceof ErebBody || super.isAlliedTo(e);
    }

    /** No loot (owner 20.11); he does not die anyway (he leaves at 5%). */
    @Override
    protected void dropAllDeathLoot(DamageSource src) {}

    @Override
    public void die(DamageSource src) {   // only /kill and the like: no scene
        super.die(src);
        if (level() instanceof ServerLevel sl && isDeadOrDying()) {
            core.onDeath();
            fight.cleanup(sl);
        }
    }

    @Override
    public void remove(RemovalReason why) {
        if (level() instanceof ServerLevel sl) fight.cleanup(sl);
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
        setFace(null);
        setSmile(false);
    }

    // ---------------------------------------------------------------- intro «Появление» (5.0 s)

    @Override
    public void onBossIntro() {
        if (!(level() instanceof ServerLevel sl)) return;
        BossConfig.PerBoss cfg = BossConfig.of(Ereb.ID);
        var atk = getAttribute(Attributes.ATTACK_DAMAGE);
        if (cfg != null && atk != null) atk.setBaseValue(BossConfig.get(cfg.attack) + ErebConfig.d(ErebConfig.RAPIER_DAMAGE));   // + the rapier
        giveRapier();
        core.lock(ErebMath.INTRO + 2, true, true);
        core.lookFlag(BossNet.LOOK_HIDDEN, true);   // the swarm first: the model is not drawn till `form`
        List<ServerPlayer> who = core.scene("ereb.intro", ErebMath.INTRO, BossNet.SCENE_LOCK_INPUT | BossNet.SCENE_BARS | BossNet.SCENE_NO_HUD,
                BossConfig.get(BossConfig.INTRO_RADIUS), position(), getYRot(), -1);
        serverTriggerAnimation("ereb_spawn");
        Fx.play(sl, Fx.fx("ereb_intro").caster(this).at(position()).yaw(getYRot()));
        core.play(new BossTimeline("scene:intro", ErebMath.INTRO)
                .at(0, () -> core.sound("ereb.spawn", 4, 1))
                .at(ErebMath.INTRO_FORM, () -> {
                    core.lookFlag(BossNet.LOOK_HIDDEN, false);
                    core.sound("ereb.appear", 4, 1);
                })
                .at(ErebMath.INTRO_TITLE, () -> {
                    core.title(who, "ereb", ErebMath.INTRO_TITLE_HOLD, Ereb.DEF.epithetKey());
                    core.music(true);
                    core.sound("ereb.thrust", 1.5f, 1.3f);   // the glint on the blade (salute)
                })
                .then(() -> {
                    core.startFight();
                    fight.begin();
                }));
    }

    // ---------------------------------------------------------------- phases, specials, the finale

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
        fight.finale();
    }

    // ---------------------------------------------------------------- «Дезинтеграция: Реплика»

    /** ereb_replica_break 2.3 s: snap 0.55, break 0.95, speak 1.55; «Прекрасная копия, увы не идеальная» over his head. */
    @Override
    public BossReplica.Reaction replicaReaction() {
        return new BossReplica.Reaction("ereb_replica_break", "ereb_replica_break", "ui.pohsmp_core.ereb.replica",
                ErebMath.REPLICA_DELAY, ErebMath.REPLICA_BREAK, ErebMath.REPLICA_SPEAK, ErebMath.REPLICA_ANIM, getBbHeight() + 0.6);
    }

    @Override
    public void onReplicaBreak(LivingEntity caster) {
        fight.interrupt();
        core.sound("ereb.cast", 2, 1.2f);
    }
}
