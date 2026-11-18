package ru.pohsmp.core.fx;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.util.HashMap;
import java.util.Map;

/**
 * A school style (assets/pohsmp_core/fx/styles/&lt;school&gt;.json, docs/fx.md): palette, default textures, blend, motion.
 * Elements refer to it as "@primary" (colour) or "@shards" (texture), so one effect recolours by changing the style.
 */
public record FxStyle(String id, Map<String, Integer> palette, Map<String, String> textures, boolean additive,
                      double rotationScale, double jitter, String easing) {

    public static FxStyle parse(String id, String json) {
        JsonObject o = JsonParser.parseString(json).getAsJsonObject();
        Map<String, Integer> pal = new HashMap<>();
        if (o.has("palette")) o.getAsJsonObject("palette").entrySet().forEach(e -> pal.put(e.getKey(), hex(e.getValue().getAsString())));
        Map<String, String> tex = new HashMap<>();
        if (o.has("textures")) o.getAsJsonObject("textures").entrySet().forEach(e -> tex.put(e.getKey(), e.getValue().getAsString()));
        JsonObject m = o.has("motion") ? o.getAsJsonObject("motion") : new JsonObject();
        return new FxStyle(id, Map.copyOf(pal), Map.copyOf(tex), !"translucent".equals(o.has("blend") ? o.get("blend").getAsString() : "additive"),
                m.has("rotationScale") ? m.get("rotationScale").getAsDouble() : 1, m.has("jitter") ? m.get("jitter").getAsDouble() : 0,
                m.has("easing") ? m.get("easing").getAsString() : "linear");
    }

    /** "#RRGGBB" or "@name" from the palette; unknown references fall back to white. */
    public int color(String ref) {
        if (ref == null) return palette.getOrDefault("primary", 0xFFFFFF);
        if (ref.startsWith("@")) return palette.getOrDefault(ref.substring(1), 0xFFFFFF);
        return hex(ref);
    }

    /** "@shards" -> the style's texture for that role; a plain name stays as it is. */
    public String texture(String ref) {
        if (ref != null && ref.startsWith("@")) return textures.getOrDefault(ref.substring(1), "spark_soft");
        return ref;
    }

    static int hex(String s) {
        return Integer.parseInt(s.startsWith("#") ? s.substring(1) : s, 16) & 0xFFFFFF;
    }
}
