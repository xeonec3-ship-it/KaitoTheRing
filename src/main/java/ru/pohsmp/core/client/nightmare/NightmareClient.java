package ru.pohsmp.core.client.nightmare;

import com.mojang.blaze3d.platform.GlStateManager;
import com.mojang.blaze3d.systems.RenderSystem;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.resources.sounds.SimpleSoundInstance;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.sounds.SoundEvents;
import net.minecraftforge.client.event.RenderGuiEvent;
import net.minecraftforge.client.event.ViewportEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.level.LevelEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;

/**
 * T25 «Погружение» on the victim's own client (nobody else sees any of it). The base the helper's visuals sit on:
 * stage 1 - the light dims and flickers now and then, the fog comes closer, the screen's edges darken, a heartbeat;
 * stage 2 - all of it stronger, the heart faster; stage 3 - the air and fog blood-black, the heart pounding.
 * «Ночь без рассвета» (night > 0): the client's day time is held at midnight (the real one comes back after).
 */
public final class NightmareClient {
    private NightmareClient() {}

    private static final ResourceLocation VIGNETTE = new ResourceLocation("minecraft", "textures/misc/vignette.png");
    private static int stage, age, flicker, nextFlicker = 100, nextBeat = 40, nextVoice = 200, nightLeft;
    /** smooth 0..3 following the stage; 0..1 for the night */
    private static float level, night;
    private static long realTime = Long.MIN_VALUE, lastSet = Long.MIN_VALUE;

    public static int stage() {
        return stage;
    }

    public static float level() {
        return level;
    }

    public static void set(int st, int ticks) {
        stage = Math.max(0, Math.min(3, st));
    }

    /** 0..1: «Ночь без рассвета» on this client now */
    public static float night() {
        return night;
    }

    public static void night(int ticks) {
        nightLeft = Math.max(0, ticks);
    }

    public static void clear() {
        stage = 0;
        level = 0;
        night = 0;
        nightLeft = 0;
        moths = 0;
        inkLeft = 0;
        realTime = Long.MIN_VALUE;
    }

    @SubscribeEvent
    public static void onTick(TickEvent.ClientTickEvent e) {
        Minecraft mc = Minecraft.getInstance();
        if (mc.level == null || mc.isPaused()) return;
        if (e.phase == TickEvent.Phase.START) {
            if (night > 0 || nightLeft > 0) {   // the server's time packets move the real time on: keep it, show midnight
                long now = mc.level.getDayTime();
                if (realTime == Long.MIN_VALUE || (now != lastSet && now != lastSet + 1)) realTime = now;
                else realTime += now - lastSet;
                if (nightLeft == 0 && night <= 0.05f) {
                    mc.level.setDayTime(realTime);
                    realTime = Long.MIN_VALUE;
                    night = 0;
                } else {
                    lastSet = realTime - Math.floorMod(realTime, 24000L) + 18000L;
                    mc.level.setDayTime(lastSet);
                }
            }
            return;
        }
        age++;
        mothsTick(mc);
        if (inkLeft > 0) inkLeft--;
        if (nightLeft > 0) nightLeft--;
        night = nightLeft > 0 ? Math.min(1, night + 0.05f) : Math.max(0, night - 0.05f);
        level += Math.signum(stage - level) * Math.min(Math.abs(stage - level), 0.04f);
        if (level <= 0.01f) return;
        if (flicker > 0) flicker--;
        else if (--nextFlicker <= 0) {   // the light falters
            flicker = 3 + mc.level.random.nextInt(6);
            nextFlicker = (int) (40 + mc.level.random.nextInt(160) / Math.max(1, level));
        }
        if (--nextBeat <= 0 && mc.player != null) {
            float v = Math.min(1f, 0.45f + 0.18f * level);   // the approved sound is ~2 s long: one beat at a time
            mc.getSoundManager().play(SimpleSoundInstance.forUI(ru.pohsmp.core.nightmare.NmSounds.HEARTBEAT, 0.95f + 0.05f * level, v));
            nextBeat = Math.max(44, 90 - Math.round(level * 15));
        }
        if (--nextVoice <= 0 && mc.player != null) {   // whispers around the victim; from stage 2 scrapes and a far child's laugh
            var r = mc.level.random;
            var s = level >= 1.5f && r.nextInt(3) == 0 ? (r.nextBoolean() ? ru.pohsmp.core.nightmare.NmSounds.SCRAPE
                    : ru.pohsmp.core.nightmare.NmSounds.CHILD_LAUGH) : ru.pohsmp.core.nightmare.NmSounds.WHISPER;
            double a = r.nextDouble() * Math.PI * 2, d = 3 + r.nextDouble() * 5;
            var p = mc.player.position();
            mc.getSoundManager().play(new SimpleSoundInstance(s, net.minecraft.sounds.SoundSource.AMBIENT, Math.min(1f, 0.4f + 0.2f * level), 1f,
                    r, p.x + Math.cos(a) * d, p.y + 1, p.z + Math.sin(a) * d));
            nextVoice = (int) (300 + r.nextInt(400) / Math.max(1, level));
        }
    }

    private static float dark() {
        return Math.min(1, level / 3f);
    }

    @SubscribeEvent(priority = EventPriority.LOW)
    public static void onFogColor(ViewportEvent.ComputeFogColor e) {
        if (level <= 0.01f && night <= 0) return;
        float d = dark();
        float k = 1 - 0.55f * d - (flicker > 0 ? 0.25f : 0);
        float r = e.getRed() * k, g = e.getGreen() * k, b = e.getBlue() * k;
        float blood = Math.max(0, level - 2);   // stage 3: blood-black
        r = r * (1 - blood) + 0.16f * blood;
        g = g * (1 - blood) + 0.02f * blood;
        b = b * (1 - blood) + 0.05f * blood;
        if (night > 0) {   // the red moon's air
            r = Math.min(1, r + 0.05f * night);
            g *= 1 - 0.3f * night;
            b *= 1 - 0.2f * night;
        }
        e.setRed(r);
        e.setGreen(g);
        e.setBlue(b);
    }

    @SubscribeEvent(priority = EventPriority.LOW)
    public static void onFog(ViewportEvent.RenderFog e) {
        if (level <= 0.01f) return;
        float k = 1 - 0.18f * level - (flicker > 0 ? 0.1f : 0);
        float far = Math.max(14f, e.getFarPlaneDistance() * k);
        if (far >= e.getFarPlaneDistance()) return;
        e.setFarPlaneDistance(far);
        e.setNearPlaneDistance(Math.min(e.getNearPlaneDistance(), far * 0.4f));
        e.setCanceled(true);
    }

    @SubscribeEvent(priority = EventPriority.LOW)
    public static void onGui(RenderGuiEvent.Post e) {
        if (level <= 0.01f && moths <= 0.01f && inkLeft <= 0) return;
        GuiGraphics g = e.getGuiGraphics();
        int w = g.guiWidth(), h = g.guiHeight();
        double t = age + e.getPartialTick();
        float pulse = (float) (0.5 + 0.5 * Math.sin(t / Math.max(2.0, 6.5 - level)));
        float a = Math.min(1, 0.35f + 0.2f * level + 0.1f * pulse * level);
        RenderSystem.enableBlend();
        RenderSystem.blendFuncSeparate(GlStateManager.SourceFactor.ZERO, GlStateManager.DestFactor.ONE_MINUS_SRC_COLOR,
                GlStateManager.SourceFactor.ONE, GlStateManager.DestFactor.ZERO);
        RenderSystem.setShaderColor(a, a * (1 - 0.15f * Math.max(0, level - 1)), a * (1 - 0.1f * Math.max(0, level - 1)), 1);
        g.blit(VIGNETTE, 0, 0, 0, 0, w, h, w, h);
        if (level > 1.5f) g.blit(VIGNETTE, 0, 0, 0, 0, w, h, w, h);
        RenderSystem.setShaderColor(1, 1, 1, 1);
        RenderSystem.defaultBlendFunc();
        RenderSystem.disableBlend();
        RenderSystem.enableBlend();
        RenderSystem.defaultBlendFunc();
        for (int s = 1; s <= 3; s++) {   // the helper's stage overlays: each fades in as the stage comes, over the one before
            float k = Math.max(0, Math.min(1, level - (s - 1)));
            if (k <= 0.01f) break;
            RenderSystem.setShaderColor(1, 1, 1, k * (s == 3 ? 0.85f + 0.15f * pulse : 1f));
            g.blit(STAGE[s - 1], 0, 0, 0, 0, w, h, w, h);
        }
        if (moths > 0.01f) {
            RenderSystem.setShaderColor(1, 1, 1, moths);
            g.blit(MOTHS, 0, 0, 0, 0, w, h, w, h);
        }
        if (inkLeft > 0) {
            float k = Math.min(1, Math.min(inkLeft, inkLen - inkLeft + 1) / 8f);
            RenderSystem.setShaderColor(1, 1, 1, k);
            g.blit(INK, 0, 0, 0, 0, w, h, w, h);
        }
        RenderSystem.setShaderColor(1, 1, 1, 1);
        RenderSystem.disableBlend();
        if (flicker > 0) g.fill(0, 0, w, h, (int) (60 + 30 * level) << 24);
    }

    private static final ResourceLocation[] STAGE = {fx("nightmare_stage1"), fx("nightmare_stage2"), fx("nightmare_stage3")};
    private static final ResourceLocation MOTHS = fx("nightmare_moths_screen"), INK = fx("nightmare_ink_screen");
    /** 0..1: the swarm at the face (a moth of ours within reach of the eyes) */
    private static float moths;
    private static int inkLeft, inkLen;

    private static ResourceLocation fx(String n) {
        return new ResourceLocation(ru.pohsmp.core.PohCore.MODID, "textures/fx/" + n + ".png");
    }

    /** Ink running down the screen for a while (the Mythic's thickening, the cast). */
    public static void ink(int ticks) {
        inkLeft = inkLen = Math.max(1, ticks);
    }

    private static void mothsTick(Minecraft mc) {
        boolean near = false;
        if (mc.player != null)
            for (var m : mc.level.getEntitiesOfClass(ru.pohsmp.core.nightmare.NightmareMob.class, mc.player.getBoundingBox().inflate(2.5)))
                if (m.kind == ru.pohsmp.core.nightmare.NightmareMob.Kind.MOTH && !m.going()) near = true;
        moths = near ? Math.min(1, moths + 0.1f) : Math.max(0, moths - 0.05f);
    }

    @SubscribeEvent
    public static void onUnload(LevelEvent.Unload e) {
        if (e.getLevel().isClientSide()) clear();
    }
}
