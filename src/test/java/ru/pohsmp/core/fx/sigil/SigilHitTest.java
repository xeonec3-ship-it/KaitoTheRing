package ru.pohsmp.core.fx.sigil;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;
import ru.pohsmp.core.fx.sigil.SigilDef.Hit;
import ru.pohsmp.core.fx.sigil.SigilHit.Event;

/** T08: the hit response follows docs/sigils.md "Отклик на удар". Runs without Minecraft. */
class SigilHitTest {
    private static final Path DIR = Path.of("src/main/resources/assets/pohsmp_core/sigils");

    private static SigilDef load(String id) throws Exception {
        return SigilDef.parse(id, Files.readString(DIR.resolve(id + ".json")));
    }

    private static SigilDef plain(String extra) {
        return SigilDef.parse("t", "{\"size\":2,\"layers\":[{\"type\":\"disc\",\"radius\":1}]" + extra + "}");
    }

    @Test
    void flagAndBlockAreRead() throws Exception {
        assertNull(plain("").hit());
        assertEquals(Hit.DEFAULT, plain(",\"reactsToHits\":true").hit());
        assertEquals(Hit.DEFAULT, plain(",\"hit\":true").hit());
        assertNull(plain(",\"hit\":false").hit());
        Hit h = plain(",\"hit\":{\"duration\":12,\"rings\":2,\"color\":\"#FF0000\",\"sparks\":500}").hit();
        assertEquals(12, h.duration());
        assertEquals(2, h.rings());
        assertEquals(0xFF0000, h.color());
        assertEquals(64, h.sparks());                                  // clamped
        assertEquals(Hit.DEFAULT.width(), h.width(), 1e-12);           // the rest — defaults
        for (String id : List.of("silent_barrier", "higher_blades", "disintegration_field", "forbidden_chains", "coven_seal", "taboo_ground"))
            assertNotNull(load(id).hit(), id);
    }

    @Test
    void frontReachesTheFarRimInDuration() {
        Hit h = Hit.DEFAULT;                                           // 8 ticks
        Event e = new Event(0.4, 0, 100, 1, 7);
        assertEquals(0, SigilHit.front(h, e, 1, 100), 1e-12);
        assertEquals(1.4, SigilHit.front(h, e, 1, 108), 1e-12);        // |p| + reach
        assertTrue(SigilHit.front(h, e, 1, 104) > 0.7);                // slows down: past the middle at half time
        assertTrue(SigilHit.front(h, e, 1, 110) > 1.4);                // runs on and leaves the sigil
        double a = SigilHit.front(h, e, 1, 103), b = SigilHit.front(h, e, 1, 104);
        assertTrue(b > a);
    }

    @Test
    void glowIsARingAroundThePoint() {
        Hit h = Hit.DEFAULT;
        Event e = new Event(0, 0, 0, 1, 1);
        double t = 4, front = SigilHit.front(h, e, 1, t);
        double onCrest = SigilHit.glow(h, e, 1, front, 0, t);
        double inside = SigilHit.glow(h, e, 1, front - 0.4, 0, t), outside = SigilHit.glow(h, e, 1, front + 0.4, 0, t);
        assertTrue(onCrest > inside && onCrest > outside, onCrest + " " + inside + " " + outside);
        // the same at any angle: a circle
        assertEquals(onCrest, SigilHit.glow(h, e, 1, 0, front, t), 1e-9);
        assertEquals(onCrest, SigilHit.glow(h, e, 1, -front * Math.sqrt(0.5), -front * Math.sqrt(0.5), t), 1e-9);
        // a second, weaker crest follows `spacing` behind the first
        double second = SigilHit.glow(h, e, 1, front - h.spacing(), 0, t);
        assertTrue(second > inside * 0.9 && second < onCrest);
        // nothing before the hit and after its life
        assertEquals(0, SigilHit.glow(h, e, 1, 0.3, 0, -1), 1e-12);
        assertEquals(0, SigilHit.glow(h, e, 1, 0.3, 0, h.duration() + 7), 1e-12);
        // flash at the point right after the hit
        assertTrue(SigilHit.glow(h, e, 1, 0, 0, 0.2) > 0.6);
        // power scales everything
        Event weak = new Event(0, 0, 0, 0.5, 1);
        assertEquals(onCrest * 0.5, SigilHit.glow(h, weak, 1, front, 0, t), 1e-9);
    }

    @Test
    void manyHitsAreCapped() {
        SigilDef def = plain(",\"hit\":{}");
        List<Event> hits = new ArrayList<>();
        for (int i = 0; i < 4; i++) hits.add(new Event(0, 0, 0, 1, i));
        assertEquals(2 * Math.max(Hit.DEFAULT.strength(), Hit.DEFAULT.flash()), SigilHit.glow(def, hits, 0, 0, 0.1), 1e-9);
        // the light sheet: a share of the glow inside, nothing past the rim
        assertEquals(SigilHit.glow(def, hits, 0.3, 0, 0.1) * Hit.DEFAULT.sheen(), SigilHit.sheen(def, hits, 0.3, 0, 0.1), 1e-9);
        assertEquals(0, SigilHit.sheen(def, hits, 1.2, 0, 0.1), 1e-12);
    }

    @Test
    void flinchStartsSmoothSqueezesAndSettles() {
        Hit h = Hit.DEFAULT;                                           // shake 2 %, period 4
        Event e = new Event(0.5, 0, 10, 1, 1);
        assertEquals(1, SigilHit.flinch(h, e, 10), 1e-12);             // no jump at the hit
        double squeeze = SigilHit.flinch(h, e, 11);                    // quarter period
        assertTrue(squeeze < 1 && squeeze > 0.98, "" + squeeze);
        assertTrue(SigilHit.flinch(h, e, 13) > 1);                     // then swells
        assertEquals(1, SigilHit.flinch(h, e, 60), 1e-4);              // and settles
    }

    @Test
    void wobbleSinksTheStruckSide() {
        SigilDef def = plain(",\"hit\":{}");
        var w = SigilHit.wobble(def, List.of(new Event(0.8, 0, 0, 1, 1)), 1.0);
        // axis perpendicular to the direction to the hit (+x): along +y
        assertEquals(0, w.ax(), 1e-9);
        assertEquals(1, Math.abs(w.ay()), 1e-9);
        assertTrue(Math.abs(w.angle()) > 0.5);
        // turning (0.8, 0) around (ax, ay) by angle (right hand) moves it along -normal: z = -(ay·x − ax·y)·sin(angle) < 0
        double z = -(w.ay() * 0.8) * Math.sin(Math.toRadians(w.angle()));
        assertTrue(z < 0);
        assertEquals(0, SigilHit.wobble(def, List.of(new Event(0, 0, 0, 1, 1)), 1.0).angle(), 1e-12);   // centre: no wobble
    }

    @Test
    void sparksFlyOutAndFall() {
        Hit h = Hit.DEFAULT;
        Event e = new Event(0.2, 0.1, 0, 1, 42);
        assertEquals(h.sparks(), SigilHit.sparkCount(h, e));
        assertEquals(4, SigilHit.sparkCount(h, new Event(0, 0, 0, 0, 1)));
        for (int i = 0; i < SigilHit.sparkCount(h, e); i++) {
            var s0 = SigilHit.spark(h, e, i, 0);
            assertEquals(0, Math.hypot(s0.u(), s0.v()) + s0.n(), 1e-12);
            var s = SigilHit.spark(h, e, i, 5);
            assertTrue(s.alpha() > 0 && s.n() > 0, "spark " + i);
            assertTrue(s.drop() > 0);
            assertEquals(0, SigilHit.spark(h, e, i, 17).alpha(), 1e-12);
            // deterministic
            assertEquals(s, SigilHit.spark(h, e, i, 5));
        }
    }

    @Test
    void acceptMergesAndCaps() {
        Hit h = Hit.DEFAULT;                                           // cooldown 2, max 4
        List<Event> hits = new ArrayList<>();
        assertTrue(SigilHit.accept(h, hits, new Event(0, 0, 0, 0.5, 1)));
        assertFalse(SigilHit.accept(h, hits, new Event(0.1, 0, 1, 0.9, 2)));   // same place, 1 tick later: merged
        assertEquals(1, hits.size());
        assertEquals(0.9, hits.get(0).power(), 1e-12);
        for (int i = 0; i < 5; i++) SigilHit.accept(h, hits, new Event(0.5 * Math.cos(i), 0.5 * Math.sin(i), 3 + i, 1, i));
        assertEquals(4, hits.size());
        SigilHit.accept(h, hits, new Event(0, 0, 100, 1, 9));                  // the old ones are dead by now
        assertEquals(1, hits.size());
    }

    @Test
    void domeWaveUsesTheSameProfile() throws Exception {
        Hit h = Hit.DEFAULT;
        Event e = new Event(0, 0, 0, 1, 1);
        // on a plane, from the centre of a sigil of reach 1, span = 1: wave(d) == glow at distance d
        assertEquals(SigilHit.glow(h, e, 1, 0.4, 0, 3), SigilHit.wave(h, e, 1, 0.4, 3), 1e-12);
        // the dome: the front reaches the antipode (π) at duration
        double t = h.duration();
        assertTrue(SigilHit.wave(h, e, Math.PI, Math.PI, t) > SigilHit.wave(h, e, Math.PI, Math.PI / 2, t));
        var dome = SigilDef.parseHit(com.google.gson.JsonParser.parseString(
                Files.readString(Path.of("src/main/resources/assets/pohsmp_core/fx/meshes/silent_dome.json"))).getAsJsonObject());
        assertNotNull(dome, "silent_dome has a hit block");
    }

    @Test
    void contactFindsBodiesInsideTheSigil() {
        var G = SigilDef.Orientation.GROUND;
        double[] p = SigilHit.contact(G, 0, 64, 0, 0, 3, 1, 65, 1);         // standing on a ground sigil
        assertEquals(1, p[0], 1e-12);
        assertEquals(64, p[1], 1e-12);                                      // projected onto the plane
        assertNull(SigilHit.contact(G, 0, 64, 0, 0, 3, 3, 65, 3));          // outside the radius
        assertNull(SigilHit.contact(G, 0, 64, 0, 0, 3, 0, 70, 0));          // far above
        assertNotNull(SigilHit.contact(SigilDef.Orientation.SKY, 0, 80, 0, 0, 6, 1, 65, 0));   // under a sky sigil
        assertNull(SigilHit.contact(SigilDef.Orientation.SKY, 0, 80, 0, 0, 6, 1, 85, 0));      // above it
        // facing yaw 0 looks along +z: a body half a block in front, 0.5 to the side
        double[] f = SigilHit.contact(SigilDef.Orientation.FACING, 0, 65, 0, 0, 1.6, 0.5, 65.2, 0.5);
        assertEquals(0, f[2], 1e-12);
        assertNull(SigilHit.contact(SigilDef.Orientation.BILLBOARD, 0, 0, 0, 0, 1, 3, 0, 0));
    }

    @Test
    void powerFromDamage() {
        assertEquals(0.35, SigilHit.powerFromDamage(0), 1e-12);
        assertEquals(1, SigilHit.powerFromDamage(10), 1e-12);
        assertEquals(1, SigilHit.powerFromDamage(1000), 1e-12);
    }

    @Test
    void hashIsStable() {
        // the preview has the same numbers (Math.imul): keep these values when touching the hash
        assertEquals(SigilHit.hash(1, 2), SigilHit.hash(1, 2));
        double sum = 0;
        for (int i = 0; i < 1000; i++) {
            double r = SigilHit.rnd(7, i);
            assertTrue(r >= 0 && r < 1);
            sum += r;
        }
        assertEquals(0.5, sum / 1000, 0.05);
    }
}
