package ru.pohsmp.core.client;

import it.unimi.dsi.fastutil.ints.Int2LongOpenHashMap;
import java.lang.reflect.Field;
import java.util.IdentityHashMap;
import java.util.Map;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.entity.EntityRenderer;
import net.minecraftforge.client.event.RenderLevelStageEvent;
import net.minecraftforge.client.event.RenderLivingEvent;
import net.minecraftforge.client.event.RenderNameTagEvent;
import net.minecraftforge.client.event.RenderPlayerEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.Event;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.util.ObfuscationReflectionHelper;

/**
 * Entities the server asked to hide ({@code Hidden}, packet {@code HideMsg}): their renderer is skipped (model, armour, held items,
 * the CNPC name) and so is the shadow, which the dispatcher draws after the renderer: the renderer's shadow radius is set to 0
 * for the hidden one and given back before the next entity of that renderer draws. Hitboxes (F3+B) stay.
 */
public final class HiddenEntities {
    private HiddenEntities() {}

    /** Entity id -> client game time when it shows again. */
    private static final Int2LongOpenHashMap UNTIL = new Int2LongOpenHashMap();
    private static final Map<EntityRenderer<?>, Float> SHADOW = new IdentityHashMap<>();
    private static Field shadowField;

    public static void set(int id, int ticks) {
        Minecraft mc = Minecraft.getInstance();
        if (ticks <= 0 || mc.level == null) UNTIL.remove(id);
        else UNTIL.put(id, mc.level.getGameTime() + ticks);
    }

    public static boolean hidden(int id) {
        Minecraft mc = Minecraft.getInstance();
        if (mc.level == null || !UNTIL.containsKey(id)) return false;
        if (mc.level.getGameTime() >= UNTIL.get(id)) {
            UNTIL.remove(id);
            return false;
        }
        return true;
    }

    private static Field shadow() {
        if (shadowField == null) shadowField = ObfuscationReflectionHelper.findField(EntityRenderer.class, "f_114477_");
        return shadowField;
    }

    private static void restore(EntityRenderer<?> r) {
        Float old = SHADOW.remove(r);
        if (old == null) return;
        try {
            shadow().setFloat(r, old);
        } catch (Throwable ignored) {
        }
    }

    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void onRenderLiving(RenderLivingEvent.Pre<?, ?> ev) {
        EntityRenderer<?> r = ev.getRenderer();
        restore(r);
        if (!hidden(ev.getEntity().getId())) return;
        try {
            Field f = shadow();
            SHADOW.put(r, f.getFloat(r));
            f.setFloat(r, 0f);
        } catch (Throwable ignored) {
        }
        ev.setCanceled(true);
    }

    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void onRenderPlayer(RenderPlayerEvent.Pre ev) {
        if (hidden(ev.getEntity().getId())) ev.setCanceled(true);
    }

    /** CNPC and others may draw the name outside the living renderer's Pre event. */
    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void onNameTag(RenderNameTagEvent ev) {
        if (hidden(ev.getEntity().getId())) ev.setResult(Event.Result.DENY);
    }

    /** Give every renderer its shadow back once the level is drawn. */
    @SubscribeEvent
    public static void onStage(RenderLevelStageEvent ev) {
        if (ev.getStage() == RenderLevelStageEvent.Stage.AFTER_ENTITIES && !SHADOW.isEmpty())
            for (EntityRenderer<?> r : SHADOW.keySet().toArray(new EntityRenderer<?>[0])) restore(r);
    }

    @SubscribeEvent
    public static void onClientTick(TickEvent.ClientTickEvent ev) {
        if (ev.phase == TickEvent.Phase.END && Minecraft.getInstance().level == null && !UNTIL.isEmpty()) UNTIL.clear();
    }
}
