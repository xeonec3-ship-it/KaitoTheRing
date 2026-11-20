package ru.pohsmp.core.boss.ereb;

import net.minecraftforge.common.ForgeConfigSpec;

/**
 * T30 Ereb: the mechanics keys of [ereb] in pohsmp_core-bosses-server.toml (docs/specs/balance_bosses.md, section 6). The body (hp,
 * armour, speed, attack, resists, arena) is the framework's own PerBoss; these keys are defined right after it, inside the same
 * section, by one line in BossConfig: {@code ru.pohsmp.core.boss.ereb.ErebConfig.define(b);}.
 */
public final class ErebConfig {
    private ErebConfig() {}

    public static ForgeConfigSpec.DoubleValue RAPIER_DAMAGE, SHARD_DAMAGE, COPIES_DAMAGE, BETRAYAL_FRIENDLY_MULT, FALSE_ALLY_DAMAGE, LABYRINTH_RADIUS,
            LABYRINTH_WALL_DAMAGE, BLADE_DANCE_DAMAGE, FEINT_COUNTER_DAMAGE, GLASS_RAIN_RADIUS, GLASS_RAIN_DAMAGE, MIRROR_STEP_DAMAGE, VEIL_RADIUS;
    public static ForgeConfigSpec.IntValue MELEE_MIN, MELEE_MAX, SHARDS_COUNT, SHARDS_PER_TARGET, SHARDS_COOLDOWN, MIRROR_IMAGES_INTERVAL,
            PHANTOM_PAIN_INTERVAL, FALSE_STEP_INTERVAL, DISGUISE_SECONDS, DISGUISE_INTERVAL, VEIL_SECONDS, VEIL_INTERVAL, BETRAYAL_SECONDS,
            BETRAYAL_INTERVAL, LABYRINTH_SECONDS, BLADE_DANCE_COOLDOWN, FEINT_COOLDOWN, GLASS_RAIN_PER_PLAYER, GLASS_RAIN_MAX, GLASS_RAIN_COOLDOWN,
            MIRROR_STEP_COOLDOWN, FINALE_DREAM_SECONDS;
    public static ForgeConfigSpec.BooleanValue ILLUSION_IMMUNE;

    /** Called from BossConfig's static block between push("ereb") and pop(). */
    public static void define(ForgeConfigSpec.Builder b) {
        RAPIER_DAMAGE = b.comment("Added to attack_damage (the rapier): a thrust = attack_damage + rapier_damage").defineInRange("rapier_damage", 8.0, 0, 1000);
        MELEE_MIN = b.comment("Ticks between his rapier attacks").defineInRange("melee_interval_min", 8, 1, 200);
        MELEE_MAX = b.defineInRange("melee_interval_max", 16, 1, 200);
        SHARDS_COUNT = b.comment("Magic by hand: a fan of glass shards (projectiles, no line to the target)").defineInRange("shards_count", 7, 1, 32);
        SHARD_DAMAGE = b.defineInRange("shard_damage", 9.0, 0, 1000);
        SHARDS_PER_TARGET = b.comment("Shards of one fan that may hit the same target").defineInRange("shards_per_target", 3, 1, 32);
        SHARDS_COOLDOWN = b.comment("Seconds between two fans").defineInRange("shards_cooldown", 5, 1, 600);
        ILLUSION_IMMUNE = b.comment("Immune to the Illusions school (damage and marks)").define("illusion_immune", true);

        COPIES_DAMAGE = b.comment("Phase 1 «Две правды»: «Отражения» (3 copies, the rest from [illusion.mirror_images]); a copy's illusory thrust")
                .defineInRange("copies_damage", 6.0, 0, 1000);
        MIRROR_IMAGES_INTERVAL = b.comment("New copies at most this often (seconds), when the old ones are gone").defineInRange("mirror_images_interval", 30, 5, 600);
        PHANTOM_PAIN_INTERVAL = b.comment("«Фантомная боль» on a player every N seconds (the T22 spell)").defineInRange("phantom_pain_interval", 20, 2, 600);
        FALSE_STEP_INTERVAL = b.comment("«Ложный шаг» every N seconds").defineInRange("false_step_interval", 12, 2, 600);
        DISGUISE_SECONDS = b.comment("Phase 2 «Чужое лицо»: a participant's look up to this long, or until his attack").defineInRange("disguise_seconds", 20, 1, 600);
        DISGUISE_INTERVAL = b.defineInRange("disguise_interval", 25, 2, 600);
        VEIL_RADIUS = b.comment("«Пелена»: radius, seconds, how often").defineInRange("veil_radius", 6.0, 1, 64);
        VEIL_SECONDS = b.defineInRange("veil_seconds", 10, 1, 600);
        VEIL_INTERVAL = b.defineInRange("veil_interval", 22, 2, 600);
        BETRAYAL_SECONDS = b.comment("Phase 3 «Предательство»: the allies look like him this long, every N s; a hit on such an ally x mult")
                .defineInRange("betrayal_seconds", 6, 1, 120);
        BETRAYAL_INTERVAL = b.defineInRange("betrayal_interval", 30, 5, 600);
        BETRAYAL_FRIENDLY_MULT = b.defineInRange("betrayal_friendly_mult", 1.0, 0, 10);
        FALSE_ALLY_DAMAGE = b.comment("Special «Ложный союзник» (at 50%): the stab in the back").defineInRange("false_ally_damage", 55.0, 0, 1000);
        LABYRINTH_RADIUS = b.comment("Special «Зеркальный лабиринт» (at 20%) over the arena").defineInRange("labyrinth_radius", 24.0, 2, 64);
        LABYRINTH_SECONDS = b.defineInRange("labyrinth_seconds", 20, 1, 600);
        LABYRINTH_WALL_DAMAGE = b.defineInRange("labyrinth_wall_damage", 6.0, 0, 1000);

        BLADE_DANCE_DAMAGE = b.comment("«Танец клинков»: 4 thrusts, each at another player").defineInRange("blade_dance_damage", 22.0, 0, 1000);
        BLADE_DANCE_COOLDOWN = b.defineInRange("blade_dance_cooldown", 18, 1, 600);
        FEINT_COUNTER_DAMAGE = b.comment("«Обманная брешь»: whoever strikes in the 1.5 s window is parried and countered").defineInRange("feint_counter_damage", 40.0, 0, 1000);
        FEINT_COOLDOWN = b.defineInRange("feint_cooldown", 20, 1, 600);
        GLASS_RAIN_PER_PLAYER = b.comment("«Стеклянный дождь»: marks per player (at most glass_rain_max), radius, damage 1.2 s after the marks")
                .defineInRange("glass_rain_per_player", 2, 1, 16);
        GLASS_RAIN_MAX = b.defineInRange("glass_rain_max", 10, 1, 64);
        GLASS_RAIN_RADIUS = b.defineInRange("glass_rain_radius", 2.0, 0.5, 16);
        GLASS_RAIN_DAMAGE = b.defineInRange("glass_rain_damage", 26.0, 0, 1000);
        GLASS_RAIN_COOLDOWN = b.defineInRange("glass_rain_cooldown", 14, 1, 600);
        MIRROR_STEP_DAMAGE = b.comment("«Шаг сквозь отражение»: a thrust in the back of another player after a 0.6 s glint").defineInRange("mirror_step_damage", 32.0, 0, 1000);
        MIRROR_STEP_COOLDOWN = b.defineInRange("mirror_step_cooldown", 12, 1, 600);
        FINALE_DREAM_SECONDS = b.comment("The finale (5%): «Сон бабочки» on every player of the fight, arena radius, this long; then he is gone")
                .defineInRange("finale_dream_seconds", 120, 1, 600);
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
