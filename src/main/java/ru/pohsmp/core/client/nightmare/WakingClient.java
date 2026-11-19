package ru.pohsmp.core.client.nightmare;

import net.minecraft.client.Minecraft;
import net.minecraft.world.entity.player.Player;
import net.minecraftforge.client.event.RenderLivingEvent;
import net.minecraftforge.client.event.RenderNameTagEvent;
import net.minecraftforge.eventbus.api.Event;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.client.illusion.Zones;
import ru.pohsmp.core.nightmare.NightmareMob;

/**
 * T22 «Кошмар наяву» (owner 19.11): on the victim's own client every other person - the caster too - is the monster the caster becomes
 * (nm_dread), with no name. Friend or foe, it cannot tell.
 */
public final class WakingClient {
    private WakingClient() {}

    @SubscribeEvent(priority = EventPriority.HIGH)
    public static void onLiving(RenderLivingEvent.Pre<?, ?> e) {
        if (e.isCanceled()) return;
        if (mobMasked(e.getEntity())) {   // the server puts the faceless monster (fx) on it: the real model is not drawn
            e.setCanceled(true);
            return;
        }
        if (!(e.getEntity() instanceof Player p) || p == Minecraft.getInstance().player || Zones.active(Zones.WAKING) == null) return;
        NmStandIn.draw(e, p, NightmareMob.Kind.DREAD);
    }

    /**
     * Owner 19.11: at stages 2 and 3 of the immersion the real mobs within 40 blocks are the faceless monster illusion_nightmare
     * (as in «Кошмар наяву»); the server sends the monster fx on each (Immersion.masks), this client hides the mob itself.
     */
    private static boolean mobMasked(net.minecraft.world.entity.Entity e) {
        var me = Minecraft.getInstance().player;
        return me != null && NightmareClient.stage() >= 2 && !HouseClient.on() && ru.pohsmp.core.nightmare.Immersion.maskable(e)
                && e.distanceToSqr(me) < 40 * 40;
    }

    @SubscribeEvent(priority = EventPriority.HIGH)
    public static void onName(RenderNameTagEvent e) {
        if (mobMasked(e.getEntity())) {
            e.setResult(Event.Result.DENY);
            return;
        }
        if (e.getEntity() instanceof Player p && p != Minecraft.getInstance().player && Zones.active(Zones.WAKING) != null)
            e.setResult(Event.Result.DENY);
    }
}
