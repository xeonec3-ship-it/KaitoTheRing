package ru.pohsmp.core.fx;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Stream;
import net.minecraftforge.fml.ModList;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.fx.sigil.SigilDef;
import ru.pohsmp.core.fx.sigil.SigilText;

/**
 * Definitions read straight from the mod jar (assets/pohsmp_core/...), the same on the server (timings) and the client (drawing):
 * sigils/&lt;id&gt;.json, fx/&lt;id&gt;.json, fx/styles/&lt;id&gt;.json, fx/meshes/&lt;id&gt;.json, textures/sigil/glyphs_&lt;font&gt;.json. Cached; {@link #reload()} drops the cache.
 * A broken or missing file is logged once and gives null, never an exception.
 */
public final class FxLib {
    private FxLib() {}

    private static final Map<String, Object> CACHE = new ConcurrentHashMap<>();
    private static final Object MISSING = new Object();

    public static void reload() {
        CACHE.clear();
    }

    public static SigilDef sigil(String id) {
        return (SigilDef) get("sigil:" + id, () -> SigilDef.parse(id, read("sigils/" + id + ".json")));
    }

    /** Glyph atlas map of an inscription font (runic, latin, cyrillic — tools/gen_sigil_glyphs.py), null if there is none. */
    public static SigilText.Font font(String name) {
        return (SigilText.Font) get("font:" + name, () -> SigilText.Font.parse(read("textures/sigil/glyphs_" + name + ".json")));
    }

    public static FxDef fx(String id) {
        return (FxDef) get("fx:" + id, () -> FxDef.parse(id, read("fx/" + id + ".json")));
    }

    public static FxStyle style(String id) {
        FxStyle s = (FxStyle) get("style:" + id, () -> FxStyle.parse(id, read("fx/styles/" + id + ".json")));
        if (s == null && !"divine".equals(id)) return style("divine");
        return s;
    }

    public static JsonObject mesh(String id) {
        return (JsonObject) get("mesh:" + id, () -> JsonParser.parseString(read("fx/meshes/" + id + ".json")).getAsJsonObject());
    }

    /** Ids (file names without .json) in a folder of assets/pohsmp_core, for command suggestions. */
    public static List<String> list(String folder) {
        List<String> out = new ArrayList<>();
        Path dir = path(folder);
        if (dir == null || !Files.isDirectory(dir)) return out;
        try (Stream<Path> s = Files.list(dir)) {
            s.forEach(p -> {
                String n = p.getFileName().toString();
                if (n.endsWith(".json")) out.add(n.substring(0, n.length() - 5));
            });
        } catch (IOException ignored) {
        }
        out.sort(String::compareTo);
        return out;
    }

    private interface Loader {
        Object load() throws Exception;
    }

    private static Object get(String key, Loader l) {
        Object o = CACHE.get(key);
        if (o == null) {
            try {
                o = l.load();
            } catch (Exception e) {
                PohCore.LOG.warn("[pohsmp_core] fx definition {} not loaded: {}", key, e.toString());
                o = MISSING;
            }
            CACHE.put(key, o);
        }
        return o == MISSING ? null : o;
    }

    private static Path path(String rel) {
        var mf = ModList.get().getModFileById(PohCore.MODID);
        if (mf == null) return null;
        return mf.getFile().findResource(("assets/" + PohCore.MODID + "/" + rel).split("/"));
    }

    private static String read(String rel) throws IOException {
        Path p = path(rel);
        if (p == null || !Files.exists(p)) throw new IOException("no file assets/" + PohCore.MODID + "/" + rel);
        return Files.readString(p, StandardCharsets.UTF_8);
    }
}
