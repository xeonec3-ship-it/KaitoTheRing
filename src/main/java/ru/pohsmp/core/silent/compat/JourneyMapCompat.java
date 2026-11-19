package ru.pohsmp.core.silent.compat;

import java.util.UUID;
import journeymap.api.v2.client.event.EntityRadarUpdateEvent;
import journeymap.api.v2.common.event.ClientEventRegistry;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.player.Player;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.silent.SilentWitch;

/** JourneyMap (API v2): the radar update of a full-set Silent Witch is cancelled - no dot, no name on the minimap or the fullscreen map. */
public final class JourneyMapCompat {
    private JourneyMapCompat() {}

    static void init() {
        ClientEventRegistry.ENTITY_RADAR_UPDATE_EVENT.subscribe(PohCore.MODID, JourneyMapCompat::onRadar);
    }

    private static void onRadar(EntityRadarUpdateEvent e) {
        var w = e.getWrappedEntity();
        if (w == null) return;
        Entity ent = w.getEntityRef() == null ? null : w.getEntityRef().get();
        boolean hide = ent instanceof Player p ? SilentWitch.nameless(p) : namelessById(w.getEntityId());
        if (hide && e.isCancellable()) e.cancel();
    }

    private static boolean namelessById(String id) {
        try {
            return id != null && SilentWitch.namelessClient(UUID.fromString(id));
        } catch (IllegalArgumentException ex) {
            return false;
        }
    }
}
