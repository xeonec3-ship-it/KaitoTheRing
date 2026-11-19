package ru.pohsmp.core.client;

import java.lang.reflect.Field;
import java.util.HashMap;
import java.util.IdentityHashMap;
import java.util.Map;
import net.minecraft.client.renderer.entity.EntityRenderer;
import net.minecraft.world.entity.Entity;
import net.minecraftforge.client.event.RenderLevelStageEvent;
import net.minecraftforge.client.event.RenderLivingEvent;
import net.minecraftforge.client.event.RenderNameTagEvent;
import net.minecraftforge.client.event.RenderPlayerEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.level.LevelEvent;
import net.minecraftforge.eventbus.api.Event;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.util.ObfuscationReflectionHelper;
import ru.pohsmp.core.net.HideMsg;

/**
 * Entities the server hid (ru.pohsmp.core.Hidden) are not drawn at all: cancelling RenderLivingEvent.Pre skips the model,
 * its layers (armour, held items, CNPC parts) and the name tag. The shadow: the server keeps them invisible, which hides it for
 * vanilla renderers, but CNPC NPCs answer isInvisible() by their own display setting, so the renderer's shadow radius is also set to 0
 * for the hidden entity and put back before the next entity with that renderer is drawn.
 * The F3+B hitbox stays. The hide time runs out here too, in case the "show" packet is lost.
 */
public final class HiddenEntities {
    private HiddenEntities() {}

    /** entity id -> client tick until which it is hidden (Long.MAX_VALUE: until shown). */
    private static final Map<Integer, Long> UNTIL = new HashMap<>();
    private static long now;

    public static void handle(HideMsg m) {
        if (m.ticks == 0) UNTIL.remove(m.entity);
        else UNTIL.put(m.entity, m.ticks < 0 ? Long.MAX_VALUE : now + m.ticks);
    }

    public static boolean hidden(Entity e) {
        if (UNTIL.isEmpty() || e == null) return false;
        Long until = UNTIL.get(e.getId());
        return until != null && now < until;
    }

    @SubscribeEvent
    public static void onTick(TickEvent.ClientTickEvent e) {
        if (e.phase != TickEvent.Phase.END) return;
        now++;
        if (!UNTIL.isEmpty() && now % 20 == 0) UNTIL.values().removeIf(u -> u <= now);
    }

    /** EntityRenderer.shadowRadius; null if it cannot be reached (then CNPC shadows stay). */
    private static final Field SHADOW = shadowField();
    /** Renderers whose shadow radius is zeroed right now -> their own radius. */
    private static final Map<EntityRenderer<?>, Float> ZEROED = new IdentityHashMap<>();

    private static Field shadowField() {
        try {
            return ObfuscationReflectionHelper.findField(EntityRenderer.class, "f_114477_");
        } catch (RuntimeException ex) {
            return null;
        }
    }

    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void onLiving(RenderLivingEvent.Pre<?, ?> e) {
        EntityRenderer<?> r = e.getRenderer();
        if (hidden(e.getEntity())) {
            e.setCanceled(true);
            zeroShadow(r);
        } else if (!ZEROED.isEmpty()) restoreShadow(r);
    }

    private static void zeroShadow(EntityRenderer<?> r) {
        if (SHADOW == null) return;
        try {
            float cur = SHADOW.getFloat(r);
            if (cur == 0) return;
            ZEROED.putIfAbsent(r, cur);
            SHADOW.setFloat(r, 0);
        } catch (IllegalAccessException ignored) {
        }
    }

    private static void restoreShadow(EntityRenderer<?> r) {
        Float own = ZEROED.remove(r);
        if (own == null) return;
        try {
            if (SHADOW.getFloat(r) == 0) SHADOW.setFloat(r, own);   // CNPC sets its own radius every frame: leave that one
        } catch (IllegalAccessException ignored) {
        }
    }

    /** After all entities of the frame: every zeroed renderer gets its shadow back. */
    @SubscribeEvent
    public static void onStage(RenderLevelStageEvent e) {
        if (e.getStage() != RenderLevelStageEvent.Stage.AFTER_ENTITIES || ZEROED.isEmpty()) return;
        for (EntityRenderer<?> r : ZEROED.keySet().toArray(new EntityRenderer<?>[0])) restoreShadow(r);
    }

    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void onPlayer(RenderPlayerEvent.Pre e) {
        if (hidden(e.getEntity())) e.setCanceled(true);
    }

    /** Renderers that draw the name tag on their own still ask this event first. */
    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void onName(RenderNameTagEvent e) {
        if (hidden(e.getEntity())) e.setResult(Event.Result.DENY);
    }

    @SubscribeEvent
    public static void onUnload(LevelEvent.Unload e) {
        if (e.getLevel().isClientSide()) UNTIL.clear();
    }
}
