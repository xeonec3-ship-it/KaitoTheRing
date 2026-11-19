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
        SPEC = b.build();
    }

    private ServerConfig() {}
}
