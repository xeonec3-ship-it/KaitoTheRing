package ru.pohsmp.core.silent.compat;

import net.minecraftforge.eventbus.api.IEventBus;
import net.minecraftforge.fml.InterModComms;
import net.minecraftforge.fml.ModList;
import net.minecraftforge.fml.event.lifecycle.FMLClientSetupEvent;
import net.minecraftforge.fml.event.lifecycle.InterModEnqueueEvent;
import net.minecraftforge.fml.loading.FMLEnvironment;
import ru.pohsmp.core.PohCore;

/**
 * Silent Witch outfit, effect 11: the full-set wearer is hidden from minimaps and look-at HUDs of other mods, each through its own API.
 * All soft: a class that touches a mod's API is loaded only when that mod is present.
 * <ul>
 * <li>Jade - {@link JadeCompat} (@WailaPlugin, found by Jade itself): ray trace callback turns the wearer into "nothing";</li>
 * <li>WTHIT - {@link WthitCompat} (waila_plugins.json): entity override returns EMPTY_ENTITY;</li>
 * <li>The One Probe - {@link TopCompat} (IMC): entity blacklist, checked on the server where TOP builds its info;</li>
 * <li>JourneyMap - {@link JourneyMapCompat}: cancels the radar update event for the wearer;</li>
 * <li>Xaero's Minimap / World Map - mixins in ru.pohsmp.core.mixin (no API for this): radar skips the wearer, tracked markers dropped.</li>
 * </ul>
 */
public final class Compat {
    private Compat() {}

    public static void common(IEventBus modBus) {
        modBus.addListener(Compat::imc);
        if (FMLEnvironment.dist.isClient()) modBus.addListener(Compat::clientSetup);
    }

    private static void imc(InterModEnqueueEvent e) {
        if (ModList.get().isLoaded("theoneprobe")) InterModComms.sendTo("theoneprobe", "getTheOneProbe", TopCompat::new);
    }

    private static void clientSetup(FMLClientSetupEvent e) {
        if (ModList.get().isLoaded("journeymap")) {
            try {
                JourneyMapCompat.init();
            } catch (Throwable t) {
                PohCore.LOG.warn("[pohsmp_core] JourneyMap API not usable, Silent Witch wearers stay on its radar: {}", t.toString());
            }
        }
    }
}
