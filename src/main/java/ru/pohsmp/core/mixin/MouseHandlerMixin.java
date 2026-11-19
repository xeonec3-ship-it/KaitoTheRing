package ru.pohsmp.core.mixin;

import net.minecraft.client.MouseHandler;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import ru.pohsmp.core.client.DownfallCut;

/**
 * Owner 19.11: while a spell's camera scene plays, the mouse does not turn the player (others saw the frozen body spin). The movement is
 * thrown away, not saved up, so the view does not jump when the scene ends.
 */
@Mixin(MouseHandler.class)
public abstract class MouseHandlerMixin {
    // SRG names (no refmap in this build): turnPlayer()V = m_91523_, accumulatedDX/DY = f_91516_/f_91517_
    @Shadow(remap = false) private double f_91516_;
    @Shadow(remap = false) private double f_91517_;

    @Inject(method = "m_91523_()V", at = @At("HEAD"), cancellable = true, remap = false, require = 0)
    private void pohsmp$noTurn(CallbackInfo ci) {
        if (!DownfallCut.active()) return;
        f_91516_ = 0;
        f_91517_ = 0;
        ci.cancel();
    }
}
