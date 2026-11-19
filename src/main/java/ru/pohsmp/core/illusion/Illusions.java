package ru.pohsmp.core.illusion;

import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.OwnableEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.living.LivingDeathEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.ServerConfig;
import ru.pohsmp.core.fx.Fx;

/**
 * T22 "Illusions": what the whole school shares.
 * <ul>
 * <li>Illusory damage: it takes health for real but is written down per target; if the target lives until its time runs out, the
 * health comes back smoothly ([illusion] returnTicks) with fx/illusion_return. Death meanwhile is real (the debt is dropped).
 * Blessing ({@link #cleanse}) ends every illusion on the target and gives the debt back at once.</li>
 * <li>Allies: the same entity, own pets, and only the players the caster chose with the Prism ({@link IllusionAllies}; owner 19.11:
 * teams and FTB Teams do not count). Allies of the caster never see its illusions.</li>
 * <li>Illusion resistance shortens what lands on a victim: time x (2 - resistance), not below resistFloor.</li>
 * </ul>
 */
public final class Illusions {
    private Illusions() {}

    // ---------------------------------------------------------------- allies

    /**
     * True if b is on a's side: never the victim of a's illusions, and sees through them.
     * Owner 19.11: players are NOT allies by teams or FTB Teams any more - only those the caster chose with the Prism (Shift + right
     * click on the player, {@link IllusionAllies}); one way: a's choice of b does not make a b's ally. Own pets stay allies; mobs - by
     * vanilla teams as before.
     */
    public static boolean ally(LivingEntity a, Entity b) {
        if (a == null || b == null) return false;
        if (a == b || a.getUUID().equals(b.getUUID())) return true;
        if (b instanceof OwnableEntity o && a.getUUID().equals(o.getOwnerUUID())) return true;
        if (a instanceof OwnableEntity o && b.getUUID().equals(o.getOwnerUUID())) return true;
        if (b instanceof Player && a instanceof Player) return IllusionAllies.chose(a.getUUID(), b.getUUID());
        return a.isAlliedTo(b) || b.isAlliedTo(a);
    }

    /** Server log: who is near a zone illusion when it rises and why each one is or is not its victim (owner 19.11: tests). */
    public static void logZone(String spell, ServerLevel sl, LivingEntity caster, net.minecraft.world.phys.Vec3 c, double r) {
        StringBuilder sb = new StringBuilder();
        for (ServerPlayer p : sl.players()) {
            if (p == caster) continue;
            double d = Math.sqrt(p.position().distanceToSqr(c));
            if (d > r + 16) continue;
            sb.append(p.getGameProfile().getName()).append(" d=").append(Math.round(d * 10) / 10.0)
                    .append(d <= r ? " inside" : " outside").append(" ally=").append(ally(caster, p))
                    .append(" chose=").append(IllusionAllies.chose(caster.getUUID(), p.getUUID()))
                    .append(" spectator=").append(p.isSpectator()).append("; ");
        }
        PohCore.LOG.info("[pohsmp] {} by {} at {} r={}: {}", spell, caster.getName().getString(), c, r, sb.length() == 0 ? "nobody near" : sb);
    }

    /** Players (not spectators, not creative) the caster's illusion works on within r of the caster. */
    public static List<ServerPlayer> victims(ServerLevel sl, LivingEntity caster, double r) {
        List<ServerPlayer> out = new ArrayList<>();
        for (ServerPlayer p : sl.players())
            if (!p.isSpectator() && p.distanceToSqr(caster) <= r * r && !ally(caster, p)) out.add(p);
        return out;
    }

    // ---------------------------------------------------------------- resistance

    /** Illusion time on this victim: ticks x (2 - Illusion resistance), at least resistFloor of it. */
    public static int duration(LivingEntity victim, int ticks) {
        if (victim == null) return ticks;
        double r = victim.getAttribute(Reg.ILLUSION_RESIST.get()) == null ? 1 : victim.getAttributeValue(Reg.ILLUSION_RESIST.get());
        double k = Math.max(ServerConfig.get(ServerConfig.IL_RESIST_FLOOR), Math.min(2, 2 - r));
        return Math.max(1, (int) Math.round(ticks * k));
    }

    public static DamageSource source(ServerLevel sl, LivingEntity caster) {
        return new DamageSource(sl.registryAccess().registryOrThrow(Registries.DAMAGE_TYPE).getHolderOrThrow(Reg.ILLUSION_DAMAGE), caster);
    }

    // ---------------------------------------------------------------- illusory damage

    private static final class Debt {
        double amount;
        long until;
        final int tag;

        Debt(double amount, long until, int tag) {
            this.amount = amount;
            this.until = until;
            this.tag = tag;
        }
    }

    private static final class Target {
        LivingEntity entity;
        final List<Debt> debts = new ArrayList<>();
        /** health still to give back and how much per tick */
        double returning, perTick;
    }

    private static final Map<UUID, Target> TARGETS = new HashMap<>();
    private static long now;

    /** Writes down health the target already lost as illusory: it comes back after ticks if the target lives. tag groups debts (0 = none). */
    public static void owe(LivingEntity t, double amount, int ticks, int tag) {
        if (t == null || amount <= 0 || t.level().isClientSide) return;
        Target g = TARGETS.computeIfAbsent(t.getUUID(), k -> new Target());
        g.entity = t;
        g.debts.add(new Debt(amount, now + Math.max(1, ticks), tag));
    }

    /** School damage from the caster that is illusory as a whole; returns the health it really took. */
    public static float illusory(LivingEntity caster, LivingEntity t, float amount, int ticks, int tag) {
        if (!t.isAlive() || !(t.level() instanceof ServerLevel sl)) return 0;
        float before = t.getHealth();
        t.invulnerableTime = 0;
        t.hurt(source(sl, caster), amount);
        float lost = Math.max(0, before - t.getHealth());
        if (t.isAlive() && lost > 0) owe(t, lost, ticks, tag);
        return lost;
    }

    /** Health owed to the target now (not yet given back). */
    public static double owed(LivingEntity t) {
        Target g = TARGETS.get(t.getUUID());
        if (g == null) return 0;
        double s = g.returning;
        for (Debt d : g.debts) s += d.amount;
        return s;
    }

    /** The debts with this tag become real: they never come back. Returns the health that stays lost. */
    public static double realize(LivingEntity t, int tag) {
        Target g = TARGETS.get(t.getUUID());
        if (g == null) return 0;
        double s = 0;
        for (var it = g.debts.iterator(); it.hasNext(); ) {
            Debt d = it.next();
            if (d.tag != tag) continue;
            s += d.amount;
            it.remove();
        }
        return s;
    }

    /** The debts with this tag (0: all) fall due now. */
    public static void settleNow(LivingEntity t, int tag) {
        Target g = TARGETS.get(t.getUUID());
        if (g == null) return;
        for (Debt d : g.debts) if (tag == 0 || d.tag == tag) d.until = now;
    }

    /** Moves the due time of the debts with this tag (e.g. a mark made longer). */
    public static void extend(LivingEntity t, int tag, long until) {
        Target g = TARGETS.get(t.getUUID());
        if (g == null) return;
        for (Debt d : g.debts) if (d.tag == tag) d.until = Math.max(d.until, until);
    }

    public static long now() {
        return now;
    }

    // ---------------------------------------------------------------- dispel (Blessing)

    /** Something of the school on a victim that Blessing can take off. */
    public interface Dispellable {
        /** Takes the illusion off t; true if there was one. */
        boolean dispel(LivingEntity t);
    }

    private static final List<Dispellable> DISPELS = new ArrayList<>();

    public static void onDispel(Dispellable d) {
        DISPELS.add(d);
    }

    /** Blessing: every illusion and mark of the school off t, its illusory damage back at once. Returns how many things went. */
    public static int cleanse(LivingEntity t) {
        int n = 0;
        for (Dispellable d : DISPELS) {
            try {
                if (d.dispel(t)) n++;
            } catch (RuntimeException ex) {
                PohCore.LOG.error("[pohsmp_core] illusion dispel failed", ex);
            }
        }
        Target g = TARGETS.get(t.getUUID());
        if (g != null && !g.debts.isEmpty()) {
            settleNow(t, 0);
            n++;
        }
        return n;
    }

    // ---------------------------------------------------------------- events

    @SubscribeEvent
    public static void onTick(TickEvent.ServerTickEvent e) {
        // owner 19.11: the labyrinth's, the bestiary's (and more) own ServerTickEvent listeners were never called on the test server,
        // with nothing in the log - so the T22/T25 tickers are driven from here, each on its own, an error in one stopping no other
        hub("illusions", () -> self(e));
        hub("copies", () -> Copies.onTick(e));
        hub("voices", () -> Voices.onTick(e));
        hub("borrowed_face", () -> ru.pohsmp.core.spell.illusion.BorrowedFaceSpell.Events.onTick(e));
        hub("mirror_images", () -> ru.pohsmp.core.spell.illusion.MirrorImagesSpell.Events.onTick(e));
        hub("veil", () -> ru.pohsmp.core.spell.illusion.VeilSpell.Events.onTick(e));
        hub("mirror_labyrinth", () -> ru.pohsmp.core.spell.illusion.MirrorLabyrinthSpell.Events.onTick(e));
        hub("waking_nightmare", () -> ru.pohsmp.core.spell.illusion.WakingNightmareSpell.Events.onTick(e));
        hub("butterfly_dream", () -> ru.pohsmp.core.spell.illusion.ButterflyDreamSpell.Events.onTick(e));
        hub("immersion", () -> ru.pohsmp.core.nightmare.Immersion.onTick(e));
        hub("endless_night", () -> ru.pohsmp.core.nightmare.EndlessNightSpell.Events.onTick(e));
        hub("house_that_isnt", () -> ru.pohsmp.core.nightmare.HouseThatIsntSpell.Events.onTick(e));
        hub("bestiary", () -> ru.pohsmp.core.nightmare.Bestiary.Events.onTick(e));
    }

    private static final Map<String, Long> HUB_ERR = new HashMap<>();

    private static void hub(String name, Runnable r) {
        try {
            r.run();
        } catch (Throwable ex) {
            long t = System.currentTimeMillis();
            Long last = HUB_ERR.get(name);
            if (last == null || t - last > 60_000) {   // once a minute per ticker
                HUB_ERR.put(name, t);
                PohCore.LOG.error("[pohsmp] ticker " + name + " failed", ex);
            }
        }
    }

    private static void self(TickEvent.ServerTickEvent e) {
        if (e.phase != TickEvent.Phase.END) return;
        now++;
        if (TARGETS.isEmpty()) return;
        MinecraftServer server = e.getServer();
        int returnTicks = Math.max(1, ServerConfig.get(ServerConfig.IL_RETURN_TICKS));
        for (var it = TARGETS.entrySet().iterator(); it.hasNext(); ) {
            var en = it.next();
            Target g = en.getValue();
            LivingEntity t = g.entity;
            if (t == null || t.isRemoved()) {
                ServerPlayer p = server.getPlayerList().getPlayer(en.getKey());
                if (p != null) t = g.entity = p;
                else if (!(t instanceof Player)) {   // a mob that is gone: nothing to give back
                    it.remove();
                    continue;
                } else continue;   // a player offline: the debt waits for him
            }
            if (!t.isAlive()) continue;
            double due = 0;
            for (var di = g.debts.iterator(); di.hasNext(); ) {
                Debt d = di.next();
                if (d.until > now) continue;
                due += d.amount;
                di.remove();
            }
            if (due > 0) {
                g.returning += due;
                g.perTick = g.returning / returnTicks;
                if (t.level() instanceof ServerLevel sl) {
                    Fx.play(sl, Fx.fx("illusion_return").at(t.position()).target(t).caster(t).attach(t));
                    sl.playSound(null, t.getX(), t.getY() + 1, t.getZ(), net.minecraft.sounds.SoundEvents.AMETHYST_BLOCK_CHIME,
                            net.minecraft.sounds.SoundSource.PLAYERS, 1f, 1.4f);
                }
                if (t instanceof ServerPlayer sp) sp.displayClientMessage(Component.translatable("ui.pohsmp_core.illusion.returned",
                        ru.pohsmp.core.spell.PohSpell.n(Math.round(due * 10) / 10.0)).withStyle(s -> s.withColor(Reg.ILLUSION_COLOR)), true);
            }
            if (g.returning > 0) {
                double step = Math.min(g.returning, Math.max(g.perTick, 0.05));
                g.returning -= step;
                t.setHealth((float) Math.min(t.getMaxHealth(), t.getHealth() + step));
                if (g.returning < 1e-3) g.returning = 0;
            }
            if (g.debts.isEmpty() && g.returning <= 0) it.remove();
        }
    }

    /** Death in the time of an illusion is real: its debt is dropped. */
    @SubscribeEvent(priority = EventPriority.LOWEST)
    public static void onDeath(LivingDeathEvent e) {
        if (!e.isCanceled() && !e.getEntity().level().isClientSide) TARGETS.remove(e.getEntity().getUUID());
    }

    @SubscribeEvent
    public static void onStopping(ServerStoppingEvent e) {
        TARGETS.clear();
    }
}
