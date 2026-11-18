package ru.pohsmp.core.spell;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import net.minecraft.core.particles.DustParticleOptions;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.living.LivingAttackEvent;
import net.minecraftforge.event.entity.living.LivingDamageEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import org.joml.Vector3f;
import ru.pohsmp.core.DivineEvents;
import ru.pohsmp.core.Reg;

/** Server state of the mark-type ordinary spells: Blood Mark, Hemorrhage, Overload, Spore Cloud, Illusion. */
public final class Marks {
    private Marks() {}

    static final DustParticleOptions BLOOD = new DustParticleOptions(new Vector3f(0.6f, 0.02f, 0.05f), 1.1f);
    static final DustParticleOptions SPORE = new DustParticleOptions(new Vector3f(0.55f, 0.75f, 0.25f), 1.3f);

    /** One running mark on one target. */
    static final class Mark {
        PohSpell spell;
        LivingEntity caster, target;
        long until;
        double a, b;          // spell values (meaning depends on kind)
        double sum;           // overload: stored damage
        Vec3 last;            // hemorrhage: last position
        int gen;              // spores: infection generation
    }

    static final Map<UUID, Mark> BLOOD_MARK = new HashMap<>();
    static final Map<UUID, Mark> HEMORRHAGE = new HashMap<>();
    static final Map<UUID, Mark> OVERLOAD = new HashMap<>();
    static final Map<UUID, Mark> SPORES = new HashMap<>();

    static Mark put(Map<UUID, Mark> map, PohSpell spell, LivingEntity caster, LivingEntity t, int ticks, double a, double b) {
        Mark m = new Mark();
        m.spell = spell;
        m.caster = caster;
        m.target = t;
        m.until = t.level().getGameTime() + ticks;
        m.a = a;
        m.b = b;
        m.last = t.position();
        map.put(t.getUUID(), m);
        return m;
    }

    // ---- Illusion decoys ----

    static final class Decoy {
        PohSpell spell;
        LivingEntity caster;
        Entity body;
        long until;
        float dmg;
        double r;
        List<Mob> lured = new ArrayList<>();
    }

    static final List<Decoy> DECOYS = new ArrayList<>();

    static void boom(ServerLevel sl, Decoy d) {
        if (!DECOYS.remove(d)) return;
        Vec3 c = d.body.position();
        Disp.kill(d.body);
        sl.playSound(null, c.x, c.y, c.z, SoundEvents.ILLUSIONER_MIRROR_MOVE, SoundSource.PLAYERS, 2f, 0.6f);
        sl.playSound(null, c.x, c.y, c.z, SoundEvents.GENERIC_EXPLODE, SoundSource.PLAYERS, 1.5f, 1.3f);
        DivineEvents.particle(sl, ParticleTypes.EXPLOSION, c.x, c.y + 1, c.z, 3, 0.6, 0);
        DivineEvents.particle(sl, ParticleTypes.WITCH, c.x, c.y + 1, c.z, 60, 0.8, 0.2);
        for (LivingEntity e : HigherSpell.around(sl, c, d.r, e -> !HigherSpell.friendly(d.caster, e))) {
            d.spell.hit(d.caster, e, d.dmg);
            Vec3 away = e.position().subtract(c).multiply(1, 0, 1);
            if (away.lengthSqr() > 1e-4) HigherSpell.push(e, away.normalize().scale(0.8).add(0, 0.35, 0));
        }
        for (Mob m : d.lured) if (m.isAlive()) m.getNavigation().stop();
    }

    // ---- events ----

    @SubscribeEvent(priority = EventPriority.LOWEST)
    public static void onDamage(LivingDamageEvent e) {
        LivingEntity t = e.getEntity();
        if (t.level().isClientSide || e.getAmount() <= 0) return;
        Mark bm = BLOOD_MARK.get(t.getUUID());
        if (bm != null && e.getSource().getEntity() instanceof LivingEntity a && a != t && a.isAlive()) {
            a.heal((float) (e.getAmount() * bm.a));
            DivineEvents.particle((ServerLevel) t.level(), BLOOD, a.getX(), a.getY() + 1, a.getZ(), 6, 0.3, 0);
        }
        Mark ov = OVERLOAD.get(t.getUUID());
        if (ov != null && !Overload.OVERLOADING.get()) ov.sum += e.getAmount();
    }

    @SubscribeEvent
    public static void onAttack(LivingAttackEvent e) {
        if (DECOYS.isEmpty() || e.getEntity().level().isClientSide) return;
        for (Decoy d : new ArrayList<>(DECOYS))
            if (d.body == e.getEntity()) {
                e.setCanceled(true);
                boom((ServerLevel) e.getEntity().level(), d);
            }
    }

    @SubscribeEvent
    public static void onServerTick(TickEvent.ServerTickEvent e) {
        if (e.phase != TickEvent.Phase.END) return;
        tickBlood();
        tickHemorrhage();
        tickOverload();
        tickSpores();
        tickDecoys();
    }

    private static boolean gone(Mark m) {
        return !m.target.isAlive() || m.target.isRemoved() || m.target.level().getGameTime() > m.until;
    }

    private static void tickBlood() {
        BLOOD_MARK.values().removeIf(m -> {
            if (gone(m)) { m.target.removeEffect(Reg.BLOOD_MARK.get()); return true; }
            if (m.target.tickCount % 5 == 0)
                DivineEvents.particle((ServerLevel) m.target.level(), BLOOD, m.target.getX(), m.target.getY() + m.target.getBbHeight() + 0.3, m.target.getZ(), 2, 0.15, 0);
            return false;
        });
    }

    private static void tickHemorrhage() {
        HEMORRHAGE.values().removeIf(m -> {
            if (gone(m)) { m.target.removeEffect(Reg.HEMORRHAGE.get()); return true; }
            if (m.target.tickCount % 10 != 0) return false;
            Vec3 p = m.target.position();
            double moved = Math.min(6, p.distanceTo(m.last));
            m.last = p;
            if (moved > 0.15) {
                m.spell.hit(m.caster, m.target, (float) (moved * m.a));
                DivineEvents.particle((ServerLevel) m.target.level(), BLOOD, p.x, p.y + 0.8, p.z, 4 + (int) (moved * 4), 0.3, 0);
                DivineEvents.particle((ServerLevel) m.target.level(), ParticleTypes.DAMAGE_INDICATOR, p.x, p.y + 1, p.z, 1, 0.2, 0);
            } else if (m.target.tickCount % 20 == 0) {
                DivineEvents.particle((ServerLevel) m.target.level(), BLOOD, p.x, p.y + 0.6, p.z, 2, 0.2, 0);
            }
            return false;
        });
    }

    private static void tickOverload() {
        Iterator<Mark> it = OVERLOAD.values().iterator();
        while (it.hasNext()) {
            Mark m = it.next();
            LivingEntity t = m.target;
            ServerLevel sl = (ServerLevel) t.level();
            if (!t.isAlive() || t.isRemoved()) { it.remove(); continue; }
            if (t.tickCount % 4 == 0)
                DivineEvents.particle(sl, ParticleTypes.ELECTRIC_SPARK, t.getX(), t.getY() + t.getBbHeight() * 0.6, t.getZ(), 2 + (int) Math.min(10, m.sum / 3), 0.4, 0.05);
            if (sl.getGameTime() < m.until) continue;
            it.remove();
            t.removeEffect(Reg.OVERLOAD.get());
            float dmg = (float) (m.b + m.sum * m.a);
            Vec3 c = t.position();
            sl.playSound(null, c.x, c.y, c.z, SoundEvents.LIGHTNING_BOLT_IMPACT, SoundSource.PLAYERS, 2.5f, 1.4f);
            DivineEvents.particle(sl, ParticleTypes.ELECTRIC_SPARK, c.x, c.y + 1, c.z, 80, 1.2, 0.3);
            DivineEvents.particle(sl, ParticleTypes.FLASH, c.x, c.y + 1, c.z, 1, 0, 0);
            for (LivingEntity e : HigherSpell.around(sl, c, 3.5, e -> !HigherSpell.friendly(m.caster, e))) {
                Overload.OVERLOADING.set(true);
                try {
                    m.spell.hit(m.caster, e, e == t ? dmg : dmg * 0.6f);
                } finally {
                    Overload.OVERLOADING.set(false);
                }
            }
        }
    }

    /** Overload: damage of the discharge itself is not stored again. */
    static final class Overload {
        static final ThreadLocal<Boolean> OVERLOADING = ThreadLocal.withInitial(() -> false);
    }

    private static void tickSpores() {
        if (SPORES.isEmpty()) return;
        List<Mark> spread = new ArrayList<>();
        SPORES.values().removeIf(m -> {
            if (gone(m)) { m.target.removeEffect(Reg.SPORES.get()); return true; }
            LivingEntity t = m.target;
            if (t.tickCount % 6 == 0) DivineEvents.particle((ServerLevel) t.level(), SPORE, t.getX(), t.getY() + t.getBbHeight() * 0.7, t.getZ(), 2, 0.3, 0);
            if (t.tickCount % 20 == 0) {
                m.spell.hit(m.caster, t, (float) m.a);
                if (m.gen < 2) spread.add(m);
            }
            return false;
        });
        for (Mark m : spread) {
            ServerLevel sl = (ServerLevel) m.target.level();
            for (LivingEntity n : HigherSpell.around(sl, m.target.position(), 2.2, e -> e != m.target && !HigherSpell.friendly(m.caster, e) && !SPORES.containsKey(e.getUUID()))) {
                infect(m.spell, m.caster, n, 100, m.a, m.gen + 1);
                DivineEvents.particle(sl, SPORE, n.getX(), n.getY() + 1, n.getZ(), 10, 0.4, 0);
            }
        }
    }

    static void infect(PohSpell spell, LivingEntity caster, LivingEntity t, int ticks, double dps, int gen) {
        Mark m = SPORES.get(t.getUUID());
        if (m != null && m.gen <= gen) {
            m.until = Math.max(m.until, t.level().getGameTime() + ticks);
        } else {
            m = put(SPORES, spell, caster, t, ticks, dps, 0);
            m.gen = gen;
        }
        t.addEffect(new MobEffectInstance(Reg.SPORES.get(), (int) (m.until - t.level().getGameTime()), 0, false, true, true));
        t.addEffect(new MobEffectInstance(MobEffects.CONFUSION, 80, 0, false, false, false));
    }

    private static void tickDecoys() {
        if (DECOYS.isEmpty()) return;
        for (Decoy d : new ArrayList<>(DECOYS)) {
            ServerLevel sl = (ServerLevel) d.body.level();
            if (d.body.isRemoved() || !d.caster.isAlive() || sl.getGameTime() > d.until) {
                if (!d.body.isRemoved()) boom(sl, d);
                else DECOYS.remove(d);
                continue;
            }
            if (sl.getGameTime() % 10 == 0) {   // lure mobs that hunt the caster
                for (Mob m : sl.getEntitiesOfClass(Mob.class, d.body.getBoundingBox().inflate(20),
                        m -> m.getTarget() == d.caster && !d.lured.contains(m))) d.lured.add(m);
                DivineEvents.particle(sl, ParticleTypes.WITCH, d.body.getX(), d.body.getY() + 1, d.body.getZ(), 3, 0.3, 0);
            }
            for (Mob m : d.lured) {
                if (!m.isAlive()) continue;
                if (m.getTarget() == d.caster) m.setTarget(null);
                if (sl.getGameTime() % 5 == 0) m.getNavigation().moveTo(d.body.getX(), d.body.getY(), d.body.getZ(), 1.2);
                m.getLookControl().setLookAt(d.body);
                if (m.distanceToSqr(d.body) < 2.2 * 2.2) {
                    m.swing(net.minecraft.world.InteractionHand.MAIN_HAND);
                    boom(sl, d);
                    break;
                }
            }
        }
    }

    @SubscribeEvent
    public static void onStopping(ServerStoppingEvent e) {
        BLOOD_MARK.clear();
        HEMORRHAGE.clear();
        OVERLOAD.clear();
        SPORES.clear();
        DECOYS.clear();
    }
}
