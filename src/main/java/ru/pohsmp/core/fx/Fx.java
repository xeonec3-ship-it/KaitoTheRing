package ru.pohsmp.core.fx;

import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.network.PacketDistributor;
import ru.pohsmp.core.fx.sigil.SigilDef;
import ru.pohsmp.core.fx.sigil.SigilTimeline;
import ru.pohsmp.core.net.FxMsg;
import ru.pohsmp.core.net.Net;
import ru.pohsmp.core.spell.Tasks;

/**
 * Server side of the data-driven effects (docs/fx.md, docs/sigils.md). Spells start an instance with one call:
 * <pre>int id = Fx.play(sl, Fx.sigil("coven_seal").at(pos).caster(player));</pre>
 * and can stop it ({@link #stop}), move it ({@link #move}) or run code when a sigil is formed ({@link #whenFormed}).
 * Players within {@link #RANGE} blocks get the instance; players who come closer or log in later get it with its current age.
 */
public final class Fx {
    private Fx() {}

    public static final double RANGE = 160;
    private static int nextId = 1;

    /** What to start. Fluent; positions in world coordinates. */
    public static final class Spec {
        final FxMsg m = new FxMsg();
        UUID only;

        private Spec(int kind, String id) {
            m.op = FxMsg.START;
            m.kind = kind;
            m.id = id;
        }

        public Spec at(double x, double y, double z) {
            m.x = x;
            m.y = y;
            m.z = z;
            return this;
        }

        public Spec at(Vec3 p) {
            return at(p.x, p.y, p.z);
        }

        public Spec yaw(float yaw) {
            m.yaw = yaw;
            return this;
        }

        /** Tilt of the instance (degrees, Minecraft sense: positive looks down); models turn by yaw and pitch. */
        public Spec pitch(float pitch) {
            m.pitch = pitch;
            return this;
        }

        public Spec style(String style) {
            m.style = style;
            return this;
        }

        public Spec scale(double s) {
            m.scale = (float) s;
            return this;
        }

        /** Anchor "caster" follows this entity; the position and yaw default to it. */
        public Spec caster(Entity e) {
            m.caster = e.getId();
            m.yaw = e.getYRot();
            if (m.x == 0 && m.y == 0 && m.z == 0) at(e.position());
            return this;
        }

        public Spec target(Entity e) {
            m.target = e.getId();
            return target(e.position());
        }

        public Spec target(Vec3 p) {
            m.hasTarget = true;
            m.tx = p.x;
            m.ty = p.y;
            m.tz = p.z;
            return this;
        }

        public Spec look(Vec3 p) {
            m.hasLook = true;
            m.lx = p.x;
            m.ly = p.y;
            m.lz = p.z;
            return this;
        }

        /** The whole instance follows this entity, keeping the offset it had at the start. */
        public Spec attach(Entity e) {
            m.attach = e.getId();
            return this;
        }

        public Spec point(String name, Vec3 p) {
            m.points.put(name, new double[] {p.x, p.y, p.z});
            return this;
        }

        public Spec color(int rgb) {
            m.color = rgb & 0xFFFFFF;
            return this;
        }

        /** ground, sky, facing, billboard; anything else keeps the definition's own. */
        public Spec orientation(String o) {
            m.orientation = -1;
            if (o != null) for (SigilDef.Orientation v : SigilDef.Orientation.values())
                if (v.name().equalsIgnoreCase(o)) m.orientation = v.ordinal();
            return this;
        }

        /** Ticks until the instance starts dissolving on its own (-1: as the definition says). */
        public Spec duration(int ticks) {
            m.duration = ticks;
            return this;
        }

        /** Only this player gets the instance (private marks). */
        public Spec only(ServerPlayer p) {
            only = p.getUUID();
            return this;
        }

        /**
         * Inscription for the sigil's text layers with this {@code slot} (docs/sigils.md «Надписи»), e.g.
         * {@code Fx.sigil("time_clock").text("count", "0")}. Up to {@link FxMsg#MAX_TEXT} characters.
         */
        public Spec text(String slot, String text) {
            if (slot != null && text != null) m.texts.put(slot, clip(text));
            return this;
        }

        public Spec seed(long seed) {
            m.seed = seed;
            return this;
        }
    }

    public static Spec fx(String id) {
        return new Spec(FxMsg.FX, id);
    }

    public static Spec sigil(String id) {
        return new Spec(FxMsg.SIGIL, id);
    }

    public static Spec mesh(String id) {
        return new Spec(FxMsg.MESH, id);
    }

    // ---------------------------------------------------------------- running instances

    private static final class Active {
        ResourceKey<Level> dim;
        FxMsg msg;
        long start, end = Long.MAX_VALUE;
        Set<UUID> sent = new HashSet<>();
        UUID owner, only;
    }

    private static final Map<Integer, Active> ACTIVE = new HashMap<>();

    /** Starts the instance for nearby players and returns its id. */
    public static int play(ServerLevel sl, Spec s) {
        FxMsg m = s.m;
        m.inst = nextId++;
        if (m.seed == 0) m.seed = sl.random.nextLong();
        Active a = new Active();
        a.dim = sl.dimension();
        a.msg = m;
        a.only = s.only;
        a.start = sl.getGameTime();
        long life = lifetime(m);
        if (life >= 0) a.end = a.start + life;
        if (m.caster >= 0 && sl.getEntity(m.caster) instanceof ServerPlayer sp) a.owner = sp.getUUID();
        ACTIVE.put(m.inst, a);
        for (ServerPlayer p : sl.players()) offer(sl, p, a);
        return m.inst;
    }

    /** Owner for "/pohsmp sigil stop" when the caster is not a player (commands, scripts). */
    public static void owner(int inst, UUID owner) {
        Active a = ACTIVE.get(inst);
        if (a != null) a.owner = owner;
    }

    /** Starts the dissolve ("" = as defined; sigils also take collapse, fade, shatter, reverse, comma-separated). */
    public static void stop(ServerLevel sl, int inst, String mode) {
        Active a = ACTIVE.get(inst);
        if (a == null) return;
        FxMsg m = new FxMsg();
        m.op = FxMsg.STOP;
        m.inst = inst;
        m.mode = mode == null ? "" : mode.toLowerCase(Locale.ROOT);
        sendTo(sl, a, m);
        a.end = Math.min(a.end, sl.getGameTime() + 60);
    }

    public static void move(ServerLevel sl, int inst, Vec3 p, float yaw) {
        move(sl, inst, p, yaw, 0);
    }

    /** Moves the instance and turns it (models in it face yaw/pitch). */
    public static void move(ServerLevel sl, int inst, Vec3 p, float yaw, float pitch) {
        Active a = ACTIVE.get(inst);
        if (a == null) return;
        a.msg.x = p.x;
        a.msg.y = p.y;
        a.msg.z = p.z;
        a.msg.yaw = yaw;
        a.msg.pitch = pitch;
        FxMsg m = new FxMsg();
        m.op = FxMsg.MOVE;
        m.inst = inst;
        m.x = p.x;
        m.y = p.y;
        m.z = p.z;
        m.yaw = yaw;
        m.pitch = pitch;
        sendTo(sl, a, m);
    }

    /**
     * Replaces the inscription in a running sigil's text layers with this slot: the new text writes itself in over the layer's
     * {@code change} ticks with a flare (counter on the Countdown clock, T04). Late joiners get the latest text. Same text — nothing sent.
     */
    public static void text(ServerLevel sl, int inst, String slot, String text) {
        Active a = ACTIVE.get(inst);
        if (a == null || slot == null || text == null) return;
        String t = clip(text);
        if (t.equals(a.msg.texts.get(slot))) return;
        a.msg.texts.put(slot, t);
        FxMsg m = new FxMsg();
        m.op = FxMsg.TEXT;
        m.inst = inst;
        m.slot = slot;
        m.text = t;
        sendTo(sl, a, m);
    }

    private static String clip(String s) {
        return s.length() <= FxMsg.MAX_TEXT ? s : s.substring(0, FxMsg.MAX_TEXT);
    }

    public static boolean running(int inst) {
        return ACTIVE.containsKey(inst);
    }

    /** Stops every instance a player owns; returns how many. */
    public static int stopOwned(ServerLevel sl, UUID owner) {
        int n = 0;
        for (var e : new HashMap<>(ACTIVE).entrySet())
            if (owner.equals(e.getValue().owner) && e.getValue().end > sl.getGameTime() + 60) {
                stop(sl, e.getKey(), "");
                n++;
            }
        return n;
    }

    /** Runs r on the server `tick` ticks after the instance started (once; skipped if it was stopped before). */
    public static void at(ServerLevel sl, int inst, int tick, Runnable r) {
        Active a = ACTIVE.get(inst);
        if (a == null) return;
        long when = a.start + tick;
        Tasks.add(() -> {
            if (sl.getGameTime() < when) return true;
            Active now = ACTIVE.get(inst);
            if (now == a && now.end >= when) r.run();
            return false;
        });
    }

    /** Runs r when the sigil instance is formed (docs/sigils.md: formedAt), e.g. to strike right after the seal is complete. */
    public static void whenFormed(ServerLevel sl, int inst, Runnable r) {
        Active a = ACTIVE.get(inst);
        if (a == null || a.msg.kind != FxMsg.SIGIL) return;
        SigilDef d = FxLib.sigil(a.msg.id);
        if (d != null) at(sl, inst, SigilTimeline.timings(d).formedAt(), r);
    }

    /** Ticks from the start until a sigil is formed, or -1 if there is no such sigil. */
    public static int formedAt(String sigilId) {
        SigilDef d = FxLib.sigil(sigilId);
        return d == null ? -1 : SigilTimeline.timings(d).formedAt();
    }

    /** Tells every client to drop cached definitions (after /pohsmp fx reload). */
    public static void reloadClients(ServerLevel sl) {
        FxLib.reload();
        FxMsg m = new FxMsg();
        m.op = FxMsg.RELOAD;
        for (ServerPlayer p : sl.getServer().getPlayerList().getPlayers()) Net.CH.send(PacketDistributor.PLAYER.with(() -> p), m);
    }

    /** -1 = until stopped. */
    private static long lifetime(FxMsg m) {
        if (m.kind == FxMsg.FX) {
            FxDef d = FxLib.fx(m.id);
            int dur = m.duration >= 0 ? m.duration : d == null ? 0 : d.duration();
            return dur < 0 ? -1 : dur + 40;
        }
        if (m.kind == FxMsg.SIGIL) {
            SigilDef d = FxLib.sigil(m.id);
            if (d == null) return 0;
            if (m.duration >= 0) return m.duration + d.dissolve().duration() + 20;
            if (d.lifetime() >= 0) return d.lifetime();
            int stop = SigilTimeline.autoStopAt(d);
            return stop < 0 ? -1 : stop + d.dissolve().duration() + 80;
        }
        return m.duration >= 0 ? m.duration + 40 : -1;
    }

    private static boolean near(ServerPlayer p, FxMsg m) {
        return p.distanceToSqr(m.x, m.y, m.z) < RANGE * RANGE || (m.hasTarget && p.distanceToSqr(m.tx, m.ty, m.tz) < RANGE * RANGE);
    }

    private static void offer(ServerLevel sl, ServerPlayer p, Active a) {
        if (p.level() != sl || a.only != null && !a.only.equals(p.getUUID()) || a.sent.contains(p.getUUID()) || !near(p, a.msg)) return;
        a.sent.add(p.getUUID());
        FxMsg m = a.msg.copyAged((int) (sl.getGameTime() - a.start));
        Net.CH.send(PacketDistributor.PLAYER.with(() -> p), m);
    }

    private static void sendTo(ServerLevel sl, Active a, FxMsg m) {
        for (ServerPlayer p : sl.getServer().getPlayerList().getPlayers())
            if (a.sent.contains(p.getUUID())) Net.CH.send(PacketDistributor.PLAYER.with(() -> p), m);
    }

    public static final class FxServerEvents {
        private FxServerEvents() {}

        @SubscribeEvent
        public static void onServerTick(TickEvent.ServerTickEvent e) {
            if (e.phase != TickEvent.Phase.END || ACTIVE.isEmpty()) return;
            var server = e.getServer();
            if (server == null || server.getTickCount() % 10 != 0) return;
            Iterator<Active> it = ACTIVE.values().iterator();
            while (it.hasNext()) {
                Active a = it.next();
                ServerLevel sl = server.getLevel(a.dim);
                if (sl == null || sl.getGameTime() > a.end) {
                    it.remove();
                    continue;
                }
                if (a.end - sl.getGameTime() < 40) continue;      // about to end: not worth sending to newcomers
                for (ServerPlayer p : sl.players()) offer(sl, p, a);
            }
        }

        @SubscribeEvent
        public static void onLogout(PlayerEvent.PlayerLoggedOutEvent e) {
            for (Active a : ACTIVE.values()) a.sent.remove(e.getEntity().getUUID());
        }

        @SubscribeEvent
        public static void onDimension(PlayerEvent.PlayerChangedDimensionEvent e) {
            for (Active a : ACTIVE.values()) a.sent.remove(e.getEntity().getUUID());
        }

        @SubscribeEvent
        public static void onStopping(ServerStoppingEvent e) {
            ACTIVE.clear();
        }
    }
}
