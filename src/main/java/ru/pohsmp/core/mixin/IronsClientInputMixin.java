package ru.pohsmp.core.mixin;

import io.redspace.ironsspellbooks.player.ClientInputEvents;
import net.minecraftforge.event.TickEvent;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import ru.pohsmp.core.client.CastLockClient;

/**
 * Owner 21.11 (2): while the local player is held by the window of an animated spell, Iron's key handling sleeps — no spell wheel,
 * no quick cast, no cast key, no cancel on the use key release (the server would refuse them anyway, see CastLock).
 */
@Mixin(value = ClientInputEvents.class, remap = false)
public abstract class IronsClientInputMixin {
    @Inject(method = "onClientTick", at = @At("HEAD"), cancellable = true, remap = false, require = 0)
    private static void pohsmp$castLock(TickEvent.ClientTickEvent e, CallbackInfo ci) {
        if (CastLockClient.locked()) ci.cancel();
    }
}
