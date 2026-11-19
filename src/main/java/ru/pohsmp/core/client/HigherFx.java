package ru.pohsmp.core.client;

import com.mojang.blaze3d.vertex.BufferBuilder;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import java.util.HashMap;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.Map;
import net.minecraft.client.Camera;
import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.client.event.RenderLevelStageEvent;
import net.minecraftforge.event.level.LevelEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import org.joml.Matrix3f;
import org.joml.Matrix4f;
import org.joml.Quaternionf;
import org.joml.Vector3f;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.net.Net.HFx;

/** Visuals of the Higher school spells, driven by HFx packets. */
public final class HigherFx {
    private HigherFx() {}

    private static ResourceLocation tex(String n) {
        return new ResourceLocation(PohCore.MODID, "textures/fx/" + n + ".png");
    }

    private static final ResourceLocation CIRCLE_A = tex("circle_a"), CIRCLE_B = tex("circle_b"), FLARE = tex("flare"),
            BEAM = tex("beam"), RING = tex("ring"), RUNE = tex("rune"), VOID = tex("void"),
            CIRCLE_TABOO = tex("circle_taboo"), RUNE_TABOO = tex("rune_taboo"), CIRCLE_WARD = tex("circle_ward"),
            RIFT_TEAR = tex("rift_tear"), RIFT_CORE = tex("rift_core"), RIFT_EDGE = tex("rift_edge"), FUTHARK = tex("futhark"),
            ORBIT_RUNES = tex("orbit_runes"), ORBIT_DASH = tex("orbit_dash"), ORBIT_SAW = tex("orbit_saw"), ORBIT_STARS = tex("orbit_stars");
    private static final ResourceLocation[] ORBITS = {ORBIT_RUNES, ORBIT_DASH, ORBIT_SAW, ORBIT_STARS};
    private static final ResourceLocation CIRCLE_COVEN = tex("circle_coven"), DOME_CELL = tex("dome_cell");
    private static final ResourceLocation PAT_ALCHEMY = tex("pat_alchemy"), PAT_METATRON = tex("pat_metatron"), PAT_ZODIAC = tex("pat_zodiac"),
            PAT_MANDALA = tex("pat_mandala"), PAT_STARS = tex("pat_stars"), RAYS = tex("rays"), GALAXY_ARMS = tex("galaxy_arms"), GALAXY_STARS = tex("galaxy_stars");
    private static final ResourceLocation[] PATTERNS = {PAT_ALCHEMY, PAT_METATRON, PAT_ZODIAC, PAT_MANDALA, PAT_STARS, RAYS, GALAXY_ARMS, GALAXY_STARS};
    private static final int SILVER = 0xD8DCFF, VIOLET = 0x6A2AD8, GOLD = 0xFFE38A;
    private static final int ALGIZ = 14;
    private static final ResourceLocation[] SIGILS = {tex("sigil_fire"), tex("sigil_ice"), tex("sigil_lightning"), tex("sigil_nature"), tex("sigil_holy"),
            tex("sigil_blood"), tex("sigil_ender"), tex("sigil_evocation"), tex("sigil_eldritch"), tex("sigil_wind")};
    private static final int[] CARD_COLOR = {0xFFC94D, 0xA8C8FF, 0xFF4D4D, 0x7DFFB0};

    private static final class Inst {
        int kind, a, b, dur, i;
        long start;
        Vec3 pos, aux;
        float f;
        long fadeAt = -1;
    }

    private static final Map<Integer, Inst> LIVE = new HashMap<>();
    private static MultiBufferSource.BufferSource SRC;

    private static MultiBufferSource.BufferSource src() {
        if (SRC == null) {
            Map<RenderType, BufferBuilder> m = new LinkedHashMap<>();
            m.put(RenderType.entityTranslucent(VOID), new BufferBuilder(4096));
            m.put(RenderType.entityTranslucent(RIFT_TEAR), new BufferBuilder(1024));
            m.put(RenderType.entityTranslucent(RIFT_CORE), new BufferBuilder(1024));
            m.put(RenderType.eyes(RIFT_EDGE), new BufferBuilder(1024));
            for (ResourceLocation t : new ResourceLocation[] {CIRCLE_A, CIRCLE_B, RING, RUNE, BEAM, FLARE, CIRCLE_TABOO, RUNE_TABOO, CIRCLE_WARD, FUTHARK}) m.put(RenderType.eyes(t), new BufferBuilder(16384));
            for (ResourceLocation t : ORBITS) m.put(RenderType.eyes(t), new BufferBuilder(8192));
            m.put(RenderType.eyes(CIRCLE_COVEN), new BufferBuilder(8192));
            m.put(RenderType.eyes(DOME_CELL), new BufferBuilder(262144));
            for (ResourceLocation t : PATTERNS) m.put(RenderType.eyes(t), new BufferBuilder(4096));
            for (ResourceLocation t : SIGILS) m.put(RenderType.eyes(t), new BufferBuilder(4096));
            SRC = MultiBufferSource.immediateWithBuffers(m, new BufferBuilder(256));
        }
        return SRC;
    }

    public static void handle(HFx m) {
        ClientLevel lvl = Minecraft.getInstance().level;
        if (lvl == null) return;
        long now = lvl.getGameTime();
        if (m.kind == HFx.FLASH) {
            PohHud.flash(m.dur, m.i);
            return;
        }
        if (m.kind == HFx.CUT) {
            DownfallCut.start(m, now);
            if (m.b == ru.pohsmp.core.spell.Cutscene.SILENT_GATE) {
                SilentMusic.start(m.key, m.dur);
                GateStaff.start(m.key, m.a, now);
            } else if (m.b == ru.pohsmp.core.spell.Cutscene.DOWNFALL) {
                GateStaff.startDownfall(m.key, m.a, now);
            }
            return;
        }
        if (m.kind == HFx.ANIM) {   // a = entity id, b = animation (0: pohsmp_coven_ritual; 1/2: held target pose on/off, T13)
            if (m.b == ru.pohsmp.core.spell.TargetPose.HELD_START || m.b == ru.pohsmp.core.spell.TargetPose.HELD_STOP) {
                TargetPoseClient.handle(m.a, m.b);
                return;
            }
            if (lvl.getEntity(m.a) instanceof net.minecraft.world.entity.player.Player p && m.b == 0)
                io.redspace.ironsspellbooks.player.ClientSpellCastHelper.animatePlayerStart(p, new ResourceLocation("irons_spellbooks", "pohsmp_coven_ritual"));
            return;
        }
        if (m.kind == HFx.STOP) {
            DownfallCut.stop(m.key);
            SilentMusic.stop(m.key);
            GateStaff.stop(m.key);
            Inst x = LIVE.get(m.key);
            if (x != null && x.fadeAt < 0) x.fadeAt = now;
            if (x != null && x.kind == HFx.JOINT) JointFx.mark(x.a, now + 10);   // the final flash of the cast still gets both outlines
            return;
        }
        if (m.kind == HFx.JOINT) JointFx.mark(m.a, now + Math.max(1, m.dur) + 10);
        Inst prev = LIVE.get(m.key);
        if ((m.kind == HFx.TABOO || m.kind == HFx.CLOSURE) && prev != null && prev.kind == m.kind && prev.fadeAt < 0) {   // refresh: keep the animation running
            prev.dur = (int) (now - prev.start) + Math.max(1, m.dur);
            prev.pos = new Vec3(m.x, m.y, m.z);
            prev.f = m.f;
            return;
        }
        Inst x = new Inst();
        x.kind = m.kind;
        x.a = m.a;
        x.b = m.b;
        x.dur = Math.max(1, m.dur);
        x.i = m.i;
        x.f = m.f;
        x.pos = new Vec3(m.x, m.y, m.z);
        x.start = now;
        Inst old = LIVE.get(m.key);
        if (old != null && old.kind == m.kind && m.kind == HFx.SEAL) x.start = now;
        LIVE.put(m.key, x);
    }

    @SubscribeEvent
    public static void onUnload(LevelEvent.Unload e) {
        if (e.getLevel().isClientSide()) LIVE.clear();
    }

    @SubscribeEvent
    public static void onRender(RenderLevelStageEvent e) {
        if (e.getStage() != RenderLevelStageEvent.Stage.AFTER_PARTICLES || LIVE.isEmpty()) return;
        Minecraft mc = Minecraft.getInstance();
        ClientLevel lvl = mc.level;
        if (lvl == null) return;
        float pt = e.getPartialTick();
        double time = lvl.getGameTime() + pt;
        Camera cam = e.getCamera();
        Vec3 cp = cam.getPosition();
        PoseStack ps = e.getPoseStack();
        ps.pushPose();
        ps.translate(-cp.x, -cp.y, -cp.z);
        PoseStack.Pose pose = ps.last();
        MultiBufferSource.BufferSource buf = src();
        Iterator<Inst> it = LIVE.values().iterator();
        while (it.hasNext()) {
            Inst x = it.next();
            double age = time - x.start;
            if (age > x.dur + 40 || (x.fadeAt >= 0 && time - x.fadeAt > 10)) {
                it.remove();
                continue;
            }
            float fade = (float) Math.min(1.0, age / 8.0);
            if (x.fadeAt >= 0) fade *= (float) Math.max(0, 1 - (time - x.fadeAt) / 10.0);
            if (age > x.dur && x.kind != HFx.BURST && x.kind != HFx.STAR) fade *= (float) Math.max(0, 1 - (age - x.dur) / 8.0);
            if (fade <= 0.01f) continue;
            Ctx c = new Ctx(lvl, buf, pose, cam, pt, time, age, fade);
            switch (x.kind) {
                case HFx.TELE -> tele(c, x);
                case HFx.SLEEP -> sleep(c, x);
                case HFx.STAR -> star(c, x);
                case HFx.SING -> sing(c, x);
                case HFx.SEAL -> seal(c, x);
                case HFx.ASC -> asc(c, x);
                case HFx.RING -> ring(c, x);
                case HFx.BURST -> burst(c, x);
                case HFx.PILLAR -> pillarFx(c, x);
                case HFx.SKY -> sky(c, x);
                case HFx.MOON -> moon(c, x);
                case HFx.DOWN -> down(c, x);
                case HFx.RIFT -> rift(c, x);
                case HFx.TABOO -> taboo(c, x);
                case HFx.SIGIL -> sigil(c, x);
                case HFx.WARD -> ward(c, x);
                case HFx.MILKY -> milky(c, x);
                case HFx.GALAXY -> galaxy(c, x);
                case HFx.SOUL -> soul(c, x);
                case HFx.TABOO_CAST -> tabooCast(c, x);
                case HFx.BLIZZARD -> blizzard(c, x);
                case HFx.CLOSURE_CAST -> closureCast(c, x);
                case HFx.CLOSURE -> closure(c, x);
                case HFx.CLOSURE_HIT -> closureHit(c, x);
                case HFx.JOINT -> joint(c, x);
                default -> {}
            }
        }
        buf.endBatch();
        ps.popPose();
    }

    private record Ctx(ClientLevel lvl, MultiBufferSource.BufferSource buf, PoseStack.Pose pose, Camera cam, float pt, double time, double age, float fade) {
        VertexConsumer vc(ResourceLocation t) {
            return buf.getBuffer(t == VOID || t == RIFT_TEAR || t == RIFT_CORE ? RenderType.entityTranslucent(t) : RenderType.eyes(t));
        }
    }

    /** Entity b position if it is known on this client, otherwise the stored position (and remember the last seen one). */
    private static Vec3 follow(Ctx c, Inst x, int id) {
        if (id < 0) return x.pos;
        Entity e = c.lvl.getEntity(id);
        if (e != null) x.pos = e.getPosition(c.pt);
        return x.pos;
    }

    private static float height(Ctx c, int id, float def) {
        Entity e = id < 0 ? null : c.lvl.getEntity(id);
        return e == null ? def : e.getBbHeight();
    }

    private static float r(int rgb) { return ((rgb >> 16) & 255) / 255f; }
    private static float g(int rgb) { return ((rgb >> 8) & 255) / 255f; }
    private static float b(int rgb) { return (rgb & 255) / 255f; }

    // ---- kinds ----

    private static void tele(Ctx c, Inst x) {
        Vec3 p = follow(c, x, x.b);
        double k = Math.min(1.0, c.age / x.dur);
        int col = x.i;
        float rad = x.f * (float) (1.35 - 0.35 * k);
        flat(c.vc(CIRCLE_A), c.pose, p.add(0, 0.05, 0), UP, rad, (float) (c.time * 0.06), r(col), g(col), b(col), c.fade * (0.5f + 0.5f * (float) k));
        flat(c.vc(RING), c.pose, p.add(0, 0.07, 0), UP, x.f * (float) (2.2 - 1.2 * k), 0, r(col), g(col), b(col), c.fade * (float) k);
    }

    private static void sleep(Ctx c, Inst x) {
        Vec3 p = follow(c, x, x.b);
        float h = height(c, x.b, 1.8f);
        Vec3 head = p.add(0, h + 0.45, 0);
        int col = x.i;
        flat(c.vc(CIRCLE_B), c.pose, head, UP, 0.65f, (float) (c.time * 0.08), r(col), g(col), b(col), c.fade);
        billboard(c.vc(FLARE), c.pose, p.add(0, h * 0.75, 0), c.cam, 1.1f, 0.35f, 0.15f, 0.6f, c.fade * 0.6f);
        for (int i = 0; i < 3; i++) {
            double ph = c.time * 0.05 + i / 3.0;
            double fr = ph - Math.floor(ph);
            Vec3 q = head.add(Math.sin(fr * 6 + i) * 0.3 + 0.2, fr * 1.2, Math.cos(fr * 6 + i) * 0.3);
            billboard(c.vc(FLARE), c.pose, q, c.cam, 0.18f + 0.12f * (float) fr, 0.75f, 0.55f, 1f, c.fade * (float) (1 - fr));
        }
        flat(c.vc(CIRCLE_A), c.pose, p.add(0, 0.05, 0), UP, 1.2f, (float) (-c.time * 0.03), r(col) * 0.6f, g(col) * 0.6f, b(col) * 0.6f, c.fade * 0.7f);
    }

    /** Pentagram-ish constellation 7 blocks above the target, stars light one by one, then the star falls. */
    private static final double[][] STARS = {{0, 1.6}, {1.5, 0.5}, {0.95, -1.3}, {-0.95, -1.3}, {-1.5, 0.5}};
    private static final int[][] LINKS = {{0, 2}, {2, 4}, {4, 1}, {1, 3}, {3, 0}};

    private static void star(Ctx c, Inst x) {
        Vec3 p = follow(c, x, x.b);
        int col = CARD_COLOR[Math.max(0, Math.min(3, x.i))];
        double k = c.age / x.dur;
        if (k > 1.0) return;
        Vec3 top = p.add(0, 7, 0);
        double rot = c.time * 0.01;
        Vec3[] pts = new Vec3[5];
        for (int s = 0; s < 5; s++) {
            double sx = STARS[s][0] * 1.4, sz = STARS[s][1] * 1.4;
            pts[s] = top.add(sx * Math.cos(rot) - sz * Math.sin(rot), Math.sin(c.time * 0.07 + s) * 0.1, sx * Math.sin(rot) + sz * Math.cos(rot));
        }
        int lit = (int) Math.min(5, Math.floor(k / 0.75 * 5) + 1);
        VertexConsumer fl = c.vc(FLARE), bm = c.vc(BEAM);
        for (int s = 0; s < lit; s++) billboard(fl, c.pose, pts[s], c.cam, 0.55f + 0.1f * (float) Math.sin(c.time * 0.3 + s), r(col), g(col), b(col), c.fade);
        for (int l = 0; l < LINKS.length; l++) {
            if (LINKS[l][0] >= lit || LINKS[l][1] >= lit) continue;
            beamLine(bm, c.pose, pts[LINKS[l][0]], pts[LINKS[l][1]], c.cam, 0.05f, r(col), g(col), b(col), c.fade * 0.8f);
        }
        flat(c.vc(CIRCLE_A), c.pose, p.add(0, 0.05, 0), UP, x.f * (float) (0.4 + 0.6 * k), (float) (c.time * 0.05), r(col), g(col), b(col), c.fade * (float) k);
        if (k > 0.8) {
            double f = (k - 0.8) / 0.2;
            Vec3 s = top.add(0, 0.5, 0).lerp(p.add(0, 0.3, 0), f * f);
            billboard(fl, c.pose, s, c.cam, 1.2f, 1f, 1f, 1f, 1f);
            billboard(fl, c.pose, s, c.cam, 2.0f, r(col), g(col), b(col), 0.8f);
            beamLine(bm, c.pose, top, s, c.cam, 0.25f, r(col), g(col), b(col), 0.7f);
        }
    }

    private static void sing(Ctx c, Inst x) {
        Vec3 p = x.pos;
        double k = Math.min(1.0, c.age / 12.0);
        float size = (float) (0.4 + 0.9 * k + 0.08 * Math.sin(c.time * 0.5));
        if (c.age > x.dur - 6) size *= (float) Math.max(0.05, (x.dur - c.age) / 6.0);
        int col = x.i;
        billboard(c.vc(FLARE), c.pose, p, c.cam, size * 2.6f, r(col), g(col), b(col), c.fade * 0.9f);
        voidDisc(c.vc(VOID), c.pose, p, c.cam, size, c.fade);
        Vec3 n1 = new Vec3(0.35, 1, 0.15).normalize(), n2 = new Vec3(-0.3, 1, -0.4).normalize();
        flat(c.vc(RING), c.pose, p, n1, size * 2.2f, (float) (c.time * 0.2), r(col), g(col), b(col), c.fade);
        flat(c.vc(RING), c.pose, p, n2, size * 1.7f, (float) (-c.time * 0.25), 1f, 0.6f, 1f, c.fade * 0.8f);
        flat(c.vc(CIRCLE_B), c.pose, p.add(0, -0.02, 0), UP, x.f, (float) (-c.time * 0.04), r(col) * 0.5f, g(col) * 0.5f, b(col) * 0.5f, c.fade * 0.5f);
        gyro(c, p, 3, size * 2.6f, (int) x.start, r(col), g(col), b(col), c.fade * 0.7f);
        VertexConsumer bm = c.vc(BEAM);
        for (int i = 0; i < 10; i++) {
            double ph = c.time * 0.035 + i * 0.618;
            double fr = ph - Math.floor(ph);
            double a = i * 2.399 + Math.floor(ph) * 1.3;
            double rr = x.f * (1 - fr);
            Vec3 from = p.add(Math.cos(a) * rr, Math.sin(a * 1.7) * 1.5 * (1 - fr), Math.sin(a) * rr);
            Vec3 to = from.lerp(p, 0.25);
            beamLine(bm, c.pose, from, to, c.cam, 0.04f, r(col), g(col), b(col), c.fade * (float) fr);
        }
    }

    /**
     * Eternal Blizzard: an ice circle on the ground (frost mandala + two counter-rotating circles), glowing frost bands up the wall,
     * a belt of runes on top, and Hagalaz / Isa (hail and ice) runes circling the wall in both directions. The snow itself is
     * Iron's swirling snowflakes sent by the server.
     */
    // ---- Eternal Blizzard: a snowstorm wall at the edge (client particles, see onClientTick), frost on the ground by the wall, wind streaks ----

    private static final ResourceLocation FROST_BAND = tex("frost_band");
    /** Wall band: from R - BLIZ_IN to R + BLIZ_OUT, BLIZ_H high; wind speed along the wall, blocks per tick. */
    private static final double BLIZ_IN = 2.6, BLIZ_OUT = 0.5, BLIZ_H = 7, BLIZ_WIND = 0.32;

    private static void blizzard(Ctx c, Inst x) {
        Vec3 p = x.pos;
        double R = x.f;
        double k = Math.min(1.0, c.age / 20.0);
        // frost creeping from the wall inwards: textured annulus, transparent inside, densest at the wall
        double r0 = R - 2.4 * k, r1 = R + 0.5;
        VertexConsumer fv = c.buf.getBuffer(RenderType.entityTranslucent(FROST_BAND));
        Matrix4f m = c.pose.pose();
        Matrix3f n = c.pose.normal();
        int seg = 96;
        float a = c.fade * 0.9f;
        for (int i = 0; i < seg; i++) {
            double a0 = Math.PI * 2 * i / seg, a1 = Math.PI * 2 * (i + 1) / seg;
            float u0 = i * 8f / seg, u1 = (i + 1) * 8f / seg;   // the band repeats 8 times around
            Vector3f[] v = {
                    new Vector3f((float) (p.x + Math.cos(a0) * r0), (float) p.y + 0.04f, (float) (p.z + Math.sin(a0) * r0)),
                    new Vector3f((float) (p.x + Math.cos(a0) * r1), (float) p.y + 0.04f, (float) (p.z + Math.sin(a0) * r1)),
                    new Vector3f((float) (p.x + Math.cos(a1) * r1), (float) p.y + 0.04f, (float) (p.z + Math.sin(a1) * r1)),
                    new Vector3f((float) (p.x + Math.cos(a1) * r0), (float) p.y + 0.04f, (float) (p.z + Math.sin(a1) * r0))};
            float[][] uv = {{u0, 0}, {u0, 1}, {u1, 1}, {u1, 0}};
            quadUV(fv, c.pose, v, uv, 1f, 1f, 1f, a);
        }
        // gusts: faint smeared streaks running along the wall with the wind
        VertexConsumer bm = c.vc(BEAM);
        java.util.Random rnd = new java.util.Random(x.start * 31L);
        for (int i = 0; i < 48; i++) {
            double rr = R - BLIZ_IN * rnd.nextDouble() + BLIZ_OUT * 0.5, y = 0.3 + rnd.nextDouble() * (BLIZ_H - 0.6) * k;
            double dir = i % 3 == 0 ? -1 : 1, speed = BLIZ_WIND * (0.8 + 0.6 * rnd.nextDouble()) / rr;
            double an = rnd.nextDouble() * Math.PI * 2 + dir * speed * c.time, len = 0.12 + 0.1 * rnd.nextDouble();
            Vec3 q0 = p.add(Math.cos(an) * rr, y, Math.sin(an) * rr), q1 = p.add(Math.cos(an + dir * len) * rr, y + 0.15, Math.sin(an + dir * len) * rr);
            beamLine(bm, c.pose, q0, q1, c.cam, 0.05f, 0.75f, 0.85f, 0.95f, c.fade * 0.22f * (float) k);
        }
    }

    /** Snowflakes of the storm wall and the snowfall inside, spawned on this client every tick for each live blizzard. */
    @SubscribeEvent
    public static void onClientTick(net.minecraftforge.event.TickEvent.ClientTickEvent e) {
        if (e.phase != net.minecraftforge.event.TickEvent.Phase.END || LIVE.isEmpty()) return;
        Minecraft mc = Minecraft.getInstance();
        ClientLevel lvl = mc.level;
        if (lvl == null || mc.isPaused()) return;
        long now = lvl.getGameTime();
        Vec3 cam = mc.gameRenderer.getMainCamera().getPosition();
        net.minecraft.util.RandomSource rnd = lvl.random;
        for (Inst x : LIVE.values()) {
            if (x.kind != HFx.BLIZZARD) continue;
            double age = now - x.start;
            if (age > x.dur || x.fadeAt >= 0) continue;
            double R = x.f, dist = Math.sqrt((cam.x - x.pos.x) * (cam.x - x.pos.x) + (cam.z - x.pos.z) * (cam.z - x.pos.z));
            if (Math.abs(dist - R) > 96) continue;
            double k = Math.min(1.0, age / 20.0) * Math.min(1.0, (x.dur - age) / 20.0);
            int n = (int) (110 * k);
            for (int i = 0; i < n; i++) {   // the wall: denser toward the outer edge, carried along the wall by the wind
                double t = rnd.nextDouble();
                double rr = R + BLIZ_OUT - (BLIZ_IN + BLIZ_OUT) * t * t;
                double an = rnd.nextDouble() * Math.PI * 2, y = x.pos.y + rnd.nextDouble() * BLIZ_H;
                double dir = rnd.nextInt(4) == 0 ? -1 : 1, w = BLIZ_WIND * (0.6 + 0.8 * rnd.nextDouble()) * dir;
                double tx = -Math.sin(an) * w, tz = Math.cos(an) * w;   // tangent, plus a little pull inward so flakes stay on the band
                double vx = tx - Math.cos(an) * 0.03, vz = tz - Math.sin(an) * 0.03, vy = (rnd.nextDouble() - 0.6) * 0.06;
                net.minecraft.core.particles.ParticleOptions o = rnd.nextInt(3) == 0 ? io.redspace.ironsspellbooks.util.ParticleHelper.SNOWFLAKE
                        : net.minecraft.core.particles.ParticleTypes.SNOWFLAKE;
                lvl.addAlwaysVisibleParticle(o, x.pos.x + Math.cos(an) * rr, y, x.pos.z + Math.sin(an) * rr, vx, vy, vz);
            }
            int fall = (int) (14 * k);
            for (int i = 0; i < fall; i++) {   // light snow inside, drifting with the wind
                double an = rnd.nextDouble() * Math.PI * 2, rr = Math.sqrt(rnd.nextDouble()) * (R - BLIZ_IN);
                lvl.addParticle(net.minecraft.core.particles.ParticleTypes.SNOWFLAKE, x.pos.x + Math.cos(an) * rr, x.pos.y + BLIZ_H - rnd.nextDouble() * 2,
                        x.pos.z + Math.sin(an) * rr, -Math.sin(an) * 0.05, -0.05, Math.cos(an) * 0.05);
            }
        }
    }

    /** White haze on the screen of a player standing inside a blizzard (thicker near the wall). */
    @SubscribeEvent
    public static void onGuiHaze(net.minecraftforge.client.event.RenderGuiEvent.Pre e) {
        if (LIVE.isEmpty()) return;
        Minecraft mc = Minecraft.getInstance();
        if (mc.level == null) return;
        Vec3 cam = mc.gameRenderer.getMainCamera().getPosition();
        double now = mc.level.getGameTime() + e.getPartialTick(), best = 0;
        for (Inst x : LIVE.values()) {
            if (x.kind != HFx.BLIZZARD) continue;
            double age = now - x.start;
            if (age > x.dur) continue;
            double dx = cam.x - x.pos.x, dz = cam.z - x.pos.z, d = Math.sqrt(dx * dx + dz * dz);
            if (d > x.f + BLIZ_OUT || cam.y < x.pos.y - 2 || cam.y > x.pos.y + BLIZ_H + 2) continue;
            double k = Math.min(1.0, age / 20.0) * Math.min(1.0, (x.dur - age) / 20.0);
            if (x.fadeAt >= 0) k *= Math.max(0, 1 - (now - x.fadeAt) / 10.0);
            double edge = Math.max(0, 1 - (x.f - d) / BLIZ_IN);   // 0 inside .. 1 in the wall
            best = Math.max(best, k * (0.10 + 0.30 * edge));
        }
        if (best > 0.004) {
            int w = e.getWindow().getGuiScaledWidth(), h = e.getWindow().getGuiScaledHeight();
            e.getGuiGraphics().fill(0, 0, w, h, (int) (best * 255) << 24 | 0xE6F0FA);
        }
    }

    private static void seal(Ctx c, Inst x) {
        Vec3 p = x.pos;
        int col = 0xFF3B3B;
        flat(c.vc(CIRCLE_A), c.pose, p.add(0, 0.05, 0), UP, x.f + 0.35f, (float) (c.time * 0.02), r(col), g(col), b(col), c.fade * 0.8f);
        flat(c.vc(RING), c.pose, p.add(0, 0.07, 0), UP, x.f + 0.1f, 0, r(col), g(col), b(col), c.fade);
        VertexConsumer rv = c.vc(RUNE), bm = c.vc(BEAM);
        for (int i = 0; i < 6; i++) {
            if ((x.i & (1 << i)) == 0) continue;
            double a = i * Math.PI / 3;
            Vec3 q = p.add(Math.cos(a) * x.f, 0, Math.sin(a) * x.f);
            float bob = (float) Math.sin(c.time * 0.12 + i) * 0.08f;
            Vec3 face = new Vec3(Math.cos(a), 0, Math.sin(a));
            rune(c, q.add(0, 1.0 + bob, 0), 9 + i * 3, 0.4f, 1f, 0.35f, 0.3f, c.fade);   // Nauthiz, Ihwaz, Sowilo... binding runes
            flat(c.vc(CIRCLE_B), c.pose, q.add(0, 0.08, 0), UP, 0.45f, (float) (c.time * 0.1), r(col), g(col), b(col), c.fade * 0.8f);
            pillar(bm, c.pose, q, 2.2f, 0.06f, (float) a, 1f, 0.3f, 0.25f, c.fade * 0.6f);
        }
    }

    private static void asc(Ctx c, Inst x) {
        Entity e = c.lvl.getEntity(x.a);
        Vec3 p = e != null ? e.getPosition(c.pt) : x.pos;
        float h = e != null ? e.getBbHeight() : 1.8f;
        int col = x.i;
        VertexConsumer bm = c.vc(BEAM);
        for (int i = 0; i < 4; i++) pillar(bm, c.pose, new Vec3(p.x, x.pos.y - 1, p.z), 60f, 1.1f, i * (float) Math.PI / 4, r(col), g(col), b(col), c.fade * 0.55f);
        flat(c.vc(CIRCLE_A), c.pose, p.add(0, -0.1, 0), UP, 1.8f, (float) (c.time * 0.05), r(col), g(col), b(col), c.fade);
        flat(c.vc(CIRCLE_B), c.pose, p.add(0, h + 0.35, 0), UP, 0.45f, (float) (-c.time * 0.12), 1f, 0.95f, 0.7f, c.fade);
        flat(c.vc(CIRCLE_A), c.pose, new Vec3(p.x, x.pos.y + 0.05, p.z), UP, 3f, (float) (-c.time * 0.02), r(col), g(col), b(col), c.fade * 0.6f);
        gyro(c, p.add(0, h * 0.55, 0), 2, 1.3f, x.a, r(col), g(col), b(col), c.fade * 0.6f);
    }

    private static void ring(Ctx c, Inst x) {
        double k = Math.min(1.0, c.age / x.dur);
        float rad = (float) (1 + (x.f - 1) * k);
        int col = x.i;
        float a = c.fade * (float) (k < 0.85 ? 1 : (1 - k) / 0.15);
        flat(c.vc(RING), c.pose, x.pos.add(0, 0.12, 0), UP, rad, 0, r(col), g(col), b(col), a);
        flat(c.vc(RING), c.pose, x.pos.add(0, 0.5, 0), UP, rad * 0.99f, 0, r(col) * 0.6f, g(col) * 0.6f, b(col), a * 0.6f);
        flat(c.vc(RING), c.pose, x.pos.add(0, 0.9, 0), UP, rad * 0.98f, 0, r(col) * 0.3f, g(col) * 0.4f, b(col), a * 0.3f);
    }

    private static void burst(Ctx c, Inst x) {
        double age = c.age;
        if (age > 30) return;
        int col = x.i;
        if (age < 8) billboard(c.vc(FLARE), c.pose, x.pos, c.cam, x.f * (0.6f + (float) (age / 8.0)), 1f, 1f, 1f, (float) (1 - age / 8.0));
        float rk = (float) Math.max(0, 1 - age / 25.0);
        flat(c.vc(RING), c.pose, x.pos, UP, 0.5f + x.f * (float) (age / 25.0), 0, r(col), g(col), b(col), rk);
        flat(c.vc(CIRCLE_A), c.pose, x.pos, UP, x.f * 0.8f, (float) (c.time * 0.1), r(col), g(col), b(col), rk * 0.7f);
    }

    private static void pillarFx(Ctx c, Inst x) {
        double k = c.age / x.dur;
        if (k > 1) return;
        float a = (float) (k < 0.2 ? k / 0.2 : (1 - k) / 0.8);
        int col = x.i;
        VertexConsumer bm = c.vc(BEAM);
        for (int i = 0; i < 4; i++) pillar(bm, c.pose, x.pos, 40f, x.f * (1.1f - 0.4f * (float) k), i * (float) Math.PI / 4, r(col), g(col), b(col), a);
        billboard(c.vc(FLARE), c.pose, x.pos.add(0, 0.5, 0), c.cam, x.f * 2.2f, r(col), g(col), b(col), a);
    }

    /** A magic circle facing down in the sky; grows in and spins, brighter with time. */
    private static void sky(Ctx c, Inst x) {
        int col = x.i;
        double k = Math.min(1.0, c.age / 20.0);
        float rad = x.f * (float) (0.3 + 0.7 * k);
        float glow = (float) Math.min(1.0, 0.6 + c.age / 300.0);
        Vec3 down = new Vec3(0, -1, 0);
        flat(c.vc(CIRCLE_A), c.pose, x.pos, down, rad, (float) (c.time * 0.03), r(col) * glow, g(col) * glow, b(col) * glow, c.fade);
        flat(c.vc(CIRCLE_B), c.pose, x.pos.add(0, -0.05, 0), down, rad * 0.62f, (float) (-c.time * 0.05), 1f, 0.85f * glow, 0.5f * glow, c.fade);
        flat(c.vc(RING), c.pose, x.pos.add(0, -0.1, 0), down, rad * 1.08f, 0, r(col), g(col), b(col), c.fade * 0.8f);
        flat(c.vc(CIRCLE_A), c.pose, x.pos, UP, rad, (float) (c.time * 0.03), r(col) * 0.6f, g(col) * 0.6f, b(col) * 0.6f, c.fade * 0.6f);
    }

    /** Blood Moon: a crimson moon high over the caster (entity a) and a faint ring of its reach on the ground. */
    private static void moon(Ctx c, Inst x) {
        Vec3 p = follow(c, x, x.a);
        int col = x.i;
        Vec3 m = p.add(0, 26, 0);
        float pulse = 1f + 0.06f * (float) Math.sin(c.time * 0.15);
        billboard(c.vc(FLARE), c.pose, m, c.cam, 16f * pulse, r(col), g(col), b(col), c.fade * 0.8f);
        billboard(c.vc(FLARE), c.pose, m, c.cam, 7f, 1f, 0.35f, 0.3f, c.fade);
        voidDisc(c.vc(VOID), c.pose, m, c.cam, 4.2f, c.fade * 0.55f);
        flat(c.vc(CIRCLE_A), c.pose, m.add(0, -0.3, 0), new Vec3(0, -1, 0), 9f, (float) (c.time * 0.01), r(col), g(col), b(col), c.fade * 0.5f);
        flat(c.vc(RING), c.pose, p.add(0, 0.08, 0), UP, x.f, 0, r(col), g(col) * 0.5f, b(col) * 0.5f, c.fade * 0.45f);
    }

    /** Downfall cast (25 s): circles and runes at the caster (entity a), a sky seal, pillars, the rift seed at pos, a golden thread, convergence. */
    private static void down(Ctx c, Inst x) {
        double t = c.age;
        int col = x.i;
        float cr = r(col), cg = g(col), cb = b(col), fd = c.fade;
        Vec3 n = new Vec3(Math.cos(x.f), 0, Math.sin(x.f));
        Entity e = c.lvl.getEntity(x.a);
        if (e != null) x.aux = e.getPosition(c.pt);
        Vec3 cp = x.aux != null ? x.aux : x.pos.add(n.scale(20));
        Vec3 rc = x.pos.add(0, 2.6, 0);
        double tm = c.time;
        float g1 = (float) Math.min(1, t / 40.0);
        flat(c.vc(CIRCLE_A), c.pose, cp.add(0, 0.05, 0), UP, 6f * g1, (float) (tm * 0.02), cr, cg, cb, fd);
        flat(c.vc(CIRCLE_B), c.pose, cp.add(0, 0.07, 0), UP, 4f * g1, (float) (-tm * 0.04), 1f, 0.9f, 0.6f, fd);
        flat(c.vc(RING), c.pose, cp.add(0, 0.09, 0), UP, 7.2f * g1, 0, cr, cg, cb, fd * 0.8f);
        flat(c.vc(PAT_ALCHEMY), c.pose, cp.add(0, 0.03, 0), UP, 9.5f * g1, (float) (-tm * 0.008), cr, cg, cb, fd * 0.55f);
        for (int i = 0; i < 3; i++) {
            double s = 60 + 30 * i;
            if (t < s) continue;
            float k = (float) Math.min(1, (t - s) / 20.0);
            flat(c.vc(i % 2 == 0 ? CIRCLE_A : CIRCLE_B), c.pose, cp.add(0, 3 + 2 * i, 0), UP, (3.5f - 0.8f * i) * k,
                    (float) (tm * 0.05 * (i % 2 == 0 ? 1 : -1)), cr, cg, cb, fd * 0.9f);
        }
        if (t > 40) {
            float k = (float) Math.min(1, (t - 40) / 20.0);
            for (int i = 0; i < 12; i++) {   // a ring of Futhark runes around the caster
                double a = tm * 0.02 + i * Math.PI / 6;
                Vec3 q = cp.add(Math.cos(a) * 4.5, 1.4 + 0.2 * Math.sin(tm * 0.1 + i), Math.sin(a) * 4.5);
                rune(c, q, i * 2 + 1, 0.45f * k, 1f, 0.85f, 0.4f, fd * k);
            }
            gyro(c, cp.add(0, 1.6, 0), 4, 2.4f * k, x.a, cr, cg, cb, fd * k * 0.8f);
        }
        if (t > 100) {
            float k = (float) Math.min(1, (t - 100) / 60.0);
            Vec3 sky = cp.add(0, 28, 0), dn = new Vec3(0, -1, 0);
            flat(c.vc(CIRCLE_A), c.pose, sky, dn, 18f * k, (float) (tm * 0.01), cr, cg, cb, fd * k);
            flat(c.vc(CIRCLE_B), c.pose, sky.add(0, -0.1, 0), dn, 11f * k, (float) (-tm * 0.02), 1f, 0.9f, 0.5f, fd * k);
            flat(c.vc(RING), c.pose, sky.add(0, -0.2, 0), dn, 20f * k, 0, cr, cg, cb, fd * k * 0.8f);
            voidDisc(c.vc(VOID), c.pose, sky.add(0, 0.5, 0), c.cam, 6f * k, fd * 0.8f * k);
        }
        if (t > 120) {
            float k = (float) Math.min(1, (t - 120) / 40.0);
            VertexConsumer bm = c.vc(BEAM);
            for (int i = 0; i < 6; i++) {
                double a = i * Math.PI / 3 + tm * 0.005;
                Vec3 q = cp.add(Math.cos(a) * 6.5, 0, Math.sin(a) * 6.5);
                pillar(bm, c.pose, q, 30f * k, 0.35f, (float) a, cr, cg, cb, fd * 0.6f * k);
                pillar(bm, c.pose, q, 30f * k, 0.35f, (float) (a + Math.PI / 2), cr, cg, cb, fd * 0.6f * k);
            }
        }
        if (t > 200) {
            float k = (float) Math.min(1, (t - 200) / 120.0);
            billboard(c.vc(FLARE), c.pose, rc, c.cam, 3.5f * k, cr, cg, cb, fd * 0.7f);
            billboardSpin(c.vc(RAYS), c.pose, rc.subtract(n.scale(0.1)), c.cam, 7f * k, (float) (tm * 0.006), cr, cg, cb, fd * 0.45f);
            Vec3 sd = new Vec3(-n.z, 0, n.x), upv = new Vec3(0, 1, 0);
            float sy = 0.25f + 1.6f * k, sx = 0.08f + 0.75f * k * k;   // the crack grows tall first, then widens
            float fl = 0.7f + 0.3f * (float) Math.sin(tm * 0.8);
            oval(c.vc(RIFT_TEAR), c.pose, rc, sd, upv, sx, sy, 0, 1f, 1f, 1f, fd, true);
            oval(c.vc(RIFT_CORE), c.pose, rc.add(n.scale(0.01)), sd, upv, sx, sy, 0, 1f, 1f, 1f, fd * k, true);
            oval(c.vc(RIFT_EDGE), c.pose, rc.add(n.scale(0.03)), sd, upv, sx, sy, 0, cr, cg, cb, fd * fl, false);
            oval(c.vc(RIFT_EDGE), c.pose, rc.subtract(n.scale(0.03)), sd, upv, sx, sy, 0, cr, cg, cb, fd * fl, false);
            flat(c.vc(RING), c.pose, rc, new Vec3(0.35, 1, 0.15).normalize(), 2.6f * k, (float) (tm * 0.2), cr, cg, cb, fd);
            flat(c.vc(RING), c.pose, rc, new Vec3(-0.3, 1, -0.4).normalize(), 2.1f * k, (float) (-tm * 0.25), 1f, 0.95f, 0.7f, fd * 0.8f);
            gyro(c, rc, 4, 3.4f * k, x.a + 5, cr, cg, cb, fd * 0.75f);
            flat(c.vc(CIRCLE_A), c.pose, x.pos.add(0, 0.05, 0), UP, 7f * k, (float) (-tm * 0.03), cr, cg, cb, fd * 0.8f);
        }
        if (t > 260) {
            float k = (float) Math.min(1, (t - 260) / 20.0);
            Vec3 top = cp.add(0, 2.4, 0);
            float w = 0.08f + 0.04f * (float) Math.sin(tm * 0.4);
            beamLine(c.vc(BEAM), c.pose, top, rc, c.cam, w, cr, cg, cb, fd * k);
            beamLine(c.vc(BEAM), c.pose, top, rc, c.cam, w * 3f, cr * 0.5f, cg * 0.4f, cb * 0.2f, fd * k * 0.5f);
        }
        if (t > 380) {
            VertexConsumer bm = c.vc(BEAM);
            for (int i = 0; i < 14; i++) {
                double ph = tm * 0.04 + i * 0.618;
                double fr = ph - Math.floor(ph);
                double a = i * 2.399 + Math.floor(ph) * 1.3;
                double rr = 14 * (1 - fr);
                Vec3 from = rc.add(Math.cos(a) * rr, Math.sin(a * 1.7) * 4 * (1 - fr), Math.sin(a) * rr);
                beamLine(bm, c.pose, from, from.lerp(rc, 0.3), c.cam, 0.06f, cr, cg, cb, fd * (float) fr);
            }
        }
        if (t > 460) {
            float k = (float) Math.min(1, (t - 460) / 40.0);
            billboard(c.vc(FLARE), c.pose, rc, c.cam, 2f + 10f * k, 1f, 0.95f, 0.8f, fd * k);
            flat(c.vc(RING), c.pose, rc, n, 3f + 12f * k, 0, cr, cg, cb, fd * (1 - k));
        }
    }

    /**
     * The open rift (drawn): a torn black silhouette with a dark halo facing n (angle f), the nether depth with burning veins inside,
     * a golden edge with branching cracks, embers drawn into it, rings around it and a circle on the ground.
     */
    private static void rift(Ctx c, Inst x) {
        double t = c.age, tm = c.time;
        float open = (float) smooth(Math.min(1, t / 18.0));
        if (t > x.dur - 20) open *= (float) Math.max(0, (x.dur - t) / 20.0);
        if (open <= 0.01f) return;
        int col = x.i;
        float cr = r(col), cg = g(col), cb = b(col), fd = c.fade;
        Vec3 n = new Vec3(Math.cos(x.f), 0, Math.sin(x.f));
        Vec3 side = new Vec3(-n.z, 0, n.x), up = new Vec3(0, 1, 0);
        Vec3 cc = x.pos.add(0, 2.6, 0);
        float ry = 2.9f * Math.min(1, open * 1.4f), rx = 1.95f * open;
        float pulse = 0.8f + 0.2f * (float) Math.sin(tm * 0.18);
        float breathe = 1f + 0.02f * (float) Math.sin(tm * 0.11);
        oval(c.vc(RIFT_TEAR), c.pose, cc, side, up, rx * breathe, ry * breathe, 0, 1f, 1f, 1f, fd, true);
        oval(c.vc(RIFT_CORE), c.pose, cc.add(n.scale(0.01)), side, up, rx * breathe, ry * breathe, 0, 1f, 1f, 1f, fd * (0.85f + 0.15f * pulse), true);
        oval(c.vc(CIRCLE_B), c.pose, cc.add(n.scale(0.02)), side, up, rx * 0.5f, ry * 0.55f, (float) (tm * 0.05), 0.9f, 0.3f, 0.05f, fd * 0.35f, false);
        oval(c.vc(FLARE), c.pose, cc.add(n.scale(0.03)), side, up, rx * 0.7f, ry * 0.75f, 0, 0.9f, 0.25f, 0.05f, fd * 0.35f * pulse, false);
        float flick = 0.75f + 0.25f * (float) Math.sin(tm * 0.9) * (float) Math.sin(tm * 0.37);
        oval(c.vc(RIFT_EDGE), c.pose, cc.add(n.scale(0.04)), side, up, rx * breathe, ry * breathe, 0, cr, cg, cb, fd * flick, false);
        oval(c.vc(RIFT_EDGE), c.pose, cc.subtract(n.scale(0.04)), side, up, rx * breathe, ry * breathe, 0, cr, cg, cb, fd * flick, false);
        // embers drawn into the rift from all around
        VertexConsumer fl = c.vc(FLARE);
        for (int i = 0; i < 18; i++) {
            double ph = tm * 0.03 + i * 0.618;
            double fr = ph - Math.floor(ph);
            double a = i * 2.399 + Math.floor(ph) * 1.7;
            double rr = 7 * (1 - fr);
            Vec3 q = cc.add(side.scale(Math.cos(a) * rr)).add(up.scale(Math.sin(a) * rr * 0.8)).add(n.scale(Math.sin(a * 1.3) * rr * 0.5));
            billboard(fl, c.pose, q, c.cam, 0.12f + 0.1f * (float) fr, 1f, 0.55f, 0.15f, fd * (float) fr);
        }
        // tilted gold rings and the ground circle
        flat(c.vc(RING), c.pose, cc, n, 3.4f * open, 0, cr, cg, cb, fd * 0.5f);
        flat(c.vc(RING), c.pose, cc, new Vec3(n.x, 0.35, n.z).normalize(), 3.9f * open, (float) (tm * 0.02), cr * 0.6f, cg * 0.5f, cb * 0.2f, fd * 0.35f);
        gyro(c, cc, 3, 3.7f * open, (int) x.start, cr, cg, cb, fd * 0.55f);
        flat(c.vc(CIRCLE_A), c.pose, x.pos.add(0, 0.05, 0), UP, 4.5f * open, (float) (tm * 0.02), cr, cg, cb, fd * 0.7f);
        flat(c.vc(CIRCLE_B), c.pose, x.pos.add(0, 0.07, 0), UP, 2.6f * open, (float) (-tm * 0.04), 1f, 0.45f, 0.1f, fd * 0.6f);
    }
    /**
     * Divine Taboo: a great seal over the whole field (radius f) high in the sky, a second counter-turning seal under it,
     * sixteen seal-runes circling under the rim, light curtains on the border, a golden column and a circle at the center.
     */
    private static void taboo(Ctx c, Inst x) {
        double t = c.age, tm = c.time;
        int col = x.i;
        float cr = r(col), cg = g(col), cb = b(col), fd = c.fade;
        float R = x.f;
        float grow = (float) smooth(Math.min(1, t / 60.0));
        float pulse = 0.85f + 0.15f * (float) Math.sin(tm * 0.05);
        Vec3 o = x.pos, sky = o.add(0, 56, 0), dn = new Vec3(0, -1, 0);
        // the great seal and its layers
        flat(c.vc(CIRCLE_TABOO), c.pose, sky, dn, R * grow, (float) (tm * 0.002), cr * pulse, cg * pulse, cb * pulse, fd);
        flat(c.vc(CIRCLE_TABOO), c.pose, sky.add(0, 0.3, 0), UP, R * grow, (float) (tm * 0.002), cr * 0.5f, cg * 0.5f, cb * 0.5f, fd * 0.6f);
        flat(c.vc(RING), c.pose, sky.add(0, -0.2, 0), dn, R * 1.04f * grow, 0, cr, cg, cb, fd * 0.9f);
        flat(c.vc(CIRCLE_A), c.pose, sky.add(0, -4, 0), dn, R * 0.5f * grow, (float) (-tm * 0.004), 1f, 0.92f, 0.6f, fd * 0.7f);
        flat(c.vc(CIRCLE_B), c.pose, sky.add(0, -7, 0), dn, R * 0.22f * grow, (float) (tm * 0.01), 1f, 0.95f, 0.75f, fd * 0.8f);
        flat(c.vc(PAT_METATRON), c.pose, sky.add(0, -2, 0), dn, R * 0.36f * grow, (float) (tm * 0.003), cr, cg, cb, fd * 0.7f);
        flat(c.vc(PAT_ZODIAC), c.pose, sky.add(0, -10, 0), dn, R * 0.14f * grow, (float) (-tm * 0.012), cr, cg, cb, fd * 0.8f);
        billboardSpin(c.vc(RAYS), c.pose, sky.add(0, -6, 0), c.cam, 30f * grow, (float) (tm * 0.002), cr, cg, cb, fd * 0.5f);
        billboard(c.vc(FLARE), c.pose, sky.add(0, -6, 0), c.cam, 14f * grow * pulse, cr, cg, cb, fd * 0.7f);
        // central column and the ground circle
        if (t > 20) {
            float k = (float) smooth(Math.min(1, (t - 20) / 40.0));
            VertexConsumer bm = c.vc(BEAM);
            for (int i = 0; i < 4; i++) pillar(bm, c.pose, o, 56f * k, 1.4f, i * (float) Math.PI / 4 + (float) (tm * 0.01), cr, cg, cb, fd * 0.55f);
            for (int i = 0; i < 2; i++) pillar(bm, c.pose, o, 56f * k, 0.4f, i * (float) Math.PI / 2, 1f, 1f, 0.9f, fd * 0.8f);
            flat(c.vc(CIRCLE_TABOO), c.pose, o.add(0, 0.06, 0), UP, 7f * k, (float) (-tm * 0.01), cr, cg, cb, fd);
            flat(c.vc(PAT_MANDALA), c.pose, o.add(0, 0.03, 0), UP, 11f * k, (float) (tm * 0.004), cr, cg, cb, fd * 0.45f);
            flat(c.vc(RING), c.pose, o.add(0, 0.08, 0), UP, 8.5f * k, 0, cr, cg, cb, fd * 0.8f);
            gyro(c, o.add(0, 26, 0), 4, 9f * k, (int) x.start, cr, cg, cb, fd * 0.8f);   // the great gyroscope on the column
            gyro(c, o.add(0, 3, 0), 3, 3.2f * k, (int) x.start + 3, cr, cg, cb, fd * 0.7f);
        }
        // seal-runes circling under the rim
        if (t > 40) {
            float k = (float) smooth(Math.min(1, (t - 40) / 40.0));
            VertexConsumer rv = c.vc(RUNE_TABOO);
            for (int i = 0; i < 16; i++) {
                double a = tm * 0.0015 + i * Math.PI / 8;
                Vec3 q = o.add(Math.cos(a) * R * 0.86, 44 + 1.2 * Math.sin(tm * 0.04 + i), Math.sin(a) * R * 0.86);
                Vec3 face = new Vec3(-Math.cos(a), 0, -Math.sin(a));
                flat(rv, c.pose, q, face, 4.5f * k, 0, cr, cg, cb, fd);
                billboard(c.vc(FLARE), c.pose, q, c.cam, 6f * k, cr * 0.6f, cg * 0.5f, cb * 0.3f, fd * 0.5f);
            }
        }
        // light curtains along the border
        if (t > 60) {
            float k = (float) smooth(Math.min(1, (t - 60) / 60.0));
            VertexConsumer bm = c.vc(BEAM);
            for (int i = 0; i < 48; i++) {
                double a = i * Math.PI / 24;
                Vec3 q = o.add(Math.cos(a) * R, -4, Math.sin(a) * R);
                float wave = 0.5f + 0.5f * (float) Math.sin(tm * 0.08 + i * 0.7);
                pillar(bm, c.pose, q, 60f * k, 1.6f, (float) (a + Math.PI / 2), cr, cg, cb, fd * (0.12f + 0.18f * wave));
            }
        }
    }

    /**
     * Ordinary cast: the drawn sigil of the school (b) flashes under the caster (a): it unfolds with an overshoot,
     * a smaller copy rises and fades, a ring runs outward and a short glow lights the center.
     */
    private static void sigil(Ctx c, Inst x) {
        if (x.b < 0 || x.b >= SIGILS.length) return;
        Vec3 p = follow(c, x, x.a);
        double t = c.age;
        int col = x.i;
        float cr = r(col), cg = g(col), cb = b(col);
        float k = (float) Math.min(1, t / 6.0);
        float size = x.f * (k < 1 ? k * 1.15f : 1f + 0.15f * (float) Math.max(0, 1 - (t - 6) / 6.0));
        float out = (float) Math.max(0, 1 - Math.max(0, t - x.dur * 0.6) / (x.dur * 0.4));
        float fd = c.fade * out;
        ResourceLocation tx = SIGILS[x.b];
        flat(c.vc(tx), c.pose, p.add(0, 0.04, 0), UP, size, (float) (c.time * 0.06), cr, cg, cb, fd);
        if (JointFx.isJoint(x.a, c.lvl.getGameTime()))   // joint cast: second outline, raised, wider, turning the other way
            flat(c.vc(tx), c.pose, p.add(0, 0.04 + JointFx.LIFT, 0), UP, size * JointFx.SCALE, (float) (-c.time * 0.09 + JointFx.TURN), cr, cg, cb, fd * JointFx.ALPHA);
        float rise = (float) Math.min(1, t / 20.0);
        flat(c.vc(tx), c.pose, p.add(0, 0.1 + 1.6 * rise, 0), UP, size * (0.65f - 0.25f * rise), (float) (-c.time * 0.1), cr, cg, cb, fd * (1 - rise) * 0.8f);
        if (t < 16) {
            float rk = (float) (t / 16.0);
            flat(c.vc(RING), c.pose, p.add(0, 0.06, 0), UP, x.f * (0.8f + 1.6f * rk), 0, cr, cg, cb, (1 - rk) * c.fade);
        }
        if (t < 10) billboard(c.vc(FLARE), c.pose, p.add(0, 0.4, 0), c.cam, 1.4f * (float) (1 - t / 10.0) + 0.3f, cr, cg, cb, c.fade * 0.8f);
        int seed = (int) x.start * 31 + x.a;
        runeSwarm(c, p, 6, x.f * 0.75f, 2.2f, x.dur - 10, seed, 0.2f, cr, cg, cb, c.fade);
        float gk = (float) smooth(Math.min(1, t / 8.0));
        gyro(c, p.add(0, 1.1, 0), 2, x.f * 0.5f * (0.6f + 0.4f * gk), seed, cr, cg, cb, fd * gk * 0.8f);
    }

    /**
     * Joint cast (T15): the school sigil (i >> 24) under the caster (a) for the whole merged cast, with a double outline: the
     * second layer is raised, wider and turns the other way, shifted by a sixteenth of a turn; a thin ring closes it.
     */
    private static void joint(Ctx c, Inst x) {
        int sb = (x.i >>> 24) & 0xFF, col = x.i & 0xFFFFFF;
        if (sb >= SIGILS.length) sb = 7;
        Vec3 p = follow(c, x, x.a);
        float cr = r(col), cg = g(col), cb = b(col), fd = c.fade;
        float k = (float) smooth(Math.min(1, c.age / 10.0));
        float R = x.f * k;
        ResourceLocation tx = SIGILS[sb];
        flat(c.vc(tx), c.pose, p.add(0, 0.05, 0), UP, R, (float) (c.time * 0.05), cr, cg, cb, fd);
        flat(c.vc(tx), c.pose, p.add(0, 0.05 + JointFx.LIFT, 0), UP, R * JointFx.SCALE, (float) (-c.time * 0.08 + JointFx.TURN), cr, cg, cb, fd * JointFx.ALPHA);
        flat(c.vc(RING), c.pose, p.add(0, 0.07, 0), UP, R * (JointFx.SCALE + 0.12f), 0, cr, cg, cb, fd * 0.5f);
        if (x.b >= 0 && c.lvl.getEntity(x.b) != null) {   // a spark running toward the partner
            Vec3 q = c.lvl.getEntity(x.b).getPosition(c.pt);
            double u = (c.time * 0.05) % 1.0;
            Vec3 s = p.add(q.subtract(p).scale(u)).add(0, 0.25, 0);
            billboard(c.vc(FLARE), c.pose, s, c.cam, 0.35f, cr, cg, cb, fd * 0.8f);
        }
    }

    /** Eight Shields: the ward circle under the caster (a) with eight runes turning with the wall. */
    private static void ward(Ctx c, Inst x) {
        Vec3 p = follow(c, x, x.a);
        int col = x.i;
        float cr = r(col), cg = g(col), cb = b(col), fd = c.fade;
        float k = (float) smooth(Math.min(1, c.age / 12.0));
        float R = x.f;
        flat(c.vc(CIRCLE_WARD), c.pose, p.add(0, 0.04, 0), UP, (R + 0.5f) * k, (float) (-c.time * 0.015), cr, cg, cb, fd * 0.9f);
        flat(c.vc(RING), c.pose, p.add(0, 0.06, 0), UP, (R + 0.7f) * k, 0, cr, cg, cb, fd * 0.6f);
        for (int i = 0; i < 8; i++) {   // Algiz, the rune of protection, over every shield
            double a = c.time * 0.015 + i * Math.PI / 4 + Math.PI / 8;
            Vec3 q = p.add(Math.cos(a) * R, 2.9 + 0.12 * Math.sin(c.time * 0.1 + i), Math.sin(a) * R);
            rune(c, q, ALGIZ, 0.38f * k, cr, cg, cb, fd);
        }
        gyro(c, p.add(0, 1.2, 0), 3, 1.15f * k, x.a, cr, cg, cb, fd * 0.7f);
    }

    // ---- great casts: Milky Way, Soul Devour, Divine Taboo ----

    private static float grow(double t, double from, double len) {
        return (float) smooth((t - from) / len);
    }

    /**
     * "Birth of a galaxy" (Milky Way cast, caster a, f = direction): a great star circle on the ground, violet and silver stars
     * circling the body, a galaxy forming overhead, then the spiral gathering before the hand with stars drawn into it.
     */
    private static void milky(Ctx c, Inst x) {
        Vec3 p = follow(c, x, x.a);
        double t = c.age, tm = c.time;
        float fd = c.fade;
        Vec3 dir = new Vec3(Math.cos(x.f), 0, Math.sin(x.f)), side = new Vec3(-dir.z, 0, dir.x);
        float vr = r(VIOLET), vg = g(VIOLET), vb = b(VIOLET), sr = r(SILVER), sg = g(SILVER), sb = b(SILVER);
        float k1 = grow(t, 0, 40);
        flat(c.vc(PAT_ZODIAC), c.pose, p.add(0, 0.04, 0), UP, 9f * k1, (float) (tm * 0.01), vr, vg, vb, fd);
        flat(c.vc(PAT_STARS), c.pose, p.add(0, 0.06, 0), UP, 6.2f * k1, (float) (-tm * 0.02), sr, sg, sb, fd * 0.7f);
        flat(c.vc(CIRCLE_A), c.pose, p.add(0, 0.08, 0), UP, 10.6f * k1, (float) (tm * 0.006), vr, vg, vb, fd * 0.6f);
        flat(c.vc(RING), c.pose, p.add(0, 0.1, 0), UP, 11.2f * k1, 0, sr, sg, sb, fd * 0.7f);
        if (t > 15) {   // stars circling the body on tilted orbits
            float k = grow(t, 15, 30);
            VertexConsumer fl = c.vc(FLARE);
            for (int i = 0; i < 30; i++) {
                double orb = i % 3, a = tm * (0.06 + 0.02 * orb) + i * 2.4;
                double tl = 0.5 + orb * 0.45, rr = 1.4 + orb * 0.5;
                Vec3 q = new Vec3(Math.cos(a) * rr, Math.sin(a) * Math.sin(tl) * rr * 0.6, Math.sin(a) * Math.cos(tl) * rr);
                boolean silver = i % 2 == 0;
                billboard(fl, c.pose, p.add(0, 1.1, 0).add(q), c.cam, 0.12f + 0.06f * (float) Math.sin(tm * 0.3 + i), silver ? sr : vr, silver ? sg : vg, silver ? sb : vb, fd * k);
            }
            gyro(c, p.add(0, 1.1, 0), 3, 1.7f * k, x.a, sr, sg, sb, fd * k * 0.6f);
        }
        if (t > 50) {   // the galaxy forming overhead
            float k = grow(t, 50, 70);
            Vec3 sky = p.add(0, 9, 0), dn = new Vec3(0, -1, 0);
            flat(c.vc(GALAXY_ARMS), c.pose, sky, dn, 8f * k, (float) (-tm * 0.03), vr, vg, vb, fd * 0.9f);
            flat(c.vc(GALAXY_STARS), c.pose, sky.add(0, -0.1, 0), dn, 8.5f * k, (float) (-tm * 0.025), sr, sg, sb, fd);
            billboard(c.vc(FLARE), c.pose, sky, c.cam, 2.5f * k, sr, sg, sb, fd * 0.8f);
        }
        if (t > 100) {   // the spiral gathering before the hand, stars sucked into it, rays
            float k = grow(t, 100, 90);
            Vec3 hc = p.add(dir.scale(3)).add(0, 1.6, 0), n = dir.scale(0.85).add(0, 0.5, 0).normalize();
            flat(c.vc(GALAXY_ARMS), c.pose, hc, n, (0.6f + 4.4f * k), (float) (-tm * 0.12), vr, vg, vb, fd);
            flat(c.vc(GALAXY_STARS), c.pose, hc, n, (0.7f + 4.8f * k), (float) (-tm * 0.09), sr, sg, sb, fd);
            billboardSpin(c.vc(RAYS), c.pose, hc, c.cam, 1.5f + 3f * k, (float) (tm * 0.02), vr, vg, vb, fd * 0.6f);
            billboard(c.vc(FLARE), c.pose, hc, c.cam, 0.8f + 1.2f * k, sr, sg, sb, fd);
            VertexConsumer fl = c.vc(FLARE);
            for (int i = 0; i < 20; i++) {
                double ph = tm * 0.04 + i * 0.618, fr = ph - Math.floor(ph), a = i * 2.399 + Math.floor(ph) * 1.7, rr = 9 * (1 - fr);
                Vec3 q = hc.add(side.scale(Math.cos(a) * rr)).add(0, Math.sin(a) * rr * 0.6, 0).add(dir.scale(Math.sin(a * 1.3) * rr * 0.4));
                billboard(fl, c.pose, q, c.cam, 0.1f + 0.1f * (float) fr, i % 2 == 0 ? sr : vr, i % 2 == 0 ? sg : vg, i % 2 == 0 ? sb : vb, fd * (float) fr);
            }
        }
        if (t > 150) {   // light falls from the sky galaxy into the spiral
            float k = grow(t, 150, 30);
            Vec3 hc = p.add(dir.scale(3)).add(0, 1.6, 0), sky = p.add(0, 9, 0);
            float w = 0.06f + 0.03f * (float) Math.sin(tm * 0.5);
            beamLine(c.vc(BEAM), c.pose, sky, hc, c.cam, w, sr, sg, sb, fd * k);
            beamLine(c.vc(BEAM), c.pose, sky, hc, c.cam, w * 4, vr, vg, vb, fd * k * 0.5f);
            for (int i = 0; i < 8; i++) {   // runes rising around the caster, again and again
                double h = (tm * 0.025 + i / 8.0) % 1.0, a = tm * 0.04 + i * Math.PI / 4;
                rune(c, p.add(Math.cos(a) * 2.3, 0.3 + 3 * h, Math.sin(a) * 2.3), i * 3 + 1, 0.25f, sr, sg, sb, fd * k * (float) Math.sin(Math.PI * h));
            }
        }
    }

    /**
     * "Galactic flow": the Milky Way spiral travelling along f from the caster (the path is MilkyWaySpell.center on both sides),
     * with a faint trail of stars, stars sucked in and short star streams that throw the caught up every 1.5 s.
     */
    private static void galaxy(Ctx c, Inst x) {
        double t = c.age, tm = c.time;
        float fd = c.fade;
        Vec3 dir = new Vec3(Math.cos(x.f), 0, Math.sin(x.f)), side = new Vec3(-dir.z, 0, dir.x);
        Vec3 ce = ru.pohsmp.core.spell.MilkyWaySpell.center(x.pos, dir, t);
        float R = (float) ru.pohsmp.core.spell.MilkyWaySpell.RAD * (0.3f + 0.7f * grow(t, 0, 10));
        float vr = r(VIOLET), vg = g(VIOLET), vb = b(VIOLET), sr = r(SILVER), sg = g(SILVER), sb = b(SILVER);
        Vec3 n = dir.scale(0.85).add(0, 0.5, 0).normalize();
        flat(c.vc(GALAXY_ARMS), c.pose, ce, n, R * 1.15f, (float) (-tm * 0.09), vr, vg, vb, fd);
        flat(c.vc(GALAXY_ARMS), c.pose, ce, n, R * 0.85f, (float) (-tm * 0.14 + 1), sr, sg, sb, fd * 0.3f);
        flat(c.vc(GALAXY_STARS), c.pose, ce, n, R * 1.25f, (float) (-tm * 0.07), sr, sg, sb, fd);
        flat(c.vc(GALAXY_STARS), c.pose, ce, n.scale(-1), R * 1.05f, (float) (tm * 0.05), vr, vg, vb, fd * 0.6f);
        billboard(c.vc(FLARE), c.pose, ce, c.cam, 2.4f, sr, sg, sb, fd);
        billboardSpin(c.vc(RAYS), c.pose, ce, c.cam, R * 0.9f, (float) (tm * 0.015), vr, vg, vb, fd * 0.55f);
        gyro(c, ce, 2, R * 0.95f, x.a, sr, sg, sb, fd * 0.45f);
        for (int j = 1; j <= 6; j++) {   // the trail: the Milky Way left behind
            if (t - j * 4 < 0) break;
            Vec3 q = ru.pohsmp.core.spell.MilkyWaySpell.center(x.pos, dir, t - j * 4);
            flat(c.vc(GALAXY_STARS), c.pose, q, n, R * (1.1f - 0.08f * j), (float) (-tm * 0.07 + j), sr, sg, sb, fd * (0.5f - 0.07f * j));
        }
        VertexConsumer fl = c.vc(FLARE);
        for (int i = 0; i < 18; i++) {
            double ph = tm * 0.05 + i * 0.618, fr = ph - Math.floor(ph), a = i * 2.399 + Math.floor(ph) * 1.3, rr = R * 1.6 * (1 - fr);
            Vec3 q = ce.add(side.scale(Math.cos(a) * rr)).add(0, Math.sin(a) * rr * 0.7, 0).add(dir.scale(Math.sin(a * 1.7) * rr * 0.5));
            billboard(fl, c.pose, q, c.cam, 0.12f + 0.12f * (float) fr, i % 2 == 0 ? sr : vr, i % 2 == 0 ? sg : vg, i % 2 == 0 ? sb : vb, fd * (float) fr);
        }
        int every = ru.pohsmp.core.spell.MilkyWaySpell.TOSS_EVERY;
        double ph = (t - every / 2.0) % every;
        if (t >= every / 2.0 && ph < 10) {   // star streams shooting up
            float k = (float) (1 - ph / 10);
            java.util.Random rnd = new java.util.Random((long) Math.floor((t - every / 2.0) / every) * 7919 + x.a);
            VertexConsumer bm = c.vc(BEAM);
            for (int i = 0; i < 7; i++) {
                double a = rnd.nextDouble() * Math.PI * 2, rr = rnd.nextDouble() * R;
                Vec3 b0 = ce.add(Math.cos(a) * rr, -3, Math.sin(a) * rr);
                beamLine(bm, c.pose, b0, b0.add(0, 3 + 7 * (1 - k), 0), c.cam, 0.12f, sr, sg, sb, fd * k);
                billboard(fl, c.pose, b0.add(0, 3 + 7 * (1 - k), 0), c.cam, 0.4f, sr, sg, sb, fd * k);
            }
        }
    }

    /**
     * Soul Devour cast (caster a, target b): an alchemical circle under the target and Metatron's cube under the caster,
     * a cage of runes and rings around the target, the soul chain with souls flowing to the caster, a seal in the sky
     * pinning the target with light, rays and an implosion at the end.
     */
    private static void soul(Ctx c, Inst x) {
        Vec3 tp = follow(c, x, x.b);
        Entity ce = c.lvl.getEntity(x.a);
        if (ce != null) x.aux = ce.getPosition(c.pt);
        Vec3 cp = x.aux != null ? x.aux : tp.add(3, 0, 0);
        double t = c.age, tm = c.time, p = Math.min(1, t / x.dur);
        float fd = c.fade;
        int col = x.i;
        float cr = r(col), cg = g(col), cb = b(col), gr = r(GOLD), gg = g(GOLD), gb = b(GOLD);
        float th = height(c, x.b, 1.8f);
        Vec3 tc = tp.add(0, th * 0.6, 0), cc = cp.add(0, 1.3, 0);
        float k1 = grow(t, 0, 40);
        flat(c.vc(PAT_ALCHEMY), c.pose, tp.add(0, 0.04, 0), UP, 3.8f * k1, (float) (tm * 0.015), cr, cg, cb, fd);
        flat(c.vc(CIRCLE_B), c.pose, tp.add(0, 0.06, 0), UP, 2.2f * k1, (float) (-tm * 0.04), cr, cg, cb, fd * 0.7f);
        flat(c.vc(RING), c.pose, tp.add(0, 0.08, 0), UP, 4.4f * k1, 0, cr, cg, cb, fd * 0.7f);
        flat(c.vc(PAT_METATRON), c.pose, cp.add(0, 0.04, 0), UP, 2.8f * k1, (float) (-tm * 0.02), gr, gg, gb, fd);
        flat(c.vc(RING), c.pose, cp.add(0, 0.06, 0), UP, 3.2f * k1, 0, gr, gg, gb, fd * 0.6f);
        if (t > 40) {   // rune cage
            float k = grow(t, 40, 40);
            for (int i = 0; i < 10; i++) {
                double a = tm * 0.03 + i * Math.PI / 5;
                Vec3 q = tp.add(Math.cos(a) * 1.7, 0.6 + (th * 0.9) * (0.5 + 0.5 * Math.sin(tm * 0.05 + i * 1.3)), Math.sin(a) * 1.7);
                rune(c, q, i * 3 + 2, 0.22f * k, cr, cg, cb, fd * k);
            }
        }
        if (t > 80) gyro(c, tc, 3, (1.9f - 0.6f * (float) p) * grow(t, 80, 30), x.b, cr, cg, cb, fd * 0.7f);
        if (t > 120) {   // the soul chain
            float k = grow(t, 120, 30);
            float w = 0.04f + 0.02f * (float) Math.sin(tm * 0.6);
            beamLine(c.vc(BEAM), c.pose, tc, cc, c.cam, w, cr, cg, cb, fd * k);
            beamLine(c.vc(BEAM), c.pose, tc, cc, c.cam, w * 4, cr * 0.5f, cg * 0.5f, cb * 0.5f, fd * k * 0.5f);
            VertexConsumer fl = c.vc(FLARE);
            int n = 4 + (int) (p * 8);
            for (int i = 0; i < n; i++) {
                double kk = (tm * 0.02 + i / (double) n) % 1.0;
                Vec3 q = tc.lerp(cc, kk).add(0, Math.sin(kk * Math.PI) * 1.2, 0);
                billboard(fl, c.pose, q, c.cam, 0.22f, cr, cg, cb, fd * k);
                billboard(fl, c.pose, q, c.cam, 0.08f, 1f, 1f, 1f, fd * k);
            }
        }
        if (t > 200) {   // the seal in the sky pins the target with light
            float k = grow(t, 200, 60);
            Vec3 sky = tp.add(0, 9, 0), dn = new Vec3(0, -1, 0);
            flat(c.vc(PAT_ZODIAC), c.pose, sky, dn, 5.5f * k, (float) (tm * 0.012), cr, cg, cb, fd);
            flat(c.vc(PAT_STARS), c.pose, sky.add(0, -0.1, 0), dn, 3.4f * k, (float) (-tm * 0.03), gr, gg, gb, fd * 0.8f);
            VertexConsumer bm = c.vc(BEAM);
            for (int i = 0; i < 3; i++) pillar(bm, c.pose, tp, 9f * k, 0.5f, i * (float) Math.PI / 3 + (float) (tm * 0.01), cr, cg, cb, fd * 0.45f * k);
        }
        if (t > 300) {   // rays behind the target and the darkening core
            float k = grow(t, 300, 80);
            billboardSpin(c.vc(RAYS), c.pose, tc, c.cam, 1.5f + 2.5f * k, (float) (tm * 0.01), cr, cg, cb, fd * 0.7f);
            voidDisc(c.vc(VOID), c.pose, tc, c.cam, 0.25f + 0.45f * k, fd * 0.7f * k);
        }
        if (t > 420) {   // implosion rings
            for (int i = 0; i < 3; i++) {
                double ph = ((t - 420) / 20.0 + i / 3.0) % 1.0;
                flat(c.vc(RING), c.pose, tc, UP, 5f * (float) (1 - ph), 0, cr, cg, cb, fd * (float) ph);
            }
        }
    }

    /**
     * Divine Taboo cast (caster a, f = zone radius): circles on the ground, a climbing spiral of runes, a column of light rising
     * through four stacked seals to the great seal in the sky, and at the end a sphere of rune rings around the caster.
     */
    private static void tabooCast(Ctx c, Inst x) {
        Vec3 p = follow(c, x, x.a);
        double t = c.age, tm = c.time;
        float fd = c.fade;
        int col = x.i;
        float cr = r(col), cg = g(col), cb = b(col);
        float k1 = grow(t, 0, 50);
        flat(c.vc(PAT_ALCHEMY), c.pose, p.add(0, 0.04, 0), UP, 8f * k1, (float) (tm * 0.008), cr, cg, cb, fd);
        flat(c.vc(CIRCLE_TABOO), c.pose, p.add(0, 0.06, 0), UP, 5.4f * k1, (float) (-tm * 0.015), 1f, 0.95f, 0.75f, fd * 0.8f);
        flat(c.vc(PAT_MANDALA), c.pose, p.add(0, 0.02, 0), UP, 11.5f * k1, (float) (tm * 0.004), cr, cg, cb, fd * 0.45f);
        flat(c.vc(RING), c.pose, p.add(0, 0.08, 0), UP, 12.2f * k1, 0, cr, cg, cb, fd * 0.7f);
        gyro(c, p.add(0, 1.2, 0), 3, 1.4f * k1, x.a, cr, cg, cb, fd * 0.7f);
        if (t > 60) {   // a spiral of runes climbing around the caster
            float k = grow(t, 60, 40);
            for (int i = 0; i < 16; i++) {
                double h = ((tm * 0.02 + i / 16.0) % 1.0);
                double a = tm * 0.05 + i * Math.PI / 8;
                Vec3 q = p.add(Math.cos(a) * 3.2, 0.3 + h * 6, Math.sin(a) * 3.2);
                rune(c, q, i, 0.3f * k, cr, cg, cb, fd * k * (float) Math.sin(Math.PI * h));
            }
        }
        if (t > 100) billboardSpin(c.vc(RAYS), c.pose, p.add(0, 1.3, 0), c.cam, 3.5f * grow(t, 100, 40), (float) (tm * 0.01), cr, cg, cb, fd * 0.6f);
        if (t > 150) {   // the column rising through four seals
            float k = grow(t, 150, 130);
            float h = 56f * k;
            VertexConsumer bm = c.vc(BEAM);
            for (int i = 0; i < 4; i++) pillar(bm, c.pose, p, h, 1.2f, i * (float) Math.PI / 4 + (float) (tm * 0.01), cr, cg, cb, fd * 0.5f);
            for (int i = 0; i < 2; i++) pillar(bm, c.pose, p, h, 0.35f, i * (float) Math.PI / 2, 1f, 1f, 0.9f, fd * 0.8f);
            ResourceLocation[] st = {PAT_STARS, PAT_METATRON, PAT_ZODIAC, CIRCLE_TABOO};
            float[] sr = {4f, 6f, 8f, 10f};
            for (int i = 0; i < 4; i++) {
                double hy = 10 + 12 * i;
                if (h < hy) continue;
                float kk = (float) smooth((h - hy) / 8.0);
                flat(c.vc(st[i]), c.pose, p.add(0, hy, 0), UP, sr[i] * kk, (float) (tm * 0.02 * (i % 2 == 0 ? 1 : -1)), cr, cg, cb, fd * 0.9f);
                flat(c.vc(RING), c.pose, p.add(0, hy - 0.1, 0), UP, sr[i] * 1.1f * kk, 0, cr, cg, cb, fd * 0.6f);
            }
        }
        if (t > 280) {   // the great seal forming in the sky
            float k = grow(t, 280, 160);
            Vec3 sky = p.add(0, 56, 0), dn = new Vec3(0, -1, 0);
            float R = x.f * 0.4f * k;
            flat(c.vc(CIRCLE_TABOO), c.pose, sky, dn, R, (float) (tm * 0.004), cr, cg, cb, fd);
            flat(c.vc(PAT_ALCHEMY), c.pose, sky.add(0, -0.3, 0), dn, R * 0.55f, (float) (-tm * 0.006), 1f, 0.95f, 0.75f, fd * 0.8f);
            flat(c.vc(RING), c.pose, sky.add(0, -0.5, 0), dn, R * 1.05f, 0, cr, cg, cb, fd * 0.8f);
            billboard(c.vc(FLARE), c.pose, sky.add(0, -2, 0), c.cam, 10f * k, cr, cg, cb, fd * 0.7f);
        }
        if (t > 380) ringSphere(c, p.add(0, 1.2, 0), 4.5f, 9, grow(t, 380, 80), cr, cg, cb, fd);
    }

    /**
     * Closing of Space, the 20 s cast (follows the caster a): the Coven seal unfolds on the ground with its heptagram of light pillars,
     * runes spiral up, the great seal forms 40 blocks overhead, and in the last third a small lattice dome grows around the caster.
     */
    private static void closureCast(Ctx c, Inst x) {
        Vec3 p = follow(c, x, x.a);
        double t = c.age, tm = c.time;
        float fd = c.fade;
        int col = x.i;
        float cr = r(col), cg = g(col), cb = b(col);
        float k1 = grow(t, 0, 60);
        flat(c.vc(CIRCLE_COVEN), c.pose, p.add(0, 0.06, 0), UP, 9f * k1, (float) (tm * 0.006), cr, cg, cb, fd);
        flat(c.vc(PAT_MANDALA), c.pose, p.add(0, 0.03, 0), UP, 13f * k1, (float) (-tm * 0.003), cr * 0.8f, cg * 0.8f, cb, fd * 0.45f);
        flat(c.vc(CIRCLE_B), c.pose, p.add(0, 0.08, 0), UP, 3.2f * k1, (float) (-tm * 0.03), 0.9f, 0.85f, 1f, fd * 0.8f);
        flat(c.vc(RING), c.pose, p.add(0, 0.09, 0), UP, 13.6f * k1, 0, cr, cg, cb, fd * 0.7f);
        gyro(c, p.add(0, 1.3, 0), 3, 1.5f * k1, x.a, cr, cg, cb, fd * 0.75f);
        if (t > 40) runeSwarm(c, p, 14, 3f, 6f, 70, x.a, 0.32f, cr, cg, cb, fd * grow(t, 40, 30));
        if (t > 100) {   // seven pillars on the points of the heptagram, each with its own little seal
            float k = grow(t, 100, 60);
            VertexConsumer bm = c.vc(BEAM);
            for (int i = 0; i < 7; i++) {
                double a = -Math.PI / 2 + i * Math.PI * 2 / 7 + tm * 0.002;
                Vec3 q = p.add(Math.cos(a) * 8.2, 0, Math.sin(a) * 8.2);
                for (int j = 0; j < 2; j++) pillar(bm, c.pose, q, 22f * k, 0.5f, j * (float) Math.PI / 2 + (float) a, cr, cg, cb, fd * 0.6f);
                flat(c.vc(CIRCLE_A), c.pose, q.add(0, 0.1, 0), UP, 1.4f * k, (float) (tm * 0.05), 1f, 0.95f, 1f, fd * 0.8f);
                rune(c, q.add(0, 22f * k + 0.6, 0), i * 3 + 1, 0.6f * k, cr, cg, cb, fd);
            }
        }
        if (t > 160) {   // the great Coven seal forming overhead, threads of light from the pillars to it
            float k = grow(t, 160, 120);
            Vec3 sky = p.add(0, 40, 0), dn = new Vec3(0, -1, 0);
            float sr = 30f * k;
            flat(c.vc(CIRCLE_COVEN), c.pose, sky, dn, sr, (float) (tm * 0.003), cr, cg, cb, fd);
            flat(c.vc(PAT_ZODIAC), c.pose, sky.add(0, -0.4, 0), dn, sr * 0.4f, (float) (-tm * 0.008), 1f, 0.9f, 1f, fd * 0.7f);
            flat(c.vc(RING), c.pose, sky.add(0, -0.6, 0), dn, sr * 1.05f, 0, cr, cg, cb, fd * 0.8f);
            billboardSpin(c.vc(RAYS), c.pose, sky.add(0, -2, 0), c.cam, 20f * k, (float) (tm * 0.003), cr, cg, cb, fd * 0.5f);
            for (int i = 0; i < 7; i++) {
                double a = -Math.PI / 2 + i * Math.PI * 2 / 7 + tm * 0.002;
                Vec3 q = p.add(Math.cos(a) * 8.2, 22, Math.sin(a) * 8.2);
                Vec3 s = sky.add(Math.cos(a) * sr * 0.82, 0, Math.sin(a) * sr * 0.82);
                beamLine(c.vc(BEAM), c.pose, q, q.lerp(s, k), c.cam, 0.25f, cr, cg, cb, fd * 0.7f);
            }
        }
        if (t > 260) {   // the dome being born around the caster
            float k = grow(t, 260, 140);
            dome(c, p, 4f + 22f * k, 12, 24, (int) x.start, cr, cg, cb, fd * (0.35f + 0.4f * k));
            ringSphere(c, p.add(0, 1.2, 0), 3.2f, 7, k, cr, cg, cb, fd);
        }
        if (t > 340) billboard(c.vc(FLARE), c.pose, p.add(0, 1.3, 0), c.cam, 6f * grow(t, 340, 60), 0.85f, 0.75f, 1f, fd * 0.8f);
    }

    /**
     * Closing of Space, the dome itself (f = radius): a lattice sphere that grows in 40 ticks, a bright band sweeping up and down it,
     * three rune belts, seven Coven seals set into the shell, the great seal at the zenith and the seal on the ground at the center.
     */
    private static void closure(Ctx c, Inst x) {
        Vec3 o = x.pos;
        double t = c.age, tm = c.time;
        float fd = c.fade;
        int col = x.i;
        float cr = r(col), cg = g(col), cb = b(col);
        float k = (float) smooth(Math.min(1, t / 40.0));
        float R = x.f * k;
        float pulse = 0.85f + 0.15f * (float) Math.sin(tm * 0.05);
        dome(c, o, R, 32, 64, (int) x.start, cr, cg, cb, fd * 0.55f * pulse);
        for (int j = -1; j <= 1; j++) {   // rune belts at the equator and at +-30 degrees
            double lat = j * Math.PI / 6;
            flat(c.vc(j == 0 ? ORBIT_RUNES : ORBIT_DASH), c.pose, o.add(0, R * Math.sin(lat), 0), UP, R * (float) Math.cos(lat) * 1.003f,
                    (float) (tm * 0.002 * (j == 0 ? 1 : -1)), cr, cg, cb, fd * 0.8f);
        }
        for (int i = 0; i < 7; i++) {   // seven seals set into the shell, facing outward, turning slowly
            double a = i * Math.PI * 2 / 7 + tm * 0.0008, lat = Math.toRadians(18);
            Vec3 n = new Vec3(Math.cos(a) * Math.cos(lat), Math.sin(lat), Math.sin(a) * Math.cos(lat));
            flat(c.vc(CIRCLE_COVEN), c.pose, o.add(n.scale(R * 1.004)), n, 11f * k, (float) (tm * 0.006), cr, cg, cb, fd * 0.9f);
        }
        Vec3 top = o.add(0, R - 0.4, 0), dn = new Vec3(0, -1, 0);
        flat(c.vc(CIRCLE_COVEN), c.pose, top, dn, 30f * k, (float) (tm * 0.002), cr * pulse, cg * pulse, cb * pulse, fd);
        flat(c.vc(PAT_STARS), c.pose, top.add(0, -0.3, 0), dn, 18f * k, (float) (-tm * 0.004), 1f, 0.92f, 1f, fd * 0.6f);
        billboard(c.vc(FLARE), c.pose, top.add(0, -2, 0), c.cam, 12f * k * pulse, cr, cg, cb, fd * 0.6f);
        flat(c.vc(CIRCLE_COVEN), c.pose, o.add(0, 0.07, 0), UP, 14f * k, (float) (-tm * 0.004), cr, cg, cb, fd);
        flat(c.vc(PAT_MANDALA), c.pose, o.add(0, 0.04, 0), UP, 20f * k, (float) (tm * 0.002), cr, cg, cb, fd * 0.4f);
        gyro(c, o.add(0, 4, 0), 4, 3f * k, (int) x.start, cr, cg, cb, fd * 0.7f);
    }

    /** A ripple where something struck the shell: a patch of lattice and rings spreading on the surface (a, b: normal yaw/pitch x1000). */
    private static void closureHit(Ctx c, Inst x) {
        double yaw = x.a / 1000.0, pitch = x.b / 1000.0;
        Vec3 n = new Vec3(Math.cos(yaw) * Math.cos(pitch), Math.sin(pitch), Math.sin(yaw) * Math.cos(pitch));
        double k = Math.min(1, c.age / x.dur);
        float a = c.fade * (float) (1 - k);
        int col = x.i;
        float cr = r(col), cg = g(col), cb = b(col);
        flat(c.vc(RING), c.pose, x.pos, n, x.f * (float) (0.3 + 1.2 * k), 0, cr, cg, cb, a);
        flat(c.vc(RING), c.pose, x.pos, n, x.f * (float) (0.15 + 0.7 * k), 0, 1f, 1f, 1f, a * 0.8f);
        flat(c.vc(CIRCLE_COVEN), c.pose, x.pos, n, x.f * 0.6f, (float) (c.time * 0.05), cr, cg, cb, a);
        flat(c.vc(DOME_CELL), c.pose, x.pos, n, x.f * (float) (0.8 + 0.6 * k), 0, cr, cg, cb, a * 1.2f);
        billboard(c.vc(FLARE), c.pose, x.pos, c.cam, x.f * 0.5f, 0.9f, 0.85f, 1f, a);
    }

    /**
     * A lattice sphere of radius R around o (lat x lon cells of the dome texture), with a bright band sweeping up and down
     * and a soft shimmer per cell.
     */
    private static void dome(Ctx c, Vec3 o, float R, int lat, int lon, int seed, float cr, float cg, float cb, float alpha) {
        if (alpha <= 0.01f || R <= 0.2f) return;
        VertexConsumer vc = c.vc(DOME_CELL);
        double band = Math.sin(c.time * 0.012 + seed);
        Vector3f[] v = new Vector3f[4];
        for (int i = 0; i < lat; i++) {
            double t0 = -Math.PI / 2 + Math.PI * i / lat, t1 = -Math.PI / 2 + Math.PI * (i + 1) / lat;
            double ym = Math.sin((t0 + t1) / 2);
            double bd = (ym - band) / 0.09;
            float glow = 0.55f + 1.1f * (float) Math.exp(-bd * bd);
            for (int j = 0; j < lon; j++) {
                double p0 = Math.PI * 2 * j / lon, p1 = Math.PI * 2 * (j + 1) / lon;
                v[0] = sph(o, R, t0, p0);
                v[1] = sph(o, R, t1, p0);
                v[2] = sph(o, R, t1, p1);
                v[3] = sph(o, R, t0, p1);
                float sh = 0.8f + 0.2f * (float) Math.sin(c.time * 0.07 + i * 1.7 + j * 2.3);
                float a = alpha * glow * sh;
                quad(vc, c.pose, v, cr * a, cg * a, cb * a, 1f);
            }
        }
    }

    private static Vector3f sph(Vec3 o, float R, double lat, double lon) {
        double cl = Math.cos(lat);
        return new Vector3f((float) (o.x + R * cl * Math.cos(lon)), (float) (o.y + R * Math.sin(lat)), (float) (o.z + R * cl * Math.sin(lon)));
    }

    /** A sphere of horizontal rune rings around p (built from the bottom up as k goes 0..1), each turning its own way. */
    private static void ringSphere(Ctx c, Vec3 p, float R, int n, float k, float cr, float cg, float cb, float alpha) {
        for (int i = 0; i < n; i++) {
            double lat = -Math.PI / 2 + Math.PI * (i + 0.5) / n;
            float kk = (float) smooth(k * n - i);
            if (kk <= 0.01f) continue;
            float rr = (float) (R * Math.cos(lat)) * kk;
            flat(c.vc(i % 2 == 0 ? ORBIT_RUNES : ORBIT_DASH), c.pose, p.add(0, R * Math.sin(lat), 0), UP, rr, (float) (c.time * 0.03 * (i % 2 == 0 ? 1 : -1.3)), cr, cg, cb, alpha * kk * 0.85f);
        }
    }

    /** A camera-facing quad turned by spin in the view plane (rays, flares). */
    private static void billboardSpin(VertexConsumer vc, PoseStack.Pose pose, Vec3 c, Camera cam, float r, float spin, float cr, float cg, float cb, float alpha) {
        if (alpha <= 0.01f || r <= 0.01f) return;
        Quaternionf q = new Quaternionf(cam.rotation()).rotateZ(spin);
        Vector3f[] v = {new Vector3f(-r, -r, 0), new Vector3f(-r, r, 0), new Vector3f(r, r, 0), new Vector3f(r, -r, 0)};
        for (Vector3f pt : v) q.transform(pt).add((float) c.x, (float) c.y, (float) c.z);
        quad(vc, pose, v, cr * alpha, cg * alpha, cb * alpha, 1f);
    }

    /**
     * A 3-D gyroscope of drawn rings around p: every ring lies on its own tilted plane that slowly precesses around the vertical
     * and turns inside it. n: how many rings (1..4), s: radius scale, seed: varies the tilts between instances.
     */
    private static void gyro(Ctx c, Vec3 p, int n, float s, int seed, float cr, float cg, float cb, float alpha) {
        if (alpha <= 0.01f || s <= 0.01f) return;
        float[] rad = {1.0f, 1.28f, 0.7f, 1.5f};
        double[] tilt = {1.2, 0.62, 0.22, 1.45};
        double[] prec = {0.014, -0.02, 0.027, -0.009};
        double[] spin = {0.035, -0.055, 0.09, 0.02};
        float[] lum = {0.85f, 0.75f, 0.9f, 0.6f};
        double tm = c.time;
        for (int i = 0; i < Math.min(4, n); i++) {
            double az = seed * 0.71 + i * 1.93 + tm * prec[i];
            double tl = tilt[i] + 0.15 * Math.sin(tm * 0.02 + i + seed);
            Vec3 nv = new Vec3(Math.sin(tl) * Math.cos(az), Math.cos(tl), Math.sin(tl) * Math.sin(az));
            flat(c.vc(ORBITS[i]), c.pose, p, nv, rad[i] * s, (float) (tm * spin[i]), cr, cg, cb, alpha * lum[i]);
        }
    }

    /** One rune of the Elder Futhark (0..23 in the usual order) facing the camera, with a soft glow behind it. */
    private static void rune(Ctx c, Vec3 p, int idx, float r, float cr, float cg, float cb, float alpha) {
        if (alpha <= 0.01f || r <= 0.01f) return;
        idx = Math.floorMod(idx, 24);
        float u0 = (idx % 6) / 6f, v0 = (idx / 6) / 4f, u1 = u0 + 1 / 6f, v1 = v0 + 0.25f;
        Quaternionf q = c.cam.rotation();
        Vector3f[] v = {new Vector3f(-r, -r, 0), new Vector3f(-r, r, 0), new Vector3f(r, r, 0), new Vector3f(r, -r, 0)};
        for (Vector3f pt : v) q.transform(pt).add((float) p.x, (float) p.y, (float) p.z);
        float[][] uv = {{u1, v1}, {u1, v0}, {u0, v0}, {u0, v1}};   // same corner order as vanilla particles: upright, not mirrored
        quadUV(c.vc(FUTHARK), c.pose, v, uv, cr * alpha, cg * alpha, cb * alpha, 1f);
        billboard(c.vc(FLARE), c.pose, p, c.cam, r * 1.6f, cr * 0.5f, cg * 0.5f, cb * 0.5f, alpha * 0.5f);
    }

    /**
     * Runes rising in the air around p: n runes picked by seed, each lives life ticks (staggered by 2), circles at radius R
     * and climbs by h, flaring in and fading out.
     */
    private static void runeSwarm(Ctx c, Vec3 p, int n, float R, float h, double life, int seed, float size, float cr, float cg, float cb, float alpha) {
        for (int i = 0; i < n; i++) {
            double lt = (c.age - i * 2) / life;
            if (lt <= 0 || lt >= 1) continue;
            double a = seed * 0.37 + i * 2 * Math.PI / n + c.time * 0.05;
            float rr = R * (0.75f + 0.35f * (float) lt);
            Vec3 q = p.add(Math.cos(a) * rr, 0.25 + h * smooth(lt) + 0.1 * Math.sin(c.time * 0.2 + i), Math.sin(a) * rr);
            float in = (float) Math.sin(Math.PI * lt);
            rune(c, q, seed * 7 + i * 5, size * (0.8f + 0.3f * in), cr, cg, cb, alpha * in);
        }
    }

    private static double smooth(double k) {
        k = Math.max(0, Math.min(1, k));
        return k * k * (3 - 2 * k);
    }

    /** A textured oval in the plane (side, up); spin turns the texture inside it. realAlpha: normal blending (VOID). */
    private static void oval(VertexConsumer vc, PoseStack.Pose pose, Vec3 c, Vec3 side, Vec3 up, float rx, float ry, float spin,
                             float cr, float cg, float cb, float alpha, boolean realAlpha) {
        if (alpha <= 0.01f || rx <= 0.01f || ry <= 0.01f) return;
        double cs = Math.cos(spin), sn = Math.sin(spin);
        double[][] uv = {{-1, -1}, {-1, 1}, {1, 1}, {1, -1}};
        Vector3f[] v = new Vector3f[4];
        for (int i = 0; i < 4; i++) {
            double u = uv[i][0] * cs - uv[i][1] * sn, w = uv[i][0] * sn + uv[i][1] * cs;
            v[i] = vec(c.add(side.scale(u * rx)).add(up.scale(w * ry)));
        }
        if (realAlpha) quad(vc, pose, v, cr, cg, cb, alpha);
        else quad(vc, pose, v, cr * alpha, cg * alpha, cb * alpha, 1f);
    }

    // ---- geometry ----

    private static final Vec3 UP = new Vec3(0, 1, 0);

    private static void flat(VertexConsumer vc, PoseStack.Pose pose, Vec3 c, Vec3 n, float r, float spin, float cr, float cg, float cb, float alpha) {
        if (alpha <= 0.01f || r <= 0.01f) return;
        Quaternionf q = new Quaternionf().rotationTo(0, 1, 0, (float) n.x, (float) n.y, (float) n.z).rotateY(spin);
        Vector3f[] v = {new Vector3f(-r, 0, -r), new Vector3f(-r, 0, r), new Vector3f(r, 0, r), new Vector3f(r, 0, -r)};
        for (Vector3f p : v) q.transform(p).add((float) c.x, (float) c.y, (float) c.z);
        quad(vc, pose, v, cr * alpha, cg * alpha, cb * alpha, 1f);
    }

    private static void billboard(VertexConsumer vc, PoseStack.Pose pose, Vec3 c, Camera cam, float r, float cr, float cg, float cb, float alpha) {
        if (alpha <= 0.01f) return;
        Quaternionf q = cam.rotation();
        Vector3f[] v = {new Vector3f(-r, -r, 0), new Vector3f(-r, r, 0), new Vector3f(r, r, 0), new Vector3f(r, -r, 0)};
        for (Vector3f p : v) q.transform(p).add((float) c.x, (float) c.y, (float) c.z);
        quad(vc, pose, v, cr * alpha, cg * alpha, cb * alpha, 1f);
    }

    /** Black disc (normal blending, real alpha). */
    private static void voidDisc(VertexConsumer vc, PoseStack.Pose pose, Vec3 c, Camera cam, float r, float alpha) {
        Quaternionf q = cam.rotation();
        Vector3f[] v = {new Vector3f(-r, -r, 0), new Vector3f(-r, r, 0), new Vector3f(r, r, 0), new Vector3f(r, -r, 0)};
        for (Vector3f p : v) q.transform(p).add((float) c.x, (float) c.y, (float) c.z);
        quad(vc, pose, v, 1f, 1f, 1f, alpha);
    }

    private static void pillar(VertexConsumer vc, PoseStack.Pose pose, Vec3 base, float h, float w, float yaw, float cr, float cg, float cb, float alpha) {
        if (alpha <= 0.01f || w <= 0.01f) return;
        float dx = (float) Math.cos(yaw) * w, dz = (float) Math.sin(yaw) * w;
        float x = (float) base.x, y = (float) base.y, z = (float) base.z;
        Vector3f[] v = {new Vector3f(x - dx, y, z - dz), new Vector3f(x - dx, y + h, z - dz), new Vector3f(x + dx, y + h, z + dz), new Vector3f(x + dx, y, z + dz)};
        quad(vc, pose, v, cr * alpha, cg * alpha, cb * alpha, 1f);
    }

    private static void beamLine(VertexConsumer vc, PoseStack.Pose pose, Vec3 a, Vec3 b, Camera cam, float w, float cr, float cg, float cb, float alpha) {
        if (alpha <= 0.01f) return;
        Vec3 d = b.subtract(a);
        Vec3 side = d.cross(cam.getPosition().subtract(a));
        if (side.lengthSqr() < 1e-6) return;
        side = side.normalize().scale(w);
        Vector3f[] v = {vec(a.subtract(side)), vec(b.subtract(side)), vec(b.add(side)), vec(a.add(side))};
        quad(vc, pose, v, cr * alpha, cg * alpha, cb * alpha, 1f);
    }

    private static Vector3f vec(Vec3 v) {
        return new Vector3f((float) v.x, (float) v.y, (float) v.z);
    }

    private static final float[][] UV = {{0, 0}, {0, 1}, {1, 1}, {1, 0}};

    private static void quad(VertexConsumer vc, PoseStack.Pose pose, Vector3f[] v, float r, float g, float b, float a) {
        quadUV(vc, pose, v, UV, r, g, b, a);
    }

    private static void quadUV(VertexConsumer vc, PoseStack.Pose pose, Vector3f[] v, float[][] uv, float r, float g, float b, float a) {
        Matrix4f m = pose.pose();
        Matrix3f n = pose.normal();
        for (int i = 0; i < 4; i++) vert(vc, m, n, v[i], uv[i], r, g, b, a);
        for (int i = 3; i >= 0; i--) vert(vc, m, n, v[i], uv[i], r, g, b, a);
    }

    private static void vert(VertexConsumer vc, Matrix4f m, Matrix3f n, Vector3f p, float[] uv, float r, float g, float b, float a) {
        vc.vertex(m, p.x, p.y, p.z).color(r, g, b, a).uv(uv[0], uv[1]).overlayCoords(OverlayTexture.NO_OVERLAY)
                .uv2(LightTexture.FULL_BRIGHT).normal(n, 0, 1, 0).endVertex();
    }
}
