package ru.pohsmp.core.fx.sigil;

import java.util.Locale;

/** Easing curves by the names used in sigil JSON (docs/sigils.md). Input is clamped to 0..1. */
public enum Easing {
    LINEAR, EASE_IN_SINE, EASE_OUT_SINE, EASE_IN_OUT_SINE, EASE_IN_CUBIC, EASE_OUT_CUBIC, EASE_IN_OUT_CUBIC, EASE_OUT_BACK;

    public double apply(double t) {
        t = Math.max(0, Math.min(1, t));
        return switch (this) {
            case LINEAR -> t;
            case EASE_IN_SINE -> 1 - Math.cos(t * Math.PI / 2);
            case EASE_OUT_SINE -> Math.sin(t * Math.PI / 2);
            case EASE_IN_OUT_SINE -> -(Math.cos(Math.PI * t) - 1) / 2;
            case EASE_IN_CUBIC -> t * t * t;
            case EASE_OUT_CUBIC -> 1 - Math.pow(1 - t, 3);
            case EASE_IN_OUT_CUBIC -> t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
            case EASE_OUT_BACK -> {
                double c1 = 1.70158, c3 = c1 + 1;
                yield 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2);
            }
        };
    }

    /** "easeOutCubic" -> EASE_OUT_CUBIC; unknown or null -> LINEAR. */
    public static Easing byName(String name) {
        if (name == null || name.isEmpty()) return LINEAR;
        String snake = name.replaceAll("([a-z])([A-Z])", "$1_$2").toUpperCase(Locale.ROOT);
        try {
            return valueOf(snake);
        } catch (IllegalArgumentException e) {
            return LINEAR;
        }
    }
}
