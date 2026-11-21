package ru.pohsmp.core.mixin;

import java.util.List;
import net.minecraft.server.level.ChunkMap;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.level.ChunkPos;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/**
 * Owner 21.11 («Появление Ковена»): block changes, light and block entities of a chunk go to the players of ChunkMap.getPlayers
 * (m_183262_); the viewers of a scene window on that chunk (spell.RemoteView) get them too, though they stand far away. Not for the
 * «edge only» query (that one is vanilla's view-distance bookkeeping).
 */
@Mixin(ChunkMap.class)
public abstract class ChunkMapMixin {
    @Shadow(remap = false) @Final ServerLevel f_140133_;

    @Inject(method = "m_183262_(Lnet/minecraft/world/level/ChunkPos;Z)Ljava/util/List;", at = @At("RETURN"), cancellable = true, remap = false, require = 0)
    private void pohsmp$windowViewers(ChunkPos pos, boolean edgeOnly, CallbackInfoReturnable<List<ServerPlayer>> cir) {
        if (!edgeOnly) {
            List<ServerPlayer> l = ru.pohsmp.core.spell.RemoteView.viewers(f_140133_, pos, cir.getReturnValue());
            if (l != cir.getReturnValue()) cir.setReturnValue(l);
        }
    }
}
