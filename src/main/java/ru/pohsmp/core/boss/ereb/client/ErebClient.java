package ru.pohsmp.core.boss.ereb.client;

import java.util.HashMap;
import java.util.Map;
import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.client.renderer.entity.NoopRenderer;
import net.minecraft.client.renderer.entity.ThrownItemRenderer;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.client.event.ClientPlayerNetworkEvent;
import net.minecraftforge.client.event.EntityRenderersEvent;
import net.minecraftforge.client.event.RenderPlayerEvent;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.boss.BossMath;
import ru.pohsmp.core.boss.client.BossCam;
import ru.pohsmp.core.boss.client.BossCam.Shot;
import ru.pohsmp.core.boss.ereb.Ereb;
import ru.pohsmp.core.boss.ereb.ErebBody;
import ru.pohsmp.core.boss.ereb.ErebEntity;
import ru.pohsmp.core.boss.ereb.ErebMath;
import ru.pohsmp.core.boss.ereb.ErebReflection;

/**
 * T30 client: renderers (Ereb and his reflections — one look; the glass shards; the invisible dream point), «Предательство» (while it
 * is on, this player sees every other player of the fight as Ereb), the camera plans of the scenes by the seconds of
 * docs/specs/tasks/T30_ereb_boss.md «Визуал и ролики» (E — Ereb, «forward» — his look; heights for his player-sized body: eyes +1.62,
 * chest +1.3).
 */
public final class ErebClient {
    private ErebClient() {}

    @SuppressWarnings({"unchecked", "rawtypes"})
    public static void renderers(EntityRenderersEvent.RegisterRenderers e) {
        e.registerEntityRenderer((EntityType) Ereb.TYPE.get(), c -> new ErebRenderer((EntityRendererProvider.Context) c));
        e.registerEntityRenderer((EntityType) Ereb.REFLECTION.get(), c -> new ErebRenderer((EntityRendererProvider.Context) c));
        e.registerEntityRenderer(Ereb.SHARD.get(), c -> new ThrownItemRenderer<>(c, 0.6f, true));
        e.registerEntityRenderer(Ereb.DREAM_POINT.get(), NoopRenderer::new);
    }

    /** Client setup: camera plans and the betrayal events. */
    public static void setup() {
        MinecraftForge.EVENT_BUS.register(ErebClient.class);
        plans();
    }

    // ---------------------------------------------------------------- «Предательство»: the others look like him

    /** Player id → its Ereb double on this client (not in the level). */
    private static final Map<Integer, ErebReflection> DOUBLES = new HashMap<>();
    private static ErebBody betrayer;

    /** The Ereb whose betrayal this client is in (near it, on), or null. Looked up once a tick. */
    @SubscribeEvent
    public static void onTick(TickEvent.ClientTickEvent e) {
        if (e.phase != TickEvent.Phase.END) return;
        Minecraft mc = Minecraft.getInstance();
        betrayer = null;
        if (mc.level == null || mc.player == null) {
            DOUBLES.clear();
            return;
        }
        for (ErebEntity b : mc.level.getEntitiesOfClass(ErebEntity.class, mc.player.getBoundingBox().inflate(64)))
            if (b.betrayal()) betrayer = b;
        if (betrayer == null) {
            DOUBLES.clear();
            return;
        }
        for (var it = DOUBLES.entrySet().iterator(); it.hasNext(); ) {
            var en = it.next();
            if (!(mc.level.getEntity(en.getKey()) instanceof Player p)) {
                it.remove();
                continue;
            }
            ErebReflection d = en.getValue();
            d.tickCount++;
            ErebDisguise.copyWalk(d, p);
        }
    }

    @SubscribeEvent
    public static void onRenderPlayer(RenderPlayerEvent.Pre e) {
        Minecraft mc = Minecraft.getInstance();
        Player p = e.getEntity();
        if (betrayer == null || p == mc.player || mc.player == null || !(p.level() instanceof ClientLevel lvl)) return;
        if (p.distanceToSqr(betrayer) > 48 * 48 || mc.player.distanceToSqr(betrayer) > 48 * 48) return;
        ErebReflection d = DOUBLES.computeIfAbsent(p.getId(), k -> Ereb.REFLECTION.get().create(lvl));
        if (d == null) return;
        e.setCanceled(true);
        float pt = e.getPartialTick();
        d.setPos(p.getX(), p.getY(), p.getZ());
        d.xo = p.xo;
        d.yo = p.yo;
        d.zo = p.zo;
        d.setYRot(p.getYRot());
        d.yRotO = p.yRotO;
        d.setXRot(p.getXRot());
        d.xRotO = p.xRotO;
        d.yBodyRot = p.yBodyRot;
        d.yBodyRotO = p.yBodyRotO;
        d.yHeadRot = p.yHeadRot;
        d.yHeadRotO = p.yHeadRotO;
        d.hurtTime = p.hurtTime;
        d.attackAnim = p.attackAnim;
        d.oAttackAnim = p.oAttackAnim;
        mc.getEntityRenderDispatcher().getRenderer(d).render(d, Mth.lerp(pt, p.yRotO, p.getYRot()), pt, e.getPoseStack(), e.getMultiBufferSource(),
                e.getPackedLight());
    }

    @SubscribeEvent
    public static void onLogout(ClientPlayerNetworkEvent.LoggingOut e) {
        DOUBLES.clear();
        betrayer = null;
        ErebDisguise.clear();
    }

    // ---------------------------------------------------------------- camera plans

    private static double sine(double k) {
        return BossMath.sine(k);
    }

    private static void plans() {
        // «Появление» 5.0 s
        BossCam.plan("ereb.intro", ErebMath.INTRO)
                .shot(0, (k, t, c) -> Shot.of(c.orbit(c.focus, 25 * sine(k), 12, 4), c.focus.add(0, 1.5, 0)))   // рой: wide, slow 25° orbit
                .shot(30, (k, t, c) -> {   // сжатие: push 12 → 6, height 4 → 2
                    double s = sine(k);
                    return Shot.of(c.orbit(c.focus, 25, 12 - 6 * s, 4 - 2 * s), c.focus.add(0, 1.5, 0));
                })
                .cut(ErebMath.INTRO_FORM, (k, t, c) ->   // звон стекла → поклон: front-side 30°, 4.5 → 5.5, on the chest
                        Shot.of(c.orbit(c.focus, 30, 4.5 + sine(BossMath.clamp01((t - ErebMath.INTRO_BOW) / 18.0)), 1.6), c.focus.add(0, 1.3, 0)))
                .cut(ErebMath.INTRO_TITLE, (k, t, c) -> Shot.of(c.rel(c.focus, 3.5, 0, 0.9), c.focus.add(0, 1.8, 0)));   // салют: low, up at the face

        // «Ложный союзник»: the victim's camera from E's appearance (0.8 s of the special) for 36 ticks; extra = the victim
        BossCam.plan("ereb.false_ally", ErebMath.FA_CAM)
                .shot(0, (k, t, c) -> {   // через плечо: 2.2 side-behind the victim (60° off its back), on the point 1 behind it
                    Vec3 v = c.extra != null ? c.extra.getPosition(c.pt) : c.focus;
                    Vec3 back = v.subtract(c.fwd).add(0, 1.4, 0);
                    double shake = t >= ErebMath.FA_STAB - ErebMath.FA_APPEAR && t < ErebMath.FA_STAB - ErebMath.FA_APPEAR + 5 ? 0.25 : 0;
                    return Shot.of(c.orbit(v, 120, 2.2, 1.9), back).shake(shake);
                })
                .shot(ErebMath.FA_STAB - ErebMath.FA_APPEAR + 8, (k, t, c) -> {   // маска спадает: back 2.2 → 4, on E
                    Vec3 v = c.extra != null ? c.extra.getPosition(c.pt) : c.focus;
                    return Shot.of(c.orbit(v, 120, 2.2 + 1.8 * sine(k), 1.9), c.b.add(0, 1.6, 0));
                });

        // the finisher, only the victim's camera (1.2 s from his coming out): on his head from beside the victim, a tremble on the thrust
        BossCam.plan("ereb.finisher", ErebMath.FIN_CAM)
                .shot(0, (k, t, c) -> {
                    Vec3 v = c.extra != null ? c.extra.getPosition(c.pt) : c.focus;
                    Vec3 head = c.b.add(0, 1.6, 0);
                    double shake = t >= ErebMath.FIN_STAB - ErebMath.FIN_APPEAR && t < ErebMath.FIN_STAB - ErebMath.FIN_APPEAR + 4 ? 0.12 : 0;
                    return Shot.of(c.orbit(v, 70, 2.4 + 0.4 * sine(k), 1.7), head).shake(shake);
                });

        // Финал: up to the cast (3.2 s); then the camera of the spell's own scene (T22 «Небесная бабочка»)
        BossCam.plan("ereb.finale", ErebMath.FINALE_CAST + 2)
                .shot(0, (k, t, c) -> Shot.of(c.rel(c.b, 2.2, 0, 1.62), c.b.add(0, 1.62, 0)))   // улыбка: close on the face
                .cut(24, (k, t, c) -> Shot.of(c.orbit(c.b, 35, 1.8, 1.3), c.rel(c.b, 0.55, 0.15, 1.25)))   // бабочка из ладони
                .cut(44, (k, t, c) -> Shot.of(c.rel(c.b, 3, 0, 1.62), c.b.add(0, 1.62, 0)))   // фраза
                .shot(56, (k, t, c) -> {   // подъём: back 1.8 → 4, up 1.3 → 2.2, on the raised hand
                    double s = sine(k);
                    return Shot.of(c.orbit(c.b, 35, 1.8 + 2.2 * s, 1.3 + 0.9 * s), c.b.add(0, 2.3, 0));
                });
    }
}
