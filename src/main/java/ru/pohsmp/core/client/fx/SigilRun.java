package ru.pohsmp.core.client.fx;

import java.util.ArrayList;
import java.util.List;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.fx.sigil.SigilDef;
import ru.pohsmp.core.fx.sigil.SigilHit;

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
    /** Plane normal for OUTWARD (from the anchor to the sigil); null = straight up. */
    public Vec3 normal;
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
    /** T08: hits drawn now, in plane coordinates (SigilHit); filled from {@link #pending} by SigilDraw, which knows the plane. */
    public final List<SigilHit.Event> hits = new ArrayList<>();
    /** T08: hits that came in since the last frame: world offset from the centre, tick since start, power, seed. */
    final List<Pending> pending = new ArrayList<>();

    record Pending(Vec3 offset, double at, double power, int seed) {}

    /**
     * A hit at world point {@code at} (FxMsg HIT), {@code tick} ticks after this sigil started. Ignored by sigils without
     * {@code hit} / {@code reactsToHits} and while dissolving. Children get it too (each keeps it if it is near enough).
     */
    public void hit(Vec3 at, double tick, double power, int seed) {
        if (def != null && def.hit() != null && Double.isNaN(stopAt) && pending.size() < 16)
            pending.add(new Pending(at.subtract(pos(0)), tick, power, seed));
        for (SigilRun c : children) c.hit(at, tick - (c.start - start), power, seed * 31 + 7);
    }

    public Vec3 pos(float pt) {
        if (follow != null && follow.isAlive()) return follow.getPosition(pt).add(offset);
        return base;
    }

    public void stop(double t) {
        if (Double.isNaN(stopAt)) stopAt = Math.max(0, t);
        for (SigilRun c : children) c.stop(t - (c.start - start));
    }
}
