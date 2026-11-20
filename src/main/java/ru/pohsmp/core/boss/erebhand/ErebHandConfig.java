package ru.pohsmp.core.boss.erebhand;

import net.minecraftforge.common.ForgeConfigSpec;

/**
 * T31 «Эреб, Длань Лжи»: the mechanics keys of [ereb_hand] in pohsmp_core-bosses-server.toml (docs/specs/balance_bosses.md, section
 * 6а — a DRAFT: the numbers of [ereb] ×≈1.3). The body (hp, armour, speed, attack, resists, arena) is the framework's own PerBoss; these
 * keys are defined right after it, inside the same section, by one line in BossConfig:
 * {@code ru.pohsmp.core.boss.erebhand.ErebHandConfig.define(b);}.
 */
public final class ErebHandConfig {
    private ErebHandConfig() {}

    public static ForgeConfigSpec.DoubleValue RAPIER_DAMAGE, SLAM_DAMAGE, SLAM_RADIUS, DOUBLE_FIRE_DAMAGE, SQUEEZE_DAMAGE, GRAB_BREAK_DAMAGE,
            MIRROR_WALLS_RADIUS, FIREWALL_SHARE, FIREWALL_PUSH, HAND_OF_LIES_DAMAGE, MASK_FAIL_SHARE, DREAM_SLAM_DAMAGE, DREAM_SLAM_RADIUS,
            FLAME_RADIUS, FLAME_DAMAGE, GRIP_DAMAGE, GRIP_RANGE, GRIP_ANGLE, GRIP_PULL, OATH_SHARE, OATH_MAX_HIT, THOUSAND_DAMAGE,
            CHANGELING_DAMAGE, RETREAT_DAMAGE, TRAITOR_DAMAGE, TRAITOR_BURST_DAMAGE, TRAITOR_BURST_RADIUS, SWARM_DAMAGE, DAWN_NEAR_RADIUS,
            DAWN_NEAR_SHARE, DAWN_FAR_SHARE;
    public static ForgeConfigSpec.IntValue MELEE_MIN, MELEE_MAX, SLAM_COOLDOWN, DOUBLES_COUNT, DOUBLES_REAL, DOUBLES_SECONDS, DOUBLES_INTERVAL,
            DOUBLE_HITS, GRAB_SECONDS, GRAB_COOLDOWN, MIRROR_WALLS_COUNT, MIRROR_WALLS_SECONDS, MIRROR_WALLS_INTERVAL, FIREWALL_BURN,
            HAND_OF_LIES_SECONDS, MASK_SECONDS, DREAM_SLAM_INTERVAL, DREAM_MAX_MINUTES, FLAME_CIRCLES, FLAME_DECOYS, FLAME_SECONDS, FLAME_COOLDOWN,
            GRIP_COOLDOWN, OATH_SECONDS, OATH_COOLDOWN, THOUSAND_MIRRORS, THOUSAND_REAL, THOUSAND_COOLDOWN, CHANGELING_COOLDOWN, RETREAT_COOLDOWN,
            TRAITOR_SECONDS, TRAITOR_HITS_ORIGINAL, TRAITOR_HITS_OTHERS, TRAITOR_COOLDOWN, SWARM_COUNT, SWARM_REAL, SWARM_BLIND_TICKS, SWARM_COOLDOWN;
    public static ForgeConfigSpec.BooleanValue ILLUSION_IMMUNE;

    /** Called from BossConfig's static block between push("ereb_hand") and pop(). */
    public static void define(ForgeConfigSpec.Builder b) {
        RAPIER_DAMAGE = b.comment("Added to attack_damage (the glass rapier): a thrust = attack_damage + rapier_damage").defineInRange("rapier_damage", 10.0, 0, 1000);
        MELEE_MIN = b.comment("Ticks between his rapier attacks").defineInRange("melee_interval_min", 8, 1, 200);
        MELEE_MAX = b.defineInRange("melee_interval_max", 16, 1, 200);
        SLAM_DAMAGE = b.comment("The ghost hand slams the ground (all phases): damage, radius round the palm, seconds between").defineInRange("slam_damage", 30.0, 0, 1000);
        SLAM_RADIUS = b.defineInRange("slam_radius", 3.5, 0.5, 16);
        SLAM_COOLDOWN = b.defineInRange("slam_cooldown", 8, 1, 600);
        ILLUSION_IMMUNE = b.comment("Immune to the Illusions school (damage and marks)").define("illusion_immune", true);

        DOUBLES_COUNT = b.comment("Phase 1 «Лживое слово»: his doubles with real and false fire strikes (count, how many are real, life, how often, the real strike, hits to break one)")
                .defineInRange("doubles_count", 3, 1, 8);
        DOUBLES_REAL = b.defineInRange("doubles_real", 1, 0, 8);
        DOUBLES_SECONDS = b.defineInRange("doubles_seconds", 12, 2, 120);
        DOUBLES_INTERVAL = b.defineInRange("doubles_interval", 24, 5, 600);
        DOUBLE_FIRE_DAMAGE = b.defineInRange("double_fire_damage", 20.0, 0, 1000);
        DOUBLE_HITS = b.defineInRange("double_hits", 2, 1, 20);
        GRAB_SECONDS = b.comment("Phase 2 «Длань»: the hand holds a player this long, squeezing every 1.2 s; the allies free it by dealing grab_break_damage to him")
                .defineInRange("grab_seconds", 5, 1, 60);
        SQUEEZE_DAMAGE = b.defineInRange("squeeze_damage", 14.0, 0, 1000);
        GRAB_BREAK_DAMAGE = b.defineInRange("grab_break_damage", 90.0, 1, 100000);
        GRAB_COOLDOWN = b.defineInRange("grab_cooldown", 16, 1, 600);
        MIRROR_WALLS_COUNT = b.comment("Phase 2: mirror walls round him that send the players' projectiles back (count, radius, seconds, how often)")
                .defineInRange("mirror_walls_count", 4, 1, 12);
        MIRROR_WALLS_RADIUS = b.defineInRange("mirror_walls_radius", 3.5, 1.5, 12);
        MIRROR_WALLS_SECONDS = b.defineInRange("mirror_walls_seconds", 8, 1, 120);
        MIRROR_WALLS_INTERVAL = b.defineInRange("mirror_walls_interval", 22, 2, 600);
        FIREWALL_SHARE = b.comment("Phase 3 «Глава Культа»: the mirror wall of fire on the arena edge — crossing it: this share of max health (boss_mechanic), fire, a push inside")
                .defineInRange("firewall_share", 0.2, 0, 1);
        FIREWALL_BURN = b.defineInRange("firewall_burn", 4, 0, 60);
        FIREWALL_PUSH = b.defineInRange("firewall_push", 1.0, 0, 10);

        HAND_OF_LIES_DAMAGE = b.comment("Special «Длань Лжи» (66%): the giant hand catches one player (damage on the catch) and holds it in the false arena this long")
                .defineInRange("hand_of_lies_damage", 20.0, 0, 1000);
        HAND_OF_LIES_SECONDS = b.defineInRange("hand_of_lies_seconds", 6, 1, 60);
        MASK_SECONDS = b.comment("Special «Падение маски» (45%): seconds to break one's own shard; not broken: this share of max health (boss_mechanic)")
                .defineInRange("mask_seconds", 8, 2, 60);
        MASK_FAIL_SHARE = b.defineInRange("mask_fail_share", 0.35, 0, 1);
        DREAM_SLAM_DAMAGE = b.comment("«Сон Бабочки: Полное Раскрытие» (20%): the giant hand over the dream slams (dream damage, not real), radius, how often; the dream's longest life (minutes)")
                .defineInRange("dream_slam_damage", 30.0, 0, 1000);
        DREAM_SLAM_RADIUS = b.defineInRange("dream_slam_radius", 4.0, 0.5, 16);
        DREAM_SLAM_INTERVAL = b.defineInRange("dream_slam_interval", 8, 2, 120);
        DREAM_MAX_MINUTES = b.defineInRange("dream_max_minutes", 20, 1, 120);

        FLAME_CIRCLES = b.comment("«Ложное пламя»: circles (decoys of them burn nothing), radius, damage every 0.5 s inside a real one, seconds, cooldown")
                .defineInRange("false_flame_circles", 5, 1, 16);
        FLAME_DECOYS = b.defineInRange("false_flame_decoys", 2, 0, 16);
        FLAME_RADIUS = b.defineInRange("false_flame_radius", 2.0, 0.5, 8);
        FLAME_DAMAGE = b.defineInRange("false_flame_damage", 9.0, 0, 1000);
        FLAME_SECONDS = b.defineInRange("false_flame_seconds", 3, 1, 30);
        FLAME_COOLDOWN = b.defineInRange("false_flame_cooldown", 14, 1, 600);
        GRIP_DAMAGE = b.comment("«Стеклянная хватка»: the cone (1 s warning): damage, length, full angle, pull to him, cooldown").defineInRange("glass_grip_damage", 34.0, 0, 1000);
        GRIP_RANGE = b.defineInRange("glass_grip_range", 6.0, 1, 32);
        GRIP_ANGLE = b.defineInRange("glass_grip_angle", 70.0, 5, 180);
        GRIP_PULL = b.defineInRange("glass_grip_pull", 1.2, 0, 5);
        GRIP_COOLDOWN = b.defineInRange("glass_grip_cooldown", 12, 1, 600);
        OATH_SECONDS = b.comment("«Чужая клятва»: the mark's seconds; what the marked one deals him goes ×share to its nearest ally (at most max_hit a hit)")
                .defineInRange("foreign_oath_seconds", 4, 1, 60);
        OATH_SHARE = b.defineInRange("foreign_oath_share", 0.5, 0, 2);
        OATH_MAX_HIT = b.defineInRange("foreign_oath_max_hit", 30.0, 0, 1000);
        OATH_COOLDOWN = b.defineInRange("foreign_oath_cooldown", 20, 1, 600);
        THOUSAND_MIRRORS = b.comment("«Тысяча отражений»: mirrors round the fight, of them real strikes, the strike, cooldown").defineInRange("thousand_mirrors", 6, 1, 16);
        THOUSAND_REAL = b.defineInRange("thousand_real", 2, 0, 16);
        THOUSAND_DAMAGE = b.defineInRange("thousand_damage", 40.0, 0, 1000);
        THOUSAND_COOLDOWN = b.defineInRange("thousand_cooldown", 18, 1, 600);

        CHANGELING_DAMAGE = b.comment("«Пламя-подменыш»: the fireball turns into a butterfly half way and hits the ally nearest its target (6 blocks; none — the target)")
                .defineInRange("changeling_flame_damage", 28.0, 0, 1000);
        CHANGELING_COOLDOWN = b.defineInRange("changeling_flame_cooldown", 12, 1, 600);
        RETREAT_DAMAGE = b.comment("«Ложное отступление»: the double stays, he is unseen 2 s and thrusts in the back of the first who comes within 3 blocks of it")
                .defineInRange("false_retreat_damage", 36.0, 0, 1000);
        RETREAT_COOLDOWN = b.defineInRange("false_retreat_cooldown", 20, 1, 600);
        TRAITOR_DAMAGE = b.comment("«Отражение-предатель»: a glass copy of a player attacks its allies (a hit), lives this long, hits to break (its original / the others), the burst if not broken")
                .defineInRange("traitor_reflection_damage", 14.0, 0, 1000);
        TRAITOR_SECONDS = b.defineInRange("traitor_reflection_seconds", 6, 1, 60);
        TRAITOR_HITS_ORIGINAL = b.defineInRange("traitor_reflection_hits_original", 1, 1, 20);
        TRAITOR_HITS_OTHERS = b.defineInRange("traitor_reflection_hits_others", 3, 1, 20);
        TRAITOR_BURST_DAMAGE = b.defineInRange("traitor_reflection_burst_damage", 30.0, 0, 1000);
        TRAITOR_BURST_RADIUS = b.defineInRange("traitor_reflection_burst_radius", 3.0, 0.5, 16);
        TRAITOR_COOLDOWN = b.defineInRange("traitor_reflection_cooldown", 24, 1, 600);
        SWARM_COUNT = b.comment("«Рой лжи»: glass butterflies at the players, of them real (a hit + blindness), the rest pass through")
                .defineInRange("swarm_of_lies_count", 12, 1, 64);
        SWARM_REAL = b.defineInRange("swarm_of_lies_real", 6, 0, 64);
        SWARM_DAMAGE = b.defineInRange("swarm_of_lies_damage", 10.0, 0, 1000);
        SWARM_BLIND_TICKS = b.defineInRange("swarm_of_lies_blind_ticks", 20, 0, 600);
        SWARM_COOLDOWN = b.defineInRange("swarm_of_lies_cooldown", 16, 1, 600);
        DAWN_NEAR_RADIUS = b.comment("Mythic «Ложный рассвет» (33%, once): the wave after 4 s — within near_radius this share of max health, the rest of the fight that share (boss_mechanic)")
                .defineInRange("false_dawn_near_radius", 6.0, 0, 64);
        DAWN_NEAR_SHARE = b.defineInRange("false_dawn_near_share", 0.6, 0, 1);
        DAWN_FAR_SHARE = b.defineInRange("false_dawn_far_share", 0.2, 0, 1);
    }

    static double d(ForgeConfigSpec.DoubleValue v) {
        return v == null ? 0 : ru.pohsmp.core.boss.BossConfig.get(v);
    }

    static int i(ForgeConfigSpec.IntValue v) {
        return v == null ? 0 : ru.pohsmp.core.boss.BossConfig.get(v);
    }

    static boolean b(ForgeConfigSpec.BooleanValue v) {
        return v != null && ru.pohsmp.core.boss.BossConfig.get(v);
    }
}
