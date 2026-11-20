package ru.pohsmp.core.boss.martin.client;

import com.mojang.blaze3d.systems.RenderSystem;
import java.util.UUID;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.Font;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.client.event.CustomizeGuiOverlayEvent;
import net.minecraftforge.client.event.EntityRenderersEvent;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.boss.BossMath;
import ru.pohsmp.core.boss.client.BossCam;
import ru.pohsmp.core.boss.client.BossCam.Shot;
import ru.pohsmp.core.boss.client.BossClient;
import ru.pohsmp.core.boss.client.BossNpcRenderer;
import ru.pohsmp.core.boss.martin.Martin;
import ru.pohsmp.core.boss.martin.MartinEntity;
import ru.pohsmp.core.boss.martin.MartinMath;

/**
 * T29 client: renderers, the look of the peaceful NPC (×2, the boss texture), the status icons next to his bar and the camera plans
 * by the seconds of docs/specs/tasks/T29_martin_boss.md «Визуал и ролики» (B — Martin, «forward» — his look, P — the arena centre;
 * heights for the ×2 body: chest +2.2, helmet +3.6, the raised blade +5.5; never closer than ~6 blocks to his centre).
 */
public final class MartinClient {
    private MartinClient() {}

    public static void renderers(EntityRenderersEvent.RegisterRenderers e) {
        e.registerEntityRenderer(Martin.TYPE.get(), MartinRenderers.Boss::new);
        e.registerEntityRenderer(Martin.SOLDIER.get(), MartinRenderers.Soldier::new);
        e.registerEntityRenderer(Martin.BANNER.get(), MartinRenderers.Banner::new);
    }

    private static double sine(double k) {
        return BossMath.sine(k);
    }

    /** Client setup: NPC look, HUD, camera plans. */
    public static void setup() {
        BossNpcRenderer.look(Martin.ID, new BossNpcRenderer.Look(MartinRenderers.GEO, MartinRenderers.TEX, MartinRenderers.ANIM, 2f));
        MinecraftForge.EVENT_BUS.register(MartinClient.class);

        // «Появление» 6.5 s
        BossCam.plan("martin.intro", MartinMath.INTRO)
                .shot(0, (k, t, c) -> Shot.of(c.rel(c.b, 16 - 3 * sine(k), 0, 3), c.b.add(0, 1.5, 0)))                    // туман: наезд 16 → 13
                .cut(MartinMath.INTRO_LOOK, (k, t, c) -> Shot.of(c.orbit(c.b, 180 - 25, 9, 4), c.rel(c.b, 6, 0, 2)))        // луч и войско: из-за спины
                .shot(MartinMath.INTRO_RISE, (k, t, c) -> Shot.of(c.rel(c.b, 8, 0, 1 + sine(k)), c.b.add(0, 3.6, 0)))       // встаёт: снизу
                .cut(MartinMath.INTRO_PULL, (k, t, c) -> Shot.of(c.orbit(c.b, -30, 5.5, 2.2), c.b.add(0, 2.6, 0))
                        .shake(t < MartinMath.INTRO_PULL + 5 ? 0.06 : 0))                                                     // меч из земли
                .shot(MartinMath.INTRO_SALUTE, (k, t, c) -> Shot.of(c.rel(c.b, 7 + 4 * sine(k), 0, 2.6), c.b.add(0, 3.0, 0))); // салют и титр

        // «Атака конницы» 4.1 s (focus = P)
        BossCam.plan("martin.cavalry", MartinMath.CAV_SCENE)
                .shot(0, (k, t, c) -> Shot.of(c.orbit(c.b, 30, 6, 0.8), c.b.add(0, 5.5, 0))
                        .shake(t >= MartinMath.CAV_CALL && t < MartinMath.CAV_CALL + 6 ? 0.06 : 0))                         // меч к небу, рог
                .cut(MartinMath.CAV_CHARGE, (k, t, c) -> {                                                                    // общий сверху
                    Vec3 me = Minecraft.getInstance().player != null ? Minecraft.getInstance().player.position() : c.rel(c.focus, 30, 0, 0);
                    Vec3 d = me.subtract(c.focus).multiply(1, 0, 1);
                    d = d.lengthSqr() < 1 ? c.fwd : d.normalize();
                    return Shot.of(c.focus.add(d.scale(30)).add(0, 22, 0), c.focus.add(0, 1, 0));
                });

        // «Приказ стоять насмерть» 2.5 s
        BossCam.plan("martin.hold", MartinMath.HOLD_SCENE)
                .shot(0, (k, t, c) -> Shot.of(c.rel(c.b, 8, 0, 1.6), c.b.add(0, 2.2, 0)))                                  // щит в землю
                .cut(MartinMath.HOLD_WALL, (k, t, c) -> Shot.of(c.orbit(c.b, 150, 9, 3), c.b.add(0, 2, 0)));              // барьер, спина открыта

        // Блок-сдача 5 s (extra = the player whose blow he blocked)
        BossCam.plan("martin.yield", MartinMath.YIELD_CAM)
                .shot(0, (k, t, c) -> {                                                                                       // из-за плеча ударившего
                    Entity v = c.extra;
                    Vec3 shield = c.b.add(0, 2.6, 0);
                    if (v == null) return Shot.of(c.rel(c.b, 7, 0, 2.4), shield);
                    Vec3 vp = v.getPosition(c.pt);
                    Vec3 d = vp.subtract(c.b).multiply(1, 0, 1);
                    d = d.lengthSqr() < 1e-3 ? c.fwd : d.normalize();
                    Vec3 side = new Vec3(-d.z, 0, d.x);
                    double dist = Math.max(6, Math.sqrt(vp.distanceToSqr(c.b.x, vp.y, c.b.z)) + 3);
                    Vec3 pos = c.b.add(d.scale(dist)).add(side.scale(0.9));
                    return Shot.of(new Vec3(pos.x, Math.max(vp.y + v.getEyeHeight() + 0.3, c.b.y + 1.8), pos.z), shield)
                            .shake(t >= MartinMath.YIELD_BLOCK && t < MartinMath.YIELD_BLOCK + 5 ? 0.1 : 0);
                })
                .cut(12, (k, t, c) -> Shot.of(c.orbit(c.b, 25, 7 - sine(k), 2.4), c.b.add(0, 3.6, 0)))                    // опускает оружие, наезд 7 → 6
                .shot(MartinMath.YIELD_SPEAK, (k, t, c) -> Shot.of(c.orbit(c.b, 25, 6, 2.4), c.b.add(0, 3.6, 0)));        // фраза
    }

    // ---------------------------------------------------------------- status icons next to his bar

    private static ResourceLocation icon(String name) {
        return MartinRenderers.rl("textures/gui/martin/status_" + name + ".png");
    }

    /** After the boss bar is drawn (BossBarClient cancels the vanilla row first): icons + labels in a column right of the bar. */
    @SubscribeEvent(priority = EventPriority.LOW, receiveCanceled = true)
    public static void onBar(CustomizeGuiOverlayEvent.BossEventProgress e) {
        var level = Minecraft.getInstance().level;
        if (level == null) return;
        UUID id = e.getBossEvent().getId();
        MartinEntity m = null;
        for (Entity en : level.entitiesForRendering())
            if (en instanceof MartinEntity me && me.getUUID().equals(id)) {
                m = me;
                break;
            }
        if (m == null) return;
        int flags = BossClient.look(m.getId());
        if ((flags & ~0xFF) == 0 || e.getIncrement() == 0) return;   // no statuses, or BossBarClient hid the bar (intro)
        GuiGraphics g = e.getGuiGraphics();
        Font font = Minecraft.getInstance().font;
        int x = (g.guiWidth() + BossMath.BAR_W) / 2 + 4, y = e.getY() - 1;
        RenderSystem.enableBlend();
        for (int i = 0; i < Martin.STATUS_BITS.length; i++) {
            if ((flags & Martin.STATUS_BITS[i]) == 0) continue;
            String n = Martin.STATUS_NAMES[i];
            g.blit(icon(n), x, y, 0, 0, 18, 18, 18, 18);
            Component label = Component.translatable("ui.pohsmp_core.martin.status." + n);
            g.pose().pushPose();
            g.pose().translate(x + 20, y + 6, 0);
            g.pose().scale(0.75f, 0.75f, 1);
            g.drawString(font, label, 0, 0, Martin.COLOR, true);
            g.pose().popPose();
            y += 19;
        }
        RenderSystem.disableBlend();
    }
}
