package ru.pohsmp.core.net;

import java.util.function.Supplier;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.fml.DistExecutor;
import net.minecraftforge.network.NetworkEvent;

/** Hides an entity from drawing on the client for {@code ticks} (0 = show it again). See {@link ru.pohsmp.core.Hidden}. */
public final class HideMsg {
    public final int id, ticks;

    public HideMsg(int id, int ticks) {
        this.id = id;
        this.ticks = ticks;
    }

    public HideMsg(FriendlyByteBuf b) {
        this(b.readVarInt(), b.readVarInt());
    }

    public void encode(FriendlyByteBuf b) {
        b.writeVarInt(id);
        b.writeVarInt(ticks);
    }

    public void handle(Supplier<NetworkEvent.Context> ctx) {
        DistExecutor.unsafeRunWhenOn(Dist.CLIENT, () -> () -> ru.pohsmp.core.client.HiddenEntities.set(id, ticks));
    }
}
