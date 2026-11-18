package ru.pohsmp.core.spell;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import net.minecraft.core.registries.Registries;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.tags.DamageTypeTags;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.player.Player;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.living.LivingAttackEvent;
import net.minecraftforge.event.entity.living.LivingDamageEvent;
import net.minecraftforge.event.entity.living.LivingEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.Reg;

/** Server-side state and event hooks of the ordinary spells: Living Shield, Eight Shields, Paralysis, Wind Mark. */
public final class PohEvents {
    private PohEvents() {}

    // ---- Living Shield ----

    private static final class Shield {
        LivingEntity caster;
        double r;
        long until;
    }

    private static final Map<UUID, Shield> SHIELDS = new HashMap<>();
    private static final ThreadLocal<Boolean> REDIRECT = ThreadLocal.withInitial(() -> false);

    static void addShield(LivingEntity caster, double r, int ticks) {
        Shield s = new Shield();
        s.caster = caster;
        s.r = r;
        s.until = caster.level().getGameTime() + ticks;
        SHIELDS.put(caster.getUUID(), s);
    }

    static boolean hasShield(LivingEntity caster) {
        Shield s = SHIELDS.get(caster.getUUID());
        return s != null && s.caster == caster && caster.level().getGameTime() <= s.until;
    }

    static List<LivingEntity> shieldedBy(LivingEntity caster) {
        List<LivingEntity> out = new ArrayList<>();
        Shield s = SHIELDS.get(caster.getUUID());
        if (s == null) return out;
        for (Player p : caster.level().players())
            if (p != caster && p.isAlive() && !p.isSpectator() && p.distanceToSqr(caster) <= s.r * s.r) out.add(p);
        return out;
    }

    private static Shield shieldFor(Player p) {
        Shield best = null;
        double bd = Double.MAX_VALUE;
        long now = p.level().getGameTime();
        for (Shield s : SHIELDS.values()) {
            if (s.caster == p || now > s.until || !s.caster.isAlive() || s.caster.level() != p.level()) continue;
            double d = s.caster.distanceToSqr(p);
            if (d <= s.r * s.r && d < bd) { bd = d; best = s; }
        }
        return best;
    }

    // ---- Eight Shields ----

    public static final class Pool {
        public float left;
        long until;
    }

    private static final Map<UUID, Pool> POOLS = new HashMap<>();

    static Pool addPool(LivingEntity caster, float amount, int ticks) {
        Pool p = new Pool();
        p.left = amount;
        p.until = caster.level().getGameTime() + ticks;
        POOLS.put(caster.getUUID(), p);
        return p;
    }

    static Pool pool(LivingEntity caster) {
        return POOLS.get(caster.getUUID());
    }

    static void removePool(LivingEntity caster, Pool p) {
        POOLS.remove(caster.getUUID(), p);
    }

    @SubscribeEvent(priority = EventPriority.LOW)
    public static void onDamage(LivingDamageEvent e) {
        LivingEntity le = e.getEntity();
        if (le.level().isClientSide || REDIRECT.get()) return;
        DamageSource src = e.getSource();
        if (src.is(DamageTypeTags.BYPASSES_INVULNERABILITY)) return;
        Pool pool = POOLS.get(le.getUUID());
        if (pool != null && pool.left > 0 && le.level().getGameTime() <= pool.until) {
            float take = Math.min(pool.left, e.getAmount());
            pool.left -= take;
            e.setAmount(e.getAmount() - take);
            if (e.getAmount() <= 0) {
                e.setCanceled(true);
                return;
            }
        }
        if (le instanceof Player p && !SHIELDS.isEmpty()) {
            Shield s = shieldFor(p);
            if (s == null) return;
            float amount = e.getAmount();
            e.setCanceled(true);
            ServerLevel sl = (ServerLevel) p.level();
            DamageSource redirected = new DamageSource(sl.registryAccess().registryOrThrow(Registries.DAMAGE_TYPE).getHolderOrThrow(Reg.SHIELD_DAMAGE),
                    src.getEntity() != null ? src.getEntity() : null);
            REDIRECT.set(true);
            try {
                s.caster.invulnerableTime = 0;
                s.caster.hurt(redirected, amount);
            } finally {
                REDIRECT.set(false);
            }
            ru.pohsmp.core.DivineEvents.particle(sl, net.minecraft.core.particles.ParticleTypes.END_ROD, p.getX(), p.getY() + 1, p.getZ(), 6, 0.3, 0.05);
        }
    }

    // ---- Paralysis ----

    @SubscribeEvent
    public static void onAttack(LivingAttackEvent e) {
        if (e.getSource().getDirectEntity() instanceof LivingEntity a && a.hasEffect(Reg.PARALYSIS.get())) e.setCanceled(true);
    }

    @SubscribeEvent
    public static void onJump(LivingEvent.LivingJumpEvent e) {
        LivingEntity le = e.getEntity();
        if (le.hasEffect(Reg.PARALYSIS.get()) || le.hasEffect(Reg.SPENT.get()))
            le.setDeltaMovement(le.getDeltaMovement().x, Math.min(0, le.getDeltaMovement().y), le.getDeltaMovement().z);
    }

    // ---- Wind Mark ----

    static void toss(LivingEntity e) {
        HigherSpell.push(e, e.getDeltaMovement().multiply(0.3, 0, 0.3).add(0, 0.92, 0));
    }

    @SubscribeEvent
    public static void onLivingTick(LivingEvent.LivingTickEvent e) {
        LivingEntity le = e.getEntity();
        if (le.level().isClientSide) return;
        MobEffectInstance t = le.getEffect(Reg.TOSS.get());
        if (t != null && t.getDuration() % 40 == 0 && t.getDuration() > 0) {
            toss(le);
            ru.pohsmp.core.DivineEvents.particle((ServerLevel) le.level(), net.minecraft.core.particles.ParticleTypes.CLOUD, le.getX(), le.getY(), le.getZ(), 15, 0.4, 0.05);
        }
        if (le instanceof Mob m && (le.hasEffect(Reg.PARALYSIS.get()) || le.hasEffect(Reg.SPENT.get()))) m.getNavigation().stop();
    }

    @SubscribeEvent
    public static void onServerTick(TickEvent.ServerTickEvent e) {
        if (e.phase != TickEvent.Phase.END) return;
        if (!SHIELDS.isEmpty()) SHIELDS.values().removeIf(s -> !s.caster.isAlive() || s.caster.isRemoved() || s.caster.level().getGameTime() > s.until);
        if (!POOLS.isEmpty()) POOLS.values().removeIf(p -> p.left <= 0);
    }

    @SubscribeEvent
    public static void onStopping(ServerStoppingEvent e) {
        SHIELDS.clear();
        POOLS.clear();
    }
}
