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
        if (!(e.getEntity() instanceof Player p) || p == Minecraft.getInstance().player || Zones.active(Zones.WAKING) == null) return;
        NmStandIn.draw(e, p, NightmareMob.Kind.DREAD);
    }

    @SubscribeEvent(priority = EventPriority.HIGH)
    public static void onName(RenderNameTagEvent e) {
        if (e.getEntity() instanceof Player p && p != Minecraft.getInstance().player && Zones.active(Zones.WAKING) != null)
            e.setResult(Event.Result.DENY);
    }
}
