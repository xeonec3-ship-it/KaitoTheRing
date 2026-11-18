package ru.pohsmp.core.client;

import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.player.LocalPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraftforge.client.event.RenderGuiEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.Reg;

/** Screen overlays: red veil of Magic Madness, white flash of big explosions. */
public final class PohHud {
    private PohHud() {}

    private static int flashLeft, flashTotal, flashColor;

    public static void flash(int ticks, int rgb) {
        if (ticks > flashLeft) {
            flashLeft = ticks;
            flashTotal = ticks;
            flashColor = rgb;
        }
    }

    @SubscribeEvent
    public static void onClientTick(TickEvent.ClientTickEvent e) {
        if (e.phase != TickEvent.Phase.END) return;
        if (flashLeft > 0) flashLeft--;
        LocalPlayer p = Minecraft.getInstance().player;
        if (p != null && p.tickCount % 16 == 0 && p.hasEffect(Reg.MADNESS.get()))
            p.playSound(SoundEvents.WARDEN_HEARTBEAT, 0.6f, 1.1f);
    }

    @SubscribeEvent
    public static void onRender(RenderGuiEvent.Post e) {
        Minecraft mc = Minecraft.getInstance();
        if (mc.player == null) return;
        GuiGraphics g = e.getGuiGraphics();
        int w = g.guiWidth(), h = g.guiHeight();
        if (mc.player.hasEffect(Reg.MADNESS.get())) {
            double t = (mc.player.tickCount + e.getPartialTick()) / 16.0 * Math.PI * 2;
            float pulse = 0.55f + 0.25f * (float) Math.pow(Math.max(0, Math.sin(t)), 6);
            int edge = (int) (pulse * 255) << 24 | 0x8A0010;
            int clear = 0x008A0010;
            int bw = w / 4, bh = h / 4;
            g.fillGradient(0, 0, w, bh, edge, clear);
            g.fillGradient(0, h - bh, w, h, clear, edge);
            sideGradient(g, 0, 0, bw, h, edge, clear);
            sideGradient(g, w - bw, 0, w, h, clear, edge);
            g.fill(0, 0, w, h, ((int) (pulse * 60) << 24) | 0x5A0008);
        }
        if (flashLeft > 0) {
            float a = flashLeft / (float) Math.max(1, flashTotal);
            g.fill(0, 0, w, h, ((int) (a * a * 235) << 24) | (flashColor & 0xFFFFFF));
        }
    }

    /** Horizontal gradient made of thin vertical strips (GuiGraphics only has vertical gradients). */
    private static void sideGradient(GuiGraphics g, int x0, int y0, int x1, int y1, int left, int right) {
        int n = Math.max(1, (x1 - x0) / 2);
        for (int i = 0; i < n; i++) {
            float k = i / (float) n;
            int a = (int) (((left >>> 24) & 255) * (1 - k) + ((right >>> 24) & 255) * k);
            int xa = x0 + (x1 - x0) * i / n, xb = x0 + (x1 - x0) * (i + 1) / n;
            g.fill(xa, y0, xb, y1, (a << 24) | (left & 0xFFFFFF));
        }
    }
}
