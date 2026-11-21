package ru.pohsmp.core.mixin;

import io.redspace.ironsspellbooks.api.util.Utils;
import io.redspace.ironsspellbooks.player.ServerPlayerEvents;
import net.minecraft.server.level.ServerPlayer;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;
import ru.pohsmp.core.spell.CastLock;
import ru.pohsmp.core.spell.CastLockMath;

/**
 * Owner 21.11: Iron's stops a cast when the hand item changes (hotbar slot, swap, the casting item gone) or a container opens.
 * While the window of our animated spell is open the slot change and screens are blocked (CastLock), and these cancels are skipped.
 */
@Mixin(value = ServerPlayerEvents.class, remap = false)
public abstract class IronsServerEventsMixin {
    @Redirect(method = "onLivingEquipmentChangeEvent", remap = false, require = 0,
            at = @At(value = "INVOKE", remap = false,
                    target = "Lio/redspace/ironsspellbooks/api/util/Utils;serverSideCancelCast(Lnet/minecraft/server/level/ServerPlayer;)V"))
    private static void pohsmp$keepOnItem(ServerPlayer p) {
        if (CastLock.cancelAllowed(p, CastLockMath.Cancel.ITEM_CHANGED)) Utils.serverSideCancelCast(p);
    }

    @Redirect(method = "onPlayerOpenContainer", remap = false, require = 0,
            at = @At(value = "INVOKE", remap = false,
                    target = "Lio/redspace/ironsspellbooks/api/util/Utils;serverSideCancelCast(Lnet/minecraft/server/level/ServerPlayer;)V"))
    private static void pohsmp$keepOnContainer(ServerPlayer p) {
        if (CastLock.cancelAllowed(p, CastLockMath.Cancel.CONTAINER)) Utils.serverSideCancelCast(p);
    }
}
