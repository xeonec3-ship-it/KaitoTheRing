package net.minecraft.world.phys;
public class Vec3 {
    public static final Vec3 ZERO = new Vec3(0, 0, 0);
    public final double x, y, z;
    public Vec3(double x, double y, double z) { this.x = x; this.y = y; this.z = z; }
    public static Vec3 directionFromRotation(float xRot, float yRot) {
        float f = (float) Math.cos(-yRot * 0.017453292F - (float) Math.PI), f1 = (float) Math.sin(-yRot * 0.017453292F - (float) Math.PI);
        float f2 = (float) -Math.cos(-xRot * 0.017453292F), f3 = (float) Math.sin(-xRot * 0.017453292F);
        return new Vec3(f1 * f2, f3, f * f2);
    }
    public Vec3 add(Vec3 o) { return new Vec3(x + o.x, y + o.y, z + o.z); }
    public Vec3 add(double a, double b, double c) { return new Vec3(x + a, y + b, z + c); }
    public Vec3 subtract(Vec3 o) { return new Vec3(x - o.x, y - o.y, z - o.z); }
    public Vec3 scale(double k) { return new Vec3(x * k, y * k, z * k); }
    public Vec3 cross(Vec3 o) { return new Vec3(y * o.z - z * o.y, z * o.x - x * o.z, x * o.y - y * o.x); }
    public double dot(Vec3 o) { return x * o.x + y * o.y + z * o.z; }
    public double lengthSqr() { return x * x + y * y + z * z; }
    public double length() { return Math.sqrt(lengthSqr()); }
    public Vec3 normalize() { double l = length(); return l < 1.0E-4 ? ZERO : new Vec3(x / l, y / l, z / l); }
    public double distanceTo(Vec3 o) { return Math.sqrt(distanceToSqr(o)); }
    public double distanceToSqr(Vec3 o) { double a = o.x - x, b = o.y - y, c = o.z - z; return a * a + b * b + c * c; }
    public Vec3 lerp(Vec3 o, double t) { return new Vec3(x + (o.x - x) * t, y + (o.y - y) * t, z + (o.z - z) * t); }
}
