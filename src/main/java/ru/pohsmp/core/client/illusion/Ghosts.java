package ru.pohsmp.core.client.illusion;

import com.mojang.blaze3d.vertex.VertexConsumer;
import java.util.HashMap;
import java.util.Map;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.LivingEntity;
import net.minecraftforge.client.event.RenderLivingEvent;
import net.minecraftforge.event.level.LevelEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;

/**
 * T22 «Сон бабочки»: the one who showed itself (a strike, a cast) is drawn see-through for its second. The model is drawn again through
 * buffers that scale the vertex alpha: the player's body (a translucent render type) fades; cutout layers such as armour stay as they are.
 */
public final class Ghosts {
    private Ghosts() {}

    private static final float ALPHA = 0.45f;
    private static final Map<Integer, Long> UNTIL = new HashMap<>();
    private static boolean drawing;

    static void set(int entity, int ticks) {
        if (Minecraft.getInstance().level == null) return;
        UNTIL.put(entity, ru.pohsmp.core.client.ClientClock.ticks() + ticks);
    }

    @SubscribeEvent(priority = EventPriority.LOW)
    @SuppressWarnings({"unchecked", "rawtypes"})
    public static void onRender(RenderLivingEvent.Pre e) {
        if (drawing || UNTIL.isEmpty() || e.isCanceled()) return;
        LivingEntity ent = e.getEntity();
        Long until = UNTIL.get(ent.getId());
        if (until == null) return;
        if (ru.pohsmp.core.client.ClientClock.ticks() > until) {
            UNTIL.remove(ent.getId());
            return;
        }
        e.setCanceled(true);
        MultiBufferSource src = e.getMultiBufferSource();
        MultiBufferSource faded = rt -> new Faded(src.getBuffer(rt));
        float yaw = Mth.rotLerp(e.getPartialTick(), ent.yRotO, ent.getYRot());
        drawing = true;
        try {
            e.getRenderer().render(ent, yaw, e.getPartialTick(), e.getPoseStack(), faded, e.getPackedLight());
        } finally {
            drawing = false;
        }
    }

    @SubscribeEvent
    public static void onUnload(LevelEvent.Unload e) {
        if (e.getLevel().isClientSide()) UNTIL.clear();
    }

    private record Faded(VertexConsumer d) implements VertexConsumer {
        @Override public VertexConsumer vertex(double x, double y, double z) { d.vertex(x, y, z); return this; }
        @Override public VertexConsumer color(int r, int g, int b, int a) { d.color(r, g, b, (int) (a * ALPHA)); return this; }
        @Override public VertexConsumer uv(float u, float v) { d.uv(u, v); return this; }
        @Override public VertexConsumer overlayCoords(int u, int v) { d.overlayCoords(u, v); return this; }
        @Override public VertexConsumer uv2(int u, int v) { d.uv2(u, v); return this; }
        @Override public VertexConsumer normal(float x, float y, float z) { d.normal(x, y, z); return this; }
        @Override public void endVertex() { d.endVertex(); }
        @Override public void defaultColor(int r, int g, int b, int a) { d.defaultColor(r, g, b, (int) (a * ALPHA)); }
        @Override public void unsetDefaultColor() { d.unsetDefaultColor(); }
    }
}
