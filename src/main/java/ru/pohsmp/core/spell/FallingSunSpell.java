package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.registry.SchoolRegistry;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.spells.SpellRarity;
import java.util.List;
import net.minecraft.core.particles.DustParticleOptions;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import org.joml.Vector3f;
import ru.pohsmp.core.DivineEvents;

/** Fire: a small sun falls where the caster looks. 1.5 s warning circle, then damage and burning in an area. Blocks stay intact. */
public class FallingSunSpell extends PohSpell {
    public static final String PATH = "falling_sun";
    private static final int WARN = 30;
    private static final DustParticleOptions ORANGE = new DustParticleOptions(new Vector3f(1f, 0.45f, 0.05f), 1.4f);

    public FallingSunSpell() {
        super(PATH, SchoolRegistry.FIRE_RESOURCE, SpellRarity.COMMON, 6, 14, 0, 40, 8);
    }

    @Override public CastType getCastType() { return CastType.INSTANT; }

    private double damage(int l, LivingEntity c) { return lv(l, 12, 30) * mult(c); }
    private double radius(int l) { return lv(l, 3, 6); }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("damage", n(damage(level, caster)), n(radius(level))), ui("delay", n(WARN / 20.0)));
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            Vec3 c = ground(sl, caster, lookPoint(sl, caster, 32));
            fall(sl, caster, c, (float) damage(spellLevel, caster), radius(spellLevel));
        }
        super.onCast(level, spellLevel, caster, source, md);
    }

    private void fall(ServerLevel sl, LivingEntity caster, Vec3 c, float dmg, double r) {
        double top = 18;
        Entity sun = Disp.block(sl, "minecraft:shroomlight", c.x, c.y + top, c.z, 1.6f, 1.6f, 1.6f, 0);
        Entity shell = Disp.block(sl, "minecraft:magma_block", c.x, c.y + top - 0.1, c.z, 1.9f, 1.9f, 1.9f, 45);
        sl.playSound(null, c.x, c.y + top, c.z, SoundEvents.BLAZE_SHOOT, SoundSource.PLAYERS, 3f, 0.5f);
        Tasks.add(new Tasks.Task() {
            int age;

            @Override
            public boolean tick() {
                age++;
                double k = Math.min(1, age / (double) WARN);
                double y = c.y + top * (1 - k * k);
                Disp.move(sun, c.x, y, c.z, age * 9f);
                Disp.move(shell, c.x, y - 0.15, c.z, 45 - age * 6f);
                DivineEvents.particle(sl, ParticleTypes.FLAME, c.x, y + 0.8, c.z, 6, 0.4, 0.02);
                DivineEvents.particle(sl, ParticleTypes.LARGE_SMOKE, c.x, y + 1.6, c.z, 2, 0.3, 0.01);
                if (age % 3 == 0) {
                    int n = (int) (r * 6);
                    for (int i = 0; i < n; i++) {
                        double a = i * Math.PI * 2 / n + age * 0.05;
                        DivineEvents.particle(sl, ORANGE, c.x + Math.cos(a) * r, c.y + 0.1, c.z + Math.sin(a) * r, 1, 0, 0);
                    }
                    DivineEvents.particle(sl, ORANGE, c.x, c.y + 0.1, c.z, 3, r * k * 0.5, 0);
                }
                if (age < WARN) return true;
                Disp.kill(sun);
                Disp.kill(shell);
                DivineEvents.particle(sl, ParticleTypes.EXPLOSION_EMITTER, c.x, c.y + 0.5, c.z, 1, 0, 0);
                DivineEvents.particle(sl, ParticleTypes.FLAME, c.x, c.y + 0.5, c.z, 120, r * 0.4, 0.15);
                DivineEvents.particle(sl, ParticleTypes.LAVA, c.x, c.y + 0.5, c.z, 30, r * 0.3, 0.1);
                sl.playSound(null, c.x, c.y, c.z, SoundEvents.GENERIC_EXPLODE, SoundSource.PLAYERS, 3f, 0.8f);
                for (LivingEntity e : HigherSpell.around(sl, c, r + 1.5, e -> !HigherSpell.friendly(caster, e))) {
                    double d = e.position().distanceTo(c);
                    if (d > r + e.getBbWidth() / 2) continue;
                    hit(caster, e, (float) (dmg * (1 - 0.4 * Math.min(1, d / r))));
                    e.setSecondsOnFire(4);
                    Vec3 away = e.position().subtract(c).multiply(1, 0, 1);
                    if (away.lengthSqr() > 1e-4) HigherSpell.push(e, away.normalize().scale(0.6).add(0, 0.4, 0));
                }
                return false;
            }
        });
    }
}
