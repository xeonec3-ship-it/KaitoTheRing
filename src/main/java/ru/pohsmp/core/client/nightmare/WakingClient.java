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
        if (e.getEntity() instanceof net.minecraft.world.entity.Mob mob && mobMasked(mob)) {
            NmStandIn.draw(e, mob, NightmareMob.Kind.DREAD);
            return;
        }
        if (!(e.getEntity() instanceof Player p) || p == Minecraft.getInstance().player || Zones.active(Zones.WAKING) == null) return;
        NmStandIn.draw(e, p, NightmareMob.Kind.DREAD);
    }

    /** Owner 19.11: under any nightmare spell (the immersion at any stage, «Кошмар наяву», «Пробуждение не наступит») mobs are the Dread too. */
    private static boolean inNightmare() {
        return NightmareClient.stage() > 0 || Zones.active(Zones.WAKING) != null || Zones.active(Zones.NO_AWAKENING) != null;
    }

    /** A real mob (not a nightmare of ours, not a CustomNPCs NPC - those are people) while this client is in a nightmare. */
    private static boolean mobMasked(net.minecraft.world.entity.Mob mob) {
        return !(mob instanceof NightmareMob) && !mob.getClass().getName().startsWith("noppes.npcs") && inNightmare();
    }

    @SubscribeEvent(priority = EventPriority.HIGH)
    public static void onName(RenderNameTagEvent e) {
        if (e.getEntity() instanceof net.minecraft.world.entity.Mob mob && mobMasked(mob)) {
            e.setResult(Event.Result.DENY);
            return;
        }
        if (e.getEntity() instanceof Player p && p != Minecraft.getInstance().player && Zones.active(Zones.WAKING) != null)
            e.setResult(Event.Result.DENY);
    }
}
