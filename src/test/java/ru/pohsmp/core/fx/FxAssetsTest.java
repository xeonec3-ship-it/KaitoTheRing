package ru.pohsmp.core.fx;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assertions.fail;

import com.google.gson.JsonParser;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.stream.Stream;
import org.junit.jupiter.api.Test;
import ru.pohsmp.core.fx.sigil.SigilDef;

/**
 * Every effect, sigil and mesh in the mod parses the way FxLib loads it in game, and what an effect refers to
 * (sigils by "id", meshes by "model", its style) exists. Runs without Minecraft.
 */
class FxAssetsTest {
    private static final Path ROOT = Path.of("src/main/resources/assets/pohsmp_core");
    private static final Path FX = ROOT.resolve("fx");

    private static String read(Path p) throws IOException {
        return Files.readString(p, StandardCharsets.UTF_8);
    }

    private static List<Path> json(Path dir) throws IOException {
        try (Stream<Path> s = Files.list(dir)) {
            return s.filter(p -> p.toString().endsWith(".json")).sorted().toList();
        }
    }

    private static String id(Path p) {
        String n = p.getFileName().toString();
        return n.substring(0, n.length() - 5);
    }

    @Test
    void everyEffectSigilAndMeshLoads() throws IOException {
        List<String> errors = new ArrayList<>();
        for (Path p : json(ROOT.resolve("sigils"))) {
            try {
                SigilDef.parse(id(p), read(p));
            } catch (RuntimeException e) {
                errors.add("sigil " + id(p) + ": " + e);
            }
        }
        for (Path p : json(FX.resolve("meshes"))) {
            try {
                JsonParser.parseString(read(p)).getAsJsonObject();
            } catch (RuntimeException e) {
                errors.add("mesh " + id(p) + ": " + e);
            }
        }
        for (Path p : json(FX)) {
            FxDef fx;
            try {
                fx = FxDef.parse(id(p), read(p));
            } catch (RuntimeException e) {
                errors.add("fx " + id(p) + ": " + e);
                continue;
            }
            if (!Files.exists(FX.resolve("styles/" + fx.style() + ".json"))) errors.add("fx " + fx.id() + ": no style " + fx.style());
            for (FxDef.Element el : fx.elements()) {
                if (!FxDef.TYPES.contains(el.type())) errors.add("fx " + fx.id() + ": unknown element type " + el.type());
                if (el.type().equals("sigil") && !Files.exists(ROOT.resolve("sigils/" + el.str("id", "") + ".json")))
                    errors.add("fx " + fx.id() + ": no sigil " + el.str("id", ""));
                if (el.type().equals("mesh")) {
                    String m = el.str("model", el.str("id", ""));
                    if (!Files.exists(FX.resolve("meshes/" + m + ".json"))) errors.add("fx " + fx.id() + ": no mesh " + m);
                }
            }
        }
        if (!errors.isEmpty()) fail(String.join("\n", errors));
    }

    /** T02: the detailed Scarlet Cut keeps the contract of the code (ScarletCutSpell): the crack bursts on tick 20. */
    @Test
    void scarletCutKeepsItsContract() throws IOException {
        FxDef fx = FxDef.parse("scarlet_cut", read(FX.resolve("scarlet_cut.json")));
        assertEquals("higher", fx.style());
        assertTrue(fx.elements().stream().anyMatch(e -> e.type().equals("sigil") && e.str("id", "").equals("scarlet_cut_seal")));
        assertTrue(fx.elements().stream().anyMatch(e -> e.delay() == 20), "something starts with the burst on tick 20");
    }

    /** T05: the final Star Fall effect is there with its sigils and glass mesh; the temporary one is gone (FxLib loads it by id). */
    @Test
    void starFallIsFinal() throws IOException {
        FxDef fx = FxDef.parse("star_fall", read(FX.resolve("star_fall.json")));
        assertEquals("higher", fx.style());
        List<String> sigils = fx.elements().stream().filter(e -> e.type().equals("sigil")).map(e -> e.str("id", "")).toList();
        assertTrue(sigils.containsAll(List.of("star_fall_target", "star_fall_sky")), sigils.toString());
        assertTrue(fx.elements().stream().anyMatch(e -> e.type().equals("mesh") && e.str("model", "").equals("star_glass")));
    }
}
