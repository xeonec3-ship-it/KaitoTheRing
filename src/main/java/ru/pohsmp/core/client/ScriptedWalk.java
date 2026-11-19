package ru.pohsmp.core.client;

import net.minecraft.client.Minecraft;
import net.minecraft.client.player.LocalPlayer;
import net.minecraft.util.Mth;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.level.LevelEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;

/**
 * A walk led by a spell (IlluMsg.WALK; Coven Arrival: the retinue players, owner 19.11 «пусть ходит по-настоящему»). The own player
 * really walks: each tick its velocity points at the goal, so the legs move, the step goes up slabs and everyone else sees a walk,
 * not a teleport. The keys are off meanwhile (the cutscene holds them); the server holds the goal and puts the player there if this
 * client could not get there in time.
 */
public final class ScriptedWalk {
    private ScriptedWalk() {}

    private static Vec3 goal;
    private static int left;
    private static float endYaw;

    public static void start(int entity, double x, double y, double z, int ticks, float yaw) {
        LocalPlayer p = Minecraft.getInstance().player;
        if (p == null || p.getId() != entity) return;
        goal = new Vec3(x, y, z);
        left = Math.max(1, ticks);
        endYaw = yaw;
    }

    public static boolean active() {
        return goal != null;
    }

    @SubscribeEvent
    public static void onTick(TickEvent.PlayerTickEvent e) {
        if (goal == null || e.phase != TickEvent.Phase.START || !e.player.level().isClientSide
                || e.player != Minecraft.getInstance().player) return;
        LocalPlayer p = (LocalPlayer) e.player;
        double dx = goal.x - p.getX(), dz = goal.z - p.getZ();
        double dist = Math.sqrt(dx * dx + dz * dz);
        if (dist > 32) {   // the server moved this player elsewhere meanwhile
            goal = null;
            return;
        }
        if (dist < 0.02 || left <= 0) {
            p.setDeltaMovement(0, p.getDeltaMovement().y, 0);
            face(p, endYaw);
            goal = null;
            return;
        }
        // the rest of the way spread over the ticks left, at least a slow walk, at most a run; the last step lands on the goal
        double speed = Math.min(dist, Mth.clamp(dist / left, 0.11, 0.38));
        p.setDeltaMovement(dx / dist * speed, p.getDeltaMovement().y, dz / dist * speed);
        if (dist > 0.25) face(p, (float) Math.toDegrees(Math.atan2(-dx, dz)));
        if (p.horizontalCollision && p.onGround()) p.jumpFromGround();   // a block in the way: hop it
        left--;
    }

    private static void face(LocalPlayer p, float yaw) {
        p.setYRot(yaw);
        p.yBodyRot = yaw;
        p.yHeadRot = yaw;
    }

    @SubscribeEvent
    public static void onUnload(LevelEvent.Unload e) {
        if (e.getLevel().isClientSide()) goal = null;
    }
}
