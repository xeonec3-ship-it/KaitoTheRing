package ru.pohsmp.core.boss;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * What a cult boss is made of — shared by server and client, no Minecraft classes. One per boss, registered in {@link BossDefs}
 * (static, so both sides know it). Built with {@link #builder(String)}; see docs/inbox/2026-11-20_cloudcode_bosses_core_T26.md,
 * «Каркас готов».
 */
public final class BossDef {
    /** How the fight ends. */
    public enum Finale {
        /** The boss dies: death cutscene, then gone (T26, T27). */
        DEATH,
        /** At finaleAt the boss stops, plays its surrender scene and becomes a peaceful NPC of its own kind (T28, T29). */
        SURRENDER,
        /** At finaleAt the boss plays its finale and leaves (vanishes) (T30 Ereb). */
        LEAVE
    }

    /** Animated overlay of a bar phase. */
    public enum Overlay {
        NONE,
        /** <sprite>_pulse drawn over the bar with a pulsing alpha while the boss's «pulse» flag is on (a magic lock...). */
        PULSE,
        /** 8 frames of 192×14 (<sprite>_<name>), frame (tick/2)%8, drawn before the bar at y − 5 (flames, threads, heat). */
        FRAMES
    }

    /** One bar phase: sprite name under textures/gui/sprites/boss_bars/ and its overlay (name = file suffix). */
    public record BarPhase(String sprite, Overlay overlay, String overlaySprite) {}

    /** A special spell: once per fight, when health first drops to at (fraction). */
    public record Special(String id, double at) {}

    public final String id;
    /** Phase thresholds, descending (e.g. 0.66, 0.33 → three phases). */
    public final double[] phases;
    public final List<BarPhase> bar;
    /** RGB of the boss: chat lines, subtitles, the epithet under the bar (when the sprite has no colour of its own). */
    public final int color;
    public final Finale finale;
    /** For SURRENDER / LEAVE: the health fraction it happens at (health never goes lower). */
    public final double finaleAt;
    public final List<Special> specials;
    /** The boss finishes players off with an animation (T26, T27). */
    public final boolean finisher;
    /** Sound event id (pohsmp_core) looped during the fight, or null. */
    public final String music;
    /** Default radius of the fight: who watches the special scenes, who counts for scaling. */
    public final double fightRadius;
    /** Title texture base name (textures/gui/title/<title>_<lang>.png) of the intro; null = none. */
    public final String title;
    /** The peaceful NPC entity id (pohsmp_core:<npc>) for SURRENDER, else null. */
    public final String npc;

    private BossDef(Builder b) {
        id = b.id;
        phases = b.phases;
        bar = Collections.unmodifiableList(new ArrayList<>(b.bar));
        color = b.color;
        finale = b.finale;
        finaleAt = b.finaleAt;
        specials = Collections.unmodifiableList(new ArrayList<>(b.specials));
        finisher = b.finisher;
        music = b.music;
        fightRadius = b.fightRadius;
        title = b.title;
        npc = b.npc;
    }

    public int phaseCount() {
        return phases.length + 1;
    }

    public BarPhase barPhase(int phase) {
        if (bar.isEmpty()) return new BarPhase(id + "_bossbar", Overlay.NONE, null);
        return bar.get(Math.max(0, Math.min(bar.size() - 1, phase)));
    }

    /** lang key of the line under the bar. */
    public String epithetKey() {
        return "ui.pohsmp_core." + id + ".epithet";
    }

    public static Builder builder(String id) {
        return new Builder(id);
    }

    public static final class Builder {
        private final String id;
        private double[] phases = {0.66, 0.33};
        private final List<BarPhase> bar = new ArrayList<>();
        private int color = 0xFFFFFF;
        private Finale finale = Finale.DEATH;
        private double finaleAt = 0;
        private final List<Special> specials = new ArrayList<>();
        private boolean finisher;
        private String music, title, npc;
        private double fightRadius = 48;

        private Builder(String id) {
            this.id = id;
            this.title = id;
            this.music = "music." + id;
        }

        /** Phase thresholds (fractions of max health where phases 2, 3... begin). Default 0.66, 0.33. */
        public Builder phases(double... thresholds) {
            for (int i = 1; i < thresholds.length; i++)
                if (thresholds[i] >= thresholds[i - 1]) throw new IllegalArgumentException("phases must go down: " + id);
            phases = thresholds.clone();
            return this;
        }

        /**
         * The usual bar set: <id>_bossbar, <id>_bossbar_p2, <id>_bossbar_p3 ... one per phase, no overlays; then
         * {@link #overlay} for the animated ones.
         */
        public Builder standardBar() {
            bar.clear();
            for (int i = 0; i <= phases.length; i++) bar.add(new BarPhase(id + "_bossbar" + (i == 0 ? "" : "_p" + (i + 1)), Overlay.NONE, null));
            return this;
        }

        /** Sets the overlay of a phase (0-based): e.g. overlay(1, PULSE, "pulse"), overlay(2, FRAMES, "flames"). */
        public Builder overlay(int phase, Overlay o, String suffix) {
            if (bar.isEmpty()) standardBar();
            BarPhase p = bar.get(phase);
            bar.set(phase, new BarPhase(p.sprite(), o, o == Overlay.NONE ? null : p.sprite() + "_" + suffix));
            return this;
        }

        public Builder color(int rgb) {
            color = rgb & 0xFFFFFF;
            return this;
        }

        public Builder death() {
            finale = Finale.DEATH;
            finaleAt = 0;
            return this;
        }

        /** Surrenders at `at` and becomes the NPC entity pohsmp_core:<npcId> (registered with Bosses.npc). */
        public Builder surrender(double at, String npcId) {
            finale = Finale.SURRENDER;
            finaleAt = at;
            npc = npcId;
            return this;
        }

        public Builder leave(double at) {
            finale = Finale.LEAVE;
            finaleAt = at;
            return this;
        }

        public Builder special(String specialId, double at) {
            specials.add(new Special(specialId, at));
            return this;
        }

        public Builder finisher(boolean on) {
            finisher = on;
            return this;
        }

        public Builder music(String soundId) {
            music = soundId;
            return this;
        }

        public Builder title(String titleBase) {
            title = titleBase;
            return this;
        }

        public Builder fightRadius(double r) {
            fightRadius = r;
            return this;
        }

        public BossDef build() {
            if (bar.isEmpty()) standardBar();
            BossDef d = new BossDef(this);
            BossDefs.register(d);
            return d;
        }
    }

    /** All defined bosses by id (both sides). */
    public static final class BossDefs {
        private BossDefs() {}

        private static final Map<String, BossDef> ALL = new LinkedHashMap<>();

        static synchronized void register(BossDef d) {
            ALL.put(d.id, d);
        }

        public static synchronized BossDef get(String id) {
            return ALL.get(id);
        }

        public static synchronized List<String> ids() {
            return new ArrayList<>(ALL.keySet());
        }
    }
}
