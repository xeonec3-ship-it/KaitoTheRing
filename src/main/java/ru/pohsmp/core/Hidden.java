package ru.pohsmp.core;

import com.mojang.brigadier.arguments.DoubleArgumentType;
import java.util.ArrayList;
import java.util.Collection;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.EntityArgument;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.phys.EntityHitResult;
import net.minecraft.world.phys.Vec3;
import net.minecraft.world.scores.PlayerTeam;
import net.minecraft.world.scores.Scoreboard;
import net.minecraft.world.scores.Team;
import net.minecraftforge.event.RegisterCommandsEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.ProjectileImpactEvent;
import net.minecraftforge.event.entity.living.LivingAttackEvent;
import net.minecraftforge.event.entity.living.LivingChangeTargetEvent;
import net.minecraftforge.event.entity.player.AttackEntityEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.event.entity.player.PlayerInteractEvent;
import net.minecraftforge.event.server.ServerStartedEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.network.PacketDistributor;
import ru.pohsmp.core.net.HideMsg;
import ru.pohsmp.core.net.Net;

/**
 * Hides any entity (players, mobs, CustomNPCs NPCs) from every viewer: the clients skip drawing it entirely (model, armour, held items,
 * name tag; client/HiddenEntities), the server keeps vanilla invisibility on it so no shadow is drawn and mobs barely see it.
 * Clients that start tracking the entity later get the hide packet too, so relogging or walking up does not reveal it.
 *
 * <p>Options: noDamage cancels all damage and melee hits; noCollide stops pushing (a scoreboard team with collision "never",
 * only if the entity is in no team of its own), projectile hits and right-click interaction; freeze keeps it where it was hidden
 * (by default mobs and NPCs, not players; hide again or {@link #moveTo} for a new spot). Fire on a hidden entity is put out.
 * Damage that bypasses invulnerability (/kill, the void) still goes through.
 */
public final class Hidden {
    private Hidden() {}

    /** Team without collisions for noCollide (added only to entities in no team). */
    public static final String TEAM = "pohsmp_hidden";
    /** Long enough to mean "until shown" (about 24 days), for callers that want a number. */
    public static final int FOREVER = Integer.MAX_VALUE / 100;

    private static final class State {
        Entity entity;
        long until;
        final boolean noDamage, noCollide, freeze;
        Vec3 anchor;
        boolean teamed;

        State(Entity e, long until, boolean noDamage, boolean noCollide, boolean freeze) {
            this.entity = e;
            this.until = until;
            this.noDamage = noDamage;
            this.noCollide = noCollide;
            this.freeze = freeze;
            this.anchor = e.position();
        }
    }

    private static final Map<UUID, State> HIDDEN = new HashMap<>();
    private static long now;

    /** Hides for ticks (&lt;= 0: until {@link #show}), no damage, no collisions. */
    public static void hide(Entity e, int ticks) {
        hide(e, ticks, true, true);
    }

    /** Hides e for ticks (&lt;= 0: until {@link #show}); mobs and NPCs are held in place, players are not. */
    public static void hide(Entity e, int ticks, boolean noDamage, boolean noCollide) {
        hide(e, ticks, noDamage, noCollide, !(e instanceof Player));
    }

    /** Hides e for ticks (&lt;= 0: until {@link #show}); hiding again renews the time, the options and the spot it is held at. */
    public static void hide(Entity e, int ticks, boolean noDamage, boolean noCollide, boolean freeze) {
        if (e == null || e.level().isClientSide || !(e.level() instanceof ServerLevel)) return;
        State old = HIDDEN.get(e.getUUID());
        if (old != null && old.teamed && !noCollide) leaveTeam(old);
        State s = new State(e, ticks > 0 ? now + ticks : Long.MAX_VALUE, noDamage, noCollide, freeze);
        if (old != null) s.teamed = old.teamed && noCollide;
        HIDDEN.put(e.getUUID(), s);
        if (noCollide && !s.teamed) joinTeam(s);
        apply(s);
        send(e, PacketDistributor.TRACKING_ENTITY_AND_SELF.with(() -> e), remaining(s));
    }

    public static void show(Entity e) {
        if (e == null) return;
        State s = HIDDEN.remove(e.getUUID());
        if (s != null) release(e);
        else if (!e.level().isClientSide) send(e, PacketDistributor.TRACKING_ENTITY_AND_SELF.with(() -> e), 0);
    }

    /** Where a frozen hidden entity is held from now on (e.g. after the caller moved it). */
    public static void moveTo(Entity e, Vec3 p) {
        State s = e == null ? null : HIDDEN.get(e.getUUID());
        if (s != null) s.anchor = p;
    }

    public static boolean isHidden(Entity e) {
        return e != null && HIDDEN.containsKey(e.getUUID());
    }

    /** Ticks left (-1 = until shown, 0 = not hidden). */
    public static int remaining(Entity e) {
        State s = e == null ? null : HIDDEN.get(e.getUUID());
        return s == null ? 0 : remaining(s);
    }

    private static int remaining(State s) {
        return s.until == Long.MAX_VALUE ? -1 : (int) Math.max(1, Math.min(Integer.MAX_VALUE, s.until - now));
    }

    private static void send(Entity e, PacketDistributor.PacketTarget to, int ticks) {
        Net.CH.send(to, new HideMsg(e.getId(), ticks));
    }

    private static void release(Entity e) {
        if (e instanceof LivingEntity le) le.setInvisible(le.hasEffect(MobEffects.INVISIBILITY));
        else e.setInvisible(false);
        if (!e.isRemoved()) send(e, PacketDistributor.TRACKING_ENTITY_AND_SELF.with(() -> e), 0);
        leaveTeam(e);
    }

    /** Every tick while hidden: invisibility (no particles, no icon: only the shared flag), no fire, held in place if frozen. */
    private static void apply(State s) {
        Entity e = s.entity;
        if (!e.isInvisible()) e.setInvisible(true);
        if (e.getRemainingFireTicks() > 0) e.clearFire();
        e.fallDistance = 0;
        if (!s.freeze) return;
        Vec3 a = s.anchor;
        if (e instanceof ServerPlayer sp) {
            if (sp.position().distanceToSqr(a) > 0.0025) sp.connection.teleport(a.x, a.y, a.z, sp.getYRot(), sp.getXRot());
            return;
        }
        if (e instanceof Mob m) {
            m.getNavigation().stop();
            m.setTarget(null);
        }
        if (e instanceof LivingEntity le) {
            le.xxa = 0;
            le.zza = 0;
            le.setJumping(false);
        }
        e.setDeltaMovement(Vec3.ZERO);
        if (e.position().distanceToSqr(a) > 0.0025) e.teleportTo(a.x, a.y, a.z);
    }

    // ---------------------------------------------------------------- team without collisions

    private static void joinTeam(State s) {
        Scoreboard sb = s.entity.level().getScoreboard();
        String name = s.entity.getScoreboardName();
        if (sb.getPlayersTeam(name) != null) return;   // the entity has its own team: leave it be
        PlayerTeam t = sb.getPlayerTeam(TEAM);
        if (t == null) {
            t = sb.addPlayerTeam(TEAM);
            t.setCollisionRule(Team.CollisionRule.NEVER);
            t.setNameTagVisibility(Team.Visibility.NEVER);
            t.setSeeFriendlyInvisibles(false);
        }
        sb.addPlayerToTeam(name, t);
        s.teamed = true;
    }

    private static void leaveTeam(State s) {
        leaveTeam(s.entity);
        s.teamed = false;
    }

    private static void leaveTeam(Entity e) {
        Scoreboard sb = e.level().getScoreboard();
        PlayerTeam t = sb.getPlayerTeam(TEAM);
        if (t != null && t.getPlayers().contains(e.getScoreboardName())) sb.removePlayerFromTeam(e.getScoreboardName(), t);
    }

    /** The entity object behind s now: a non-player that changed dimension is a new object with the same UUID. */
    private static Entity resolve(MinecraftServer server, State s) {
        if (!s.entity.isRemoved()) return s.entity;
        if (s.entity.getRemovalReason() != Entity.RemovalReason.CHANGED_DIMENSION) return null;
        for (ServerLevel l : server.getAllLevels()) {
            Entity e = l.getEntity(s.entity.getUUID());
            if (e != null && !e.isRemoved()) return e;
        }
        return s.entity;   // not added to its new level yet: try next tick
    }

    // ---------------------------------------------------------------- events

    @SubscribeEvent
    public static void onTick(TickEvent.ServerTickEvent e) {
        if (e.phase != TickEvent.Phase.END) return;
        now++;
        if (HIDDEN.isEmpty()) return;
        for (var it = HIDDEN.entrySet().iterator(); it.hasNext(); ) {
            State s = it.next().getValue();
            Entity cur = resolve(e.getServer(), s);
            if (cur == null) {   // dead or unloaded: nothing to restore on the client, the entity is gone there
                it.remove();
                if (s.teamed) leaveTeam(s.entity);
                continue;
            }
            if (cur != s.entity) {   // changed dimension: the new object takes over, hidden where it arrived
                s.entity = cur;
                s.anchor = cur.position();
            }
            if (cur.isRemoved()) continue;
            if (now >= s.until) {
                it.remove();
                release(cur);
                continue;
            }
            apply(s);
        }
    }

    /** A viewer that starts seeing a hidden entity (walked up, relogged, changed dimension) is told at once. */
    @SubscribeEvent
    public static void onStartTracking(PlayerEvent.StartTracking e) {
        State s = HIDDEN.get(e.getTarget().getUUID());
        if (s == null || !(e.getEntity() instanceof ServerPlayer sp)) return;
        if (s.entity != e.getTarget() && s.entity.isRemoved()) s.entity = e.getTarget();
        send(e.getTarget(), PacketDistributor.PLAYER.with(() -> sp), remaining(s));
    }

    /** A hidden player's own client after a relog, respawn or dimension change. */
    @SubscribeEvent
    public static void onLogin(PlayerEvent.PlayerLoggedInEvent e) {
        resendSelf(e.getEntity());
    }

    @SubscribeEvent
    public static void onRespawn(PlayerEvent.PlayerRespawnEvent e) {
        resendSelf(e.getEntity());
    }

    @SubscribeEvent
    public static void onDimension(PlayerEvent.PlayerChangedDimensionEvent e) {
        resendSelf(e.getEntity());
    }

    private static void resendSelf(Player p) {
        State s = HIDDEN.get(p.getUUID());
        if (s == null || !(p instanceof ServerPlayer sp)) return;
        s.entity = sp;
        send(sp, PacketDistributor.PLAYER.with(() -> sp), remaining(s));
    }

    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void onAttack(LivingAttackEvent e) {
        if (HIDDEN.isEmpty()) return;
        State s = HIDDEN.get(e.getEntity().getUUID());
        if (s != null && s.noDamage && !e.getSource().is(net.minecraft.tags.DamageTypeTags.BYPASSES_INVULNERABILITY)) e.setCanceled(true);
    }

    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void onMelee(AttackEntityEvent e) {
        if (HIDDEN.isEmpty()) return;
        State s = HIDDEN.get(e.getTarget().getUUID());
        if (s != null && s.noDamage) e.setCanceled(true);
    }

    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void onInteract(PlayerInteractEvent.EntityInteract e) {
        if (!HIDDEN.isEmpty() && noCollide(e.getTarget())) e.setCanceled(true);
    }

    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void onInteractAt(PlayerInteractEvent.EntityInteractSpecific e) {
        if (!HIDDEN.isEmpty() && noCollide(e.getTarget())) e.setCanceled(true);
    }

    /** Projectiles fly through a hidden entity. */
    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void onProjectile(ProjectileImpactEvent e) {
        if (!HIDDEN.isEmpty() && e.getRayTraceResult() instanceof EntityHitResult h && noCollide(h.getEntity()))
            e.setImpactResult(ProjectileImpactEvent.ImpactResult.SKIP_ENTITY);
    }

    /** Mobs do not pick a hidden entity as their target. */
    @SubscribeEvent
    public static void onTarget(LivingChangeTargetEvent e) {
        if (!HIDDEN.isEmpty() && e.getNewTarget() != null && HIDDEN.containsKey(e.getNewTarget().getUUID())) e.setCanceled(true);
    }

    private static boolean noCollide(Entity e) {
        State s = e == null ? null : HIDDEN.get(e.getUUID());
        return s != null && s.noCollide;
    }

    /** A crash while something was hidden leaves names in the team: clear it on start. */
    @SubscribeEvent
    public static void onStarted(ServerStartedEvent e) {
        Scoreboard sb = e.getServer().getScoreboard();
        PlayerTeam t = sb.getPlayerTeam(TEAM);
        if (t != null) sb.removePlayerTeam(t);
    }

    @SubscribeEvent
    public static void onStopping(ServerStoppingEvent e) {
        for (State s : new ArrayList<>(HIDDEN.values())) if (!s.entity.isRemoved()) release(s.entity);
        HIDDEN.clear();
    }

    // ---------------------------------------------------------------- commands

    @SubscribeEvent
    public static void onCommands(RegisterCommandsEvent e) {
        e.getDispatcher().register(Commands.literal("pohsmp").requires(s -> s.hasPermission(2))
                .then(Commands.literal("hide").then(Commands.argument("targets", EntityArgument.entities())
                        .executes(c -> hideCmd(c.getSource(), EntityArgument.getEntities(c, "targets"), 0))
                        .then(Commands.argument("seconds", DoubleArgumentType.doubleArg(0, 86400))
                                .executes(c -> hideCmd(c.getSource(), EntityArgument.getEntities(c, "targets"),
                                        DoubleArgumentType.getDouble(c, "seconds"))))))
                .then(Commands.literal("show").then(Commands.argument("targets", EntityArgument.entities())
                        .executes(c -> showCmd(c.getSource(), EntityArgument.getEntities(c, "targets"))))));
    }

    /** seconds 0 = until /pohsmp show. */
    private static int hideCmd(CommandSourceStack src, Collection<? extends Entity> targets, double seconds) {
        int ticks = (int) Math.round(seconds * 20);
        for (Entity e : targets) hide(e, ticks);
        int n = targets.size();
        src.sendSuccess(() -> Component.literal("Hidden: " + n + (ticks > 0 ? " for " + seconds + " s" : " until /pohsmp show")), true);
        return n;
    }

    private static int showCmd(CommandSourceStack src, Collection<? extends Entity> targets) {
        List<Entity> shown = new ArrayList<>();
        for (Entity e : targets) {
            if (isHidden(e)) shown.add(e);
            show(e);
        }
        int n = shown.size();
        src.sendSuccess(() -> Component.literal("Shown: " + n), true);
        return n;
    }
}
