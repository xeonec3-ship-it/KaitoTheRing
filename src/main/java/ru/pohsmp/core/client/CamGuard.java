package ru.pohsmp.core.client;

import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.core.BlockPos;
import net.minecraft.tags.BlockTags;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.phys.Vec3;
import net.minecraft.world.phys.shapes.VoxelShape;

/**
 * Keeps the cutscene camera out of the terrain for every scene (owner 19.11: off the flat world the camera went into hills and showed
 * the caves). Each frame: a ray from the focus (the look point) to the wanted camera stops 0.4 short of the first solid block; the camera
 * itself must have 0.3 of air around it; a low shot under the open sky stays 1 above the ground. When the shot collapses (closer than
 * 1.5 to the focus) the same shot is tried turned round the focus by ±30/60/90° and raised by 2/4, the first free one is kept until it
 * collapses too or the shot cuts. Leaves do not count (only solid blocks). The correction lets go smoothly (0.25 per frame).
 */
final class CamGuard {
    private CamGuard() {}

    private static final double PAD = 0.4, RADIUS = 0.3, MIN = 1.5, STEP = 0.1, EASE = 0.25, CUT = 4;
    private static final double[][] VARIANTS = variants();
    private static int variant;
    private static Vec3 lastWanted, offset = Vec3.ZERO;

    private static double[][] variants() {
        int[] angles = {0, 30, -30, 60, -60, 90, -90};
        double[] ups = {0, 2, 4};
        double[][] v = new double[angles.length * ups.length][];
        int i = 0;
        for (double up : ups) for (int a : angles) v[i++] = new double[] {Math.toRadians(a), up};
        return v;
    }

    /** A new cutscene: back to the shots as written. */
    static void reset() {
        variant = 0;
        lastWanted = null;
        offset = Vec3.ZERO;
    }

    static Vec3 guard(ClientLevel lvl, Vec3 wanted, Vec3 focus) {
        if (lastWanted == null || lastWanted.distanceToSqr(wanted) > CUT * CUT) {   // a cut: the next shot starts as written
            variant = 0;
            offset = Vec3.ZERO;
        }
        lastWanted = wanted;
        if (solidAt(lvl, focus)) return lift(lvl, wanted);   // the focus itself is in a block: only keep the camera out of the ground
        Vec3 got = resolve(lvl, wanted, focus, variant);
        if (got.distanceTo(focus) < MIN && wanted.distanceTo(focus) >= MIN) {
            int best = variant;
            double far = got.distanceTo(focus);
            for (int i = 0; i < VARIANTS.length; i++) {
                if (i == variant) continue;
                Vec3 p = resolve(lvl, wanted, focus, i);
                double d = p.distanceTo(focus);
                if (d >= MIN) {
                    best = i;
                    got = p;
                    break;
                }
                if (d > far + 0.25) {
                    far = d;
                    best = i;
                    got = p;
                }
            }
            variant = best;
        }
        Vec3 need = got.subtract(wanted);
        if (need.lengthSqr() >= offset.lengthSqr()) offset = need;   // pushing in: at once, never through a wall
        else offset = offset.add(need.subtract(offset).scale(EASE));   // letting go: smoothly
        Vec3 out = wanted.add(offset);
        return clear(lvl, out, focus) ? out : got;
    }

    /** The wanted camera under this variant, made free: turned and raised, lifted off the ground, cut by the ray, pulled out of blocks. */
    private static Vec3 resolve(ClientLevel lvl, Vec3 wanted, Vec3 focus, int i) {
        double a = VARIANTS[i][0];
        Vec3 r = wanted.subtract(focus);
        double cos = Math.cos(a), sin = Math.sin(a);
        Vec3 p = focus.add(r.x * cos - r.z * sin, r.y + VARIANTS[i][1], r.x * sin + r.z * cos);
        if (p.y < focus.y && lvl.canSeeSky(BlockPos.containing(focus))) p = lift(lvl, p);
        Vec3 d = p.subtract(focus);
        double len = d.length();
        if (len < 1e-4) return p;
        Vec3 u = d.scale(1 / len);
        double reach = len;
        for (double s = STEP; s <= len; s += STEP) {
            if (solidAt(lvl, focus.add(u.scale(s)))) {
                reach = Math.max(0, s - PAD);
                break;
            }
        }
        while (reach > 0 && !roomy(lvl, focus.add(u.scale(reach)))) reach -= STEP;
        return focus.add(u.scale(Math.max(0, reach)));
    }

    /** A low camera under the open sky: at least 1 above the top solid block of its column. */
    private static Vec3 lift(ClientLevel lvl, Vec3 p) {
        int x = net.minecraft.util.Mth.floor(p.x), z = net.minecraft.util.Mth.floor(p.z);
        int y = lvl.getHeight(Heightmap.Types.MOTION_BLOCKING, x, z) - 1;
        int bottom = lvl.getMinBuildHeight();
        BlockPos.MutableBlockPos bp = new BlockPos.MutableBlockPos(x, y, z);
        while (y > bottom) {
            bp.setY(y);
            if (solid(lvl, bp, lvl.getBlockState(bp))) break;
            y--;
        }
        double ground = y + 1;
        return p.y < ground + 1 ? new Vec3(p.x, ground + 1, p.z) : p;
    }

    private static boolean clear(ClientLevel lvl, Vec3 p, Vec3 focus) {
        if (!roomy(lvl, p)) return false;
        Vec3 d = p.subtract(focus);
        double len = d.length();
        for (double s = STEP; s < len; s += STEP) if (solidAt(lvl, focus.add(d.scale(s / len)))) return false;
        return true;
    }

    /** 0.3 of air round the camera (the centre and the six points at that distance). */
    private static boolean roomy(ClientLevel lvl, Vec3 p) {
        return !solidAt(lvl, p) && !solidAt(lvl, p.add(RADIUS, 0, 0)) && !solidAt(lvl, p.add(-RADIUS, 0, 0)) && !solidAt(lvl, p.add(0, RADIUS, 0))
                && !solidAt(lvl, p.add(0, -RADIUS, 0)) && !solidAt(lvl, p.add(0, 0, RADIUS)) && !solidAt(lvl, p.add(0, 0, -RADIUS));
    }

    private static boolean solidAt(ClientLevel lvl, Vec3 p) {
        BlockPos bp = BlockPos.containing(p);
        BlockState s = lvl.getBlockState(bp);
        if (!solid(lvl, bp, s)) return false;
        VoxelShape sh = s.getCollisionShape(lvl, bp);
        double x = p.x - bp.getX(), y = p.y - bp.getY(), z = p.z - bp.getZ();
        for (var box : sh.toAabbs()) if (box.minX <= x && x <= box.maxX && box.minY <= y && y <= box.maxY && box.minZ <= z && z <= box.maxZ) return true;
        return false;
    }

    private static boolean solid(ClientLevel lvl, BlockPos bp, BlockState s) {
        return !s.isAir() && !s.is(BlockTags.LEAVES) && !s.getCollisionShape(lvl, bp).isEmpty();
    }
}
