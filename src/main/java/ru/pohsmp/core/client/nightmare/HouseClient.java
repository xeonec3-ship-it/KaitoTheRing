package ru.pohsmp.core.client.nightmare;

import net.minecraft.client.Minecraft;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraftforge.client.event.RenderLivingEvent;
import net.minecraftforge.client.event.RenderNameTagEvent;
import net.minecraftforge.client.event.ViewportEvent;
import net.minecraftforge.eventbus.api.Event;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.client.illusion.Zones;
import ru.pohsmp.core.nightmare.NightmareMob;

/**
 * T25 «Дом, которого нет», the victim's own client: the real world is gone (LevelRendererMixin: no blocks, sky, clouds; black fog here),
 * of all the living only the nightmares are drawn, and the caster is drawn as one more shadow (an nm_lurker that is not there).
 * The corridor itself comes from the server (mesh fx, only for the victim).
 */
public final class HouseClient {
    private HouseClient() {}

    public static boolean on() {
        return Zones.active(Zones.HOUSE) != null;
    }

    @SubscribeEvent(priority = EventPriority.HIGH)
    public static void onLiving(RenderLivingEvent.Pre<?, ?> e) {
        LivingEntity le = e.getEntity();
        if (le instanceof NightmareMob || le == Minecraft.getInstance().player) return;
        Zones.Zone z = Zones.active(Zones.HOUSE);
        if (z == null) return;
        if (le.getId() == z.caster()) NmStandIn.draw(e, le, NightmareMob.Kind.LURKER);
        else e.setCanceled(true);
    }

    @SubscribeEvent(priority = EventPriority.HIGH)
    public static void onName(RenderNameTagEvent e) {
        Entity en = e.getEntity();
        if (en instanceof LivingEntity && en != Minecraft.getInstance().player && on()) e.setResult(Event.Result.DENY);
    }

    @SubscribeEvent(priority = EventPriority.LOW)
    public static void onFog(ViewportEvent.RenderFog e) {
        if (!on()) return;
        e.setNearPlaneDistance(1f);
        e.setFarPlaneDistance(16f);
        e.setCanceled(true);
    }

    @SubscribeEvent(priority = EventPriority.LOW)
    public static void onFogColor(ViewportEvent.ComputeFogColor e) {
        if (!on()) return;
        e.setRed(0.012f);
        e.setGreen(0.006f);
        e.setBlue(0.01f);
    }
}
