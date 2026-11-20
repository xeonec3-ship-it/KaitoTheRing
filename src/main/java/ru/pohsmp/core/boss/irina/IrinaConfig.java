package ru.pohsmp.core.boss.irina;

import net.minecraftforge.common.ForgeConfigSpec;
import ru.pohsmp.core.boss.BossConfig;

/**
 * The mechanics keys of [irina] in pohsmp_core-bosses-server.toml (docs/specs/balance_bosses.md, section 3). Defined from
 * BossConfig's [irina] section by one line ({@code IrinaConfig.define(b);}) so the shared config file is touched only there.
 */
public final class IrinaConfig {
    private IrinaConfig() {}

    public static ForgeConfigSpec.DoubleValue HUNT_SPEED_MULT, THREAD_BOLT_DAMAGE, MARK_DAMAGE_MULT, BOND_SHARE, BOND_BREAK_DISTANCE, BOND_SNAP_SHARE,
            HAPPINESS_RADIUS, WHIP_DAMAGE, COCOON_HP_PER_ALLY, COCOON_HP_MIN, COCOON_CRUSH_SHARE, GAZE_ANGLE, KNOT_DAMAGE, PUPPET_WALK_MULT,
            PUPPET_BREAK_SHARE, MELEE_REACH;
    public static ForgeConfigSpec.IntValue THREAD_BOLT_INTERVAL, MARK_REASSIGN, BOND_RESHUFFLE, BOND_REFORM, STOLEN_SECONDS, STOLEN_MAX_AMP,
            STOLEN_RESISTANCE_MAX, STEAL_INTERVAL, STEAL_TARGETS, STEAL_PER_TARGET, STEAL_SECONDS, WHIP_COOLDOWN, WHIP_SLOW_SECONDS, COCOON_SECONDS,
            GAZE_SECONDS, GAZE_SLOW_SECONDS, GAZE_SLOW_AMP, GAZE_COOLDOWN, KNOTS_BASE, KNOTS_MAX, KNOT_LIFE, KNOT_SNARE, KNOTS_COOLDOWN,
            SWAP_COOLDOWN, SWAP_NAUSEA, PUPPET_SECONDS, PUPPET_COOLDOWN, MELEE_INTERVAL;

    /** Called inside the pushed [irina] section of BossConfig's builder. */
    public static void define(ForgeConfigSpec.Builder b) {
        HUNT_SPEED_MULT = b.comment("Speed x while she hunts the marked one (phase 1)").defineInRange("hunt_speed_mult", 1.2, 0.1, 10);
        MELEE_REACH = b.comment("Staff hook reach (blocks)").defineInRange("melee_reach", 3.2, 1, 10);
        MELEE_INTERVAL = b.comment("Ticks between staff hooks").defineInRange("melee_interval_ticks", 30, 5, 400);
        THREAD_BOLT_DAMAGE = b.comment("«Нитяной укол» (base ranged attack: a knot under the target, stabs 0.8 s later)").defineInRange("thread_bolt_damage", 20.0, 0, 1000);
        THREAD_BOLT_INTERVAL = b.defineInRange("thread_bolt_interval_ticks", 50, 5, 2000);
        MARK_REASSIGN = b.comment("Phase 1 «Зависть»: the mark goes to the top damage (30 s window) every N s").defineInRange("mark_reassign_seconds", 15, 1, 600);
        MARK_DAMAGE_MULT = b.comment("...damage of everyone else to her while the mark is on").defineInRange("mark_damage_mult", 0.5, 0, 10);
        BOND_RESHUFFLE = b.comment("Phase 2 «Красные нити»: pairs reshuffled every N s").defineInRange("bond_reshuffle_seconds", 30, 1, 600);
        BOND_SHARE = b.comment("...share of a bonded player's damage that goes to the partner").defineInRange("bond_share", 0.5, 0, 1);
        BOND_BREAK_DISTANCE = b.comment("...farther than this the thread snaps").defineInRange("bond_break_distance", 12.0, 2, 64);
        BOND_SNAP_SHARE = b.comment("...snap: this share of max health to both (through armour)").defineInRange("bond_snap_share", 0.30, 0, 1);
        BOND_REFORM = b.comment("...a new thread after a snap").defineInRange("bond_reform_seconds", 10, 0, 600);
        HAPPINESS_RADIUS = b.comment("«Чужое счастье» (66%): radius; stolen effects on her for N s, levels capped").defineInRange("happiness_radius", 24.0, 2, 128);
        STOLEN_SECONDS = b.defineInRange("stolen_seconds", 30, 1, 600);
        STOLEN_MAX_AMP = b.comment("0 = level I").defineInRange("stolen_max_amplifier", 1, 0, 10);
        STOLEN_RESISTANCE_MAX = b.defineInRange("stolen_resistance_max", 0, 0, 10);
        STEAL_INTERVAL = b.comment("Phase 3: steal every N s from the nearest players, effects on her for steal_seconds").defineInRange("steal_interval", 20, 1, 600);
        STEAL_TARGETS = b.defineInRange("steal_targets", 3, 1, 16);
        STEAL_PER_TARGET = b.defineInRange("steal_per_target", 2, 1, 16);
        STEAL_SECONDS = b.defineInRange("steal_seconds", 20, 1, 600);
        WHIP_DAMAGE = b.comment("Phase 3 whip of threads (ring 1.5-7 round her, 0.8 s warning)").defineInRange("whip_damage", 30.0, 0, 1000);
        WHIP_COOLDOWN = b.defineInRange("whip_cooldown", 6, 1, 600);
        WHIP_SLOW_SECONDS = b.defineInRange("whip_slow_seconds", 2, 0, 60);
        COCOON_SECONDS = b.comment("«Только мой» (15%): cocoon time (the scene is built for 4)").defineInRange("cocoon_seconds", 4, 1, 30);
        COCOON_HP_PER_ALLY = b.defineInRange("cocoon_hp_per_ally", 40.0, 0, 10000);
        COCOON_HP_MIN = b.defineInRange("cocoon_hp_min", 60.0, 1, 10000);
        COCOON_CRUSH_SHARE = b.comment("...not broken: this share of the victim's max health (through armour)").defineInRange("cocoon_crush_share", 0.6, 0, 1);
        GAZE_SECONDS = b.comment("«Ревнивый взгляд»: looked at her longer than this inside the cone → slowed").defineInRange("gaze_seconds", 2, 1, 60);
        GAZE_ANGLE = b.defineInRange("gaze_angle", 25.0, 1, 90);
        GAZE_SLOW_SECONDS = b.defineInRange("gaze_slow_seconds", 4, 1, 60);
        GAZE_SLOW_AMP = b.comment("0 = level I").defineInRange("gaze_slow_amplifier", 1, 0, 10);
        GAZE_COOLDOWN = b.defineInRange("gaze_cooldown", 15, 1, 600);
        KNOTS_BASE = b.comment("«Узлы»: base + ceil(N/2), at most knots_max; live N s; snare N s").defineInRange("knots_base", 3, 1, 32);
        KNOTS_MAX = b.defineInRange("knots_max", 6, 1, 32);
        KNOT_LIFE = b.defineInRange("knot_life_seconds", 20, 1, 600);
        KNOT_SNARE = b.defineInRange("knot_snare_seconds", 2, 1, 60);
        KNOT_DAMAGE = b.defineInRange("knot_damage", 10.0, 0, 1000);
        KNOTS_COOLDOWN = b.defineInRange("knots_cooldown", 22, 1, 600);
        SWAP_COOLDOWN = b.comment("«Подмена любимого»").defineInRange("swap_cooldown", 25, 1, 600);
        SWAP_NAUSEA = b.defineInRange("swap_nausea_seconds", 2, 0, 60);
        PUPPET_SECONDS = b.comment("«Марионетка»: walks to her at walk_mult; broken by damage of the others >= share of her max health").defineInRange("puppet_seconds", 3, 1, 60);
        PUPPET_WALK_MULT = b.defineInRange("puppet_walk_mult", 0.6, 0, 5);
        PUPPET_BREAK_SHARE = b.defineInRange("puppet_break_share", 0.02, 0, 1);
        PUPPET_COOLDOWN = b.defineInRange("puppet_cooldown", 20, 1, 600);
    }

    static double get(ForgeConfigSpec.DoubleValue v) {
        return BossConfig.get(v);
    }

    static int get(ForgeConfigSpec.IntValue v) {
        return BossConfig.get(v);
    }
}
