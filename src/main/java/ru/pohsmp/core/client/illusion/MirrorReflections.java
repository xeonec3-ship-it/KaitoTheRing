package ru.pohsmp.core.client.illusion;

import com.mojang.blaze3d.pipeline.RenderTarget;
import com.mojang.blaze3d.systems.RenderSystem;
import com.mojang.blaze3d.vertex.BufferBuilder;
import com.mojang.blaze3d.vertex.BufferUploader;
import com.mojang.blaze3d.vertex.DefaultVertexFormat;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.Tesselator;
import com.mojang.blaze3d.vertex.VertexFormat;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.GameRenderer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.culling.Frustum;
import net.minecraft.client.renderer.entity.EntityRenderDispatcher;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.client.event.RenderNameTagEvent;
import net.minecraftforge.eventbus.api.Event;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import org.joml.Matrix4f;
import org.lwjgl.opengl.GL11;
import ru.pohsmp.core.illusion.Maze;

/**
 * T22 «Зеркальный лабиринт»: the caster's reflections in the mirror walls, on the victim's client only.
 * <p>
 * No copy entity: the caster itself (the real entity this client already has - its skin, armour, hand items, Iron's and Epic Fight
 * animations, all of it) is drawn a second time through a reflection matrix in the plane of the wall's face turned to the camera.
 * So the position and the turn are mirrored in that plane and every move is mirrored too (its right hand is the image's left).
 * <p>
 * Clipping to the glass by the stencil buffer: the visible part of the face is marked, the depth there is pushed to the far plane
 * (nothing behind a mirror is seen), the reflection is drawn only inside the mark, then the face's depth is put back and a thin layer of
 * the mirror texture goes over it. Without a stencil buffer (a shader pack that does not give one) there are no reflections at all,
 * rather than images sticking out of the walls.
 * <p>
 * A wall reflects the caster only when the caster is on the camera's side of it, no farther than {@link #RANGE} blocks from it,
 * and the image can be seen through that pane from the camera; of those, the {@link #MAX} nearest to the victim.
 */
public final class MirrorReflections {
    private MirrorReflections() {}

    static final double RANGE = 16.0;
    static final int MAX = 4;
    private static final float GLASS = 0.35f;

    /** true while a reflection is being drawn (no name over it: the name tag is see-through and would pass the glass) */
    private static boolean drawing;
    private static boolean warned;

    /** The mirror face a reflection is drawn in: the plane coordinate {@code plane} on the axis Z (wall along X) or X. */
    private record Face(double[] wall, boolean alongX, double plane, double dist) {}

    /** Asked for on the client tick while the victim is in a labyrinth: the stencil buffer is added between frames, not in one. */
    static void prepare() {
        RenderTarget rt = Minecraft.getInstance().getMainRenderTarget();
        if (!rt.isStencilEnabled()) rt.enableStencil();
    }

    /**
     * Draws the reflections. ps is in world coordinates (already moved by -camera), mat = ps.last().pose(); called after the walls and
     * before the cracks.
     */
    static void draw(PoseStack ps, Vec3 cam, Maze m, int casterId, float pt, Frustum frustum) {
        Minecraft mc = Minecraft.getInstance();
        if (mc.level == null) return;
        Entity caster = mc.level.getEntity(casterId);
        if (caster == null || caster.isRemoved() || caster == mc.getCameraEntity()) return;
        RenderTarget rt = mc.getMainRenderTarget();
        // the stencil must be in the buffer drawn into now: not so with «Fabulous» graphics (translucent target) or a shader pack's own
        if (!rt.isStencilEnabled() || GL11.glGetInteger(org.lwjgl.opengl.GL30.GL_DRAW_FRAMEBUFFER_BINDING) != rt.frameBufferId) {
            if (!warned) ru.pohsmp.core.PohCore.LOG.warn("[pohsmp] mirror_labyrinth: no stencil buffer here, the walls show no reflections");
            warned = true;
            return;
        }
        Vec3 cp = caster.getPosition(pt);
        double y0 = m.cy - Maze.BELOW, y1 = m.cy + Maze.ABOVE;
        List<Face> faces = faces(m, cam, cp, caster.getBbHeight(), y0, y1, frustum);
        if (faces.isEmpty()) return;

        MultiBufferSource.BufferSource buf = mc.renderBuffers().bufferSource();
        buf.endBatch();   // nothing of the world goes through the stencil with the reflection
        EntityRenderDispatcher d = mc.getEntityRenderDispatcher();
        boolean boxes = d.shouldRenderHitBoxes();
        d.setRenderHitBoxes(false);
        d.setRenderShadow(false);
        int light = d.getPackedLightCoords(caster, pt);
        float yaw = Mth.lerp(pt, caster.yRotO, caster.getYRot());
        drawing = true;
        try {
            for (Face f : faces) one(ps, buf, d, caster, cp, yaw, pt, light, f, y0, y1);
        } finally {
            drawing = false;
            GL11.glFrontFace(GL11.GL_CCW);
            GL11.glDepthRange(0, 1);
            GL11.glDisable(GL11.GL_STENCIL_TEST);
            RenderSystem.stencilMask(0xFF);
            RenderSystem.stencilFunc(GL11.GL_ALWAYS, 0, 0xFF);
            RenderSystem.stencilOp(GL11.GL_KEEP, GL11.GL_KEEP, GL11.GL_KEEP);
            RenderSystem.colorMask(true, true, true, true);
            RenderSystem.depthMask(true);
            RenderSystem.depthFunc(GL11.GL_LEQUAL);
            RenderSystem.enableCull();
            d.setRenderHitBoxes(boxes);
            d.setRenderShadow(mc.options.entityShadows().get());
        }
    }

    /** The faces turned to the camera that can show the caster's image, nearest to the camera first, at most MAX. */
    private static List<Face> faces(Maze m, Vec3 cam, Vec3 cp, double h, double y0, double y1, Frustum frustum) {
        List<Face> out = new ArrayList<>();
        for (double[] w : m.walls) {
            boolean alongX = Math.abs(w[0] - w[2]) > Math.abs(w[1] - w[3]);
            double line = alongX ? w[1] : w[0];
            double camN = alongX ? cam.z : cam.x, casN = alongX ? cp.z : cp.x;
            if (Math.abs(camN - line) <= Maze.HALF_THICK + 0.01) continue;   // the camera is in the glass
            double s = Math.signum(camN - line);
            if (Math.signum(casN - line) != s || Math.abs(casN - line) <= Maze.HALF_THICK) continue;   // the caster is not before this face
            if (segDist(w, cp.x, cp.z) > RANGE) continue;
            double plane = line + s * Maze.HALF_THICK;
            double lo = Math.min(alongX ? w[0] : w[1], alongX ? w[2] : w[3]), hi = Math.max(alongX ? w[0] : w[1], alongX ? w[2] : w[3]);
            AABB box = alongX ? new AABB(lo, y0, plane - 0.02, hi, y1, plane + 0.02) : new AABB(plane - 0.02, y0, lo, plane + 0.02, y1, hi);
            if (frustum != null && !frustum.isVisible(box)) continue;
            if (!seen(cam, cp, h, alongX, plane, lo, hi, y0, y1)) continue;
            out.add(new Face(w, alongX, plane, segDist(w, cam.x, cam.z)));
        }
        out.sort(Comparator.comparingDouble(Face::dist));
        return out.size() > MAX ? out.subList(0, MAX) : out;
    }

    /** Whether some of the image (feet, middle, head; the body's width as a margin) is seen through the pane from the camera. */
    private static boolean seen(Vec3 cam, Vec3 cp, double h, boolean alongX, double plane, double lo, double hi, double y0, double y1) {
        double camN = alongX ? cam.z : cam.x, camT = alongX ? cam.x : cam.z;
        double imgN = 2 * plane - (alongX ? cp.z : cp.x), imgT = alongX ? cp.x : cp.z;
        double t = (plane - camN) / (imgN - camN);
        if (!(t > 0 && t < 1)) return false;
        double along = camT + (imgT - camT) * t;
        if (along < lo - 0.6 || along > hi + 0.6) return false;
        for (double k = 0; k <= 1.0; k += 0.5) {
            double y = cam.y + (cp.y + h * k - cam.y) * t;
            if (y >= y0 - 0.3 && y <= y1 + 0.3) return true;
        }
        return false;
    }

    private static double segDist(double[] w, double x, double z) {
        double dx = w[2] - w[0], dz = w[3] - w[1];
        double l2 = dx * dx + dz * dz;
        double t = l2 < 1e-9 ? 0 : Mth.clamp(((x - w[0]) * dx + (z - w[1]) * dz) / l2, 0, 1);
        double px = w[0] + dx * t - x, pz = w[1] + dz * t - z;
        return Math.sqrt(px * px + pz * pz);
    }

    private static void one(PoseStack ps, MultiBufferSource.BufferSource buf, EntityRenderDispatcher d, Entity caster, Vec3 cp, float yaw,
                            float pt, int light, Face f, double y0, double y1) {
        Matrix4f mat = ps.last().pose();
        // 1: mark the face where it is seen (the wall's own depth is there: LEQUAL passes, anything in front of the glass keeps it)
        GL11.glEnable(GL11.GL_STENCIL_TEST);
        RenderSystem.stencilMask(0xFF);
        RenderSystem.clearStencil(0);
        RenderSystem.clear(GL11.GL_STENCIL_BUFFER_BIT, Minecraft.ON_OSX);
        RenderSystem.colorMask(false, false, false, false);
        RenderSystem.depthMask(false);
        RenderSystem.enableDepthTest();
        RenderSystem.depthFunc(GL11.GL_LEQUAL);
        RenderSystem.stencilFunc(GL11.GL_ALWAYS, 1, 0xFF);
        RenderSystem.stencilOp(GL11.GL_KEEP, GL11.GL_KEEP, GL11.GL_REPLACE);
        quad(mat, f, y0, y1);
        // 2: inside the mark the depth goes to the far plane: the image is drawn "behind" the glass whole
        RenderSystem.stencilMask(0x00);
        RenderSystem.stencilFunc(GL11.GL_EQUAL, 1, 0xFF);
        RenderSystem.stencilOp(GL11.GL_KEEP, GL11.GL_KEEP, GL11.GL_KEEP);
        RenderSystem.depthMask(true);
        RenderSystem.depthFunc(GL11.GL_ALWAYS);
        GL11.glDepthRange(1, 1);
        quad(mat, f, y0, y1);
        GL11.glDepthRange(0, 1);
        RenderSystem.depthFunc(GL11.GL_LEQUAL);
        RenderSystem.colorMask(true, true, true, true);
        // 3: the caster through the reflection in the face's plane (a reflection turns the faces' winding over: front = clockwise)
        ps.pushPose();
        if (f.alongX()) {
            ps.translate(0, 0, f.plane());
            ps.last().pose().scale(1, 1, -1);
            ps.last().normal().scale(1, 1, -1);
            ps.translate(0, 0, -f.plane());
        } else {
            ps.translate(f.plane(), 0, 0);
            ps.last().pose().scale(-1, 1, 1);
            ps.last().normal().scale(-1, 1, 1);
            ps.translate(-f.plane(), 0, 0);
        }
        GL11.glFrontFace(GL11.GL_CW);
        try {
            d.render(caster, cp.x, cp.y, cp.z, yaw, pt, ps, buf, light);
        } catch (RuntimeException ex) {
            ru.pohsmp.core.PohCore.LOG.debug("[pohsmp] mirror_labyrinth: reflection not drawn", ex);
        }
        buf.endBatch();
        GL11.glFrontFace(GL11.GL_CCW);
        ps.popPose();
        // 4: the face's depth back (particles, rain and the rest stay behind the glass), then a thin layer of the mirror over the image
        RenderSystem.colorMask(false, false, false, false);
        RenderSystem.depthFunc(GL11.GL_ALWAYS);
        quad(mat, f, y0, y1);
        RenderSystem.depthFunc(GL11.GL_LEQUAL);
        RenderSystem.colorMask(true, true, true, true);
        ZoneDraw.face(buf, mat, f.wall(), f.alongX(), f.plane(), y0, y1, GLASS);
        GL11.glDisable(GL11.GL_STENCIL_TEST);
        RenderSystem.stencilMask(0xFF);
    }

    /** The face as a bare quad (position only) for the stencil and the depth. */
    private static void quad(Matrix4f mat, Face f, double y0, double y1) {
        double[] w = f.wall();
        float x1, z1, x2, z2;
        if (f.alongX()) {
            x1 = (float) w[0];
            x2 = (float) w[2];
            z1 = z2 = (float) f.plane();
        } else {
            z1 = (float) w[1];
            z2 = (float) w[3];
            x1 = x2 = (float) f.plane();
        }
        RenderSystem.setShader(GameRenderer::getPositionShader);
        RenderSystem.disableCull();
        BufferBuilder bb = Tesselator.getInstance().getBuilder();
        bb.begin(VertexFormat.Mode.QUADS, DefaultVertexFormat.POSITION);
        bb.vertex(mat, x1, (float) y0, z1).endVertex();
        bb.vertex(mat, x2, (float) y0, z2).endVertex();
        bb.vertex(mat, x2, (float) y1, z2).endVertex();
        bb.vertex(mat, x1, (float) y1, z1).endVertex();
        BufferUploader.drawWithShader(bb.end());
        RenderSystem.enableCull();
    }

    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void onName(RenderNameTagEvent e) {
        if (drawing) e.setResult(Event.Result.DENY);
    }
}
