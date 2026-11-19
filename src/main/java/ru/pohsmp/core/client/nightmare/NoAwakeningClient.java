package ru.pohsmp.core.client.nightmare;

import net.minecraft.client.Minecraft;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraftforge.client.event.RenderLivingEvent;
import net.minecraftforge.client.event.RenderNameTagEvent;
import net.minecraftforge.eventbus.api.Event;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.client.illusion.Zones;
import ru.pohsmp.core.nightmare.NightmareMob;

/**
 * T25 «Пробуждение не наступит», a victim's own client: the caster is the Dread (nm_dread), every real monster around is one of the
 * nightmares (which one - by its id, so it keeps its look), and from the third thickening no real person has a name over its head.
 */
public final class NoAwakeningClient {
    private NoAwakeningClient() {}

    private static final NightmareMob.Kind[] MASKS = {NightmareMob.Kind.MAW, NightmareMob.Kind.CRAWLER, NightmareMob.Kind.LURKER,
            NightmareMob.Kind.WEEPER, NightmareMob.Kind.HOLLOW_CHILD};

    private static int step(Zones.Zone z) {
        try {
            return Integer.parseInt(z.text());
        } catch (NumberFormatException e) {
            return 0;
        }
    }

    @SubscribeEvent(priority = EventPriority.HIGH)
    public static void onLiving(RenderLivingEvent.Pre<?, ?> e) {
        LivingEntity le = e.getEntity();
        if (le instanceof NightmareMob || e.isCanceled()) return;
        if (ru.pohsmp.core.client.DownfallCut.morphed(le)) {   // the scene's turning: everyone watching (the caster too) sees the Dread
            NmStandIn.draw(e, le, NightmareMob.Kind.DREAD);
            return;
        }
        if (le == Minecraft.getInstance().player) return;
        Zones.Zone z = Zones.active(Zones.NO_AWAKENING);
        if (z == null) return;
        if (le.getId() == z.caster()) NmStandIn.draw(e, le, NightmareMob.Kind.DREAD);
        // owner 19.11: no other monsters - the real mobs keep their own look (MASKS kept for if it comes back)
    }

    @SubscribeEvent(priority = EventPriority.HIGH)
    public static void onName(RenderNameTagEvent e) {
        Entity en = e.getEntity();
        if (ru.pohsmp.core.client.DownfallCut.morphed(en)) {
            e.setResult(Event.Result.DENY);
            return;
        }
        if (en == Minecraft.getInstance().player) return;
        Zones.Zone z = Zones.active(Zones.NO_AWAKENING);
        if (z == null) return;
        if (en.getId() == z.caster() || (en instanceof Player && step(z) >= 3)) e.setResult(Event.Result.DENY);
    }
}
