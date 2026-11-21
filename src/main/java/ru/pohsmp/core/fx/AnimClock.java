package ru.pohsmp.core.fx;

/**
 * Monotonic animation clock in ticks (pure logic, no Minecraft; the client instance is client/ClientClock).
 * <p>
 * Why: the client's level game time is not monotonic on a dedicated server. The client adds 1 to it every client tick, and the
 * server overwrites it with its own value every 20 server ticks (ClientboundSetTimePacket). With the server below 20 TPS the
 * client runs ahead and is pulled back each second, network jitter adds ±1-2 ticks: everything timed by
 * {@code level.getGameTime() + partialTick} (runes, magic circles, sigils, cameras) jumps back and forth - the "slideshow".
 * This clock counts only its own client ticks; server packets never touch it. Moments from the server are relative (an age or a
 * duration) and are placed on this clock when the packet arrives ({@link #ago}).
 */
public final class AnimClock {
    private long ticks;

    /** One client tick passed (called once per client tick, not while the game is paused). */
    public void tick() {
        ticks++;
    }

    /** Whole ticks so far: the drop-in for {@code level.getGameTime()} in client visuals. */
    public long ticks() {
        return ticks;
    }

    /** Frame time: ticks + the partial tick of the frame (clamped to 0..1). */
    public double now(float partialTick) {
        return (double) ticks + Math.max(0f, Math.min(1f, partialTick));   // double: long + float would be float math
    }

    /** The moment `age` ticks ago on this clock (a packet says "this started `age` ticks ago"). */
    public long ago(long age) {
        return ticks - age;
    }
}
