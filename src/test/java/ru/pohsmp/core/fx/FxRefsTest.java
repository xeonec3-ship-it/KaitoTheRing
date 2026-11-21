package ru.pohsmp.core.fx;

import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assertions.fail;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Stream;
import org.junit.jupiter.api.Test;

/**
 * FX audit 21.11: every resource an effect needs is in the jar, so nothing silently draws white or not at all in game.
 * FxLib gives null for a missing fx/sigil/mesh (the effect is simply not there) and FxDraw.tex gives plain white for a missing
 * texture, so a broken name never crashes — this test is the only thing that catches it.
 * <ul>
 * <li>JSON: textures of fx / meshes / sigils (with "@role" resolved through the style), styles' textures, sigil fonts, "impact"
 * sigils of beam rain, sigil children;</li>
 * <li>code: every fx / sigil / mesh name passed to {@code Fx.fx / Fx.sigil / Fx.mesh} as a literal, a ternary of literals, a
 * {@code static final String} constant or constant + literal suffix;</li>
 * <li>sounds: every sound literal in code, every GeckoLib {@code sound_effects} keyframe and every sounds.json file and subtitle.</li>
 * </ul>
 * Fails on any broken reference. Runs without Minecraft (plain files).
 */
class FxRefsTest {
    private static final Path SRC = Path.of("src/main/java");
    private static final Path ROOT = Path.of("src/main/resources/assets/pohsmp_core");
    private static final Path FX = ROOT.resolve("fx");

    /**
     * Played only through an existence check (IllusionBase.fx(sl, spec, id) skips a missing one) and knowingly not drawn yet.
     * Adding a name here is a decision, not a fix: say why.
     */
    private static final Set<String> OPTIONAL = Set.of(
            "fx:nightmare_no_awakening_morph");   // «Кошмар без пробуждения», morph flash: never drawn, guarded; particles + sound stand in

    private static String read(Path p) {
        try {
            return Files.readString(p, StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    private static List<Path> files(Path dir, String ext, boolean deep) {
        try (Stream<Path> s = deep ? Files.walk(dir) : Files.list(dir)) {
            return s.filter(p -> p.toString().endsWith(ext)).sorted().toList();
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    private static String id(Path p) {
        String n = p.getFileName().toString();
        return n.substring(0, n.lastIndexOf('.'));
    }

    private static boolean texture(String name) {
        return Files.exists(ROOT.resolve("textures/sigil/" + name + ".png")) || Files.exists(ROOT.resolve("textures/fx/" + name + ".png"));
    }

    private static final Map<String, Map<String, String>> STYLE_TEX = new HashMap<>();

    private static Map<String, String> styleTextures(String style) {
        return STYLE_TEX.computeIfAbsent(style, s -> {
            Map<String, String> m = new HashMap<>();
            Path p = FX.resolve("styles/" + s + ".json");
            if (!Files.exists(p)) return m;
            JsonObject o = JsonParser.parseString(read(p)).getAsJsonObject();
            if (o.has("textures")) o.getAsJsonObject("textures").entrySet().forEach(e -> m.put(e.getKey(), e.getValue().getAsString()));
            return m;
        });
    }

    /** Walks a definition: "texture", "font", "impact" anywhere; a mesh part may switch the style ("style" in a mesh). */
    private static void walk(JsonElement e, String style, boolean meshStyles, String where, List<String> errors) {
        if (e.isJsonArray()) {
            for (JsonElement x : e.getAsJsonArray()) walk(x, style, meshStyles, where, errors);
            return;
        }
        if (!e.isJsonObject()) return;
        JsonObject o = e.getAsJsonObject();
        String st = meshStyles && o.has("style") && o.get("style").isJsonPrimitive() ? o.get("style").getAsString() : style;
        for (var en : o.entrySet()) {
            JsonElement v = en.getValue();
            if (v.isJsonPrimitive() && v.getAsJsonPrimitive().isString()) {
                String s = v.getAsString();
                switch (en.getKey()) {
                    case "texture" -> {
                        String t = s.startsWith("@") ? styleTextures(st).getOrDefault(s.substring(1), "spark_soft") : s;
                        if (!texture(t)) errors.add(where + ": texture " + s + (s.equals(t) ? "" : " (" + st + " -> " + t + ")"));
                    }
                    case "font" -> {
                        if (!Files.exists(ROOT.resolve("textures/sigil/glyphs_" + s + ".json"))) errors.add(where + ": font " + s);
                    }
                    case "impact" -> {
                        if (!Files.exists(ROOT.resolve("sigils/" + s + ".json"))) errors.add(where + ": impact sigil " + s);
                    }
                    default -> {}
                }
            }
            walk(v, st, meshStyles, where, errors);
        }
    }

    @Test
    void everyTextureFontAndSubSigilOfTheDefinitionsExists() {
        List<String> errors = new ArrayList<>();
        for (Path p : files(FX.resolve("styles"), ".json", false))
            styleTextures(id(p)).forEach((role, t) -> {
                if (!texture(t)) errors.add("style " + id(p) + ": texture " + role + "=" + t);
            });
        for (Path p : files(FX, ".json", false)) {
            JsonObject o = JsonParser.parseString(read(p)).getAsJsonObject();
            walk(o, o.has("style") ? o.get("style").getAsString() : "divine", false, "fx " + id(p), errors);
        }
        for (Path p : files(FX.resolve("meshes"), ".json", false)) {
            JsonObject o = JsonParser.parseString(read(p)).getAsJsonObject();
            walk(o, o.has("style") ? o.get("style").getAsString() : "divine", true, "mesh " + id(p), errors);
        }
        for (Path p : files(ROOT.resolve("sigils"), ".json", false)) {
            JsonObject o = JsonParser.parseString(read(p)).getAsJsonObject();
            walk(o, "divine", false, "sigil " + id(p), errors);
            if (o.has("children")) for (JsonElement c : o.getAsJsonArray("children")) {
                String cid = c.getAsJsonObject().has("id") ? c.getAsJsonObject().get("id").getAsString() : "";
                if (!Files.exists(ROOT.resolve("sigils/" + cid + ".json"))) errors.add("sigil " + id(p) + ": child sigil " + cid);
            }
        }
        if (!errors.isEmpty()) fail(errors.size() + " broken references:\n" + String.join("\n", errors));
    }

    // ---------------------------------------------------------------- code

    private static final Pattern CALL = Pattern.compile("Fx\\.(fx|sigil|mesh)\\(");
    private static final Pattern LITERAL = Pattern.compile("\"([^\"]*)\"");
    private static final Pattern CONST_DECL = Pattern.compile("static final String (\\w+)\\s*=\\s*\"([^\"]*)\"");
    private static final Pattern CONST_USE = Pattern.compile("^([A-Z][A-Z0-9_]*)(?:\\s*\\+\\s*\"([^\"]*)\")?$");
    private static final Pattern TERNARY = Pattern.compile("^[^?]+\\?\\s*\"([^\"]*)\"\\s*:\\s*\"([^\"]*)\"$");

    private static String argument(String t, int open) {
        int d = 0;
        for (int i = open; i < t.length(); i++) {
            char c = t.charAt(i);
            if (c == '(') d++;
            else if (c == ')' && --d == 0) return t.substring(open + 1, i).trim();
        }
        return "";
    }

    record Ref(String kind, String name, String where) {}

    /** Names the code passes to Fx.fx / Fx.sigil / Fx.mesh, as far as they can be read without running it. */
    static List<Ref> codeRefs(List<String> unresolved) {
        List<Path> java = files(SRC, ".java", true);
        Map<String, String> consts = new HashMap<>();
        Map<Path, String> text = new HashMap<>();
        for (Path p : java) {
            String t = read(p);
            text.put(p, t);
            Matcher m = CONST_DECL.matcher(t);
            while (m.find()) consts.putIfAbsent(p.getFileName() + "#" + m.group(1), m.group(2));
        }
        List<Ref> out = new ArrayList<>();
        for (Path p : java) {
            String t = text.get(p);
            Matcher m = CALL.matcher(t);
            while (m.find()) {
                String arg = argument(t, m.end() - 1);
                String where = p.getFileName() + ":" + (t.substring(0, m.start()).split("\n", -1).length);
                Matcher lit = LITERAL.matcher(arg), tern = TERNARY.matcher(arg), cu = CONST_USE.matcher(arg);
                if (arg.matches("\"[^\"]*\"")) out.add(new Ref(m.group(1), arg.substring(1, arg.length() - 1), where));
                else if (tern.matches()) {
                    out.add(new Ref(m.group(1), tern.group(1), where));
                    out.add(new Ref(m.group(1), tern.group(2), where));
                } else if (cu.matches() && consts.containsKey(p.getFileName() + "#" + cu.group(1))) {
                    String base = consts.get(p.getFileName() + "#" + cu.group(1));
                    out.add(new Ref(m.group(1), base + (cu.group(2) == null ? "" : cu.group(2)), where));
                } else if (lit.find()) unresolved.add(where + " " + arg);   // literal prefix + variable: checked by hand / by its own test
            }
        }
        return out;
    }

    @Test
    void everyFxNameInTheCodeExists() {
        List<String> unresolved = new ArrayList<>();
        List<Ref> refs = codeRefs(unresolved);
        assertTrue(refs.size() > 300, "the scan reads the code (found only " + refs.size() + ")");
        Set<String> errors = new TreeSet<>();
        for (Ref r : refs) {
            String dir = switch (r.kind()) {
                case "fx" -> "fx/";
                case "sigil" -> "sigils/";
                default -> "fx/meshes/";
            };
            if (!Files.exists(ROOT.resolve(dir + r.name() + ".json")) && !OPTIONAL.contains(r.kind() + ":" + r.name()))
                errors.add(r.where() + ": Fx." + r.kind() + "(\"" + r.name() + "\") - no assets/pohsmp_core/" + dir + r.name() + ".json");
        }
        if (!errors.isEmpty()) fail(String.join("\n", errors));
    }

    /** Irina's bonds are "irina_bond_" + (1..4): the one concatenation in the bosses, kept honest here. */
    @Test
    void irinaBondsExist() {
        for (int i = 1; i <= 4; i++) assertTrue(Files.exists(FX.resolve("irina_bond_" + i + ".json")), "irina_bond_" + i);
    }

    private static final Pattern REWARD_PLAY = Pattern.compile("play\\(\\s*\\w+\\s*,\\s*\"([a-z0-9_]+)\"\\s*,\\s*(?:\"([a-z0-9_]+)\"|null)");

    /**
     * T34 reward spells play their own fx or, until it is drawn, the boss fx it came from (RewardSpell.play(level, own, fallback, ..)):
     * the fallback must exist, and with no fallback the own one must.
     */
    @Test
    void rewardSpellsHaveTheirFxOrABossFallback() {
        Set<String> errors = new TreeSet<>();
        int n = 0;
        for (Path p : files(SRC.resolve("ru/pohsmp/core/spell/reward"), ".java", false)) {
            String t = read(p);
            Matcher m = REWARD_PLAY.matcher(t);
            while (m.find()) {
                n++;
                boolean own = Files.exists(FX.resolve(m.group(1) + ".json"));
                String fb = m.group(2);
                if (fb != null && !Files.exists(FX.resolve(fb + ".json"))) errors.add(p.getFileName() + ": fallback " + fb);
                if (fb == null && !own) errors.add(p.getFileName() + ": " + m.group(1) + " (no fallback)");
            }
        }
        assertTrue(n >= 15, "the scan reads the reward spells (found " + n + ")");
        if (!errors.isEmpty()) fail(String.join("\n", errors));
    }

    // ---------------------------------------------------------------- sounds

    private static JsonObject sounds() {
        return JsonParser.parseString(read(ROOT.resolve("sounds.json"))).getAsJsonObject();
    }

    private static final Pattern SOUND_CALL = Pattern.compile(
            "\\b(?:sound|playSound|sfx|soundAt|loop)\\(\\s*(?:[^,\"()]+(?:\\([^()]*\\))?,\\s*)?\"([a-z0-9_.:/]+)\"");

    @Test
    void everySoundNameInTheCodeAndAnimationsIsInSoundsJson() {
        JsonObject s = sounds();
        Set<String> errors = new TreeSet<>();
        for (Path p : files(SRC, ".java", true)) {
            String t = read(p);
            Matcher m = SOUND_CALL.matcher(t);
            while (m.find()) {
                String n = m.group(1);
                if (n.contains(":") && !n.startsWith("pohsmp_core:")) continue;
                n = n.replace("pohsmp_core:", "");
                if (!s.has(n)) errors.add(p.getFileName() + ":" + t.substring(0, m.start()).split("\n", -1).length + ": sound " + n);
            }
        }
        for (Path p : files(ROOT.resolve("animations"), ".json", true)) {
            JsonObject anims = JsonParser.parseString(read(p)).getAsJsonObject().getAsJsonObject("animations");
            if (anims == null) continue;
            for (var a : anims.entrySet()) {
                JsonObject se = a.getValue().getAsJsonObject().getAsJsonObject("sound_effects");
                if (se == null) continue;
                for (var k : se.entrySet()) {
                    List<JsonElement> evs = new ArrayList<>();
                    if (k.getValue().isJsonArray()) k.getValue().getAsJsonArray().forEach(evs::add);
                    else evs.add(k.getValue());
                    for (JsonElement ev : evs) {
                        String eff = ev.getAsJsonObject().has("effect") ? ev.getAsJsonObject().get("effect").getAsString() : "";
                        String n = eff.split("\\|")[0].trim();   // "pohsmp_core:name|volume|pitch" (BossSoundClient)
                        if (n.isEmpty() || n.contains(":") && !n.startsWith("pohsmp_core:")) continue;
                        n = n.replace("pohsmp_core:", "");
                        if (!s.has(n)) errors.add(p.getFileName() + " " + a.getKey() + " @" + k.getKey() + ": sound " + n);
                    }
                }
            }
        }
        if (!errors.isEmpty()) fail(String.join("\n", errors));
    }

    /**
     * sounds.json: every file is there and every subtitle is translated in both languages. Music parts (music/...) may be missing on
     * purpose — BossMusicClient checks each part and falls back (T33: Aris waits for the owner's track).
     */
    @Test
    void soundsJsonFilesAndSubtitlesExist() {
        JsonObject s = sounds();
        Set<String> errors = new TreeSet<>();
        Set<String> langs = new HashSet<>();
        Map<String, JsonObject> lang = new HashMap<>();
        for (String l : List.of("en_us", "ru_ru")) {
            lang.put(l, JsonParser.parseString(read(ROOT.resolve("lang/" + l + ".json"))).getAsJsonObject());
            langs.add(l);
        }
        for (var e : s.entrySet()) {
            JsonObject ev = e.getValue().getAsJsonObject();
            if (ev.has("subtitle")) for (String l : langs)
                if (!lang.get(l).has(ev.get("subtitle").getAsString())) errors.add(e.getKey() + ": subtitle not in " + l);
            JsonArray arr = ev.has("sounds") ? ev.getAsJsonArray("sounds") : new JsonArray();
            for (JsonElement x : arr) {
                String name;
                if (x.isJsonObject()) {
                    if (x.getAsJsonObject().has("type") && "event".equals(x.getAsJsonObject().get("type").getAsString())) continue;
                    name = x.getAsJsonObject().get("name").getAsString();
                } else name = x.getAsString();
                if (name.contains(":") && !name.startsWith("pohsmp_core:")) continue;
                name = name.replace("pohsmp_core:", "");
                if (name.startsWith("music/")) continue;
                if (!Files.exists(ROOT.resolve("sounds/" + name + ".ogg"))) errors.add(e.getKey() + ": no sounds/" + name + ".ogg");
            }
        }
        if (!errors.isEmpty()) fail(String.join("\n", errors));
    }
}
