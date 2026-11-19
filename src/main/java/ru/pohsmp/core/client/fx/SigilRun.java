package ru.pohsmp.core.client.fx;

import java.util.ArrayList;
import java.util.List;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.fx.sigil.SigilDef;

/** One sigil being drawn on this client: definition, where, how it is turned, when it started and stopped. */
public final class SigilRun {
    public SigilDef def;
    public Vec3 base = Vec3.ZERO;
    /** Follows this entity (keeping offset) while it is alive. */
    public Entity follow;
    public Vec3 offset = Vec3.ZERO;
    /** For "caster" anchored children. */
    public Entity caster;
    public float yaw;
    public int color = -1;
    public double scale = 1, alpha = 1;
    public SigilDef.Orientation orient;
    /** Absolute game time (ticks) of the start. */
    public double start;
    /** Ticks since start when the dissolve began; NaN while running. */
    public double stopAt = Double.NaN;
    /** Optional automatic stop (ticks since start), -1 none. */
    public double stopAfter = -1;
    public long seed;
    public boolean spawned;
    /** Surface heights cached by {@link SigilLight} (groundLight / blockGlow). */
    Object light;
    public final List<SigilRun> children = new ArrayList<>();

    public Vec3 pos(float pt) {
        if (follow != null && follow.isAlive()) return follow.getPosition(pt).add(offset);
        return base;
    }

    public void stop(double t) {
        if (Double.isNaN(stopAt)) stopAt = Math.max(0, t);
        for (SigilRun c : children) c.stop(t - (c.start - start));
    }
}
