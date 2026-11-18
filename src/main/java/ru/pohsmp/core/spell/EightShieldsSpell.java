package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.registry.SchoolRegistry;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.spells.SpellRarity;
import io.redspace.ironsspellbooks.entity.spells.AbstractShieldEntity;
import io.redspace.ironsspellbooks.entity.spells.shield.ShieldEntity;
import java.lang.reflect.Field;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.projectile.Projectile;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.EntityHitResult;
import net.minecraftforge.entity.PartEntity;
import net.minecraftforge.event.entity.ProjectileImpactEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.DivineEvents;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.net.Net;
import ru.pohsmp.core.net.Net.HFx;

/**
 * Evocation: eight Iron's magic shields stand around the caster as a slowly turning octagonal wall and share one pool.
 * The pool absorbs damage to the caster and hits on the shields; each spent eighth of the pool breaks one shield.
 * The caster's own projectiles pass through its shields.
 */
public class EightShieldsSpell extends PohSpell {
    public static final String PATH = "eight_shields";
    private static final double RAD = 3.0;
    private static final float HP = 10000f;
    private static final int COLOR = 0x9FE6FF;

    /** shield entity id -> owner uuid (for letting the owner's projectiles through) */
    private static final Map<Integer, UUID> OWNERS = new ConcurrentHashMap<>();
    private static Field ageField;

    public EightShieldsSpell() {
        super(PATH, SchoolRegistry.EVOCATION_RESOURCE, SpellRarity.COMMON, 6, 40, 0, 40, 8);
    }

    @Override public CastType getCastType() { return CastType.INSTANT; }

    private double pool(int l, LivingEntity c) { return lv(l, 16, 40) * mult(c); }
    private int ticks(int l) { return (int) (lv(l, 6, 30) * 20); }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("pool", n(pool(level, caster))), ui("time", n(ticks(level) / 20.0)));
    }

    private static void resetAge(ShieldEntity s) {
        try {
            if (ageField == null) {
                ageField = ShieldEntity.class.getDeclaredField("age");
                ageField.setAccessible(true);
            }
            ageField.setInt(s, 0);
        } catch (ReflectiveOperationException | RuntimeException ignored) {
        }
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            int dur = ticks(spellLevel);
            float max = (float) pool(spellLevel, caster);
            PohEvents.Pool pool = PohEvents.addPool(caster, max, dur);
            caster.addEffect(new MobEffectInstance(Reg.EIGHT_SHIELDS.get(), dur, 0, false, false, true));
            List<ShieldEntity> shields = new ArrayList<>();
            for (int i = 0; i < 8; i++) {
                ShieldEntity s = new ShieldEntity(sl, HP);
                double a = i * Math.PI / 4;
                s.moveTo(caster.getX() + Math.cos(a) * RAD, caster.getY() + 1.1, caster.getZ() + Math.sin(a) * RAD);
                s.setRotation((float) Math.toDegrees(Math.PI / 2 - a), 0);
                Disp.track(s);
                sl.addFreshEntity(s);
                OWNERS.put(s.getId(), caster.getUUID());
                shields.add(s);
            }
            int key = HigherSpell.key();
            Net.sendNear(sl, caster.getX(), caster.getY(), caster.getZ(), caster.getX(), caster.getY(), caster.getZ(),
                    new HFx(HFx.WARD, key, caster.getId(), -1, dur, caster.getX(), caster.getY(), caster.getZ(), RAD, COLOR));
            sl.playSound(null, caster.getX(), caster.getY(), caster.getZ(), SoundEvents.ARMOR_EQUIP_NETHERITE, SoundSource.PLAYERS, 1.5f, 0.8f);
            sl.playSound(null, caster.getX(), caster.getY(), caster.getZ(), SoundEvents.BEACON_ACTIVATE, SoundSource.PLAYERS, 1.2f, 1.6f);
            Tasks.add(new Tasks.Task() {
                int age;

                @Override
                public boolean tick() {
                    age++;
                    // hits on the shields drain the shared pool
                    for (ShieldEntity s : shields) {
                        if (s.isRemoved()) continue;
                        float lost = HP - s.getHealth();
                        if (lost > 0) {
                            pool.left -= lost;
                            s.setHealth(HP);
                        }
                    }
                    boolean over = age > dur || !caster.isAlive() || caster.isRemoved() || pool.left <= 0 || PohEvents.pool(caster) != pool
                            || caster.level() != sl;
                    int keep = over ? 0 : (int) Math.ceil(8 * pool.left / max);
                    for (int i = 0; i < 8; i++) {
                        ShieldEntity s = shields.get(i);
                        if (s.isRemoved()) continue;
                        if (i >= keep) {
                            DivineEvents.particle(sl, ParticleTypes.ELECTRIC_SPARK, s.getX(), s.getY(), s.getZ(), 30, 0.8, 0.15);
                            sl.playSound(null, s.getX(), s.getY(), s.getZ(), SoundEvents.GLASS_BREAK, SoundSource.PLAYERS, 1f, 1.3f);
                            OWNERS.remove(s.getId());
                            s.discard();
                            continue;
                        }
                        double a = age * 0.015 + i * Math.PI / 4;
                        s.setPos(caster.getX() + Math.cos(a) * RAD, caster.getY() + 1.1, caster.getZ() + Math.sin(a) * RAD);
                        s.setRotation((float) Math.toDegrees(Math.PI / 2 - a), 0);
                        resetAge(s);
                    }
                    if (over) {
                        Net.sendNear(sl, caster.getX(), caster.getY(), caster.getZ(), caster.getX(), caster.getY(), caster.getZ(),
                                new HFx(HFx.STOP, key, -1, -1, 0, 0, 0, 0, 0, 0));
                        PohEvents.removePool(caster, pool);
                        caster.removeEffect(Reg.EIGHT_SHIELDS.get());
                    }
                    return !over;
                }
            });
        }
        super.onCast(level, spellLevel, caster, source, md);
    }

    public static final class EightShieldsEvents {
        private EightShieldsEvents() {}

        /** The owner's projectiles go through its own shields. */
        @SubscribeEvent
        public static void onImpact(ProjectileImpactEvent e) {
            if (OWNERS.isEmpty() || !(e.getRayTraceResult() instanceof EntityHitResult hit)) return;
            Entity t = hit.getEntity();
            Entity shield = t instanceof PartEntity<?> part ? part.getParent() : t;
            if (!(shield instanceof AbstractShieldEntity)) return;
            UUID owner = OWNERS.get(shield.getId());
            Projectile p = e.getProjectile();
            if (owner != null && p.getOwner() != null && owner.equals(p.getOwner().getUUID())) e.setImpactResult(ProjectileImpactEvent.ImpactResult.SKIP_ENTITY);
        }
    }
}
