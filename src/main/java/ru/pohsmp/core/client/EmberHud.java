package ru.pohsmp.core.client;

import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.renderer.item.ItemProperties;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.ItemStack;
import net.minecraftforge.client.event.RenderGuiEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.event.lifecycle.FMLClientSetupEvent;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.ember.EmberBlade;

/**
 * T14, client: the heat gauge — a bent bar of "embers" over the hotbar, only while the blade is in hand; dark red to bright
 * orange, pulses when full (special attack ready). Temporary drawing in rectangles until the manager's HUD texture.
 * Also the item property pohsmp_core:hot (whip form model).
 */
public final class EmberHud {
    private EmberHud() {}

    private static final int SEG = 30, SEG_W = 4, GAP = 1;

    public static void setup(FMLClientSetupEvent e) {
        e.enqueueWork(() -> ItemProperties.register(Reg.EMBER_BLADE.get(), new ResourceLocation(PohCore.MODID, "hot"),
                (s, level, holder, seed) -> EmberBlade.hot(s) ? 1f : 0f));
    }

    @SubscribeEvent
    public static void onRender(RenderGuiEvent.Post e) {
        Minecraft mc = Minecraft.getInstance();
        if (mc.player == null || mc.options.hideGui) return;
        ItemStack s = mc.player.getMainHandItem();
        if (!(s.getItem() instanceof EmberBlade)) return;
        GuiGraphics g = e.getGuiGraphics();
        int w = g.guiWidth(), h = g.guiHeight();
        float heat = EmberBlade.heat(s) / EmberBlade.MAX_HEAT;
        boolean full = heat >= 1f;
        double t = (mc.player.tickCount + e.getPartialTick()) / 10.0;
        float pulse = full ? 0.75f + 0.25f * (float) Math.sin(t * Math.PI) : 1f;
        int total = SEG * (SEG_W + GAP) - GAP, x0 = w / 2 - total / 2, base = mc.player.isCreative() ? h - 32 : h - 60;   // over the hotbar; in survival over hearts and armor
        int lit = (int) Math.ceil(heat * SEG - 1e-4);
        for (int i = 0; i < SEG; i++) {
            double u = (i + 0.5) / SEG * 2 - 1;   // -1..1 across the bar
            int y = base + (int) Math.round(u * u * 5);   // bent like a smile over the hotbar
            int x = x0 + i * (SEG_W + GAP);
            g.fill(x - 1, y - 1, x + SEG_W + 1, y + 4, 0xAA120806);
            if (i < lit) {
                float k = (float) i / (SEG - 1);
                int col = lerp(0x5A0E08, 0xFF9A2A, k);
                g.fill(x, y, x + SEG_W, y + 3, 0xFF000000 | dim(col, pulse));
                g.fill(x, y, x + SEG_W, y + 1, 0xFF000000 | dim(lerp(col, 0xFFE7A0, 0.45f), pulse));
            }
        }
        if (EmberBlade.hot(s))   // a small flame mark at the right end: whip form
            g.fill(x0 + total + 3, base + 2, x0 + total + 6, base + 6, 0xFFFF6A1A);
    }

    private static int lerp(int a, int b, float k) {
        int r = (int) (((a >> 16) & 255) + (((b >> 16) & 255) - ((a >> 16) & 255)) * k);
        int gg = (int) (((a >> 8) & 255) + (((b >> 8) & 255) - ((a >> 8) & 255)) * k);
        int bb = (int) ((a & 255) + ((b & 255) - (a & 255)) * k);
        return (r << 16) | (gg << 8) | bb;
    }

    private static int dim(int c, float k) {
        return ((int) (((c >> 16) & 255) * k) << 16) | ((int) (((c >> 8) & 255) * k) << 8) | (int) ((c & 255) * k);
    }
}
