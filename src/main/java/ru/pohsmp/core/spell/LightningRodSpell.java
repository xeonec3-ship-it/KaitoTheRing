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
            // own model (owner, 19.11.2026): copper mast with a coil and a floating crystal, the zone circle — fx/lightning_rod.json
            int fx = ru.pohsmp.core.fx.Fx.play(sl, ru.pohsmp.core.fx.Fx.fx("lightning_rod").at(c).yaw(0));
            Vec3 top = c.add(0, 2.95, 0);
            sl.playSound(null, c.x, c.y, c.z, SoundEvents.TRIDENT_THUNDER, SoundSource.PLAYERS, 1.5f, 1.6f);
            Tasks.add(new Tasks.Task() {
                int age;

                @Override
                public boolean tick() {
                    age++;
                    if (age % 20 == 0) {
                        boolean any = false;
                        for (LivingEntity e : HigherSpell.around(sl, c, R, e -> !HigherSpell.friendly(caster, e))) {
                            any = true;
                            Vec3 b = e.position().add(0, e.getBbHeight() * 0.6, 0);
                            ru.pohsmp.core.fx.Fx.play(sl, ru.pohsmp.core.fx.Fx.fx("lightning_rod_zap").at(top).target(b).seed(sl.random.nextLong()));
                            hit(caster, e, dmg);
                        }
                        if (any) sl.playSound(null, c.x, c.y, c.z, SoundEvents.LIGHTNING_BOLT_IMPACT, SoundSource.PLAYERS, 1.6f, 1.5f);
                    }
                    if (age >= pulses * 20 + 5) {
                        ru.pohsmp.core.fx.Fx.stop(sl, fx, "");
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
