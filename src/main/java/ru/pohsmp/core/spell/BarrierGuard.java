package ru.pohsmp.core.spell;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import net.minecraft.core.registries.Registries;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.OwnableEntity;
import net.minecraft.world.entity.animal.AbstractGolem;
import net.minecraft.world.entity.npc.AbstractVillager;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.common.Tags;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.ServerConfig;

/**
 * Owner 19.11 («the barrier kills mobs that try to pass it»): shared by the Barrier spell (silent/SageBarrierSpell) and the dome of
 * Closing of Space / Coven Arrival (SpaceClosureSpell). A mob that crosses the shell dies at once (an ordinary death with its drops),
 * with a flash in the barrier's colour, a ripple on the shell and a quiet sound of falling apart. Bosses are pushed off instead and lose
 * a part of their max health once a second of contact. The callers decide what a crossing is and keep the mobs that were inside when
 * the barrier rose out of it.
 */
public final class BarrierGuard {
    private BarrierGuard() {}

    /** What the shell does to e when it crosses it. */
    public enum Verdict { PASS, KILL, BOSS }

    public static Verdict judge(LivingEntity caster, Entity e) {
        if (!(e instanceof Mob m) || !m.isAlive() || !ServerConfig.BARRIER_KILL_MOBS.get()) return Verdict.PASS;
        if (boss(m)) return Verdict.BOSS;
        if (m instanceof AbstractVillager || m instanceof AbstractGolem || CnpcHooks.isNpc(m)) return Verdict.PASS;
        if (m instanceof OwnableEntity o && o.getOwnerUUID() != null) return Verdict.PASS;   // anybody's pets
        if (caster != null && (HigherSpell.friendly(caster, m) || m.isAlliedTo(caster))) return Verdict.PASS;
        return Verdict.KILL;
    }

    public static boolean boss(Entity e) {
        EntityType<?> t = e.getType();
        return ru.pohsmp.core.boss.BossGuard.isBoss(e) || t.is(Tags.EntityTypes.BOSSES) || t == EntityType.WITHER || t == EntityType.ENDER_DRAGON || t == EntityType.WARDEN
                || t == EntityType.ELDER_GUARDIAN;
    }

    /** No attacker and no position: the shells' own damage filters let it through. */
    private static DamageSource source(ServerLevel sl) {
        return new DamageSource(sl.registryAccess().registryOrThrow(Registries.DAMAGE_TYPE).getHolderOrThrow(Reg.HIGHER_DAMAGE));
    }

    /** Kills the mob where it touched the shell at `at` (the caller draws the ripple on its own shell). */
    public static void kill(ServerLevel sl, LivingEntity e, Vec3 at, int rgb) {
        HigherSpell.burst(sl, at.x, at.y, at.z, 1.4, rgb);
        sl.playSound(null, at.x, at.y, at.z, SoundEvents.AMETHYST_CLUSTER_BREAK, SoundSource.HOSTILE, 0.7f, 0.55f);
        sl.playSound(null, at.x, at.y, at.z, SoundEvents.SOUL_ESCAPE, SoundSource.HOSTILE, 0.6f, 0.8f);
        e.invulnerableTime = 0;
        e.hurt(source(sl), Float.MAX_VALUE);
        if (e.isAlive()) e.kill();   // immune to magic: still gone
    }

    // ---------------------------------------------------------------- Waystones (manager 19.11)

    /** Inside either barrier: the Barrier spell's dome or the Closing of Space / Coven dome. */
    public static boolean inBarrier(net.minecraft.world.level.Level level, Vec3 p) {
        return ru.pohsmp.core.spell.silent.SageBarrierSpell.anyInside(level, p) || SpaceClosureSpell.anyInside(level, p);
    }

    private static final java.util.Set<String> WARP_ITEMS = java.util.Set.of("waystones:warp_stone", "waystones:warp_scroll",
            "waystones:bound_scroll", "waystones:return_scroll");

    private static void deny(Entity e) {
        if (e instanceof net.minecraft.world.entity.player.Player p)
            p.displayClientMessage(net.minecraft.network.chat.Component.translatable("ui.pohsmp_core.barrier.no_warp")
                    .withStyle(s -> s.withColor(SpaceClosureSpell.COLOR)), true);
    }

    /**
     * Waystones (soft: only when loaded): no warp stone, warp scrolls or waystone teleport when the traveller or the destination is
     * inside a barrier. WaystoneTeleportEvent.Pre is cancelled (its item is then not used up, no cooldown); the warp items are not even
     * started inside a barrier. Called from PohCore.
     */
    @SuppressWarnings("unchecked")
    public static void hookWaystones() {
        if (!net.minecraftforge.fml.ModList.get().isLoaded("waystones")) return;
        try {
            Class<? extends net.minecraftforge.eventbus.api.Event> pre = (Class<? extends net.minecraftforge.eventbus.api.Event>)
                    Class.forName("net.blay09.mods.waystones.api.WaystoneTeleportEvent$Pre");
            java.lang.reflect.Method ctx = pre.getMethod("getContext");
            net.minecraftforge.common.MinecraftForge.EVENT_BUS.addListener(net.minecraftforge.eventbus.api.EventPriority.HIGH, false, pre, ev -> {
                try {
                    Object c = ctx.invoke(ev);
                    Entity e = (Entity) c.getClass().getMethod("getEntity").invoke(c);
                    Object dest = c.getClass().getMethod("getDestination").invoke(c);
                    net.minecraft.world.level.Level dl = (net.minecraft.world.level.Level) dest.getClass().getMethod("getLevel").invoke(dest);
                    Vec3 to = (Vec3) dest.getClass().getMethod("getLocation").invoke(dest);
                    if (e == null || e.level().isClientSide) return;
                    if (inBarrier(e.level(), e.position()) || (dl != null && to != null && inBarrier(dl, to))) {
                        ev.setCanceled(true);
                        deny(e);
                    }
                } catch (ReflectiveOperationException | RuntimeException ex) {
                    LOG.warn("[pohsmp] waystones barrier check failed: {}", ex.toString());
                }
            });
            LOG.info("[pohsmp] barriers: Waystones teleports out of / into barriers are blocked");
        } catch (ReflectiveOperationException | RuntimeException ex) {
            LOG.warn("[pohsmp] Waystones API not found, barrier teleport rule off: {}", ex.toString());
        }
    }

    private static final org.slf4j.Logger LOG = com.mojang.logging.LogUtils.getLogger();

    public static final class WarpEvents {
        private WarpEvents() {}

        @net.minecraftforge.eventbus.api.SubscribeEvent
        public static void onUse(net.minecraftforge.event.entity.player.PlayerInteractEvent.RightClickItem e) {
            if (e.getLevel().isClientSide || !warpItem(e.getItemStack())) return;
            if (!inBarrier(e.getLevel(), e.getEntity().position())) return;
            e.setCanceled(true);
            e.setCancellationResult(net.minecraft.world.InteractionResult.FAIL);
            deny(e.getEntity());
        }

        @net.minecraftforge.eventbus.api.SubscribeEvent
        public static void onUseStart(net.minecraftforge.event.entity.living.LivingEntityUseItemEvent.Start e) {
            if (e.getEntity().level().isClientSide || !warpItem(e.getItem()) || !inBarrier(e.getEntity().level(), e.getEntity().position())) return;
            e.setCanceled(true);
            deny(e.getEntity());
        }

        private static boolean warpItem(net.minecraft.world.item.ItemStack s) {
            if (s.isEmpty()) return false;
            net.minecraft.resources.ResourceLocation id = net.minecraftforge.registries.ForgeRegistries.ITEMS.getKey(s.getItem());
            return id != null && WARP_ITEMS.contains(id.toString());
        }
    }

    private static final Map<UUID, Long> LAST_BOSS_HIT = new HashMap<>();

    /** A boss on the shell: pushed along `away` (unit, the side it came from), once a second it loses BARRIER_BOSS_PCT of its max health. */
    public static void repel(ServerLevel sl, LivingEntity e, Vec3 away, Vec3 at, int rgb) {
        e.setDeltaMovement(away.scale(1.1).add(0, 0.3, 0));   // not HigherSpell.push: the shell pushes even displacement-immune bosses
        e.hurtMarked = true;
        long now = sl.getGameTime();
        Long last = LAST_BOSS_HIT.get(e.getUUID());
        if (last != null && now - last < 20) return;
        LAST_BOSS_HIT.put(e.getUUID(), now);
        if (LAST_BOSS_HIT.size() > 256) LAST_BOSS_HIT.values().removeIf(t -> now - t > 200);
        HigherSpell.burst(sl, at.x, at.y, at.z, 2.2, rgb);
        sl.playSound(null, at.x, at.y, at.z, SoundEvents.AMETHYST_BLOCK_RESONATE, SoundSource.HOSTILE, 1.5f, 0.5f);
        float dmg = (float) (e.getMaxHealth() * ru.pohsmp.core.boss.BossGuard.barrierShare(e, ServerConfig.BARRIER_BOSS_PCT.get()));   // cult bosses: [bosses_common] barrier_push_share
        if (dmg > 0) {
            e.invulnerableTime = 0;
            e.hurt(source(sl), dmg);
        }
    }

    // ---- streams against the shell (Milky Way, manager 19.11) and the cracks they leave ----

    /** One live barrier shell of the level: owner (the zone or dome object, for the crack limit), centre, radius, colour. */
    public record Shell(Object owner, Vec3 c, double r, int color) {}

    /** Where a stream stops: the shell, the stopped centre, the touch point on the shell, and whether the stream is inside it. */
    public record Stop(Shell shell, Vec3 at, Vec3 touch, boolean inside) {}

    public static java.util.List<Shell> shells(net.minecraft.world.level.Level lvl) {
        java.util.List<Shell> out = new java.util.ArrayList<>();
        SpaceClosureSpell.shells(lvl, out);
        ru.pohsmp.core.spell.silent.SageBarrierSpell.shells(lvl, out);
        return out;
    }

    /**
     * A stream of radius rad moving from cur to next: if next comes closer than rad to a shell from cur's side (outside: |c - o| < r + rad,
     * inside: > r - rad), the stop at that distance along the shell normal; null when nothing is in the way.
     */
    public static Stop stream(net.minecraft.world.level.Level lvl, Vec3 cur, Vec3 next, double rad) {
        for (Shell s : shells(lvl)) {
            boolean inside = cur.distanceToSqr(s.c()) < s.r() * s.r();
            if (inside && s.r() <= rad) continue;   // a stream wider than the dome it starts in (Barrier r 5 vs Milky Way 6): no room to stop in
            Vec3 d = next.subtract(s.c());
            double len = d.length();
            if (inside ? len <= s.r() - rad : len >= s.r() + rad) continue;
            Vec3 n = len < 1e-6 ? new Vec3(1, 0, 0) : d.scale(1 / len);
            double keep = inside ? Math.max(0, s.r() - rad) : s.r() + rad;
            return new Stop(s, s.c().add(n.scale(keep)), s.c().add(n.scale(s.r())), inside);
        }
        return null;
    }

    /** True when a and b are on the same side of every shell of the level (a stream does not reach through a barrier). */
    public static boolean sameSide(net.minecraft.world.level.Level lvl, Vec3 a, Vec3 b) {
        for (Shell s : shells(lvl)) {
            double r2 = s.r() * s.r();
            if ((a.distanceToSqr(s.c()) < r2) != (b.distanceToSqr(s.c()) < r2)) return false;
        }
        return true;
    }

    public static final int CRACK_TICKS = 66, CRACK_EVERY = 10, CRACK_MAX = 4;
    private static final Map<Object, java.util.ArrayDeque<Long>> CRACKS = new java.util.WeakHashMap<>();

    /**
     * Cracks where a stream presses on a shell (client HigherFx.closureCrack, textures/fx/barrier_cracks.png): at most one per 0.5 s
     * and 4 at once per shell; a flash and the lattice ripple with the glass breaking at the start, a high chime when it has healed (3.3 s).
     * Visual only. Placed near the touch point, a little apart each time, so several do not lie on one another.
     */
    public static void crack(ServerLevel sl, Stop st) {
        Shell s = st.shell();
        long now = sl.getGameTime();
        java.util.ArrayDeque<Long> q = CRACKS.computeIfAbsent(s.owner(), k -> new java.util.ArrayDeque<>());
        while (!q.isEmpty() && now - q.peekFirst() >= CRACK_TICKS) q.pollFirst();
        if (q.size() >= CRACK_MAX || (!q.isEmpty() && now - q.peekLast() < CRACK_EVERY)) return;
        q.addLast(now);
        Vec3 n = st.touch().subtract(s.c()).normalize();
        double jit = Math.min(3.5, s.r() * 0.3);
        Vec3 off = new Vec3(sl.random.nextGaussian(), sl.random.nextGaussian(), sl.random.nextGaussian());
        off = off.subtract(n.scale(off.dot(n)));
        if (off.lengthSqr() > 1e-6) off = off.normalize().scale(jit * Math.sqrt(sl.random.nextDouble()));
        Vec3 p = s.c().add(st.touch().add(off).subtract(s.c()).normalize().scale(s.r()));
        Vec3 pn = p.subtract(s.c()).normalize();
        int yaw = (int) Math.round(Math.atan2(pn.z, pn.x) * 1000), pitch = (int) Math.round(Math.asin(Math.max(-1, Math.min(1, pn.y))) * 1000);
        float rad = (float) Math.min(6.5, s.r() * 0.75);
        ru.pohsmp.core.net.Net.sendNear(sl, p.x, p.y, p.z, p.x, p.y, p.z, new ru.pohsmp.core.net.Net.HFx(ru.pohsmp.core.net.Net.HFx.CLOSURE_CRACK, HigherSpell.key(),
                yaw, pitch, CRACK_TICKS, p.x, p.y, p.z, rad, s.color()));
        ru.pohsmp.core.net.Net.sendNear(sl, p.x, p.y, p.z, p.x, p.y, p.z, new ru.pohsmp.core.net.Net.HFx(ru.pohsmp.core.net.Net.HFx.CLOSURE_HIT, HigherSpell.key(),
                yaw, pitch, 24, p.x, p.y, p.z, rad * 0.55, s.color()));
        sl.playSound(null, p.x, p.y, p.z, SoundEvents.GLASS_BREAK, SoundSource.PLAYERS, 1.2f, 0.6f + 0.2f * sl.random.nextFloat());
        Tasks.add(new Tasks.Task() {
            int age;

            @Override
            public boolean tick() {
                if (++age < CRACK_TICKS) return true;
                sl.playSound(null, p.x, p.y, p.z, SoundEvents.AMETHYST_BLOCK_CHIME, SoundSource.PLAYERS, 1.2f, 1.4f);
                return false;
            }
        });
    }
}
