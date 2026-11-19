package ru.pohsmp.core.mixin;

import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.Entity;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import ru.pohsmp.core.erased.Erased;

/**
 * T24 «Стёртое имя»: an erased player is not sent to anyone but himself - as if he had left. updatePlayer (m_140497_) decides whether a
 * viewer sees an entity; for an erased one we take the viewer off (m_140485_ removePlayer: "entity removed" to its client) instead.
 * No model, armour, name, shadow, entity sounds, minimap dot or Jade line follow from that: the client has no such entity.
 */
@Mixin(targets = "net.minecraft.server.level.ChunkMap$TrackedEntity")
public abstract class TrackedEntityMixin {
    @Shadow(remap = false) @Final Entity f_140472_;

    @Shadow(remap = false)
    public abstract void m_140485_(ServerPlayer viewer);

    @Inject(method = "m_140497_(Lnet/minecraft/server/level/ServerPlayer;)V", at = @At("HEAD"), cancellable = true, remap = false, require = 0)
    private void pohsmp$erased(ServerPlayer viewer, CallbackInfo ci) {
        if (viewer != f_140472_ && Erased.hiddenFrom(f_140472_, viewer)) {
            m_140485_(viewer);
            ci.cancel();
        }
    }
}
