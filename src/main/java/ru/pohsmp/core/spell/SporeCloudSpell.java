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
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.DivineEvents;

/** Nature: a cloud of spores where the caster looks; it slows, sickens and hurts, and the infected pass the spores on to their neighbours. */
public class SporeCloudSpell extends PohSpell {
    public static final String PATH = "spore_cloud";
    private static final double R = 3.2;

    public SporeCloudSpell() {
        super(PATH, SchoolRegistry.NATURE_RESOURCE, SpellRarity.COMMON, 6, 16, 0, 35, 6);
    }

    @Override public CastType getCastType() { return CastType.INSTANT; }

    private double dps(int l, LivingEntity c) { return lv(l, 1, 3) * mult(c); }
    private int seconds(int l) { return (int) Math.round(lv(l, 6, 10)); }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("damage", n(dps(level, caster)), n(R)), ui("time", seconds(level)), ui("spread"));
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            Vec3 c = ground(sl, caster, lookPoint(sl, caster, 16));
            double dps = dps(spellLevel, caster);
            int ticks = seconds(spellLevel) * 20;
            PohSpell me = this;
            sl.playSound(null, c.x, c.y, c.z, SoundEvents.AZALEA_LEAVES_BREAK, SoundSource.PLAYERS, 2f, 0.5f);
            sl.playSound(null, c.x, c.y, c.z, SoundEvents.PUFFER_FISH_BLOW_OUT, SoundSource.PLAYERS, 1.5f, 0.6f);
            Tasks.add(new Tasks.Task() {
                int age;

                @Override
                public boolean tick() {
                    age++;
                    if (age % 2 == 0) {
                        for (int i = 0; i < 6; i++) {
                            double a = sl.random.nextDouble() * Math.PI * 2, r = Math.sqrt(sl.random.nextDouble()) * R;
                            DivineEvents.particle(sl, Marks.SPORE, c.x + Math.cos(a) * r, c.y + 0.2 + sl.random.nextDouble() * 1.8, c.z + Math.sin(a) * r, 1, 0.05, 0);
                        }
                        DivineEvents.particle(sl, ParticleTypes.SPORE_BLOSSOM_AIR, c.x, c.y + 1, c.z, 2, R * 0.5, 0);
                    }
                    if (age % 20 == 0)
                        for (LivingEntity e : HigherSpell.around(sl, c.add(0, 1, 0), R + 0.5, e -> !HigherSpell.friendly(caster, e))) {
                            if (hdist(e, c) > R + e.getBbWidth() / 2) continue;
                            hit(caster, e, (float) dps);
                            e.addEffect(new MobEffectInstance(MobEffects.MOVEMENT_SLOWDOWN, 40, 1, false, true, true));
                            Marks.infect(me, caster, e, 100, dps * 0.5, 0);
                        }
                    if (age % 40 == 0) sl.playSound(null, c.x, c.y, c.z, SoundEvents.MOSS_STEP, SoundSource.PLAYERS, 1f, 0.5f);
                    return age < ticks;
                }
            });
        }
        super.onCast(level, spellLevel, caster, source, md);
    }
}
