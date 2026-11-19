package ru.pohsmp.core.client;

import io.redspace.ironsspellbooks.entity.spells.ice_spike.IceSpikeEntity;
import net.minecraft.client.Minecraft;
import net.minecraft.world.entity.Entity;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.spell.FrostSpikeWallSpell;

/**
 * Frost Spike Wall uses Iron's ice spikes, which rise, rest 2 s and sink by their own clock. The wall's spikes (marked by their size,
 * see FrostSpikeWallSpell.wallSize) keep the clock stopped at "risen" here too, so they stand until the server removes them.
 */
public final class IceWallClient {
    private IceWallClient() {}

    @SubscribeEvent
    public static void onTick(TickEvent.ClientTickEvent e) {
        if (e.phase != TickEvent.Phase.END) return;
        Minecraft mc = Minecraft.getInstance();
        if (mc.level == null || mc.isPaused()) return;
        for (Entity en : mc.level.entitiesForRendering()) {
            if (!(en instanceof IceSpikeEntity s) || !FrostSpikeWallSpell.isWallSize(s.getSpikeSize())) continue;
            int up = s.getWaitTime() + IceSpikeEntity.RISE_TIME;
            if (s.tickCount > up) s.tickCount = up;
        }
    }
}
