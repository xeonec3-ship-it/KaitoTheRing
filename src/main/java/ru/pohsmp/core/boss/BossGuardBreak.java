package ru.pohsmp.core.boss;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.fx.Fx;
import ru.pohsmp.core.fx.FxLib;

/**
 * T32 «Сломать блок» (Guard Break), the same move for every cult boss (owner 21.11): when a fighter in reach holds the Epic Fight
 * guard longer than guard_break_hold_seconds, or has blocked guard_break_blocks of its hits in a row, the boss (not more often than
 * guard_break_cooldown) plays its guard_break animation (<id>_guard_break; Aris: animation.aris.guard_break) + fx <id>_guard_break (its flash on the weapon is the warning; without
 * the fx: sparks), and guard_break_warn_ticks before the blow the common crack boss.guard_break; on the hit everyone in its arc takes
 * the boss's strongest melee hit of the phase (pohsmp_core:boss_guard_break: no guard, no parry), and whoever was guarding gets the
 * guard broken (Epic Fight stamina 0, its neutralize, stunned guard_break_stun_ticks). Without Epic Fight nothing here ever starts.
 * Each boss only gives its animation, timings and damage ({@link PohBoss}). Not during scenes, finales, its own attacks, control
 * windows (paralysis, sleep, roots, held by «Целевая поза»), hidden; never at a target on a «столб».
 */
public final class BossGuardBreak {
    private BossGuardBreak() {}

    /** Reach of the blow (horizontal, from the boss) and its arc in front (degrees). */
    public static final double REACH = 4.5, ARC = 150;
    /** A parry with ef_parry_no_recoil = false: the boss staggers this long. */
    public static final int PARRY_STAGGER = 16;

    /**
     * Ticks of a boss's guard_break animation: the blow at hit, the whole length (docs/inbox/2026-11-21_mgr_guard_break_visuals.md:
     * warn 2, hit 14, length 36 — Irina, Aris, Ereb, Ereb Hand; Martin 40 with his shield push). TEMP: the Head of the Cult's stand-in
     * until his animation comes (after the scythe grip letter; planned 14 / 36).
     */
    public record Timing(int hit, int length) {
        public static final Timing STANDARD = new Timing(14, 36);
        public static final Timing TEMP = new Timing(14, 28);   // TEMP_GUARD_BREAK: cult_leader only
    }

    /** Per boss (owned by BossCore). */
    static final class State {
        final BossGuardBreakMath.Cooldown cooldown = new BossGuardBreakMath.Cooldown();
        BossTimeline running;
    }

    /** Every player's guard as the bosses see it (one guard per player, whichever boss looks). */
    private static final Map<UUID, BossGuardBreakMath.GuardWatch> WATCH = new HashMap<>();

    static BossGuardBreakMath.GuardWatch watch(ServerPlayer p) {
        return WATCH.computeIfAbsent(p.getUUID(), k -> new BossGuardBreakMath.GuardWatch());
    }

    // ---------------------------------------------------------------- from Epic Fight (BossEpicFight, server)

    /** A hit of this boss was blocked or parried by p's Epic Fight guard. */
    static void blocked(BossCore c, ServerPlayer p, boolean parried) {
        watch(p).blocked(p.level().getGameTime());
        if (parried && !BossConfig.get(BossConfig.EF_PARRY_NO_RECOIL) && !c.inFinale() && !c.inScene()) c.lock(PARRY_STAGGER, true, false);
    }

    /** A blockable hit of a boss landed on p (not blocked): the chain is broken. */
    static void landed(ServerPlayer p) {
        BossGuardBreakMath.GuardWatch w = WATCH.get(p.getUUID());
        if (w != null) w.landed();
    }

    // ---------------------------------------------------------------- tick (BossCore.tick: fight started)

    static void tick(BossCore c, PohBoss boss, State st) {
        if (!BossEpicFight.ON || !(c.mob.level() instanceof ServerLevel sl)) return;
        Mob mob = c.mob;
        long now = sl.getGameTime();
        if (mob.tickCount % 200 == 0) WATCH.values().removeIf(w -> now - w.seen() > 400);
        if (c.inFinale()) return;
        int hold = (int) Math.round(BossConfig.get(BossConfig.GB_HOLD_SECONDS) * 20), blocks = BossConfig.get(BossConfig.GB_BLOCKS);
        ServerPlayer pick = null;
        double best = Double.MAX_VALUE;
        for (ServerPlayer p : c.fighters()) {
            if (mob.tickCount % 20 == 0) BossEpicFight.listen(p);
            BossGuardBreakMath.GuardWatch w = watch(p);
            w.update(BossEpicFight.guarding(p), now);
            if (!w.wants(now, hold, blocks) || c.onPillar(p)) continue;
            double d = mob.distanceToSqr(p);
            if (d > (REACH - 0.5) * (REACH - 0.5) || Math.abs(p.getY() - mob.getY()) > 3) continue;
            if (p == mob.getTarget()) d = -1;   // its own target first
            if (d < best) {
                best = d;
                pick = p;
            }
        }
        if (pick == null || st.running != null && !st.running.done() || !st.cooldown.ready(now) || !free(c, boss)) return;
        start(c, boss, st, sl, pick);
    }

    /** Not in a scene / its own attack / a control window, not hidden. */
    private static boolean free(BossCore c, PohBoss boss) {
        Mob mob = c.mob;
        if (c.inScene() || !boss.guardBreakFree() || mob.isNoAi() || mob.isPassenger()) return false;
        if ((c.look() & BossNet.LOOK_HIDDEN) != 0) return false;
        if (mob.hasEffect(Reg.PARALYSIS.get()) || mob.hasEffect(Reg.NIGHTMARE.get()) || mob.hasEffect(Reg.SPENT.get())) return false;
        return !ru.pohsmp.core.spell.TargetPose.held(mob);
    }

    private static void start(BossCore c, PohBoss boss, State st, ServerLevel sl, ServerPlayer target) {
        Mob mob = c.mob;
        Timing tm = boss.guardBreakTiming();
        int[] t = BossGuardBreakMath.timing(tm.hit(), tm.length(), BossConfig.get(BossConfig.GB_WARN_TICKS));
        st.cooldown.use(sl.getGameTime(), BossConfig.get(BossConfig.GB_COOLDOWN) * 20);
        face(mob, target.position());
        mob.getNavigation().stop();
        c.lock(t[2], true, false);
        boss.playGuardBreak(boss.guardBreakAnimation());
        String fx = c.def.id + "_guard_break";
        if (FxLib.fx(fx) != null) Fx.play(sl, Fx.fx(fx).caster(mob).at(mob.position()).yaw(mob.getYRot()).target(target));   // tick 14: the crack at the target
        boss.onGuardBreakStart(target);
        st.running = c.play(new BossTimeline("guard_break", t[2])
                .at(t[0], () -> warn(c, sl, target))
                .at(t[1], () -> blow(c, boss, sl))
                .then(() -> st.running = null));
        PohCore.LOG.debug("[boss] {}: guard break at {}", c.def.id, target.getGameProfile().getName());
    }

    private static void face(Mob mob, Vec3 at) {
        double dx = at.x - mob.getX(), dz = at.z - mob.getZ();
        if (dx * dx + dz * dz < 1e-4) return;
        float yaw = (float) Math.toDegrees(Math.atan2(-dx, dz));
        mob.setYRot(yaw);
        mob.setYHeadRot(yaw);
        mob.setYBodyRot(yaw);
    }

    /** 0.6 s before the blow: the flash on the weapon / hand + the common crack. */
    private static void warn(BossCore c, ServerLevel sl, ServerPlayer target) {
        Mob mob = c.mob;
        if (target.isAlive()) face(mob, target.position());
        if (FxLib.fx(c.def.id + "_guard_break") == null) {   // the boss's fx has its own flash; until it comes: sparks at the weapon hand
            double a = Math.toRadians(mob.getYRot());
            double x = mob.getX() - Math.sin(a) * 0.7 - Math.cos(a) * 0.4, z = mob.getZ() + Math.cos(a) * 0.7 - Math.sin(a) * 0.4;
            sl.sendParticles(ParticleTypes.ELECTRIC_SPARK, x, mob.getY() + mob.getBbHeight() * 0.65, z, 24, 0.15, 0.25, 0.15, 0.25);
            sl.sendParticles(ParticleTypes.FLASH, x, mob.getY() + mob.getBbHeight() * 0.65, z, 1, 0, 0, 0, 0);
        }
        c.sound("boss.guard_break", 2.5f, 1);
    }

    /** The blow: everyone in its arc takes the heavy hit; a guard that was up is broken. */
    private static void blow(BossCore c, PohBoss boss, ServerLevel sl) {
        Mob mob = c.mob;
        float dmg = (float) boss.guardBreakDamage();
        int stun = BossConfig.get(BossConfig.GB_STUN_TICKS);
        long now = sl.getGameTime();
        for (ServerPlayer p : c.fighters()) {
            if (c.onPillar(p) || !BossGuardBreakMath.inBlow(p.getX() - mob.getX(), p.getY() - mob.getY(), p.getZ() - mob.getZ(), mob.getYRot(), REACH, ARC))
                continue;
            boolean guarded = BossEpicFight.guarding(p);
            p.invulnerableTime = 0;
            boolean landed = dmg > 0 && p.hurt(c.guardBreakSource(), dmg);
            if (guarded && (landed || dmg <= 0) && p.isAlive()) {
                BossEpicFight.breakGuard(p, stun);
                if (stun > 0) p.addEffect(new net.minecraft.world.effect.MobEffectInstance(Reg.PARALYSIS.get(), stun, 0, false, false, true));
                sl.playSound(null, p.getX(), p.getY(), p.getZ(), SoundEvents.SHIELD_BREAK, SoundSource.HOSTILE, 1.5f, 0.8f);
            }
            watch(p).reset(now);
        }
    }
}
