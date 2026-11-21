package ru.pohsmp.core.mixin;

import it.unimi.dsi.fastutil.longs.Long2ObjectMap;
import it.unimi.dsi.fastutil.longs.Long2ObjectOpenHashMap;
import java.util.function.Consumer;
import net.minecraft.client.multiplayer.ClientChunkCache;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.chunk.ChunkStatus;
import net.minecraft.world.level.chunk.EmptyLevelChunk;
import net.minecraft.world.level.chunk.LevelChunk;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.event.level.ChunkEvent;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
import ru.pohsmp.core.client.RemoteChunksClient;

/**
 * Owner 21.11 («Появление Ковена»): far chunks of a scene window (spell.RemoteView). Vanilla keeps chunks only within its cache radius
 * around the player and ignores the rest («Ignoring chunk since it's not in the view range»); a chunk inside an open window goes into
 * a side map instead, and getChunk finds it there when the vanilla storage has none. The player's own chunks are not touched.
 * SRG, no refmap: replaceWithPacketData = m_194116_, getChunk = m_7587_, drop = m_104455_, level = f_104411_.
 */
@Mixin(ClientChunkCache.class)
public abstract class ClientChunkCacheMixin implements RemoteChunksClient.Side {
    @Shadow(remap = false) @Final ClientLevel f_104411_;

    @Unique private final Long2ObjectOpenHashMap<LevelChunk> pohsmp$far = new Long2ObjectOpenHashMap<>();

    @Override
    public Long2ObjectMap<LevelChunk> pohsmp$side() {
        return pohsmp$far;
    }

    /** At the «not in the view range» warning: a chunk of an open window is kept on the side. */
    @Inject(method = "m_194116_(IILnet/minecraft/network/FriendlyByteBuf;Lnet/minecraft/nbt/CompoundTag;Ljava/util/function/Consumer;)Lnet/minecraft/world/level/chunk/LevelChunk;",
            at = @At(value = "INVOKE", target = "Lorg/slf4j/Logger;warn(Ljava/lang/String;Ljava/lang/Object;Ljava/lang/Object;)V", remap = false),
            cancellable = true, remap = false, require = 0)
    private void pohsmp$keepFar(int x, int z, FriendlyByteBuf buf, CompoundTag tag, Consumer<?> out, CallbackInfoReturnable<LevelChunk> cir) {
        if (!RemoteChunksClient.allowed(x, z)) return;
        long k = ChunkPos.asLong(x, z);
        ChunkPos pos = new ChunkPos(x, z);
        LevelChunk ch = pohsmp$far.get(k);
        if (ch == null) {
            ch = new LevelChunk(f_104411_, pos);
            pohsmp$far.put(k, ch);
        }
        pohsmp$fill(ch, buf, tag, out);
        f_104411_.onChunkLoaded(pos);
        MinecraftForge.EVENT_BUS.post(new ChunkEvent.Load(ch, false));
        cir.setReturnValue(ch);
    }

    @SuppressWarnings({"unchecked", "rawtypes"})
    @Unique
    private static void pohsmp$fill(LevelChunk ch, FriendlyByteBuf buf, CompoundTag tag, Consumer out) {
        ch.replaceWithPacketData(buf, tag, out);
    }

    /** Vanilla took the chunk into its own storage (the player came close): the side copy is no longer needed. */
    @Inject(method = "m_194116_(IILnet/minecraft/network/FriendlyByteBuf;Lnet/minecraft/nbt/CompoundTag;Ljava/util/function/Consumer;)Lnet/minecraft/world/level/chunk/LevelChunk;",
            at = @At("RETURN"), remap = false, require = 0)
    private void pohsmp$taken(int x, int z, FriendlyByteBuf buf, CompoundTag tag, Consumer<?> out, CallbackInfoReturnable<LevelChunk> cir) {
        if (pohsmp$far.isEmpty() || cir.getReturnValue() == null) return;
        long k = ChunkPos.asLong(x, z);
        LevelChunk side = pohsmp$far.get(k);
        if (side != null && side != cir.getReturnValue()) pohsmp$far.remove(k);
    }

    /** Lookups the vanilla storage cannot answer (out of its range) fall back to the side map. */
    @Inject(method = "m_7587_(IILnet/minecraft/world/level/chunk/ChunkStatus;Z)Lnet/minecraft/world/level/chunk/LevelChunk;",
            at = @At("RETURN"), cancellable = true, remap = false, require = 0)
    private void pohsmp$getFar(int x, int z, ChunkStatus status, boolean create, CallbackInfoReturnable<LevelChunk> cir) {
        if (pohsmp$far.isEmpty()) return;
        LevelChunk rv = cir.getReturnValue();
        if (rv != null && !(rv instanceof EmptyLevelChunk)) return;
        LevelChunk side = pohsmp$far.get(ChunkPos.asLong(x, z));
        if (side != null) cir.setReturnValue(side);
    }

    /** «Forget chunk» (vanilla or the window's end): the side copy is unloaded like a vanilla one. */
    @Inject(method = "m_104455_(II)V", at = @At("HEAD"), remap = false, require = 0)
    private void pohsmp$dropFar(int x, int z, CallbackInfo ci) {
        if (pohsmp$far.isEmpty()) return;
        LevelChunk side = pohsmp$far.remove(ChunkPos.asLong(x, z));
        if (side == null) return;
        MinecraftForge.EVENT_BUS.post(new ChunkEvent.Unload(side));
        f_104411_.unload(side);
    }
}
