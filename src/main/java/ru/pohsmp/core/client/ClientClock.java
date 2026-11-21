package ru.pohsmp.core.client;

import net.minecraft.client.Minecraft;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.fx.AnimClock;

/**
 * The client's own monotonic animation time (see fx/AnimClock): every client visual - fx, runes, circles, sigils, cutscene cameras,
 * the Gate staff, the ember whip, hidden hands, the Nero cat - is timed by this instead of {@code level.getGameTime()}, which the
 * dedicated server rewrites every second (time packets) and makes the animations jerk.
 */
public final class ClientClock {
    private ClientClock() {}

    private static final AnimClock CLOCK = new AnimClock();

    /** Whole client ticks (the drop-in for {@code mc.level.getGameTime()} in client visuals). */
    public static long ticks() {
        return CLOCK.ticks();
    }

    /** ticks() + partial tick: the time of this frame. */
    public static double now(float partialTick) {
        return CLOCK.now(partialTick);
    }

    /** Runs first among the END handlers, so the others see this tick's value (like the level time, ticked before them). */
    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void onTick(TickEvent.ClientTickEvent e) {
        if (e.phase != TickEvent.Phase.END) return;
        Minecraft mc = Minecraft.getInstance();
        if (mc.level == null || mc.isPaused()) return;   // paused single player: the level time stops too
        CLOCK.tick();
    }
}
