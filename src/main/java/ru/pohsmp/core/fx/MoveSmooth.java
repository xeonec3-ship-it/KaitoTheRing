package ru.pohsmp.core.fx;

/**
 * Smooth glide of an fx instance moved by the server (FxMsg.MOVE; pure logic, used by client/fx/FxClient).
 * <p>
 * Why: the server sends MOVE every server tick (the turning seals of Eight Shields, wind spears, oblivion blades, the fire whip,
 * Ereb's walls and arrows...). The client used to put the instance right at the new place: the motion was only as smooth as the packets -
 * at most 20 steps a second, and on a dedicated server fewer and uneven (TPS below 20, packets bunched by the network).
 * Now every MOVE starts a glide from where the instance is drawn at that moment to the new place, over the usual gap between MOVEs
 * (measured, 1..6 ticks): one packet of delay, no steps. Times are on the client's monotonic clock (AnimClock), in ticks.
 * Angles are degrees and turn the short way round.
 */
public final class MoveSmooth {
    /** A jump longer than this (blocks) is a teleport: no glide. */
    public static final double SNAP = 8;
    public static final double MIN_GAP = 1, MAX_GAP = 6;

    private final double[] from = new double[5], to = new double[5];
    private double at, gap = MIN_GAP, last = Double.NaN;

    public MoveSmooth(double x, double y, double z, double yaw, double pitch) {
        set(to, x, y, z, yaw, pitch);
        System.arraycopy(to, 0, from, 0, 5);
    }

    /** A MOVE arrived at clock time now. */
    public void move(double now, double x, double y, double z, double yaw, double pitch) {
        double[] cur = sample(now);
        if (!Double.isNaN(last)) {
            double g = Math.max(MIN_GAP, Math.min(MAX_GAP, now - last));
            gap = gap * 0.6 + g * 0.4;
        }
        last = now;
        double dx = x - cur[0], dy = y - cur[1], dz = z - cur[2];
        System.arraycopy(cur, 0, from, 0, 5);
        set(to, x, y, z, yaw, pitch);
        if (dx * dx + dy * dy + dz * dz > SNAP * SNAP) System.arraycopy(to, 0, from, 0, 5);
        at = now;
    }

    /** {x, y, z, yaw, pitch} to draw at clock time now. */
    public double[] sample(double now) {
        double u = Math.max(0, Math.min(1, (now - at) / gap));
        double[] r = new double[5];
        for (int i = 0; i < 3; i++) r[i] = from[i] + (to[i] - from[i]) * u;
        r[3] = angle(from[3], to[3], u);
        r[4] = angle(from[4], to[4], u);
        return r;
    }

    /** The gap between MOVEs as measured so far, in ticks. */
    public double gap() {
        return gap;
    }

    private static double angle(double a, double b, double u) {
        double d = ((b - a) % 360 + 540) % 360 - 180;
        return a + d * u;
    }

    private static void set(double[] v, double x, double y, double z, double yaw, double pitch) {
        v[0] = x;
        v[1] = y;
        v[2] = z;
        v[3] = yaw;
        v[4] = pitch;
    }
}
