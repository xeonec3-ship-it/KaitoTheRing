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
    // Silent Witch outfit (T19)
    public static final ForgeConfigSpec.DoubleValue SW_CAST, SW_CAST_SILENT, SW_MANA_ROBE, SW_MANA_HOOD, SW_REGEN, SW_RESIST, SW_RESIST_SILENT,
            SW_GATE_BONUS;
    public static final ForgeConfigSpec.BooleanValue SW_MUTE_CHANT, SW_SILENT_STEPS, SW_NO_VIBRATIONS, SW_TEAM, SW_GATE_MAGIC_IMMUNE;
    public static final ForgeConfigSpec.IntValue SW_BARRIER_COOLDOWN, SW_BARRIER_INVUL, SW_STEALTH_RANGE, SW_EXPOSE_SECONDS;
    public static final ForgeConfigSpec.ConfigValue<String> SW_GATE_SPELL;

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
        b.comment("Silent Witch outfit: hood, robe, robe skirt (T19)").push("silent_witch");
        SW_CAST = b.comment("1. Robe: cast time reduction for every spell (Iron's cast_time_reduction)").defineInRange("castTimeReduction", 0.15, 0.0, 0.9);
        SW_CAST_SILENT = b.comment("1. Robe: total cast time reduction for spells of the Silent school (includes castTimeReduction)").defineInRange("silentCastTimeReduction", 0.25, 0.0, 0.9);
        SW_MUTE_CHANT = b.comment("1. Robe: spells with spoken lines (Replica, Explosion) do not write them to chat").define("muteChants", true);
        SW_MANA_ROBE = b.comment("2. Robe: max mana").defineInRange("maxManaRobe", 100.0, 0.0, 10000.0);
        SW_MANA_HOOD = b.comment("2. Hood: max mana").defineInRange("maxManaHood", 100.0, 0.0, 10000.0);
        SW_REGEN = b.comment("2. Robe + hood: mana regeneration bonus, split equally between the two").defineInRange("manaRegen", 0.25, 0.0, 10.0);
        SW_RESIST = b.comment("3. Skirt + hood: magic resistance (Iron's spell_resist), split equally").defineInRange("spellResist", 0.15, 0.0, 10.0);
        SW_RESIST_SILENT = b.comment("3. Skirt + hood: Silent magic resistance, split equally").defineInRange("silentResist", 0.30, 0.0, 10.0);
        SW_BARRIER_COOLDOWN = b.comment("4. Full set: lethal damage leaves 1 health once per this many seconds").defineInRange("barrierCooldownSeconds", 600, 1, 86400);
        SW_BARRIER_INVUL = b.comment("4. Invulnerability after the barrier saves the wearer (seconds)").defineInRange("barrierInvulnerableSeconds", 3, 0, 60);
        SW_SILENT_STEPS = b.comment("5. Skirt: no step, jump, landing or swim sounds from the wearer").define("silentSteps", true);
        SW_NO_VIBRATIONS = b.comment("5. Skirt: the wearer makes no vibrations (sculk sensors, shriekers, the Warden)").define("noVibrations", true);
        SW_STEALTH_RANGE = b.comment("6. Hood: mobs farther than this do not notice the wearer").defineInRange("stealthRange", 12, 0, 256);
        SW_EXPOSE_SECONDS = b.comment("6. After the wearer attacks or casts, mobs see them normally for this long (seconds)").defineInRange("exposeSeconds", 10, 0, 600);
        SW_TEAM = b.comment("6/11. Also put the wearer in a scoreboard team with nameTagVisibility=never so clients without the mod do not draw the name",
                "(only when the player is in no other team)").define("nameTagTeam", true);
        SW_GATE_SPELL = b.comment("10. The Gate spell id (cast only in the full outfit)").define("gateSpell", "pohsmp_core:silent_gate");
        SW_GATE_BONUS = b.comment("10. Full set: Gate beams deal this much more damage").defineInRange("gateDamageBonus", 0.20, 0.0, 10.0);
        SW_GATE_MAGIC_IMMUNE = b.comment("10. Full set: no magic damage while casting the Gate").define("gateMagicImmune", true);
        b.pop();
        SPEC = b.build();
    }

    private ServerConfig() {}

    /** Value of a server config option, or its default while the config is not loaded (main menu, early tooltips). */
    public static <T> T get(ForgeConfigSpec.ConfigValue<T> v) {
        try {
            return v.get();
        } catch (IllegalStateException e) {
            return v.getDefault();
        }
    }
}
