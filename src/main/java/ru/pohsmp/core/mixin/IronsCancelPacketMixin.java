package ru.pohsmp.core.mixin;

import io.redspace.ironsspellbooks.network.casting.CancelCastPacket;
import net.minecraft.server.level.ServerPlayer;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;
import ru.pohsmp.core.spell.CastLock;
import ru.pohsmp.core.spell.CastLockMath;

/**
 * Owner 21.11: the client asks Iron's to cancel the cast when it opens a screen (the chat and the pause menu stay allowed while the
 * window is open, other screens are blocked on the client). The server ignores the request while the window is open.
 */
@Mixin(value = CancelCastPacket.class, remap = false)
public abstract class IronsCancelPacketMixin {
    @Redirect(method = "lambda$handle$0", remap = false, require = 0,
            at = @At(value = "INVOKE", remap = false,
                    target = "Lio/redspace/ironsspellbooks/network/casting/CancelCastPacket;cancelCast(Lnet/minecraft/server/level/ServerPlayer;Z)V"))
    private void pohsmp$keepOnRequest(ServerPlayer p, boolean cooldown) {
        if (p == null || CastLock.cancelAllowed(p, CastLockMath.Cancel.CLIENT_REQUEST)) CancelCastPacket.cancelCast(p, cooldown);
    }
}
