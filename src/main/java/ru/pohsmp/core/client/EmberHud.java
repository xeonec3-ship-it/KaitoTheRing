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
 * T14, client: the heat gauge over the hotbar (the manager's texture), only while the blade is in hand; pulses when full
 * (special attack ready).
 * Also the item property pohsmp_core:hot (whip form model).
 */
public final class EmberHud {
    private EmberHud() {}

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
        float heat = Math.min(1f, EmberBlade.heat(s) / EmberBlade.MAX_HEAT);
        double t = (mc.player.tickCount + e.getPartialTick()) / 10.0;
        float alpha = heat >= 1f ? 0.65f + 0.35f * (float) Math.sin(t * Math.PI) : 1f;   // full: the fill pulses (special attack ready)
        int x0 = w / 2 - BAR_W / 2, y = mc.player.isCreative() ? h - 40 : h - 76;   // over the hotbar; in survival over hearts and armor
        int fill = Math.round(heat * BAR_W);
        com.mojang.blaze3d.systems.RenderSystem.enableBlend();
        if (fill > 0) {   // bottom half of the texture: the fill, left to right by the heat share
            g.setColor(1f, 1f, 1f, alpha);
            g.blit(BAR, x0, y, 0, BAR_H, fill, BAR_H, BAR_W, BAR_H * 2);
            g.setColor(1f, 1f, 1f, 1f);
        }
        g.blit(BAR, x0, y, 0, 0, BAR_W, BAR_H, BAR_W, BAR_H * 2);   // top half: the frame
        com.mojang.blaze3d.systems.RenderSystem.disableBlend();
        if (EmberBlade.hot(s))   // a small flame mark at the right end: whip form
            g.fill(x0 + BAR_W + 3, y + 6, x0 + BAR_W + 6, y + 10, 0xFFFF6A1A);
    }

    /** textures/gui/ember_heat_bar.png (manager): 128x32, top 16 rows the frame, bottom 16 the fill. */
    private static final ResourceLocation BAR = new ResourceLocation(PohCore.MODID, "textures/gui/ember_heat_bar.png");
    private static final int BAR_W = 128, BAR_H = 16;

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
