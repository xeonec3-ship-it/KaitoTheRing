package ru.pohsmp.core.boss;

import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.phys.Vec3;

/**
 * A cult boss entity (T26-T30). The entity owns a {@link BossCore} (composition: the bosses stand on different Iron's / GeckoLib
 * bases) and calls it from its own tick / hurt / tracking methods — see «Каркас готов» in
 * docs/inbox/2026-11-20_cloudcode_bosses_core_T26.md. The framework calls the hooks below.
 */
public interface PohBoss {
    BossCore bossCore();

    default Mob bossMob() {
        return (Mob) this;
    }

    /** Before the entity is added to the world by /pohsmp boss (positioned, finalizeSpawn done): spawn data for the clients. */
    default void onBossPreSpawn() {}

    /** The intro: called once right after /pohsmp boss spawned it (arena = spawn point). Default: no scene, bar at once. */
    default void onBossIntro() {
        bossCore().startFight();
    }

    /** Health crossed a phase threshold (from < to). Default: nothing (the bar already flashed to the new sprite). */
    default void onBossPhase(int from, int to) {}

    /**
     * A special spell is due (its health fraction reached, once per fight). Return false if it cannot start now (another scene is
     * running...): it is asked again next tick.
     */
    default boolean onBossSpecial(BossDef.Special special) {
        return true;
    }

    /** SURRENDER / LEAVE: health reached def.finaleAt. The boss is already locked (invulnerable, no AI) and the bar is gone. */
    default void onBossFinale() {
        bossCore().endFinale();
    }

    /** Switch the boss's own AI off / on for scenes. Default: Mob.setNoAi. */
    default void setBossAi(boolean on) {
        bossMob().setNoAi(!on);
    }

    // ---------------------------------------------------------------- «Дезинтеграция: Реплика» (BossReplica, all five are immune)

    /**
     * How this boss breaks a Replica cast at it: animation + fx (<id>_replica_break), phrase ui.pohsmp_core.<id>.replica, timings.
     * One line to change: {@code return BossReplica.Reaction.of("irina", 3.0);} or a new Reaction(...). null = no reaction (the
     * Replica would work — do not, owner: none of the five).
     */
    default BossReplica.Reaction replicaReaction() {
        return BossReplica.Reaction.of(bossCore().def.id, bossMob().getBbHeight() + 0.6);
    }

    /** The break animation has just started (extra fx, sounds of the boss's own). */
    default void onReplicaBreak(net.minecraft.world.entity.LivingEntity caster) {}

    // ---------------------------------------------------------------- finisher (def.finisher)

    /** Finisher length in ticks (the victim dies at {@link #finisherKillTick()}). */
    default int finisherTicks() {
        return 48;
    }

    default int finisherKillTick() {
        return 44;
    }

    /** The victim's PlayerAnimator pose (irons_spellbooks:<name>), or null for the held pose of TargetPose. */
    default String finisherVictimAnim() {
        return null;
    }

    /** Called when a finisher starts: the boss's animation, fx, the victim's camera. */
    default void onFinisherStart(ServerPlayer victim) {}

    /** Where the victim is held at tick t of the finisher (from = where it was hit). Default: stays. */
    default Vec3 finisherVictimPos(ServerPlayer victim, int t, Vec3 from) {
        return from;
    }

    /** Called each finisher tick (sounds, fx on its events). */
    default void onFinisherTick(ServerPlayer victim, int t) {}
}
