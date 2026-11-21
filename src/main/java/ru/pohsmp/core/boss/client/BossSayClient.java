package ru.pohsmp.core.boss.client;

import com.mojang.blaze3d.systems.RenderSystem;
import java.util.List;
import net.minecraft.ChatFormatting;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.Font;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.resources.sounds.SimpleSoundInstance;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.Style;
import net.minecraft.network.chat.TextColor;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.util.RandomSource;
import net.minecraftforge.client.event.RegisterGuiOverlaysEvent;
import net.minecraftforge.client.gui.overlay.ForgeGui;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.boss.BossNet;
import ru.pohsmp.core.boss.BossSayMath;
import ru.pohsmp.core.client.ClientClock;
import ru.pohsmp.core.client.ClientConfig;

/**
 * The bosses' spoken lines as a subtitle «свиток» at the bottom centre, over the hotbar (owner 21.11: «красиво, а не как в чате»).
 * The speaker's name in the boss colour between two small marks, a fading thread under it, the phrase in italic parchment white typed
 * letter by letter (40/s, a quiet pen sound), held by its length, faded out; lines in a row queue up (timings, wrapping, the queue,
 * the layout: {@link BossSayMath}). Every boss has its own scroll: textures/gui/boss_say/&lt;boss&gt;.png (48×32, a 9-slice with 12 px
 * sides and 8 px top/bottom) and &lt;boss&gt;_mark.png (18×9: the left mark, then the right one). Drawn by a GUI overlay above all the
 * others; BossCam lets it through in the scenes that hide the HUD, then it sits over the letterbox bar.
 *
 * <p>System lines of a fight (BossNet.SAY c = {@link BossSayMath#SYSTEM}: «Эреб исчез. Бой окончен.», «%s — предмет ревности Ирины»;
 * owner 21.11) go through the same queue but are not speech: the neutral «default» scroll, no name and no thread, the text upright
 * in a cool grey-white, the boss's own marks dimmed beside it as the only sign of whose fight it is, no pen sound.
 */
public final class BossSayClient {
    private BossSayClient() {}

    public static final ResourceLocation OVERLAY_ID = new ResourceLocation(PohCore.MODID, "boss_say");
    private static final int TEX_W = 48, TEX_H = 32, SIDE = 12, EDGE = 8, MARK = 9;
    private static final Style ITALIC = Style.EMPTY.withItalic(true);

    /** What one line draws. */
    private record Said(Component name, int color, String text, String style, boolean system) {}

    private static final BossSayMath.Queue<Said> QUEUE = new BossSayMath.Queue<>();
    private static BossSayMath.Line<Said> soundLine;
    private static int soundVisible;
    private static final RandomSource RNG = RandomSource.create();

    public static void overlays(RegisterGuiOverlaysEvent e) {
        e.registerAboveAll(OVERLAY_ID.getPath(), BossSayClient::render);
    }

    static void onMsg(BossNet.Msg m) {
        if (m.c == BossSayMath.SYSTEM) {
            system(m);
            return;
        }
        Component name;
        try {
            name = Component.Serializer.fromJson(m.s2);
        } catch (RuntimeException ex) {
            name = null;
        }
        if (name == null) name = Component.literal("?");
        String text = Component.translatable(m.s1).getString();
        Said s = new Said(name, m.b & 0xFFFFFF, text, BossSayMath.styleName(m.d), false);
        QUEUE.push(new BossSayMath.Line<>(s, text.strip().length()), ClientClock.now(Minecraft.getInstance().getPartialTick()));
        if (ClientConfig.SAY_TO_CHAT.get()) {
            Component line = Component.literal(text).withStyle(Style.EMPTY.withColor(TextColor.fromRgb(s.color)).withItalic(true));
            Minecraft.getInstance().gui.getChat().addMessage(Component.empty().append(name.copy().withStyle(st -> st.withColor(s.color)))
                    .append(Component.literal(": ").withStyle(ChatFormatting.GRAY)).append(line));
        }
    }

    /** A system line: s1 the lang key, s2 its packed arguments (plain strings), d the boss style (whose marks stand by it). */
    private static void system(BossNet.Msg m) {
        Object[] args = BossSayMath.unpackArgs(m.s2);
        String text = Component.translatable(m.s1, args).getString();
        Said s = new Said(Component.empty(), m.b & 0xFFFFFF, text, BossSayMath.styleName(m.d), true);
        QUEUE.push(new BossSayMath.Line<>(s, text.strip().length()), ClientClock.now(Minecraft.getInstance().getPartialTick()));
        if (ClientConfig.SAY_TO_CHAT.get()) Minecraft.getInstance().gui.getChat().addMessage(Component.literal(text).withStyle(ChatFormatting.GRAY));
    }

    static void clear() {
        QUEUE.clear();
        soundLine = null;
    }

    static void render(ForgeGui gui, GuiGraphics g, float partialTick, int w, int h) {
        Minecraft mc = Minecraft.getInstance();
        if (mc.level == null) return;
        double now = ClientClock.now(partialTick);
        BossSayMath.Line<Said> l = QUEUE.update(now);
        if (l == null) return;
        Said s = l.payload;
        double age = l.age(now);
        float a = BossSayMath.alpha(age, l.outAt());
        int visible = BossSayMath.visible(age, l.chars);
        typingSound(mc, l, visible);
        if (a < 0.03f) return;

        Font f = mc.font;
        if (s.system) {
            renderSystem(gui, g, f, l, s, w, h, partialTick, age, a, visible);
            return;
        }
        List<String> lines = BossSayMath.wrap(s.text, BossSayMath.maxTextWidth(w), t -> f.width(italic(t)));
        int textW = 0;
        for (String t : lines) textW = Math.max(textW, f.width(italic(t)));
        int nameW = f.width(s.name);
        int bw = BossSayMath.boxWidth(nameW, textW, w), bh = BossSayMath.boxHeight(lines.size());
        int hud = BossCam.hudHidden() ? 0 : Math.max(gui.leftHeight, gui.rightHeight);
        int bottom = BossSayMath.bottom(h, hud, BossCam.barHeight(partialTick, h));
        int x = (w - bw) / 2, y = bottom - bh + (int) Math.round(BossSayMath.rise(age, l.outAt()));
        ResourceLocation tex = new ResourceLocation(PohCore.MODID, "textures/gui/boss_say/" + s.style + ".png");
        ResourceLocation mark = new ResourceLocation(PohCore.MODID, "textures/gui/boss_say/" + s.style + "_mark.png");

        RenderSystem.enableBlend();
        RenderSystem.defaultBlendFunc();
        g.setColor(1, 1, 1, a);
        nineSlice(g, tex, x, y, bw, bh);
        int ny = y + BossSayMath.PAD_TOP;
        int nx = w / 2 - nameW / 2;
        g.blit(mark, nx - MARK - 4, ny - 1, 0, 0, MARK, MARK, 2 * MARK, MARK);
        g.blit(mark, nx + nameW + 3, ny - 1, MARK, 0, MARK, MARK, 2 * MARK, MARK);
        g.setColor(1, 1, 1, 1);

        int al = Math.max(4, Math.round(a * 255)) << 24;
        g.drawString(f, s.name, nx, ny, al | s.color, true);
        thread(g, w / 2, ny + BossSayMath.NAME_H + 1, Math.min(bw - 2 * BossSayMath.PAD_X, Math.max(nameW + 48, textW * 3 / 4)), s.color, a);
        int ty = ny + BossSayMath.NAME_H + BossSayMath.NAME_GAP;
        int tc = BossSayMath.textColor(s.color);
        List<String> typed = BossSayMath.typed(lines, visible);
        for (int i = 0; i < lines.size(); i++) {
            String part = typed.get(i);
            if (!part.isEmpty()) {
                int lx = w / 2 - f.width(italic(lines.get(i))) / 2;   // centred by the whole line: the text does not slide while typed
                g.drawString(f, italic(part), lx, ty + i * BossSayMath.LINE_H, al | tc, true);
            }
        }
        RenderSystem.disableBlend();
    }

    /** The system scroll: «default» texture, no name, the text upright in SYSTEM_TEXT, the boss marks dimmed beside the first line. */
    private static void renderSystem(ForgeGui gui, GuiGraphics g, Font f, BossSayMath.Line<Said> l, Said s, int w, int h, float partialTick,
                                     double age, float a, int visible) {
        List<String> lines = BossSayMath.wrap(s.text, BossSayMath.maxTextWidth(w) - 2 * 13, f::width);
        int textW = 0;
        for (String t : lines) textW = Math.max(textW, f.width(t));
        int bw = BossSayMath.systemBoxWidth(textW, w), bh = BossSayMath.systemBoxHeight(lines.size());
        int hud = BossCam.hudHidden() ? 0 : Math.max(gui.leftHeight, gui.rightHeight);
        int bottom = BossSayMath.bottom(h, hud, BossCam.barHeight(partialTick, h));
        int x = (w - bw) / 2, y = bottom - bh + (int) Math.round(BossSayMath.rise(age, l.outAt()));
        ResourceLocation tex = new ResourceLocation(PohCore.MODID, "textures/gui/boss_say/default.png");
        ResourceLocation mark = new ResourceLocation(PohCore.MODID, "textures/gui/boss_say/" + s.style + "_mark.png");
        int ty = y + BossSayMath.PAD_TOP;

        RenderSystem.enableBlend();
        RenderSystem.defaultBlendFunc();
        g.setColor(1, 1, 1, a);
        nineSlice(g, tex, x, y, bw, bh);
        g.setColor(1, 1, 1, a * BossSayMath.SYSTEM_MARK_ALPHA);
        int fw = lines.isEmpty() ? 0 : f.width(lines.get(0));
        g.blit(mark, w / 2 - fw / 2 - MARK - 4, ty - 1, 0, 0, MARK, MARK, 2 * MARK, MARK);
        g.blit(mark, w / 2 + fw / 2 + 3, ty - 1, MARK, 0, MARK, MARK, 2 * MARK, MARK);
        g.setColor(1, 1, 1, 1);
        int al = Math.max(4, Math.round(a * 255)) << 24;
        List<String> typed = BossSayMath.typed(lines, visible);
        for (int i = 0; i < lines.size(); i++) {
            String part = typed.get(i);
            if (!part.isEmpty()) g.drawString(f, part, w / 2 - f.width(lines.get(i)) / 2, ty + i * BossSayMath.LINE_H, al | BossSayMath.SYSTEM_TEXT, true);
        }
        RenderSystem.disableBlend();
    }

    private static Component italic(String s) {
        return Component.literal(s).withStyle(ITALIC);
    }

    /** The thin thread under the name: the boss colour, fading to both ends. */
    private static void thread(GuiGraphics g, int cx, int y, int width, int rgb, float a) {
        int half = Math.max(8, width / 2);
        for (int i = 0; i < half; i += 2) {
            double k = 1 - (double) i / half;
            int alpha = (int) (a * 150 * k * k);
            if (alpha < 4) continue;
            int c = (alpha << 24) | rgb;
            g.fill(cx + i, y, cx + i + 2, y + 1, c);
            g.fill(cx - i - 2, y, cx - i, y + 1, c);
        }
    }

    /** 9-slice of a TEX_W×TEX_H texture: the corners as they are, the sides and the middle stretched (they are plain along that axis). */
    private static void nineSlice(GuiGraphics g, ResourceLocation tex, int x, int y, int w, int h) {
        int cw = TEX_W - 2 * SIDE, ch = TEX_H - 2 * EDGE, mw = w - 2 * SIDE, mh = h - 2 * EDGE;
        // corners
        g.blit(tex, x, y, SIDE, EDGE, 0, 0, SIDE, EDGE, TEX_W, TEX_H);
        g.blit(tex, x + w - SIDE, y, SIDE, EDGE, TEX_W - SIDE, 0, SIDE, EDGE, TEX_W, TEX_H);
        g.blit(tex, x, y + h - EDGE, SIDE, EDGE, 0, TEX_H - EDGE, SIDE, EDGE, TEX_W, TEX_H);
        g.blit(tex, x + w - SIDE, y + h - EDGE, SIDE, EDGE, TEX_W - SIDE, TEX_H - EDGE, SIDE, EDGE, TEX_W, TEX_H);
        if (mw > 0) {
            g.blit(tex, x + SIDE, y, mw, EDGE, SIDE, 0, cw, EDGE, TEX_W, TEX_H);
            g.blit(tex, x + SIDE, y + h - EDGE, mw, EDGE, SIDE, TEX_H - EDGE, cw, EDGE, TEX_W, TEX_H);
        }
        if (mh > 0) {
            g.blit(tex, x, y + EDGE, SIDE, mh, 0, EDGE, SIDE, ch, TEX_W, TEX_H);
            g.blit(tex, x + w - SIDE, y + EDGE, SIDE, mh, TEX_W - SIDE, EDGE, SIDE, ch, TEX_W, TEX_H);
        }
        if (mw > 0 && mh > 0) g.blit(tex, x + SIDE, y + EDGE, mw, mh, SIDE, EDGE, cw, ch, TEX_W, TEX_H);
    }

    /** A quiet pen scratch every few typed letters (vanilla cartography table sound, very low, high pitch: a whisper of the quill). */
    private static void typingSound(Minecraft mc, BossSayMath.Line<Said> l, int visible) {
        if (soundLine != l) {
            soundLine = l;
            soundVisible = 0;
        }
        if (visible <= soundVisible) return;
        int n = BossSayMath.sounds(soundVisible, visible);
        soundVisible = visible;
        if (n <= 0 || !ClientConfig.SAY_SOUND.get() || visible >= l.chars + 1 || l.payload.system) return;
        float pitch = 1.55f + RNG.nextFloat() * 0.4f;
        mc.getSoundManager().play(SimpleSoundInstance.forUI(SoundEvents.UI_CARTOGRAPHY_TABLE_TAKE_RESULT, pitch, 0.09f));
    }
}
