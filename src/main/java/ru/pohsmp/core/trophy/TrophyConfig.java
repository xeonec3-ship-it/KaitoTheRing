package ru.pohsmp.core.trophy;

import net.minecraftforge.common.ForgeConfigSpec;

/** T35 boss armor: set bonuses and the mantle/mask (pohsmp_core-boss_armor-server.toml). Draft numbers: balance_bosses.md «Броня боссов (T35)». */
public final class TrophyConfig {
    private TrophyConfig() {}

    public static final ForgeConfigSpec SPEC;
    public static final ForgeConfigSpec.DoubleValue REFLECT_SHARE, REFLECT_CAP, SMITH_WEAPON, SMITH_BOSS_KNOCKBACK, WARLORD_THRESHOLD, WARLORD_CUT,
            WARLORD_RADIUS, DASH_MIN, DASH_MAX, MASK_CHANCE, MANTLE_WORLD_FIRE;
    public static final ForgeConfigSpec.IntValue WARLORD_TICKS, WARLORD_COOLDOWN, TRAITOR_TICKS, TRAITOR_COOLDOWN, MASK_TICKS, MASK_COOLDOWN, MASK_RADIUS;
    public static final ForgeConfigSpec.BooleanValue SET_PARTICLES, NO_ANVIL;

    static {
        ForgeConfigSpec.Builder b = new ForgeConfigSpec.Builder();
        b.comment("T35: boss armor (admin-only). Piece attributes are in code (TrophySet), these are the set bonuses.").push("boss_armor");
        SET_PARTICLES = b.comment("A full set shows its sign (particles of the boss's colour) around the wearer").define("setParticles", true);
        NO_ANVIL = b.comment("No repair on the anvil by combining two pieces (Mending still works)").define("noAnvilRepair", true);
        b.push("jealous");
        REFLECT_SHARE = b.comment("Jealous Attire: share of a hit given back to the attacker by the threads").defineInRange("reflectShare", 0.10, 0.0, 1.0);
        REFLECT_CAP = b.comment("Most damage given back by one hit").defineInRange("reflectCap", 20.0, 0.0, 1000.0);
        b.pop();
        b.push("smith");
        SMITH_WEAPON = b.comment("Smith's Plate: weapon (melee) damage bonus").defineInRange("weaponBonus", 0.10, 0.0, 2.0);
        SMITH_BOSS_KNOCKBACK = b.comment("Knockback immunity: a cult boss still pushes the wearer this much (1 = fully, 0 = not at all)")
                .defineInRange("bossKnockback", 0.5, 0.0, 1.0);
        b.pop();
        b.push("warlord");
        WARLORD_THRESHOLD = b.comment("«Стоять насмерть» starts on a hit that leaves the wearer under this share of max health").defineInRange("threshold", 0.30, 0.0, 1.0);
        WARLORD_CUT = b.comment("Damage taken during it is multiplied by this").defineInRange("damageMult", 0.5, 0.0, 1.0);
        WARLORD_TICKS = b.comment("How long it lasts, ticks").defineInRange("ticks", 60, 1, 1200);
        WARLORD_COOLDOWN = b.comment("Cooldown, ticks (2 min)").defineInRange("cooldown", 2400, 0, 72000);
        WARLORD_RADIUS = b.comment("Allies (players) within this radius get Resistance I").defineInRange("auraRadius", 8.0, 0.0, 64.0);
        b.pop();
        b.push("traitor");
        DASH_MIN = b.comment("A dash/roll: horizontal speed of at least this many blocks per tick").defineInRange("dashMinSpeed", 0.75, 0.1, 10.0);
        DASH_MAX = b.comment("...and at most this (faster = a teleport, not counted)").defineInRange("dashMaxSpeed", 6.0, 0.1, 100.0);
        TRAITOR_TICKS = b.comment("Invisibility after a dash, ticks").defineInRange("invisTicks", 20, 1, 400);
        TRAITOR_COOLDOWN = b.comment("Cooldown, ticks (20 s)").defineInRange("cooldown", 400, 0, 72000);
        b.pop();
        b.push("cult_mantle");
        MANTLE_WORLD_FIRE = b.comment("Cult Head's Mantle: fire and lava damage without an attacker is multiplied by this").defineInRange("worldFireMult", 0.5, 0.0, 1.0);
        b.pop();
        b.push("mask_of_lies");
        MASK_CHANCE = b.comment("Mask of Lies: chance to leave an illusory double when hurt").defineInRange("chance", 0.15, 0.0, 1.0);
        MASK_TICKS = b.comment("The double lives this long, ticks").defineInRange("ticks", 40, 1, 400);
        MASK_COOLDOWN = b.comment("At most one double per this many ticks").defineInRange("cooldown", 160, 0, 72000);
        MASK_RADIUS = b.comment("Mobs within this radius that hunt the wearer go for the double instead (not cult bosses)").defineInRange("radius", 16, 0, 64);
        b.pop();
        b.pop();
        SPEC = b.build();
    }

    public static <T> T get(ForgeConfigSpec.ConfigValue<T> v) {
        try {
            return v.get();
        } catch (IllegalStateException e) {
            return v.getDefault();
        }
    }
}
