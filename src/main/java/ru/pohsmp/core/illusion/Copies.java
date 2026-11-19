package ru.pohsmp.core.illusion;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.function.Consumer;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Pose;
import net.minecraft.world.entity.projectile.Projectile;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.living.LivingDeathEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.network.PacketDistributor;
import ru.pohsmp.core.fx.Fx;
import ru.pohsmp.core.net.IlluMsg;
import ru.pohsmp.core.net.Net;

/**
 * T22: false players. A copy lives only on the server as a point with a player's hitbox; the victims' clients get packets and draw it as
 * a real player (client/illusion/Copies: the caster's skin, armour, hand items, name, shadow - the real player renderer).
 * Nobody else sees it. Two ways to move: MIRROR - the caster's own moves a few ticks late, shifted by the copy's offset (run, jump,
 * sneak, swing); RUNNER - on along a straight course at the caster's speed, one swing on the way.
 * A victim's strike (client report {@link #hitBy}) or arrow takes one of the copy's hits; with none left it vanishes like a dashing
 * player (fx/illusion_poof, only to its victims). A copy's swing at a victim in reach is illusory damage.
 */
public final class Copies {
    private Copies() {}

    /** HUNTER («Сон бабочки»): walks up to its (only) victim on its own and strikes it now and then. */
    public enum Mode { MIRROR, RUNNER, HUNTER }

    /** One tick of the caster's moves. */
    private record Frame(Vec3 pos, float yaw, float pitch, int flags, String spell) {}

    public static final class Copy {
        public final int id;
        public final LivingEntity owner;
        public final Mode mode;
        public final Set<UUID> victims = new HashSet<>();
        Vec3 pos, offset, vel;
        float yaw, pitch;
        long until;
        int hits;
        final int maxHits, delay;
        int swingAt = -1, age, nextSwing = 20;
        /** illusory damage of its strike, how long until it comes back, the debt tag */
        public float damage;
        public int damageReturn, tag;
        /** strikes and arrows go through it as through air («Пелена») */
        public boolean ghost;
        boolean gone;

        Copy(int id, LivingEntity owner, Mode mode, Vec3 pos, int maxHits, int delay, long until) {
            this.id = id;
            this.owner = owner;
            this.mode = mode;
            this.pos = pos;
            this.maxHits = maxHits;
            this.delay = delay;
            this.until = until;
            this.yaw = owner.getYRot();
            this.pitch = owner.getXRot();
        }

        public Vec3 pos() {
            return pos;
        }

        public boolean gone() {
            return gone;
        }
    }

    private static final Map<UUID, List<Copy>> BY_OWNER = new HashMap<>();
    private static final Map<UUID, ArrayDeque<Frame>> HISTORY = new HashMap<>();
    /** victim -> game tick of its last strike at a copy */
    private static final Map<UUID, Long> LAST_HIT = new HashMap<>();
    private static int NEXT = 1;
    private static long now;
    private static final int HISTORY_LEN = 40;
    public static final int SWING = 1, JUMP = 2, SPRINT = 4, SNEAK = 8, CAST = 16;

    /** Hooks of the spells: what happens when a copy is gone (its spell may react). */
    private static final List<Consumer<Copy>> ON_GONE = new ArrayList<>();

    public static void onGone(Consumer<Copy> c) {
        ON_GONE.add(c);
    }

    static {
        // the voice for a victim: from the running copy («Ложный шаг»), else from the copy nearest to it («Отражения»); not from «Пелена»
        Voices.provider(out -> {
            for (List<Copy> l : BY_OWNER.values())
                for (Copy c : l) {
                    if (c.gone || c.ghost || !(c.owner.level() instanceof ServerLevel sl)) continue;
                    for (ServerPlayer v : players(sl, c)) {
                        Map<UUID, Vec3> m = out.get(c.owner.getUUID());
                        Vec3 had = m == null ? null : m.get(v.getUUID());
                        Vec3 at = c.pos.add(0, 1.6, 0);
                        if (had == null || c.mode == Mode.RUNNER || had.distanceToSqr(v.position()) > at.distanceToSqr(v.position()))
                            out.computeIfAbsent(c.owner.getUUID(), k -> new HashMap<>()).put(v.getUUID(), at);
                    }
                }
        });
    }

    /** A new copy of owner at pos for the victims; it lives ticks. delay - ticks behind the caster (MIRROR). */
    public static Copy spawn(LivingEntity owner, Mode mode, Vec3 pos, Vec3 vel, int ticks, int maxHits, int delay, List<ServerPlayer> victims) {
        Copy c = new Copy(NEXT++, owner, mode, pos, maxHits, delay, now + ticks);
        c.offset = pos.subtract(owner.position());
        c.vel = vel == null ? Vec3.ZERO : vel;
        if (mode == Mode.RUNNER) c.swingAt = Math.max(2, ticks / 2);
        BY_OWNER.computeIfAbsent(owner.getUUID(), k -> new ArrayList<>()).add(c);
        HISTORY.computeIfAbsent(owner.getUUID(), k -> new ArrayDeque<>());
        for (ServerPlayer p : victims) show(c, p);
        return c;
    }

    /** One more victim sees the copy (came close later). */
    public static void show(Copy c, ServerPlayer p) {
        if (c.gone || !c.victims.add(p.getUUID())) return;
        int left = (int) Math.max(1, c.until - now);
        Net.CH.send(PacketDistributor.PLAYER.with(() -> p), new IlluMsg(IlluMsg.COPY_SPAWN, c.owner.getId(), left, c.id, c.owner.getUUID(),
                c.owner.getName().getString(), c.pos.x, c.pos.y, c.pos.z, c.yaw, c.pitch));
    }

    public static List<Copy> of(LivingEntity owner) {
        List<Copy> l = BY_OWNER.get(owner.getUUID());
        return l == null ? List.of() : l;
    }

    /** Every copy of owner vanishes (poof). */
    public static void clear(LivingEntity owner) {
        for (Copy c : new ArrayList<>(of(owner))) gone(c);
    }

    /** The copy vanishes the way a dashing player does: the neutral poof, for its victims only. */
    public static void gone(Copy c) {
        if (c.gone) return;
        c.gone = true;
        List<Copy> l = BY_OWNER.get(c.owner.getUUID());
        if (l != null) l.remove(c);
        if (c.owner.level() instanceof ServerLevel sl)
            for (ServerPlayer p : players(sl, c)) {
                Net.CH.send(PacketDistributor.PLAYER.with(() -> p), new IlluMsg(IlluMsg.COPY_GONE, c.owner.getId(), 0, c.id, null, "", c.pos.x, c.pos.y, c.pos.z, 0, 0));
                ru.pohsmp.core.spell.illusion.IllusionBase.fx(sl, Fx.fx("illusion_poof").at(c.pos).only(p), "illusion_poof");
            }
        for (Consumer<Copy> h : ON_GONE) h.accept(c);
    }

    /** The caster and copy c swap places (no one sees it: the copy stands where the caster stood). */
    public static void swap(Copy c) {
        LivingEntity o = c.owner;
        Vec3 was = o.position(), to = c.pos;
        if (o instanceof ServerPlayer sp) sp.connection.teleport(to.x, to.y, to.z, sp.getYRot(), sp.getXRot());
        else o.teleportTo(to.x, to.y, to.z);
        Vec3 delta = to.subtract(was);
        ArrayDeque<Frame> h = HISTORY.get(o.getUUID());
        if (h != null) {   // the copies keep their places: the history moves with the caster
            ArrayDeque<Frame> moved = new ArrayDeque<>();
            for (Frame f : h) moved.addLast(new Frame(f.pos().add(delta), f.yaw(), f.pitch(), f.flags(), f.spell()));
            HISTORY.put(o.getUUID(), moved);
        }
        for (Copy x : of(o)) if (x.mode == Mode.MIRROR) x.offset = x.offset.subtract(delta);
        c.offset = was.subtract(to);
        c.pos = was;
    }

    private static List<ServerPlayer> players(ServerLevel sl, Copy c) {
        List<ServerPlayer> out = new ArrayList<>();
        for (UUID id : c.victims) {
            ServerPlayer p = sl.getServer().getPlayerList().getPlayer(id);
            if (p != null && p.level() == sl) out.add(p);
        }
        return out;
    }

    /** The hitbox of a copy (a standing player). */
    public static AABB box(Copy c) {
        return new AABB(c.pos.x - 0.3, c.pos.y, c.pos.z - 0.3, c.pos.x + 0.3, c.pos.y + 1.8, c.pos.z + 0.3);
    }

    /** A victim's client says it struck copy id (vanilla click or Epic Fight swing in front of it). */
    public static void hitBy(ServerPlayer p, int id) {
        long last = LAST_HIT.getOrDefault(p.getUUID(), -100L);
        if (now - last < 8) return;
        for (List<Copy> l : BY_OWNER.values())
            for (Copy c : l) {
                if (c.id != id || c.ghost || !c.victims.contains(p.getUUID()) || p.level() != c.owner.level()) continue;
                if (p.getEyePosition().distanceTo(box(c).getCenter()) > 6) return;
                LAST_HIT.put(p.getUUID(), now);
                hurt(c, p.getYRot());
                return;
            }
    }

    private static void hurt(Copy c, float fromYaw) {
        c.hits++;
        if (c.owner.level() instanceof ServerLevel sl)
            for (ServerPlayer v : players(sl, c))
                Net.CH.send(PacketDistributor.PLAYER.with(() -> v), new IlluMsg(IlluMsg.COPY_HURT, c.owner.getId(), 0, c.id, null, "", c.pos.x, c.pos.y, c.pos.z, fromYaw, 0));
        if (c.hits >= c.maxHits) gone(c);
    }

    // ---------------------------------------------------------------- tick

    private static int flags(LivingEntity o) {
        int f = 0;
        if (o.swinging && o.swingTime == 0) f |= SWING;
        if (!o.onGround() && o.getDeltaMovement().y > 0.05) f |= JUMP;
        if (o.isSprinting()) f |= SPRINT;
        if (o.isShiftKeyDown() || o.getPose() == Pose.CROUCHING) f |= SNEAK;
        if (o instanceof ServerPlayer sp && io.redspace.ironsspellbooks.api.magic.MagicData.getPlayerMagicData(sp).isCasting()) f |= CAST;
        return f;
    }

    @SubscribeEvent
    public static void onTick(TickEvent.ServerTickEvent e) {
        if (e.phase != TickEvent.Phase.END) return;
        now++;
        if (BY_OWNER.isEmpty()) return;
        for (var it = BY_OWNER.entrySet().iterator(); it.hasNext(); ) {
            var en = it.next();
            List<Copy> l = en.getValue();
            if (l.isEmpty()) {
                it.remove();
                HISTORY.remove(en.getKey());
                continue;
            }
            LivingEntity o = l.get(0).owner;
            if (o.isRemoved() || !o.isAlive()) {
                for (Copy c : new ArrayList<>(l)) gone(c);
                continue;
            }
            ArrayDeque<Frame> h = HISTORY.computeIfAbsent(en.getKey(), k -> new ArrayDeque<>());
            int fl = flags(o);
            String spell = (fl & CAST) != 0 && o instanceof ServerPlayer sp
                    ? io.redspace.ironsspellbooks.api.magic.MagicData.getPlayerMagicData(sp).getCastingSpellId() : "";
            h.addFirst(new Frame(o.position(), o.getYHeadRot(), o.getXRot(), fl, spell == null ? "" : spell));
            while (h.size() > HISTORY_LEN) h.removeLast();
            for (Copy c : new ArrayList<>(l)) step((ServerLevel) o.level(), c, h);
        }
    }

    private static void step(ServerLevel sl, Copy c, ArrayDeque<Frame> h) {
        c.age++;
        if (now >= c.until) {
            gone(c);
            return;
        }
        int fl = 0;
        String spell = "";
        if (c.mode == Mode.MIRROR) {
            Frame f = frame(h, c.delay);
            Vec3 want = f.pos().add(c.offset);
            double rise = f.pos().y - floor(sl, f.pos(), f.pos().y);   // how high the caster is above its own floor (a jump)
            double fy = floor(sl, want, want.y);
            Vec3 next = new Vec3(want.x, fy + Math.max(0, rise), want.z);
            if (!free(sl, next)) next = c.pos;   // a wall: the copy waits rather than walking into it
            c.pos = next;
            c.yaw = f.yaw();
            c.pitch = f.pitch();
            fl = f.flags();
            spell = f.spell();   // the client sends a harmless bolt of this school's colour when the copy's cast ends
        } else if (c.mode == Mode.HUNTER) {
            fl = hunt(sl, c);
        } else {
            Vec3 next = c.pos.add(c.vel.x, 0, c.vel.z);
            double fy = floor(sl, next, c.pos.y);
            next = new Vec3(next.x, fy, next.z);
            if (free(sl, next)) c.pos = next;
            fl = (c.owner.isSprinting() ? SPRINT : 0) | (c.age == c.swingAt ? SWING : 0);
        }
        for (ServerPlayer p : players(sl, c))
            Net.CH.send(PacketDistributor.PLAYER.with(() -> p), new IlluMsg(IlluMsg.COPY_MOVE, c.owner.getId(), fl, c.id, null, spell, c.pos.x, c.pos.y, c.pos.z, c.yaw, c.pitch));
        if ((fl & SWING) != 0 && c.damage > 0) strike(sl, c);
        if (!c.ghost) arrows(sl, c);
    }

    /** HUNTER: a step towards its victim (stops 2 blocks off), a swing every ~1-1.6 s in reach. */
    private static int hunt(ServerLevel sl, Copy c) {
        List<ServerPlayer> ps = players(sl, c);
        if (ps.isEmpty()) return 0;
        ServerPlayer t = ps.get(0);
        Vec3 to = t.position().subtract(c.pos);
        double dist = Math.sqrt(to.x * to.x + to.z * to.z);
        int fl = 0;
        if (dist > 1e-3) c.yaw = (float) Math.toDegrees(Math.atan2(-to.x, to.z));
        c.pitch = (float) -Math.toDegrees(Math.atan2(t.getEyeY() - (c.pos.y + 1.62), Math.max(0.5, dist))) * 0.5f;
        if (dist > 2.0) {
            double step = Math.min(dist - 2.0, 0.26);
            Vec3 next = c.pos.add(to.x / dist * step, 0, to.z / dist * step);
            next = new Vec3(next.x, floor(sl, next, c.pos.y), next.z);
            if (!free(sl, next)) {   // a block in the way: one hop up it
                Vec3 up = new Vec3(next.x, floor(sl, next, c.pos.y + 1.1), next.z);
                if (up.y - c.pos.y <= 1.25 && free(sl, up)) {
                    next = up;
                    fl |= JUMP;
                } else next = null;
            }
            if (next != null) {
                c.pos = next;
                fl |= SPRINT;
            }
        }
        if (dist <= 3.0 && Math.abs(to.y) < 2.5 && c.age >= c.nextSwing) {
            fl |= SWING;
            c.nextSwing = c.age + 20 + sl.random.nextInt(13);
        }
        return fl;
    }

    /** A copy's swing: illusory damage to a victim in reach in front of it. */
    private static void strike(ServerLevel sl, Copy c) {
        Vec3 look = Vec3.directionFromRotation(0, c.yaw);
        for (ServerPlayer p : players(sl, c)) {
            Vec3 to = p.position().subtract(c.pos);
            double d = to.length();
            if (d > 3.2 || d < 1e-3 || to.normalize().dot(look) < 0.4) continue;
            Illusions.illusory(c.owner, p, c.damage, c.damageReturn, c.tag);
        }
    }

    /** A victim's arrow or bolt that flies into the copy: it is taken (the copy flinches), others' fly through. */
    private static void arrows(ServerLevel sl, Copy c) {
        AABB b = box(c);
        for (Projectile pr : sl.getEntitiesOfClass(Projectile.class, b.inflate(1.5))) {
            Entity shooter = pr.getOwner();
            if (shooter == null || !c.victims.contains(shooter.getUUID())) continue;
            Vec3 a = pr.position(), z = a.add(pr.getDeltaMovement());
            if (!b.contains(a) && b.clip(a, z).isEmpty()) continue;
            pr.discard();
            hurt(c, shooter.getYRot());
            if (c.gone) return;
        }
    }

    private static Frame frame(ArrayDeque<Frame> h, int back) {
        int i = 0;
        Frame last = h.peekFirst();
        for (Frame f : h) {
            last = f;
            if (i++ >= back) break;
        }
        return last;
    }

    /** Top of the floor under p (from a bit above around down to 4 below); around itself if nothing. */
    private static double floor(ServerLevel sl, Vec3 p, double around) {
        int x = net.minecraft.util.Mth.floor(p.x), z = net.minecraft.util.Mth.floor(p.z);
        int top = net.minecraft.util.Mth.floor(around + 1.2);
        BlockPos.MutableBlockPos bp = new BlockPos.MutableBlockPos();
        for (int y = top; y > top - 6; y--) {
            bp.set(x, y, z);
            var shape = sl.getBlockState(bp).getCollisionShape(sl, bp);
            if (shape.isEmpty()) continue;
            double surface = y + shape.max(net.minecraft.core.Direction.Axis.Y);
            if (surface <= around + 1.2) return surface;
        }
        return around;
    }

    private static boolean free(ServerLevel sl, Vec3 p) {
        return sl.noCollision(new AABB(p.x - 0.3, p.y + 0.01, p.z - 0.3, p.x + 0.3, p.y + 1.8, p.z + 0.3));
    }

    // ---------------------------------------------------------------- events

    @SubscribeEvent
    public static void onDeath(LivingDeathEvent e) {
        if (!e.getEntity().level().isClientSide) clear(e.getEntity());
    }

    @SubscribeEvent
    public static void onLogout(PlayerEvent.PlayerLoggedOutEvent e) {
        clear(e.getEntity());
        LAST_HIT.remove(e.getEntity().getUUID());
    }

    @SubscribeEvent
    public static void onDimension(PlayerEvent.PlayerChangedDimensionEvent e) {
        clear(e.getEntity());
    }

    @SubscribeEvent
    public static void onStopping(ServerStoppingEvent e) {
        BY_OWNER.clear();
        HISTORY.clear();
        LAST_HIT.clear();
    }
}
