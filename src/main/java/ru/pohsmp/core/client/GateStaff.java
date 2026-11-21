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
 * "Gate" (T03): the staff is not in the witch's hands during the scene (HiddenHands hides the held item). Until 37.4 s it floats upright
 * before her on the left, swaying slowly; then it glides into her left fist and stands upright there to the end of the scene.
 * Drawn from the CUT packet of the scene (Cutscene SILENT_GATE) for everyone who watches it.
 */
public final class GateStaff {
    private GateStaff() {}

    /** The scene length (the left hand takes the staff at 37.4–38.4 s: fx/gate/GateStaffPose). */
    private static final int END = ru.pohsmp.core.spell.silent.SilentGateSpell.SCENE_MAX;   // «Приказ»: the STOP packet ends it earlier

    /**
     * "Downfall": the staff went through the head at the start of the cast (manager 19.11). Until this tick it is out of the hand and
     * hangs upright to the right of the caster, then the normal staff in the hand.
     */
    private static final int DOWNFALL_HANG = 53;

    private record Run(int caster, long start, int scene) {
        boolean downfall() { return scene == ru.pohsmp.core.spell.Cutscene.DOWNFALL; }
        int end() { return downfall() ? DOWNFALL_HANG : END + 40; }
    }

    private static final Map<Integer, Run> RUNS = new HashMap<>();

    /** A running «Безмолвные врата» scene: its key, the caster and the game time it started (for the mana, fx/gate/GateManaRender). */
    public record GateRun(int key, int caster, long start) {}

    public static java.util.List<GateRun> gateRuns() {
        java.util.List<GateRun> out = new java.util.ArrayList<>();
        RUNS.forEach((k, r) -> { if (!r.downfall()) out.add(new GateRun(k, r.caster(), r.start())); });
        return out;
    }

    public static void start(int key, int casterId, long now) {
        RUNS.put(key, new Run(casterId, now, ru.pohsmp.core.spell.Cutscene.SILENT_GATE));
    }

    /** "Downfall" scene start: hide the held staff and hang it beside the caster until {@link #DOWNFALL_HANG}. */
    public static void startDownfall(int key, int casterId, long now) {
        Minecraft mc = Minecraft.getInstance();
        if (mc.level == null || !(mc.level.getEntity(casterId) instanceof LivingEntity le) || !isStaff(le.getMainHandItem())) return;
        HiddenHands.hide(le, DOWNFALL_HANG, 0, true);
        RUNS.put(key, new Run(casterId, now, ru.pohsmp.core.spell.Cutscene.DOWNFALL));
    }

    private static boolean isStaff(ItemStack s) {
        return s.getItem() instanceof io.redspace.ironsspellbooks.item.weapons.StaffItem;
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
        double now = ClientClock.now(pt);
        Vec3 cam = e.getCamera().getPosition();
        MultiBufferSource.BufferSource buf = mc.renderBuffers().bufferSource();
        RUNS.values().removeIf(r -> now - r.start() > r.end());
        for (Run r : RUNS.values()) {
            Entity en = mc.level.getEntity(r.caster());
            if (!(en instanceof LivingEntity le) || !le.isAlive()) continue;
            ItemStack st = le.getMainHandItem();
            if (r.downfall() ? !isStaff(st) : !(st.getItem() instanceof SilentWitchStaff)) continue;
            double t = now - r.start();
            float body = net.minecraft.util.Mth.rotLerp(pt, le.yBodyRotO, le.yBodyRot);
            Vec3 p = le.getPosition(pt);
            PoseStack ps = e.getPoseStack();
            ps.pushPose();
            ps.translate(p.x - cam.x, p.y - cam.y, p.z - cam.z);
            ps.mulPose(Axis.YP.rotationDegrees(-body));   // local: +x left, +z forward
            if (r.downfall()) {   // hanging upright to the right, a little forward, slow sway
                ps.translate(-0.8, 1.1 + 0.05 * Math.sin(t * 0.08), 0.25);
                ps.mulPose(Axis.ZP.rotationDegrees((float) (3 * Math.sin(t * 0.06))));
            } else {   // floating upright front-left, then glides into the left fist (STAFF_L): fx/gate/GateStaffPose, the mana trail uses it too
                double[] l = ru.pohsmp.core.client.fx.gate.GateStaffPose.local(t);
                ps.translate(l[0], l[1], l[2]);
                ps.mulPose(Axis.ZP.rotationDegrees((float) l[3]));
                ps.mulPose(Axis.XP.rotationDegrees((float) l[4]));
            }
            int light = LevelRenderer.getLightColor(mc.level, BlockPos.containing(p.add(0, 1, 0)));
            mc.getItemRenderer().renderStatic(st, ItemDisplayContext.NONE, light, OverlayTexture.NO_OVERLAY, ps, buf, mc.level, en.getId());
            ps.popPose();
        }
        buf.endBatch();
    }
}
