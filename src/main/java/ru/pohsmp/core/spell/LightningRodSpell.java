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
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.DivineEvents;

/** Lightning: a glowing rod rises where the caster looks and strikes every enemy closer than 5 blocks once a second. */
public class LightningRodSpell extends PohSpell {
    public static final String PATH = "lightning_rod";
    private static final double R = 5;

    public LightningRodSpell() {
        super(PATH, SchoolRegistry.LIGHTNING_RESOURCE, SpellRarity.COMMON, 6, 18, 0, 40, 6);
    }

    @Override public CastType getCastType() { return CastType.INSTANT; }

    private double damage(int l, LivingEntity c) { return lv(l, 3, 8) * mult(c); }
    private int pulses(int l) { return (int) Math.round(lv(l, 4, 9)); }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("damage", n(damage(level, caster)), n(R)), ui("pulses", pulses(level)));
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            Vec3 c = ground(sl, caster, lookPoint(sl, caster, 16));
            float dmg = (float) damage(spellLevel, caster);
            int pulses = pulses(spellLevel);
            Entity rod = Disp.block(sl, "minecraft:lightning_rod", c.x, c.y, c.z, 1.2f, 2.4f, 1.2f, 0);
            Entity glow = Disp.block(sl, "minecraft:sea_lantern", c.x, c.y + 2.5, c.z, 0.5f, 0.5f, 0.5f, 45);
            sl.playSound(null, c.x, c.y, c.z, SoundEvents.TRIDENT_THUNDER, SoundSource.PLAYERS, 1.5f, 1.6f);
            Tasks.add(new Tasks.Task() {
                int age;

                @Override
                public boolean tick() {
                    age++;
                    Disp.move(glow, c.x, c.y + 2.5 + Math.sin(age * 0.2) * 0.1, c.z, age * 8f);
                    if (age % 4 == 0) {
                        DivineEvents.particle(sl, ParticleTypes.ELECTRIC_SPARK, c.x, c.y + 2.7, c.z, 3, 0.25, 0.05);
                        for (int i = 0; i < 16; i++) {
                            double a = i * Math.PI / 8 + age * 0.03;
                            DivineEvents.particle(sl, ParticleTypes.ELECTRIC_SPARK, c.x + Math.cos(a) * R, c.y + 0.1, c.z + Math.sin(a) * R, 1, 0, 0);
                        }
                    }
                    if (age % 20 == 0) {
                        boolean any = false;
                        for (LivingEntity e : HigherSpell.around(sl, c, R, e -> !HigherSpell.friendly(caster, e))) {
                            any = true;
                            Vec3 a = new Vec3(c.x, c.y + 2.6, c.z), b = e.position().add(0, e.getBbHeight() * 0.6, 0);
                            int steps = (int) (a.distanceTo(b) * 4);
                            Vec3 prev = a;
                            for (int i = 1; i <= steps; i++) {   // jagged bolt
                                Vec3 p = a.lerp(b, i / (double) steps);
                                if (i < steps) p = p.add((sl.random.nextDouble() - 0.5) * 0.4, (sl.random.nextDouble() - 0.5) * 0.4, (sl.random.nextDouble() - 0.5) * 0.4);
                                DivineEvents.particle(sl, ParticleTypes.ELECTRIC_SPARK, p.x, p.y, p.z, 2, 0.02, 0);
                                prev = p;
                            }
                            DivineEvents.particle(sl, ParticleTypes.FLASH, b.x, b.y, b.z, 1, 0, 0);
                            hit(caster, e, dmg);
                        }
                        if (any) sl.playSound(null, c.x, c.y, c.z, SoundEvents.LIGHTNING_BOLT_IMPACT, SoundSource.PLAYERS, 1.6f, 1.5f);
                    }
                    if (age >= pulses * 20 + 5) {
                        Disp.kill(rod);
                        Disp.kill(glow);
                        DivineEvents.particle(sl, ParticleTypes.ELECTRIC_SPARK, c.x, c.y + 1.5, c.z, 30, 0.4, 0.2);
                        return false;
                    }
                    return true;
                }
            });
        }
        super.onCast(level, spellLevel, caster, source, md);
    }
}
