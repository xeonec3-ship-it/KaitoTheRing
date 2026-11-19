package ru.pohsmp.core.client.fx.gate;

import net.minecraft.world.phys.Vec3;

/**
 * Where the witch's staff is in the «Безмолвные врата» scene, as a pure function of the scene clock (ticks from the scene start):
 * until 37.4 s it floats upright front-left of her, swaying and bobbing; over 37.4–38.4 s it glides into her left fist at the belt
 * (pose STAFF_L of tools/gen_player_anims.py, the hand closes on it at 37.6–38.8 s) and stands there upright to the end.
 * Used by {@code client/GateStaff} (draws the staff) and by {@link GateMana} (the trail of mana from its head and foot), so both agree.
 * Local axes as in GateStaff: x to the caster's left, y up, z forward, from the feet, turned with the body yaw.
 */
public final class GateStaffPose {
    private GateStaffPose() {}

    /** Ticks of the glide from the float into the left fist. */
    public static final int TAKE_FROM = 748, TAKE_TO = 768;
    /** Head (ring and eye) and foot of the staff from the item origin along its axis, in blocks (geo silent_witch_staff: y -16..31 px). */
    static final double HEAD = 1.55, FOOT = .98;

    /** {x, y, z, roll about z (deg), tilt about x (deg)} of the item origin at scene tick t. */
    public static double[] local(double t) {
        double k = smoother((t - TAKE_FROM) / (TAKE_TO - TAKE_FROM));
        double fx = .75, fy = 1.15 + .08 * Math.sin(t * .06), fz = .65, rz = 4 * Math.sin(t * .045), rx = 3 * Math.sin(t * .037 + 1);
        double hx = .36, hy = .98, hz = .3;
        return new double[]{fx + (hx - fx) * k, fy + (hy - fy) * k, fz + (hz - fz) * k, rz * (1 - k), rx * (1 - k)};
    }

    static double smoother(double x) { x = Math.max(0, Math.min(1, x)); return x * x * x * (x * (6 * x - 15) + 10); }

    /** World position of the item origin and the unit axis toward the head. */
    static Vec3[] world(double t, Vec3 feet, double bodyYawDeg) {
        double[] l = local(t);
        Vec3 f = Vec3.directionFromRotation(0, (float) bodyYawDeg), left = new Vec3(f.z, 0, -f.x);
        Vec3 origin = feet.add(left.scale(l[0])).add(0, l[1], 0).add(f.scale(l[2]));
        // GateStaff: mulPose(ZP rz) then mulPose(XP rx) on the item, so the axis (0,1,0) -> Z(X(up)).
        double a = Math.toRadians(l[4]), b = Math.toRadians(l[3]);
        double ax = -Math.cos(a) * Math.sin(b), ay = Math.cos(a) * Math.cos(b), az = Math.sin(a);
        Vec3 axis = left.scale(ax).add(0, ay, 0).add(f.scale(az));
        return new Vec3[]{origin, axis};
    }
    public static Vec3 head(double t, Vec3 feet, double bodyYawDeg) { Vec3[] w = world(t, feet, bodyYawDeg); return w[0].add(w[1].scale(HEAD)); }
    public static Vec3 foot(double t, Vec3 feet, double bodyYawDeg) { Vec3[] w = world(t, feet, bodyYawDeg); return w[0].subtract(w[1].scale(FOOT)); }
}
