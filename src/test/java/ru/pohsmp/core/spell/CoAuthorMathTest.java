package ru.pohsmp.core.spell;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;

/** Owner 21.11: joint cast co-authors (point 4) and the hostility memory (point 5). */
class CoAuthorMathTest {
    private static final UUID A = new UUID(0, 1), B = new UUID(0, 2), C = new UUID(0, 3);
    private static final String SPELL = "pohsmp_core:explosion";

    @Test
    void coAuthorsAreShieldedFromTheirSpell() {
        List<CoAuthorMath.Link> links = new ArrayList<>();
        CoAuthorMath.Link l = new CoAuthorMath.Link(A, B, SPELL);
        links.add(l);
        assertTrue(CoAuthorMath.shields(links, A, B, 10, SPELL, true, null), "the joint spell of A on B");
        assertTrue(CoAuthorMath.shields(links, B, A, 10, SPELL, true, null), "either way");
        assertTrue(CoAuthorMath.shields(links, A, B, 10, null, true, null), "our own spell damage type");
        assertFalse(CoAuthorMath.shields(links, A, B, 10, "irons_spellbooks:fireball", true, null), "another Iron's spell is not shared");
        assertFalse(CoAuthorMath.shields(links, A, B, 10, null, false, null), "a sword hit is not the spell");
        assertFalse(CoAuthorMath.shields(links, A, C, 10, SPELL, true, null), "a third player is not an owner");
        assertFalse(CoAuthorMath.shields(links, A, A, 10, SPELL, true, null));
        assertTrue(CoAuthorMath.linked(links, B, A, 10));
    }

    @Test
    void linkLivesWhileCastingAndAfterForItsFields() {
        List<CoAuthorMath.Link> links = new ArrayList<>();
        CoAuthorMath.Link l = new CoAuthorMath.Link(A, B, SPELL);
        links.add(l);
        assertTrue(CoAuthorMath.linked(links, A, B, 1_000_000), "casting: no end yet");
        l.fired(100);
        assertTrue(CoAuthorMath.linked(links, A, B, 100 + CoAuthorMath.LINGER - 1), "the Ark lasts 60 s");
        assertFalse(CoAuthorMath.linked(links, A, B, 100 + CoAuthorMath.LINGER));
        CoAuthorMath.prune(links, 100 + CoAuthorMath.LINGER);
        assertTrue(links.isEmpty());
    }

    @Test
    void entitiesOfTheSpellShieldForever() {
        List<CoAuthorMath.Link> none = new ArrayList<>();
        assertTrue(CoAuthorMath.shields(none, A, B, 999_999, null, false, List.of(A, B)), "a zone of the joint spell, link long gone");
        assertFalse(CoAuthorMath.shields(none, A, C, 0, null, false, List.of(A, B)), "the zone still hits others");
    }

    @Test
    void hostilityWindowBothWays() {
        Map<String, Long> m = CoAuthorMath.memory();
        long mem = 20 * 300;
        assertFalse(CoAuthorMath.hostile(m, A, B, 0, mem));
        CoAuthorMath.hurt(m, B, A, 100);   // B hit A
        assertTrue(CoAuthorMath.hostile(m, A, B, 100, mem), "A-B after B hit A");
        assertTrue(CoAuthorMath.hostile(m, B, A, 100 + mem - 1, mem));
        assertFalse(CoAuthorMath.hostile(m, A, B, 100 + mem, mem), "5 minutes later");
        assertTrue(CoAuthorMath.hostile(m, A, B, 100 + mem * 50, 0), "0 = forever");
        assertFalse(CoAuthorMath.hostile(m, A, C, 100, mem), "another pair");
        CoAuthorMath.hurt(m, A, A, 200);
        assertEquals(1, m.size(), "hurting oneself is not hostility");
        CoAuthorMath.forget(m, B);
        assertFalse(CoAuthorMath.hostile(m, A, B, 101, 0), "forgotten on logout");
    }

    @Test
    void attributionThroughProjectilesPetsAndZones() {
        Map<String, String> owner = new HashMap<>();
        owner.put("arrow", "alice");
        owner.put("wolf", "bob");
        owner.put("zone", "summon");
        owner.put("summon", "carol");
        owner.put("loop1", "loop2");
        owner.put("loop2", "loop1");
        java.util.function.Predicate<String> player = s -> s.equals("alice") || s.equals("bob") || s.equals("carol");
        assertEquals("alice", CoAuthorMath.attribute("alice", owner::get, player), "melee");
        assertEquals("alice", CoAuthorMath.attribute("arrow", owner::get, player), "projectile");
        assertEquals("bob", CoAuthorMath.attribute("wolf", owner::get, player), "pet");
        assertEquals("carol", CoAuthorMath.attribute("zone", owner::get, player), "zone of a summon");
        assertNull(CoAuthorMath.attribute("zombie", owner::get, player), "a mob of nobody");
        assertNull(CoAuthorMath.attribute("loop1", owner::get, player), "owner loop ends");
    }

    @Test
    void wiredIn() throws IOException {
        String joint = Files.readString(Path.of("src/main/java/ru/pohsmp/core/spell/JointCast.java"));
        assertTrue(joint.contains("CoAuthors.link(") && joint.contains("CoAuthors.fired(") && joint.contains("CoAuthors.unlink(")
                && joint.contains("CoAuthors.hostile("));
        assertTrue(Files.readString(Path.of("src/main/java/ru/pohsmp/core/spell/HigherSpell.java")).contains("CoAuthors.linked(caster, e)"));
        for (String f : new String[] {"ExplosionSpell", "FrozenHourSpell", "DisintegrationSpell"})
            assertTrue(Files.readString(Path.of("src/main/java/ru/pohsmp/core/spell/" + f + ".java")).contains("CoAuthors.linked("), f);
        assertTrue(Files.readString(Path.of("src/main/resources/pohsmp_core.mixins.json")).contains("\"IronsFriendlyFireMixin\""));
        assertTrue(Files.readString(Path.of("src/main/java/ru/pohsmp/core/ServerConfig.java")).contains("\"hostility_memory_seconds\", 300"));
        for (String lang : new String[] {"ru_ru", "en_us"})
            assertTrue(Files.readString(Path.of("src/main/resources/assets/pohsmp_core/lang/" + lang + ".json")).contains("\"ui.pohsmp_core.joint_cast.hostile\""), lang);
    }
}
