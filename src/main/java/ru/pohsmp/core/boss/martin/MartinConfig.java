package ru.pohsmp.core.boss.martin;

import net.minecraftforge.common.ForgeConfigSpec;
import ru.pohsmp.core.boss.BossConfig;

/**
 * [martin] mechanics of pohsmp_core-bosses-server.toml (docs/specs/balance_bosses.md, section 5). Defined inside BossConfig's
 * «martin» section by one call there ({@link #define}); the body (hp, armour, speed...) stays in BossConfig.PerBoss.
 */
public final class MartinConfig {
    private MartinConfig() {}

    public static ForgeConfigSpec.DoubleValue SWORD_DAMAGE, OVERHEAD_DAMAGE, THRUST_DAMAGE, SHIELD_DASH_DAMAGE, SHIELD_DASH_PUSH, SWING_REACH,
            SOLDIER_HP, SOLDIER_ARMOR, SOLDIER_DAMAGE, SOLDIER_SPEED, FORMATION_MULT, FORMATION_RADIUS,
            BANNER_HP, BANNER_RADIUS, BANNER_DAMAGE_MULT, BANNER_SPEED_MULT, BANNER_TAKEN_MULT,
            P3_DAMAGE_MULT, P3_INTERVAL_MULT, HOLD_ARC, CAVALRY_DAMAGE, CAVALRY_PUSH,
            WALL_DAMAGE, WALL_PUSH, VOLLEY_DAMAGE, VOLLEY_RADIUS, DUEL_RADIUS, DUEL_PUSH, WARCRY_RADIUS, WARCRY_MULT;
    public static ForgeConfigSpec.IntValue MELEE_MIN, MELEE_MAX, SOLDIERS_BASE, SOLDIERS_MAX, SOLDIERS_REFILL, BANNER_REPLANT, HOLD_SECONDS,
            CAVALRY_LANES, WALL_COOLDOWN, VOLLEY_BASE, VOLLEY_MAX, VOLLEY_COOLDOWN, DUEL_SECONDS, DUEL_COOLDOWN, WARCRY_SECONDS,
            WARCRY_COOLDOWN;
    public static ForgeConfigSpec.BooleanValue FORMATION_P2;

    /** Called by BossConfig inside push("martin") … pop(). */
    public static void define(ForgeConfigSpec.Builder b) {
        SWORD_DAMAGE = b.comment("Added to attack_damage: the two-handed sword (swing = attack_damage + sword_damage)").defineInRange("sword_damage", 14.0, 0, 1000);
        OVERHEAD_DAMAGE = b.comment("«Рубящий сверху» (martin_overhead, ~4.5 blocks in front); x p3_damage_mult in phase 3").defineInRange("overhead_damage", 48.0, 0, 1000);
        THRUST_DAMAGE = b.comment("Thrust (martin_thrust) along 5 blocks in front").defineInRange("thrust_damage", 30.0, 0, 1000);
        SHIELD_DASH_DAMAGE = b.comment("Phase 3 shield dash").defineInRange("shield_dash_damage", 26.0, 0, 1000);
        SHIELD_DASH_PUSH = b.defineInRange("shield_dash_push", 2.0, 0, 10);
        SWING_REACH = b.comment("Reach of his swing (blocks from his centre)").defineInRange("swing_reach", 4.6, 1, 10);
        MELEE_MIN = b.comment("Ticks between his melee attacks").defineInRange("melee_interval_min", 20, 1, 400);
        MELEE_MAX = b.defineInRange("melee_interval_max", 40, 1, 400);
        SOLDIERS_BASE = b.comment("Phase 1 «Строй»: ghost soldiers = soldiers_base + N, at most soldiers_max; refilled every soldiers_refill_seconds")
                .defineInRange("soldiers_base", 2, 0, 16);
        SOLDIERS_MAX = b.defineInRange("soldiers_max", 8, 0, 32);
        SOLDIERS_REFILL = b.defineInRange("soldiers_refill_seconds", 30, 5, 3600);
        SOLDIER_HP = b.comment("Soldier health (x the boss's player multiplier), armour, hit, speed").defineInRange("soldier_hp", 45.0, 1, 10000);
        SOLDIER_ARMOR = b.defineInRange("soldier_armor", 10.0, 0, 30);
        SOLDIER_DAMAGE = b.defineInRange("soldier_damage", 12.0, 0, 1000);
        SOLDIER_SPEED = b.defineInRange("soldier_speed", 0.27, 0, 2);
        FORMATION_MULT = b.comment("Damage to Martin when a soldier within formation_radius stands on the line from the attacker").defineInRange("formation_damage_mult", 0.5, 0, 1);
        FORMATION_RADIUS = b.defineInRange("formation_radius", 4.2, 0, 16);
        FORMATION_P2 = b.comment("The line also covers him in phase 2 (while soldiers live)").define("formation_in_phase2", true);
        BANNER_HP = b.comment("Phase 2 «Знамя»: banner health (x player multiplier), aura radius, soldiers in it: damage x, speed x, taken x")
                .defineInRange("banner_hp", 120.0, 1, 100000);
        BANNER_RADIUS = b.defineInRange("banner_radius", 8.0, 1, 32);
        BANNER_DAMAGE_MULT = b.defineInRange("banner_damage_mult", 1.3, 0, 10);
        BANNER_SPEED_MULT = b.defineInRange("banner_speed_mult", 1.2, 0, 10);
        BANNER_TAKEN_MULT = b.defineInRange("banner_soldier_taken_mult", 0.75, 0, 10);
        BANNER_REPLANT = b.comment("A cut banner is planted again after this (phase 2 only; 0 = never)").defineInRange("banner_replant_seconds", 45, 0, 3600);
        P3_DAMAGE_MULT = b.comment("Phase 3 «Последний полководец»: his damage x, melee interval x").defineInRange("p3_damage_mult", 1.25, 0, 10);
        P3_INTERVAL_MULT = b.defineInRange("p3_interval_mult", 0.75, 0.1, 10);
        HOLD_SECONDS = b.comment("«Приказ стоять насмерть» (special at 50%): seconds, the front arc (degrees) where he and the soldiers take no damage")
                .defineInRange("hold_seconds", 10, 1, 120);
        HOLD_ARC = b.defineInRange("hold_arc", 100.0, 0, 360);
        CAVALRY_LANES = b.comment("«Атака конницы» (special at 25%): lanes = cavalry_lanes_base + (N>=4) + (N>=6); a rider's hit, push")
                .defineInRange("cavalry_lanes_base", 3, 1, 12);
        CAVALRY_DAMAGE = b.defineInRange("cavalry_damage", 45.0, 0, 1000);
        CAVALRY_PUSH = b.defineInRange("cavalry_push", 2.0, 0, 10);
        WALL_DAMAGE = b.comment("«Стена щитов»: hit and push of the moving wall (once per player), cooldown").defineInRange("shield_wall_damage", 8.0, 0, 1000);
        WALL_PUSH = b.defineInRange("shield_wall_push", 1.2, 0, 10);
        WALL_COOLDOWN = b.defineInRange("shield_wall_cooldown", 30, 1, 3600);
        VOLLEY_BASE = b.comment("«Залп лучников»: marks = volley_marks_base + N (at most max), damage in volley_radius, cooldown").defineInRange("volley_marks_base", 1, 0, 16);
        VOLLEY_MAX = b.defineInRange("volley_marks_max", 6, 1, 32);
        VOLLEY_DAMAGE = b.defineInRange("volley_damage", 30.0, 0, 1000);
        VOLLEY_RADIUS = b.defineInRange("volley_radius", 1.5, 0.2, 8);
        VOLLEY_COOLDOWN = b.defineInRange("volley_cooldown", 16, 1, 3600);
        DUEL_SECONDS = b.comment("«Вызов на дуэль»: seconds, ring radius, push of the others, cooldown").defineInRange("duel_seconds", 6, 1, 120);
        DUEL_RADIUS = b.defineInRange("duel_radius", 6.0, 1, 32);
        DUEL_PUSH = b.defineInRange("duel_push", 1.5, 0, 10);
        DUEL_COOLDOWN = b.defineInRange("duel_cooldown", 40, 1, 3600);
        WARCRY_RADIUS = b.comment("«Боевой клич»: casts in this radius are broken (no mana back); soldiers' damage x for warcry_buff_seconds")
                .defineInRange("warcry_radius", 12.0, 1, 64);
        WARCRY_MULT = b.defineInRange("warcry_buff_mult", 1.25, 0, 10);
        WARCRY_SECONDS = b.defineInRange("warcry_buff_seconds", 6, 0, 120);
        WARCRY_COOLDOWN = b.defineInRange("warcry_cooldown", 25, 1, 3600);
    }

    static double d(ForgeConfigSpec.DoubleValue v) {
        return BossConfig.get(v);
    }

    static int i(ForgeConfigSpec.IntValue v) {
        return BossConfig.get(v);
    }

    static boolean b(ForgeConfigSpec.BooleanValue v) {
        return BossConfig.get(v);
    }
}
