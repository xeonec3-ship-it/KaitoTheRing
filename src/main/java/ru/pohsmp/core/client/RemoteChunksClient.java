package ru.pohsmp.core.client;

import it.unimi.dsi.fastutil.longs.Long2ObjectMap;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.network.protocol.game.ClientboundForgetLevelChunkPacket;
import net.minecraft.world.level.chunk.LevelChunk;
import ru.pohsmp.core.spell.RemoteViewMath;

/**
 * Client of spell.RemoteView (owner 21.11, «Появление Ковена»): the squares of far chunks the server is allowed to send this client
 * although they lie outside its own view area. ClientChunkCacheMixin keeps such chunks in a side map of the chunk cache instead of
 * throwing them away; the window's end drops them the way a vanilla «forget chunk» does (light, entities, the Forge unload event).
 */
public final class RemoteChunksClient {
    private RemoteChunksClient() {}

    /** Implemented by ClientChunkCacheMixin: the far chunks it holds. */
    public interface Side {
        Long2ObjectMap<LevelChunk> pohsmp$side();
    }

    /** Window id -> {centre x, centre z, radius}; reset when the client level changes. */
    private static final Map<Integer, int[]> WINDOWS = new HashMap<>();
    private static ClientLevel forLevel;

    private static void check() {
        ClientLevel lvl = Minecraft.getInstance().level;
        if (lvl != forLevel) {
            WINDOWS.clear();
            forLevel = lvl;
        }
    }

    /** HFx.VIEW: r >= 0 opens window id over (cx, cz), r < 0 ends it. */
    public static void window(int id, int cx, int cz, int r) {
        check();
        if (r >= 0) {
            WINDOWS.put(id, new int[] {cx, cz, r});
            return;
        }
        int[] w = WINDOWS.remove(id);
        ClientLevel lvl = Minecraft.getInstance().level;
        var conn = Minecraft.getInstance().getConnection();
        if (w == null || lvl == null || conn == null || !(lvl.getChunkSource() instanceof Side s)) return;
        List<Long> drop = new ArrayList<>();
        for (long k : s.pohsmp$side().keySet()) {
            int x = RemoteViewMath.x(k), z = RemoteViewMath.z(k);
            if (RemoteViewMath.inSquare(w[0], w[1], w[2], x, z) && !allowed(x, z)) drop.add(k);
        }
        // the vanilla path: ClientChunkCache.drop (the mixin drops the side copy) and the light removal
        for (long k : drop) conn.handleForgetLevelChunk(new ClientboundForgetLevelChunkPacket(RemoteViewMath.x(k), RemoteViewMath.z(k)));
    }

    /** True if a window lets the client keep chunk (x, z) although it is out of its view range. */
    public static boolean allowed(int x, int z) {
        check();
        for (int[] w : WINDOWS.values()) if (RemoteViewMath.inSquare(w[0], w[1], w[2], x, z)) return true;
        return false;
    }
}
