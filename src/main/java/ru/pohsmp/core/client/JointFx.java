package ru.pohsmp.core.client;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.player.ClientMagicData;
import java.lang.reflect.Field;
import java.util.HashMap;
import java.util.Map;
import net.minecraft.client.Minecraft;
import net.minecraft.world.entity.Entity;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.net.Net;

/**
 * Client side of the joint cast (T15): which entities are in a merged cast right now (their sigils get a second outline)
 * and the own cast bar shortened by the server.
 */
public final class JointFx {
    private JointFx() {}

    /** Second outline: raised by LIFT blocks, SCALE times wider, turned by TURN radians and spinning the other way, ALPHA of the first. */
    public static final float LIFT = 0.12f, SCALE = 1.22f, TURN = (float) (Math.PI / 8), ALPHA = 0.65f;

    private static final Map<Integer, Long> UNTIL = new HashMap<>();

    static void mark(int entityId, long untilTick) {
        if (entityId >= 0) UNTIL.put(entityId, untilTick);
    }

    public static boolean isJoint(int entityId, long now) {
        if (UNTIL.isEmpty()) return false;
        Long u = UNTIL.get(entityId);
        if (u == null) return false;
        if (u < now) {
            UNTIL.remove(entityId);
            return false;
        }
        return true;
    }

    public static boolean isJoint(Entity e) {
        return e != null && e.level() != null && isJoint(e.getId(), e.level().getGameTime());
    }

    private static Field PLAYER_DATA;

    public static void castTime(Net.CastTime m) {
        try {
            if (PLAYER_DATA == null) {
                PLAYER_DATA = ClientMagicData.class.getDeclaredField("playerMagicData");
                PLAYER_DATA.setAccessible(true);
            }
            ru.pohsmp.core.spell.JointCast.setCastTime((MagicData) PLAYER_DATA.get(null), m.duration, m.remaining);
        } catch (ReflectiveOperationException ex) {
            PohCore.LOG.warn("[pohsmp_core] joint cast: cannot update the cast bar", ex);
        }
        if (Minecraft.getInstance().player != null) mark(Minecraft.getInstance().player.getId(), Minecraft.getInstance().level.getGameTime() + m.remaining + 10);
    }
}
