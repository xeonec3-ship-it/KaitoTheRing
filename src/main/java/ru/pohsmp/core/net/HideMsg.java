package ru.pohsmp.core.net;

import java.util.function.Supplier;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.fml.DistExecutor;
import net.minecraftforge.network.NetworkEvent;

/** Hide an entity on the client (ru.pohsmp.core.Hidden): ticks &gt; 0 for that long, -1 until shown, 0 show now. */
public final class HideMsg {
    public final int entity, ticks;

    public HideMsg(int entity, int ticks) {
        this.entity = entity;
        this.ticks = ticks;
    }

    public HideMsg(FriendlyByteBuf b) {
        entity = b.readVarInt();
        ticks = b.readInt();
    }

    public void encode(FriendlyByteBuf b) {
        b.writeVarInt(entity);
        b.writeInt(ticks);
    }

    public void handle(Supplier<NetworkEvent.Context> ctx) {
        DistExecutor.unsafeRunWhenOn(Dist.CLIENT, () -> () -> ru.pohsmp.core.client.HiddenEntities.handle(this));
    }
}
