package ru.pohsmp.core;

import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;
import java.util.UUID;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.phys.Vec3;
import net.minecraft.world.scores.PlayerTeam;
import net.minecraft.world.scores.Scoreboard;
import net.minecraft.world.scores.Team;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.living.LivingAttackEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.network.PacketDistributor;
import ru.pohsmp.core.net.HideMsg;
import ru.pohsmp.core.net.Net;

/**
 * Hides any entity from everyone (T01): clients skip its model, armour, held items, name and shadow ({@code client/HiddenEntities}).
 * Works for CustomNPCs NPCs, which ignore invisibility when drawn. Players who start tracking it later are told too.
 * Options: no damage, no collisions (a scoreboard team with collision NEVER, only if it has no team), frozen in place.
 */
public final class Hidden {
    private Hidden() {}

    private static final class Entry {
        long until;
        boolean noDamage, noCollide, freeze;
        Vec3 pos;
        String team;
    }

    private static final Map<UUID, Entry> ALL = new HashMap<>();
    private static final String TEAM = "pohsmp_hidden";
    /** Long enough to mean "until shown" (about 24 days). */
    public static final int FOREVER = Integer.MAX_VALUE / 100;

    public static boolean isHidden(Entity e) {
        return e != null && ALL.containsKey(e.getUUID());
    }

    /** Hides e for ticks (≤ 0: until {@link #show}). */
    public static void hide(Entity e, int ticks, boolean noDamage, boolean noCollide, boolean freeze) {
        if (e == null || !(e.level() instanceof ServerLevel sl)) return;
        int t = ticks <= 0 ? FOREVER : ticks;
        Entry en = ALL.computeIfAbsent(e.getUUID(), u -> new Entry());
        en.until = sl.getServer().getTickCount() + (long) t;
        en.noDamage = noDamage;
        en.noCollide = noCollide;
        en.freeze = freeze;
        en.pos = e.position();
        if (noCollide && en.team == null && e.getTeam() == null) {
            Scoreboard sb = sl.getScoreboard();
            PlayerTeam pt = sb.getPlayerTeam(TEAM);
            if (pt == null) {
                pt = sb.addPlayerTeam(TEAM);
                pt.setCollisionRule(Team.CollisionRule.NEVER);
                pt.setNameTagVisibility(Team.Visibility.NEVER);
            }
            sb.addPlayerToTeam(e.getScoreboardName(), pt);
            en.team = TEAM;
        }
        quiet(e);
        send(e, t);
    }

    public static void hide(Entity e, int ticks) {
        hide(e, ticks, false, false, false);
    }

    public static void show(Entity e) {
        if (e == null) return;
        Entry en = ALL.remove(e.getUUID());
        if (en == null) return;
        release(e, en);
        send(e, 0);
    }

    /** Where a frozen hidden entity is kept (e.g. after the caller moved it). */
    public static void moveTo(Entity e, Vec3 p) {
        Entry en = e == null ? null : ALL.get(e.getUUID());
        if (en != null) en.pos = p;
    }

    private static void release(Entity e, Entry en) {
        if (en.team != null && e.level() instanceof ServerLevel sl) {
            PlayerTeam pt = sl.getScoreboard().getPlayerTeam(en.team);
            if (pt != null && e.getTeam() == pt) sl.getScoreboard().removePlayerFromTeam(e.getScoreboardName(), pt);
        }
    }

    /** Things the client draws regardless of the renderer: fire on it, the glowing outline. */
    private static void quiet(Entity e) {
        if (e.getRemainingFireTicks() > 0) e.clearFire();
        if (e.hasGlowingTag()) e.setGlowingTag(false);
    }

    private static void send(Entity e, int ticks) {
        HideMsg m = new HideMsg(e.getId(), ticks);
        Net.CH.send(PacketDistributor.TRACKING_ENTITY_AND_SELF.with(() -> e), m);
    }

    private static Entity find(MinecraftServer srv, UUID u) {
        ServerPlayer p = srv.getPlayerList().getPlayer(u);
        if (p != null) return p;
        for (ServerLevel l : srv.getAllLevels()) {
            Entity e = l.getEntity(u);
            if (e != null) return e;
        }
        return null;
    }

    public static final class HiddenEvents {
        private HiddenEvents() {}

        @SubscribeEvent
        public static void onTick(TickEvent.ServerTickEvent ev) {
            if (ev.phase != TickEvent.Phase.END || ALL.isEmpty()) return;
            MinecraftServer srv = net.minecraftforge.server.ServerLifecycleHooks.getCurrentServer();
            if (srv == null) return;
            long now = srv.getTickCount();
            for (Iterator<Map.Entry<UUID, Entry>> it = ALL.entrySet().iterator(); it.hasNext();) {
                var me = it.next();
                Entry en = me.getValue();
                Entity e = find(srv, me.getKey());
                if (now >= en.until) {
                    it.remove();
                    if (e != null) {
                        release(e, en);
                        send(e, 0);
                    }
                    continue;
                }
                if (e == null) continue;   // unloaded or gone for now: kept until it expires
                quiet(e);
                if (en.freeze && en.pos != null) {
                    e.setDeltaMovement(Vec3.ZERO);
                    e.fallDistance = 0;
                    if (e.position().distanceToSqr(en.pos) > 1e-4) {
                        if (e instanceof ServerPlayer sp) sp.connection.teleport(en.pos.x, en.pos.y, en.pos.z, sp.getYRot(), sp.getXRot());
                        else e.teleportTo(en.pos.x, en.pos.y, en.pos.z);
                    }
                }
            }
        }

        /** A player who starts seeing a hidden entity (came near, relogged, it changed dimension) is told at once. */
        @SubscribeEvent
        public static void onStartTracking(PlayerEvent.StartTracking ev) {
            Entry en = ALL.get(ev.getTarget().getUUID());
            if (en == null || !(ev.getEntity() instanceof ServerPlayer sp)) return;
            long left = en.until - sp.getServer().getTickCount();
            if (left > 0) Net.CH.send(PacketDistributor.PLAYER.with(() -> sp), new HideMsg(ev.getTarget().getId(), (int) Math.min(left, FOREVER)));
        }

        /** The hidden player sees his own state too after a relog or a dimension change. */
        @SubscribeEvent
        public static void onLogin(PlayerEvent.PlayerLoggedInEvent ev) {
            resendSelf(ev.getEntity());
        }

        @SubscribeEvent
        public static void onChangeDim(PlayerEvent.PlayerChangedDimensionEvent ev) {
            resendSelf(ev.getEntity());
        }

        private static void resendSelf(Entity e) {
            Entry en = ALL.get(e.getUUID());
            if (en != null && e instanceof ServerPlayer sp) {
                long left = en.until - sp.getServer().getTickCount();
                if (left > 0) send(sp, (int) Math.min(left, FOREVER));
            }
        }

        @SubscribeEvent(priority = EventPriority.HIGH)
        public static void onAttack(LivingAttackEvent ev) {
            LivingEntity t = ev.getEntity();
            Entry en = ALL.get(t.getUUID());
            if (en != null && en.noDamage && !ev.getSource().is(net.minecraft.tags.DamageTypeTags.BYPASSES_INVULNERABILITY)) ev.setCanceled(true);
        }

        @SubscribeEvent
        public static void onStop(ServerStoppingEvent ev) {
            for (var me : ALL.entrySet()) {
                Entity e = find(ev.getServer(), me.getKey());
                if (e != null) release(e, me.getValue());
            }
            ALL.clear();
        }
    }
}
