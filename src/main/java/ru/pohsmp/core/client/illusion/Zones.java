package ru.pohsmp.core.client.illusion;

import java.util.HashMap;
import java.util.Map;
import net.minecraft.client.multiplayer.ClientLevel;
import ru.pohsmp.core.net.IlluMsg;

/**
 * T22: illusion zones this client is inside (the server sends them only to the victims): «Пелена», «Зеркальный лабиринт»,
 * «Кошмар наяву», «Сон бабочки». kind = IlluMsg.i.
 */
public final class Zones {
    private Zones() {}

    public static final int VEIL = IlluMsg.Z_VEIL, LABYRINTH = IlluMsg.Z_LABYRINTH, NIGHTMARE = IlluMsg.Z_NIGHTMARE, DREAM = IlluMsg.Z_DREAM;

    public record Zone(int kind, int caster, double x, double y, double z, double r, long until, String text) {}

    private static final Map<Long, Zone> ZONES = new HashMap<>();

    private static long key(int caster, int kind) {
        return ((long) caster << 8) | kind;
    }

    static void handle(IlluMsg m) {
        ru.pohsmp.core.PohCore.LOG.info("[pohsmp] illusion zone {} kind {} from entity {} for {} ticks", m.kind == IlluMsg.ZONE ? "on" : "off", m.i, m.entity, m.ticks);
        if (m.i == DREAM) {   // the mirror of the dream folds in / out
            if (m.kind == IlluMsg.ZONE) DreamScreen.enter();
            else DreamScreen.exit();
        }
        if (m.kind == IlluMsg.ZONE) ZONES.put(key(m.entity, m.i), new Zone(m.i, m.entity, m.x, m.y, m.z, m.yaw, IllusionClient.now() + m.ticks, m.text));
        else if (m.i != 0) ZONES.remove(key(m.entity, m.i));
        else ZONES.values().removeIf(z -> z.caster() == m.entity);   // no kind given: every zone of that caster
    }

    /** The zone of this kind this client is in now, or null. */
    public static Zone active(int kind) {
        if (ZONES.isEmpty()) return null;
        long now = IllusionClient.now();
        for (Zone z : ZONES.values()) if (z.kind() == kind && now < z.until()) return z;
        return null;
    }

    static void tick(ClientLevel lvl) {
        if (!ZONES.isEmpty()) ZONES.values().removeIf(z -> IllusionClient.now() >= z.until());
    }

    static void clear() {
        ZONES.clear();
    }
}
