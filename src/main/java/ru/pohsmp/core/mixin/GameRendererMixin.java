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
        if (!DownfallCut.active()) return;
        Minecraft mc = Minecraft.getInstance();
        GuiGraphics g = new GuiGraphics(mc, mc.renderBuffers().bufferSource());
        DownfallCut.drawBars(g, pt);
        g.flush();
    }
}
