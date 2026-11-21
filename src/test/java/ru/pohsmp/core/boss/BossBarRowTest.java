package ru.pohsmp.core.boss;

import static org.junit.jupiter.api.Assertions.*;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.regex.Pattern;
import java.util.stream.Stream;
import org.junit.jupiter.api.Test;

/** The boss bar row (T34 bug: no bar at all for Aris — her server had no boss event, so the client never drew one). */
class BossBarRowTest {
    /** spawn → intro (bar hidden) → fight (BAR_VISIBLE) → a second player joins late → both see it; finale → gone for all. */
    @Test
    void spawnIntroFightLateJoin() {
        BossBarRow<String> row = new BossBarRow<>();
        boolean visible = false, cam = true;
        assertTrue(row.seen("owner"));                                        // spawn: tracked at once
        assertFalse(BossBarRow.drawn(row.has("owner"), true, visible, cam));  // intro: row there, bar hidden
        cam = false;
        visible = true;                                                       // startFight: setBar(true)
        assertTrue(BossBarRow.drawn(row.has("owner"), true, visible, cam));
        assertTrue(row.seen("late"));                                         // a late viewer: startSeenByPlayer → row + BAR msg
        assertTrue(BossBarRow.drawn(row.has("late"), true, visible, cam));
        assertFalse(row.seen("late"));                                        // no double add
        assertTrue(row.unseen("late"));                                       // walked away
        assertFalse(BossBarRow.drawn(row.has("late"), true, visible, cam));
        assertTrue(row.seen("late"));                                         // came back
        assertEquals(List.of("owner", "late"), row.close());                  // surrender / death
        assertFalse(row.has("owner"));
        assertFalse(row.seen("third"));                                       // the finale: nobody joins again
        assertFalse(BossBarRow.drawn(false, true, true, false));
    }

    @Test
    void sceneHidesBar() {
        assertFalse(BossBarRow.drawn(true, true, true, true));
        assertFalse(BossBarRow.drawn(true, false, true, false));
    }

    private static final Pattern POH_BOSS = Pattern.compile("class\\s+\\w+Entity\\s+extends\\s+(\\w+).*implements[^{]*\\bPohBoss\\b",
            Pattern.DOTALL);

    /** Every boss either gets the row from BossCore, or brings its own boss event with its UUID (only FireBossEntity, the Cult Leader). */
    @Test
    void everyBossHasARow() throws IOException {
        Path root = Path.of("src/main/java/ru/pohsmp/core/boss");
        int bosses = 0;
        try (Stream<Path> files = Files.walk(root)) {
            for (Path f : (Iterable<Path>) files.filter(p -> p.toString().endsWith("Entity.java"))::iterator) {
                String src = Files.readString(f);
                var m = POH_BOSS.matcher(src);
                if (!m.find()) continue;
                bosses++;
                boolean optOut = src.contains("coreBossEvent()") && src.contains("return false;");
                if (optOut) assertEquals("FireBossEntity", m.group(1), f + ": opts out of the core row without a base boss event");
                assertFalse(src.contains("new ExtendedServerBossEvent") || src.contains("new ServerBossEvent"),
                        f + ": a second boss event next to BossCore's");
                assertTrue(src.contains("core.onSeen(p)") && src.contains("core.onUnseen(p)"), f + ": the row needs onSeen / onUnseen");
            }
        }
        assertEquals(6, bosses, "cult_leader, irina, aris, martin, ereb, ereb_hand");
    }
}
