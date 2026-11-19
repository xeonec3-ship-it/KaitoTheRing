package ru.pohsmp.core.client;

import net.minecraftforge.client.event.ClientPlayerNetworkEvent;
import net.minecraftforge.client.event.RenderNameTagEvent;
import net.minecraftforge.eventbus.api.Event;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.silent.SilentWitch;

/** Silent Witch outfit, client side: no name tag above a hooded wearer for anyone, operators included (effects 6, 11). */
public final class SilentWitchClient {
    private SilentWitchClient() {}

    @SubscribeEvent(priority = EventPriority.LOWEST)
    public static void onNameTag(RenderNameTagEvent e) {
        if (SilentWitch.nameTagHidden(e.getEntity())) e.setResult(Event.Result.DENY);
    }

    @SubscribeEvent
    public static void onLogout(ClientPlayerNetworkEvent.LoggingOut e) {
        SilentWitch.clearClient();
    }
}
