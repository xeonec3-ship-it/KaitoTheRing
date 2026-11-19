package ru.pohsmp.core.client.mythic;

import com.mojang.blaze3d.platform.GlStateManager;
import com.mojang.blaze3d.systems.RenderSystem;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.resources.ResourceLocation;
import net.minecraftforge.client.event.RenderGuiEvent;
import net.minecraftforge.client.event.ViewportEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.level.LevelEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.net.IlluMsg;

/**
 * T23, what only this client sees of the Mythic skies. «Око бездны» (SKY_DREAD, while the Eye can see you): the screen's edges darken,
 * the view and the interface sway a little. «Последний рассвет» (SKY_DAWN): day light even at night (the client's day time is held at
 * noon, the real one comes back after), a warm tone of the air.
 */
public final class SkyClient {
    private SkyClient() {}

    private static final ResourceLocation VIGNETTE = new ResourceLocation("minecraft", "textures/misc/vignette.png");
    private static int dreadLeft, dawnLeft, age;
    private static float dread, dawn;
    private static long realTime = Long.MIN_VALUE, lastSet = Long.MIN_VALUE;
    private static boolean pushed;

    public static void set(int kind, int ticks) {
        if (kind == IlluMsg.SKY_DREAD) dreadLeft = Math.max(0, ticks);
        else if (kind == IlluMsg.SKY_DAWN) dawnLeft = Math.max(0, ticks);
    }

    public static void clear() {
        dreadLeft = dawnLeft = 0;
        dread = dawn = 0;
        realTime = Long.MIN_VALUE;
    }

    @SubscribeEvent
    public static void onTick(TickEvent.ClientTickEvent e) {
        Minecraft mc = Minecraft.getInstance();
        if (mc.level == null || mc.isPaused()) return;
        if (e.phase == TickEvent.Phase.START) {
            if (dawn > 0 || dawnLeft > 0) {   // the server's time packets move the real time on: keep it, show noon
                long now = mc.level.getDayTime();
                if (realTime == Long.MIN_VALUE || (now != lastSet && now != lastSet + 1)) realTime = now;   // first tick or a time packet
                else realTime += now - lastSet;
                if (dawnLeft == 0 && dawn <= 0.05f) {
                    mc.level.setDayTime(realTime);
                    realTime = Long.MIN_VALUE;
                    dawn = 0;
                } else {
                    lastSet = noon(realTime);
                    mc.level.setDayTime(lastSet);
                }
            }
            return;
        }
        age++;
        if (dreadLeft > 0) dreadLeft--;
        if (dawnLeft > 0) dawnLeft--;
        dread = dreadLeft > 0 ? Math.min(1, dread + 0.08f) : Math.max(0, dread - 0.05f);
        dawn = dawnLeft > 0 ? Math.min(1, dawn + 0.05f) : Math.max(0, dawn - 0.05f);
    }

    /** Noon of the same day: the sun stands high, the moon's phase stays. */
    private static long noon(long time) {
        return time - Math.floorMod(time, 24000L) + 6000L;
    }

    @SubscribeEvent
    public static void onAngles(ViewportEvent.ComputeCameraAngles e) {
        if (dread <= 0) return;
        double t = age + e.getPartialTick();
        e.setRoll(e.getRoll() + (float) (Math.sin(t / 13.0) * 2.5 * dread));
        e.setPitch(e.getPitch() + (float) (Math.sin(t / 21.0) * 0.8 * dread));
    }

    @SubscribeEvent
    public static void onFov(ViewportEvent.ComputeFov e) {
        if (dread <= 0) return;
        double t = age + e.getPartialTick();
        e.setFOV(e.getFOV() + Math.sin(t / 17.0) * 3 * dread);
    }

    @SubscribeEvent
    public static void onFog(ViewportEvent.ComputeFogColor e) {
        if (dawn > 0) {
            e.setRed(Math.min(1, e.getRed() + 0.12f * dawn));
            e.setGreen(Math.min(1, e.getGreen() + 0.05f * dawn));
            e.setBlue(e.getBlue() * (1 - 0.15f * dawn));
        }
        if (dread > 0) {
            float k = 1 - 0.45f * dread;
            e.setRed(e.getRed() * k);
            e.setGreen(e.getGreen() * k);
            e.setBlue(e.getBlue() * (1 - 0.3f * dread));
        }
    }

    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void onGuiPre(RenderGuiEvent.Pre e) {
        if (dread <= 0) return;
        double t = age + e.getPartialTick();
        e.getGuiGraphics().pose().pushPose();
        e.getGuiGraphics().pose().translate(Math.sin(t / 11.0) * 1.5 * dread, Math.sin(t / 15.0) * 1.0 * dread, 0);
        pushed = true;
    }

    @SubscribeEvent(priority = EventPriority.LOWEST)
    public static void onGuiPost(RenderGuiEvent.Post e) {
        GuiGraphics g = e.getGuiGraphics();
        if (pushed) {
            g.pose().popPose();
            pushed = false;
        }
        if (dread <= 0) return;
        float a = 0.85f * dread;
        RenderSystem.enableBlend();
        RenderSystem.blendFuncSeparate(GlStateManager.SourceFactor.ZERO, GlStateManager.DestFactor.ONE_MINUS_SRC_COLOR,
                GlStateManager.SourceFactor.ONE, GlStateManager.DestFactor.ZERO);
        RenderSystem.setShaderColor(a, a, a, 1);
        g.blit(VIGNETTE, 0, 0, 0, 0, g.guiWidth(), g.guiHeight(), g.guiWidth(), g.guiHeight());
        g.blit(VIGNETTE, 0, 0, 0, 0, g.guiWidth(), g.guiHeight(), g.guiWidth(), g.guiHeight());
        RenderSystem.setShaderColor(1, 1, 1, 1);
        RenderSystem.defaultBlendFunc();
        RenderSystem.disableBlend();
    }

    @SubscribeEvent
    public static void onUnload(LevelEvent.Unload e) {
        if (e.getLevel().isClientSide()) clear();
    }
}
