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

    @Shadow(remap = false) @Final net.minecraft.server.level.ServerEntity f_140471_;
    @Shadow(remap = false) @Final java.util.Set<net.minecraft.server.network.ServerPlayerConnection> f_140475_;

    @Inject(method = "m_140497_(Lnet/minecraft/server/level/ServerPlayer;)V", at = @At("HEAD"), cancellable = true, remap = false, require = 0)
    private void pohsmp$erased(ServerPlayer viewer, CallbackInfo ci) {
        // T25: a nightmare only for those immersed deep enough
        if (viewer != f_140472_ && (Erased.hiddenFrom(f_140472_, viewer) || ru.pohsmp.core.nightmare.Bestiary.hiddenFrom(f_140472_, viewer))) {
            m_140485_(viewer);
            ci.cancel();
        }
        // owner 21.11 («Появление Ковена»): a far entity in a chunk a scene window has sent the viewer (spell.RemoteView) is seen
        // although it is beyond the tracking range - the arena players see the caster at his far spot
        if (viewer != f_140472_ && f_140472_.broadcastToPlayer(viewer) && ru.pohsmp.core.spell.RemoteView.sees(viewer, f_140472_)) {
            if (f_140475_.add(viewer.connection)) {
                f_140471_.addPairing(viewer);
                net.minecraftforge.event.ForgeEventFactory.onStartEntityTracking(f_140472_, viewer);
            }
            ci.cancel();
        }
    }
}
