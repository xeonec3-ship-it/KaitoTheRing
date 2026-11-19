package ru.pohsmp.core.mixin;

import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.player.Player;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
import ru.pohsmp.core.silent.SilentWitch;

/** Xaero's Minimap (and the World Map, which reuses its radar): a full-set Silent Witch counts as invisible, so the radar skips her. */
@Pseudo
@Mixin(targets = "xaero.hud.minimap.radar.state.RadarStateUpdater", remap = false)
public class XaeroRadarMixin {
    @Inject(method = "isInvisibleTo", at = @At("HEAD"), cancellable = true, require = 0)
    private void pohsmp$silentWitch(Entity entity, Player viewer, CallbackInfoReturnable<Boolean> cir) {
        if (entity != viewer && SilentWitch.nameless(entity)) cir.setReturnValue(true);
    }
}
