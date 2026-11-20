package ru.pohsmp.core.boss.martin;

/**
 * Pure numbers of T29 «Мартин, Последний Полководец» (no Minecraft classes; MartinMathTest): the ticks of his animations and scenes
 * (docs/inbox/2026-11-20_mgr_T29_visuals.md, events × 20), the cavalry formula of fx martin_cavalry_lane, the shield wall, the arcs.
 * Directions as in the fx system (FxMath): forward of yaw = (−sin, 0, cos), right = (−cos, 0, −sin).
 */
public final class MartinMath {
    private MartinMath() {}

    // ---------------------------------------------------------------- scenes

    /** Intro (martin_spawn 6.5 s): look 1.0, rise 2.6, pull 4.0, salute 5.0; title + music 5.4 s, bar 6.5 s. */
    public static final int INTRO = 130, INTRO_LOOK = 20, INTRO_RISE = 52, INTRO_PULL = 80, INTRO_SALUTE = 100, INTRO_TITLE = 108,
            INTRO_TITLE_HOLD = 42;

    /** «Атака конницы»: martin_cavalry 3.4 s (call 1.0, charge 2.0); the lanes start on call, riders 40 ticks later; scene to 4.1 s. */
    public static final int CAV_ANIM = 68, CAV_TITLE = 6, CAV_CALL = 20, CAV_CHARGE = 40, CAV_SCENE = 82, LANE_FX = 72, LANE_WARN = 40,
            RIDERS = 3, RIDER_TICKS = 28, LANE_LENGTH = 40;
    public static final double LANE_HALF = 1.5, RIDER_REACH = 1.5;

    /** «Приказ стоять насмерть»: martin_hold_the_line 2.5 s (shield_draw 0.15, wall 1.1), then martin_hold_loop, martin_hold_end 0.8 s. */
    public static final int HOLD_TITLE = 6, HOLD_WALL = 22, HOLD_SCENE = 50, HOLD_END_ANIM = 16;

    /** Surrender: martin_block_yield (block 0.2, lower 1.2, speak 2.4) → martin_to_npc at 4.4 s (1.2 s) → NPC; camera back at 5.0 s. */
    public static final int YIELD_BLOCK = 4, YIELD_LOWER = 24, YIELD_SPEAK = 48, YIELD_TO_NPC = 88, YIELD_CAM = 100, YIELD_END = 112,
            YIELD_WAIT = 200;

    /** Phase 2: martin_phase2 3 s (roar 1.4); at 2.4 s martin_banner_plant (plant 1.3 → 3.7 s of the transition). */
    public static final int P2_ANIM = 60, P2_ROAR = 28, P2_PLANT_ANIM = 48, P2_PLANT = 48 + 26, P2_LOCK = 48 + 48;
    /** Banner planted later (a replant): martin_banner_plant alone. */
    public static final int PLANT_ANIM = 48, PLANT_AT = 26;
    /** Phase 3: martin_phase3 3.2 s (kneel 0.8, spin 1.4, roar 2.0). */
    public static final int P3_ANIM = 64, P3_ROAR = 40;

    // ---------------------------------------------------------------- melee and the four spells (length, event)

    public static final int SWING = 32, SWING_SWING = 12, SWING_HIT = 15, OVERHEAD = 40, OVERHEAD_SWING = 16, OVERHEAD_HIT = 19, THRUST = 28, THRUST_HIT = 12;
    public static final int BASH = 30, BASH_DASH = 9, BASH_HIT = 15;
    public static final int COMMAND = 44, COMMAND_AT = 17;
    public static final int WALL_ANIM = 40, WALL_SLAM = 20, WALL_RISE = 20, WALL_MOVE = 160, WALL_FX = 200;
    public static final double WALL_TRAVEL = 18, WALL_HALF_WIDTH = 12, WALL_DEPTH = 0.8, GAP_HALF = 0.8;
    /** Centres of the gaps of mesh martin_shield_line (x to the right of the wall's yaw). */
    public static final double[] WALL_GAPS = {-6.24, 0.32, 6.88};
    public static final int VOLLEY = 44, VOLLEY_DRAW = 16, VOLLEY_LOOSE = 24, VOLLEY_IMPACT = 30, VOLLEY_MARK_FX = 60;
    public static final int DUEL = 40, DUEL_CHALLENGE = 18;
    public static final int WARCRY = 36, WARCRY_CRY = 12;
    /** martin_replica_break 2.4 s: block 0.4, slash 0.9, break 1.35, speak 1.7. */
    public static final int REPLICA_DELAY = 40, REPLICA_BLOCK = 8, REPLICA_SLASH = 18, REPLICA_BREAK = 27, REPLICA_SPEAK = 34, REPLICA_ANIM = 48;
    /** Soldier: attack 1.0 s (hit 0.45), spawn fx → the entity on tick 4, vanish 0.8 s. */
    public static final int SOLDIER_ATTACK = 20, SOLDIER_HIT = 9, SOLDIER_SPAWN_AT = 4, SOLDIER_VANISH = 16;
    /** Banner cut: removed 2 s later. */
    public static final int BANNER_GONE = 40;

    /**
     * Finisher (owner 20.11, ТЗ «Добивание»; provisional until martin_finisher arrives, 2.5 s): the victim is drawn 3.2 before him and
     * pierced (0.4 s), lifted on the blade, raised over his head (0.8–1.5 s), thrown to his feet (1.7–2.0 s, the soldiers slam their
     * shields), dies at 2.3 s. Its camera: 2 s from 0.2 s.
     */
    public static final int FINISHER = 50, FINISHER_KILL = 46, FINISHER_PIERCE = 8, FINISHER_RAISE = 16, FINISHER_RAISED = 30,
            FINISHER_THROW = 34, FINISHER_SLAM = 40, FINISHER_CAM_FROM = 4, FINISHER_CAM = 40;

    /**
     * Where the finisher holds the victim at tick t: {pull (0..1 from where it was hit to the hold line), blocks in front of him,
     * height above his feet}.
     */
    public static double[] finisherHold(int t) {
        double pull = Math.min(1, t / (double) FINISHER_PIERCE);
        pull *= pull;
        double f, up;
        if (t <= FINISHER_RAISE) {
            f = 3.2;
            up = t <= FINISHER_PIERCE ? 0 : 1.6 * ease((t - FINISHER_PIERCE) / (double) (FINISHER_RAISE - FINISHER_PIERCE));
        } else if (t <= FINISHER_RAISED) {
            double k = ease((t - FINISHER_RAISE) / (double) (FINISHER_RAISED - FINISHER_RAISE));
            f = 3.2 - 2.6 * k;
            up = 1.6 + 3.2 * k;
        } else if (t <= FINISHER_THROW) {
            f = 0.6;
            up = 4.8;
        } else if (t <= FINISHER_SLAM) {
            double k = (t - FINISHER_THROW) / (double) (FINISHER_SLAM - FINISHER_THROW);
            f = 0.6 + 1.6 * k;
            up = 4.8 * (1 - k * k);
        } else {
            f = 2.2;
            up = 0;
        }
        return new double[] {pull, f, up};
    }

    private static double ease(double u) {
        u = Math.max(0, Math.min(1, u));
        return 0.5 - 0.5 * Math.cos(Math.PI * u);
    }

    // ---------------------------------------------------------------- counts

    /** Soldiers in the line: base + players, at most max. */
    public static int soldiers(int players, int base, int max) {
        return Math.max(0, Math.min(max, base + Math.max(1, players)));
    }

    /** Cavalry lanes: base + (N ≥ 4) + (N ≥ 6). */
    public static int lanes(int players, int base) {
        return base + (players >= 4 ? 1 : 0) + (players >= 6 ? 1 : 0);
    }

    /** Arrow marks: base + players, at most max. */
    public static int volleyMarks(int players, int base, int max) {
        return Math.max(1, Math.min(max, base + Math.max(1, players)));
    }

    // ---------------------------------------------------------------- cavalry (fx martin_cavalry_lane)

    /**
     * Where rider k (0..2) stands along the lane at tick t of the lane fx (blocks from the lane start along its yaw), or NaN when it
     * is not on the lane: rider k leaves on tick 40 + 2k, z = −4 − 3.2k + 52·(t − 40 − 2k)/28.
     */
    public static double riderZ(int k, double t) {
        double s = t - LANE_WARN - 2 * k;
        if (s < 0 || s > RIDER_TICKS) return Double.NaN;
        return -4 - 3.2 * k + 52 * s / RIDER_TICKS;
    }

    /** True if a player at (x right, z forward) of the lane start is hit by any rider at tick t of the lane. */
    public static boolean laneHit(double x, double z, double t) {
        if (Math.abs(x) >= LANE_HALF) return false;
        for (int k = 0; k < RIDERS; k++) {
            double rz = riderZ(k, t);
            if (!Double.isNaN(rz) && Math.abs(z - rz) < RIDER_REACH) return true;
        }
        return false;
    }

    // ---------------------------------------------------------------- shield wall (fx martin_shield_wall)

    /** Where the wall is (blocks forward of its start) t ticks after the slam: rises 0..20, then 18 blocks in 160 ticks. */
    public static double wallZ(double t) {
        if (t <= WALL_RISE) return 0;
        return WALL_TRAVEL * Math.min(1, (t - WALL_RISE) / WALL_MOVE);
    }

    public static boolean inGap(double x) {
        for (double g : WALL_GAPS) if (Math.abs(x - g) < GAP_HALF) return true;
        return false;
    }

    /** Pushed by the wall: just in front of it (0 < z − wall < 0.8), within its width and not in a gap. */
    public static boolean wallPushes(double x, double z, double wall) {
        double d = z - wall;
        return d > 0 && d < WALL_DEPTH && Math.abs(x) < WALL_HALF_WIDTH && !inGap(x);
    }

    // ---------------------------------------------------------------- geometry

    /** Local coordinates of (px, pz) from origin (ox, oz) for a yaw: {x right, z forward}. */
    public static double[] local(double ox, double oz, float yawDeg, double px, double pz) {
        double a = Math.toRadians(yawDeg), dx = px - ox, dz = pz - oz;
        double fx = -Math.sin(a), fz = Math.cos(a), rx = -Math.cos(a), rz = -Math.sin(a);
        return new double[] {dx * rx + dz * rz, dx * fx + dz * fz};
    }

    /** True if direction (dx, dz) from someone facing yawDeg lies within the arc (full degrees) in front of them. */
    public static boolean inFront(float yawDeg, double dx, double dz, double arcDeg) {
        double len = Math.sqrt(dx * dx + dz * dz);
        if (len < 1e-6) return true;
        double a = Math.toRadians(yawDeg);
        double cos = (-Math.sin(a) * dx + Math.cos(a) * dz) / len;
        return cos >= Math.cos(Math.toRadians(arcDeg / 2));
    }

    /**
     * «Строй»: does a soldier at (sx, sz) stand on the line from the attacker (ax, az) to Martin (bx, bz), between them, within
     * width of it.
     */
    public static boolean blocksLine(double ax, double az, double bx, double bz, double sx, double sz, double width) {
        double vx = bx - ax, vz = bz - az, l2 = vx * vx + vz * vz;
        if (l2 < 1e-6) return false;
        double t = ((sx - ax) * vx + (sz - az) * vz) / l2;
        if (t <= 0.02 || t >= 0.98) return false;
        double cx = ax + vx * t - sx, cz = az + vz * t - sz;
        return cx * cx + cz * cz <= width * width;
    }
}
