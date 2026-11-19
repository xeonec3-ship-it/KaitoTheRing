package ru.pohsmp.core.fx.sigil;

import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.function.Function;

/**
 * Inscriptions on sigils (layer type {@code text}, T07, docs/sigils.md «Надписи»): glyph atlases, where every letter goes and how it
 * appears letter by letter. Pure math, no Minecraft: the client renderer draws one textured square per {@link Letter}, the preview
 * (tools/sigil_preview.template.html) uses the same formulas.
 *
 * <p>Units: positions and sizes are in sigil units (the same as layer radii: share of {@code size}), angles in degrees, counter-clockwise
 * from the plane's u axis (90 = top). A glyph's "up" is the direction from its baseline to its top.
 */
public final class SigilText {
    private SigilText() {}

    /** outer — letters stand on the circle with their tops outwards, read clockwise (top of a coin); inner — tops to the centre,
     *  read counter-clockwise (bottom of a coin); line — a straight line through the centre (radius = its offset along v). */
    public enum Side { OUTER, INNER, LINE }

    /** Which point of the text sits at {@code angle} (circle) or at the centre (line). */
    public enum Align { CENTER, START, END }

    /**
     * Text settings of a layer. size — glyph cell height (sigil units); spacing — extra gap between letters (share of size);
     * repeat — copies around the circle (0 = as many as fit); angle — where the text is anchored (degrees; NaN = default: 90 for
     * outer, 270 for inner, 0 for line); slot — name under which the text can be replaced at start or later (null = fixed);
     * change — ticks a replaced text takes to write itself in; changeFlash — extra brightness at the moment of replacement;
     * fit — shrink the letters when the text does not fit its share of the circle.
     */
    public record Spec(String text, String font, double size, double spacing, int repeat, Side side, Align align, double angle,
                       String slot, int change, double changeFlash, boolean fit) {
        public static final double DEFAULT_SIZE = 0.12;

        public double anchorAngle() {
            if (!Double.isNaN(angle)) return angle;
            return side == Side.OUTER ? 90 : side == Side.INNER ? 270 : 0;
        }

        public static Spec parse(JsonObject l) {
            String side = str(l, "side", "outer"), align = str(l, "align", "center");
            return new Spec(str(l, "text", ""), str(l, "font", "latin").toLowerCase(Locale.ROOT), Math.max(0.005, num(l, "size", DEFAULT_SIZE)),
                    num(l, "spacing", 0.06), Math.max(0, (int) num(l, "repeat", 1)), Side.valueOf(side.toUpperCase(Locale.ROOT)),
                    Align.valueOf(align.toUpperCase(Locale.ROOT)), l.has("angle") ? num(l, "angle", 0) : Double.NaN,
                    l.has("slot") ? str(l, "slot", "") : null, Math.max(1, (int) num(l, "change", 6)), num(l, "changeFlash", 0.8),
                    !l.has("fit") || l.get("fit").getAsBoolean());
        }
    }

    // ---------------------------------------------------------------- fonts (textures/sigil/glyphs_<name>.json)

    /** One glyph: atlas cell and advance (share of the cell height). */
    public record Glyph(int cell, double advance) {}

    /**
     * A glyph atlas written by tools/gen_sigil_glyphs.py. Cell k is column k % cols, row k / cols. baseline / capHeight — shares
     * of the cell from its top; space — advance of a space; upper — look letters up in upper case (runes); fallback — font to try
     * for characters this one lacks.
     */
    public record Font(String name, String texture, int cols, int rows, double baseline, double capHeight, double space, boolean upper,
                       String fallback, Map<Integer, Glyph> glyphs) {
        public static Font parse(String json) {
            JsonObject o = JsonParser.parseString(json).getAsJsonObject();
            Map<Integer, Glyph> g = new HashMap<>();
            for (Map.Entry<String, JsonElement> e : o.getAsJsonObject("glyphs").entrySet()) {
                var a = e.getValue().getAsJsonArray();
                g.put(e.getKey().codePointAt(0), new Glyph(a.get(0).getAsInt(), a.get(1).getAsDouble()));
            }
            String fb = o.has("fallback") && !o.get("fallback").isJsonNull() ? o.get("fallback").getAsString() : null;
            return new Font(str(o, "font", "?"), str(o, "texture", "glyphs_latin"), (int) num(o, "cols", 16), (int) num(o, "rows", 1),
                    num(o, "baseline", 0.7), num(o, "capHeight", 0.44), num(o, "space", 0.25), o.has("upper") && o.get("upper").getAsBoolean(),
                    fb, Collections.unmodifiableMap(g));
        }

        /** Texture coordinates of a cell: {u0, v0, u1, v1} (v0 at the top). */
        public float[] uv(int cell) {
            int cx = cell % cols, cy = cell / cols;
            return new float[] {(float) cx / cols, (float) cy / rows, (float) (cx + 1) / cols, (float) (cy + 1) / rows};
        }

        Glyph find(int cp) {
            Glyph g = glyphs.get(cp);
            if (g == null && upper) g = glyphs.get(Character.toUpperCase(cp));
            if (g == null) g = glyphs.get(Character.toLowerCase(cp));
            if (g == null) g = glyphs.get(Character.toUpperCase(cp));
            return g;
        }
    }

    /** A glyph found in some font of the chain (the font is needed for its texture). */
    public record Resolved(Font font, Glyph glyph) {}

    /** Looks cp up in the font, then in its fallbacks (at most 4 deep). null — no such glyph anywhere. */
    public static Resolved resolve(Font font, int cp, Function<String, Font> fonts) {
        Font f = font;
        for (int depth = 0; f != null && depth < 5; depth++) {
            Glyph g = f.find(cp);
            if (g != null) return new Resolved(f, g);
            f = f.fallback() == null ? null : fonts.apply(f.fallback());
        }
        return null;
    }

    // ---------------------------------------------------------------- layout

    /**
     * One letter to draw: glyph cell centre (x, y) in sigil units, the angle of its "up" (degrees), its square side, the atlas
     * (texture, cell, uv) and its place in reading order within its copy (0 = first), for {@link #reveal}.
     */
    public record Letter(String texture, int cell, float[] uv, double x, double y, double up, double size, int order, int copy) {}

    /** Letters plus how many drawable letters one copy has and how many copies were laid out (repeat 0 resolves here). */
    public record Layout(List<Letter> letters, int perCopy, int copies, double size) {
        public static final Layout EMPTY = new Layout(List.of(), 0, 0, 0);
    }

    private record Item(Resolved r, double advance) {}

    /**
     * Lays text out on the circle {@code radius} (sigil units) — or on a straight line for {@link Side#LINE} — as docs/sigils.md says:
     * <pre>
     * advance_i = glyph advance · size;  between letters + spacing · size;  L = Σ advance + spacing · size · (n − 1)
     * circle: the middle of capitals lies on the radius; letter centre angle θ_i = A + dir · (pos_i − anchor) / r (radians → degrees),
     *         dir = −1 for outer (clockwise), +1 for inner; pos_i = start of letter + advance_i / 2; anchor = L/2, 0 or L (align)
     * copies: n = repeat, or (repeat 0) ⌊2πr / (L + space·size)⌋, at A − k·360/n (outer) / A + k·360/n (inner)
     * fit: if L / r > 0.97 · 2π / n, size shrinks so it fits
     * </pre>
     */
    public static Layout layout(Spec s, String text, double radius, Font font, Function<String, Font> fonts) {
        if (font == null || text == null || text.isEmpty()) return Layout.EMPTY;
        List<Item> items = new ArrayList<>();
        text.codePoints().forEach(cp -> {
            if (Character.isWhitespace(cp)) {
                items.add(new Item(null, font.space()));
                return;
            }
            Resolved r = resolve(font, cp, fonts);
            items.add(r == null ? new Item(null, font.space()) : new Item(r, r.glyph().advance()));
        });
        double sumAdv = 0;
        for (Item it : items) sumAdv += it.advance;
        double units = sumAdv + s.spacing() * Math.max(0, items.size() - 1);      // length in sizes
        double size = s.size();
        double r = Math.abs(radius);
        boolean line = s.side() == Side.LINE || r < 1e-4;
        int copies = 1;
        if (!line) {
            if (s.repeat() == 0) {
                double gap = font.space() + s.spacing();
                copies = Math.max(1, (int) Math.floor(2 * Math.PI * r / ((units + gap) * size)));
            } else copies = s.repeat();
            double avail = 0.97 * 2 * Math.PI * r / copies;
            if (s.fit() && units * size > avail) size = avail / units;
        }
        double len = units * size;
        double anchor = s.align() == Align.CENTER ? len / 2 : s.align() == Align.START ? 0 : len;
        // the middle of capitals sits on the line/circle; the cell centre is (0.5 − (baseline − cap/2)) · size below it
        double drop = (0.5 - (font.baseline() - font.capHeight() / 2)) * size;
        List<Letter> out = new ArrayList<>();
        int perCopy = 0;
        for (Item it : items) if (it.r != null) perCopy++;
        double A = s.anchorAngle();
        for (int c = 0; c < copies; c++) {
            double pos = 0;
            int order = 0;
            for (int i = 0; i < items.size(); i++) {
                Item it = items.get(i);
                double adv = it.advance * size, mid = pos + adv / 2 - anchor;
                pos += adv + s.spacing() * size;
                if (it.r == null) continue;
                Glyph g = it.r.glyph();
                if (line) {
                    double k = Math.toRadians(A), ux = Math.cos(k), uy = Math.sin(k), vx = -uy, vy = ux;     // along and up the line
                    double off = radius - drop;
                    out.add(new Letter(it.r.font().texture(), g.cell(), it.r.font().uv(g.cell()), ux * mid + vx * off, uy * mid + vy * off,
                            A + 90, size, order++, 0));
                } else {
                    boolean outer = s.side() == Side.OUTER;
                    double dir = outer ? -1 : 1, base = A + dir * c * 360.0 / copies;
                    double th = base + dir * Math.toDegrees(mid / r);
                    double up = outer ? th : th + 180;
                    double rc = r - drop * (outer ? 1 : -1);                                    // cell centre radius
                    double k = Math.toRadians(th);
                    out.add(new Letter(it.r.font().texture(), g.cell(), it.r.font().uv(g.cell()), Math.cos(k) * rc, Math.sin(k) * rc, up,
                            size, order++, c));
                }
            }
        }
        return new Layout(List.copyOf(out), perCopy, line ? 1 : copies, size);
    }

    // ---------------------------------------------------------------- appearing

    /** How one letter looks while it appears: opacity, extra scale (starts larger and settles), extra brightness (a flare as it lands). */
    public record LetterState(double alpha, double scale, double brightness) {
        public static final LetterState SHOWN = new LetterState(1, 1, 1);
    }

    /** Letters fade in over this many letter-steps (a soft pen front). */
    public static final double SOFT = 1.5;

    /**
     * Letter-by-letter writing ({@code draw}): at progress p (0..1) letter k (reading order; reversed when direction &lt; 0) has
     * <pre>
     * x = p · (count + SOFT) − k;   alpha = clamp01(x / SOFT);   scale = 1 + 0.35 · (1 − alpha);   brightness = 1 + 0.9 · 4·alpha·(1 − alpha)
     * </pre>
     * so the first letter starts at p = 0 and the last one is fully written exactly at p = 1.
     */
    public static LetterState reveal(int order, int count, double progress, int direction) {
        if (progress >= 1 || count <= 0) return LetterState.SHOWN;
        if (progress <= 0) return new LetterState(0, 1.35, 1);
        int k = direction < 0 ? count - 1 - order : order;
        double a = clamp01((progress * (count + SOFT) - k) / SOFT);
        return new LetterState(a, 1 + 0.35 * (1 - a), 1 + 0.9 * 4 * a * (1 - a));
    }

    /** Progress of writing in a replaced text, {@code since} ticks after the replacement (≥ change → 1). */
    public static double changeProgress(double since, int change) {
        if (Double.isNaN(since)) return 1;
        return clamp01(since / Math.max(1, change));
    }

    /** Whole-layer brightness right after a replacement: 1 + changeFlash · (1 − p)², p = changeProgress. */
    public static double changeFlash(double since, int change, double flash) {
        double p = changeProgress(since, change);
        return 1 + flash * (1 - p) * (1 - p);
    }

    /** The text a layer shows: the replacement for its slot if there is one, else its own. */
    public static String textFor(Spec s, Map<String, String> replaced) {
        if (s.slot() != null && replaced != null) {
            String r = replaced.get(s.slot());
            if (r != null) return r;
        }
        return s.text();
    }

    static double clamp01(double x) {
        return Math.max(0, Math.min(1, x));
    }

    private static double num(JsonObject o, String k, double d) {
        return o.has(k) ? o.get(k).getAsDouble() : d;
    }

    private static String str(JsonObject o, String k, String d) {
        return o.has(k) && !o.get(k).isJsonNull() ? o.get(k).getAsString() : d;
    }
}
