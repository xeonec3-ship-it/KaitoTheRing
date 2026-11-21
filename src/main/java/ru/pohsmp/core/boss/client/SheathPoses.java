package ru.pohsmp.core.boss.client;

import com.mojang.blaze3d.vertex.PoseStack;
import java.util.Map;
import java.util.Set;
import java.util.WeakHashMap;
import net.minecraft.world.entity.Entity;
import software.bernie.geckolib.animatable.GeoEntity;
import software.bernie.geckolib.core.animation.AnimationController;

/**
 * Iron's poses with no room for a one-handed weapon in the right hand (letter 2026-11-21_mgr_t26_hold_tyros §11): kneeling_prayer (the
 * hands folded at the chest — the rapier went through the body ~200 frames), self_cast_two_hands, cross_arms. While one plays, the
 * weapon shrinks into the fist (scale about the grip point, quintic over {@link #TICKS} ticks) and grows back after — from Iron's
 * HumanoidRenderer.adjustHandItemRendering, so no animation keys: the hand stays a fist. Iron's own sheath (shouldWeaponBeSheathed)
 * works only for SwordItem and hangs it at the hip — in kneeling_prayer that is through the thigh — so it is not used.
 */
public final class SheathPoses {
    public static final Set<String> POSES = Set.of("kneeling_prayer", "self_cast_two_hands", "cross_arms");
    public static final float TICKS = 4;

    private static final Map<Entity, float[]> STATE = new WeakHashMap<>();   // {weight 0..1 (1 = in hand), last time}

    private SheathPoses() {}

    @SuppressWarnings({"rawtypes"})
    public static boolean playing(Entity e) {
        if (!(e instanceof GeoEntity geo)) return false;
        var manager = geo.getAnimatableInstanceCache().getManagerForId(e.getId());
        if (manager == null) return false;
        for (AnimationController c : manager.getAnimationControllers().values()) {
            var q = c.getCurrentAnimation();
            if (q == null || !POSES.contains(q.animation().name())) continue;
            var st = c.getAnimationState();
            if (st == AnimationController.State.RUNNING || st == AnimationController.State.TRANSITIONING) return true;
        }
        return false;
    }

    /** How much of the weapon is shown (1 — whole, 0 — hidden in the fist), eased. */
    public static float shown(Entity e, float pt) {
        float now = e.tickCount + pt;
        float[] s = STATE.computeIfAbsent(e, k -> new float[] {1, now});
        float dt = Math.max(0, Math.min(TICKS, now - s[1]));
        s[1] = now;
        s[0] = playing(e) ? Math.max(0, s[0] - dt / TICKS) : Math.min(1, s[0] + dt / TICKS);
        float x = s[0];
        return x * x * x * (x * (6 * x - 15) + 10);
    }

    /** For HumanoidRenderer.adjustHandItemRendering: scales the held weapon about the grip. */
    public static void apply(PoseStack ps, Entity e, float pt) {
        float k = shown(e, pt);
        if (k < 1) ps.scale(Math.max(1e-3f, k), Math.max(1e-3f, k), Math.max(1e-3f, k));
    }
}
