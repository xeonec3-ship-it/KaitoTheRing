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
    public static final ForgeConfigSpec.DoubleValue COUNTDOWN_MAX;
    public static final ForgeConfigSpec.DoubleValue STAR_FALL_DAMAGE, STAR_FALL_EDGE;

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
        b.push("countdown");
        COUNTDOWN_MAX = b.comment("Countdown: the repeated hit is capped at this share of the target's max health").defineInRange("maxRepeat", 0.4, 0.0, 100.0);
        b.pop();
        b.push("star_fall");
        STAR_FALL_DAMAGE = b.comment("Star Fall: damage in the centre of the impact (before spell power and resistances)").defineInRange("damage", 40.0, 0.0, 100000.0);
        STAR_FALL_EDGE = b.comment("Star Fall: share of that damage at the edge of the radius (8 blocks); it falls off linearly from the centre").defineInRange("edgeShare", 0.35, 0.0, 1.0);
        b.pop();
        SPEC = b.build();
    }

    private ServerConfig() {}
}
