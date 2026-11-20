package ru.pohsmp.core.boss.irina.client;

import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.client.event.EntityRenderersEvent;
import ru.pohsmp.core.boss.BossMath;
import ru.pohsmp.core.boss.client.BossCam;
import ru.pohsmp.core.boss.client.BossCam.Shot;
import ru.pohsmp.core.boss.irina.Irina;
import ru.pohsmp.core.boss.irina.IrinaMath;

/**
 * T27 client: the renderer and the camera plans of the scenes by the seconds of docs/specs/tasks/T27_irina_boss.md «Визуал и
 * ролики» (I — Irina, «forward» — her look at the scene start, V — the victim). Heights: the hood (her «face», darkness) +2.0, the
 * hat brim r ≈ 0.75 at +2.25 — close shots stay at +3.0 or lower and never inside the hat or the cocoon.
 */
public final class IrinaClient {
    private IrinaClient() {}

    @SuppressWarnings({"unchecked", "rawtypes"})
    public static void renderers(EntityRenderersEvent.RegisterRenderers e) {
        e.registerEntityRenderer((EntityType) Irina.TYPE.get(), c -> new IrinaRenderer((EntityRendererProvider.Context) c));
    }

    private static double sine(double k) {
        return BossMath.sine(k);
    }

    private static Vec3 up(Vec3 p, double h) {
        return p.add(0, h, 0);
    }

    /** Flat unit direction from a to b (or fallback). */
    private static Vec3 dir(Vec3 a, Vec3 b, Vec3 fallback) {
        Vec3 d = b.subtract(a).multiply(1, 0, 1);
        return d.lengthSqr() < 1e-4 ? fallback : d.normalize();
    }

    private static Vec3 rotY(Vec3 d, double deg) {
        double a = Math.toRadians(deg);
        return new Vec3(d.x * Math.cos(a) - d.z * Math.sin(a), 0, d.x * Math.sin(a) + d.z * Math.cos(a));
    }

    public static void setup() {
        // «Появление» 7 s
        BossCam.plan("irina.intro", IrinaMath.INTRO)
                .shot(0, (k, t, c) -> Shot.of(c.orbit(c.b, 35, 6 - 1.5 * sine(k), 0.8), up(c.b, 0.6)))            // кокон: low, 35° aside, 6 → 4.5
                .shot(28, (k, t, c) -> Shot.of(c.orbit(c.b, 35 + 60 * sine(k), 4.5, 1.2), up(c.b, 0.8)))          // облёт 60°
                .cut(IrinaMath.INTRO_UNRAVEL, (k, t, c) -> Shot.of(c.rel(c.b, 7 + sine(k), 0, 1.5), up(c.b, 1.4)))   // расплетание: front 7 → 8
                .shot(88, (k, t, c) -> Shot.of(c.rel(c.b, 3.5, 0, 0.9), up(c.b, 2.4)))                             // шляпа: front-below
                .cut(IrinaMath.INTRO_FLOURISH, (k, t, c) -> Shot.of(c.rel(c.b, 10, 0, 2.5), up(c.b, 1.6)));         // взмах: wide

        // «Смерть» 5 s
        BossCam.plan("irina.death", IrinaMath.DEATH)
                .shot(0, (k, t, c) -> Shot.of(c.orbit(c.b, 90 + 20 * sine(k), 5, 1.6), up(c.b, 1.6)))             // удар: side, 20° orbit
                .shot(IrinaMath.DEATH_KNEES, (k, t, c) -> Shot.of(c.orbit(c.b, 30, 3.5, 0.7), up(c.b, 1.2 - 0.7 * sine(k))))   // шляпа
                .shot(IrinaMath.DEATH_FALL, (k, t, c) -> Shot.of(c.orbit(c.b, 30, 3.5 + 2.5 * sine(Math.min(1, k * 2)), 2.5), up(c.b, 0.5)));   // нити

        // «Чужое счастье» 6 s (focus = where she stood)
        BossCam.plan("irina.happiness", IrinaMath.HAPPY)
                .shot(0, (k, t, c) -> Shot.of(c.rel(c.b, 5, 0, 1.0), up(c.b, 2)))                                  // подъём: up at her
                .shot(IrinaMath.HAPPY_SPREAD, (k, t, c) -> {                                                        // общий с высоты, players' side
                    Vec3 me = Minecraft.getInstance().player != null ? Minecraft.getInstance().player.position() : c.rel(c.focus, 24, 0, 0);
                    Vec3 d = dir(c.focus, me, c.fwd);
                    return Shot.of(up(c.focus.add(d.scale(24)), 18), up(c.b, 1));
                })
                .shot(IrinaMath.HAPPY_GATHER, (k, t, c) -> Shot.of(c.orbit(c.b, 40 * sine(k), 10, 4), up(c.b, 1.6)))   // воронка: 40° orbit
                .cut(IrinaMath.HAPPY_ABSORB, (k, t, c) -> Shot.of(c.rel(c.b, 4, 0, 2), up(c.b, 2)).shake(t < IrinaMath.HAPPY_ABSORB + 6 ? 0.06 : 0));   // поглощение

        // «Только мой», everyone but the victim (0–2 s, then back in 1 s); extra = the victim
        BossCam.plan("irina.only_mine", IrinaMath.MINE_CAM_END)
                .shot(0, (k, t, c) -> {   // ладонь: over her shoulder, on the victim
                    Vec3 v = c.extra != null ? c.extra.getPosition(c.pt) : c.rel(c.b, 6, 0, 0);
                    return Shot.of(c.rel(c.b, -3.6, 1.6, 2.2), up(v, 1));
                })
                .cut(IrinaMath.MINE_YANK, (k, t, c) -> {   // рывок → кокон: beside both, between them
                    Vec3 v = c.extra != null ? c.extra.getPosition(c.pt) : c.rel(c.b, 2, 0, 0);
                    Vec3 mid = c.b.lerp(v, 0.5);
                    return Shot.of(up(mid.add(c.side.scale(6)), 1.5), up(mid, 1.2));
                });

        // «Только мой», the victim's own camera from the yank to the crush: 3 behind-above it, on her hood, to see the allies tear the cocoon
        BossCam.plan("irina.only_mine_victim", IrinaMath.MINE_CRUSH - IrinaMath.MINE_YANK)
                .shot(0, (k, t, c) -> {
                    Entity v = c.extra;
                    if (v == null) return Shot.of(c.rel(c.b, 5, 0, 2.5), up(c.b, 2));
                    Vec3 vp = v.getPosition(c.pt);
                    Vec3 d = dir(c.b, vp, c.fwd);
                    return Shot.of(up(vp.add(d.scale(3)), 2.5), up(c.b, 2));
                });

        // the finisher, only the victim's camera (0.3–2.3 s): beside the victim, 15° aside, at its eyes, on her hood
        BossCam.plan("irina.finisher", IrinaMath.FINISHER_CAM)
                .shot(0, (k, t, c) -> {
                    Entity v = c.extra;
                    Vec3 hood = up(c.b, 2.0);
                    if (v == null) return Shot.of(c.rel(c.b, 2.4, 0, 1.6), hood);
                    Vec3 vp = v.getPosition(c.pt);
                    Vec3 d = rotY(dir(c.b, vp, c.fwd), 15);
                    Vec3 pos = c.b.add(d.scale(2.4));
                    return Shot.of(new Vec3(pos.x, vp.y + v.getEyeHeight(), pos.z), hood)
                            .shake(t >= IrinaMath.FINISHER_PIERCE - IrinaMath.FINISHER_CAM_FROM && t < IrinaMath.FINISHER_PIERCE - IrinaMath.FINISHER_CAM_FROM + 4 ? 0.06 : 0);
                });
    }
}
