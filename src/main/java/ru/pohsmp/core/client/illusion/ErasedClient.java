package ru.pohsmp.core.client.illusion;

import com.mojang.blaze3d.systems.RenderSystem;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.resources.sounds.SimpleSoundInstance;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.sounds.SoundEvents;
import net.minecraftforge.client.event.RenderGuiEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.level.LevelEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.PohCore;

/**
 * T24: the screen of the erased player - a pale vignette breathing at the edges and faded letters creeping across it, a dull far hum.
 * IlluMsg.ERASED ticks > 0 turns it on for that long, 0 turns it off. Nothing else of the world changes on this client.
 */
public final class ErasedClient {
    private ErasedClient() {}

    private static final ResourceLocation VIGNETTE = new ResourceLocation(PohCore.MODID, "textures/gui/overlay/erased_vignette.png");
    private static final ResourceLocation LETTERS = new ResourceLocation(PohCore.MODID, "textures/gui/overlay/erased_letters.png");

    private static int left, age;
    private static float fade;

    public static void set(int ticks) {
        left = Math.max(0, ticks);
        if (left > 0 && fade <= 0) age = 0;
    }

    public static void clear() {
        left = 0;
        fade = 0;
        desaturate(Minecraft.getInstance(), false);
    }

    private static final ResourceLocation GREY = new ResourceLocation(PohCore.MODID, "shaders/post/erased.json");
    private static boolean grey;

    /** The world a quarter paler (vanilla color_convolve, saturation 0.75) while erased; another post effect taking over is left alone. */
    private static void desaturate(Minecraft mc, boolean on) {
        if (on == grey) return;
        var gr = mc.gameRenderer;
        if (on) {
            if (gr.currentEffect() != null) return;   // the game's own (a spectated creeper...) - leave it
            gr.loadEffect(GREY);
            grey = true;
        } else {
            if (gr.currentEffect() != null && GREY.toString().equals(gr.currentEffect().getName())) gr.shutdownEffect();
            grey = false;
        }
    }

    @SubscribeEvent
    public static void onTick(TickEvent.ClientTickEvent e) {
        if (e.phase != TickEvent.Phase.END) return;
        Minecraft mc = Minecraft.getInstance();
        if (mc.isPaused()) return;
        desaturate(mc, left > 0);
        if (left > 0) {
            left--;
            age++;
            fade = Math.min(1, fade + 0.05f);
            if (mc.player != null && age % 160 == 1)
                mc.getSoundManager().play(SimpleSoundInstance.forUI(SoundEvents.AMBIENT_BASALT_DELTAS_LOOP.get(), 0.5f, 0.12f));
        } else if (fade > 0) {
            age++;
            fade = Math.max(0, fade - 0.05f);
        }
    }

    @SubscribeEvent
    public static void onGui(RenderGuiEvent.Post e) {
        if (fade <= 0) return;
        GuiGraphics g = e.getGuiGraphics();
        int w = g.guiWidth(), h = g.guiHeight();
        float t = age + e.getPartialTick();
        RenderSystem.enableBlend();
        RenderSystem.defaultBlendFunc();
        RenderSystem.setShaderColor(1, 1, 1, fade * (0.85f + 0.1f * (float) Math.sin(t / 40f)));
        g.blit(VIGNETTE, 0, 0, w, h, 0, 0, 256, 256, 256, 256);
        RenderSystem.setShaderColor(1, 1, 1, fade * 0.5f);
        int off = (int) (t * 0.0015f * 256) % 256;
        g.blit(LETTERS, 0, 0, w, h, off, 0, 256, 256, 256, 256);
        RenderSystem.setShaderColor(1, 1, 1, 1);
        RenderSystem.disableBlend();
    }

    @SubscribeEvent
    public static void onUnload(LevelEvent.Unload e) {
        if (e.getLevel().isClientSide()) clear();
    }
}
