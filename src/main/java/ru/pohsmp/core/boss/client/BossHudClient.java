package ru.pohsmp.core.boss.client;

import com.mojang.blaze3d.systems.RenderSystem;
import com.mojang.blaze3d.vertex.PoseStack;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import net.minecraft.client.Camera;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.Font;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.client.event.RenderGuiEvent;
import net.minecraftforge.client.event.RenderLevelStageEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.boss.BossMath;
import ru.pohsmp.core.boss.BossNet;

/**
 * Titles and spoken lines of the bosses. Titles: textures/gui/title/<base>_<lang>.png (1024×192; ru for Russian clients, en for the
 * rest), half of the screen wide at 30% height, in 0.5 s, held, out 0.75 s, an optional line under it. Lines: a short text over an
 * entity (its colour) for some ticks — «субтитр над ним» of the taunts and surrender phrases.
 */
public final class BossHudClient {
    private BossHudClient() {}

    private record Title(ResourceLocation tex, int hold, String sub, long at) {}

    private record Line(int entity, String key, int ticks, int color, float height, long at) {}

    private static final List<Title> TITLES = new ArrayList<>();
    private static final Map<Integer, Line> LINES = new HashMap<>();

    private static long now() {
        var lvl = Minecraft.getInstance().level;
        return lvl == null ? 0 : ru.pohsmp.core.client.ClientClock.ticks();
    }

    static void onMsg(BossNet.Msg m) {
        if (m.kind == BossNet.TITLE) {
            String lang = Minecraft.getInstance().getLanguageManager().getSelected();
            String l = lang != null && lang.startsWith("ru") ? "ru" : "en";
            TITLES.add(new Title(new ResourceLocation(PohCore.MODID, "textures/gui/title/" + m.s1 + "_" + l + ".png"), m.a, m.s2, now()));
        } else if (m.kind == BossNet.SUBTITLE) {
            LINES.put(m.a, new Line(m.a, m.s1, m.b, m.c, m.f, now()));
        }
    }

    static void clear() {
        TITLES.clear();
        LINES.clear();
    }

    @SubscribeEvent(priority = EventPriority.LOWEST)
    public static void onGui(RenderGuiEvent.Post e) {
        if (TITLES.isEmpty()) return;
        GuiGraphics g = e.getGuiGraphics();
        double t = now() + e.getPartialTick();
        int w = g.guiWidth(), h = g.guiHeight();
        int tw = Math.min(w - 20, Math.max(256, w / 2)), th = tw * 192 / 1024;
        Iterator<Title> it = TITLES.iterator();
        while (it.hasNext()) {
            Title ti = it.next();
            double age = t - ti.at;
            float a = BossMath.titleAlpha(age, ti.hold);
            if (age > ti.hold + BossMath.TITLE_OUT) {
                it.remove();
                continue;
            }
            if (a <= 0) continue;
            int x = (w - tw) / 2, y = (int) (h * 0.30) - th / 2;
            RenderSystem.enableBlend();
            g.setColor(1, 1, 1, a);
            g.blit(ti.tex, x, y, tw, th, 0, 0, 1024, 192, 1024, 192);
            g.setColor(1, 1, 1, 1);
            RenderSystem.disableBlend();
            if (ti.sub != null && !ti.sub.isEmpty()) {
                Font f = Minecraft.getInstance().font;
                Component c = Component.translatable(ti.sub);
                int alpha = Math.max(8, (int) (a * 255));
                g.drawString(f, c, w / 2 - f.width(c) / 2, y + th + 4, (alpha << 24) | 0xE8D9B0, true);
            }
        }
    }

    /** The lines over the entities, as billboards (like name tags, but the boss's colour and longer). */
    @SubscribeEvent
    public static void onLevel(RenderLevelStageEvent e) {
        if (e.getStage() != RenderLevelStageEvent.Stage.AFTER_PARTICLES || LINES.isEmpty()) return;
        Minecraft mc = Minecraft.getInstance();
        if (mc.level == null) return;
        Camera cam = e.getCamera();
        Vec3 cp = cam.getPosition();
        PoseStack ps = e.getPoseStack();
        MultiBufferSource.BufferSource buf = mc.renderBuffers().bufferSource();
        Font font = mc.font;
        long now = now();
        Iterator<Line> it = LINES.values().iterator();
        while (it.hasNext()) {
            Line l = it.next();
            if (now - l.at > l.ticks) {
                it.remove();
                continue;
            }
            Entity en = mc.level.getEntity(l.entity);
            if (en == null) continue;
            Vec3 p = en.getPosition(e.getPartialTick()).add(0, l.height, 0);
            float fade = (float) Math.min(1, Math.min((now - l.at) / 6.0, (l.ticks - (now - l.at)) / 10.0));
            int alpha = Math.max(8, (int) (fade * 255));
            Component c = Component.translatable(l.key);
            ps.pushPose();
            ps.translate(p.x - cp.x, p.y - cp.y, p.z - cp.z);
            ps.mulPose(cam.rotation());
            float s = 0.035f;
            ps.scale(-s, -s, s);
            float x = -font.width(c) / 2f;
            font.drawInBatch(c, x, 0, (alpha << 24) | l.color, false, ps.last().pose(), buf, Font.DisplayMode.SEE_THROUGH, (int) (fade * 0x40) << 24, 0xF000F0);
            ps.popPose();
        }
        buf.endBatch();
    }
}
