package ru.pohsmp.core.spell;

import java.util.HashMap;
import java.util.Map;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.LivingEntity;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.network.PacketDistributor;
import ru.pohsmp.core.net.Net;
import ru.pohsmp.core.net.Net.HFx;

/**
 * T13: the pose of a target held by a spell (Disintegration, its Replica, any other hold): the looping player animation
 * pohsmp_held_target (tools/gen_player_anims.py) runs on that entity for every client that sees it, from {@link #hold}
 * until the matching {@link #release}. Counted, so two holds on one target end only when both let go. Players get it on
 * their PlayerAnimator layer (client/TargetPoseClient), other humanoids (CustomNPCs NPCs, zombies) on their model.
 */
public final class TargetPose {
    private TargetPose() {}

    /** HFx.ANIM b values (a = entity id). */
    public static final int HELD_START = 1, HELD_STOP = 2;

    /** entity id -> number of holds on it (server side). */
    private static final Map<Integer, Integer> HELD = new HashMap<>();

    public static void hold(LivingEntity target) {
        if (target.level().isClientSide) return;
        if (HELD.merge(target.getId(), 1, Integer::sum) == 1) send(target, HELD_START);
    }

    public static void release(LivingEntity target) {
        if (target.level().isClientSide) return;
        Integer n = HELD.get(target.getId());
        if (n == null) return;
        if (n > 1) {
            HELD.put(target.getId(), n - 1);
            return;
        }
        HELD.remove(target.getId());
        send(target, HELD_STOP);
    }

    public static boolean held(LivingEntity target) {
        return HELD.containsKey(target.getId());
    }

    private static void send(LivingEntity target, int what) {
        Net.CH.send(PacketDistributor.TRACKING_ENTITY_AND_SELF.with(() -> target), msg(target, what));
    }

    private static HFx msg(LivingEntity target, int what) {
        return new HFx(HFx.ANIM, 0, target.getId(), what, 0, 0, 0, 0, 0, 0);
    }

    /** Server lifecycle and late viewers. */
    public static final class Events {
        private Events() {}

        /** A player who starts seeing a held target (came near, joined) gets the pose too. */
        @SubscribeEvent
        public static void onStartTracking(PlayerEvent.StartTracking e) {
            if (e.getTarget() instanceof LivingEntity le && HELD.containsKey(le.getId()) && e.getEntity() instanceof ServerPlayer p)
                Net.CH.send(PacketDistributor.PLAYER.with(() -> p), msg(le, HELD_START));
        }

        @SubscribeEvent
        public static void onServerStopped(net.minecraftforge.event.server.ServerStoppedEvent e) {
            HELD.clear();
        }
    }
}
