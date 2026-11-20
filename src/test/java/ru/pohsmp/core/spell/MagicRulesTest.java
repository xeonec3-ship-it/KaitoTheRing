package ru.pohsmp.core.spell;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Set;
import java.util.TreeSet;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Stream;
import org.junit.jupiter.api.Test;

/** Owner 20.11: what is crafted / written into books / imbued, and which spells have a fixed cast time. */
class MagicRulesTest {
    private static final Path SRC = Path.of("src/main/java");

    @Test
    void craftBannedForHigherAndAboveAndSilent() {
        for (String t : List.of("higher", "mythic", "divine", "creation", "unknown")) assertTrue(MagicRules.craftBanned(t, false), t);
        assertTrue(MagicRules.craftBanned(null, true), "any Silent spell");
        assertFalse(MagicRules.craftBanned(null, false), "ordinary spells stay craftable");
    }

    @Test
    void bindBannedAboveHigherOnly() {
        for (String t : List.of("mythic", "divine", "creation", "unknown")) assertTrue(MagicRules.bindBanned(t), t);
        assertFalse(MagicRules.bindBanned("higher"), "Higher still goes into books and items");
        assertFalse(MagicRules.bindBanned(null), "ordinary spells");
    }

    /** The rule keys are exactly the keys of ru.pohsmp.core.Tier (read from its source: the enum needs Minecraft to load). */
    @Test
    void ruleKeysMatchTierEnum() throws IOException {
        String tier = Files.readString(SRC.resolve("ru/pohsmp/core/Tier.java"), StandardCharsets.UTF_8);
        Matcher m = Pattern.compile("^\\s*[A-Z]+\\(\"([a-z]+)\",", Pattern.MULTILINE).matcher(tier);
        Set<String> keys = new TreeSet<>();
        while (m.find()) keys.add(m.group(1));
        assertEquals(new TreeSet<>(MagicRules.NO_CRAFT_TIERS), keys, "every tier is craft-banned");
        Set<String> bind = new TreeSet<>(keys);
        bind.remove("higher");
        assertEquals(bind, new TreeSet<>(MagicRules.NO_BIND_TIERS));
    }

    /** Every spell that starts a camera cutscene is marked FixedCastSpell (in its own class or its abstract base in the same file). */
    @Test
    void everyCutsceneSpellHasFixedCast() throws IOException {
        List<String> missing;
        int found;
        try (Stream<Path> s = Files.walk(SRC)) {
            List<Path> users = s.filter(p -> p.toString().endsWith(".java")).filter(p -> read(p).contains("Cutscene.start(")).toList();
            found = users.size();
            missing = users.stream().filter(p -> !read(p).contains("FixedCastSpell")).map(Path::toString).toList();
        }
        assertTrue(found >= 13, "cutscene spells found: " + found);
        assertTrue(missing.isEmpty(), "add 'implements FixedCastSpell' to: " + missing);
    }

    private static String read(Path p) {
        try {
            return Files.readString(p, StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
    }
}
