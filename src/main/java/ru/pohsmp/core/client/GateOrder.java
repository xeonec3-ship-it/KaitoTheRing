package ru.pohsmp.core.client;

import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.player.Player;
import net.minecraftforge.client.event.InputEvent;
import net.minecraftforge.client.event.RenderGuiEvent;
import net.minecraftforge.event.level.LevelEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.net.Net;
import ru.pohsmp.core.spell.silent.SilentGateSpell;

/**
 * «Безмолвные врата», «Приказ» (owner 19.11), client of every watcher. Phases come from the server (HFx.ANIM with the scene key):
 * WAIT — the wait music loop, the camera before the witch; the caster's own client shows the hint and turns his left click into the
 * command (the attack / block breaking is cancelled). COMMAND — the strike music, the hand-down animation, the strike camera timed from
 * here. STRIKE — the strike animation of the caster.
 */
public final class GateOrder {
    private GateOrder() {}

    private static int key = Integer.MIN_VALUE, caster = -1;
    /** Game time the wait / the command began on this client; -1 before. */
    private static long waitAt = -1, commandAt = -1;
    /** The local player is the waiting caster and has not clicked yet. */
    private static boolean mine;

    public static void handle(int k, int casterId, int code, long now) {
        Minecraft mc = Minecraft.getInstance();
        if (code == SilentGateSpell.ANIM_WAIT) {
            key = k;
            caster = casterId;
            waitAt = now;
            commandAt = -1;
            mine = mc.player != null && mc.player.getId() == casterId;
            SilentMusic.switchTo(k, Reg.MUSIC_GATE_WAIT.get(), true);
        } else if (code == SilentGateSpell.ANIM_COMMAND) {
            key = k;
            caster = casterId;
            if (waitAt < 0) waitAt = now;
            commandAt = now;
            mine = false;
            SilentMusic.switchTo(k, Reg.MUSIC_GATE_STRIKE.get(), false);
            animate(casterId, "pohsmp_silent_gate_command");
        } else if (code == SilentGateSpell.ANIM_STRIKE) {
            animate(casterId, "pohsmp_silent_gate_finish");
        }
    }

    private static void animate(int id, String anim) {
        Minecraft mc = Minecraft.getInstance();
        if (mc.level != null && mc.level.getEntity(id) instanceof Player p)
            io.redspace.ironsspellbooks.player.ClientSpellCastHelper.animatePlayerStart(p, new ResourceLocation("irons_spellbooks", anim));
    }

    /** Scene STOP. */
    public static void stop(int k) {
        if (k != key) return;
        key = Integer.MIN_VALUE;
        waitAt = commandAt = -1;
        mine = false;
    }

    /**
     * Scene seconds for the camera of the Gate (DownfallCut scene 7), from t = ticks since the scene start: the cast as it is; then
     * {@link Double#NaN} = the wait camera (also the 0.35 s of the hand coming down); the strike from the command as the old 50-65 s.
     */
    public static double sceneSeconds(int k, double t, double now) {
        if (k == key && commandAt >= 0) {
            double since = now - commandAt - SilentGateSpell.STRIKE_LAG;
            return since < 0 ? Double.NaN : 50 + since / 20.0;
        }
        if (t >= SilentGateSpell.CAST) return Double.NaN;
        return t / 20.0;
    }

    /** Seconds of the wait so far (for the slow push-in of the wait camera). */
    public static double waitSeconds(double now) {
        return waitAt < 0 ? 0 : Math.max(0, now - waitAt) / 20.0;
    }

    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void onClick(InputEvent.InteractionKeyMappingTriggered e) {
        if (!mine || !e.isAttack()) return;
        e.setCanceled(true);
        e.setSwingHand(false);
        mine = false;   // one command; the server answers with the COMMAND phase
        Net.CH.sendToServer(new Net.GateCommand());
    }

    @SubscribeEvent
    public static void onHud(RenderGuiEvent.Post e) {
        if (!mine) return;
        Minecraft mc = Minecraft.getInstance();
        GuiGraphics g = e.getGuiGraphics();
        Component text = Component.translatable("ui.pohsmp_core.silent_gate.command");
        double t = mc.player == null ? 0 : (mc.player.tickCount + e.getPartialTick()) / 10.0;
        int alpha = (int) (170 + 85 * Math.sin(t));
        int w = mc.font.width(text), x = g.guiWidth() / 2 - w / 2, y = g.guiHeight() - 64;
        g.fill(x - 6, y - 4, x + w + 6, y + 12, 0x88000000);
        g.drawString(mc.font, text, x, y, (alpha << 24) | 0xBFF2E8, true);
    }

    @SubscribeEvent
    public static void onUnload(LevelEvent.Unload e) {
        if (e.getLevel().isClientSide()) stop(key);
    }
}
