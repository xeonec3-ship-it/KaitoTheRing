package ru.pohsmp.core.mixin;

import io.redspace.ironsspellbooks.api.util.Utils;
import io.redspace.ironsspellbooks.network.casting.CancelCastPacket;
import net.minecraft.server.level.ServerPlayer;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;
import ru.pohsmp.core.spell.CastLock;
import ru.pohsmp.core.spell.CastLockMath;

/**
 * Owner 21.11: the book cast key and the quick cast keys (Utils.serverSideInitiateCast / serverSideInitiateQuickCast) cancel a running cast
 * of another spell BEFORE attemptInitiateCast — that is how an animated spell was cut by another one. While the window is open the
 * cancel is skipped; attemptInitiateCast then refuses the new spell (AbstractSpellMixin) with the hint.
 * releaseUsingHelper: letting go of the use button with a staff or scroll — the animated spell goes on.
 */
@Mixin(value = Utils.class, remap = false)
public abstract class IronsInitiateCastMixin {
    @Redirect(method = {"serverSideInitiateCast", "serverSideInitiateQuickCast"}, remap = false, require = 0,
            at = @At(value = "INVOKE", remap = false,
                    target = "Lio/redspace/ironsspellbooks/network/casting/CancelCastPacket;cancelCast(Lnet/minecraft/server/level/ServerPlayer;Z)V"))
    private static void pohsmp$keepOnNewCast(ServerPlayer p, boolean cooldown) {
        if (CastLock.cancelAllowed(p, CastLockMath.Cancel.NEW_CAST)) CancelCastPacket.cancelCast(p, cooldown);
    }

    @Redirect(method = "releaseUsingHelper", remap = false, require = 0,
            at = @At(value = "INVOKE", remap = false,
                    target = "Lio/redspace/ironsspellbooks/api/util/Utils;serverSideCancelCast(Lnet/minecraft/server/level/ServerPlayer;)V"))
    private static void pohsmp$keepOnRelease(ServerPlayer p) {
        if (CastLock.cancelAllowed(p, CastLockMath.Cancel.USE_RELEASED)) Utils.serverSideCancelCast(p);
    }
}
