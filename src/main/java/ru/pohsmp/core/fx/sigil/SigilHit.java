package ru.pohsmp.core.fx.sigil;

import java.util.List;
import ru.pohsmp.core.fx.sigil.SigilDef.Hit;

/**
 * Response of a sigil to a hit (T08, docs/sigils.md "Отклик на удар"): the formulas the client renderer and
 * tools/sigil_preview.html share. Pure math, no Minecraft.
 *
 * <p>Plane coordinates: (x, y) in the sigil plane along its axes (u, v), centre (0, 0), unit = the sigil's current radius
 * ({@link SigilTimeline#globalScale}, i.e. with expand, without the flinch) — the same unit as layer radii: the rim of a layer
 * of radius 1 is at distance 1. Times are ticks since the sigil started (fractional).
 */
public final class SigilHit {
    private SigilHit() {}

    /** One hit: point in plane units, tick it happened, power 0..1 (scales everything), seed for sparks. */
    public record Event(double x, double y, double at, double power, int seed) {
        public double dist() {
            return Math.hypot(x, y);
        }
    }

    /** Ripple amplitude falls by this factor from one ring to the next. */
    public static final double RING_FALLOFF = 0.55;
    /** Wobble and flinch decay time, share of hit.duration. */
    public static final double DECAY = 0.7;
    /** Gravity of sparks, blocks / tick². */
    public static final double SPARK_GRAVITY = 0.03;

    /** Ticks a hit still has something to draw (wave, flinch, sparks). */
    public static double life(Hit h) {
        return Math.max(h.duration() + 6, 18);
    }

    public static boolean alive(Hit h, Event e, double t) {
        double age = t - e.at();
        return age >= 0 && age <= life(h);
    }

    /** Distance from the hit point to the farthest point of the sigil (reach = largest layer radius, {@link SigilDef#reach()}). */
    public static double span(Event e, double reach) {
        return e.dist() + reach;
    }

    /**
     * Radius of the leading crest around the hit point: reaches the far rim exactly at hit.duration, slightly slowing
     * (front = span · f · (1.6 − 0.6 f)), then runs on at the speed it had (0.4 · span per duration) and leaves the sigil.
     */
    public static double front(Hit h, Event e, double reach, double t) {
        return frontAt(h, span(e, reach), (t - e.at()) / h.duration());
    }

    private static double frontAt(Hit h, double span, double f) {
        if (f <= 0) return 0;
        if (f <= 1) return span * f * (1.6 - 0.6 * f);
        return span * (1 + 0.4 * (f - 1));
    }

    /** Overall fade of the wave: 1 → 0.55 while it runs, then out in 6 ticks. */
    public static double envelope(Hit h, Event e, double t) {
        double age = t - e.at();
        if (age < 0) return 0;
        double f = Math.min(1, age / h.duration());
        return (1 - 0.45 * f) * clamp01((h.duration() + 6 - age) / 6);
    }

    /**
     * Extra brightness at plane point (x, y): Gaussian crests (width = hit.width) at front, front − spacing, …
     * (each next one RING_FALLOFF weaker; a crest fades in while it leaves the point), dimmer far from the point
     * (÷ (1 + 0.6·d)), plus the flash at the point itself (radius 1.2·width, decays in ~2.5 ticks).
     * Multiply the layer's colour · alpha by this and draw it over the layer (additive).
     */
    public static double glow(Hit h, Event e, double reach, double x, double y, double t) {
        return wave(h, e, span(e, reach), Math.hypot(x - e.x(), y - e.y()), t);
    }

    /**
     * The same wave on any surface, by distance {@code d} from the hit along it; {@code span} — distance from the hit to the
     * farthest point of the surface (the front gets there in hit.duration). For a dome of radius 1: d = angle between the
     * directions to the hit and to the point (radians), span = π. Used for the Barrier dome (MeshDraw "hit").
     */
    public static double wave(Hit h, Event e, double span, double d, double t) {
        double age = t - e.at();
        if (age < 0 || age > h.duration() + 6) return 0;
        double front = frontAt(h, span, age / h.duration()), sum = 0, amp = 1;
        for (int i = 0; i < h.rings(); i++) {
            double c = front - i * h.spacing();
            if (c > -h.width()) {
                double k = (d - c) / h.width();
                sum += amp * Math.exp(-k * k) * clamp01(c / h.width() + 1);
            }
            amp *= RING_FALLOFF;
        }
        double wave = h.strength() * envelope(h, e, t) * sum / (1 + 0.6 * d);
        double core = h.flash() * Math.exp(-sq(d / (h.width() * 1.2))) * Math.exp(-age / 2.5);
        return e.power() * (wave + core);
    }

    /**
     * Brightness of the plain light sheet over the sigil's disc (radius reach) at (x, y): glow · sheen, going to 0 over the
     * last 0.08 radii before the rim (the sheet must not show past the sigil).
     */
    public static double sheen(SigilDef def, List<Event> hits, double x, double y, double t) {
        Hit h = def.hit();
        if (h == null || h.sheen() <= 0) return 0;
        double reach = def.reach();
        return glow(def, hits, x, y, t) * h.sheen() * clamp01((reach * 1.02 - Math.hypot(x, y)) / 0.08);
    }

    /** Sum over all hits, capped at 2 · strength (many hits at once do not burn the sigil white). */
    public static double glow(SigilDef def, List<Event> hits, double x, double y, double t) {
        Hit h = def.hit();
        if (h == null || hits.isEmpty()) return 0;
        double reach = def.reach(), s = 0;
        for (Event e : hits) s += glow(h, e, reach, x, y, t);
        return Math.min(s, 2 * Math.max(h.strength(), h.flash()));
    }

    /**
     * Flinch: scale multiplier of the whole sigil, 1 − shake · power · e^(−age/τ) · sin(2π age / shakePeriod), τ = 0.7·duration.
     * Starts at 1 (no jump), first squeezes in, rings out.
     */
    public static double flinch(Hit h, Event e, double t) {
        double age = t - e.at();
        if (age < 0) return 1;
        return 1 - h.shake() * e.power() * Math.exp(-age / (DECAY * h.duration())) * Math.sin(2 * Math.PI * age / h.shakePeriod());
    }

    public static double scale(SigilDef def, List<Event> hits, double t) {
        Hit h = def.hit();
        if (h == null) return 1;
        double s = 1;
        for (Event e : hits) s *= flinch(h, e, t);
        return Math.max(0.8, Math.min(1.2, s));
    }

    /**
     * Wobble: turn the plane by {@code angle} degrees around the in-plane axis (ax, ay) through its centre (the axis is
     * perpendicular to the direction to the hit). Positive angle sinks the struck side along −normal first.
     */
    public record Wobble(double ax, double ay, double angle) {
        public static final Wobble NONE = new Wobble(1, 0, 0);
    }

    /**
     * angle = tilt · power · e^(−age/τ) · sin(2π age / (1.6 · shakePeriod)) · min(1, d / 0.3) — a hit at the very centre only
     * flinches. Several hits add up as vectors (axis · angle).
     */
    public static Wobble wobble(SigilDef def, List<Event> hits, double t) {
        Hit h = def.hit();
        if (h == null || h.tilt() == 0) return Wobble.NONE;
        double wx = 0, wy = 0;
        for (Event e : hits) {
            double age = t - e.at(), d = e.dist();
            if (age < 0 || d < 1e-6) continue;
            double a = h.tilt() * e.power() * Math.exp(-age / (DECAY * h.duration())) * Math.sin(2 * Math.PI * age / (1.6 * h.shakePeriod()))
                    * Math.min(1, d / 0.3);
            // axis (−y, x)/d: turning by +a around it moves the struck point (x, y) towards −normal
            wx += -e.y() / d * a;
            wy += e.x() / d * a;
        }
        double len = Math.hypot(wx, wy);
        if (len < 1e-9) return Wobble.NONE;
        return new Wobble(wx / len, wy / len, Math.max(-12, Math.min(12, len)));
    }

    /** Number of sparks of a hit: sparks · (0.4 + 0.6 · power), rounded. */
    public static int sparkCount(Hit h, Event e) {
        return (int) Math.round(h.sparks() * (0.4 + 0.6 * clamp01(e.power())));
    }

    /**
     * One spark: offset from the hit point in BLOCKS along the plane axes (u, v) and the normal (n), plus {@code drop} blocks
     * straight down in the world (gravity); alpha 0 = gone. size — billboard half-size in blocks.
     * Direction: random around, 35..100 % towards the normal; speed sparkSpeed · (0.55..1.45) blocks/tick with drag
     * (distance = speed · k · (1 − e^(−age/k)), k = life/2); life 9..16 ticks.
     */
    public record Spark(double u, double v, double n, double drop, double alpha, double size) {}

    public static Spark spark(Hit h, Event e, int i, double t) {
        double age = t - e.at();
        double r1 = rnd(e.seed(), i * 4), r2 = rnd(e.seed(), i * 4 + 1), r3 = rnd(e.seed(), i * 4 + 2), r4 = rnd(e.seed(), i * 4 + 3);
        double life = 9 + 7 * r4;
        if (age < 0 || age > life) return new Spark(0, 0, 0, 0, 0, 0);
        double th = 2 * Math.PI * r1, up = 0.35 + 0.65 * r2, side = Math.sqrt(1 - up * up);
        double speed = h.sparkSpeed() * (0.55 + 0.9 * r3), k = life * 0.5;
        double dist = speed * k * (1 - Math.exp(-age / k));
        double fade = 1 - age / life;
        return new Spark(Math.cos(th) * side * dist, Math.sin(th) * side * dist, up * dist, 0.5 * SPARK_GRAVITY * age * age,
                Math.pow(fade, 1.2), 0.03 + 0.04 * fade);
    }

    /**
     * Adds a hit to the list of live ones (drops dead ones first). A hit within {@code cooldown} ticks and 0.25 radii of a
     * live one is merged into it (keeps the stronger power) and false is returned; beyond {@code max} the oldest goes.
     */
    public static boolean accept(Hit h, List<Event> hits, Event e) {
        hits.removeIf(o -> e.at() - o.at() > life(h));
        for (int i = 0; i < hits.size(); i++) {
            Event o = hits.get(i);
            if (Math.abs(e.at() - o.at()) <= h.cooldown() && Math.hypot(e.x() - o.x(), e.y() - o.y()) <= 0.25) {
                if (e.power() > o.power()) hits.set(i, new Event(o.x(), o.y(), o.at(), e.power(), o.seed()));
                return false;
            }
        }
        while (hits.size() >= h.max()) hits.remove(0);
        hits.add(e);
        return true;
    }

    /**
     * Server side (T08): is a struck body inside the sigil, and where does the hit land on it? c — sigil centre, yaw — its view yaw
     * (for FACING), radius — its current radius in blocks (globalScale · reach), b — the middle of the struck body.
     * Flat sigils: the body must be within the radius along the plane and in a window along the normal — GROUND: 1 block under to
     * 4 above; SKY (normal down): 1 above to 48 below; FACING: ± max(1.5, radius/2). BILLBOARD / OUTWARD: within the radius + 1 of
     * the centre. Returns the point on the plane (the body projected onto it; the body itself for billboard/outward) or null.
     */
    public static double[] contact(SigilDef.Orientation o, double cx, double cy, double cz, double yaw, double radius, double bx, double by, double bz) {
        double dx = bx - cx, dy = by - cy, dz = bz - cz;
        double nx, ny, nz, below, above;
        switch (o) {
            case GROUND -> { nx = 0; ny = 1; nz = 0; below = 1; above = 4; }
            case SKY -> { nx = 0; ny = -1; nz = 0; below = 1; above = 48; }
            case FACING -> {
                double a = Math.toRadians(yaw);
                nx = -Math.sin(a); ny = 0; nz = Math.cos(a);
                below = above = Math.max(1.5, radius / 2);
            }
            default -> {
                return dx * dx + dy * dy + dz * dz <= sq(radius + 1) ? new double[] {bx, by, bz} : null;
            }
        }
        double d = dx * nx + dy * ny + dz * nz;
        if (d < -below || d > above) return null;
        double px = dx - nx * d, py = dy - ny * d, pz = dz - nz * d;
        if (px * px + py * py + pz * pz > radius * radius) return null;
        return new double[] {cx + px, cy + py, cz + pz};
    }

    /** Power of a hit from the damage dealt: 0.35 at 0, 1 at 10+ damage (5 hearts). */
    public static double powerFromDamage(double damage) {
        return clamp01(0.35 + 0.065 * Math.max(0, damage));
    }

    // ---------------------------------------------------------------- shared helpers (the same in the preview)

    /** Integer hash; the preview uses the same one (Math.imul), so random sparks and cracks match exactly. */
    public static int hash(int a, int b) {
        int h = a * 0x27D4EB2D ^ b * 0x165667B1;
        h ^= h >>> 15;
        h *= 0x2C1B3C6D;
        h ^= h >>> 12;
        h *= 0x297A2D39;
        h ^= h >>> 15;
        return h;
    }

    /** Uniform [0, 1) from (a, b). */
    public static double rnd(int a, int b) {
        return (hash(a, b) >>> 8) / 16777216.0;
    }

    static double clamp01(double x) {
        return Math.max(0, Math.min(1, x));
    }

    private static double sq(double x) {
        return x * x;
    }
}
