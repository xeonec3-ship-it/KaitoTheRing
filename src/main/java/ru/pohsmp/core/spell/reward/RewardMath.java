package ru.pohsmp.core.spell.reward;

import java.util.List;

/**
 * T34 boss reward spells (docs/specs/tasks/T34_boss_reward_spells.md): pure numbers and geometry, no Minecraft (RewardMathTest).
 * Level tables are the programmer's DRAFT (docs/specs/balance_bosses.md «Наградные заклинания (T34)»), waiting for the manager.
 * Timings marked TEMP_T34 wait for the visual helper's letter (docs/inbox/2026-11-21_mgr_T34_visuals.md).
 */
public final class RewardMath {
    private RewardMath() {}

    /** The six, one per cult boss (T26-T31), in the order of the spec table. */
    public static final String ASHEN_HARVEST = "ashen_harvest", JEALOUS_EMBRACE = "jealous_embrace", ANVIL_STRIKE = "anvil_strike",
            WARLORD_BANNER = "warlord_banner", MIRROR_STEP = "mirror_step", HAND_OF_LIES = "hand_of_lies";
    public static final List<String> ALL = List.of(ASHEN_HARVEST, JEALOUS_EMBRACE, ANVIL_STRIKE, WARLORD_BANNER, MIRROR_STEP, HAND_OF_LIES);

    public static final int MAX_LEVEL = 3;

    /** Value of a per-level table (level 1..3, clamped). */
    public static double at(double[] t, int level) {
        int i = Math.max(1, Math.min(level, t.length)) - 1;
        return t[i];
    }

    public static int ticks(double seconds) {
        return (int) Math.round(seconds * 20);
    }

    // ---------------------------------------------------------------- «Пепельная Жатва» (Глава Культа)
    public static final int ASH_CAST = 16;                       // TEMP_T34
    public static final int ASH_SWING_AT = 0;                    // TEMP_T34: ticks after the cast ends
    public static final double ASH_CD = 18, ASH_RADIUS = 4, ASH_ARC = 150, ASH_TRAIL_SECONDS = 3;
    public static final int ASH_MANA = 50, ASH_MANA_LVL = 10;
    public static final double[] ASH_DAMAGE = {10, 13, 16}, ASH_FIRE = {4, 5, 6}, ASH_TRAIL_DPS = {2, 3, 4};

    // ---------------------------------------------------------------- «Объятия Ревности» (Ирина)
    public static final int EMB_CAST = 10;                       // TEMP_T34
    public static final int EMB_HOOK_AT = 6;                     // TEMP_T34: the hook strikes this many ticks after the pull
    public static final double EMB_CD = 16, EMB_RANGE = 16, EMB_MARK_BONUS = 0.20, EMB_STOP_AT = 1.8;
    public static final int EMB_MANA = 40, EMB_MANA_LVL = 10;
    public static final double[] EMB_DAMAGE = {6, 8, 10}, EMB_MARK = {5, 6, 7};

    // ---------------------------------------------------------------- «Удар Наковальни» (Арис)
    public static final int ANV_CAST = 20;                       // TEMP_T34
    public static final int ANV_FALL = 10;                       // TEMP_T34: the hammer lands this many ticks after the cast ends
    public static final double ANV_CD = 22, ANV_RANGE = 20, ANV_RADIUS = 3, ANV_KNOCK = 0.9, ANV_TEMPER_BONUS = 0.20;
    public static final int ANV_MANA = 60, ANV_MANA_LVL = 10;
    public static final double[] ANV_DAMAGE = {12, 16, 20}, ANV_TEMPER = {15, 20, 25};

    // ---------------------------------------------------------------- «Знамя Полководца» (Мартин)
    public static final int BAN_CAST = 30;                       // TEMP_T34
    public static final int BAN_SOLDIERS_AT = 10;                // TEMP_T34: soldiers rise this many ticks after the banner is planted
    public static final int BAN_SOLDIER_HIT = 8;                 // TEMP_T34: wind-up of a soldier's stab (Martin's soldiers: MartinMath.SOLDIER_HIT)
    public static final int BAN_SOLDIER_VANISH = 16;             // ticks of the vanish animation before removal
    public static final double BAN_CD = 60, BAN_RADIUS = 8;
    public static final int BAN_SOLDIERS = 2, BAN_MANA = 100, BAN_MANA_LVL = 20;
    public static final double[] BAN_SECONDS = {20, 25, 30}, BAN_SOLDIER_HP = {30, 40, 50}, BAN_SOLDIER_DAMAGE = {5, 6, 7};

    // ---------------------------------------------------------------- «Шаг сквозь отражение» (Эреб)
    public static final int MIR_CAST = 8;                        // TEMP_T34
    public static final int MIR_STAB_AT = 3;                     // TEMP_T34: the stab after the reappearing
    public static final double MIR_CD = 14, MIR_RANGE = 16, MIR_BEHIND = 1.2;
    public static final int MIR_MANA = 40, MIR_MANA_LVL = 10;
    public static final double[] MIR_DAMAGE = {9, 12, 15}, MIR_INVIS = {2, 2.5, 3};

    // ---------------------------------------------------------------- «Длань Лжи» (Длань Лжи)
    public static final int HAND_CAST = 14;                      // TEMP_T34
    public static final int HAND_GRAB_AT = 6;                    // TEMP_T34: the hand closes this many ticks after the cast ends
    public static final double HAND_CD = 24, HAND_RANGE = 16, HAND_BONUS = 0.25, HAND_BOSS_SLOW = 2.5;
    public static final int HAND_MANA = 60, HAND_MANA_LVL = 10;
    public static final double[] HAND_HOLD = {2.5, 3, 3.5}, HAND_HOLD_PVP = {1.5, 1.75, 2};

    // ---------------------------------------------------------------- geometry (Minecraft yaw: forward = (-sin yaw, cos yaw))

    /** Is the point (dx, dz) from the caster within radius r and inside the arc (full width, degrees) around the look yaw? */
    public static boolean inSector(double dx, double dz, float yawDeg, double r, double arcDeg) {
        double d2 = dx * dx + dz * dz;
        if (d2 > r * r) return false;
        if (d2 < 0.25) return true;   // standing inside the caster
        double yaw = Math.toRadians(yawDeg);
        double fx = -Math.sin(yaw), fz = Math.cos(yaw);
        double cos = (dx * fx + dz * fz) / Math.sqrt(d2);
        return cos >= Math.cos(Math.toRadians(arcDeg / 2));
    }

    /** Point at distance d behind a body (x, z) facing yawDeg, turned by extraDeg (0 = straight behind). */
    public static double[] behind(double x, double z, float yawDeg, double d, double extraDeg) {
        double yaw = Math.toRadians(yawDeg + extraDeg);
        return new double[] {x + Math.sin(yaw) * d, z - Math.cos(yaw) * d};
    }

    /** Order of the spots tried around the target for «Шаг сквозь отражение»: behind, then the back corners, then the sides. */
    public static final double[] MIR_TRIES = {0, 45, -45, 90, -90};

    /** Yaw (degrees) looking from (x, z) at (tx, tz). */
    public static float yawTo(double x, double z, double tx, double tz) {
        return (float) Math.toDegrees(Math.atan2(-(tx - x), tz - z));
    }

    /**
     * Horizontal speed of a pull that stops a target about EMB_STOP_AT blocks from the caster: ground friction keeps ~0.546 of the
     * speed each tick, so the whole slide is ~2.2 × the start speed. Never above 3 blocks/tick.
     */
    public static double pullSpeed(double dist) {
        return Math.max(0, Math.min(3.0, (dist - EMB_STOP_AT) / 2.2));
    }

    /** All the bonus multipliers of one hit: each active bonus adds its share (1 + a)(1 + b)... */
    public static double mult(double... bonuses) {
        double m = 1;
        for (double b : bonuses) m *= 1 + b;
        return m;
    }

    /** Mana cost of a level (Iron's: base + perLevel × (level - 1)). */
    public static int mana(int base, int perLevel, int level) {
        return base + perLevel * (Math.max(1, level) - 1);
    }
}
