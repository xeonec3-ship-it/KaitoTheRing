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
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.Level;
import org.joml.Vector3f;
import ru.pohsmp.core.DivineEvents;
import ru.pohsmp.core.Reg;

/** Holy: for a while every other player near the caster is shielded; the damage they would take (after their armor) goes to the caster. */
public class LivingShieldSpell extends PohSpell {
    public static final String PATH = "living_shield";
    private static final DustParticleOptions GOLD = new DustParticleOptions(new Vector3f(1f, 0.9f, 0.45f), 1.1f);

    public LivingShieldSpell() {
        super(PATH, SchoolRegistry.HOLY_RESOURCE, SpellRarity.UNCOMMON, 6, 40, 0, 40, 8);
    }

    @Override public CastType getCastType() { return CastType.INSTANT; }

    private double radius(int l) { return lv(l, 4, 10); }
    private int ticks(int l) { return (int) (lv(l, 6, 16) * 20); }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("radius", n(radius(level))), ui("time", n(ticks(level) / 20.0)), ui("cost"));
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            double r = radius(spellLevel);
            int dur = ticks(spellLevel);
            PohEvents.addShield(caster, r, dur);
            caster.addEffect(new MobEffectInstance(Reg.LIVING_SHIELD.get(), dur, 0, false, false, true));
            sl.playSound(null, caster.getX(), caster.getY(), caster.getZ(), SoundEvents.BEACON_POWER_SELECT, SoundSource.PLAYERS, 1.5f, 1.3f);
            Tasks.add(new Tasks.Task() {
                int age;

                @Override
                public boolean tick() {
                    age++;
                    if (!caster.isAlive() || caster.isRemoved() || age > dur || !PohEvents.hasShield(caster)) return false;
                    if (age % 4 == 0) {
                        int n = (int) (r * 4);
                        for (int i = 0; i < n; i++) {
                            double a = i * Math.PI * 2 / n + age * 0.03;
                            DivineEvents.particle(sl, GOLD, caster.getX() + Math.cos(a) * r, caster.getY() + 0.15, caster.getZ() + Math.sin(a) * r, 1, 0, 0);
                        }
                    }
                    if (age % 10 == 0) {
                        for (LivingEntity p : PohEvents.shieldedBy(caster))
                            DivineEvents.particle(sl, ParticleTypes.END_ROD, p.getX(), p.getY() + p.getBbHeight() + 0.3, p.getZ(), 1, 0.2, 0.01);
                    }
                    return true;
                }
            });
        }
        super.onCast(level, spellLevel, caster, source, md);
    }
}
