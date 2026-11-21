package ru.pohsmp.core.boss.aris;

/**
 * T28 «Арис, Мифический Кузнец»: timings (ticks, from the animation events of animations/entity/aris.animation.json and the plans of
 * docs/specs/tasks/T28_aris_boss.md «Визуал и ролики») and pure geometry of her attacks. No Minecraft classes (ArisMathTest).
 */
public final class ArisMath {
    private ArisMath() {}

    // ---------------------------------------------------------------- texture states (textures/entity/aris/<name>.png + _glowmask)

    public static final int TEX_BASE = 0, TEX_DIM = 1, TEX_SPENT = 2, TEX_MYTHIC = 3;
    private static final String[] TEX = {"aris", "aris_dim", "aris_spent", "aris_mythic"};

    public static String texture(int state) {
        return TEX[state < 0 || state >= TEX.length ? 0 : state];
    }

    // ---------------------------------------------------------------- animations (index = synced action id; 0 = none)

    /** Animation names (animation.aris.<name>) and their lengths in ticks. */
    public static final String[] ANIMS = {"", "slam", "swing", "cast", "forge", "last_blow", "phase2", "phase3", "spawn", "surrender",
            "billet", "chains", "quench", "bellows", "replica_break", "finisher", "guard_break"};
    /** guard_break 36: T32 visuals (docs/inbox/2026-11-21_mgr_guard_break_visuals.md): warn tick 2, hit tick 14, length 36. */
    public static final int[] ANIM_TICKS = {0, 44, 42, 32, 80, 100, 40, 60, 180, 100, 28, 32, 36, 30, 40, 48, 36};

    public static int anim(String name) {
        for (int i = 1; i < ANIMS.length; i++) if (ANIMS[i].equals(name)) return i;
        return 0;
    }

    // ---------------------------------------------------------------- intro (9.0 s)

    public static final int INTRO = 180, INTRO_DIM = 90, INTRO_HORNS = 120, INTRO_IMPACT = 140, INTRO_TITLE = 150, INTRO_TITLE_HOLD = 30,
            INTRO_SPAWN_SOUND = 40;
    public static final int[] INTRO_KNOCKS = {12, 24, 36};

    /** Texture of the intro at tick t: 0–4.5 s spent, 4.5 dim, 6.0 (horns) the fighting one. */
    public static int introTexture(int t) {
        return t < INTRO_DIM ? TEX_SPENT : t < INTRO_HORNS ? TEX_DIM : TEX_BASE;
    }

    // ---------------------------------------------------------------- melee and phase 1

    public static final int SWING = 42, SWING_HIT = 12;
    public static final double SWING_REACH = 3.6;
    public static final int SLAM = 44, SLAM_IMPACT = 15, SLAM_WAVE = 22;
    /** The hammer head touches the ground this far before her (slam / forge / last_blow). */
    public static final double SLAM_FWD = 1.35, FORGE_FWD = 1.2, LAST_FWD = 1.45;   // visual letter «Правка направлений» 20.11
    public static final double SLAM_RADIUS = 8, SLAM_BAND = 0.7, JUMP_CLEAR = 1.0;

    /** Radius of the molten ring t ticks after the impact (0..8 over 22 ticks). */
    public static double slamRadius(int t) {
        return SLAM_RADIUS * Math.max(0, Math.min(t, SLAM_WAVE)) / SLAM_WAVE;
    }

    /** The ring hits at horizontal distance d at tick t (a player more than 1 block over the ground jumps it). */
    public static boolean slamHits(double d, int t, double aboveGround) {
        if (t < 0 || t > SLAM_WAVE || aboveGround > JUMP_CLEAR) return false;
        return Math.abs(d - slamRadius(t)) < SLAM_BAND;
    }

    /** «Веер металла»: 5 crests 2..10 blocks ahead, one every 2 ticks after the impact; band width 3. */
    public static final int WAVE_CRESTS = 5, WAVE_STEP = 2;
    public static final double WAVE_SPACING = 2, WAVE_WIDTH = 3;

    /** Index (1..5) of the crest that rises at tick t after the impact, or 0. */
    public static int crestAt(int t) {
        if (t < 0 || t % WAVE_STEP != 0) return 0;
        int k = t / WAVE_STEP + 1;
        return k <= WAVE_CRESTS ? k : 0;
    }

    /** A crest k (distance 2k) touches a point at (forward, side) from her: within 1 block along, within width/2 across. */
    public static boolean crestHits(int k, double forward, double side) {
        return k > 0 && Math.abs(forward - k * WAVE_SPACING) <= 1.0 && Math.abs(side) <= WAVE_WIDTH / 2;
    }

    // ---------------------------------------------------------------- anvils

    public static final int CAST = 32, CAST_AT = 16, ANVIL_GROW = 12;
    /** Collision of an anvil: long side 2.6, height 1.6, short side 1.2 (visual letter). */
    public static final double ANVIL_LONG = 2.6, ANVIL_HEIGHT = 1.6, ANVIL_SHORT = 1.2;

    public static int anvilCount(int players, int small, int big) {
        return players >= 4 ? big : small;
    }

    /** Height of the anvil's box while it grows (age in ticks). */
    public static double anvilHeight(int age) {
        return ANVIL_HEIGHT * Math.max(0, Math.min(age, ANVIL_GROW)) / ANVIL_GROW;
    }

    /** Is the segment a→b (on the ground plane) blocked by a box of half sizes hx, hz around (cx, cz)? (cover from «Мехи», billets) */
    public static boolean segmentHitsBox(double ax, double az, double bx, double bz, double cx, double cz, double hx, double hz) {
        double t0 = 0, t1 = 1, dx = bx - ax, dz = bz - az;
        double[] p = {-dx, dx, -dz, dz};
        double[] q = {ax - (cx - hx), (cx + hx) - ax, az - (cz - hz), (cz + hz) - az};
        for (int i = 0; i < 4; i++) {
            if (Math.abs(p[i]) < 1e-9) {
                if (q[i] < 0) return false;
                continue;
            }
            double r = q[i] / p[i];
            if (p[i] < 0) t0 = Math.max(t0, r);
            else t1 = Math.min(t1, r);
            if (t0 > t1) return false;
        }
        return true;
    }

    // ---------------------------------------------------------------- phase 2: blades

    public static final int BLADES_FX = 40;
    public static final int[] BLADE_TICKS = {20, 26, 32};
    public static final double BLADE_ORBIT_R = 3.2, BLADE_ORBIT_H = 2.6;
    /** A blade aims (stops, turns to its target) this long before it darts, and darts at most this long. */
    public static final int BLADE_AIM = 12, BLADE_DART = 16;
    public static final double BLADE_SPEED = 1.1;

    /** Where blade i of n circles round her at tick t: angle in radians (one turn in 8 s). */
    public static double bladeAngle(int i, int n, long t) {
        return 2 * Math.PI * i / Math.max(1, n) + t * (2 * Math.PI / 160.0);
    }

    // ---------------------------------------------------------------- specials

    public static final int FORGE = 80, FORGE_FX = 6, FORGE_TITLE = 6, FORGE_TITLE_HOLD = 50, FORGE_IGNITE = 66;
    public static final int[] FORGE_STRIKES = {20, 36, 52};
    /** fx aris_forge ticks: 0–60 warning, 60–260 the floor burns, 260–300 cools. */
    public static final int FORGE_FLOOR_FROM = 60, FORGE_FLOOR_TO = 260, FORGE_FX_LEN = 300;
    public static final double ISLAND_R = 2.2;

    public static int islandCount(int players, int min, int max) {
        int n = Math.max(min, 2 + (players + 1) / 2);
        return Math.max(1, Math.min(max, n));
    }

    /**
     * Island centres (x, z offsets from the arena centre): evenly round the arena, turned by rot radians, alternating 9 and 15 blocks
     * from the centre (inside r24, never in the middle where she stands), scaled for small arenas.
     */
    public static double[][] islandOffsets(int n, double rot, double arenaR) {
        double[][] out = new double[n][2];
        double k = Math.min(1, arenaR / 24.0);
        for (int i = 0; i < n; i++) {
            double a = rot + 2 * Math.PI * i / n, r = (i % 2 == 0 ? 9 : 15) * k;
            out[i][0] = Math.cos(a) * r;
            out[i][1] = Math.sin(a) * r;
        }
        return out;
    }

    public static final int LAST = 100, LAST_TITLE = 6, LAST_TITLE_HOLD = 50, LAST_PEAK = 62, LAST_FALL = 70, LAST_BLOW = 80;

    /** «Последний удар молота»: centre → edge linearly inside r, nothing outside. */
    public static double lastBlowDamage(double d, double r, double center, double edge) {
        if (d > r || r <= 0) return 0;
        return center + (edge - center) * Math.max(0, d) / r;
    }

    // ---------------------------------------------------------------- phase transitions, surrender

    public static final int PHASE2 = 40, PHASE2_ROAR = 20, PHASE3 = 60, PHASE3_IGNITE = 32;

    public static final int SURRENDER = 100, SURRENDER_STAGGER = 8, SURRENDER_PLANT = 24, SURRENDER_HAMMER_DROP = 64, SURRENDER_SPEAK = 72,
            SURRENDER_SUBTITLE = 80;

    /** Texture of the surrender scene at tick t (letter T28 visuals §2): the horns flicker 2.0–2.6 s, then go out. */
    public static int surrenderTexture(int t, int before) {
        if (t < 24) return before;
        if (t < 40) return TEX_BASE;
        if (t < 43) return TEX_DIM;
        if (t < 45) return TEX_BASE;
        if (t < 49) return TEX_DIM;
        if (t < 50) return TEX_BASE;
        if (t < 52) return TEX_DIM;
        return TEX_SPENT;
    }

    // ---------------------------------------------------------------- the four new spells

    public static final int BILLET = 28, BILLET_THROW = 14, BILLET_FLIGHT = 10, BILLET_LIE = 60;
    public static final int CHAINS = 32, CHAINS_AT = 16;
    public static final int QUENCH = 36, QUENCH_SPLASH = 16;
    public static final int BELLOWS = 30, BELLOWS_GUST = 16;
    public static final double BELLOWS_HALF_ANGLE = 30, BELLOWS_LEN = 8;

    /** A point (dx, dz from her) is in the cone of half angle half° and length len looking along yaw (Minecraft yaw: −sin, +cos). */
    public static boolean inCone(double dx, double dz, float yawDeg, double half, double len) {
        double d = Math.sqrt(dx * dx + dz * dz);
        if (d > len) return false;
        if (d < 0.5) return true;
        double a = Math.toRadians(yawDeg), fx = -Math.sin(a), fz = Math.cos(a);
        double cos = (dx * fx + dz * fz) / d;
        return cos >= Math.cos(Math.toRadians(half));
    }

    /** Where a thrown billet is k ticks into its flight of n: lerp from → to with an arc up to 3 blocks. Returns {x, y, z}. */
    public static double[] billetArc(double[] from, double[] to, int k, int n) {
        double u = Math.max(0, Math.min(1, k / (double) n));
        return new double[] {from[0] + (to[0] - from[0]) * u, from[1] + (to[1] - from[1]) * u + 3 * 4 * u * (1 - u), from[2] + (to[2] - from[2]) * u};
    }

    // ---------------------------------------------------------------- finisher (owner 20.11: «всем боссам добивание»)

    /**
     * animation.aris.finisher (fx aris_finisher; docs/inbox/2026-11-20_mgr_aris_finisher.md): 2.4 s — pull 0–0.7 s (the victim is pulled
     * 1.9 before her and pressed down), windup 0.7, the hammer on her back at 1.5 s, kill at 2.2 s.
     */
    public static final int FINISHER = 48, FINISHER_PULL = 14, FINISHER_SLAM = 30, FINISHER_KILL = 44, FINISHER_CAM_FROM = 6, FINISHER_CAM = 40;
    public static final double FINISHER_DIST = 1.9;   // the victim lies head to her, pelvis here (visual 20.11)
    /** Animations the visual assistant has not delivered yet (the test only checks them once they exist). */
    public static final java.util.Set<String> PENDING = java.util.Set.of("guard_break");   // T32, the visuals are being made

    /** Pull of the victim toward the hold point at finisher tick t (0..1, ease in-out). */
    public static double finisherPull(int t) {
        double u = Math.max(0, Math.min(1, t / (double) FINISHER_PULL));
        return u < 0.5 ? 2 * u * u : 1 - Math.pow(-2 * u + 2, 2) / 2;
    }

    // ---------------------------------------------------------------- «Дезинтеграция: Реплика» (animation.aris.replica_break, 2.0 s)

    public static final int REPLICA_DELAY = 40, REPLICA = 40, REPLICA_STRIKE = 13, REPLICA_BREAK = 23, REPLICA_SPEAK = 28;
    public static final double REPLICA_SUBTITLE_H = 3.3;
}
