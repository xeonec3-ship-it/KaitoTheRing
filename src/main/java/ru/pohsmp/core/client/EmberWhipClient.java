package ru.pohsmp.core.client;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import net.minecraft.client.Camera;
import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.player.AbstractClientPlayer;
import net.minecraft.client.renderer.LevelRenderer;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.client.resources.model.BakedModel;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.HumanoidArm;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.item.ItemDisplayContext;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.Vec3;
import net.minecraft.world.phys.shapes.VoxelShape;
import net.minecraftforge.client.event.RenderLevelStageEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.level.LevelEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import org.joml.Matrix3f;
import org.joml.Matrix4f;
import org.joml.Vector4f;
import ru.pohsmp.core.client.fx.FxDraw;
import ru.pohsmp.core.ember.EmberBlade;
import ru.pohsmp.core.ember.WhipSim;
import ru.pohsmp.core.net.Net.HFx;

/**
 * T14: the whip of the fire sword-whip ("Раскалённые угли") on the client — a physics rope ({@link WhipSim}) drawn as a smooth
 * plaited tube, for every player holding the blade in the whip form (hot) in the main hand.
 * <ul>
 * <li><b>Root in the hand of any animation.</b> {@code mixin/ItemRendererMixin} hands over the pose matrix every time the held
 *     blade is drawn (vanilla or Epic Fight, third and first person); the display transform of the item model is applied here as
 *     the item renderer does, and the guard of the icon (where the whip leaves the hilt) and the blade direction are taken from
 *     it. Not drawn this frame (out of view) — an estimate from the body.</li>
 * <li><b>Simulation</b> once per client tick, 6 substeps between the last two hand poses; the drawing goes through the substeps
 *     at the frame's partial tick, the first points are bent onto this frame's hand so the whip never lags behind the fist.</li>
 * <li><b>Strikes</b> come from the server ({@link HFx#WHIP}: the lash of a hit, the turn of "Fire Vortex"); a vanilla swing
 *     without a hit lashes too. The crack ({@link WhipSim.Crack}) — a flash, sparks and a short crack sound right here.</li>
 * </ul>
 * Look (approved by the scenarist, tools/gen_ember_fx.py whip()): round, thinning 0.15 → 0.03, #C2470E → #FFC27A, plaited in
 * rings with slanting stitches, a highlight on top, a cracker tassel at the end; it glows a little by itself (hot).
 */
public final class EmberWhipClient {
    private EmberWhipClient() {}

    // ---------------------------------------------------------------- where the whip leaves the hilt (item model space, 0..1)

    /**
     * The icon (tools/gen_ember_blade.py): weapon axis from the pommel (2.6, 29.4) to the point (29.6, 2.2) of 32 px; the blade
     * starts at u 0.34 (the guard). In the whip form the hand shows the hilt only (models/item/ember_blade_hot.json, in hand) and
     * the whip comes out of the guard along the blade axis.
     */
    static final float AX0 = 2.6f / 32, AY0 = 1 - 29.4f / 32, AX1 = 29.6f / 32, AY1 = 1 - 2.2f / 32, ROOT_U = 0.35f;
    static final float ROOT_X = AX0 + (AX1 - AX0) * ROOT_U, ROOT_Y = AY0 + (AY1 - AY0) * ROOT_U, DIR_X = AX1 - AX0, DIR_Y = AY1 - AY0;

    /** Sides of the tube and spline samples per rope span (near / far). */
    static final int SIDES = 8, SIDES_FAR = 5, PER = 3, PER_FAR = 2;
    static final double FAR = 28, MAX_DIST = 72;
    /** Braid: ring bands every BAND blocks, slanting stitches every STITCH blocks of length. */
    static final double BAND = 0.12, STITCH = 0.05;
    static final int HIGHLIGHT = 0xFFE7A0, TASSEL_A = 0xFF9A3A, TASSEL_B = 0xFFC27A;
    /** Least block light of the whip: it is hot. */
    static final int SELF_LIGHT = 11;

    static final class State {
        final WhipSim sim = new WhipSim();
        /** Last captured hand pose: in the world (third person), or in view space for the first person (converted when used). */
        double rx, ry, rz, dx, dy, dz;
        boolean firstPerson, captured;
        double capturedAt = -1e9;
        long lastLash = -100;
        boolean swung;
        int swingTime = -1;
        /** The hand's angle round the body axis (atan2(z, x)) and its turn per tick: which way the swing really goes. */
        double handAngle = Double.NaN, handTurn;

        /**
         * Sweep sign for a lash: the way the hand turns round the body now (any animation), else the server's direction. The angle
         * grows to the holder's right in Minecraft (+x east, +z south), so the sign is taken from the motion, not from a convention.
         */
        int sweep(int fallback) {
            return Math.abs(handTurn) > 0.04 ? (handTurn > 0 ? 1 : -1) : fallback;
        }
    }

    private static final Map<Integer, State> STATES = new HashMap<>();
    private static final List<Flash> FLASHES = new ArrayList<>();

    private record Flash(double x, double y, double z, double vx, double vy, double vz, double start, float rot) {}

    /** Inverse of the level view rotation of this frame (set at AFTER_SKY), and whether the level is being drawn now. */
    private static Matrix4f invView;
    private static boolean inLevel;

    // ---------------------------------------------------------------- the hand pose, from the item renderer (mixin)

    /** Called by mixin/ItemRendererMixin before the held item is drawn (the pose stack is still that of the hand). */
    public static void capture(LivingEntity e, ItemStack s, ItemDisplayContext ctx, boolean left, PoseStack ps) {
        if (!(s.getItem() instanceof EmberBlade) || !EmberBlade.hot(s)) return;
        boolean first = ctx == ItemDisplayContext.FIRST_PERSON_RIGHT_HAND || ctx == ItemDisplayContext.FIRST_PERSON_LEFT_HAND;
        boolean third = ctx == ItemDisplayContext.THIRD_PERSON_RIGHT_HAND || ctx == ItemDisplayContext.THIRD_PERSON_LEFT_HAND;
        // the main hand only: the same stack, or (a renderer that copies it) an equal one drawn on the main arm's side
        boolean rightSide = ctx == ItemDisplayContext.FIRST_PERSON_RIGHT_HAND || ctx == ItemDisplayContext.THIRD_PERSON_RIGHT_HAND;
        ItemStack main = e.getMainHandItem();
        if (main != s && !(ItemStack.isSameItemSameTags(main, s) && rightSide == (e.getMainArm() == HumanoidArm.RIGHT))) return;
        Minecraft mc = Minecraft.getInstance();
        if (!(first || third) || (third && (!inLevel || invView == null)) || (first && e != mc.player) || mc.level == null) return;
        try {
            PoseStack q = new PoseStack();
            q.last().pose().set(ps.last().pose());
            q.last().normal().set(ps.last().normal());
            BakedModel model = mc.getItemRenderer().getModel(s, e.level(), e, e.getId() + ctx.ordinal());
            net.minecraftforge.client.ForgeHooksClient.handleCameraTransforms(q, model, ctx, left);
            q.translate(-0.5F, -0.5F, -0.5F);
            Matrix4f m = q.last().pose();
            Vector4f r = m.transform(new Vector4f(ROOT_X, ROOT_Y, 0.5f, 1));
            Vector4f t = m.transform(new Vector4f(ROOT_X + DIR_X * 0.25f, ROOT_Y + DIR_Y * 0.25f, 0.5f, 1));
            State st = STATES.computeIfAbsent(e.getId(), k -> new State());
            st.firstPerson = first;
            if (first) {   // view space of the hand (its own projection, fov 70): to the world's fov, converted when used
                double k = Math.tan(Math.toRadians(mc.options.fov().get()) / 2) / Math.tan(Math.toRadians(70) / 2);
                st.rx = r.x() * k;
                st.ry = r.y() * k;
                st.rz = r.z();
                st.dx = (t.x() - r.x()) * k;
                st.dy = (t.y() - r.y()) * k;
                st.dz = t.z() - r.z();
            } else {       // camera-relative, rotated by the view: back to the world now
                Vec3 cam = mc.gameRenderer.getMainCamera().getPosition();
                Vector4f rw = invView.transform(new Vector4f(r.x(), r.y(), r.z(), 1)), tw = invView.transform(new Vector4f(t.x(), t.y(), t.z(), 1));
                st.rx = rw.x() + cam.x;
                st.ry = rw.y() + cam.y;
                st.rz = rw.z() + cam.z;
                st.dx = tw.x() - rw.x();
                st.dy = tw.y() - rw.y();
                st.dz = tw.z() - rw.z();
            }
            st.captured = true;
            st.capturedAt = mc.level.getGameTime() + mc.getFrameTime();
        } catch (RuntimeException ex) {   // a model or mod that draws differently must not break the frame
            ru.pohsmp.core.PohCore.LOG.debug("[ember] whip root capture failed", ex);
        }
    }

    /** The hand pose for the whip root now: the capture of the last frames, else an estimate from the body. */
    static WhipSim.Pose root(State st, LivingEntity e, float pt) {
        Minecraft mc = Minecraft.getInstance();
        double now = mc.level.getGameTime() + pt;
        if (st.captured && now - st.capturedAt < 2.5) {
            if (!st.firstPerson) return new WhipSim.Pose(st.rx, st.ry, st.rz, st.dx, st.dy, st.dz);
            if (invView != null && e == mc.player && mc.options.getCameraType().isFirstPerson()) {
                Vec3 cam = mc.gameRenderer.getMainCamera().getPosition();
                Vector4f r = invView.transform(new Vector4f((float) st.rx, (float) st.ry, (float) st.rz, 1));
                Vector4f d = invView.transform(new Vector4f((float) st.dx, (float) st.dy, (float) st.dz, 0));
                return new WhipSim.Pose(r.x() + cam.x, r.y() + cam.y, r.z() + cam.z, d.x(), d.y(), d.z());
            }
        }
        double yaw = Math.toRadians(Mth.rotLerp(pt, e.yBodyRotO, e.yBodyRot));
        Vec3 p = e.getPosition(pt);
        double fx = -Math.sin(yaw), fz = Math.cos(yaw), side = e.getMainArm() == HumanoidArm.LEFT ? -1 : 1;
        double rx = -Math.cos(yaw) * side, rz = -Math.sin(yaw) * side;   // toward the main hand
        return new WhipSim.Pose(p.x + rx * 0.37 + fx * 0.15, p.y + e.getBbHeight() * 0.4, p.z + rz * 0.37 + fz * 0.15, fx * 0.55, -0.83, fz * 0.55);
    }

    static WhipSim.Body body(LivingEntity e) {
        return new WhipSim.Body(e.getX(), e.getY(), e.getZ(), e.getBbWidth() / 2, e.getBbHeight());
    }

    /** Collision boxes of the level for the rope: the top of the block's collision shape, NaN when it lets the whip through. */
    static WhipSim.Solid solid(ClientLevel level) {
        BlockPos.MutableBlockPos mp = new BlockPos.MutableBlockPos();
        return (x, y, z) -> {
            mp.set(x, y, z);
            if (!level.hasChunkAt(mp)) return Double.NaN;
            BlockState bs = level.getBlockState(mp);
            if (bs.isAir()) return Double.NaN;
            VoxelShape sh = bs.getCollisionShape(level, mp);
            return sh.isEmpty() ? Double.NaN : sh.max(Direction.Axis.Y);
        };
    }

    static boolean holdsWhip(LivingEntity e) {
        ItemStack s = e.getMainHandItem();
        return s.getItem() instanceof EmberBlade && EmberBlade.hot(s) && e.isAlive() && !e.isSpectator();
    }

    // ---------------------------------------------------------------- strikes

    /** {@link HFx#WHIP} from the server: a = holder, b = lash / vortex, dur = ticks, x = facing angle, y = direction, f = half arc. */
    public static void strike(HFx m) {
        Minecraft mc = Minecraft.getInstance();
        if (mc.level == null || !(mc.level.getEntity(m.a) instanceof LivingEntity e) || !holdsWhip(e)) return;
        State st = STATES.computeIfAbsent(e.getId(), k -> new State());
        long now = mc.level.getGameTime();
        if (m.b == EmberBlade.VORTEX) {
            // the turn goes the way the hand goes round (ember_vortex turns +1), the whip starting a little behind the hand;
            // before the first hand pose: from behind the back
            int turn = st.sweep(1);
            st.sim.vortex(Double.isNaN(st.handAngle) ? m.x + Math.PI : st.handAngle - 0.9 * turn, turn, m.dur);
        }
        else {
            if (now - st.lastLash < 5) return;   // this swing already lashes (started by the client swing)
            int dir = m.y < 0 ? -1 : 1, s = st.sweep(dir);
            st.sim.lash(m.x, -m.f * s, m.f * s, m.dur, dir < 0);   // the 2nd lash of the combo (dir −1) rises
        }
        st.lastLash = now;
    }

    // ---------------------------------------------------------------- tick

    @SubscribeEvent
    public static void onTick(TickEvent.ClientTickEvent e) {
        Minecraft mc = Minecraft.getInstance();
        if (e.phase != TickEvent.Phase.END || mc.level == null || mc.isPaused()) return;
        ClientLevel level = mc.level;
        Vec3 cam = mc.gameRenderer.getMainCamera().getPosition();
        WhipSim.Solid solid = solid(level);
        java.util.Set<Integer> keep = new java.util.HashSet<>();
        for (AbstractClientPlayer p : level.players()) {
            if (!holdsWhip(p) || p.distanceToSqr(cam) > MAX_DIST * MAX_DIST) continue;
            keep.add(p.getId());
            State st = STATES.computeIfAbsent(p.getId(), k -> new State());
            // a swing without a hit (vanilla swing; an Epic Fight swing moves the hand, and the hand moves the whip)
            if (p.swinging && (!st.swung || p.swingTime < st.swingTime) && level.getGameTime() - st.lastLash > 6) {
                Vec3 f = p.getLookAngle();
                double half = Math.toRadians(50);
                int s = st.sweep(1);
                st.sim.lash(Math.atan2(f.z, f.x), -half * s, half * s, EmberBlade.LASH_TICKS, false);
                st.lastLash = level.getGameTime();
            }
            st.swung = p.swinging;
            st.swingTime = p.swingTime;
            WhipSim.Pose hand = root(st, p, 1);
            double ang = Math.atan2(hand.z() - p.getZ(), hand.x() - p.getX());
            st.handTurn = Double.isNaN(st.handAngle) ? 0 : Mth.wrapDegrees(Math.toDegrees(ang - st.handAngle)) * Math.PI / 180;
            st.handAngle = ang;
            List<WhipSim.Crack> cracks = st.sim.step(hand, body(p), solid);
            for (WhipSim.Crack c : cracks) crack(level, c);
            if (st.sim.striking()) flames(level, st.sim);
        }
        STATES.keySet().retainAll(keep);
        double now = level.getGameTime();
        FLASHES.removeIf(f -> now - f.start() > 6);
    }

    /** The crack: flash (drawn in onRender), sparks and a short sharp crack where the tip snapped. */
    static void crack(ClientLevel level, WhipSim.Crack c) {
        var rnd = level.random;
        double sp = Math.max(1e-6, c.speed());
        double ux = c.vx() / sp, uy = c.vy() / sp, uz = c.vz() / sp;
        FLASHES.add(new Flash(c.x(), c.y(), c.z(), ux, uy, uz, level.getGameTime() + Minecraft.getInstance().getFrameTime(), rnd.nextFloat() * 90));
        for (int i = 0; i < 10; i++) {   // sparks fly on along the snap
            double k = 0.08 + 0.12 * rnd.nextDouble();
            level.addParticle(i % 3 == 0 ? ParticleTypes.FLAME : ParticleTypes.SMALL_FLAME, c.x(), c.y(), c.z(),
                    ux * k + (rnd.nextDouble() - 0.5) * 0.12, uy * k + (rnd.nextDouble() - 0.3) * 0.12, uz * k + (rnd.nextDouble() - 0.5) * 0.12);
        }
        for (int i = 0; i < 6; i++)
            level.addParticle(ParticleTypes.FIREWORK, c.x(), c.y(), c.z(), (rnd.nextDouble() - 0.5) * 0.25, (rnd.nextDouble() - 0.2) * 0.2, (rnd.nextDouble() - 0.5) * 0.25);
        level.addParticle(ParticleTypes.LAVA, c.x(), c.y(), c.z(), 0, 0, 0);
        level.playLocalSound(c.x(), c.y(), c.z(), SoundEvents.FIREWORK_ROCKET_BLAST, SoundSource.PLAYERS, 0.75f, 1.75f + rnd.nextFloat() * 0.2f, false);
        level.playLocalSound(c.x(), c.y(), c.z(), SoundEvents.LAVA_POP, SoundSource.PLAYERS, 0.5f, 1.4f, false);
    }

    /** A strike burns: a few small flames off the outer half of the whip. */
    static void flames(ClientLevel level, WhipSim sim) {
        var rnd = level.random;
        for (int k = 0; k < 3; k++) {
            double[] p = sim.point(WhipSim.N / 3 + rnd.nextInt(WhipSim.N - WhipSim.N / 3));
            level.addParticle(ParticleTypes.SMALL_FLAME, p[0], p[1], p[2], 0, 0.01, 0);
        }
    }

    @SubscribeEvent
    public static void onUnload(LevelEvent.Unload e) {
        if (e.getLevel().isClientSide()) {
            STATES.clear();
            FLASHES.clear();
        }
    }

    // ---------------------------------------------------------------- drawing

    @SubscribeEvent
    public static void onRender(RenderLevelStageEvent e) {
        if (e.getStage() == RenderLevelStageEvent.Stage.AFTER_SKY || e.getStage() == RenderLevelStageEvent.Stage.AFTER_SOLID_BLOCKS) {
            // the view rotation of this frame (before the entities are drawn): for the hand captures
            invView = new Matrix4f(e.getPoseStack().last().pose()).invert();
            inLevel = true;
            return;
        }
        if (e.getStage() != RenderLevelStageEvent.Stage.AFTER_ENTITIES) return;
        inLevel = false;   // the held items of the level are drawn by now; later ones (GUI previews) are not ours
        Minecraft mc = Minecraft.getInstance();
        if (mc.level == null || (STATES.isEmpty() && FLASHES.isEmpty())) return;
        float pt = e.getPartialTick();
        Camera camera = e.getCamera();
        Vec3 cam = camera.getPosition();
        PoseStack ps = e.getPoseStack();
        MultiBufferSource.BufferSource buf = mc.renderBuffers().bufferSource();
        RenderType type = RenderType.entityCutoutNoCull(FxDraw.WHITE);
        VertexConsumer vc = buf.getBuffer(type);
        double[] pts = new double[3 * WhipSim.N];
        for (Map.Entry<Integer, State> en : STATES.entrySet()) {
            State st = en.getValue();
            if (!st.sim.ready() || !(mc.level.getEntity(en.getKey()) instanceof LivingEntity le) || !holdsWhip(le)) continue;
            double dist = le.position().distanceTo(cam);
            if (dist > MAX_DIST) continue;
            st.sim.sample(pt, pts);
            WhipSim.Pose r = root(st, le, pt);
            pinToHand(pts, r, st.sim.length() / (WhipSim.N - 1));
            int light = LevelRenderer.getLightColor(mc.level, BlockPos.containing(pts[3 * (WhipSim.N / 2)], pts[3 * (WhipSim.N / 2) + 1], pts[3 * (WhipSim.N / 2) + 2]));
            light = LightTexture.pack(Math.max(SELF_LIGHT, LightTexture.block(light)), LightTexture.sky(light));
            boolean far = dist > FAR;
            double[] sp = WhipSim.spline(pts, far ? PER_FAR : PER);
            tube(vc, ps.last(), sp, cam, far ? SIDES_FAR : SIDES, light);
            double[] before = new double[3 * WhipSim.N];
            st.sim.sample(Math.max(0, pt - 0.25), before);
            tassel(vc, ps.last(), sp, before, pts, cam, light);
        }
        buf.endBatch(type);
        if (!FLASHES.isEmpty()) flashes(ps, buf, camera, mc.level.getGameTime() + pt);
    }

    /** Bends the first points of the interpolated rope onto this frame's hand pose (the root never lags behind the fist). */
    static void pinToHand(double[] pts, WhipSim.Pose r, double seg) {
        WhipSim.Pose n = new WhipSim.Pose(r.x(), r.y(), r.z(), r.dx(), r.dy(), r.dz());
        double l = Math.sqrt(n.dx() * n.dx() + n.dy() * n.dy() + n.dz() * n.dz());
        double ddx = l < 1e-9 ? 0 : n.dx() / l, ddy = l < 1e-9 ? -1 : n.dy() / l, ddz = l < 1e-9 ? 0 : n.dz() / l;
        double ox = r.x() - pts[0], oy = r.y() - pts[1], oz = r.z() - pts[2];
        for (int i = 2; i < 8; i++) {
            double w = (1 - i / 8.0) * (1 - i / 8.0);
            pts[3 * i] += ox * w;
            pts[3 * i + 1] += oy * w;
            pts[3 * i + 2] += oz * w;
        }
        pts[0] = r.x();
        pts[1] = r.y();
        pts[2] = r.z();
        pts[3] = r.x() + ddx * seg;
        pts[4] = r.y() + ddy * seg;
        pts[5] = r.z() + ddz * seg;
    }

    /**
     * The plaited tube along the spline: rings of {@code sides} vertices on frames carried along the curve (no twisting), thinning
     * to the tip; per face colour: the gradient, ring bands, two slanting stitch lines, a warm highlight on the faces turned up.
     */
    static void tube(VertexConsumer vc, PoseStack.Pose pose, double[] sp, Vec3 cam, int sides, int light) {
        int m = sp.length / 3;
        double[][] T = new double[m][], Nn = new double[m][], B = new double[m][];
        double[] arc = new double[m];
        for (int j = 0; j < m; j++) {
            int a = Math.max(0, j - 1), b = Math.min(m - 1, j + 1);
            T[j] = norm(sp[3 * b] - sp[3 * a], sp[3 * b + 1] - sp[3 * a + 1], sp[3 * b + 2] - sp[3 * a + 2], 0, 0, 1);
            if (j > 0) arc[j] = arc[j - 1] + Math.sqrt(sq(sp[3 * j] - sp[3 * j - 3]) + sq(sp[3 * j + 1] - sp[3 * j - 2]) + sq(sp[3 * j + 2] - sp[3 * j - 1]));
        }
        // parallel transport of the frame: start "up" across the tangent
        double[] up = {0, 1, 0};
        double[] n0 = sub(up, scale(T[0], dot(up, T[0])));
        if (len(n0) < 1e-4) n0 = sub(new double[] {1, 0, 0}, scale(T[0], T[0][0]));
        Nn[0] = norm(n0[0], n0[1], n0[2], 1, 0, 0);
        B[0] = cross(T[0], Nn[0]);
        for (int j = 1; j < m; j++) {
            double[] n = sub(Nn[j - 1], scale(T[j], dot(Nn[j - 1], T[j])));
            Nn[j] = norm(n[0], n[1], n[2], Nn[j - 1][0], Nn[j - 1][1], Nn[j - 1][2]);
            B[j] = cross(T[j], Nn[j]);
        }
        double total = Math.max(1e-6, arc[m - 1]);
        float[][] ring = new float[sides][], ringN = new float[sides][], prev = new float[sides][], prevN = new float[sides][];
        Matrix4f mat = pose.pose();
        Matrix3f nm = pose.normal();
        for (int j = 0; j < m; j++) {
            double u = arc[j] / total;
            int band = (int) Math.floor(arc[j] / BAND);
            double r = WhipSim.thickness(u) / 2 * (1 + 0.035 * Math.cos(arc[j] / BAND * 2 * Math.PI));   // plaited rings swell a little
            for (int k = 0; k < sides; k++) {
                double th = 2 * Math.PI * k / sides, c = Math.cos(th), s = Math.sin(th);
                double nx = Nn[j][0] * c + B[j][0] * s, ny = Nn[j][1] * c + B[j][1] * s, nz = Nn[j][2] * c + B[j][2] * s;
                ring[k] = new float[] {(float) (sp[3 * j] - cam.x + nx * r), (float) (sp[3 * j + 1] - cam.y + ny * r), (float) (sp[3 * j + 2] - cam.z + nz * r)};
                ringN[k] = new float[] {(float) nx, (float) ny, (float) nz};
            }
            if (j > 0) {
                double um = (arc[j - 1] + arc[j]) / 2 / total;
                int base = WhipSim.color(um);
                for (int k = 0; k < sides; k++) {
                    int k2 = (k + 1) % sides;
                    int col = base;
                    if (band % 2 == 1) col = shade(col, 0.86);                                  // ring bands of the plait
                    int stitch = Math.floorMod(k - (int) Math.floor(arc[j] / STITCH), sides);     // two helices of stitches
                    if (WhipSim.thickness(um) > 0.045 && (stitch == 0 || stitch == sides / 2)) col = shade(col, 0.68);
                    double upness = (ringN[k][1] + ringN[k2][1] + prevN[k][1] + prevN[k2][1]) / 4;
                    if (upness > 0.55) col = WhipSim.mix(col, HIGHLIGHT, 0.5 * (upness - 0.55) / 0.45);   // highlight on top
                    vert(vc, mat, nm, prev[k], prevN[k], col, light);
                    vert(vc, mat, nm, ring[k], ringN[k], col, light);
                    vert(vc, mat, nm, ring[k2], ringN[k2], col, light);
                    vert(vc, mat, nm, prev[k2], prevN[k2], col, light);
                }
            }
            float[][] t = prev;
            prev = ring;
            ring = t;
            t = prevN;
            prevN = ringN;
            ringN = t;
        }
    }

    /**
     * The cracker at the end: seven thin strands fanned from the tip, trailing behind its motion and drooping a little; light orange
     * and pale at the very ends.
     */
    static void tassel(VertexConsumer vc, PoseStack.Pose pose, double[] sp, double[] before, double[] now, Vec3 cam, int light) {
        int m = sp.length / 3, n = WhipSim.N - 1;
        double[] tip = {sp[3 * m - 3], sp[3 * m - 2], sp[3 * m - 1]};
        double[] T = norm(tip[0] - sp[3 * m - 6], tip[1] - sp[3 * m - 5], tip[2] - sp[3 * m - 4], 0, -1, 0);
        double[] side = cross(T, new double[] {0, 1, 0});
        if (len(side) < 1e-4) side = new double[] {1, 0, 0};
        side = norm(side[0], side[1], side[2], 1, 0, 0);
        double[] side2 = cross(side, T);
        // tip velocity over the last quarter tick (blocks per tick)
        double vx = (now[3 * n] - before[3 * n]) * 4, vy = (now[3 * n + 1] - before[3 * n + 1]) * 4, vz = (now[3 * n + 2] - before[3 * n + 2]) * 4;
        Matrix4f mat = pose.pose();
        Matrix3f nm = pose.normal();
        for (int k = 0; k < 7; k++) {
            double ang = (k - 3) * 0.22, L = 0.28 + 0.06 * (k % 3);
            double[] d = norm(T[0] + side[0] * Math.sin(ang) * 0.8 + side2[0] * Math.cos(k * 1.7) * 0.25,
                    T[1] + side[1] * Math.sin(ang) * 0.8 + side2[1] * Math.cos(k * 1.7) * 0.25,
                    T[2] + side[2] * Math.sin(ang) * 0.8 + side2[2] * Math.cos(k * 1.7) * 0.25, T[0], T[1], T[2]);
            double[] p = tip.clone();
            int col = k % 2 == 0 ? TASSEL_A : TASSEL_B;
            for (int s = 0; s < 4; s++) {
                double t0 = s / 4.0, t1 = (s + 1) / 4.0;
                double[] q = {tip[0] + d[0] * L * t1 - vx * 0.05 * t1 * t1, tip[1] + d[1] * L * t1 - vy * 0.05 * t1 * t1 - 0.05 * t1 * t1,
                        tip[2] + d[2] * L * t1 - vz * 0.05 * t1 * t1};
                double w0 = 0.011 * (1 - 0.6 * t0), w1 = 0.011 * (1 - 0.6 * t1);
                int c = s == 3 ? WhipSim.mix(col, HIGHLIGHT, 0.6) : col;
                strand(vc, mat, nm, p, q, w0, w1, side, side2, cam, c, light);
                p = q;
            }
        }
    }

    /** One piece of a tassel strand: two crossed thin quads (visible from any side). */
    private static void strand(VertexConsumer vc, Matrix4f mat, Matrix3f nm, double[] a, double[] b, double wa, double wb, double[] s1, double[] s2,
            Vec3 cam, int col, int light) {
        for (double[] s : new double[][] {s1, s2}) {
            float[] n = {(float) s[0], (float) s[1], (float) s[2]};
            vert(vc, mat, nm, new float[] {(float) (a[0] - cam.x - s[0] * wa), (float) (a[1] - cam.y - s[1] * wa), (float) (a[2] - cam.z - s[2] * wa)}, n, col, light);
            vert(vc, mat, nm, new float[] {(float) (b[0] - cam.x - s[0] * wb), (float) (b[1] - cam.y - s[1] * wb), (float) (b[2] - cam.z - s[2] * wb)}, n, col, light);
            vert(vc, mat, nm, new float[] {(float) (b[0] - cam.x + s[0] * wb), (float) (b[1] - cam.y + s[1] * wb), (float) (b[2] - cam.z + s[2] * wb)}, n, col, light);
            vert(vc, mat, nm, new float[] {(float) (a[0] - cam.x + s[0] * wa), (float) (a[1] - cam.y + s[1] * wa), (float) (a[2] - cam.z + s[2] * wa)}, n, col, light);
        }
    }

    /** The crack flash: a white-hot core, a sharp star and a ring of shock running out, gone in a quarter second. */
    static void flashes(PoseStack ps, MultiBufferSource.BufferSource buf, Camera camera, double now) {
        Vec3 cam = camera.getPosition();
        ps.pushPose();
        ps.translate(-cam.x, -cam.y, -cam.z);
        FxDraw.Frame f = new FxDraw.Frame(ps.last(), buf, camera, cam, now, 0, false);
        for (Iterator<Flash> it = FLASHES.iterator(); it.hasNext();) {
            Flash fl = it.next();
            double t = (now - fl.start()) / 5;
            if (t < 0 || t > 1) continue;
            Vec3 c = new Vec3(fl.x(), fl.y(), fl.z());
            double fade = 1 - t;
            FxDraw.billboard(f.add(FxDraw.tex("glow")), f, c, 0.25 + 0.5 * Math.sqrt(t), 0, 0xFFF2C0, 1.4 * fade * fade);
            FxDraw.billboard(f.add(FxDraw.tex("spark_sharp")), f, c, 0.55 + 0.5 * t, fl.rot() + 40 * t, 0xFFC27A, 1.2 * fade);
            FxDraw.billboard(f.add(FxDraw.tex("ring")), f, c, 0.15 + 1.25 * t, 0, 0xFFB040, 0.9 * fade);
        }
        ps.popPose();
        buf.endBatch();
    }

    // ---------------------------------------------------------------- small math

    private static void vert(VertexConsumer vc, Matrix4f m, Matrix3f nm, float[] p, float[] n, int rgb, int light) {
        vc.vertex(m, p[0], p[1], p[2]).color(((rgb >> 16) & 255) / 255f, ((rgb >> 8) & 255) / 255f, (rgb & 255) / 255f, 1f).uv(0.5f, 0.5f)
                .overlayCoords(OverlayTexture.NO_OVERLAY).uv2(light).normal(nm, n[0], n[1], n[2]).endVertex();
    }

    static int shade(int rgb, double k) {
        return (int) (((rgb >> 16) & 255) * k) << 16 | (int) (((rgb >> 8) & 255) * k) << 8 | (int) ((rgb & 255) * k);
    }

    private static double sq(double v) {
        return v * v;
    }

    private static double dot(double[] a, double[] b) {
        return a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
    }

    private static double len(double[] a) {
        return Math.sqrt(dot(a, a));
    }

    private static double[] sub(double[] a, double[] b) {
        return new double[] {a[0] - b[0], a[1] - b[1], a[2] - b[2]};
    }

    private static double[] scale(double[] a, double k) {
        return new double[] {a[0] * k, a[1] * k, a[2] * k};
    }

    private static double[] cross(double[] a, double[] b) {
        return new double[] {a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]};
    }

    /** Normalised (x, y, z), or the fallback (fx, fy, fz) when it is too short. */
    private static double[] norm(double x, double y, double z, double fx, double fy, double fz) {
        double l = Math.sqrt(x * x + y * y + z * z);
        return l < 1e-9 ? new double[] {fx, fy, fz} : new double[] {x / l, y / l, z / l};
    }
}
