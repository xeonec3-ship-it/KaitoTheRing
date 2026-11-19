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

    // [silent_staff] - the four Silent Witch staff spells (T20)
    public static final ForgeConfigSpec.IntValue SPEARS_CAST, SPEARS_MANA, SPEARS_TARGETS, SPEARS_HOVER;
    public static final ForgeConfigSpec.DoubleValue SPEARS_COOLDOWN, SPEARS_RANGE, SPEARS_CONE, SPEARS_SPEED, SPEARS_DAMAGE, SPEARS_KNOCKBACK;
    public static final ForgeConfigSpec.IntValue VOLLEY_CAST, VOLLEY_MANA, VOLLEY_SEALS, VOLLEY_PER_TARGET;
    public static final ForgeConfigSpec.DoubleValue VOLLEY_COOLDOWN, VOLLEY_RADIUS, VOLLEY_ARC, VOLLEY_SEAL_RADIUS, VOLLEY_DAMAGE;
    public static final ForgeConfigSpec.IntValue BARRIER_CAST, BARRIER_MANA, BARRIER_SECONDS;
    public static final ForgeConfigSpec.DoubleValue BARRIER_COOLDOWN, BARRIER_RADIUS;
    public static final ForgeConfigSpec.IntValue FLAME_CAST, FLAME_MANA, FLAME_BREATH, FLAME_INTERVAL, FLAME_BURN;
    public static final ForgeConfigSpec.DoubleValue FLAME_COOLDOWN, FLAME_CONE, FLAME_RANGE, FLAME_DAMAGE, FLAME_BURN_DPS;

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
        b.comment("Silent Witch staff spells: Wind Spears, Silent Volley, Barrier, Black Flame of Worgan.",
                "Damage is multiplied by the caster's Silent spell power (the staff itself gives +25%).").push("silent_staff");
        b.push("wind_spears");
        SPEARS_CAST = b.comment("Cast time (ticks)").defineInRange("castTicks", 20, 0, 1200);
        SPEARS_COOLDOWN = b.comment("Cooldown (seconds)").defineInRange("cooldown", 6.0, 0.0, 3600.0);
        SPEARS_MANA = b.comment("Mana cost").defineInRange("mana", 40, 0, 10000);
        SPEARS_TARGETS = b.comment("Most targets (one spear each)").defineInRange("targets", 5, 1, 32);
        SPEARS_CONE = b.comment("Cone in front of the caster, full angle (degrees)").defineInRange("coneDegrees", 60.0, 1.0, 360.0);
        SPEARS_RANGE = b.comment("Range (blocks)").defineInRange("range", 32.0, 1.0, 128.0);
        SPEARS_HOVER = b.comment("Spears hang over the shoulders before they fly (ticks)").defineInRange("hoverTicks", 10, 0, 200);
        SPEARS_SPEED = b.comment("Spear speed (blocks per tick)").defineInRange("speed", 3.0, 0.1, 16.0);
        SPEARS_DAMAGE = b.comment("Damage of one spear (to the head)").defineInRange("damage", 14.0, 0.0, 10000.0);
        SPEARS_KNOCKBACK = b.comment("Knockback strength").defineInRange("knockback", 0.6, 0.0, 10.0);
        b.pop();
        b.push("silent_volley");
        VOLLEY_CAST = b.comment("Cast time (ticks); the seals appear during it").defineInRange("castTicks", 60, 0, 1200);
        VOLLEY_COOLDOWN = b.comment("Cooldown (seconds)").defineInRange("cooldown", 20.0, 0.0, 3600.0);
        VOLLEY_MANA = b.comment("Mana cost").defineInRange("mana", 100, 0, 10000);
        VOLLEY_SEALS = b.comment("Seals (= arrows)").defineInRange("seals", 24, 1, 128);
        VOLLEY_ARC = b.comment("Arc of the seals behind and to the sides of the caster (degrees)").defineInRange("arcDegrees", 200.0, 10.0, 360.0);
        VOLLEY_SEAL_RADIUS = b.comment("Distance of the seals from the caster (blocks)").defineInRange("sealRadius", 2.5, 0.5, 16.0);
        VOLLEY_RADIUS = b.comment("Enemies within this radius are shot (blocks)").defineInRange("radius", 24.0, 1.0, 128.0);
        VOLLEY_DAMAGE = b.comment("Damage of one arrow").defineInRange("damage", 6.0, 0.0, 10000.0);
        VOLLEY_PER_TARGET = b.comment("Most arrows into one target").defineInRange("perTarget", 6, 1, 128);
        b.pop();
        b.push("sage_barrier");
        BARRIER_CAST = b.comment("Cast time (ticks)").defineInRange("castTicks", 30, 0, 1200);
        BARRIER_COOLDOWN = b.comment("Cooldown (seconds)").defineInRange("cooldown", 40.0, 0.0, 3600.0);
        BARRIER_MANA = b.comment("Mana cost").defineInRange("mana", 120, 0, 10000);
        BARRIER_RADIUS = b.comment("Dome radius (blocks); the dome follows the caster").defineInRange("radius", 5.0, 1.0, 64.0);
        BARRIER_SECONDS = b.comment("Dome lifetime (seconds)").defineInRange("seconds", 8, 1, 3600);
        b.pop();
        b.push("worgan_flame");
        FLAME_CAST = b.comment("Cast time (ticks); the dragon shadow rises during it").defineInRange("castTicks", 40, 0, 1200);
        FLAME_COOLDOWN = b.comment("Cooldown (seconds)").defineInRange("cooldown", 30.0, 0.0, 3600.0);
        FLAME_MANA = b.comment("Mana cost").defineInRange("mana", 150, 0, 10000);
        FLAME_BREATH = b.comment("Breath duration (ticks)").defineInRange("breathTicks", 60, 1, 1200);
        FLAME_CONE = b.comment("Breath cone, full angle (degrees)").defineInRange("coneDegrees", 40.0, 1.0, 180.0);
        FLAME_RANGE = b.comment("Breath length (blocks)").defineInRange("range", 12.0, 1.0, 64.0);
        FLAME_DAMAGE = b.comment("Damage of one breath hit").defineInRange("damage", 3.0, 0.0, 10000.0);
        FLAME_INTERVAL = b.comment("One breath hit per target every this many ticks").defineInRange("hitInterval", 10, 1, 200);
        FLAME_BURN = b.comment("Black flame burning time (seconds); water does not put it out").defineInRange("burnSeconds", 8, 0, 600);
        FLAME_BURN_DPS = b.comment("Black flame damage per second").defineInRange("burnDamagePerSecond", 1.5, 0.0, 10000.0);
        b.pop();
        b.pop();
        SPEC = b.build();
    }

    private ServerConfig() {}
}
