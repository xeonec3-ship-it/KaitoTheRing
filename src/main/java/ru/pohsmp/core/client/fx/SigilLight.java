package ru.pohsmp.core.client.fx;

import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.material.FluidState;
import net.minecraft.world.phys.Vec3;
import net.minecraft.world.phys.shapes.VoxelShape;
import ru.pohsmp.core.client.fx.FxDraw.Frame;
import ru.pohsmp.core.fx.sigil.SigilDef;
import ru.pohsmp.core.fx.sigil.SigilTimeline;

/**
 * Light of a sigil on the world, without shaders (docs/sigils.md, "Свет на земле"): an additive decal laid over the top faces
 * of the blocks under the sigil, one quad per block column, lifted a hair above the face so it follows the relief.
 * <ul>
 *   <li>groundLight — the soft glow texture stretched over a square of side 2R around the point under the sigil's centre,
 *   so it reads as one round spot moving with the sigil;</li>
 *   <li>blockGlow — flat colour with per-corner brightness {@link SigilDef.BlockGlow#at}, so each top face is tinted and the
 *   tint fades towards the edge.</li>
 * </ul>
 * Surface heights are scanned from the client level and cached per run for a few ticks (not every frame).
 * Off when [fx] quality = low.
 */
final class SigilLight {
    private SigilLight() {}

    private static final ResourceLocation GLOW = FxDraw.tex("glow");
    /** Lift above the face against z-fighting. */
    private static final double LIFT = 0.015;
    /** Larger glow is clipped to this many blocks around the centre. */
    private static final int MAX_BLOCKS = 24;
    /** How far above / below the ground under the centre a column's surface may be. */
    private static final int UP = 4, DOWN = 8;
    private static final int REFRESH_TICKS = 10;

    /** Cached surface heights around the sigil: tops[(dz + n) * (2n + 1) + dx + n], NaN = no surface. */
    static final class Cache {
        int cx, cz, n = -1;
        double cy = Double.NaN, ground = Double.NaN, madeAt = -1e9;
        float[] tops;
    }

    static void draw(Frame f, SigilRun r, SigilDef d, double t, Vec3 c, double gs) {
        SigilDef.GroundLight gl = d.groundLight();
        SigilDef.BlockGlow bg = d.blockGlow();
        if (f.low() || gl == null && bg == null || gs <= 1e-3) return;
        double level = SigilTimeline.lightLevel(d, t, r.stopAt) * r.alpha;
        if (level <= 0.003) return;
        ClientLevel lvl = Minecraft.getInstance().level;
        if (lvl == null) return;
        double reach = Math.max(gl != null ? gl.reach() : 0, bg != null ? bg.reach() : 0);
        double rGl = gl != null ? gl.radius() * gs : 0, rBg = bg != null ? bg.radius() * gs : 0;
        int n = Math.min(MAX_BLOCKS, (int) Math.ceil(Math.max(rGl, rBg)) + 1);
        Cache k = cache(lvl, r, c, n, reach, f.time());
        if (Double.isNaN(k.ground)) return;
        double h = c.y - k.ground;
        int col = r.color >= 0 ? r.color : d.color();
        if (gl != null && h <= gl.reach()) {
            double a = gl.strength() * level * (1 - 0.5 * Math.max(0, h) / gl.reach());
            if (a > 0.003) spot(f, k, c, Math.min(rGl, MAX_BLOCKS), col, a);
        }
        if (bg != null && h <= bg.reach()) {
            double a = level * (1 - 0.5 * Math.max(0, h) / bg.reach());
            if (a > 0.003) tint(f, k, c, Math.min(rBg, MAX_BLOCKS), bg, col, a);
        }
    }

    // ---------------------------------------------------------------- decals

    /** Glow texture over the square [c - R, c + R], cut along block edges and laid on each column's top. */
    private static void spot(Frame f, Cache k, Vec3 c, double R, int col, double a) {
        if (R < 0.05) return;
        VertexConsumer vc = f.add(GLOW);
        for (int dz = -k.n; dz <= k.n; dz++)
            for (int dx = -k.n; dx <= k.n; dx++) {
                float top = k.tops[(dz + k.n) * (2 * k.n + 1) + dx + k.n];
                if (Float.isNaN(top)) continue;
                double bx = k.cx + dx, bz = k.cz + dz;
                double x0 = Math.max(bx, c.x - R), x1 = Math.min(bx + 1, c.x + R);
                double z0 = Math.max(bz, c.z - R), z1 = Math.min(bz + 1, c.z + R);
                if (x1 <= x0 || z1 <= z0) continue;
                double y = top + LIFT;
                vertGlow(vc, f, c, R, x0, y, z0, col, a);
                vertGlow(vc, f, c, R, x0, y, z1, col, a);
                vertGlow(vc, f, c, R, x1, y, z1, col, a);
                vertGlow(vc, f, c, R, x1, y, z0, col, a);
            }
    }

    private static void vertGlow(VertexConsumer vc, Frame f, Vec3 c, double R, double x, double y, double z, int col, double a) {
        FxDraw.vert(vc, f, x, y, z, (float) (0.5 + (x - c.x) / (2 * R)), (float) (0.5 + (z - c.z) / (2 * R)), col, a);
    }

    /** Each top face within R gets the colour, brightness by distance of its corners from the centre. */
    private static void tint(Frame f, Cache k, Vec3 c, double R, SigilDef.BlockGlow bg, int col, double a) {
        if (R < 0.05) return;
        VertexConsumer vc = f.add(FxDraw.WHITE);
        for (int dz = -k.n; dz <= k.n; dz++)
            for (int dx = -k.n; dx <= k.n; dx++) {
                float top = k.tops[(dz + k.n) * (2 * k.n + 1) + dx + k.n];
                if (Float.isNaN(top)) continue;
                double x0 = k.cx + dx, z0 = k.cz + dz, x1 = x0 + 1, z1 = z0 + 1;
                double a00 = bg.at(dist(c, x0, z0) / R) * a, a01 = bg.at(dist(c, x0, z1) / R) * a;
                double a11 = bg.at(dist(c, x1, z1) / R) * a, a10 = bg.at(dist(c, x1, z0) / R) * a;
                if (a00 + a01 + a11 + a10 <= 0.004) continue;
                double y = top + LIFT;
                FxDraw.vert(vc, f, x0, y, z0, 0.5f, 0.5f, col, a00);
                FxDraw.vert(vc, f, x0, y, z1, 0.5f, 0.5f, col, a01);
                FxDraw.vert(vc, f, x1, y, z1, 0.5f, 0.5f, col, a11);
                FxDraw.vert(vc, f, x1, y, z0, 0.5f, 0.5f, col, a10);
            }
    }

    private static double dist(Vec3 c, double x, double z) {
        double ax = x - c.x, az = z - c.z;
        return Math.sqrt(ax * ax + az * az);
    }

    // ---------------------------------------------------------------- surface scan

    private static Cache cache(ClientLevel lvl, SigilRun r, Vec3 c, int n, double reach, double now) {
        Cache k = r.light instanceof Cache x ? x : new Cache();
        r.light = k;
        int cx = (int) Math.floor(c.x), cz = (int) Math.floor(c.z);
        boolean stale = k.n != n || k.cx != cx || k.cz != cz || Double.isNaN(k.cy) || Math.abs(k.cy - c.y) > 0.5
                || now - k.madeAt >= REFRESH_TICKS || now < k.madeAt;
        if (!stale) return k;
        k.cx = cx;
        k.cz = cz;
        k.cy = c.y;
        k.n = n;
        k.madeAt = now;
        BlockPos.MutableBlockPos p = new BlockPos.MutableBlockPos();
        // ground under the centre: first surface at or below the sigil (a ground sigil sits on it)
        k.ground = Double.NaN;
        int yTop = (int) Math.floor(c.y + 0.2), yMin = (int) Math.floor(c.y - reach);
        for (int y = yTop; y >= yMin; y--) {
            double top = surface(lvl, p.set(cx, y, cz));
            if (!Double.isNaN(top) && top <= c.y + 0.6) {
                k.ground = top;
                break;
            }
        }
        int side = 2 * n + 1;
        if (k.tops == null || k.tops.length != side * side) k.tops = new float[side * side];
        java.util.Arrays.fill(k.tops, Float.NaN);
        if (Double.isNaN(k.ground)) return k;
        int g = (int) Math.floor(k.ground - 1e-3);
        for (int dz = -n; dz <= n; dz++)
            for (int dx = -n; dx <= n; dx++) {
                if (dx * dx + dz * dz > (n + 1) * (n + 1)) continue;
                k.tops[(dz + n) * side + dx + n] = (float) column(lvl, p, cx + dx, cz + dz, g + UP, g - DOWN);
            }
        return k;
    }

    /** Highest exposed surface in the column between yTop and yMin (a face with free space right above it), NaN if none. */
    private static double column(ClientLevel lvl, BlockPos.MutableBlockPos p, int x, int z, int yTop, int yMin) {
        boolean freeAbove = Double.isNaN(surface(lvl, p.set(x, yTop + 1, z)));
        for (int y = yTop; y >= yMin; y--) {
            double top = surface(lvl, p.set(x, y, z));
            if (Double.isNaN(top)) {
                freeAbove = true;
                continue;
            }
            if (freeAbove) return top;
        }
        return Double.NaN;
    }

    /** Top of what stands in this block (collision box or liquid surface), NaN if nothing to light (air, grass, flowers). */
    private static double surface(ClientLevel lvl, BlockPos p) {
        BlockState st = lvl.getBlockState(p);
        if (st.isAir()) return Double.NaN;
        FluidState fl = st.getFluidState();
        if (!fl.isEmpty()) return p.getY() + fl.getHeight(lvl, p);
        VoxelShape sh = st.getCollisionShape(lvl, p);
        if (sh.isEmpty()) return Double.NaN;
        return p.getY() + sh.max(Direction.Axis.Y);
    }
}
