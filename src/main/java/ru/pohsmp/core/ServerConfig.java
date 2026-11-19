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
    public static final ForgeConfigSpec.ConfigValue<java.util.List<? extends String>> JOINT_SPELLS;
    public static final ForgeConfigSpec.DoubleValue JOINT_RADIUS, JOINT_WINDOW, JOINT_MULT;

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
        SPEC = b.build();
    }

    private ServerConfig() {}
}
