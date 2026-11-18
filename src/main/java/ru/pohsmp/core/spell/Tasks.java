package ru.pohsmp.core.spell;

import java.util.ArrayList;
import java.util.List;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.PohCore;

/** Server tick scheduler for spells that keep working after the cast. Not saved: a restart drops running tasks. */
public final class Tasks {
    private Tasks() {}

    @FunctionalInterface
    public interface Task {
        /** Called every server tick; return false to finish. */
        boolean tick();
    }

    private static final List<Task> RUN = new ArrayList<>();
    private static final List<Task> ADD = new ArrayList<>();

    public static void add(Task t) {
        ADD.add(t);
    }

    @SubscribeEvent
    public static void onServerTick(TickEvent.ServerTickEvent e) {
        if (e.phase != TickEvent.Phase.END) return;
        if (!ADD.isEmpty()) {
            RUN.addAll(ADD);
            ADD.clear();
        }
        if (RUN.isEmpty()) return;
        RUN.removeIf(t -> {
            try {
                return !t.tick();
            } catch (Exception ex) {
                PohCore.LOG.error("[pohsmp_core] spell task failed", ex);
                return true;
            }
        });
    }

    @SubscribeEvent
    public static void onStopping(ServerStoppingEvent e) {
        RUN.clear();
        ADD.clear();
    }
}
