package ru.pohsmp.core.boss.aris;

import net.minecraftforge.common.ForgeConfigSpec;
import ru.pohsmp.core.boss.BossConfig;

/**
 * Mechanics keys of [aris] in pohsmp_core-bosses-server.toml (defaults: docs/specs/balance_bosses.md §4). Defined inside the [aris]
 * section by one call from BossConfig ({@code ArisConfig.define(b);} after the body), so the shared file keeps a single line of T28.
 */
public final class ArisConfig {
    private ArisConfig() {}

    public static ForgeConfigSpec.DoubleValue HAMMER, MYTHIC_DAMAGE, MYTHIC_INTERVAL, SLAM_DAMAGE, WAVE_DAMAGE, ANVIL_RISE_DAMAGE,
            FLOOR_SHARE, BLADE_HP, BLADE_DAMAGE, REFORGE_MULT, LAST_CENTER, LAST_EDGE, LAST_RADIUS, LAST_PUSH,
            BILLET_DAMAGE, BILLET_RADIUS, QUENCH_MULT, QUENCH_RADIUS, QUENCH_FOG, BELLOWS_DAMAGE, BELLOWS_PUSH;
    public static ForgeConfigSpec.IntValue MELEE_MIN, MELEE_MAX, SLAM_CD, WAVE_CD, ANVILS, ANVILS_BIG, ANVIL_SECONDS, ANVILS_CD, ISLANDS_MIN,
            ISLANDS_MAX, FORGE_SECONDS, BLADES_PER, BLADES_MAX, BLADE_ATTACK, BLADES_CD, REFORGE_SECONDS, REFORGE_TARGETS_BIG, REFORGE_CD,
            BILLET_DELAY, BILLET_CD, CHAINS_SECONDS, CHAINS_HITS, CHAINS_CD, QUENCH_SECONDS, QUENCH_CD, BELLOWS_BURN, BELLOWS_CD;

    /** Called by BossConfig inside push("aris") … pop(). */
    public static void define(ForgeConfigSpec.Builder b) {
        HAMMER = b.comment("Added to attack_damage (her hammer): a swing = 18 + 12 = 30").defineInRange("hammer_damage", 12.0, 0, 1000);
        MELEE_MIN = b.comment("Ticks between hammer swings").defineInRange("melee_interval_min", 14, 1, 200);
        MELEE_MAX = b.defineInRange("melee_interval_max", 30, 1, 200);
        SLAM_DAMAGE = b.comment("Phase 1 «Ковка»: the molten ring r8 (jump over it)").defineInRange("slam_damage", 26.0, 0, 1000);
        SLAM_CD = b.defineInRange("slam_cooldown", 8, 1, 600);
        WAVE_DAMAGE = b.comment("…the fan of molten metal (5 crests 2..10 blocks ahead, width 3), once per player").defineInRange("metal_wave_damage", 22.0, 0, 1000);
        WAVE_CD = b.defineInRange("metal_wave_cooldown", 10, 1, 600);
        ANVILS = b.comment("…anvils rising from the ground (obstacles, cover from «Мехи» and billets): count, with 4+ players").defineInRange("anvils_count", 2, 0, 8);
        ANVILS_BIG = b.defineInRange("anvils_count_big", 3, 0, 8);
        ANVIL_SECONDS = b.defineInRange("anvil_seconds", 8, 1, 120);
        ANVIL_RISE_DAMAGE = b.comment("An anvil grown under a player: this + a toss").defineInRange("anvil_rise_damage", 15.0, 0, 1000);
        ANVILS_CD = b.defineInRange("anvils_cooldown", 20, 1, 600);
        ISLANDS_MIN = b.comment("«Горн» (special at 75%, once): islands; the floor burns this share of max health per second").defineInRange("forge_islands_min", 4, 1, 12);
        ISLANDS_MAX = b.defineInRange("forge_islands_max", 6, 1, 12);
        FLOOR_SHARE = b.defineInRange("forge_floor_share_per_second", 0.06, 0, 1);
        FORGE_SECONDS = b.comment("(the fx burns 10 s; less here stops the damage earlier)").defineInRange("forge_seconds", 10, 1, 10);
        BLADES_PER = b.comment("Phase 2 «Оружейная»: blades per forging, alive at most, health (x players), hit, attack period, forging cooldown")
                .defineInRange("blades_per_forge", 3, 1, 3);
        BLADES_MAX = b.defineInRange("blades_max", 6, 1, 12);
        BLADE_HP = b.defineInRange("blade_hp", 24.0, 1, 10000);
        BLADE_DAMAGE = b.defineInRange("blade_damage", 14.0, 0, 1000);
        BLADE_ATTACK = b.defineInRange("blade_attack_ticks", 60, 10, 1200);
        BLADES_CD = b.defineInRange("blades_cooldown", 15, 1, 600);
        MYTHIC_DAMAGE = b.comment("Phase 3 «Мифический сплав»: her damage x, swing interval x").defineInRange("mythic_damage_mult", 1.3, 0, 10);
        MYTHIC_INTERVAL = b.defineInRange("mythic_interval_mult", 0.85, 0.1, 10);
        REFORGE_SECONDS = b.comment("…«перековка»: weapon damage (melee, arrows) of the target x reforge_weapon_mult; 2 targets with 5+ players")
                .defineInRange("reforge_seconds", 10, 1, 120);
        REFORGE_MULT = b.defineInRange("reforge_weapon_mult", 0.6, 0, 1);
        REFORGE_TARGETS_BIG = b.defineInRange("reforge_targets_big", 2, 1, 8);
        REFORGE_CD = b.defineInRange("reforge_cooldown", 20, 1, 600);
        LAST_CENTER = b.comment("«Последний удар молота» (special at 10%, once): damage centre → edge in radius, the push of the wave r30")
                .defineInRange("last_blow_center", 75.0, 0, 1000);
        LAST_EDGE = b.defineInRange("last_blow_edge", 30.0, 0, 1000);
        LAST_RADIUS = b.defineInRange("last_blow_radius", 14.0, 1, 64);
        LAST_PUSH = b.defineInRange("last_blow_wave_push", 1.5, 0, 10);
        BILLET_DAMAGE = b.comment("«Раскалённая заготовка»").defineInRange("billet_damage", 40.0, 0, 1000);
        BILLET_RADIUS = b.defineInRange("billet_radius", 3.0, 0.5, 16);
        BILLET_DELAY = b.comment("(the fx pulses 3 s)").defineInRange("billet_delay_seconds", 3, 1, 3);
        BILLET_CD = b.defineInRange("billet_cooldown", 14, 1, 600);
        CHAINS_SECONDS = b.comment("«Цепи кузни»: seconds, or this many hits of allies on the chained one").defineInRange("chains_seconds", 4, 1, 60);
        CHAINS_HITS = b.defineInRange("chains_hits", 3, 1, 20);
        CHAINS_CD = b.defineInRange("chains_cooldown", 18, 1, 600);
        QUENCH_SECONDS = b.comment("«Закалка»: damage to her x mult while she is in the steam (radius); fog distance of players in it")
                .defineInRange("quench_seconds", 5, 1, 5);
        QUENCH_MULT = b.defineInRange("quench_damage_mult", 0.6, 0, 1);
        QUENCH_RADIUS = b.defineInRange("quench_radius", 5.0, 1, 32);
        QUENCH_FOG = b.defineInRange("quench_fog_distance", 3.0, 1, 32);
        QUENCH_CD = b.defineInRange("quench_cooldown", 30, 1, 600);
        BELLOWS_DAMAGE = b.comment("«Мехи»: the cone 60°×8 (warning 0.8 s)").defineInRange("bellows_damage", 28.0, 0, 1000);
        BELLOWS_PUSH = b.defineInRange("bellows_push", 1.5, 0, 10);
        BELLOWS_BURN = b.defineInRange("bellows_burn_seconds", 5, 0, 60);
        BELLOWS_CD = b.defineInRange("bellows_cooldown", 10, 1, 600);
    }

    static double get(ForgeConfigSpec.DoubleValue v) {
        return BossConfig.get(v);
    }

    static int get(ForgeConfigSpec.IntValue v) {
        return BossConfig.get(v);
    }
}
