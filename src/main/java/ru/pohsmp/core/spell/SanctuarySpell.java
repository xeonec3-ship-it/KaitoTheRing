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
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import org.joml.Vector3f;
import ru.pohsmp.core.DivineEvents;

/** Holy: a dome of light around the cast point; allies inside heal every second, enemies are pushed out of it. */
public class SanctuarySpell extends PohSpell {
    public static final String PATH = "sanctuary";
    private static final DustParticleOptions GOLD = new DustParticleOptions(new Vector3f(1f, 0.9f, 0.5f), 1.4f);

    public SanctuarySpell() {
        super(PATH, SchoolRegistry.HOLY_RESOURCE, SpellRarity.UNCOMMON, 6, 30, 0, 50, 8);
    }

    @Override public CastType getCastType() { return CastType.INSTANT; }

    private double radius(int l) { return lv(l, 4, 7); }
    private double heal(int l, LivingEntity c) { return lv(l, 1, 3) * mult(c); }
    private int seconds(int l) { return (int) Math.round(lv(l, 5, 10)); }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("heal", n(heal(level, caster)), n(radius(level))), ui("time", seconds(level)));
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            Vec3 c = caster.position();
            double R = radius(spellLevel);
            float heal = (float) heal(spellLevel, caster);
            int ticks = seconds(spellLevel) * 20;
            sl.playSound(null, c.x, c.y, c.z, SoundEvents.BEACON_ACTIVATE, SoundSource.PLAYERS, 1.5f, 1.4f);
            Tasks.add(new Tasks.Task() {
                int age;

                @Override
                public boolean tick() {
                    age++;
                    if (age % 3 == 0) {   // dome outline
                        for (int i = 0; i < 18; i++) {
                            double th = sl.random.nextDouble() * Math.PI * 2, ph = sl.random.nextDouble() * Math.PI / 2;
                            DivineEvents.particle(sl, GOLD, c.x + Math.cos(th) * Math.cos(ph) * R, c.y + Math.sin(ph) * R, c.z + Math.sin(th) * Math.cos(ph) * R, 1, 0, 0);
                        }
                        for (int i = 0; i < 24; i++) {
                            double a = i * Math.PI / 12 + age * 0.02;
                            DivineEvents.particle(sl, ParticleTypes.END_ROD, c.x + Math.cos(a) * R, c.y + 0.1, c.z + Math.sin(a) * R, 1, 0, 0);
                        }
                    }
                    for (LivingEntity e : HigherSpell.around(sl, c, R + 0.5, e -> true)) {
                        if (HigherSpell.foe(caster, e)) {
                            Vec3 away = e.position().subtract(c).multiply(1, 0, 1);
                            if (away.lengthSqr() < 1e-4) away = new Vec3(1, 0, 0);
                            HigherSpell.push(e, away.normalize().scale(0.55).add(0, 0.15, 0));
                            if (age % 10 == 0) DivineEvents.particle(sl, ParticleTypes.END_ROD, e.getX(), e.getY() + 1, e.getZ(), 4, 0.3, 0.02);
                        } else if (age % 20 == 0 && e.getHealth() < e.getMaxHealth()) {
                            e.heal(heal);
                            DivineEvents.particle(sl, ParticleTypes.HEART, e.getX(), e.getY() + e.getBbHeight() + 0.3, e.getZ(), 1, 0.2, 0);
                        }
                    }
                    if (age >= ticks) {
                        sl.playSound(null, c.x, c.y, c.z, SoundEvents.BEACON_DEACTIVATE, SoundSource.PLAYERS, 1.2f, 1.4f);
                        return false;
                    }
                    return true;
                }
            });
        }
        super.onCast(level, spellLevel, caster, source, md);
    }
}
