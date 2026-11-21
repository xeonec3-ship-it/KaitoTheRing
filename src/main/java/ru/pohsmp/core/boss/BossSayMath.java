package ru.pohsmp.core.boss;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.List;
import java.util.function.ToIntFunction;

/**
 * The bosses' spoken lines on screen (owner 21.11: «красиво, а не как в чате»): timings, wrapping, the queue and the layout of the
 * subtitle «свиток» drawn by boss/client/BossSayClient. Pure (no Minecraft classes), so it is unit-tested. Times are in ticks (20/s).
 *
 * <p>A line: the scroll fades in and rises (IN), the text is typed from TYPE_DELAY at {@link #CPS} characters a second, stays
 * {@link #hold} after the last letter (2.5 s + 0.06 s a character), fades out (OUT). Several lines in a row queue up; while
 * something waits, the current one stays at most {@link #QUEUE_HOLD} after it is typed.
 */
public final class BossSayMath {
    private BossSayMath() {}

    /** Typing speed, characters a second. */
    public static final double CPS = 40;
    public static final int IN = 7, TYPE_DELAY = 3, OUT = 10;
    /** Hold after the last letter: HOLD_BASE + HOLD_PER_CHAR × length (2.5 s + 0.06 s a character). */
    public static final double HOLD_BASE = 50, HOLD_PER_CHAR = 1.2;
    /** While another line waits, the current one holds at most this long after it is typed. */
    public static final int QUEUE_HOLD = 30;
    /** At most this many lines wait; older waiting ones are dropped. */
    public static final int QUEUE_MAX = 4;
    /** How far the scroll rises while fading in (GUI px). */
    public static final int RISE = 6;
    /** A quiet pen sound every this many typed letters. */
    public static final int SOUND_EVERY = 5;

    /** The boss styles (textures/gui/boss_say/<id>.png); their order is the wire index (BossNet.SAY d). */
    public static final List<String> STYLES = List.of("cult_leader", "irina", "aris", "martin", "ereb", "ereb_hand");

    public static int styleIndex(String bossId) {
        return STYLES.indexOf(bossId);
    }

    /** The texture name of a style index; unknown → "default". */
    public static String styleName(int index) {
        return index >= 0 && index < STYLES.size() ? STYLES.get(index) : "default";
    }

    // ---------------------------------------------------------------- system lines

    /** BossNet.SAY c: 0 — the boss speaks (its name over the line), SYSTEM — a system line of the fight (no speaker, neutral). */
    public static final int SPEECH = 0, SYSTEM = 1;
    /** The separator of the packed arguments of a system line (BossNet.SAY s2); the wire string is at most ARGS_MAX long. */
    public static final char ARG_SEP = '\u0001';
    public static final int ARGS_MAX = 250;
    /** The text of a system line: a cool neutral grey-white (no boss tint, not italic). */
    public static final int SYSTEM_TEXT = 0xD6D3CC;
    /** The boss marks by a system line: dimmed to this opacity (a small sign of whose fight it is, not a name). */
    public static final float SYSTEM_MARK_ALPHA = 0.55f;

    /** Arguments of a system line into one wire string (each cut so the whole fits ARGS_MAX; null → ""). */
    public static String packArgs(String... args) {
        if (args == null || args.length == 0) return "";
        int each = Math.max(1, (ARGS_MAX - (args.length - 1)) / args.length);
        StringBuilder b = new StringBuilder();
        for (int i = 0; i < args.length; i++) {
            if (i > 0) b.append(ARG_SEP);
            String a = args[i] == null ? "" : args[i].replace(ARG_SEP, ' ');
            b.append(a.length() > each ? a.substring(0, each) : a);
        }
        return b.toString();
    }

    public static String[] unpackArgs(String packed) {
        if (packed == null || packed.isEmpty()) return new String[0];
        return packed.split(String.valueOf(ARG_SEP), -1);
    }

    /** Height of a system scroll: no name line. */
    public static int systemBoxHeight(int lines) {
        return PAD_TOP + Math.max(1, lines) * LINE_H - 1 + PAD_BOTTOM;
    }

    /** Width of a system scroll: the text and the two small marks beside its first line (13 px each). */
    public static int systemBoxWidth(int textWidth, int guiWidth) {
        return Math.min(textWidth + 2 * 13 + 2 * PAD_X, guiWidth - 2 * SCREEN_MARGIN);
    }

    // ---------------------------------------------------------------- timings

    public static double typeTicks(int chars) {
        return Math.max(0, chars) * 20.0 / CPS;
    }

    public static double hold(int chars) {
        return HOLD_BASE + HOLD_PER_CHAR * Math.max(0, chars);
    }

    /** When (from the start) the last letter is typed. */
    public static double typedAt(int chars) {
        return TYPE_DELAY + typeTicks(chars);
    }

    /** When (from the start) it begins to fade out, if nothing waits. */
    public static double outAt(int chars) {
        return typedAt(chars) + hold(chars);
    }

    /** The whole life of a line alone on screen. */
    public static double total(int chars) {
        return outAt(chars) + OUT;
    }

    /** Letters shown at age (ticks since the start). */
    public static int visible(double age, int chars) {
        if (age <= TYPE_DELAY) return 0;
        return (int) Math.min(chars, Math.floor((age - TYPE_DELAY) * CPS / 20.0));
    }

    /** Opacity at age, given when the fade-out begins (outAt may be shortened by the queue). */
    public static float alpha(double age, double outAt) {
        if (age < 0) return 0;
        double in = Math.min(1, age / IN);
        double out = age <= outAt ? 1 : Math.max(0, 1 - (age - outAt) / OUT);
        return (float) (smooth(in) * smooth(out));
    }

    /** GUI px below the resting place (rises from RISE to 0 while fading in; sinks a little while fading out). */
    public static double rise(double age, double outAt) {
        double in = RISE * (1 - smooth(Math.min(1, Math.max(0, age / IN))));
        double out = age > outAt ? 2 * smooth(Math.min(1, (age - outAt) / OUT)) : 0;
        return in + out;
    }

    /** How many pen sounds between two counts of visible letters (0 or 1 a frame in practice). */
    public static int sounds(int before, int after) {
        return Math.max(0, after / SOUND_EVERY - before / SOUND_EVERY);
    }

    static double smooth(double x) {
        x = Math.max(0, Math.min(1, x));
        return x * x * (3 - 2 * x);
    }

    // ---------------------------------------------------------------- wrapping

    /**
     * Greedy word wrap to maxWidth by the given width function (the client passes the italic font width). A word wider than the line
     * is cut by letters. Spaces at the line breaks are dropped; empty text → no lines.
     */
    public static List<String> wrap(String text, int maxWidth, ToIntFunction<String> width) {
        List<String> out = new ArrayList<>();
        if (text == null) return out;
        String t = text.strip().replaceAll("\\s+", " ");
        if (t.isEmpty()) return out;
        StringBuilder line = new StringBuilder();
        for (String word : t.split(" ")) {
            String probe = line.length() == 0 ? word : line + " " + word;
            if (width.applyAsInt(probe) <= maxWidth) {
                line.setLength(0);
                line.append(probe);
                continue;
            }
            if (line.length() > 0) {
                out.add(line.toString());
                line.setLength(0);
            }
            // the word alone; too wide → cut it by letters
            String w = word;
            while (width.applyAsInt(w) > maxWidth && w.length() > 1) {
                int cut = w.length() - 1;
                while (cut > 1 && width.applyAsInt(w.substring(0, cut)) > maxWidth) cut--;
                out.add(w.substring(0, cut));
                w = w.substring(cut);
            }
            line.append(w);
        }
        if (line.length() > 0) out.add(line.toString());
        return out;
    }

    /** Letters of the wrapped lines (what is typed). */
    public static int chars(List<String> lines) {
        int n = 0;
        for (String l : lines) n += l.length();
        return n;
    }

    /** The typed part of each line when `visible` letters are shown (lines are typed one after another). */
    public static List<String> typed(List<String> lines, int visible) {
        List<String> out = new ArrayList<>(lines.size());
        int left = Math.max(0, visible);
        for (String l : lines) {
            int k = Math.min(l.length(), left);
            out.add(l.substring(0, k));
            left -= k;
        }
        return out;
    }

    // ---------------------------------------------------------------- layout (GUI px)

    /** Padding inside the scroll: sides, top, bottom; the name line and the gap under it; a text line. */
    public static final int PAD_X = 14, PAD_TOP = 6, PAD_BOTTOM = 6, NAME_H = 9, NAME_GAP = 5, LINE_H = 10;
    /** The text is at most this wide (and never wider than the screen allows). */
    public static final int MAX_TEXT = 300, MIN_TEXT = 100, SCREEN_MARGIN = 10;

    /** The widest text line for a GUI width: a narrow screen gets the whole width but the margins and padding. */
    public static int maxTextWidth(int guiWidth) {
        return Math.max(MIN_TEXT, Math.min(MAX_TEXT, guiWidth - 2 * (SCREEN_MARGIN + PAD_X)));
    }

    public static int boxHeight(int lines) {
        return PAD_TOP + NAME_H + NAME_GAP + Math.max(1, lines) * LINE_H - 1 + PAD_BOTTOM;
    }

    /** Scroll width for the widest of the name and the lines (the ornaments by the name take 2 × 13 px more). */
    public static int boxWidth(int nameWidth, int textWidth, int guiWidth) {
        int w = Math.max(nameWidth + 2 * 13, textWidth) + 2 * PAD_X;
        return Math.min(w, guiWidth - 2 * SCREEN_MARGIN);
    }

    /** The vanilla action bar line sits at guiHeight − 72..−64; the scroll stays above it and above the HUD rows. */
    public static final int ACTIONBAR_CLEAR = 74;

    /**
     * Bottom edge of the scroll. hud: the HUD's height at the bottom (Forge's leftHeight/rightHeight; 0 when the HUD is hidden in a
     * scene); bar: the letterbox bar height of a scene (0 without).
     */
    public static int bottom(int guiHeight, int hud, int bar) {
        if (hud <= 0) return guiHeight - Math.max(bar + 8, (int) (guiHeight * 0.1));
        return guiHeight - Math.max(ACTIONBAR_CLEAR, hud + 8);
    }

    /** The phrase colour: a warm parchment white tinted 18% towards the boss. */
    public static int textColor(int bossRgb) {
        return mix(0xF2ECDF, bossRgb, 0.18);
    }

    public static int mix(int a, int b, double t) {
        int r = (int) Math.round(((a >> 16) & 255) * (1 - t) + ((b >> 16) & 255) * t);
        int g = (int) Math.round(((a >> 8) & 255) * (1 - t) + ((b >> 8) & 255) * t);
        int bl = (int) Math.round((a & 255) * (1 - t) + (b & 255) * t);
        return (r << 16) | (g << 8) | bl;
    }

    // ---------------------------------------------------------------- the queue

    /** One line on screen or waiting; payload: whatever the client draws (its wrapped text, name, colours). */
    public static final class Line<T> {
        public final T payload;
        public final int chars;
        double start = Double.NaN;
        double outAt;

        public Line(T payload, int chars) {
            this.payload = payload;
            this.chars = chars;
        }

        public double start() {
            return start;
        }

        /** Age at which it begins to fade out (relative to its start). */
        public double outAt() {
            return outAt;
        }

        public double age(double now) {
            return now - start;
        }
    }

    /** The lines one after another: the current one and the waiting ones (oldest first). */
    public static final class Queue<T> {
        private Line<T> current;
        private final Deque<Line<T>> waiting = new ArrayDeque<>();

        public void push(Line<T> l, double now) {
            update(now);
            if (current == null) {
                begin(l, now);
                return;
            }
            waiting.addLast(l);
            while (waiting.size() > QUEUE_MAX) waiting.pollFirst();
            hurry(now);
        }

        /** The line to draw now (null: nothing); starts the next one when the current one is gone. */
        public Line<T> update(double now) {
            while (current != null && now >= current.start + current.outAt + OUT) {
                double endedAt = current.start + current.outAt + OUT;
                current = null;
                Line<T> next = waiting.pollFirst();
                if (next != null) {
                    begin(next, endedAt);   // back to back, even if this frame came late
                    hurry(now);
                }
            }
            return current;
        }

        public int waiting() {
            return waiting.size();
        }

        public void clear() {
            current = null;
            waiting.clear();
        }

        private void begin(Line<T> l, double at) {
            l.start = at;
            l.outAt = outAt(l.chars);
            current = l;
        }

        /** Something waits: the current line holds at most QUEUE_HOLD after it is typed (never cut while typing). */
        private void hurry(double now) {
            if (current == null || waiting.isEmpty()) return;
            double typed = typedAt(current.chars);
            current.outAt = Math.min(current.outAt, Math.max(typed, now - current.start) + QUEUE_HOLD);
        }
    }
}
