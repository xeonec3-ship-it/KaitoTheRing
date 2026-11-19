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
 * cannot be hurt and watches the scene until it ends (or the cast stops). Scenes: 0 Downfall, 1 Milky Way, 2 Soul Devour, 3 Divine Taboo.
 */
public final class Cutscene {
    private Cutscene() {}

    public static final double R = 64;
    /** Coven Arrival: watchers within this of the arena and of the caster (the other scenes use R). */
    public static final double R_COVEN = 98;
    public static final int DOWNFALL = 0, MILKY_WAY = 1, SOUL_DEVOUR = 2, TABOO = 3, SPACE_CLOSURE = 4, COVEN_ARRIVAL = 5;

    /**
     * Starts the scene for everyone within r of the caster (in the caster's level) or of `extra` in `extraLevel` (may be another dimension).
     * The packet carries the caster's entity id: on clients in the other level that entity is unknown, the client copes with it.
     */
    public static List<UUID> start(ServerLevel sl, LivingEntity caster, int key, int scene, int dur, Vec3 focus, double ang, double r,
                                   ServerLevel extraLevel, Vec3 extra) {
        List<UUID> watchers = new ArrayList<>();
        long until = sl.getGameTime() + dur + 60;
        Net.HFx cut = new Net.HFx(Net.HFx.CUT, key, caster.getId(), scene, dur, focus.x, focus.y, focus.z, ang, 0);
        for (ServerPlayer sp : sl.getServer().getPlayerList().getPlayers()) {
            if (sp.isSpectator()) continue;
            boolean near = sp.level() == sl && sp.distanceToSqr(caster) <= r * r
                    || extraLevel != null && sp.level() == extraLevel && sp.position().distanceToSqr(extra) <= r * r;
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
        if (f != null) f.pos = pos;
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
    }

    private static final Map<UUID, Frozen> FROZEN = new HashMap<>();

    /** Starts the scene for everyone near the caster. focus: the second point of the scene (rift, target, sky...), ang: a direction (radians). */
    public static List<UUID> start(ServerLevel sl, LivingEntity caster, int key, int scene, int dur, Vec3 focus, double ang) {
        List<UUID> watchers = new ArrayList<>();
        long until = sl.getGameTime() + dur + 60;
        Net.HFx cut = new Net.HFx(Net.HFx.CUT, key, caster.getId(), scene, dur, focus.x, focus.y, focus.z, ang, 0);
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
            if (sp.position().distanceToSqr(f.pos) > 0.0025) sp.connection.teleport(f.pos.x, f.pos.y, f.pos.z, sp.getYRot(), sp.getXRot());
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
