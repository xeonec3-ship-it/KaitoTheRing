package ru.pohsmp.core.illusion;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;

/**
 * T22 «Зеркальный лабиринт»: the same maze on the server (wall hits) and on the victims' clients (the mirror walls), built from the centre,
 * the radius and a seed. Cells of 3 blocks round the centre; a perfect maze by depth-first carving; only the walls inside the radius stay.
 * Walls are flat segments (x1,z1)-(x2,z2) along the grid lines.
 */
public final class Maze {
    public static final double CELL = 3.0, HALF_THICK = 0.07, BELOW = 2.0, ABOVE = 4.0;

    public final double cx, cy, cz, r;
    public final List<double[]> walls = new ArrayList<>();

    public Maze(double cx, double cy, double cz, double r, long seed) {
        this.cx = cx;
        this.cy = cy;
        this.cz = cz;
        this.r = r;
        int n = Math.max(3, (int) Math.floor(2 * r / CELL));
        if (n % 2 == 0) n--;   // odd, so the centre is the middle of a cell
        double ox = cx - n * CELL / 2, oz = cz - n * CELL / 2;
        // east[x][z]: wall between (x,z) and (x+1,z); south[x][z]: wall between (x,z) and (x,z+1)
        boolean[][] east = new boolean[n][n], south = new boolean[n][n];
        for (boolean[] a : east) java.util.Arrays.fill(a, true);
        for (boolean[] a : south) java.util.Arrays.fill(a, true);
        boolean[][] seen = new boolean[n][n];
        Random rnd = new Random(seed);
        ArrayDeque<int[]> st = new ArrayDeque<>();
        int m = n / 2;
        st.push(new int[] {m, m});
        seen[m][m] = true;
        int[][] dirs = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};
        while (!st.isEmpty()) {
            int[] c = st.peek();
            List<int[]> open = new ArrayList<>();
            for (int[] d : dirs) {
                int x = c[0] + d[0], z = c[1] + d[1];
                if (x >= 0 && z >= 0 && x < n && z < n && !seen[x][z]) open.add(d);
            }
            if (open.isEmpty()) {
                st.pop();
                continue;
            }
            int[] d = open.get(rnd.nextInt(open.size()));
            int x = c[0] + d[0], z = c[1] + d[1];
            if (d[0] == 1) east[c[0]][c[1]] = false;
            else if (d[0] == -1) east[x][z] = false;
            else if (d[1] == 1) south[c[0]][c[1]] = false;
            else south[x][z] = false;
            seen[x][z] = true;
            st.push(new int[] {x, z});
        }
        // a few more openings, so it is a labyrinth to walk and not one long corridor
        for (int k = 0; k < n; k++) {
            int x = rnd.nextInt(n - 1), z = rnd.nextInt(n);
            if (rnd.nextBoolean()) east[x][z] = false;
            else south[z][x] = false;
        }
        for (int x = 0; x < n; x++)
            for (int z = 0; z < n; z++) {
                if (x < n - 1 && east[x][z]) add(ox + (x + 1) * CELL, oz + z * CELL, ox + (x + 1) * CELL, oz + (z + 1) * CELL);
                if (z < n - 1 && south[x][z]) add(ox + x * CELL, oz + (z + 1) * CELL, ox + (x + 1) * CELL, oz + (z + 1) * CELL);
            }
    }

    private void add(double x1, double z1, double x2, double z2) {
        double mx = (x1 + x2) / 2 - cx, mz = (z1 + z2) / 2 - cz;
        if (mx * mx + mz * mz <= (r - 1) * (r - 1)) walls.add(new double[] {x1, z1, x2, z2});
    }

    /** The wall p stands in (its body of radius 0.3), or null. y is the feet. */
    public double[] wallAt(double x, double y, double z, double bodyR) {
        if (y < cy - BELOW - 1.8 || y > cy + ABOVE) return null;
        for (double[] w : walls) {
            double minX = Math.min(w[0], w[2]) - HALF_THICK - bodyR, maxX = Math.max(w[0], w[2]) + HALF_THICK + bodyR;
            double minZ = Math.min(w[1], w[3]) - HALF_THICK - bodyR, maxZ = Math.max(w[1], w[3]) + HALF_THICK + bodyR;
            if (x >= minX && x <= maxX && z >= minZ && z <= maxZ) return w;
        }
        return null;
    }
}
