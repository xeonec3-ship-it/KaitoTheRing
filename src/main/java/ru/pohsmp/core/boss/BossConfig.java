package ru.pohsmp.core.boss;

import java.util.LinkedHashMap;
import java.util.Map;
import net.minecraftforge.common.ForgeConfigSpec;

/**
 * Server config of the cult bosses: its own file, world/serverconfig/pohsmp_core-bosses-server.toml, sections [bosses_common],
 * [cult_leader], [irina], [aris], [martin], [ereb]. Keys (snake_case, owner's wish) and defaults from docs/specs/balance_bosses.md
 * (the manager's draft of 20.11). Only the keys the code uses are here; T27-T30 add their mechanics keys to their own section.
 */
public final class BossConfig {
    private BossConfig() {}

    public static final ForgeConfigSpec SPEC;

    // [bosses_common]
    public static final ForgeConfigSpec.DoubleValue HP_PER_PLAYER, HP_PER_PLAYER_SQ, COUNT_RADIUS_EXTRA, INTRO_RADIUS, SCENE_RADIUS;
    public static final ForgeConfigSpec.IntValue MAX_COUNTED, FINISHER_COOLDOWN, ABILITY_GCD, TOP_DAMAGE_WINDOW, REPLICA_TAUNT_COOLDOWN, ENRAGE_MINUTES;
    public static final ForgeConfigSpec.DoubleValue ENRAGE_STEP, ENRAGE_MAX;
    public static final ForgeConfigSpec.BooleanValue SCENES, SPECIALS;

    /** The body of a boss (absolute attribute values; a negative resist = leave the base class's own). */
    public static final class PerBoss {
        public final ForgeConfigSpec.DoubleValue hp, armor, toughness, knockback, speed, attack, spellPower, spellResist, arena;
        public final ForgeConfigSpec.DoubleValue fireResist, iceResist, holyResist, bloodResist, eldritchResist;
        public final ForgeConfigSpec.IntValue xp;

        PerBoss(ForgeConfigSpec.Builder b, Body d) {
            hp = b.comment("Max health for one player; more players: x(1 + hp_per_extra_player*(N-1) + ...)").defineInRange("hp", d.hp, 1, 1_000_000);
            armor = b.defineInRange("armor", d.armor, 0, 30);
            toughness = b.defineInRange("armor_toughness", d.toughness, 0, 20);
            knockback = b.defineInRange("knockback_resistance", d.kb, 0, 1);
            speed = b.defineInRange("movement_speed", d.speed, 0, 2);
            attack = b.comment("Melee damage (before armour)").defineInRange("attack_damage", d.attack, 0, 1000);
            spellPower = b.defineInRange("spell_power", d.power, 0, 100);
            spellResist = b.defineInRange("spell_resist", d.resist, 0, 100);
            fireResist = b.comment("School resists (Iron's: 1 = normal, >1 = less damage); -1 = leave as is").defineInRange("fire_resist", d.fire, -1, 100);
            iceResist = b.defineInRange("ice_resist", d.ice, -1, 100);
            holyResist = b.defineInRange("holy_resist", d.holy, -1, 100);
            bloodResist = b.defineInRange("blood_resist", d.blood, -1, 100);
            eldritchResist = b.defineInRange("eldritch_resist", d.eldritch, -1, 100);
            arena = b.comment("Arena radius around the spawn point").defineInRange("arena_radius", d.arena, 4, 128);
            xp = b.comment("Experience on death (no loot at all)").defineInRange("xp", d.xp, 0, 100000);
        }
    }

    /** Defaults of a body (balance_bosses.md). */
    private record Body(double hp, double armor, double toughness, double kb, double speed, double attack, double power, double resist,
                        double fire, double ice, double holy, double blood, double eldritch, double arena, int xp) {}

    private static final Map<String, PerBoss> PER = new LinkedHashMap<>();

    // [cult_leader] (T26) mechanics
    public static final ForgeConfigSpec.DoubleValue CL_SCYTHE, CL_FURY_DAMAGE, CL_FURY_INTERVAL, CL_SICKLE_DAMAGE, CL_DASH_DAMAGE, CL_TRAIL_DAMAGE,
            CL_TRAIL_WIDTH, CL_BRAND_DAMAGE, CL_BRAND_RADIUS, CL_PILLARS_DAMAGE, CL_FF_PILLAR_DAMAGE, CL_FF_PILLAR_RADIUS, CL_FF_RING_DAMAGE,
            CL_VERDICT_RADIUS, CL_FIREWALL_SHARE, CL_FIREWALL_PUSH, CL_CULTIST_HP, CL_CULTIST_ARMOR, CL_CULTIST_POWER, CL_ASH_DAMAGE, CL_ASH_WIDTH,
            CL_ASH_BURN;
    public static final ForgeConfigSpec.IntValue CL_MELEE_MIN, CL_MELEE_MAX, CL_SICKLE_COOLDOWN, CL_SICKLE_BURN, CL_DASH_COOLDOWN, CL_TRAIL_INTERVAL,
            CL_TRAIL_SECONDS, CL_BRAND_DELAY, CL_BRAND_COOLDOWN, CL_BRAND_TARGETS_BIG, CL_PILLARS_COUNT, CL_PILLARS_COUNT_P3, CL_PILLARS_COOLDOWN,
            CL_VERDICT_INTERVAL, CL_VERDICT_SECONDS, CL_FIREWALL_BURN, CL_CULTISTS_SMALL, CL_CULTISTS_MID, CL_CULTISTS_BIG, CL_CULTIST_WAVE;

    static {
        ForgeConfigSpec.Builder b = new ForgeConfigSpec.Builder();
        b.comment("Common rules of the cult bosses (T26-T30). Spawned only with /pohsmp boss <id> (op 2); no natural spawn, no loot.").push("bosses_common");
        HP_PER_PLAYER = b.comment("Health: x(1 + hp_per_extra_player*(N-1) + hp_per_extra_player_sq*(N-1)^2), N = players in the arena")
                .defineInRange("hp_per_extra_player", 0.35, 0, 10);
        HP_PER_PLAYER_SQ = b.defineInRange("hp_per_extra_player_sq", 0.0, 0, 10);
        MAX_COUNTED = b.comment("N is never more than this").defineInRange("max_counted_players", 8, 1, 100);
        COUNT_RADIUS_EXTRA = b.comment("Players (survival/adventure) within arena_radius + this of the spawn point count").defineInRange("count_radius_extra", 8.0, 0, 128);
        INTRO_RADIUS = b.comment("Who sees the intro and death scenes").defineInRange("intro_radius", 64.0, 4, 256);
        SCENE_RADIUS = b.comment("Who sees the special spell scenes (the fight does not stop)").defineInRange("scene_radius", 48.0, 4, 256);
        FINISHER_COOLDOWN = b.comment("Finishing a player off with an animation: not more often than this").defineInRange("finisher_cooldown_seconds", 5, 0, 600);
        ABILITY_GCD = b.comment("At least this between two of the bosses' own attacks").defineInRange("ability_gcd_seconds", 3, 0, 60);
        TOP_DAMAGE_WINDOW = b.comment("«The strongest enemy» = most damage dealt to the boss in this window").defineInRange("top_damage_window_seconds", 30, 1, 3600);
        REPLICA_TAUNT_COOLDOWN = b.comment("«Дезинтеграция: Реплика» never works on them; their phrase about it not more often than this")
                .defineInRange("replica_taunt_cooldown", 20, 0, 3600);
        ENRAGE_MINUTES = b.comment("A long fight: after this many minutes +enrage_step damage every minute, up to enrage_max (0 = off)")
                .defineInRange("enrage_minutes", 14, 0, 600);
        ENRAGE_STEP = b.defineInRange("enrage_step", 0.2, 0, 10);
        ENRAGE_MAX = b.defineInRange("enrage_max", 2.0, 1, 100);
        SCENES = b.comment("Camera scenes on/off (the same timings without the camera)").define("scenes", true);
        SPECIALS = b.comment("Special spells (one per fight each) on/off").define("specials", true);
        b.pop();

        b.comment("T26 Head of the Cult of Mellisto (Tyros, First Flamebearer)").push("cult_leader");
        PER.put("cult_leader", new PerBoss(b, new Body(4500, 16, 2, 1.0, 0.24, 14, 1.6, 1.25, 1.75, -1, -1, -1, -1, 28, 500)));
        CL_SCYTHE = b.comment("Added to attack_damage (the cult scythe; Tyros's scythe gives 10)").defineInRange("scythe_damage", 10.0, 0, 1000);
        CL_MELEE_MIN = b.comment("Ticks between melee attacks (Tyros 10-30)").defineInRange("melee_interval_min", 8, 1, 200);
        CL_MELEE_MAX = b.defineInRange("melee_interval_max", 22, 1, 200);
        CL_FURY_DAMAGE = b.comment("Phase 3 fury: his damage x, melee interval x").defineInRange("fury_damage_mult", 1.2, 0, 10);
        CL_FURY_INTERVAL = b.defineInRange("fury_attack_interval_mult", 0.75, 0.1, 10);
        CL_SICKLE_DAMAGE = b.comment("«Огненный серп»: per touch (out and back: up to two)").defineInRange("sickle_damage", 28.0, 0, 1000);
        CL_SICKLE_COOLDOWN = b.defineInRange("sickle_cooldown", 12, 1, 600);
        CL_SICKLE_BURN = b.defineInRange("sickle_burn_seconds", 4, 0, 60);
        CL_DASH_DAMAGE = b.comment("«Пепельный след»: the dash, then the strip").defineInRange("ash_dash_damage", 30.0, 0, 1000);
        CL_TRAIL_DAMAGE = b.defineInRange("ash_trail_damage", 4.0, 0, 1000);
        CL_TRAIL_INTERVAL = b.defineInRange("ash_trail_interval_ticks", 10, 1, 200);
        CL_TRAIL_SECONDS = b.defineInRange("ash_trail_seconds", 4, 1, 60);
        CL_TRAIL_WIDTH = b.defineInRange("ash_trail_width", 1.6, 0.2, 8);
        CL_DASH_COOLDOWN = b.defineInRange("ash_dash_cooldown", 14, 1, 600);
        CL_BRAND_DAMAGE = b.comment("«Клеймо культа»").defineInRange("brand_damage", 40.0, 0, 1000);
        CL_BRAND_RADIUS = b.defineInRange("brand_radius", 3.0, 0.5, 16);
        CL_BRAND_DELAY = b.defineInRange("brand_delay_seconds", 3, 1, 30);
        CL_BRAND_COOLDOWN = b.defineInRange("brand_cooldown", 18, 1, 600);
        CL_BRAND_TARGETS_BIG = b.comment("Targets from phase 2 when 4+ players fight").defineInRange("brand_targets_big_group", 2, 1, 8);
        CL_PILLARS_DAMAGE = b.comment("«Столпы пламени»").defineInRange("pillars_damage", 35.0, 0, 1000);
        CL_PILLARS_COUNT = b.defineInRange("pillars_count", 5, 1, 32);
        CL_PILLARS_COUNT_P3 = b.defineInRange("pillars_count_p3", 7, 1, 32);
        CL_PILLARS_COOLDOWN = b.defineInRange("pillars_cooldown", 16, 1, 600);
        CL_FF_PILLAR_DAMAGE = b.comment("«Первое Пламя»: the pillar in the centre, the ring of fire (jumping over it: no damage)")
                .defineInRange("first_flame_pillar_damage", 60.0, 0, 1000);
        CL_FF_PILLAR_RADIUS = b.defineInRange("first_flame_pillar_radius", 3.0, 0.5, 16);
        CL_FF_RING_DAMAGE = b.defineInRange("first_flame_ring_damage", 35.0, 0, 1000);
        CL_VERDICT_INTERVAL = b.comment("Phase 2 «Приговор Меллисто»: every N s, no one but him casts for verdict_seconds in verdict_radius")
                .defineInRange("verdict_interval", 25, 5, 600);
        CL_VERDICT_SECONDS = b.defineInRange("verdict_seconds", 10, 1, 120);
        CL_VERDICT_RADIUS = b.defineInRange("verdict_radius", 24.0, 4, 64);
        CL_FIREWALL_SHARE = b.comment("Phase 3 wall of fire: crossing it costs this share of the player's max health (through armour)")
                .defineInRange("firewall_damage_share", 0.25, 0, 1);
        CL_FIREWALL_BURN = b.defineInRange("firewall_burn_seconds", 4, 0, 60);
        CL_FIREWALL_PUSH = b.comment("...and pushes back inside").defineInRange("firewall_push", 1.0, 0, 10);
        CL_CULTISTS_SMALL = b.comment("Phase 3 fire cultists: N <= 2 / 3-4 / 5+ players").defineInRange("cultists_small", 2, 0, 16);
        CL_CULTISTS_MID = b.defineInRange("cultists_mid", 3, 0, 16);
        CL_CULTISTS_BIG = b.defineInRange("cultists_big", 4, 0, 16);
        CL_CULTIST_WAVE = b.comment("A second wave this long after the first, if all are dead (0 = none)").defineInRange("cultist_second_wave_seconds", 45, 0, 3600);
        CL_CULTIST_HP = b.comment("Cultist health (x the boss's player multiplier)").defineInRange("cultist_hp", 60.0, 1, 10000);
        CL_CULTIST_ARMOR = b.defineInRange("cultist_armor", 6.0, 0, 30);
        CL_CULTIST_POWER = b.defineInRange("cultist_spell_power", 1.0, 0, 100);
        CL_ASH_DAMAGE = b.comment("«Пепел Меллисто»: the slash across the arena, its width, the burning trace (10 s)").defineInRange("ash_slash_damage", 70.0, 0, 1000);
        CL_ASH_WIDTH = b.defineInRange("ash_slash_width", 1.5, 0.2, 8);
        CL_ASH_BURN = b.defineInRange("ash_burn_damage", 4.0, 0, 1000);
        b.pop();

        b.comment("T27 Irina, the Witch of Jealousy").push("irina");
        PER.put("irina", new PerBoss(b, new Body(4400, 8, 0, 1.0, 0.26, 22, 1.4, 1.3, 0.85, -1, -1, 1.3, -1, 24, 500)));
        b.pop();
        b.comment("T28 Aris, the Mythic Smith").push("aris");
        PER.put("aris", new PerBoss(b, new Body(4400, 18, 3, 1.0, 0.22, 18, 1.3, 1.1, 1.5, 0.85, -1, -1, -1, 24, 500)));
        ru.pohsmp.core.boss.aris.ArisConfig.define(b);   // T28 mechanics
        b.pop();
        b.comment("T29 Martin, the Last Warlord").push("martin");
        PER.put("martin", new PerBoss(b, new Body(4000, 18, 4, 1.0, 0.23, 20, 1.2, 1.15, -1, -1, 0.9, -1, -1, 24, 500)));
        ru.pohsmp.core.boss.martin.MartinConfig.define(b);   // T29 mechanics keys
        b.pop();
        b.comment("T30 Ereb, the First Traitor").push("ereb");
        PER.put("ereb", new PerBoss(b, new Body(4000, 10, 0, 1.0, 0.28, 10, 1.5, 1.3, -1, -1, 0.85, -1, 1.2, 24, 500)));
        b.pop();
        SPEC = b.build();
    }

    /** The body values of a boss id, or null if the config has no section for it. */
    public static PerBoss of(String bossId) {
        return PER.get(bossId);
    }

    /** Reads a value, or its default if the config is not loaded yet (unit tests, very early calls). */
    public static <T> T get(ForgeConfigSpec.ConfigValue<T> v) {
        try {
            return v.get();
        } catch (IllegalStateException e) {
            return v.getDefault();
        }
    }
}
