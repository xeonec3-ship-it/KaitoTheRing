/*
 * Part of this file (the spring chain: verlet step with damping, follow-the-leader stretch cap, curl-noise drift, keeping the
 * points out of the body cylinder, Catmull-Rom sampling) is adapted from GateMana.java of the God Wand mod by HyIsNoob
 * (https://github.com/HyIsNoob/god-wand, common/src/main/java/net/godwand/client/GateMana.java), MIT License:
 *
 *   Copyright (c) 2026 HyIsNoob (God Wand contributors)
 *
 *   Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation
 *   files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy,
 *   modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software
 *   is furnished to do so, subject to the following conditions:
 *
 *   The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
 *
 *   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
 *   OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
 *   LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR
 *   IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 *
 * Full notice: docs/third_party/god-wand-MIT.txt. No God Wand assets are used.
 */
package ru.pohsmp.core.ember;

import java.util.ArrayList;
import java.util.List;

/**
 * T14: the physics of the whip of the fire sword-whip ("Раскалённые угли"), without Minecraft (unit tests: WhipSimTest).
 * <p>
 * A rope of {@link #N} points (position-based verlet): gravity, air drag, distance constraints with the mass thinning toward the
 * tip (a lighter tip moves faster — that is what makes a whip crack), bending stiffness that is strong at the handle and gone at the
 * tip, a stretch cap, a little curl-noise drift, kept out of the holder's body cylinder and out of solid blocks.
 * The first two points are the handle: pinned to the hand pose (position and blade direction) every substep, so the whip follows
 * whatever animation moves the hand.
 * <p>
 * A strike ({@link #lash}, {@link #vortex}) adds a soft "guide": every point is pulled toward its place on a sweeping arc, the
 * tip lagging behind the root, so the bend runs down the whip as a wave and the tip snaps over at the end. The tip speed is watched
 * substep by substep: its peak above {@link #CRACK_SPEED} is the crack ({@link Crack}: flash, sparks and the sound on the client).
 * <p>
 * Units: blocks and game ticks. One {@link #step} per client tick ({@link #SUB} substeps inside), the drawing interpolates
 * between the last two ticks ({@link #sample}).
 */
public final class WhipSim {
    /** Points of the rope (the first two are the handle). */
    public static final int N = 36;
    /** Rope length from the hand: hanging free and stretched out in a strike (the server lash reaches 6 from the body, the vortex r 5). */
    public static final double LEN_IDLE = 2.1, LEN_FULL = 5.6;
    /** Thickness (diameter) at the hand and at the tip, blocks. */
    public static final double THICK_ROOT = 0.15, THICK_TIP = 0.03;
    /** Tip speed (blocks per tick) above which its peak is a crack. */
    public static final double CRACK_SPEED = 1.15;
    static final int SUB = 6, ITER = 6, CRACK_COOLDOWN = 7;
    /** Bending stiffness left at the tip: a plaited whip does not zigzag when it lies on the ground or shortens. */
    static final double BEND_TIP = 0.008;
    /** Trail: stiffness (per tick squared), how far back in ticks the end of the whip follows the blade, sag at the end. */
    static final double TRAIL_K = 0.32, TRAIL_BACK = 4.3, TRAIL_SAG = 0.54;
    /** Extra drag per tick at rest (no strike): the hanging whip only sways slowly. */
    static final double CALM_DRAG = 0.86;
    /** Stiffness of the strike guide (per tick squared). */
    static final double GUIDE_K = 0.6;
    static final double GRAVITY = 0.032, DRAG = 0.955, MAX_STRETCH = 1.04, CURL = 0.0016, SWAY = 0.0012;
    /** Body cylinder the points stay out of: radius added to the holder's half width. */
    static final double BODY_PAD = 0.06;

    /** Hand pose: where the whip leaves the hilt and which way the blade points (any length, normalised here). */
    public record Pose(double x, double y, double z, double dx, double dy, double dz) {
        Pose norm() {
            double l = Math.sqrt(dx * dx + dy * dy + dz * dz);
            return l < 1e-9 ? new Pose(x, y, z, 0, -1, 0) : new Pose(x, y, z, dx / l, dy / l, dz / l);
        }
    }

    /** The holder's body (the whip never goes through it): feet position, half width and height. */
    public record Body(double x, double y, double z, double halfWidth, double height) {}

    /**
     * Blocks around the whip. top(x, y, z): the top of the collision box inside block (x, y, z) as 0..1 (1 — a full block, 0.5 —
     * a bottom slab), or NaN when the block lets the whip through.
     */
    public interface Solid {
        double top(int x, int y, int z);

        Solid NONE = (x, y, z) -> Double.NaN;
    }

    /** The tip cracked: where, its velocity (blocks per tick) and speed. */
    public record Crack(double x, double y, double z, double vx, double vy, double vz, double speed) {}

    // ---------------------------------------------------------------- state

    final double[] x = new double[N], y = new double[N], z = new double[N];      // now
    final double[] ox = new double[N], oy = new double[N], oz = new double[N];   // one substep ago (verlet velocity)
    final double[] lx = new double[N], ly = new double[N], lz = new double[N];   // at the previous tick (interpolation)
    private final double[] sx = new double[N], sy = new double[N], sz = new double[N];   // at the substep start (free of blocks)
    /** The rope after each substep of the last tick (0 — the tick start): the drawing goes through them, a fast tip draws no chords. */
    private final double[][] hist = new double[SUB + 1][3 * N];
    private boolean cracked;
    private Pose lastRoot;
    private boolean ready;
    private double time, len = LEN_IDLE;
    private int cooldown;
    private double tipSpeed, prevTipSpeed, peakSpeed;
    private final double[] peakAt = new double[6];

    // the hand's path, one entry per substep (newest at hh): position and blade direction
    private static final int HIST = (int) Math.ceil((TRAIL_BACK + 2) * SUB) + 2;
    private final double[][] hp = new double[HIST][6];
    private int hh = -1, hn;

    // the strike guide
    private int mode = NONE;
    private double driveT, driveLen, a0, a1, tilt;
    private static final int NONE = 0, LASH = 1, VORTEX = 2;
    /** Ticks after a strike before the whip shortens back to {@link #LEN_IDLE}. */
    static final int HOLD = 10;
    private double sinceStrike = 1e9;

    public boolean ready() {
        return ready;
    }

    /** Current rest length of the rope. */
    public double length() {
        return len;
    }

    /** Tip speed at the last substep, blocks per tick. */
    public double tipSpeed() {
        return tipSpeed;
    }

    /** True while a strike guides the whip or it is still stretched out after one. */
    public boolean striking() {
        return mode != NONE || sinceStrike < HOLD;
    }

    // ---------------------------------------------------------------- strikes

    /**
     * A lash: the whip sweeps the horizontal arc from facing + from to facing + to (radians, + = left as in EmberBlade: the angle
     * of a horizontal direction is atan2(z, x)) over {@code ticks}, rising a little when {@code rising} (the 2nd lash of the combo
     * goes from below upward). The arc starts a bit behind {@code from} (the wind-up).
     */
    public void lash(double facing, double from, double to, int ticks, boolean rising) {
        mode = LASH;
        driveT = 0;
        driveLen = Math.max(2, ticks);
        double windUp = 0.35 * Math.signum(from - to);
        a0 = facing + from + windUp;
        a1 = facing + to;
        tilt = rising ? 0.55 : 0;
        sinceStrike = 0;
        cracked = false;
    }

    /**
     * "Fire Vortex": the whip flung out to its full length goes round the holder from behind ({@code start}, the angle as in
     * {@link #lash}) a full turn and on to the front, a turn and a half (direction by {@code turn} = ±1; the effect ember_vortex
     * turns +1), ending where the hand is when the body has turned round.
     */
    public void vortex(double start, int turn, int ticks) {
        mode = VORTEX;
        driveT = 0;
        driveLen = Math.max(2, ticks);
        a0 = start;
        a1 = start + 3 * Math.PI * (turn >= 0 ? 1 : -1);
        tilt = 0;
        sinceStrike = 0;
        cracked = false;
    }

    // ---------------------------------------------------------------- simulation

    /** 0..1: how fast the hand moves along the ground (over the last tick), 1 from a run (0.35 blocks per tick) up. */
    private double airflow() {
        if (hn <= SUB) return 0;
        double[] a = hp[hh], b = hp[Math.floorMod(hh - SUB, HIST)];
        return clamp01(Math.hypot(a[0] - b[0], a[2] - b[2]) / 0.35);
    }

    private void remember(double rx, double ry, double rz, double dx, double dy, double dz) {
        hh = (hh + 1) % HIST;
        double[] e = hp[hh];
        e[0] = rx;
        e[1] = ry;
        e[2] = rz;
        e[3] = dx;
        e[4] = dy;
        e[5] = dz;
        if (hn < HIST) hn++;
    }

    /**
     * Trail target of point i, {@code older} substeps further in the past (0 — now, 1 — one substep before, for the target's speed):
     * the hand pose u * TRAIL_BACK ticks back plus its blade direction times the rope length to i, sagging, not under the floor.
     */
    private double[] trail(int i, int older, double seg, Body body) {
        double u = (double) i / (N - 1);
        double back = Math.min(hn - 1.001, u * TRAIL_BACK * SUB + older);
        int k = (int) back;
        double f = back - k;
        double[] a = hp[Math.floorMod(hh - k, HIST)], b = hp[Math.floorMod(hh - k - 1, HIST)];
        double s = i * seg;
        double px = lerp(a[0], b[0], f), py = lerp(a[1], b[1], f), pz = lerp(a[2], b[2], f);
        double dx = lerp(a[3], b[3], f), dy = lerp(a[4], b[4], f), dz = lerp(a[5], b[5], f);
        double dl = Math.sqrt(dx * dx + dy * dy + dz * dz);
        if (dl > 1e-9) {
            dx /= dl;
            dy /= dl;
            dz /= dl;
        }
        double ty = py + dy * s - TRAIL_SAG * u * u * (1 - 0.85 * airflow());
        if (body != null) ty = Math.max(body.y() + 0.02, ty);
        return new double[] {px + dx * s, ty, pz + dz * s};
    }

    /** Puts the rope hanging straight down from the hand and lets it settle (first step, or after a teleport). */
    void reset(Pose r, Body body, Solid solid) {
        double seg = len / (N - 1);
        for (int i = 0; i < N; i++) {
            double px = r.x(), py = r.y(), pz = r.z();
            if (i >= 1) {
                px += r.dx() * seg;
                py += r.dy() * seg;
                pz += r.dz() * seg;
            }
            if (i >= 2) py -= (i - 1) * seg;
            x[i] = ox[i] = lx[i] = px;
            y[i] = oy[i] = ly[i] = py;
            z[i] = oz[i] = lz[i] = pz;
        }
        lastRoot = r;
        ready = true;
        for (int k = 0; k < 30; k++) tick(r, r, body, solid, null);
        for (int i = 0; i < N; i++) {
            lx[i] = x[i];
            ly[i] = y[i];
            lz[i] = z[i];
        }
        for (int s = 0; s <= SUB; s++) record(s);
        tipSpeed = prevTipSpeed = 0;
    }

    /**
     * One game tick. {@code root} — the hand pose now (the previous one is remembered, the substeps go between them). Returns the
     * cracks of this tick (usually none, at most one).
     */
    public List<Crack> step(Pose root, Body body, Solid solid) {
        Pose r = root.norm();
        if (solid == null) solid = Solid.NONE;
        List<Crack> out = new ArrayList<>(1);
        if (!ready || lastRoot == null || dist2(lastRoot, r) > 36) {   // first time or teleported: start hanging
            reset(r, body, solid);
            return out;
        }
        for (int i = 0; i < N; i++) {
            lx[i] = x[i];
            ly[i] = y[i];
            lz[i] = z[i];
        }
        record(0);
        tick(lastRoot, r, body, solid, out);
        lastRoot = r;
        return out;
    }

    private void tick(Pose from, Pose to, Body body, Solid solid, List<Crack> out) {
        // length: out to full at once in a strike, back slowly after it
        double want = striking() ? LEN_FULL : LEN_IDLE;
        double rate = want > len ? 0.9 : 0.12, was = len;
        len += Math.max(-rate, Math.min(rate, want - len));
        double seg = len / (N - 1);
        if (len < was) reelIn(seg);
        double h = 1.0 / SUB;
        for (int s = 1; s <= SUB; s++) {
            double k = (double) s / SUB;
            double rx = lerp(from.x(), to.x(), k), ry = lerp(from.y(), to.y(), k), rz = lerp(from.z(), to.z(), k);
            double dx = lerp(from.dx(), to.dx(), k), dy = lerp(from.dy(), to.dy(), k), dz = lerp(from.dz(), to.dz(), k);
            double dl = Math.sqrt(dx * dx + dy * dy + dz * dz);
            if (dl < 1e-9) {
                dx = 0;
                dy = -1;
                dz = 0;
            } else {
                dx /= dl;
                dy /= dl;
                dz /= dl;
            }
            substep(rx, ry, rz, dx, dy, dz, seg, h, body, solid, out);
            if (out != null) record(s);
            time += h;
            if (mode != NONE) {
                driveT += h;
                if (driveT > driveLen * 1.6 + 3) mode = NONE;
            }
        }
        sinceStrike += 1;
        if (cooldown > 0) cooldown--;
    }

    private void substep(double rx, double ry, double rz, double dx, double dy, double dz, double seg, double h, Body body, Solid solid,
            List<Crack> out) {
        double tipX = x[N - 1], tipY = y[N - 1], tipZ = z[N - 1];
        // after a strike the whip calms down quicker (a real whip spends its energy in the crack)
        boolean settle = mode == NONE ? sinceStrike < HOLD + 6 : driveT > driveLen * (mode == VORTEX ? 1.5 : 1.35);
        // at rest (no strike) the whip is calm: much stronger drag, no blocks, only a smooth floor under the feet (owner 19.11: it
        // twitched all the time from the ground contacts)
        boolean calm = !striking();
        double drag = Math.pow(DRAG * (settle ? 0.8 : 1) * (calm ? CALM_DRAG : 1), h);
        // the handle: pinned to the hand; the hand's path is remembered for the trail
        pin(0, rx, ry, rz);
        pin(1, rx + dx * seg, ry + dy * seg, rz + dz * seg);
        remember(rx, ry, rz, dx, dy, dz);
        // integrate the free points
        double env = mode == NONE ? 0 : envelope();
        double air = airflow();
        for (int i = 2; i < N; i++) {
            double u = (double) i / (N - 1);
            double vx = (x[i] - ox[i]) * drag, vy = (y[i] - oy[i]) * drag, vz = (z[i] - oz[i]) * drag;
            sx[i] = x[i];
            sy[i] = y[i];
            sz[i] = z[i];
            ox[i] = x[i];
            oy[i] = y[i];
            oz[i] = z[i];
            // running: the air the holder runs through holds the outer whip up, it streams almost level behind
            double ax = 0, ay = -GRAVITY * (1 - 0.85 * air * u), az = 0;
            // a slow drift (curl noise) and a gentle sway, more toward the tip: the hanging whip is never quite still
            double free = (0.3 + 0.7 * u) * (calm ? 0.4 : 1);
            double[] c = curl(x[i] * 0.7, y[i] * 0.7, z[i] * 0.7, time);
            ax += c[0] * CURL * free;
            ay += c[1] * CURL * free * 0.5;
            az += c[2] * CURL * free;
            ax += Math.sin(time * 0.07 + u * 2.1) * SWAY * u;
            az += Math.cos(time * 0.053 + u * 1.7) * SWAY * u;
            double kt = (1 - env) * TRAIL_K * smooth(0.04, 0.2, u) * (1 - 0.5 * u);
            if (kt > 0 && hn > 1) {
                // the trail (the look the owner liked in the animation preview): point i goes where the blade tip was u * TRAIL_BACK
                // ticks ago, out along the blade direction of that moment, sagging toward the end. The whip lags behind the hand,
                // curls along the path of a swing and streams behind a walking or running holder; the chain adds inertia and the crack.
                double[] t = trail(i, 0, seg, body), tp = trail(i, 1, seg, body);
                double cc = 2 * Math.sqrt(kt) * 0.8;
                ax += (t[0] - x[i]) * kt + ((t[0] - tp[0]) / h - vx / h) * cc;
                ay += (t[1] - y[i]) * kt + ((t[1] - tp[1]) / h - vy / h) * cc;
                az += (t[2] - z[i]) * kt + ((t[2] - tp[2]) / h - vz / h) * cc;
            }
            if (env > 0) {
                // the strike guide: a damped spring (PD) toward the point's place on the arc, and toward the arc's own speed there,
                // so the rope follows the sweep without overshooting; weaker at the handle (the hand leads it) and at the tip (free)
                double[] t = guide(i, driveT, rx, ry, rz, seg, body), tp = guide(i, driveT - h, rx, ry, rz, seg, body);
                double kk = env * GUIDE_K * smooth(0.04, 0.25, u) * (1 - 0.4 * u), cc = 2 * Math.sqrt(kk) * 0.9;
                double vxt = (t[0] - tp[0]) / h, vyt = (t[1] - tp[1]) / h, vzt = (t[2] - tp[2]) / h;
                ax += (t[0] - x[i]) * kk + (vxt - vx / h) * cc;
                ay += (t[1] - y[i]) * kk + (vyt - vy / h) * cc;
                az += (t[2] - z[i]) * kk + (vzt - vz / h) * cc;
            }
            x[i] += vx + ax * h * h;
            y[i] += vy + ay * h * h;
            z[i] += vz + az * h * h;
        }
        // constraints: lengths (lighter toward the tip) and bending (stiff at the handle, none at the tip)
        for (int it = 0; it < ITER; it++) {
            for (int i = 1; i < N - 1; i++) {
                double wi = i < 2 ? 0 : invMass(i), wj = invMass(i + 1);
                double ex = x[i + 1] - x[i], ey = y[i + 1] - y[i], ez = z[i + 1] - z[i];
                double d = Math.sqrt(ex * ex + ey * ey + ez * ez);
                if (d < 1e-9) continue;
                double corr = (d - seg) / d / (wi + wj);
                x[i] += ex * corr * wi;
                y[i] += ey * corr * wi;
                z[i] += ez * corr * wi;
                x[i + 1] -= ex * corr * wj;
                y[i + 1] -= ey * corr * wj;
                z[i + 1] -= ez * corr * wj;
            }
            for (int i = 1; i < N - 1; i++) {
                double u = (double) i / (N - 1), b = BEND_TIP + 0.3 * Math.pow(1 - u, 3);
                double tx = x[i] - x[i - 1], ty = y[i] - y[i - 1], tz = z[i] - z[i - 1];
                double tl = Math.sqrt(tx * tx + ty * ty + tz * tz);
                if (tl < 1e-9) continue;
                double wx = x[i] + tx / tl * seg, wy = y[i] + ty / tl * seg, wz = z[i] + tz / tl * seg;
                x[i + 1] += (wx - x[i + 1]) * b;
                y[i + 1] += (wy - y[i + 1]) * b;
                z[i + 1] += (wz - z[i + 1]) * b;
            }
        }
        // the body cylinder never reaches past the hand: in a backhand the fist crosses before the chest, the whip leaves it there
        double bodyR = body == null ? 0 : Math.min(body.halfWidth() + BODY_PAD, Math.hypot(rx - body.x(), rz - body.z()) - 0.04);
        // order of say: the body gives way to the rope's length (a rope that straddles the body is not torn apart), the blocks
        // have the last word (the whip never ends up inside a wall or under the floor)
        for (int pass = 0; pass < 3; pass++) {
            if (bodyR > 0.12) for (int i = 4; i < N; i++) keepOut(i, body, bodyR);
            capStretch(seg);
            for (int i = 2; i < N; i++) {
                if (calm) {   // walls still stop it; the floor under the feet is the smooth plane
                    restOnFloor(i, body);
                    collide(i, solid);   // on the plane the floor block is never entered: only walls push
                } else collide(i, solid);
            }
        }
        // the tip speed, substep by substep: its peak above CRACK_SPEED is the crack
        double mx = x[N - 1] - tipX, my = y[N - 1] - tipY, mz = z[N - 1] - tipZ;
        prevTipSpeed = tipSpeed;
        tipSpeed = Math.sqrt(mx * mx + my * my + mz * mz) / h;
        if (out != null) {
            if (tipSpeed > peakSpeed) {
                peakSpeed = tipSpeed;
                peakAt[0] = x[N - 1];
                peakAt[1] = y[N - 1];
                peakAt[2] = z[N - 1];
                peakAt[3] = mx / h;
                peakAt[4] = my / h;
                peakAt[5] = mz / h;
            }
            if (tipSpeed < peakSpeed * 0.8) {   // past the peak
                // in a strike: one crack, in its snap (second half); by the hand alone (a swing without a hit): a harder one
                boolean may = mode == NONE ? peakSpeed > CRACK_SPEED * 2.6 && sinceStrike > HOLD + 10
                        : !cracked && driveT >= (mode == VORTEX ? 0.8 : 0.6) * driveLen && peakSpeed > CRACK_SPEED;
                if (may && cooldown == 0 && out.isEmpty()) {
                    out.add(new Crack(peakAt[0], peakAt[1], peakAt[2], peakAt[3], peakAt[4], peakAt[5], peakSpeed));
                    cooldown = CRACK_COOLDOWN;
                    cracked = true;
                    spend();
                }
                peakSpeed = tipSpeed;
            }
        }
    }

    /**
     * Shortening: the rope is drawn into the hilt — its line in space stays where it is and ends sooner (the points are re-spread
     * over the shorter length), so the whip is never squeezed into kinks (it would coil up lying on the ground) and nothing jumps.
     * The old positions are re-spread the same way: the motion goes on.
     */
    private void reelIn(double seg) {
        double[] arc = new double[N];
        for (int i = 2; i < N; i++) arc[i] = arc[i - 1] + Math.sqrt(sq(x[i] - x[i - 1]) + sq(y[i] - y[i - 1]) + sq(z[i] - z[i - 1]));
        double take = arc[N - 1] - (N - 2) * seg;
        if (take <= 1e-9) return;
        double[] nx = new double[N], ny = new double[N], nz = new double[N], px = new double[N], py = new double[N], pz = new double[N];
        int j = 1;
        for (int i = 2; i < N; i++) {
            double want = (i - 1) * seg;   // the curve stays where it is, it ends sooner
            while (j < N - 2 && arc[j + 1] < want) j++;
            double span = arc[j + 1] - arc[j], t = span < 1e-12 ? 0 : clamp01((want - arc[j]) / span);
            nx[i] = lerp(x[j], x[j + 1], t);
            ny[i] = lerp(y[j], y[j + 1], t);
            nz[i] = lerp(z[j], z[j + 1], t);
            px[i] = lerp(ox[j], ox[j + 1], t);
            py[i] = lerp(oy[j], oy[j + 1], t);
            pz[i] = lerp(oz[j], oz[j + 1], t);
        }
        for (int i = 2; i < N; i++) {
            x[i] = nx[i];
            y[i] = ny[i];
            z[i] = nz[i];
            ox[i] = px[i];
            oy[i] = py[i];
            oz[i] = pz[i];
        }
    }

    private static double sq(double v) {
        return v * v;
    }

    /** The crack takes the energy of the outer half: its speed drops (most at the tip), no wild flailing after it. */
    private void spend() {
        for (int i = 2; i < N; i++) {
            double k = 1 - 0.7 * smooth(0.35, 1, (double) i / (N - 1));
            ox[i] = x[i] - (x[i] - ox[i]) * k;
            oy[i] = y[i] - (y[i] - oy[i]) * k;
            oz[i] = z[i] - (z[i] - oz[i]) * k;
        }
    }

    private void record(int s) {
        double[] h = hist[s];
        for (int i = 0; i < N; i++) {
            h[3 * i] = x[i];
            h[3 * i + 1] = y[i];
            h[3 * i + 2] = z[i];
        }
    }

    private void pin(int i, double px, double py, double pz) {
        ox[i] = x[i];
        oy[i] = y[i];
        oz[i] = z[i];
        x[i] = px;
        y[i] = py;
        z[i] = pz;
    }

    /** Inverse mass: 1 near the hand, 3.5 at the tip (the taper). */
    static double invMass(int i) {
        double u = (double) i / (N - 1);
        return 1 + 2.5 * u * u;
    }

    private void capStretch(double seg) {
        double cap = seg * MAX_STRETCH;
        for (int i = 1; i < N - 1; i++) {
            double ex = x[i + 1] - x[i], ey = y[i + 1] - y[i], ez = z[i + 1] - z[i];
            double d = Math.sqrt(ex * ex + ey * ey + ez * ez);
            if (d <= cap || d < 1e-9) continue;
            double k = cap / d;
            double nx = x[i] + ex * k, ny = y[i] + ey * k, nz = z[i] + ez * k;
            // drag the old position along, so the cap does not pump energy into the rope
            ox[i + 1] += (nx - x[i + 1]) * 0.6;
            oy[i + 1] += (ny - y[i + 1]) * 0.6;
            oz[i + 1] += (nz - z[i + 1]) * 0.6;
            x[i + 1] = nx;
            y[i + 1] = ny;
            z[i + 1] = nz;
        }
    }

    /** Pushes point i out of the holder's body cylinder (sideways, keeping the height). */
    private void keepOut(int i, Body b, double r) {
        double dy = y[i] - b.y();
        if (dy < -0.1 || dy > b.height() + 0.1) return;
        double ex = x[i] - b.x(), ez = z[i] - b.z(), d = Math.hypot(ex, ez);
        if (d >= r) return;
        if (d < 1e-6) {   // dead centre: out the way the point was coming from
            ex = ox[i] - b.x();
            ez = oz[i] - b.z();
            d = Math.hypot(ex, ez);
            if (d < 1e-6) {
                ex = 1;
                ez = 0;
                d = 1;
            }
        }
        double k = (r + 1e-4) / d;
        x[i] = b.x() + ex * k;
        z[i] = b.z() + ez * k;
    }

    /** At rest: the ground is a flat plane at the holder's feet; a point on it just lies there (no friction pushes, no jitter). */
    private void restOnFloor(int i, Body body) {
        if (body == null) return;
        double fl = body.y() + 0.02;
        if (y[i] >= fl) return;
        y[i] = fl;
        oy[i] = fl;
        ox[i] += (x[i] - ox[i]) * 0.15;
        oz[i] += (z[i] - oz[i]) * 0.15;
    }

    /** Is the point outside every collision box? */
    private static boolean free(Solid solid, double px, double py, double pz) {
        int by = floor(py);
        double top = solid.top(floor(px), by, floor(pz));
        return Double.isNaN(top) || py >= by + Math.max(0.05, Math.min(1, top));
    }

    /**
     * Point i out of the blocks: if it went in during this substep, back along its path to the surface, then it slides on along the
     * free axes (a whip lies on the floor and slides along walls), losing speed on the touch (friction). A point that was already
     * inside (the hand went into a block) is lifted to the free space above, up to two blocks.
     */
    private void collide(int i, Solid solid) {
        if (free(solid, x[i], y[i], z[i])) return;
        double sx = this.sx[i], sy = this.sy[i], sz = this.sz[i];
        if (!free(solid, sx, sy, sz)) {
            for (double up = 0.1; up <= 2.01; up += 0.1)
                if (free(solid, x[i], y[i] + up, z[i])) {
                    y[i] += up;
                    oy[i] = y[i];
                    return;
                }
            return;
        }
        double lo = 0, hi = 1;
        for (int k = 0; k < 12; k++) {
            double m = (lo + hi) / 2;
            if (free(solid, lerp(sx, x[i], m), lerp(sy, y[i], m), lerp(sz, z[i], m))) lo = m;
            else hi = m;
        }
        double px = lerp(sx, x[i], lo), py = lerp(sy, y[i], lo), pz = lerp(sz, z[i], lo);
        boolean floor = !free(solid, px, py - 0.02, pz);
        // slide on along the axes that are still free (y last: lying on the floor keeps its x and z)
        if (free(solid, x[i], py, pz)) px = x[i];
        if (free(solid, px, py, z[i])) pz = z[i];
        if (free(solid, px, y[i], pz)) py = y[i];
        x[i] = px;
        y[i] = py;
        z[i] = pz;
        // the touch takes speed: a lot across the surface, some along it
        double fr = floor ? 0.25 : 0.3;
        ox[i] += (x[i] - ox[i]) * fr;
        oy[i] += (y[i] - oy[i]) * (floor ? 1 : fr);
        oz[i] += (z[i] - oz[i]) * fr;
    }

    // ---------------------------------------------------------------- the strike guide

    /** 0..1: up at once, held for the strike, let go while the tip still flies (it snaps over on its own). */
    private double envelope() {
        double t = driveT, end = driveLen + (mode == VORTEX ? 0.5 : 0.35) * driveLen;
        if (t < 0.6) return t / 0.6;
        if (t < end) return 1;
        return Math.max(0, 1 - (t - end) / 2.5);
    }

    /**
     * Where point i should be on the arc now: tip behind the root (the wave), rope stretched out with a little sag. The arc turns
     * about the holder's axis at the hand's height (as the server measures the hit), so the rope never has to go through the body.
     */
    private double[] guide(int i, double time, double rx, double ry, double rz, double seg, Body body) {
        double u = (double) i / (N - 1);
        double lag = (mode == VORTEX ? 0.25 : 0.5) * driveLen * Math.pow(u, 1.3);
        double tau = clamp01((time - lag) / driveLen);
        double e = mode == VORTEX ? spin(tau) : easeInOutSharp(tau, u);
        double a = a0 + (a1 - a0) * e;
        double s = i * seg;
        double elev = mode == VORTEX ? -0.08 : -0.1 + tilt * (e - 0.5);
        double horiz = Math.cos(elev);
        double sag = (mode == VORTEX ? 0.25 : 0.4) * Math.sin(Math.PI * u) * (1 - Math.abs(2 * tau - 1) * 0.5);
        double cx = rx, cz = rz, r0 = 0;
        if (body != null) {
            cx = body.x();
            cz = body.z();
            r0 = Math.hypot(rx - cx, rz - cz);
        }
        double r = r0 + horiz * s;
        return new double[] {cx + Math.cos(a) * r, ry + Math.sin(elev) * s - sag, cz + Math.sin(a) * r};
    }

    /** The vortex turn: speeds up over the first fifth, then an even spin, slowing over the last fifth. */
    static double spin(double t) {
        double a = 0.2, v = 1 / (1 - a);   // the even speed so that the whole turn is 1
        if (t < a) return v * t * t / (2 * a);
        if (t > 1 - a) return 1 - v * (1 - t) * (1 - t) / (2 * a);
        return v * (t - a / 2);
    }

    /** Sharper toward the tip: the outer rope waits and then catches up fast (the tip speeds up at the end). */
    static double easeInOutSharp(double t, double u) {
        double p = 2 + 2.5 * u;
        return t < 0.5 ? Math.pow(2 * t, p) / 2 : 1 - Math.pow(2 - 2 * t, p) / 2;
    }

    // ---------------------------------------------------------------- drawing helpers

    /**
     * The rope at {@code partial} (0 — the previous tick, 1 — now) into {@code out} (x0 y0 z0 x1 ...; 3 * N values), through the
     * substeps of the tick.
     */
    public void sample(double partial, double[] out) {
        double f = clamp01(partial) * SUB;
        int k = Math.min(SUB - 1, (int) f);
        double t = f - k;
        double[] a = hist[k], b = hist[k + 1];
        for (int j = 0; j < 3 * N; j++) out[j] = lerp(a[j], b[j], t);
    }

    /** Point i now (tests, server-free hit checks). */
    public double[] point(int i) {
        return new double[] {x[i], y[i], z[i]};
    }

    /**
     * A smooth curve through the points (Catmull-Rom, {@code per} samples per span, the ends repeated): 3 * ((n - 1) * per + 1)
     * values. The tube of the whip is drawn along it.
     */
    public static double[] spline(double[] pts, int per) {
        int n = pts.length / 3, m = (n - 1) * per + 1;
        double[] out = new double[3 * m];
        for (int j = 0; j < m; j++) {
            int i = Math.min(n - 2, j / per);
            double t = (double) (j - i * per) / per;
            if (j == m - 1) {
                i = n - 2;
                t = 1;
            }
            int a = Math.max(0, i - 1), b = i, c = i + 1, d = Math.min(n - 1, i + 2);
            for (int k = 0; k < 3; k++)
                out[3 * j + k] = catmull(pts[3 * a + k], pts[3 * b + k], pts[3 * c + k], pts[3 * d + k], t);
        }
        return out;
    }

    static double catmull(double a, double b, double c, double d, double t) {
        double t2 = t * t, t3 = t2 * t;
        return 0.5 * (2 * b + (c - a) * t + (2 * a - 5 * b + 4 * c - d) * t2 + (-a + 3 * b - 3 * c + d) * t3);
    }

    /** Thickness (diameter) at u along the whip: 0.15 at the hand, 0.03 at the tip. */
    public static double thickness(double u) {
        return THICK_TIP + (THICK_ROOT - THICK_TIP) * Math.pow(1 - clamp01(u), 0.8);
    }

    /** Colour at u: #C2470E at the hand to #FFC27A at the tip. */
    public static int color(double u) {
        return mix(0xC2470E, 0xFFC27A, Math.pow(clamp01(u), 0.85));
    }

    public static int mix(int a, int b, double t) {
        t = clamp01(t);
        int r = (int) Math.round(((a >> 16) & 255) * (1 - t) + ((b >> 16) & 255) * t);
        int g = (int) Math.round(((a >> 8) & 255) * (1 - t) + ((b >> 8) & 255) * t);
        int bl = (int) Math.round((a & 255) * (1 - t) + (b & 255) * t);
        return r << 16 | g << 8 | bl;
    }

    // ---------------------------------------------------------------- math

    /** Divergence-free drift: the curl of a vector potential made of three travelling sines (as GateMana.curl). */
    static double[] curl(double px, double py, double pz, double t) {
        double ax = 1.1 * py + .7 * pz + .031 * t, ay = 1.3 * pz + .9 * px + .026 * t + 1.7, az = .9 * px + 1.2 * py + .029 * t + 3.1;
        return new double[] {1.2 * Math.cos(az) - 1.3 * Math.cos(ay), .7 * Math.cos(ax) - .9 * Math.cos(az), .9 * Math.cos(ay) - 1.1 * Math.cos(ax)};
    }

    private static double dist2(Pose a, Pose b) {
        double dx = a.x() - b.x(), dy = a.y() - b.y(), dz = a.z() - b.z();
        return dx * dx + dy * dy + dz * dz;
    }

    static double lerp(double a, double b, double t) {
        return a + (b - a) * t;
    }

    static double clamp01(double v) {
        return v < 0 ? 0 : v > 1 ? 1 : v;
    }

    static double smooth(double e0, double e1, double v) {
        double t = clamp01((v - e0) / (e1 - e0));
        return t * t * (3 - 2 * t);
    }

    private static int floor(double v) {
        int i = (int) v;
        return v < i ? i - 1 : i;
    }
}
