package ru.pohsmp.core.fx.sigil;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.util.ArrayList;
import java.util.EnumSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;

/**
 * A sigil definition read from assets/pohsmp_core/sigils/&lt;id&gt;.json. Format: docs/sigils.md.
 * Pure data: no Minecraft classes, so the server can read it for timings and tests can run without the game.
 * Times are ticks, angles degrees, sizes blocks.
 */
public record SigilDef(String id, double size, int color, Orientation orientation, int lifetime, int hold,
                       List<Layer> layers, Expand expand, Flash formedFlash, List<Child> onFormed, Dissolve dissolve,
                       GroundLight groundLight, BlockGlow blockGlow, Hit hit) {

    /** OUTWARD: fixed, laid on a sphere around the element's anchor (normal from the anchor to the sigil), e.g. seals on a dome. */
    public enum Orientation { GROUND, SKY, FACING, BILLBOARD, OUTWARD }

    /** TEXT — an inscription (T07): letters from a glyph atlas along the circle {@code radius} or a line, see {@link SigilText}. */
    public enum LayerType { DISC, BAND, ARCS, SPOKES, TEXT }

    public enum AppearMode { GROW, FADE, DRAW, TWIST, UNFOLD, ASSEMBLE, PIECES }

    public enum DissolveMode { REVERSE, COLLAPSE, FADE, SHATTER, CRACKS }

    public record Appear(int delay, int duration, Easing easing, Set<AppearMode> modes, double startAngle, int direction, double twist,
                         Pieces pieces) {
        public int end() {
            return delay + duration;
        }
    }

    /** Order in which pieces arrive. */
    public enum PieceOrder { SCATTER, AROUND, ALTERNATE }

    /**
     * Mode {@code pieces}: the layer is cut into {@code count} equal sectors that fly in one after another and lock into place.
     * pieceTime — share of appear.duration one piece flies; fly — extra distance from the centre (share of radius); lift — height
     * above the plane (share of radius); orbit — degrees around the centre; tilt — degrees around the piece's tangent;
     * spin — degrees around its own centre; lockFlash — extra brightness at the moment it locks.
     */
    public record Pieces(int count, double pieceTime, PieceOrder order, double fly, double lift, double orbit, double tilt, double spin,
                         double lockFlash) {
        public static final Pieces DEFAULT = new Pieces(8, 0.45, PieceOrder.SCATTER, 0.9, 0.5, 40, 75, 120, 0.8);
    }

    public record Rotation(double speed, double boost) {
        public static final Rotation NONE = new Rotation(0, 0);
    }

    public record Pulse(double amp, double period) {}

    public record Layer(String id, LayerType type, String texture, double radius, double heightOffset, int color, double brightness,
                        double inner, int repeat, int count, double arcLength, double width,
                        Appear appear, Rotation rotation, Pulse pulse, SigilText.Spec text) {}

    public record Expand(double scale, int delay, int duration, Easing easing) {}

    public record Flash(int color, double size, int duration, int sparks) {}

    /** Child sigils spawned when the parent is formed; arc == null means "at the parent's centre". */
    public record Child(String id, boolean anchorCaster, Arc arc) {}

    public record Arc(int count, double radius, double angle, double height, boolean behind, int stagger) {}

    public record Dissolve(Set<DissolveMode> modes, int duration, int stagger, Cracks cracks) {
        public static final Dissolve DEFAULT = new Dissolve(EnumSet.of(DissolveMode.FADE), 20, 0, null);

        /** Parameters of the {@code cracks} mode (defaults when the mode is on without its own block), or null if it is off. */
        public Cracks cracksOrNull() {
            return modes.contains(DissolveMode.CRACKS) ? cracks != null ? cracks : Cracks.DEFAULT : null;
        }
    }

    /**
     * Dissolve mode {@code cracks} (T09, docs/sigils.md "Распад трещинами"): cracks run from the centre to the rim along {@code count}
     * uneven radial lines (plus {@code rings} circular ones), the sigil breaks into count·(rings+1) shards that tumble down and go out.
     * Shares of the dissolve duration: crackTime — cracks spread; fallTime — one shard falls. Distances in sigil radii.
     */
    public record Cracks(int count, int rings, double irregular, double jag, double crackTime, double fallTime, double gap, double push,
                         double pop, double fall, double tumble, double spin, double glow, int dust, int color) {
        public static final Cracks DEFAULT = new Cracks(9, 1, 0.35, 0.22, 0.4, 0.45, 0.03, 0.25, 0.25, 1.2, 150, 60, 1.4, 28, -1);
    }

    /**
     * Response to hits (T08, docs/sigils.md "Отклик на удар"): a ring of light runs from the hit point to the rim in
     * {@code duration} ticks (and {@code rings - 1} weaker ripples behind it, {@code spacing} radii apart), the sigil flinches
     * (scale ±{@code shake}, wobble by {@code tilt}°), {@code sparks} sparks fly from the point, the point flashes.
     * color: sparks and flash (-1 = mix of the sigil colour and white). max — hits drawn at once; cooldown — ticks a new hit
     * near an old one is merged into it. sheen — the same wave as plain light over the whole disc of the sigil (so the ring reads
     * on sparse patterns too), share of the brightness on the layers.
     */
    public record Hit(int duration, double width, double strength, int rings, double spacing, double shake, double shakePeriod,
                      double tilt, double flash, int sparks, double sparkSpeed, int color, int max, int cooldown, double sheen) {
        public static final Hit DEFAULT = new Hit(8, 0.1, 1.0, 3, 0.26, 0.02, 4, 2.5, 0.9, 10, 0.16, -1, 4, 2, 0.35);
    }

    /**
     * Soft disc of the sigil's colour on the nearest surface under it, follows the sigil. radius — share of the sigil's current
     * radius (grows with expand, shrinks with collapse); strength — brightness 0..1+; reach — how far down (blocks) to look for
     * the surface. null = off.
     */
    public record GroundLight(double radius, double strength, double reach) {
        public static final GroundLight DEFAULT = new GroundLight(0.8, 0.6, 32);
    }

    /**
     * Top faces of blocks within radius (share of the sigil's current radius, around the point under its centre) tinted with its
     * colour, dimmer towards the edge. strength — brightness at the centre; falloff — edge exponent (1 linear, 2 softer centre);
     * reach — how far down (blocks) to look for the ground under the sigil. null = off.
     */
    public record BlockGlow(double radius, double strength, double falloff, double reach) {
        public static final BlockGlow DEFAULT = new BlockGlow(1.1, 0.35, 1.5, 32);

        /** Brightness at relative distance x = dist / radius: strength at 0, 0 at 1 and beyond. */
        public double at(double x) {
            if (x >= 1) return 0;
            return strength * Math.pow(1 - Math.max(0, x), falloff);
        }
    }

    // ------------------------------------------------------------------ parsing

    public static SigilDef parse(String id, String json) {
        return parse(id, JsonParser.parseString(json).getAsJsonObject());
    }

    public static SigilDef parse(String id, JsonObject o) {
        int color = color(str(o, "color", "#FFFFFF"));
        List<Layer> layers = new ArrayList<>();
        for (JsonElement e : arr(o, "layers")) layers.add(layer(e.getAsJsonObject(), color));
        Expand expand = null;
        if (o.has("expand")) {
            JsonObject x = o.getAsJsonObject("expand");
            expand = new Expand(num(x, "scale", 1), (int) num(x, "delay", 0), (int) num(x, "duration", 0), Easing.byName(str(x, "easing", null)));
        }
        Flash flash = null;
        if (o.has("formedFlash")) {
            JsonObject f = o.getAsJsonObject("formedFlash");
            flash = new Flash(color(str(f, "color", "#FFFFFF")), num(f, "size", 1.2), (int) num(f, "duration", 10), (int) num(f, "sparks", 0));
        }
        List<Child> children = new ArrayList<>();
        for (JsonElement e : arr(o, "onFormed")) {
            JsonObject c = e.getAsJsonObject();
            Arc arc = null;
            if (c.has("arc")) {
                JsonObject a = c.getAsJsonObject("arc");
                arc = new Arc((int) num(a, "count", 1), num(a, "radius", 1), num(a, "angle", 0), num(a, "height", 0),
                        bool(a, "behind", false), (int) num(a, "stagger", 0));
            }
            children.add(new Child(str(c, "id", ""), "caster".equals(str(c, "anchor", "")), arc));
        }
        Dissolve dissolve = Dissolve.DEFAULT;
        if (o.has("dissolve")) {
            JsonObject d = o.getAsJsonObject("dissolve");
            Set<DissolveMode> modes = EnumSet.noneOf(DissolveMode.class);
            for (JsonElement m : arr(d, "modes")) modes.add(DissolveMode.valueOf(m.getAsString().toUpperCase(Locale.ROOT)));
            if (d.has("mode")) modes.add(DissolveMode.valueOf(str(d, "mode", "fade").toUpperCase(Locale.ROOT)));
            if (modes.isEmpty()) modes.add(DissolveMode.FADE);
            Cracks cracks = null;
            if (d.has("cracks") && d.get("cracks").isJsonObject()) {
                JsonObject c = d.getAsJsonObject("cracks");
                Cracks k = Cracks.DEFAULT;
                cracks = new Cracks(Math.max(3, (int) num(c, "count", k.count())), Math.max(0, Math.min(3, (int) num(c, "rings", k.rings()))),
                        clamp(num(c, "irregular", k.irregular()), 0, 0.8), clamp(num(c, "jag", k.jag()), 0, 0.45),
                        clamp(num(c, "crackTime", k.crackTime()), 0.05, 0.9), clamp(num(c, "fallTime", k.fallTime()), 0.05, 0.95),
                        num(c, "gap", k.gap()), num(c, "push", k.push()), num(c, "pop", k.pop()), num(c, "fall", k.fall()),
                        num(c, "tumble", k.tumble()), num(c, "spin", k.spin()), Math.max(0, num(c, "glow", k.glow())),
                        Math.max(0, (int) num(c, "dust", k.dust())), c.has("color") ? color(str(c, "color", "#FFFFFF")) : k.color());
            }
            dissolve = new Dissolve(modes, (int) num(d, "duration", 20), (int) num(d, "stagger", 0), cracks);
        }
        GroundLight gl = null;
        if (o.has("groundLight") && !o.get("groundLight").isJsonNull() && !isFalse(o.get("groundLight"))) {
            JsonObject g = o.get("groundLight").isJsonObject() ? o.getAsJsonObject("groundLight") : new JsonObject();
            GroundLight d = GroundLight.DEFAULT;
            gl = new GroundLight(Math.max(0.01, num(g, "radius", d.radius())), Math.max(0, num(g, "strength", d.strength())),
                    Math.max(1, num(g, "reach", d.reach())));
        }
        BlockGlow bg = null;
        if (o.has("blockGlow") && !o.get("blockGlow").isJsonNull() && !isFalse(o.get("blockGlow"))) {
            JsonObject g = o.get("blockGlow").isJsonObject() ? o.getAsJsonObject("blockGlow") : new JsonObject();
            BlockGlow d = BlockGlow.DEFAULT;
            bg = new BlockGlow(Math.max(0.01, num(g, "radius", d.radius())), Math.max(0, num(g, "strength", d.strength())),
                    Math.max(0.1, num(g, "falloff", d.falloff())), Math.max(1, num(g, "reach", d.reach())));
        }
        return new SigilDef(id, num(o, "size", 1), color, Orientation.valueOf(str(o, "orientation", "ground").toUpperCase(Locale.ROOT)),
                (int) num(o, "lifetime", -1), (int) num(o, "hold", -1), List.copyOf(layers), expand, flash, List.copyOf(children), dissolve,
                gl, bg, parseHit(o));
    }

    /**
     * {@code "hit": {...}} / {@code true} / {@code {}} or {@code "reactsToHits": true} of a sigil (or of a mesh, MeshDraw) -> Hit with
     * defaults for missing fields; null when absent or {@code "hit": false}.
     */
    public static Hit parseHit(JsonObject o) {
        Hit hit = null;
        boolean hitOn = o.has("hit") && !o.get("hit").isJsonNull() && !isFalse(o.get("hit"));
        if (hitOn || o.has("reactsToHits") && o.get("reactsToHits").isJsonPrimitive() && o.get("reactsToHits").getAsBoolean()) {
            JsonObject h = hitOn && o.get("hit").isJsonObject() ? o.getAsJsonObject("hit") : new JsonObject();
            Hit d = Hit.DEFAULT;
            hit = new Hit(Math.max(1, (int) num(h, "duration", d.duration())), Math.max(0.02, num(h, "width", d.width())),
                    Math.max(0, num(h, "strength", d.strength())), Math.max(1, Math.min(6, (int) num(h, "rings", d.rings()))),
                    Math.max(0.02, num(h, "spacing", d.spacing())), Math.max(0, num(h, "shake", d.shake())),
                    Math.max(1, num(h, "shakePeriod", d.shakePeriod())), num(h, "tilt", d.tilt()), Math.max(0, num(h, "flash", d.flash())),
                    Math.max(0, Math.min(64, (int) num(h, "sparks", d.sparks()))), Math.max(0, num(h, "sparkSpeed", d.sparkSpeed())),
                    h.has("color") ? color(str(h, "color", "#FFFFFF")) : d.color(), Math.max(1, Math.min(16, (int) num(h, "max", d.max()))),
                    Math.max(0, (int) num(h, "cooldown", d.cooldown())), Math.max(0, num(h, "sheen", d.sheen())));
        }
        return hit;
    }

    /** Largest layer radius (share of size, at least 1): how far the sigil really reaches. */
    public double reach() {
        double r = 1;
        for (Layer l : layers) r = Math.max(r, l.radius());
        return r;
    }

    private static double clamp(double x, double lo, double hi) {
        return Math.max(lo, Math.min(hi, x));
    }

    /** {@code "groundLight": false} switches the flag off explicitly; {@code true} means "on with defaults". */
    private static boolean isFalse(JsonElement e) {
        return e.isJsonPrimitive() && e.getAsJsonPrimitive().isBoolean() && !e.getAsBoolean();
    }

    private static Layer layer(JsonObject l, int defColor) {
        JsonObject ap = l.has("appear") ? l.getAsJsonObject("appear") : new JsonObject();
        Set<AppearMode> modes = EnumSet.noneOf(AppearMode.class);
        for (JsonElement m : arr(ap, "modes")) modes.add(AppearMode.valueOf(m.getAsString().toUpperCase(Locale.ROOT)));
        if (modes.isEmpty()) modes.add(AppearMode.FADE);
        Pieces pieces = null;
        if (modes.contains(AppearMode.PIECES)) {
            JsonObject pc = ap.has("pieces") && ap.get("pieces").isJsonObject() ? ap.getAsJsonObject("pieces") : new JsonObject();
            Pieces d = Pieces.DEFAULT;
            pieces = new Pieces(Math.max(1, (int) num(pc, "count", d.count())), Math.max(0.05, Math.min(1, num(pc, "pieceTime", d.pieceTime()))),
                    PieceOrder.valueOf(str(pc, "order", "scatter").toUpperCase(Locale.ROOT)), num(pc, "fly", d.fly()), num(pc, "lift", d.lift()),
                    num(pc, "orbit", d.orbit()), num(pc, "tilt", d.tilt()), num(pc, "spin", d.spin()), num(pc, "lockFlash", d.lockFlash()));
        }
        Appear appear = new Appear((int) num(ap, "delay", 0), Math.max(1, (int) num(ap, "duration", 1)), Easing.byName(str(ap, "easing", null)),
                modes, num(ap, "startAngle", 0), (int) num(ap, "direction", 1), num(ap, "twist", -120), pieces);
        Rotation rot = Rotation.NONE;
        if (l.has("rotation")) {
            JsonObject r = l.getAsJsonObject("rotation");
            rot = new Rotation(num(r, "speed", 0), num(r, "boost", 0));
        }
        Pulse pulse = null;
        if (l.has("pulse")) {
            JsonObject p = l.getAsJsonObject("pulse");
            pulse = new Pulse(num(p, "amp", 0), Math.max(1, num(p, "period", 20)));
        }
        LayerType type = LayerType.valueOf(str(l, "type", "disc").toUpperCase(Locale.ROOT));
        return new Layer(str(l, "id", ""), type, str(l, "texture", "core"),
                num(l, "radius", 1), num(l, "heightOffset", 0), l.has("color") ? color(str(l, "color", "#FFFFFF")) : defColor,
                num(l, "brightness", 1), num(l, "inner", 0.85), (int) num(l, "repeat", 6), (int) num(l, "count", 4),
                num(l, "arcLength", 45), num(l, "width", 0.05), appear, rot, pulse, type == LayerType.TEXT ? SigilText.Spec.parse(l) : null);
    }

    static int color(String hex) {
        String h = hex.startsWith("#") ? hex.substring(1) : hex;
        return Integer.parseInt(h, 16) & 0xFFFFFF;
    }

    private static JsonArray arr(JsonObject o, String k) {
        return o.has(k) && o.get(k).isJsonArray() ? o.getAsJsonArray(k) : new JsonArray();
    }

    private static double num(JsonObject o, String k, double d) {
        return o.has(k) ? o.get(k).getAsDouble() : d;
    }

    private static String str(JsonObject o, String k, String d) {
        return o.has(k) ? o.get(k).getAsString() : d;
    }

    private static boolean bool(JsonObject o, String k, boolean d) {
        return o.has(k) ? o.get(k).getAsBoolean() : d;
    }
}
