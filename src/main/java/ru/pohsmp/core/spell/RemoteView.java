package ru.pohsmp.core.spell;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import net.minecraft.network.protocol.game.ClientboundLevelChunkWithLightPacket;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.level.TicketType;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.chunk.LevelChunk;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.network.PacketDistributor;
import ru.pohsmp.core.net.Net;
import ru.pohsmp.core.net.Net.HFx;

/**
 * Owner 21.11 («Появление Ковена»: the arena players see air where the caster stands, the caster sees air at the arena): a scene
 * camera shows a place far from the player, but vanilla sends a player only the chunks of his own view distance, so the far place
 * is empty on his client.
 *
 * A window keeps a far square of chunks (radius r around a point) on one player's client for a while:
 * - server: a region ticket (TicketType pohsmp_remote_view, one per window) keeps the square loaded, renewed every second while the
 *   window lives and removed when it ends;
 * - the chunks go to that player as ordinary ClientboundLevelChunkWithLightPacket, a few per tick, nearest to the point first; block
 *   changes in them reach him too (ChunkMapMixin: ChunkMap.getPlayers adds the window's viewers), and so do the entities standing in
 *   them (TrackedEntityMixin: the viewer is paired with them, so the caster's model and animation are seen);
 * - client: vanilla keeps chunks only within its cache radius around the player and throws the far ones away («Ignoring chunk since
 *   it's not in the view range»). HFx.VIEW tells the client the window's square first; ClientChunkCacheMixin keeps such chunks in a side
 *   map next to the vanilla storage, so the player's own surroundings stay as they are (no re-centring, no re-sending);
 * - the end (the scene ends, the player dies, the safety limit): HFx.VIEW off - the client drops the side chunks of that square; the
 *   ticket is removed; the paired entities are dropped by vanilla on the viewer's next move check. Logout / another dimension: only the
 *   ticket (the client has lost that level anyway). Pure logic: RemoteViewMath.
 */
public final class RemoteView {
    private RemoteView() {}

    /** Keeps a window's square loaded; one ticket per window (the key is the window id), so ending one window frees only its own. */
    private static final TicketType<Integer> TICKET = TicketType.create("pohsmp_remote_view", Integer::compare, 60);

    private static final class Window {
        final int id;
        final int owner;
        final ResourceKey<Level> dim;
        final int cx, cz, r;
        final long until;
        final RemoteViewMath.Queue queue;
        boolean released;

        Window(int id, int owner, ResourceKey<Level> dim, int cx, int cz, int r, long until, long[] keys) {
            this.id = id;
            this.owner = owner;
            this.dim = dim;
            this.cx = cx;
            this.cz = cz;
            this.r = r;
            this.until = until;
            this.queue = new RemoteViewMath.Queue(keys);
        }
    }

    private static final Map<UUID, List<Window>> WINDOWS = new HashMap<>();
    private static int nextId = 1;

    /**
     * Keeps the square of radius r (chunks) around p in level `lvl` on sp's client for at most `ticks`, for the scene `owner` (its
     * cutscene key). Nothing if sp is in another level (the client holds one level only), if the square is in his own view anyway,
     * or if this owner already has a window there.
     */
    public static void open(ServerPlayer sp, ServerLevel lvl, Vec3 p, int r, int owner, int ticks) {
        if (sp.level() != lvl || sp.hasDisconnected() || !sp.isAlive()) return;
        ChunkPos c = new ChunkPos(net.minecraft.core.BlockPos.containing(p));
        List<Window> ws = WINDOWS.computeIfAbsent(sp.getUUID(), u -> new ArrayList<>());
        for (Window w : ws) if (w.owner == owner && w.dim == lvl.dimension() && w.cx == c.x && w.cz == c.z && !w.released) return;
        ChunkPos home = sp.chunkPosition();
        int vd = sp.server.getPlayerList().getViewDistance();
        if (RemoteViewMath.covered(home.x, home.z, c.x, c.z, r, vd)) {
            if (ws.isEmpty()) WINDOWS.remove(sp.getUUID());
            return;
        }
        Window w = new Window(nextId++, owner, lvl.dimension(), c.x, c.z, r, lvl.getGameTime() + ticks,
                RemoteViewMath.toSend(home.x, home.z, vd, c.x, c.z, r));
        ws.add(w);
        lvl.getChunkSource().addRegionTicket(TICKET, c, r, w.id);
        // the client must know the square before the first chunk of it comes (chunks go from the next tick)
        Net.CH.send(PacketDistributor.PLAYER.with(() -> sp), new HFx(HFx.VIEW, w.id, c.x, c.z, r, 0, 0, 0, 0, 0));
    }

    /** Ends the windows of a scene for one player (its place is no longer shown to him). */
    public static void close(UUID player, int owner) {
        List<Window> ws = WINDOWS.get(player);
        if (ws != null) for (Window w : ws) if (w.owner == owner) w.released = true;
    }

    /** Ends every window of a scene (it is over or cut short). */
    public static void closeAll(int owner) {
        for (List<Window> ws : WINDOWS.values()) for (Window w : ws) if (w.owner == owner) w.released = true;
    }

    // ---------------------------------------------------------------- hooks (mixins)

    /** TrackedEntityMixin: viewer gets the entity although it is far - it stands in a chunk his window has sent him. */
    public static boolean sees(ServerPlayer viewer, Entity e) {
        if (WINDOWS.isEmpty()) return false;
        List<Window> ws = WINDOWS.get(viewer.getUUID());
        if (ws == null || viewer.level() != e.level()) return false;
        ChunkPos cp = e.chunkPosition();
        for (Window w : ws)
            if (!w.released && w.dim == e.level().dimension() && RemoteViewMath.inSquare(w.cx, w.cz, w.r, cp.x, cp.z)
                    && w.queue.wasSent(RemoteViewMath.key(cp.x, cp.z))) return true;
        return false;
    }

    /** Fx: an effect at (x, z) in sp's level is sent to him if one of his windows shows that spot (the arena portal for the far caster). */
    public static boolean covers(ServerPlayer sp, double x, double z) {
        if (WINDOWS.isEmpty()) return false;
        List<Window> ws = WINDOWS.get(sp.getUUID());
        if (ws == null) return false;
        int cx = net.minecraft.util.Mth.floor(x) >> 4, cz = net.minecraft.util.Mth.floor(z) >> 4;
        for (Window w : ws) if (!w.released && w.dim == sp.level().dimension() && RemoteViewMath.inSquare(w.cx, w.cz, w.r, cx, cz)) return true;
        return false;
    }

    /** ChunkMapMixin: the window viewers of a chunk, added to vanilla's list (block changes, light, block entities go to them too). */
    public static List<ServerPlayer> viewers(ServerLevel lvl, ChunkPos cp, List<ServerPlayer> vanilla) {
        if (WINDOWS.isEmpty()) return vanilla;
        List<ServerPlayer> out = null;
        long k = RemoteViewMath.key(cp.x, cp.z);
        for (var e : WINDOWS.entrySet()) {
            for (Window w : e.getValue()) {
                if (w.released || w.dim != lvl.dimension() || !w.queue.wasSent(k)) continue;
                ServerPlayer sp = lvl.getServer().getPlayerList().getPlayer(e.getKey());
                if (sp == null || sp.level() != lvl || vanilla.contains(sp) || out != null && out.contains(sp)) break;
                if (out == null) out = new ArrayList<>(vanilla);
                out.add(sp);
                break;
            }
        }
        return out == null ? vanilla : out;
    }

    // ---------------------------------------------------------------- every tick

    private static void tick(MinecraftServer srv) {
        if (WINDOWS.isEmpty()) return;
        for (Iterator<Map.Entry<UUID, List<Window>>> it = WINDOWS.entrySet().iterator(); it.hasNext(); ) {
            var e = it.next();
            ServerPlayer sp = srv.getPlayerList().getPlayer(e.getKey());
            for (Iterator<Window> wi = e.getValue().iterator(); wi.hasNext(); ) {
                Window w = wi.next();
                ServerLevel lvl = srv.getLevel(w.dim);
                boolean online = sp != null && !sp.hasDisconnected() && lvl != null;
                boolean same = online && sp.level() == lvl;
                RemoteViewMath.End end = RemoteViewMath.end(online, same, online && sp.isAlive(), lvl == null ? 0 : lvl.getGameTime(), w.until, w.released);
                if (end != RemoteViewMath.End.KEEP) {
                    if (lvl != null) lvl.getChunkSource().removeRegionTicket(TICKET, new ChunkPos(w.cx, w.cz), w.r, w.id);
                    if (end == RemoteViewMath.End.CLOSE)
                        Net.CH.send(PacketDistributor.PLAYER.with(() -> sp), new HFx(HFx.VIEW, w.id, w.cx, w.cz, -1, 0, 0, 0, 0, 0));
                    wi.remove();
                    continue;
                }
                if (lvl.getGameTime() % 20 == 0) lvl.getChunkSource().addRegionTicket(TICKET, new ChunkPos(w.cx, w.cz), w.r, w.id);
                if (w.queue.done()) continue;
                for (long k : w.queue.next(RemoteViewMath.PER_TICK, k -> lvl.getChunkSource().getChunkNow(RemoteViewMath.x(k), RemoteViewMath.z(k)) != null)) {
                    LevelChunk ch = lvl.getChunkSource().getChunkNow(RemoteViewMath.x(k), RemoteViewMath.z(k));
                    if (ch != null) sp.connection.send(new ClientboundLevelChunkWithLightPacket(ch, lvl.getLightEngine(), null, null));
                }
            }
            if (e.getValue().isEmpty()) it.remove();
        }
    }

    /** Windows alive (for tests and the log). */
    public static int count() {
        int n = 0;
        for (List<Window> ws : WINDOWS.values()) n += ws.size();
        return n;
    }

    public static final class Events {
        private Events() {}

        @SubscribeEvent
        public static void onTick(TickEvent.ServerTickEvent e) {
            if (e.phase == TickEvent.Phase.END) tick(e.getServer());
        }

        @SubscribeEvent
        public static void onStopping(ServerStoppingEvent e) {
            WINDOWS.clear();
        }
    }
}
