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

    /** T34: the six boss reward spells - Higher (into books: yes), never copied / merged; nothing else is affected. */
    @Test
    void rewardSpellsInscribableButNotCopied() throws IOException {
        assertEquals(6, MagicRules.REWARD_SPELLS.size());
        for (String id : MagicRules.REWARD_SPELLS) {
            assertTrue(MagicRules.copyBanned(id), id);
            assertTrue(id.startsWith("pohsmp_core:"), id);
        }
        assertFalse(MagicRules.copyBanned("pohsmp_core:nightmare_cradle"), "other Higher spells merge as before");
        assertFalse(MagicRules.copyBanned("irons_spellbooks:fireball"));
        assertFalse(MagicRules.copyBanned(null));
        assertFalse(MagicRules.bindBanned("higher"), "reward spells are Higher: written into books");
        // owner 21.11 (later): Жатва and Длань live only in their items (T35) - no scrolls, no books; the other four as before
        assertEquals(Set.of("pohsmp_core:ashen_harvest", "pohsmp_core:hand_of_lies"), MagicRules.ITEM_ONLY_SPELLS);
        assertTrue(MagicRules.REWARD_SPELLS.containsAll(MagicRules.ITEM_ONLY_SPELLS));
        for (String id : List.of("pohsmp_core:jealous_embrace", "pohsmp_core:anvil_strike", "pohsmp_core:warlord_banner", "pohsmp_core:mirror_step"))
            assertFalse(MagicRules.itemOnly(id), id);
        assertFalse(MagicRules.itemOnly(null));
        assertTrue(MagicRules.craftBanned("higher", false), "reward spells are never crafted");
        // built-in Higher tier = listed in Reg.HIGHER_SPELLS; registered; fixed cast through RewardSpell
        String reg = Files.readString(SRC.resolve("ru/pohsmp/core/Reg.java"), StandardCharsets.UTF_8);
        int hs = reg.indexOf("List<String> HIGHER_SPELLS");
        String higher = reg.substring(hs, reg.indexOf(");", hs));
        String rewards = Files.readString(SRC.resolve("ru/pohsmp/core/spell/reward/Rewards.java"), StandardCharsets.UTF_8);
        for (String c : List.of("ASHEN_HARVEST", "JEALOUS_EMBRACE", "ANVIL_STRIKE", "WARLORD_BANNER", "MIRROR_STEP", "HAND_OF_LIES")) {
            assertTrue(higher.contains("RewardMath." + c), c + " in Reg.HIGHER_SPELLS");
            assertTrue(rewards.contains("RewardMath." + c + ","), c + " registered");
        }
        assertTrue(reg.contains("Rewards.registerSpells(SPELLS)"));
        String base = Files.readString(SRC.resolve("ru/pohsmp/core/spell/reward/RewardSpell.java"), StandardCharsets.UTF_8);
        assertTrue(base.contains("extends HigherSpell implements FixedCastSpell"), "Higher school + fixed cast");
        assertTrue(base.contains("RewardMath.MAX_LEVEL"), "levels 1..3");
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
