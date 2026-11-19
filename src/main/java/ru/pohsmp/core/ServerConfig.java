package ru.pohsmp.core;

import net.minecraftforge.common.ForgeConfigSpec;

public final class ServerConfig {
    public static final ForgeConfigSpec SPEC;
    public static final ForgeConfigSpec.IntValue BACKLASH_SECONDS, SLOW_SECONDS, WEAK_SECONDS, NAUSEA_SECONDS;
    public static final ForgeConfigSpec.BooleanValue BLOCK_MANA;
    public static final ForgeConfigSpec.BooleanValue AURA;
    public static final ForgeConfigSpec.DoubleValue DIS_PERCENT;
    public static final ForgeConfigSpec.DoubleValue DIS_FLAT;
    public static final ForgeConfigSpec.IntValue DIS_RANGE;
    public static final ForgeConfigSpec.BooleanValue DIS_KILL;
    public static final ForgeConfigSpec.DoubleValue REPLICA_PERCENT;
    public static final ForgeConfigSpec.DoubleValue HIGHER_MULT;
    public static final ForgeConfigSpec.DoubleValue GATE_RAY_DAMAGE, GATE_RAY_RADIUS, GATE_RAYS_PER_SECOND, GATE_MAIN_PERCENT, GATE_MAIN_FLAT,
            GATE_MAIN_RADIUS, GATE_AREA, GATE_SET_BONUS;
    public static final ForgeConfigSpec.IntValue GATE_HIT_COOLDOWN, GATE_AIM_INTERVAL, GATE_RANGE, GATE_SILENCE_SECONDS;
    public static final ForgeConfigSpec.ConfigValue<java.util.List<? extends String>> JOINT_SPELLS;
    public static final ForgeConfigSpec.DoubleValue JOINT_RADIUS, JOINT_WINDOW, JOINT_MULT;
    public static final ForgeConfigSpec.DoubleValue COUNTDOWN_MAX;
    public static final ForgeConfigSpec.IntValue SCARLET_CUTS_MIN, SCARLET_CUTS_MAX, SCARLET_INTERVAL, SCARLET_CRACK_DELAY;
    public static final ForgeConfigSpec.DoubleValue SCARLET_DAMAGE, SCARLET_WIDTH, SCARLET_NEAR, SCARLET_FAR,
            SCARLET_SHARD_DAMAGE, SCARLET_SHARD_RADIUS, SCARLET_KNOCK_UP;

    static {
        ForgeConfigSpec.Builder b = new ForgeConfigSpec.Builder();
        b.push("divine");
        AURA = b.comment("Golden aura around a player casting a Divine-tier scroll").define("aura", true);
        BACKLASH_SECONDS = b.comment("Duration of the Divine Backlash effect after a successful Divine-tier scroll cast (seconds)").defineInRange("backlashSeconds", 60, 1, 3600);
        SLOW_SECONDS = b.comment("Slowness II part, from the start of the effect (seconds, 0 = off)").defineInRange("slowSeconds", 10, 0, 3600);
        WEAK_SECONDS = b.comment("Weakness II part, from the start of the effect (seconds, 0 = off)").defineInRange("weakSeconds", 15, 0, 3600);
        NAUSEA_SECONDS = b.comment("Hidden nausea (no icon) put together with the effect (seconds, 0 = off)").defineInRange("nauseaSeconds", 5, 0, 3600);
        BLOCK_MANA = b.comment("No mana gain of any kind (regeneration, potions) while the effect lasts").define("blockMana", true);
        b.pop();
        b.push("disintegration");
        DIS_PERCENT = b.comment("Damage as a share of the target's max health").defineInRange("damagePercent", 1.0, 0.0, 10.0);
        DIS_FLAT = b.comment("Flat damage added on top").defineInRange("damageFlat", 0.0, 0.0, 100000.0);
        DIS_KILL = b.comment("The target always dies (absorption, resistances and totems do not save it; creative/spectator players are exempt)").define("alwaysKill", true);
        DIS_RANGE = b.comment("Targeting range in blocks").defineInRange("range", 48, 4, 128);
        b.pop();
        b.push("disintegration_replica");
        REPLICA_PERCENT = b.comment("Disintegration: Replica - damage as a share of the target's max health, through armor; never kills (leaves 1 HP)").defineInRange("damagePercent", 0.9, 0.0, 10.0);
        b.pop();
        b.push("higher");
        HIGHER_MULT = b.comment("Damage and healing multiplier for all Higher-school spells").defineInRange("damageMult", 1.0, 0.0, 100.0);
        b.pop();
        b.push("silent_gate");
        GATE_RANGE = b.comment("Gate: how far the caster's look picks the strike point (blocks)").defineInRange("range", 64, 8, 128);
        GATE_AREA = b.comment("Radius of the area the rays fall on, around the strike point").defineInRange("area", 20.0, 2.0, 64.0);
        GATE_RAY_DAMAGE = b.comment("Damage of one ray (Silent magic: through armor, scaled by Silent spell power, cut by Silent resistance)").defineInRange("rayDamage", 10.0, 0.0, 10000.0);
        GATE_RAY_RADIUS = b.comment("Radius of one ray's hit").defineInRange("rayRadius", 1.5, 0.1, 16.0);
        GATE_RAYS_PER_SECOND = b.comment("Rays per second at random points of the area").defineInRange("raysPerSecond", 8.0, 0.0, 100.0);
        GATE_AIM_INTERVAL = b.comment("Every this many ticks one ray falls exactly on every foe in the area").defineInRange("aimedInterval", 10, 1, 200);
        GATE_HIT_COOLDOWN = b.comment("One creature is hit by rays at most once per this many ticks").defineInRange("hitCooldownTicks", 8, 0, 200);
        GATE_MAIN_PERCENT = b.comment("Main beam (52 s): share of the target's max health").defineInRange("mainPercent", 0.5, 0.0, 10.0);
        GATE_MAIN_FLAT = b.comment("Main beam: flat damage added").defineInRange("mainFlat", 30.0, 0.0, 100000.0);
        GATE_MAIN_RADIUS = b.comment("Main beam: radius of its hit").defineInRange("mainRadius", 3.0, 0.5, 32.0);
        GATE_SET_BONUS = b.comment("Silent Witch full set (always worn when Gate is cast): ray and main beam damage multiplier").defineInRange("setBonus", 1.2, 0.0, 100.0);
        GATE_SILENCE_SECONDS = b.comment("'Silence' after the cast: Gate cannot be cast again for this long (other magic is fine)").defineInRange("silenceSeconds", 180, 0, 86400);
        b.pop();
        b.push("joint_cast");
        JOINT_SPELLS = b.comment("Joint cast: spells (full ids) two mages can cast together from scrolls. Only long casts (with a cast bar) take part.",
                        "The second mage starts the same spell from a scroll within the window and the radius: both casts end together after",
                        "castTimeMult of the first mage's cast time, the spell takes effect once (from the first mage), the second scroll is spent too.")
                .defineListAllowEmpty(java.util.List.of("spells"), () -> java.util.List.of("pohsmp_core:explosion", "pohsmp_core:heaven_fall",
                        "pohsmp_core:ark", "pohsmp_core:frozen_hour", "pohsmp_core:disintegration"), o -> o instanceof String s && s.contains(":"));
        JOINT_RADIUS = b.comment("Max distance between the two mages (blocks)").defineInRange("radius", 6.0, 1.0, 64.0);
        JOINT_WINDOW = b.comment("The second mage must start within this many seconds of the first one's cast start").defineInRange("windowSeconds", 2.0, 0.05, 30.0);
        JOINT_MULT = b.comment("Cast time of a joint cast as a share of the first mage's cast time").defineInRange("castTimeMult", 0.7, 0.05, 1.0);
        b.pop();
        b.push("countdown");
        COUNTDOWN_MAX = b.comment("Countdown: the repeated hit is capped at this share of the target's max health").defineInRange("maxRepeat", 0.4, 0.0, 100.0);
        b.pop();
        b.push("scarlet_cut");
        SCARLET_CUTS_MIN = b.comment("Scarlet Cut: fewest cuts in a series").defineInRange("cutsMin", 3, 1, 20);
        SCARLET_CUTS_MAX = b.comment("Most cuts in a series (the count is picked at random between min and max)").defineInRange("cutsMax", 5, 1, 20);
        SCARLET_INTERVAL = b.comment("Ticks between cuts").defineInRange("interval", 4, 1, 40);
        SCARLET_DAMAGE = b.comment("Damage of one cut to everyone it hits (times [higher] damageMult)").defineInRange("damage", 6.0, 0.0, 10000.0);
        SCARLET_WIDTH = b.comment("Width of a cut across the view, blocks").defineInRange("width", 4.0, 0.5, 32.0);
        SCARLET_NEAR = b.comment("A cut hits from this distance in front of the caster...").defineInRange("near", 3.0, 0.0, 32.0);
        SCARLET_FAR = b.comment("...up to this distance, blocks").defineInRange("far", 6.0, 0.5, 64.0);
        SCARLET_CRACK_DELAY = b.comment("Ticks from a cut until its crack bursts (the effect's burst is timed for 20)").defineInRange("crackDelay", 20, 1, 200);
        SCARLET_SHARD_DAMAGE = b.comment("Damage of the crack's burst (times [higher] damageMult)").defineInRange("shardDamage", 4.0, 0.0, 10000.0);
        SCARLET_SHARD_RADIUS = b.comment("The burst hits within this distance of the crack line, blocks").defineInRange("shardRadius", 1.5, 0.1, 16.0);
        SCARLET_KNOCK_UP = b.comment("Upward push of the burst").defineInRange("knockUp", 0.4, 0.0, 5.0);
        b.pop();
        SPEC = b.build();
    }

    private ServerConfig() {}
}
