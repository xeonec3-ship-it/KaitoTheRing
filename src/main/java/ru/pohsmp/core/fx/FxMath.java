package ru.pohsmp.core.fx;

import java.util.ArrayList;
import java.util.List;
import java.util.SplittableRandom;
import ru.pohsmp.core.fx.sigil.SigilDef;

/**
 * Placement math of effects without Minecraft classes: offsets in the caster's view axes, arcs of child sigils,
 * strike points of a beam rain. Same seed -> same result on every client.
 * Minecraft yaw convention: yaw 0 looks along +Z, yaw 90 along -X.
 */
public final class FxMath {
    private FxMath() {}

    public record Vec(double x, double y, double z) {
        public static final Vec ZERO = new Vec(0, 0, 0);

        public Vec add(Vec o) {
            return new Vec(x + o.x, y + o.y, z + o.z);
        }

        public Vec scale(double k) {
            return new Vec(x * k, y * k, z * k);
        }

        public double dist(Vec o) {
            return Math.sqrt((x - o.x) * (x - o.x) + (y - o.y) * (y - o.y) + (z - o.z) * (z - o.z));
        }
    }

    /** Horizontal forward of a yaw (degrees). */
    public static Vec forward(double yawDeg) {
        double a = Math.toRadians(yawDeg);
        return new Vec(-Math.sin(a), 0, Math.cos(a));
    }

    /** Horizontal right of a yaw: facing +Z (yaw 0), the right hand is -X. */
    public static Vec right(double yawDeg) {
        double a = Math.toRadians(yawDeg);
        return new Vec(-Math.cos(a), 0, -Math.sin(a));
    }

    /** base + offset in view axes: x to the right, y up, z forward (horizontal, by yaw only). */
    public static Vec offset(Vec base, double yawDeg, double x, double y, double z) {
        return base.add(right(yawDeg).scale(x)).add(new Vec(0, y, 0)).add(forward(yawDeg).scale(z));
    }

    /** One child of an arc: where and how many ticks after the parent is formed. */
    public record Placed(Vec pos, int delay) {}

    /**
     * Children on an arc around a centre (docs/sigils.md, onFormed.arc): count points over `angle` degrees,
     * centred behind the caster when `behind`, else in front; a slight wave in height so the arc reads as a crown.
     */
    public static List<Placed> arc(SigilDef.Arc arc, Vec centre, double yawDeg) {
        List<Placed> out = new ArrayList<>();
        Vec f = forward(yawDeg), left = right(yawDeg).scale(-1);
        double back = arc.behind() ? -1 : 1;
        for (int i = 0; i < arc.count(); i++) {
            double u = arc.count() > 1 ? (double) i / (arc.count() - 1) : 0.5;
            double th = Math.toRadians(-arc.angle() / 2 + arc.angle() * u);
            Vec p = centre.add(left.scale(Math.sin(th) * arc.radius()))
                    .add(f.scale(back * Math.cos(th) * arc.radius()))
                    .add(new Vec(0, arc.height() + Math.cos(th * 2) * 0.12, 0));
            out.add(new Placed(p, i * arc.stagger()));
        }
        return out;
    }

    /** One beam of a beam rain: tick offset from the element start and the ground point it hits. */
    public record Strike(int tick, double x, double z) {}

    /** Beam rain strike points, uniform over a disc of radius `area` around the centre; deterministic by seed. */
    public static List<Strike> beamRain(long seed, Vec centre, double area, int count, int interval) {
        SplittableRandom r = new SplittableRandom(seed);
        List<Strike> out = new ArrayList<>(count);
        for (int i = 0; i < count; i++) {
            double a = r.nextDouble() * Math.PI * 2, d = Math.sqrt(r.nextDouble()) * area;
            out.add(new Strike(i * Math.max(0, interval), centre.x() + Math.cos(a) * d, centre.z() + Math.sin(a) * d));
        }
        return out;
    }
}
