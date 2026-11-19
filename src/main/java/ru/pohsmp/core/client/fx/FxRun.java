package ru.pohsmp.core.client.fx;

import java.util.HashMap;
import java.util.Map;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.fx.FxDef;
import ru.pohsmp.core.fx.FxMath;
import ru.pohsmp.core.fx.FxStyle;

/** One running effect on this client: definition, style, who/where (live entities when known), per-element state. */
public final class FxRun {
    public FxDef def;
    public FxStyle style;
    public double start, stopAt = Double.NaN;
    public int duration = -1;
    public Vec3 base = Vec3.ZERO, attachOffset = Vec3.ZERO;
    public float yaw, pitch;
    public Entity caster, target, attach;
    public Vec3 targetPos, look;
    public final Map<String, Vec3> points = new HashMap<>();
    /** text slots of this instance (Fx.Spec.text), handed to its sigil elements (T24: the nameplate) */
    public final Map<String, String> texts = new HashMap<>();
    public double scale = 1;
    public long seed;
    public int color = -1;
    /** Per element index: state kept between frames (fixed anchor points, sub-sigils, meshes). */
    public final Map<Integer, ElementDraw.State> state = new HashMap<>();

    public int length() {
        return duration >= 0 ? duration : def.duration();
    }

    public Vec3 origin(float pt) {
        if (attach != null && attach.isAlive()) return attach.getPosition(pt).add(attachOffset);
        return base;
    }

    public FxDef.Context ctx(float pt) {
        Vec3 c = caster != null && caster.isAlive() ? caster.getPosition(pt) : origin(pt);
        double y = caster != null && caster.isAlive() ? caster.getViewYRot(pt) : yaw;
        Vec3 eyes = caster != null && caster.isAlive() ? caster.getEyePosition(pt) : c.add(0, 1.6, 0);
        FxMath.Vec e = v(eyes);
        FxMath.Vec hand = FxMath.offset(e, y, 0.35, -0.45, 0.3);
        Vec3 t = target != null && target.isAlive() ? target.getPosition(pt) : targetPos;
        Map<String, FxMath.Vec> pts = new HashMap<>();
        points.forEach((k, p) -> pts.put(k, v(p)));
        return new FxDef.Context(v(c), e, hand, y, t == null ? null : v(t), look == null ? null : v(look), pts, scale, seed);
    }

    static FxMath.Vec v(Vec3 p) {
        return new FxMath.Vec(p.x, p.y, p.z);
    }

    static Vec3 w(FxMath.Vec p) {
        return new Vec3(p.x(), p.y(), p.z());
    }
}
