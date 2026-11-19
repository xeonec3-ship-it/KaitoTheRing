package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import java.util.List;
import java.util.Optional;
import net.minecraft.core.particles.DustParticleOptions;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import org.joml.Vector3f;
import ru.pohsmp.core.DivineEvents;
import ru.pohsmp.core.fx.Fx;
import ru.pohsmp.core.spell.silent.SilentSpell;

/** Higher: six dark blades circle the caster for 12 s; every half second one flies at the nearest enemy and comes back. */
public class OblivionBladesSpell extends HigherSpell {
    public static final String PATH = "oblivion_blades";
    private static final int LIFE = 240, N = 6;
    private static final double R = 12, DMG = 7, SPEED = 1.3, ORBIT = 1.6;
    private static final DustParticleOptions DARK = new DustParticleOptions(new Vector3f(0.3f, 0.05f, 0.4f), 1f);

    public OblivionBladesSpell() {
        super(PATH, 0);
    }

    @Override public CastType getCastType() { return CastType.INSTANT; }
    @Override public Optional<SoundEvent> getCastStartSound() { return Optional.empty(); }
    @Override public Optional<SoundEvent> getCastFinishSound() { return Optional.of(SoundEvents.ENCHANTMENT_TABLE_USE); }

    @Override
    public List<MutableComponent> getUniqueInfo(int spellLevel, LivingEntity caster) {
        return List.of(ui("blades", N, LIFE / 20), ui("damage", num(DMG), (int) R));
    }

    private static final class Blade {
        int fx = -1;       // own model: fx/oblivion_blade.json (mesh oblivion_blade + dark trail)
        int mode;          // 0 orbit, 1 out, 2 back
        LivingEntity t;
        Vec3 pos;
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            Blade[] bl = new Blade[N];
            for (int i = 0; i < N; i++) {
                bl[i] = new Blade();
                bl[i].pos = orbit(caster, i, 0);
                Vec3 tan = orbit(caster, i, 1).subtract(bl[i].pos);
                bl[i].fx = Fx.play(sl, Fx.fx("oblivion_blade").at(bl[i].pos).yaw(SilentSpell.yawOf(tan)).pitch(SilentSpell.pitchOf(tan)));
            }
            Tasks.add(new Tasks.Task() {
                int age, next;

                @Override
                public boolean tick() {
                    age++;
                    if (!caster.isAlive() || caster.isRemoved() || age > LIFE) {
                        for (Blade b : bl) {
                            DivineEvents.particle(sl, ParticleTypes.REVERSE_PORTAL, b.pos.x, b.pos.y, b.pos.z, 10, 0.2, 0.05);
                            Fx.stop(sl, b.fx, "");
                        }
                        return false;
                    }
                    if (age % 10 == 0) {   // launch the next resting blade
                        for (int k = 0; k < N; k++) {
                            Blade b = bl[(next + k) % N];
                            if (b.mode != 0) continue;
                            LivingEntity t = nearestFoe(sl, caster);
                            if (t != null) {
                                b.mode = 1;
                                b.t = t;
                                next = (next + k + 1) % N;
                                sl.playSound(null, b.pos.x, b.pos.y, b.pos.z, SoundEvents.PLAYER_ATTACK_SWEEP, SoundSource.PLAYERS, 1f, 0.6f);
                            }
                            break;
                        }
                    }
                    for (int i = 0; i < N; i++) {
                        Blade b = bl[i];
                        Vec3 home = orbit(caster, i, age);
                        Vec3 was = b.pos;
                        if (b.mode == 0) {
                            b.pos = home;
                        } else if (b.mode == 1) {
                            if (b.t == null || !b.t.isAlive()) { b.mode = 2; continue; }   // turns back next tick
                            Vec3 aim = b.t.position().add(0, b.t.getBbHeight() * 0.55, 0);
                            Vec3 d = aim.subtract(b.pos);
                            if (d.length() < SPEED + 0.4) {
                                hurt(sl, caster, b.t, dmg(DMG));
                                DivineEvents.particle(sl, ParticleTypes.SWEEP_ATTACK, aim.x, aim.y, aim.z, 1, 0, 0);
                                DivineEvents.particle(sl, DARK, aim.x, aim.y, aim.z, 12, 0.3, 0);
                                sl.playSound(null, aim.x, aim.y, aim.z, SoundEvents.PLAYER_ATTACK_STRONG, SoundSource.PLAYERS, 1f, 0.7f);
                                b.mode = 2;
                            } else {
                                b.pos = b.pos.add(d.normalize().scale(SPEED));
                            }
                        } else {
                            Vec3 d = home.subtract(b.pos);
                            if (d.length() < SPEED + 0.2) { b.mode = 0; b.pos = home; }
                            else b.pos = b.pos.add(d.normalize().scale(SPEED));
                        }
                        Vec3 d = b.pos.subtract(was);   // point the blade along its motion
                        if (d.lengthSqr() < 1e-6) d = orbit(caster, i, age + 1).subtract(b.pos);
                        Fx.move(sl, b.fx, b.pos, SilentSpell.yawOf(d), SilentSpell.pitchOf(d));
                    }
                    return true;
                }
            });
        }
        super.onCast(level, spellLevel, caster, source, md);
    }

    private static Vec3 orbit(LivingEntity c, int i, int age) {
        double a = i * Math.PI * 2 / N + age * 0.08;
        return new Vec3(c.getX() + Math.cos(a) * ORBIT, c.getY() + 1.1 + Math.sin(age * 0.1 + i) * 0.15, c.getZ() + Math.sin(a) * ORBIT);
    }

    private static LivingEntity nearestFoe(ServerLevel sl, LivingEntity caster) {
        LivingEntity best = null;
        double bd = R * R;
        for (LivingEntity e : around(sl, caster.position(), R, e -> foe(caster, e))) {
            double d = e.distanceToSqr(caster);
            if (d < bd && caster.hasLineOfSight(e)) { bd = d; best = e; }
        }
        return best;
    }
}
