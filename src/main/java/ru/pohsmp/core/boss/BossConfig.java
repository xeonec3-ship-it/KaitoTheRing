package ru.pohsmp.core.boss;

import java.util.LinkedHashMap;
import java.util.Map;
import net.minecraftforge.common.ForgeConfigSpec;

/**
 * Server config of the cult bosses: its own file, world/serverconfig/pohsmp_core-bosses-server.toml (sections [bosses_common],
 * [cult_leader], [irina], [aris], [martin], [ereb]). Values are placeholders until docs/specs/balance_bosses.md (the assistant's
 * balance) is in; the keys follow the per-boss pattern below so T27-T30 only add their own mechanics keys.
 */
public final class BossConfig {
    private BossConfig() {}

    public static final ForgeConfigSpec SPEC;

    // [bosses_common]
    public static final ForgeConfigSpec.DoubleValue HP_PER_PLAYER, HP_PER_PLAYER_SQ, HP_MAX_MULT, SCALE_RADIUS, INTRO_RADIUS, SCENE_RADIUS;
    public static final ForgeConfigSpec.IntValue FINISHER_COOLDOWN;
    public static final ForgeConfigSpec.BooleanValue SCENES, SPECIALS;

    /** Per boss: base health, attack damage multiplier, speed multiplier, xp. */
    public static final class PerBoss {
        public final ForgeConfigSpec.DoubleValue health, damage, speed;
        public final ForgeConfigSpec.IntValue xp;

        PerBoss(ForgeConfigSpec.Builder b, double hp, double dmg, double spd, int xp) {
            health = b.comment("Base max health (one player); scaled up by [bosses_common] for more players").defineInRange("health", hp, 1, 1_000_000);
            damage = b.comment("Attack damage / spell power multiplier").defineInRange("damageMultiplier", dmg, 0.0, 100.0);
            speed = b.comment("Movement speed multiplier").defineInRange("speedMultiplier", spd, 0.1, 10.0);
            this.xp = b.comment("Experience dropped on death (no loot at all)").defineInRange("xp", xp, 0, 100000);
        }
    }

    private static final Map<String, PerBoss> PER = new LinkedHashMap<>();

    // [cult_leader] (T26) mechanics
    public static final ForgeConfigSpec.IntValue CL_VERDICT_INTERVAL, CL_VERDICT_SECONDS, CL_CULTISTS_MIN, CL_CULTISTS_MAX, CL_BRAND_DELAY,
            CL_SPELL_COOLDOWN;
    public static final ForgeConfigSpec.DoubleValue CL_VERDICT_RADIUS, CL_ARENA_RADIUS, CL_FIREWALL_DAMAGE, CL_FIRST_FLAME_DAMAGE, CL_PILLAR_DAMAGE,
            CL_ASH_SLASH_DAMAGE, CL_ASH_SLASH_WIDTH, CL_SICKLE_DAMAGE, CL_TRAIL_DAMAGE, CL_TRAIL_WIDTH, CL_BRAND_DAMAGE, CL_BRAND_RADIUS,
            CL_PILLARS_DAMAGE;

    static {
        ForgeConfigSpec.Builder b = new ForgeConfigSpec.Builder();
        b.comment("Common rules of the cult bosses (T26-T30). Spawned only with /pohsmp boss <id>; no natural spawn, no loot.").push("bosses_common");
        HP_PER_PLAYER = b.comment("Health scaling: x(1 + e*healthPerExtraPlayer + e^2*healthPerExtraPlayerSq), e = players in the fight - 1")
                .defineInRange("healthPerExtraPlayer", 0.4, 0, 10);
        HP_PER_PLAYER_SQ = b.defineInRange("healthPerExtraPlayerSq", 0.1, 0, 10);
        HP_MAX_MULT = b.comment("Upper cap of that multiplier (1 = no cap)").defineInRange("healthMaxMultiplier", 4.0, 1, 100);
        SCALE_RADIUS = b.comment("Players within this of the spawn point count for scaling").defineInRange("scaleRadius", 48.0, 4, 256);
        INTRO_RADIUS = b.comment("Who sees the intro and death scenes").defineInRange("introRadius", 64.0, 4, 256);
        SCENE_RADIUS = b.comment("Who sees the special spell scenes (the fight does not stop)").defineInRange("sceneRadius", 48.0, 4, 256);
        FINISHER_COOLDOWN = b.comment("Finishing a player off with an animation: not more often than this (seconds)").defineInRange("finisherCooldown", 5, 0, 600);
        SCENES = b.comment("Camera scenes on/off (intro, specials, death); off = the same timings without the camera").define("scenes", true);
        SPECIALS = b.comment("Special spells (one per fight each) on/off").define("specials", true);
        b.pop();

        b.comment("T26 Head of the Cult of Mellisto (Tyros, First Flamebearer): about three times the Echo of Tyros").push("cult_leader");
        PER.put("cult_leader", new PerBoss(b, 3000, 1.3, 1.1, 60));
        CL_ARENA_RADIUS = b.comment("Arena radius around the spawn point (the wall of fire in phase 3)").defineInRange("arenaRadius", 28.0, 8, 64);
        CL_VERDICT_INTERVAL = b.comment("Phase 2 «Приговор Меллисто»: every N seconds").defineInRange("verdictInterval", 25, 5, 600);
        CL_VERDICT_SECONDS = b.comment("...no one but him casts for this long").defineInRange("verdictSeconds", 10, 1, 120);
        CL_VERDICT_RADIUS = b.defineInRange("verdictRadius", 24.0, 4, 64);
        CL_FIREWALL_DAMAGE = b.comment("Phase 3: damage when crossing the wall of fire").defineInRange("firewallDamage", 8.0, 0, 1000);
        CL_CULTISTS_MIN = b.comment("Phase 3: fire cultists summoned").defineInRange("cultistsMin", 2, 0, 16);
        CL_CULTISTS_MAX = b.defineInRange("cultistsMax", 4, 0, 16);
        CL_FIRST_FLAME_DAMAGE = b.comment("«Первое Пламя»: the ring of fire (jump over it)").defineInRange("firstFlameRingDamage", 14.0, 0, 1000);
        CL_PILLAR_DAMAGE = b.comment("«Первое Пламя»: the pillar in the centre").defineInRange("firstFlamePillarDamage", 20.0, 0, 1000);
        CL_ASH_SLASH_DAMAGE = b.comment("«Пепел Меллисто»: the slash across the arena").defineInRange("ashSlashDamage", 24.0, 0, 1000);
        CL_ASH_SLASH_WIDTH = b.comment("...its half-width... full width of the burning line").defineInRange("ashSlashWidth", 1.5, 0.2, 8);
        CL_SPELL_COOLDOWN = b.comment("The four new attacks: seconds between them").defineInRange("spellCooldown", 9, 1, 120);
        CL_SICKLE_DAMAGE = b.comment("«Огненный серп»").defineInRange("sickleDamage", 12.0, 0, 1000);
        CL_TRAIL_DAMAGE = b.comment("«Пепельный след»: per second in the burning strip").defineInRange("ashTrailDamage", 4.0, 0, 1000);
        CL_TRAIL_WIDTH = b.defineInRange("ashTrailWidth", 1.6, 0.2, 8);
        CL_BRAND_DELAY = b.comment("«Клеймо культа»: seconds until the brand explodes").defineInRange("brandDelay", 3, 1, 30);
        CL_BRAND_DAMAGE = b.defineInRange("brandDamage", 16.0, 0, 1000);
        CL_BRAND_RADIUS = b.defineInRange("brandRadius", 3.0, 0.5, 16);
        CL_PILLARS_DAMAGE = b.comment("«Столпы пламени»: each pillar").defineInRange("pillarsDamage", 12.0, 0, 1000);
        b.pop();

        b.comment("T27 Irina").push("irina");
        PER.put("irina", new PerBoss(b, 2400, 1.2, 1.1, 50));
        b.pop();
        b.comment("T28 Aris").push("aris");
        PER.put("aris", new PerBoss(b, 2600, 1.3, 1.0, 50));
        b.pop();
        b.comment("T29 Martin").push("martin");
        PER.put("martin", new PerBoss(b, 2800, 1.3, 1.0, 50));
        b.pop();
        b.comment("T30 Ereb").push("ereb");
        PER.put("ereb", new PerBoss(b, 2200, 1.2, 1.2, 50));
        b.pop();
        SPEC = b.build();
    }

    /** The per-boss values (health, damage, speed, xp) of a boss id, or null if the config has no section for it. */
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
