package ru.pohsmp.core.client;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.math.Axis;
import java.util.HashMap;
import java.util.Map;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.LevelRenderer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.core.BlockPos;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.item.ItemDisplayContext;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.client.event.RenderLevelStageEvent;
import net.minecraftforge.event.level.LevelEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.SilentWitchStaff;

/**
 * "Gate" (T03): the staff is not in the witch's hands during the scene (HiddenHands hides the held item). Until 38 s it floats upright
 * before her on the left, swaying slowly; from 38 s she holds it in the left hand, low and slanted, to the end of the scene.
 * Drawn from the CUT packet of the scene (Cutscene SILENT_GATE) for everyone who watches it.
 */
public final class GateStaff {
    private GateStaff() {}

    /** Ticks from the scene start when the left hand takes the staff, and the scene length. */
    private static final int TAKE = 760, END = 1300;

    private record Run(int caster, long start) {}

    private static final Map<Integer, Run> RUNS = new HashMap<>();

    public static void start(int key, int casterId, long now) {
        RUNS.put(key, new Run(casterId, now));
    }

    /**
     * The scene ended or the cast was cancelled: the floating staff goes and the caster's hands show at once (owner 19.11: after a
     * cancel the staff stayed hidden for the finish-animation time).
     */
    public static void stop(int key) {
        Run r = RUNS.remove(key);
        Minecraft mc = Minecraft.getInstance();
        if (r != null && mc.level != null && mc.level.getEntity(r.caster()) instanceof LivingEntity le) HiddenHands.show(le);
    }

    @SubscribeEvent
    public static void onUnload(LevelEvent.Unload e) {
        if (e.getLevel().isClientSide()) RUNS.clear();
    }

    @SubscribeEvent
    public static void onRender(RenderLevelStageEvent e) {
        if (e.getStage() != RenderLevelStageEvent.Stage.AFTER_ENTITIES || RUNS.isEmpty()) return;
        Minecraft mc = Minecraft.getInstance();
        if (mc.level == null) return;
        float pt = e.getPartialTick();
        double now = mc.level.getGameTime() + pt;
        Vec3 cam = e.getCamera().getPosition();
        MultiBufferSource.BufferSource buf = mc.renderBuffers().bufferSource();
        RUNS.values().removeIf(r -> now - r.start() > END + 40);
        for (Run r : RUNS.values()) {
            Entity en = mc.level.getEntity(r.caster());
            if (!(en instanceof LivingEntity le) || !le.isAlive()) continue;
            ItemStack st = le.getMainHandItem();
            if (!(st.getItem() instanceof SilentWitchStaff)) continue;
            double t = now - r.start();
            float body = net.minecraft.util.Mth.rotLerp(pt, le.yBodyRotO, le.yBodyRot);
            Vec3 p = le.getPosition(pt);
            PoseStack ps = e.getPoseStack();
            ps.pushPose();
            ps.translate(p.x - cam.x, p.y - cam.y, p.z - cam.z);
            ps.mulPose(Axis.YP.rotationDegrees(-body));   // local: +x left, +z forward
            if (t < TAKE) {   // floating upright, front-left, slow sway and bob
                ps.translate(0.75, 1.15 + 0.08 * Math.sin(t * 0.06), 0.65);
                ps.mulPose(Axis.ZP.rotationDegrees((float) (4 * Math.sin(t * 0.045))));
                ps.mulPose(Axis.XP.rotationDegrees((float) (3 * Math.sin(t * 0.037 + 1))));
            } else {          // in the left fist at the belt, a little forward (pose STAFF_L): the staff stands upright (owner 19.11)
                ps.translate(0.36, 0.98, 0.3);
            }
            int light = LevelRenderer.getLightColor(mc.level, BlockPos.containing(p.add(0, 1, 0)));
            mc.getItemRenderer().renderStatic(st, ItemDisplayContext.NONE, light, OverlayTexture.NO_OVERLAY, ps, buf, mc.level, en.getId());
            ps.popPose();
        }
        buf.endBatch();
    }
}
