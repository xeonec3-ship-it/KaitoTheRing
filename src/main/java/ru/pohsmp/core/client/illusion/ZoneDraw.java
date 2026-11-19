package ru.pohsmp.core.client.illusion;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.Minecraft;
import net.minecraft.client.player.Input;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.client.event.MovementInputUpdateEvent;
import net.minecraftforge.client.event.RenderLevelStageEvent;
import net.minecraftforge.client.event.RenderLivingEvent;
import net.minecraftforge.client.event.RenderNameTagEvent;
import net.minecraftforge.eventbus.api.Event;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.event.TickEvent;
import org.joml.Matrix4f;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.illusion.Maze;

/**
 * T22, what the victim's own client draws inside a zone.
 * «Зеркальный лабиринт»: the maze walls (the same Maze as on the server, by the seed) as mirror panes, cracking towards the end;
 * left and right of the movement keys swapped.
 * «Кошмар наяву»: every other living thing is not drawn (and has no name) - the server puts the faceless monster (fx) on each one, only for it.
 */
public final class ZoneDraw {
    private ZoneDraw() {}

    private static final ResourceLocation WALL = new ResourceLocation(PohCore.MODID, "textures/fx/illusion_mirror_wall.png");
    private static final ResourceLocation CRACKS = new ResourceLocation(PohCore.MODID, "textures/fx/illusion_mirror_wall_cracks.png");

    private static Maze maze;
    private static String mazeKey = "";

    private static Maze maze(Zones.Zone z) {
        String k = z.text() + "@" + z.x() + "," + z.z();
        if (maze == null || !k.equals(mazeKey)) {
            long seed;
            try {
                seed = Long.parseLong(z.text());
            } catch (NumberFormatException ex) {
                seed = 0;
            }
            maze = new Maze(z.x(), z.y(), z.z(), z.r(), seed);
            mazeKey = k;
        }
        return maze;
    }

    @SubscribeEvent
    public static void onInput(MovementInputUpdateEvent e) {
        if (Zones.active(Zones.LABYRINTH) == null && Zones.active(Zones.DREAM) == null) return;   // «Сон бабочки»: the mirror world too
        Input in = e.getInput();
        in.leftImpulse = -in.leftImpulse;
        boolean l = in.left;
        in.left = in.right;
        in.right = l;
    }

    @SubscribeEvent
    public static void onRender(RenderLevelStageEvent e) {
        if (e.getStage() != RenderLevelStageEvent.Stage.AFTER_TRANSLUCENT_BLOCKS) return;
        Zones.Zone z = Zones.active(Zones.LABYRINTH);
        if (z == null) return;
        Maze m = maze(z);
        Vec3 cp = e.getCamera().getPosition();
        PoseStack ps = e.getPoseStack();
        ps.pushPose();
        ps.translate(-cp.x, -cp.y, -cp.z);
        Matrix4f mat = ps.last().pose();
        MultiBufferSource.BufferSource buf = Minecraft.getInstance().renderBuffers().bufferSource();
        long left = z.until() - IllusionClient.now();
        float crack = left < 60 ? (float) (1 - left / 60.0) : 0f;
        double y0 = m.cy - Maze.BELOW, y1 = m.cy + Maze.ABOVE;
        VertexConsumer vc = buf.getBuffer(RenderType.entityTranslucent(WALL));
        for (double[] w : m.walls) pane(vc, mat, w, y0, y1, 0.9f);
        buf.endBatch(RenderType.entityTranslucent(WALL));
        if (crack > 0) {
            VertexConsumer cc = buf.getBuffer(RenderType.entityTranslucent(CRACKS));
            for (double[] w : m.walls) pane(cc, mat, w, y0, y1, crack);
            buf.endBatch(RenderType.entityTranslucent(CRACKS));
        }
        ps.popPose();
    }

    /** Both faces of a wall (offset by its half thickness), the texture once per 3x3 cell. */
    private static void pane(VertexConsumer vc, Matrix4f mat, double[] w, double y0, double y1, float a) {
        boolean alongX = Math.abs(w[0] - w[2]) > Math.abs(w[1] - w[3]);
        double ox = alongX ? 0 : Maze.HALF_THICK, oz = alongX ? Maze.HALF_THICK : 0;
        float u = (float) (Math.max(Math.abs(w[0] - w[2]), Math.abs(w[1] - w[3])) / Maze.CELL);
        float v = (float) ((y1 - y0) / Maze.CELL);
        for (int s = -1; s <= 1; s += 2) {
            double x1 = w[0] + ox * s, z1 = w[1] + oz * s, x2 = w[2] + ox * s, z2 = w[3] + oz * s;
            float nx = (float) (ox * s / Maze.HALF_THICK), nz = (float) (oz * s / Maze.HALF_THICK);
            v(vc, mat, x1, y0, z1, 0, v, a, nx, nz);
            v(vc, mat, x2, y0, z2, u, v, a, nx, nz);
            v(vc, mat, x2, y1, z2, u, 0, a, nx, nz);
            v(vc, mat, x1, y1, z1, 0, 0, a, nx, nz);
        }
    }

    private static void v(VertexConsumer vc, Matrix4f m, double x, double y, double z, float u, float v, float a, float nx, float nz) {
        vc.vertex(m, (float) x, (float) y, (float) z).color(1f, 1f, 1f, a).uv(u, v).overlayCoords(OverlayTexture.NO_OVERLAY)
                .uv2(LightTexture.FULL_BRIGHT).normal(nx, 0, nz).endVertex();
    }

    /** «Кошмар наяву»: the real models of everyone else are gone for the victim (the monsters are fx from the server). */
    @SubscribeEvent(priority = EventPriority.HIGH)
    public static void onLiving(RenderLivingEvent.Pre<?, ?> e) {
        LivingEntity le = e.getEntity();
        if (le == Minecraft.getInstance().player || Zones.active(Zones.NIGHTMARE) == null) return;
        e.setCanceled(true);
    }

    @SubscribeEvent(priority = EventPriority.HIGH)
    public static void onName(RenderNameTagEvent e) {
        if (e.getEntity() instanceof LivingEntity && e.getEntity() != Minecraft.getInstance().player && Zones.active(Zones.NIGHTMARE) != null)
            e.setResult(Event.Result.DENY);
    }

    /** «Сон бабочки»: health the hearts hide (the held back damage, owner 19.11), drawn as if already lost. */
    static float fakeLoss;
    private static float realHealth = -1;

    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void onHeartsPre(net.minecraftforge.client.event.RenderGuiOverlayEvent.Pre e) {
        var p = Minecraft.getInstance().player;
        if (fakeLoss <= 0 || p == null || !e.getOverlay().id().equals(net.minecraftforge.client.gui.overlay.VanillaGuiOverlay.PLAYER_HEALTH.id())) return;
        realHealth = p.getHealth();
        p.setHealth(Math.max(0.5f, realHealth - fakeLoss));   // client copy only, for this one draw; put back in Post
    }

    @SubscribeEvent(priority = EventPriority.LOWEST)
    public static void onHeartsPost(net.minecraftforge.client.event.RenderGuiOverlayEvent.Post e) {
        restore();
    }

    /** Also when another handler cancels the hearts' Pre (no Post comes then): put the health back the next frame. */
    @SubscribeEvent
    public static void onFrame(TickEvent.RenderTickEvent e) {
        if (e.phase == TickEvent.Phase.START) restore();
    }

    private static void restore() {
        var p = Minecraft.getInstance().player;
        if (realHealth >= 0 && p != null) p.setHealth(realHealth);
        realHealth = -1;
    }

    /** «Сон бабочки»: the «death» in the dream - the screen goes dark, a line, and back (the server moves the player meanwhile). */
    private static long deathFrom = -1, deathTo = -1;

    static void dreamDeath(int ticks) {
        deathFrom = IllusionClient.now();
        deathTo = deathFrom + Math.max(10, ticks);
    }

    @SubscribeEvent
    public static void onGui(net.minecraftforge.client.event.RenderGuiEvent.Post e) {
        if (deathTo < 0) return;
        long now = IllusionClient.now();
        if (now >= deathTo) {
            deathFrom = deathTo = -1;
            return;
        }
        double t = now - deathFrom + e.getPartialTick(), len = deathTo - deathFrom;
        float a = (float) Math.min(1, Math.min(t / 6.0, (len - t) / 14.0));
        if (a <= 0) return;
        var g = e.getGuiGraphics();
        int w = g.guiWidth(), h = g.guiHeight();
        g.fill(0, 0, w, h, ((int) (a * 235) << 24) | 0x0A0614);
        var font = Minecraft.getInstance().font;
        var line = net.minecraft.network.chat.Component.translatable("ui.pohsmp_core.butterfly_dream.died");
        int tw = font.width(line);
        int alpha = Math.max(4, (int) (a * 255));
        g.drawString(font, line, (w - tw) / 2, h / 2 - 4, (alpha << 24) | 0xD9C8FF, false);
    }

    static void clear() {
        deathFrom = deathTo = -1;
        maze = null;
        mazeKey = "";
        fakeLoss = 0;
        realHealth = -1;
    }
}
