package ru.pohsmp.core.spell;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.tags.DamageTypeTags;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.living.LivingAttackEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.network.PacketDistributor;
import ru.pohsmp.core.net.Net;

/**
 * Cast cutscenes of the great spells (client: DownfallCut). Every player within R of the caster is frozen in place,
 * cannot be hurt and watches the scene until it ends (or the cast stops). Scenes: 0 Downfall, 1 Milky Way, 2 Soul Devour, 3 Divine Taboo,
 * 4 Closing of Space, 5 Coven Arrival, 6 Star Fall, 7 Gate, 8 Soul Seal, 9 Blessing.
 */
public final class Cutscene {
    private Cutscene() {}

    public static final double R = 64;
    /** Coven Arrival: watchers within this of the arena and of the caster (the other scenes use R). */
    public static final double R_COVEN = 98;
    /** «Безмолвные врата»: camera, music and silence for everyone this close to the caster or the strike point (owner 19.11, was 64). */
    public static final double R_GATE = 128;
    public static final int DOWNFALL = 0, MILKY_WAY = 1, SOUL_DEVOUR = 2, TABOO = 3, SPACE_CLOSURE = 4, COVEN_ARRIVAL = 5, STAR_FALL = 6, SILENT_GATE = 7,
            SOUL_SEAL = 8, BLESSING = 9,   // T21: i of the packet = the target's entity id
            BUTTERFLY_DREAM = 10,          // T22: focus = 5 blocks ahead of the caster (the way it looked when it began)
            WORLD_TREE = 11,               // T23: focus = the tree's foot
            ABYSS_EYE = 12,                // T23: focus = the eye in the sky
            LAST_DAWN = 13,                // T23: focus = the sunrise point on the horizon
            ERASED_NAME = 14;              // T24: focus = the target, i = the target's entity id

    /**
     * Starts the scene for everyone within r of the caster (in the caster's level) or of `extra` in `extraLevel` (may be another dimension).
     * The packet carries the caster's entity id: on clients in the other level that entity is unknown, the client copes with it.
     */
    public static List<UUID> start(ServerLevel sl, LivingEntity caster, int key, int scene, int dur, Vec3 focus, double ang, double r,
                                   ServerLevel extraLevel, Vec3 extra) {
        return start(sl, caster, key, scene, dur, focus, ang, r, extraLevel, extra, java.util.Set.of());
    }

    /** The same, and the players in `also` watch (and are held) wherever they are (Coven Arrival: the retinue, owner 19.11). */
    public static List<UUID> start(ServerLevel sl, LivingEntity caster, int key, int scene, int dur, Vec3 focus, double ang, double r,
                                   ServerLevel extraLevel, Vec3 extra, java.util.Set<UUID> also) {
        List<UUID> watchers = new ArrayList<>();
        long until = sl.getGameTime() + dur + 60;
        Net.HFx cut = new Net.HFx(Net.HFx.CUT, key, caster.getId(), scene, dur, focus.x, focus.y, focus.z, ang, 0);
        for (ServerPlayer sp : sl.getServer().getPlayerList().getPlayers()) {
            if (sp.isSpectator()) continue;
            boolean near = sp.level() == sl && sp.distanceToSqr(caster) <= r * r
                    || extraLevel != null && sp.level() == extraLevel && sp.position().distanceToSqr(extra) <= r * r
                    || also.contains(sp.getUUID());
            if (!near) continue;
            Frozen f = new Frozen();
            f.pos = sp.position();
            f.until = until;
            f.caster = caster.getUUID();
            FROZEN.put(sp.getUUID(), f);
            watchers.add(sp.getUUID());
            Net.CH.send(PacketDistributor.PLAYER.with(() -> sp), cut);
        }
        return watchers;
    }

    /** A frozen player was moved by the spell: hold them at the new place instead of pulling them back. */
    public static void refreeze(ServerPlayer sp, Vec3 pos) {
        Frozen f = FROZEN.get(sp.getUUID());
        if (f == null) return;
        f.pos = pos;
        f.walkUntil = 0;   // moved by the spell: a walk of its own is over
    }

    /** The same, and the body faces yaw (a walk led by the spell: the player's own mouse is locked in the scene). */
    public static void refreeze(ServerPlayer sp, Vec3 pos, float yaw) {
        Frozen f = FROZEN.get(sp.getUUID());
        if (f == null || sp.level().getGameTime() < f.walkUntil) return;   // a walk of its own holds the goal itself
        f.pos = pos;
        f.yaw = yaw;
    }

    /**
     * A frozen player walks to `to` by itself within ticks (its client: ScriptedWalk), facing yaw at the end: the freeze lets it move
     * meanwhile and holds it at the goal afterwards (a client that could not walk is put there then).
     */
    public static void walk(ServerPlayer sp, Vec3 to, int ticks, float yaw) {
        Frozen f = FROZEN.get(sp.getUUID());
        if (f == null) return;
        f.pos = to;
        f.yaw = yaw;
        f.walkUntil = sp.level().getGameTime() + ticks + 6;
        Net.CH.send(PacketDistributor.PLAYER.with(() -> sp),
                new ru.pohsmp.core.net.IlluMsg(ru.pohsmp.core.net.IlluMsg.WALK, sp.getId(), ticks, 0, null, "", to.x, to.y, to.z, yaw, 0));
    }

    /** True while a frozen player walks by itself (Cutscene.walk). */
    public static boolean walking(ServerPlayer sp) {
        Frozen f = FROZEN.get(sp.getUUID());
        return f != null && sp.level().getGameTime() < f.walkUntil;
    }

    /** Lets the watchers move, be hurt and be thrown again while their camera keeps playing (Star Fall: the impact inside the scene). */
    public static void thaw(List<UUID> who) {
        for (UUID u : who) FROZEN.remove(u);
    }

    /** Ends the scene for some watchers only (they left for another dimension). */
    public static void release(ServerLevel sl, List<UUID> who, int key) {
        Net.HFx stop = new Net.HFx(Net.HFx.STOP, key, -1, -1, 0, 0, 0, 0, 0, 0);
        for (UUID u : who) {
            FROZEN.remove(u);
            ServerPlayer sp = sl.getServer().getPlayerList().getPlayer(u);
            if (sp != null) Net.CH.send(PacketDistributor.PLAYER.with(() -> sp), stop);
        }
    }

    private static final class Frozen {
        Vec3 pos;
        long until;
        UUID caster;
        float yaw = Float.NaN;
        long walkUntil;
    }

    private static final Map<UUID, Frozen> FROZEN = new HashMap<>();

    /** Starts the scene for everyone near the caster. focus: the second point of the scene (rift, target, sky...), ang: a direction (radians). */
    public static List<UUID> start(ServerLevel sl, LivingEntity caster, int key, int scene, int dur, Vec3 focus, double ang) {
        return start(sl, caster, key, scene, dur, focus, ang, 0);
    }

    /** The same with an extra int for the client (T21: the target's entity id). */
    public static List<UUID> start(ServerLevel sl, LivingEntity caster, int key, int scene, int dur, Vec3 focus, double ang, int extra) {
        List<UUID> watchers = new ArrayList<>();
        long until = sl.getGameTime() + dur + 60;
        Net.HFx cut = new Net.HFx(Net.HFx.CUT, key, caster.getId(), scene, dur, focus.x, focus.y, focus.z, ang, extra);
        for (ServerPlayer sp : sl.players()) {
            if (sp.isSpectator() || sp.distanceToSqr(caster) > R * R) continue;
            Frozen f = new Frozen();
            f.pos = sp.position();
            f.until = until;
            f.caster = caster.getUUID();
            FROZEN.put(sp.getUUID(), f);
            watchers.add(sp.getUUID());
            Net.CH.send(PacketDistributor.PLAYER.with(() -> sp), cut);
        }
        return watchers;
    }

    /** Ends the scene: the camera returns and the watchers are free. */
    public static void end(ServerLevel sl, LivingEntity caster, List<UUID> watchers, int key) {
        Net.HFx stop = new Net.HFx(Net.HFx.STOP, key, -1, -1, 0, 0, 0, 0, 0, 0);
        for (UUID u : watchers) {
            Frozen f = FROZEN.get(u);
            if (f != null && f.caster.equals(caster.getUUID())) FROZEN.remove(u);
            ServerPlayer sp = sl.getServer().getPlayerList().getPlayer(u);
            if (sp != null) Net.CH.send(PacketDistributor.PLAYER.with(() -> sp), stop);
        }
    }

    /** A white flash on the watchers' screens. */
    public static void flash(ServerLevel sl, List<UUID> watchers, int dur, int rgb) {
        Net.HFx fl = new Net.HFx(Net.HFx.FLASH, 0, -1, -1, dur, 0, 0, 0, 0, rgb);
        for (UUID u : watchers) {
            ServerPlayer sp = sl.getServer().getPlayerList().getPlayer(u);
            if (sp != null) Net.CH.send(PacketDistributor.PLAYER.with(() -> sp), fl);
        }
    }

    /** Ids of frozen players (for tests). */
    public static List<UUID> frozen() {
        return new ArrayList<>(FROZEN.keySet());
    }

    public static final class CutsceneEvents {
        private CutsceneEvents() {}

        @SubscribeEvent
        public static void onPlayerTick(TickEvent.PlayerTickEvent e) {
            if (e.phase != TickEvent.Phase.END || !(e.player instanceof ServerPlayer sp) || FROZEN.isEmpty()) return;
            Frozen f = FROZEN.get(sp.getUUID());
            if (f == null) return;
            if (sp.level().getGameTime() > f.until || sp.isSpectator()) {
                FROZEN.remove(sp.getUUID());
                return;
            }
            if (sp.level().getGameTime() < f.walkUntil) {   // walking by itself: free to move, not hurt by the fall
                sp.fallDistance = 0;
                return;
            }
            boolean turn = !Float.isNaN(f.yaw) && Math.abs(net.minecraft.util.Mth.wrapDegrees(f.yaw - sp.getYRot())) > 1;
            if (turn || sp.position().distanceToSqr(f.pos) > 0.0025) {
                float yaw = Float.isNaN(f.yaw) ? sp.getYRot() : f.yaw;
                sp.connection.teleport(f.pos.x, f.pos.y, f.pos.z, yaw, sp.getXRot());
                sp.setYHeadRot(yaw);
                sp.setYBodyRot(yaw);
            }
            sp.setDeltaMovement(Vec3.ZERO);
            sp.fallDistance = 0;
        }

        @SubscribeEvent(priority = EventPriority.HIGHEST)
        public static void onAttack(LivingAttackEvent e) {
            if (FROZEN.isEmpty() || !(e.getEntity() instanceof ServerPlayer sp) || !FROZEN.containsKey(sp.getUUID())) return;
            if (!e.getSource().is(DamageTypeTags.BYPASSES_INVULNERABILITY)) e.setCanceled(true);
        }

        @SubscribeEvent
        public static void onLogout(PlayerEvent.PlayerLoggedOutEvent e) {
            FROZEN.remove(e.getEntity().getUUID());
        }

        @SubscribeEvent
        public static void onStopping(ServerStoppingEvent e) {
            FROZEN.clear();
        }
    }
}
