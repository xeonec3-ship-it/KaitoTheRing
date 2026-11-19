package ru.pohsmp.core.mixin;

import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.renderer.GameRenderer;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import ru.pohsmp.core.client.DownfallCut;

/**
 * Cutscenes hide the HUD like F1 (DownfallCut.syncHud at the start of the frame). With hideGui on Gui.render and RenderGuiEvent do not run,
 * so the letterbox bars and titles are drawn here: after the HUD block, before loading overlays and screens, in GUI space.
 */
@Mixin(GameRenderer.class)
public abstract class GameRendererMixin {
    // SRG names (no refmap in this build, like the other mixins): render(FJZ)V = m_109093_, Minecraft.getOverlay = m_91265_
    @Inject(method = "m_109093_(FJZ)V", at = @At("HEAD"), remap = false, require = 0)
    private void pohsmp$hud(float pt, long nanos, boolean level, CallbackInfo ci) {
        DownfallCut.syncHud();
    }

    @Inject(method = "m_109093_(FJZ)V", at = @At(value = "INVOKE", target = "Lnet/minecraft/client/Minecraft;m_91265_()Lnet/minecraft/client/gui/screens/Overlay;", ordinal = 0, remap = false), remap = false, require = 0)
    private void pohsmp$bars(float pt, long nanos, boolean level, CallbackInfo ci) {
        Minecraft mc = Minecraft.getInstance();
        if (mc.level != null) {   // T22 «Сон бабочки»: ripple, the dream death, the waking shards - over the HUD and the scene bars
            GuiGraphics g = new GuiGraphics(mc, mc.renderBuffers().bufferSource());
            if (DownfallCut.active()) DownfallCut.drawBars(g, pt);
            ru.pohsmp.core.client.illusion.DreamScreen.overlay(g, pt);
            g.flush();
        }
    }

    /** T22: right after the level (and the hand) is drawn - the dream mirror folds the picture here. renderLevel = m_109089_. */
    @Inject(method = "m_109093_(FJZ)V", at = @At(value = "INVOKE", target = "Lnet/minecraft/client/renderer/GameRenderer;m_109089_(FJLcom/mojang/blaze3d/vertex/PoseStack;)V",
            shift = At.Shift.AFTER, remap = false), remap = false, require = 0)
    private void pohsmp$afterLevel(float pt, long nanos, boolean level, CallbackInfo ci) {
        ru.pohsmp.core.client.illusion.DreamScreen.afterLevel(pt);
    }
}
