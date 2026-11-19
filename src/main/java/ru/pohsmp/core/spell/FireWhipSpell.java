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
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.DivineEvents;
import ru.pohsmp.core.fx.Fx;
import ru.pohsmp.core.spell.silent.SilentSpell;

/** Fire: a whip of flame lashes an arc in front of the caster; everyone in the arc burns, the nearest one is pulled in. */
public class FireWhipSpell extends PohSpell {
    public static final String PATH = "fire_whip";
    private static final double LEN = 6, HALF = Math.toRadians(65);

    public FireWhipSpell() {
        super(PATH, SchoolRegistry.FIRE_RESOURCE, SpellRarity.COMMON, 6, 5, 0, 20, 4);
    }

    @Override public CastType getCastType() { return CastType.INSTANT; }

    private double damage(int l, LivingEntity c) { return lv(l, 5, 14) * mult(c); }
    private int burn(int l) { return (int) lv(l, 2, 6); }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("damage", n(damage(level, caster)), n(LEN)), ui("burn", burn(level)));
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            Vec3 o = caster.position().add(0, caster.getBbHeight() * 0.6, 0);
            Vec3 f = caster.getLookAngle().multiply(1, 0, 1);
            if (f.lengthSqr() < 1e-4) f = new Vec3(0, 0, 1);
            f = f.normalize();
            double yaw = Math.atan2(f.z, f.x);
            float dmg = (float) damage(spellLevel, caster);
            int burn = burn(spellLevel);
            sl.playSound(null, o.x, o.y, o.z, SoundEvents.BLAZE_SHOOT, SoundSource.PLAYERS, 1.2f, 0.7f);
            sl.playSound(null, o.x, o.y, o.z, SoundEvents.FIRECHARGE_USE, SoundSource.PLAYERS, 1f, 1.4f);
            final Vec3 fo = o;
            // own model (owner, 19.11.2026): handle + burning lash, fx/meshes/fire_whip.json, turned along the swing
            int whip = Fx.play(sl, Fx.mesh("fire_whip").at(fo).yaw(SilentSpell.yawOf(dir(yaw, -HALF))).duration(20));
            Tasks.add(new Tasks.Task() {   // the lash sweeps from right to left over 5 ticks
                int age;

                @Override
                public boolean tick() {
                    double a0 = -HALF + 2 * HALF * age / 5.0, a1 = -HALF + 2 * HALF * (age + 1) / 5.0;
                    Fx.move(sl, whip, fo, SilentSpell.yawOf(dir(yaw, a1)));
                    for (double a = a0; a <= a1; a += 0.15)   // a few flames along the swept arc
                        for (double r = 1.5; r <= LEN; r += 1.5) {
                            double sag = Math.sin(r / LEN * Math.PI) * 0.6;
                            DivineEvents.particle(sl, r > LEN - 1 ? ParticleTypes.LAVA : ParticleTypes.FLAME,
                                    fo.x + Math.cos(yaw + a) * r, fo.y - sag, fo.z + Math.sin(yaw + a) * r, 1, 0.02, 0.01);
                        }
                    age++;
                    if (age >= 5) Fx.stop(sl, whip, "");
                    return age < 5;
                }
            });
            LivingEntity near = null;
            double best = 99;
            for (LivingEntity e : HigherSpell.around(sl, caster.position(), LEN + 1, e -> !HigherSpell.friendly(caster, e))) {
                Vec3 d = e.position().subtract(caster.position()).multiply(1, 0, 1);
                double dist = d.length();
                if (dist > LEN + e.getBbWidth() / 2 || Math.abs(e.getY() - caster.getY()) > 3) continue;
                if (dist > 0.5 && Math.acos(Math.max(-1, Math.min(1, d.normalize().dot(f)))) > HALF) continue;
                hit(caster, e, dmg);
                e.setSecondsOnFire(burn);
                if (dist < best) { best = dist; near = e; }
            }
            if (near != null && best > 2) {
                Vec3 pull = caster.position().subtract(near.position()).multiply(1, 0, 1).normalize().scale(Math.min(1.6, best * 0.28));
                HigherSpell.push(near, pull.add(0, 0.35, 0));
                sl.playSound(null, near.getX(), near.getY(), near.getZ(), SoundEvents.FISHING_BOBBER_RETRIEVE, SoundSource.PLAYERS, 1.5f, 0.6f);
            }
        }
        super.onCast(level, spellLevel, caster, source, md);
    }

    private static Vec3 dir(double yaw, double a) {
        return new Vec3(Math.cos(yaw + a), 0, Math.sin(yaw + a));
    }
}
