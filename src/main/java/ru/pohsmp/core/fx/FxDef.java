package ru.pohsmp.core.fx;

import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * An effect (assets/pohsmp_core/fx/&lt;id&gt;.json, docs/fx.md): elements on one timeline.
 * Each element keeps its type-specific parameters as raw JSON ({@link Element#params}); the renderer of a type reads them.
 */
public record FxDef(String id, String style, int duration, List<Element> elements) {

    public record Element(String type, int delay, int duration, Anchor at, Anchor to, boolean follow, String color,
                          double brightness, double scale, JsonObject params) {
        public int end() {
            return duration < 0 ? Integer.MAX_VALUE : delay + duration;
        }

        public boolean activeAt(double t) {
            return t >= delay && t < end();
        }

        public double num(String key, double def) {
            return params.has(key) ? params.get(key).getAsDouble() : def;
        }

        public String str(String key, String def) {
            return params.has(key) ? params.get(key).getAsString() : def;
        }
    }

    public static FxDef parse(String id, String json) {
        JsonObject o = JsonParser.parseString(json).getAsJsonObject();
        List<Element> els = new ArrayList<>();
        if (o.has("elements")) for (JsonElement e : o.getAsJsonArray("elements")) els.add(element(e.getAsJsonObject()));
        return new FxDef(id, o.has("style") ? o.get("style").getAsString() : "divine",
                o.has("duration") ? o.get("duration").getAsInt() : -1, List.copyOf(els));
    }

    private static Element element(JsonObject e) {
        return new Element(e.get("type").getAsString(), e.has("delay") ? e.get("delay").getAsInt() : 0,
                e.has("duration") ? e.get("duration").getAsInt() : -1,
                Anchor.parse(e.has("at") ? e.get("at").getAsString() : "caster"),
                e.has("to") ? Anchor.parse(e.get("to").getAsString()) : null,
                e.has("follow") && e.get("follow").getAsBoolean(), e.has("color") ? e.get("color").getAsString() : null,
                e.has("brightness") ? e.get("brightness").getAsDouble() : 1, e.has("scale") ? e.get("scale").getAsDouble() : 1, e);
    }

    /** Where an element is: "caster", "target", "caster.eyes", "caster.hand", "point:name", "look:24", each with an optional "+x,y,z". */
    public record Anchor(String kind, String arg, double ox, double oy, double oz) {
        public static Anchor parse(String s) {
            String base = s, off = null;
            int plus = s.indexOf('+');
            if (plus >= 0) {
                base = s.substring(0, plus);
                off = s.substring(plus + 1);
            }
            double x = 0, y = 0, z = 0;
            if (off != null) {
                String[] p = off.split(",");
                x = Double.parseDouble(p[0].trim());
                y = p.length > 1 ? Double.parseDouble(p[1].trim()) : 0;
                z = p.length > 2 ? Double.parseDouble(p[2].trim()) : 0;
            }
            String kind = base, arg = null;
            int colon = base.indexOf(':');
            if (colon >= 0) {
                kind = base.substring(0, colon);
                arg = base.substring(colon + 1);
            }
            return new Anchor(kind.trim(), arg, x, y, z);
        }

        /** World point for this anchor; offsets are in the caster's view axes (x right, y up, z forward). */
        public FxMath.Vec resolve(Context ctx) {
            FxMath.Vec base = switch (kind) {
                case "caster" -> ctx.caster();
                case "caster.eyes" -> ctx.eyes();
                case "caster.hand" -> ctx.hand();
                case "target" -> ctx.target() != null ? ctx.target() : ctx.caster();
                case "point" -> ctx.points().getOrDefault(arg, ctx.caster());
                case "look" -> ctx.look() != null ? ctx.look() : ctx.eyes().add(FxMath.forward(ctx.yaw()).scale(arg == null ? 16 : Double.parseDouble(arg)));
                default -> ctx.caster();
            };
            return FxMath.offset(base, ctx.yaw(), ox, oy, oz);
        }
    }

    /**
     * Who and where: filled by the spell on the server (and sent to clients). `look` is the ray-traced point of the caster's view,
     * if the spell computed it; otherwise "look:N" takes N blocks straight ahead from the eyes.
     */
    public record Context(FxMath.Vec caster, FxMath.Vec eyes, FxMath.Vec hand, double yaw, FxMath.Vec target, FxMath.Vec look,
                          Map<String, FxMath.Vec> points, double scale, long seed) {}
}
