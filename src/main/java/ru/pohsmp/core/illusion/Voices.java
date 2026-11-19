package ru.pohsmp.core.illusion;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;

/**
 * T22 (manager's decision 1): where a victim of an illusion hears the caster's voice (Simple Voice Chat) from. Built every server tick
 * as a fresh map speaker -> (listener -> place) from the spells' providers; the voice chat thread only reads the last one
 * (compat/VoiceIllusions). No voice chat on the server - the map is built and nobody reads it.
 */
public final class Voices {
    private Voices() {}

    @FunctionalInterface
    public interface Provider {
        /** Puts speaker -> listener -> place for every redirect of this spell now. */
        void fill(Map<UUID, Map<UUID, Vec3>> out);
    }

    private static final List<Provider> PROVIDERS = new ArrayList<>();
    private static volatile Map<UUID, Map<UUID, Vec3>> NOW = Map.of();

    public static void provider(Provider p) {
        PROVIDERS.add(p);
    }

    /** The place listener hears speaker from, or null for the speaker itself. Any thread. */
    public static Vec3 from(UUID speaker, UUID listener) {
        Map<UUID, Vec3> m = NOW.get(speaker);
        return m == null ? null : m.get(listener);
    }

    public static void put(Map<UUID, Map<UUID, Vec3>> out, UUID speaker, UUID listener, Vec3 at) {
        out.computeIfAbsent(speaker, k -> new HashMap<>()).putIfAbsent(listener, at);
    }

    @SubscribeEvent
    public static void onTick(TickEvent.ServerTickEvent e) {
        if (e.phase != TickEvent.Phase.END) return;
        if (PROVIDERS.isEmpty()) return;
        Map<UUID, Map<UUID, Vec3>> out = new HashMap<>();
        for (Provider p : PROVIDERS) p.fill(out);
        NOW = out.isEmpty() ? Map.of() : out;
    }

    @SubscribeEvent
    public static void onStopping(ServerStoppingEvent e) {
        NOW = Map.of();
    }
}
