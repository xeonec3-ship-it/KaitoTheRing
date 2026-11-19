package ru.pohsmp.core.fx;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.List;
import ru.pohsmp.core.fx.FxMath.Vec;

/**
 * Memory of a moving point for trail / ribbon (docs/fx.md): samples (time, position) newest first, older than `length`
 * ticks dropped. Samples closer than `minStep` blocks to the previous one replace it, so a resting point keeps one sample.
 */
public final class FxTrail {
    public record Sample(double time, Vec pos) {}

    private final Deque<Sample> samples = new ArrayDeque<>();
    private final double length, minStep;

    public FxTrail(double length, double minStep) {
        this.length = Math.max(1, length);
        this.minStep = minStep;
    }

    public void add(double time, Vec pos) {
        Sample head = samples.peekFirst();
        if (head != null && time < head.time()) samples.clear();            // time went back (rewound / reloaded): start over
        if (head != null && samples.size() > 1 && head.pos().dist(pos) < minStep) samples.pollFirst();
        samples.addFirst(new Sample(time, pos));
        while (samples.size() > 2 && time - samples.peekLast().time() > length) samples.pollLast();
    }

    /** Samples newest first, with the age fraction 0 (now) .. 1 (length ticks ago). */
    public List<Sample> samples() {
        return new ArrayList<>(samples);
    }

    public double age(Sample s, double now) {
        return Math.max(0, Math.min(1, (now - s.time()) / length));
    }

    public int size() {
        return samples.size();
    }
}
