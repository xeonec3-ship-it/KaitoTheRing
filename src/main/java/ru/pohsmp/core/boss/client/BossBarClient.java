package ru.pohsmp.core.boss.client;

import com.mojang.blaze3d.systems.RenderSystem;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.Font;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraftforge.client.event.CustomizeGuiOverlayEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.boss.BossDef;
import ru.pohsmp.core.boss.BossMath;
import ru.pohsmp.core.boss.BossNet;

/**
 * The cult bosses' bar, by phase, drawn instead of the vanilla boss bar row of that boss (the server keeps its ExtendedServerBossEvent /
 * ServerBossEvent for progress and name; this cancels Iron's BossbarManager too by running first). Layout as Iron's
 * BossbarManager.renderCustomBossbar: x = (w − 192)/2, y = event y − 1, empty half v = 0, full half v = 18 width 3 + progress·186;
 * FRAMES overlays (flames, threads, heat: 8 × 192×14) before the bar at y − 5; PULSE overlays (_p2_pulse) over it while the boss's
 * pulse flag is on; 6 ticks of _flash on a phase change; the epithet (ui.pohsmp_core.<boss>.epithet) small under the bar.
 */
public final class BossBarClient {
    private BossBarClient() {}

    private static final class Bar {
        String bossId;
        int phase;
        boolean visible, pulse;
        long flashAt = Long.MIN_VALUE;
    }

    private static final Map<UUID, Bar> BARS = new HashMap<>();

    static void onMsg(BossNet.Msg m) {
        if (m.kind == BossNet.BAR_STOP) {
            BARS.remove(m.u);
            return;
        }
        Bar b = BARS.computeIfAbsent(m.u, k -> new Bar());
        b.bossId = m.s1;
        b.visible = (m.b & BossNet.BAR_VISIBLE) != 0;
        b.pulse = (m.b & BossNet.BAR_PULSE) != 0;
        if ((m.b & BossNet.BAR_FLASH) != 0 && m.a != b.phase) b.flashAt = now();
        b.phase = m.a;
    }

    static void clear() {
        BARS.clear();
    }

    private static long now() {
        var lvl = Minecraft.getInstance().level;
        return lvl == null ? 0 : ru.pohsmp.core.client.ClientClock.ticks();
    }

    private static ResourceLocation tex(String sprite) {
        return new ResourceLocation(PohCore.MODID, "textures/gui/sprites/boss_bars/" + sprite + ".png");
    }

    @SubscribeEvent(priority = EventPriority.HIGH)
    public static void onBar(CustomizeGuiOverlayEvent.BossEventProgress e) {
        Bar b = BARS.get(e.getBossEvent().getId());
        if (b == null) return;
        e.setCanceled(true);
        // this event fires only for a row the server boss event made (BossCore / FireBossEntity), so inRow and the message are known here
        if (!ru.pohsmp.core.boss.BossBarRow.drawn(true, true, b.visible, BossCam.hidesBars())) {   // the intro: the bar comes at its end
            e.setIncrement(0);
            return;
        }
        BossDef def = BossDef.BossDefs.get(b.bossId);
        if (def == null) return;
        GuiGraphics g = e.getGuiGraphics();
        Font font = Minecraft.getInstance().font;
        int x = (g.guiWidth() - BossMath.BAR_W) / 2, y = e.getY() - 1;
        float pt = Minecraft.getInstance().getFrameTime();
        double t = now() + pt;
        BossDef.BarPhase ph = def.barPhase(b.phase);
        float progress = e.getBossEvent().getProgress();
        int fill = BossMath.fillWidth(progress);

        RenderSystem.enableBlend();
        if (ph.overlay() == BossDef.Overlay.FRAMES) {
            int fr = BossMath.overlayFrame(now());
            g.blit(tex(ph.overlaySprite()), x, y + BossMath.BAR_H / 2 - BossMath.FRAME_H, 0, fr * BossMath.FRAME_H, BossMath.BAR_W, BossMath.FRAME_H,
                    BossMath.BAR_W, BossMath.FRAME_H * BossMath.FRAMES);
        }
        ResourceLocation bar = tex(ph.sprite());
        g.blit(bar, x, y, 0, 0, BossMath.BAR_W, BossMath.BAR_H, BossMath.BAR_W, BossMath.BAR_H * 2);
        g.blit(bar, x, y, 0, BossMath.BAR_H, fill, BossMath.BAR_H, BossMath.BAR_W, BossMath.BAR_H * 2);
        if (ph.overlay() == BossDef.Overlay.PULSE && b.pulse) {
            ResourceLocation pulse = tex(ph.overlaySprite());
            g.setColor(1, 1, 1, BossMath.pulseAlpha(t));
            g.blit(pulse, x, y, 0, 0, BossMath.BAR_W, BossMath.BAR_H, BossMath.BAR_W, BossMath.BAR_H * 2);
            g.blit(pulse, x, y, 0, BossMath.BAR_H, fill, BossMath.BAR_H, BossMath.BAR_W, BossMath.BAR_H * 2);
            g.setColor(1, 1, 1, 1);
        }
        float flash = BossMath.flashAlpha(t - b.flashAt);
        if (flash > 0) {
            g.setColor(1, 1, 1, flash);
            g.blit(tex(def.id + "_bossbar_flash"), x, y, 0, 0, BossMath.BAR_W, BossMath.BAR_H, BossMath.BAR_W, BossMath.BAR_H);
            g.setColor(1, 1, 1, 1);
        }
        RenderSystem.disableBlend();

        Component name = e.getBossEvent().getName();
        g.drawString(font, name, g.guiWidth() / 2 - font.width(name) / 2, y - 8, 0xFFFFFF);
        Component epithet = Component.translatable(def.epithetKey());
        g.pose().pushPose();
        g.pose().translate(g.guiWidth() / 2f, y + BossMath.BAR_H + 1, 0);
        g.pose().scale(0.75f, 0.75f, 1);
        g.drawString(font, epithet, -font.width(epithet) / 2, 0, def.color, true);
        g.pose().popPose();
        e.setIncrement(BossMath.BAR_H + 9 + 8);
    }
}
