package ru.pohsmp.core.boss;

import java.util.ArrayList;
import java.util.List;

/**
 * A fixed-length script by ticks (owner: «ролики фиксированной длительности»): actions at given ticks of the script, run once each
 * as the script's clock passes them, in order (same tick: in the order added). The clock is advanced by its owner (the boss tick),
 * so a script never waits for anything; {@link #cancel} drops what is left. Pure Java (BossTimelineTest).
 */
public final class BossTimeline {
    private record Step(int at, Runnable run) {}

    private final List<Step> steps = new ArrayList<>();
    private final String name;
    private final int length;
    private int t = -1, next;
    private boolean cancelled;
    private Runnable onEnd;

    public BossTimeline(String name, int length) {
        this.name = name;
        this.length = length;
    }

    /** Adds an action at tick `at` (0 = the first tick). Steps may be added in any order before the script starts. */
    public BossTimeline at(int at, Runnable r) {
        if (t >= 0) throw new IllegalStateException("timeline " + name + " already running");
        int i = steps.size();
        while (i > 0 && steps.get(i - 1).at > at) i--;
        steps.add(i, new Step(at, r));
        return this;
    }

    /** Runs every tick from `from` to `to` inclusive (the step gets the tick number). */
    public BossTimeline during(int from, int to, java.util.function.IntConsumer r) {
        for (int i = from; i <= to; i++) {
            int k = i;
            at(i, () -> r.accept(k));
        }
        return this;
    }

    /** Runs when the script ends by itself (not on cancel). */
    public BossTimeline then(Runnable r) {
        onEnd = r;
        return this;
    }

    /** Advances one tick; returns false when the script is over (ended or cancelled). */
    public boolean tick() {
        if (cancelled) return false;
        t++;
        while (next < steps.size() && steps.get(next).at <= t) steps.get(next++).run.run();
        if (t >= length) {
            cancelled = true;
            if (onEnd != null) onEnd.run();
            return false;
        }
        return true;
    }

    public void cancel() {
        cancelled = true;
    }

    public boolean done() {
        return cancelled;
    }

    /** Current tick of the script (-1 before the first tick). */
    public int time() {
        return t;
    }

    public int length() {
        return length;
    }

    public String name() {
        return name;
    }
}
