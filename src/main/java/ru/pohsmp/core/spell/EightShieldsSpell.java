package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.registry.SchoolRegistry;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.spells.SpellRarity;
import java.util.List;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.projectile.AbstractArrow;
import net.minecraft.world.entity.projectile.Projectile;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.DivineEvents;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.fx.Fx;

/**
 * Evocation: eight rune seals stand around the caster as a slowly turning octagonal wall and share one pool.
 * The seals themselves are the shields (no entities): an enemy projectile flying into a seal from outside is stopped
 * and its damage goes to the pool. The pool also absorbs damage to the caster (PohEvents); each spent eighth of it
 * breaks one seal. The caster's own projectiles pass through.
 */
public class EightShieldsSpell extends PohSpell {
    public static final String PATH = "eight_shields";
    private static final double RAD = 3.0;
    /** height of the seal centres above the caster's feet */
    private static final double SEAL_Y = 1.6;
    /** hit radius of a seal (sigil size 1.3 * glow radius 1.05) */
    private static final double SEAL_R = 1.35;
    /** pool cost of a projectile whose damage is unknown */
    private static final float OTHER_HIT = 6f;
    /** sigils/eight_shields_seal.json: one per wall segment, upright, facing outwards. */
    private static final String SEAL = "eight_shields_seal";

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

    private static double angle(int age, int i) { return age * 0.015 + i * Math.PI / 4; }

    private static Vec3 center(LivingEntity c, double a) {
        return new Vec3(c.getX() + Math.cos(a) * RAD, c.getY() + SEAL_Y, c.getZ() + Math.sin(a) * RAD);
    }

    private static float yaw(double a) { return (float) Math.toDegrees(Math.PI / 2 - a); }

    /** Damage the projectile would deal, for the pool. */
    private static float damageOf(Projectile p) {
        if (p instanceof AbstractArrow arrow) return (float) Math.ceil(p.getDeltaMovement().length() * arrow.getBaseDamage());
        return OTHER_HIT;
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            int dur = ticks(spellLevel);
            float max = (float) pool(spellLevel, caster);
            PohEvents.Pool pool = PohEvents.addPool(caster, max, dur);
            caster.addEffect(new MobEffectInstance(Reg.EIGHT_SHIELDS.get(), dur, 0, false, false, true));
            int[] seals = new int[8];
            boolean[] alive = new boolean[8];
            for (int i = 0; i < 8; i++) {
                double a = angle(0, i);
                seals[i] = Fx.play(sl, Fx.sigil(SEAL).at(center(caster, a)).yaw(yaw(a)).duration(dur + 20));
                alive[i] = true;
            }
            int ward = Fx.play(sl, Fx.sigil("eight_shields").at(caster.position().add(0, 0.05, 0)).caster(caster).attach(caster).duration(dur));   // octagram under the wall
            sl.playSound(null, caster.getX(), caster.getY(), caster.getZ(), SoundEvents.ARMOR_EQUIP_NETHERITE, SoundSource.PLAYERS, 1.5f, 0.8f);
            sl.playSound(null, caster.getX(), caster.getY(), caster.getZ(), SoundEvents.BEACON_ACTIVATE, SoundSource.PLAYERS, 1.2f, 1.6f);
            Tasks.add(new Tasks.Task() {
                int age;

                @Override
                public boolean tick() {
                    age++;
                    boolean over = age > dur || !caster.isAlive() || caster.isRemoved() || pool.left <= 0 || PohEvents.pool(caster) != pool
                            || caster.level() != sl;
                    if (!over) block();
                    over = over || pool.left <= 0;
                    int keep = over ? 0 : (int) Math.ceil(8 * pool.left / max);
                    for (int i = 0; i < 8; i++) {
                        if (!alive[i]) continue;
                        Vec3 c = center(caster, angle(age, i));
                        if (i >= keep) {
                            alive[i] = false;
                            DivineEvents.particle(sl, ParticleTypes.ELECTRIC_SPARK, c.x, c.y, c.z, 30, 0.8, 0.15);
                            sl.playSound(null, c.x, c.y, c.z, SoundEvents.GLASS_BREAK, SoundSource.PLAYERS, 1f, 1.3f);
                            Fx.stop(sl, seals[i], "");
                            continue;
                        }
                        Fx.move(sl, seals[i], c, yaw(angle(age, i)));
                    }
                    if (over) {
                        Fx.stop(sl, ward, "");
                        PohEvents.removePool(caster, pool);
                        caster.removeEffect(Reg.EIGHT_SHIELDS.get());
                    }
                    return !over;
                }

                /** Stops enemy projectiles that would cross a live seal (from outside inwards) before their next move. */
                private void block() {
                    AABB box = caster.getBoundingBox().inflate(RAD + 6);
                    for (Projectile p : sl.getEntitiesOfClass(Projectile.class, box, Entity::isAlive)) {
                        Entity owner = p.getOwner();
                        if (owner == caster) continue;
                        Vec3 v = p.getDeltaMovement();
                        Vec3 from = new Vec3(p.xo, p.yo, p.zo);
                        Vec3 to = p.position().add(v);
                        Vec3 seg = to.subtract(from);
                        for (int i = 0; i < 8; i++) {
                            if (!alive[i]) continue;
                            double a = angle(age, i);
                            Vec3 c = center(caster, a);
                            Vec3 n = new Vec3(Math.cos(a), 0, Math.sin(a));   // outward normal of the seal
                            double vn = seg.dot(n);
                            if (vn >= 0) continue;                              // flying outwards or along the seal
                            double t = c.subtract(from).dot(n) / vn;
                            if (t < 0 || t > 1) continue;
                            Vec3 hit = from.add(seg.scale(t));
                            if (hit.distanceToSqr(c) > SEAL_R * SEAL_R) continue;
                            pool.left -= damageOf(p);
                            DivineEvents.particle(sl, ParticleTypes.ELECTRIC_SPARK, hit.x, hit.y, hit.z, 12, 0.25, 0.1);
                            DivineEvents.particle(sl, ParticleTypes.END_ROD, hit.x, hit.y, hit.z, 4, 0.15, 0.03);
                            sl.playSound(null, hit.x, hit.y, hit.z, SoundEvents.AMETHYST_BLOCK_HIT, SoundSource.PLAYERS, 1f, 1.2f);
                            p.discard();
                            break;
                        }
                    }
                }
            });
        }
        super.onCast(level, spellLevel, caster, source, md);
    }
}
