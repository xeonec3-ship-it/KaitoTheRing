package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.registry.SchoolRegistry;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.spells.SpellRarity;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.DivineEvents;
import ru.pohsmp.core.Reg;

/** Lightning: a shock wave runs along the ground from the caster; whoever it touches is hurt and paralysed. Jumping over it avoids it. */
public class GroundShockSpell extends PohSpell {
    public static final String PATH = "ground_shock";
    private static final double SPEED = 0.6;

    public GroundShockSpell() {
        super(PATH, SchoolRegistry.LIGHTNING_RESOURCE, SpellRarity.COMMON, 6, 15, 0, 35, 7);
    }

    @Override public CastType getCastType() { return CastType.INSTANT; }

    private double radius(int l) { return lv(l, 6, 12); }
    private double damage(int l, LivingEntity c) { return lv(l, 4, 10) * mult(c); }
    private int para(int l) { return (int) (lv(l, 1, 3) * 20); }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("damage", n(damage(level, caster)), n(radius(level))), ui("paralysis", n(para(level) / 20.0)));
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            Vec3 c = caster.position();
            double R = radius(spellLevel);
            float dmg = (float) damage(spellLevel, caster);
            int pt = para(spellLevel);
            sl.playSound(null, c.x, c.y, c.z, SoundEvents.LIGHTNING_BOLT_IMPACT, SoundSource.PLAYERS, 2f, 1.2f);
            Set<UUID> done = new HashSet<>();
            Tasks.add(new Tasks.Task() {
                double r = 0.5;

                @Override
                public boolean tick() {
                    r += SPEED;
                    int n = (int) (r * 5) + 6;
                    for (int i = 0; i < n; i++) {
                        double a = i * Math.PI * 2 / n + r;
                        DivineEvents.particle(sl, ParticleTypes.ELECTRIC_SPARK, c.x + Math.cos(a) * r, c.y + 0.15, c.z + Math.sin(a) * r, 1, 0.05, 0.05);
                    }
                    if ((int) (r / SPEED) % 4 == 0) sl.playSound(null, c.x, c.y, c.z, SoundEvents.BEEHIVE_WORK, SoundSource.PLAYERS, 1f, 2f);
                    for (LivingEntity e : HigherSpell.around(sl, c, r + 2, e -> !HigherSpell.friendly(caster, e))) {
                        if (done.contains(e.getUUID()) || Math.abs(hdist(e, c) - r) > 0.5 + e.getBbWidth() / 2) continue;
                        if (e.getY() > c.y + 0.9 || e.getY() < c.y - 2) continue;
                        done.add(e.getUUID());
                        hit(caster, e, dmg);
                        e.addEffect(new MobEffectInstance(Reg.PARALYSIS.get(), pt, 0, false, true, true));
                        DivineEvents.particle(sl, ParticleTypes.ELECTRIC_SPARK, e.getX(), e.getY() + 1, e.getZ(), 20, 0.4, 0.2);
                    }
                    return r < R;
                }
            });
        }
        super.onCast(level, spellLevel, caster, source, md);
    }
}
