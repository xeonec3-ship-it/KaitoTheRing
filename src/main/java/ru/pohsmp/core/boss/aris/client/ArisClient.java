package ru.pohsmp.core.boss.aris.client;

import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.entity.NoopRenderer;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.client.event.EntityRenderersEvent;
import net.minecraftforge.client.event.ViewportEvent;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.boss.BossMath;
import ru.pohsmp.core.boss.aris.Aris;
import ru.pohsmp.core.boss.aris.ArisMath;
import ru.pohsmp.core.boss.client.BossCam;
import ru.pohsmp.core.boss.client.BossCam.Shot;
import ru.pohsmp.core.boss.client.BossNpcRenderer;

/**
 * T28 client: renderers (Aris; the anvils, blades and billets are drawn by their fx only), the look of her NPC (aris_dim, sitting
 * on the fallen hammer), the steam fog of «Закалка», and the camera plans of docs/specs/tasks/T28_aris_boss.md «Визуал и ролики»
 * (A — Aris, «forward» — her look, P — the scene focus; heights for scale 1.0: chest +1.6, head/horns +2.2…2.4).
 */
public final class ArisClient {
    private ArisClient() {}

    @SuppressWarnings({"unchecked", "rawtypes"})
    public static void renderers(EntityRenderersEvent.RegisterRenderers e) {
        e.registerEntityRenderer(Aris.TYPE.get(), ArisRenderer::new);
        e.registerEntityRenderer((EntityType) Aris.NPC.get(), c -> new BossNpcRenderer(c));
        e.registerEntityRenderer(Aris.BLADE.get(), NoopRenderer::new);
        e.registerEntityRenderer(Aris.ANVIL.get(), NoopRenderer::new);
        e.registerEntityRenderer(Aris.BILLET.get(), NoopRenderer::new);
    }

    public static void setup() {
        BossNpcRenderer.look(Aris.ID, new BossNpcRenderer.Look(new ResourceLocation(PohCore.MODID, "geo/entity/aris.geo.json"),
                new ResourceLocation(PohCore.MODID, "textures/entity/aris/aris_dim.png"),
                new ResourceLocation(PohCore.MODID, "animations/entity/aris.animation.json"), 1f));
        MinecraftForge.EVENT_BUS.register(ArisClient.class);
        plans();
    }

    // ---------------------------------------------------------------- «Закалка»: fog in the steam

    @SubscribeEvent
    public static void onFog(ViewportEvent.RenderFog e) {
        var p = Minecraft.getInstance().player;
        if (p == null || Aris.STEAMED == null) return;
        MobEffectInstance s = p.getEffect(Aris.STEAMED.get());
        if (s == null) return;
        float far = s.getAmplifier() + 1 + 1.5f;
        e.setNearPlaneDistance(0);
        e.setFarPlaneDistance(Math.min(e.getFarPlaneDistance(), far));
        e.setCanceled(true);
    }

    @SubscribeEvent
    public static void onFogColor(ViewportEvent.ComputeFogColor e) {
        var p = Minecraft.getInstance().player;
        if (p == null || Aris.STEAMED == null || !p.hasEffect(Aris.STEAMED.get())) return;
        e.setRed(0.78f);
        e.setGreen(0.8f);
        e.setBlue(0.82f);
    }

    // ---------------------------------------------------------------- camera plans

    private static double sine(double k) {
        return BossMath.sine(k);
    }

    /** Her forward now (she may turn during a scene). */
    private static Vec3 fwdNow(BossCam.Ctx c) {
        if (c.boss == null) return c.fwd;
        double a = Math.toRadians(c.boss.getViewYRot(c.pt));
        return new Vec3(-Math.sin(a), 0, Math.cos(a));
    }

    /** The side of the watching player (for the wide shots «со стороны игроков»). */
    private static Vec3 playerSide(BossCam.Ctx c) {
        var me = Minecraft.getInstance().player;
        Vec3 d = me != null ? me.position().subtract(c.focus).multiply(1, 0, 1) : Vec3.ZERO;
        return d.lengthSqr() < 1 ? c.fwd : d.normalize();
    }

    private static void plans() {
        // «Появление» 9.0 s (focus P = the spawn point; she rises from the melt there)
        BossCam.plan("aris.intro", ArisMath.INTRO)
                .shot(0, (k, t, c) -> Shot.of(c.orbit(c.focus, 30, 7 - 1.5 * sine(k), 1.0), c.focus.add(0, 0.3, 0)))   // кузня под землёй
                .cut(40, (k, t, c) -> Shot.of(c.rel(c.focus, 5, 0, 1.2), c.focus.add(0, 0.5 + 1.1 * sine(k), 0)))      // из расплава
                .shot(90, (k, t, c) -> Shot.of(c.orbit(c.focus, 25, 5.5, 1.6), c.focus.add(0, 2.2, 0)))                // встаёт
                .cut(120, (k, t, c) -> Shot.of(c.orbit(c.focus, -35, 4, 0.5), c.focus.add(0, 3.0, 0))                 // удар: from below, front-right
                        .shake(t >= ArisMath.INTRO_IMPACT && t < ArisMath.INTRO_IMPACT + 6 ? 0.12 : 0))
                .shot(144, (k, t, c) -> Shot.of(c.rel(c.focus, 9, 0, 2.4), c.focus.add(0, 1.8, 0)));                  // титр

        // «Горн» 4.0 s (focus P = the arena centre)
        BossCam.plan("aris.forge", ArisMath.FORGE)
                .shot(0, (k, t, c) -> Shot.of(c.orbit(c.b, 30, 5, 1.0), c.b.add(0, 1.2, 0)))   // молот
                .cut(20, (k, t, c) -> {   // три удара: low by the ground, aside, on the strike point; a tremble on each
                    Vec3 f = fwdNow(c), hit = c.b.add(f.scale(ArisMath.FORGE_FWD));
                    Vec3 side = new Vec3(f.z, 0, -f.x);
                    boolean shake = false;
                    for (int s : ArisMath.FORGE_STRIKES) shake |= t >= s && t < s + 4;
                    return Shot.of(c.b.add(side.scale(6)).add(0, 0.4, 0), hit.add(0, 0.2, 0)).shake(shake ? 0.1 : 0);
                })
                .cut(56, (k, t, c) -> Shot.of(c.focus.add(playerSide(c).scale(26)).add(0, 16, 0), c.focus.add(0, 1, 0)));   // общий план

        // «Последний удар молота» 5.0 s (focus P = the impact point before her)
        BossCam.plan("aris.last_blow", ArisMath.LAST)
                .shot(0, (k, t, c) -> Shot.of(c.rel(c.b, 6, 0, 1.4), c.b.add(0, 1.6, 0)))   // стойка
                .cut(28, (k, t, c) -> {   // заряд: from behind her, up at the giant hammer
                    Vec3 f = fwdNow(c);
                    return Shot.of(c.b.subtract(f.scale(4)).add(0, 2.5, 0), c.focus.add(0, 18, 0))
                            .shake(t >= ArisMath.LAST_PEAK && t < ArisMath.LAST_PEAK + 6 ? 0.06 : 0);
                })
                .cut(ArisMath.LAST_FALL, (k, t, c) -> Shot.of(c.focus.add(playerSide(c).scale(24)).add(0, 10, 0), c.focus.add(0, 4, 0))   // падение, удар
                        .shake(t >= ArisMath.LAST_BLOW && t < ArisMath.LAST_BLOW + 10 ? 0.25 : 0));

        // «Сдача» 5.0 s (focus = where she kneels)
        BossCam.plan("aris.surrender", ArisMath.SURRENDER)
                .shot(0, (k, t, c) -> Shot.of(c.orbit(c.b, 30 + 15 * sine(k), 5, 1.6), c.b.add(0, 1.6, 0)))           // сломлена
                .shot(ArisMath.SURRENDER_PLANT, (k, t, c) -> Shot.of(c.orbit(c.b, -35, 3.5, 1.0), c.b.add(0, 2.4 - 0.8 * sine(k), 0)))   // рога гаснут
                .shot(68, (k, t, c) -> Shot.of(c.orbit(c.b, -35, 3.5, 1.0), c.b.add(0, 1.6, 0)));                     // фраза
    }
}
