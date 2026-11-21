package ru.pohsmp.core.fx;

import static org.junit.jupiter.api.Assertions.*;

import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Stream;
import org.junit.jupiter.api.Test;

/**
 * T34: a parameter of the wrong JSON type threw while drawing and the client dropped the whole effect without a word (Ereb's intro,
 * the Hand's false death — «он просто исчезает» — and ~70 more: "tumble": true, curtain "height": [8, 14]).
 */
class FxParamTypesTest {
    private static final Path FX = Path.of("src/main/resources/assets/pohsmp_core/fx");
    private static final Path DRAW = Path.of("src/main/java/ru/pohsmp/core/client/fx");

    private static double num(String json, double def) {
        return FxDef.Element.asNum(JsonParser.parseString(json), def);
    }

    @Test
    void numIsTolerant() {
        assertEquals(2.5, num("2.5", 0));
        assertEquals(1, num("true", 0));
        assertEquals(0, num("false", 7));
        assertEquals(11, num("[8, 14]", 0));
        assertEquals(3, num("\"3\"", 0));
        assertEquals(7, num("\"fast\"", 7));
        assertEquals(7, num("{\"amp\": 1}", 7));
        assertEquals(7, num("[]", 7));
    }

    private static Set<String> keys(String src, String regex) {
        Set<String> out = new HashSet<>();
        Matcher m = Pattern.compile(regex).matcher(src);
        while (m.find()) out.add(m.group(1));
        return out;
    }

    /** Keys the renderers read ONLY as an array / ONLY as an object must be that in every effect (those reads are not tolerant). */
    @Test
    void arrayAndObjectParamsHaveTheirType() throws IOException {
        StringBuilder src = new StringBuilder();
        try (Stream<Path> s = Files.list(DRAW)) {
            for (Path p : (Iterable<Path>) s.filter(p -> p.toString().endsWith(".java") && !p.endsWith("MeshDraw.java"))::iterator) src.append(Files.readString(p));
        }
        String all = src.toString();
        Set<String> arrays = keys(all, "getAsJsonArray\\(\"(\\w+)\"\\)"), objects = keys(all, "getAsJsonObject\\(\"(\\w+)\"\\)");
        Set<String> loose = new HashSet<>(keys(all, "\\bnum\\(\"(\\w+)\""));
        loose.addAll(keys(all, "range\\(\\w+, \"(\\w+)\""));
        loose.addAll(keys(all, "wave\\(\\w+, \"(\\w+)\""));
        loose.addAll(keys(all, "isJsonArray\\(\\)[^;]*\"(\\w+)\""));
        // the element's own fields (FxDef: anchors, timing); MeshDraw reads mesh definitions, not effect elements
        loose.addAll(Set.of("at", "to", "from", "type", "delay", "duration", "follow", "color", "caster"));
        arrays.removeAll(loose);
        objects.removeAll(loose);
        objects.removeAll(arrays);
        List<String> bad = new ArrayList<>();
        int effects = 0;
        try (Stream<Path> s = Files.list(FX)) {
            for (Path f : (Iterable<Path>) s.filter(p -> p.toString().endsWith(".json"))::iterator) {
                JsonObject o = JsonParser.parseString(Files.readString(f)).getAsJsonObject();
                if (!o.has("elements")) continue;
                effects++;
                int i = 0;
                for (JsonElement e : o.getAsJsonArray("elements")) {
                    for (Map.Entry<String, JsonElement> en : e.getAsJsonObject().entrySet()) {
                        if (arrays.contains(en.getKey()) && !en.getValue().isJsonArray()) bad.add(f.getFileName() + " #" + i + " " + en.getKey() + " (array)");
                        if (objects.contains(en.getKey()) && !en.getValue().isJsonObject()) bad.add(f.getFileName() + " #" + i + " " + en.getKey() + " (object)");
                    }
                    i++;
                }
            }
        }
        assertTrue(effects > 100);
        assertTrue(bad.isEmpty(), "wrong type: " + bad);
    }
}
