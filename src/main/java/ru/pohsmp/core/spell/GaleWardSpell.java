package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.spells.SpellRarity;
import java.util.List;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.projectile.Projectile;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.DivineEvents;

/** Wind: a whirl around the caster pushes away creatures and projectiles that come close. */
public class GaleWardSpell extends PohSpell {
    public static final String PATH = "gale_ward";
    public static final ResourceLocation WIND = new ResourceLocation("wind_spellbooks", "wind");
    private static final double R = 3.5;

    public GaleWardSpell() {
        super(PATH, WIND, SpellRarity.COMMON, 6, 25, 0, 35, 7);
    }

    @Override public CastType getCastType() { return CastType.INSTANT; }

    private int ticks(int l) { return (int) (lv(l, 4, 12) * 20); }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("time", n(ticks(level) / 20.0)), ui("radius", n(R)));
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            int dur = ticks(spellLevel);
            sl.playSound(null, caster.getX(), caster.getY(), caster.getZ(), SoundEvents.ELYTRA_FLYING, SoundSource.PLAYERS, 0.6f, 1.5f);
            Tasks.add(new Tasks.Task() {
                int age;

                @Override
                public boolean tick() {
                    age++;
                    if (age > dur || !caster.isAlive() || caster.isRemoved()) return false;
                    Vec3 c = caster.position().add(0, caster.getBbHeight() / 2, 0);
                    for (int i = 0; i < 3; i++) {
                        double a = age * 0.45 + i * Math.PI * 2 / 3;
                        double y = caster.getY() + ((age * 0.08 + i * 0.6) % 2.2);
                        DivineEvents.particle(sl, ParticleTypes.CLOUD, caster.getX() + Math.cos(a) * R * 0.8, y, caster.getZ() + Math.sin(a) * R * 0.8, 1, 0, 0);
                    }
                    if (age % 30 == 0) sl.playSound(null, c.x, c.y, c.z, SoundEvents.PHANTOM_FLAP, SoundSource.PLAYERS, 0.6f, 1.6f);
                    for (Entity e : sl.getEntities(caster, new AABB(c, c).inflate(R))) {
                        if (e.position().distanceToSqr(caster.position()) > R * R) continue;
                        Vec3 away = e.position().subtract(caster.position());
                        if (away.lengthSqr() < 1e-4) continue;
                        if (e instanceof Projectile pr) {
                            if (pr.getOwner() == caster) continue;
                            Vec3 v = pr.getDeltaMovement();
                            Vec3 n = away.normalize();
                            double dot = v.dot(n);
                            if (dot < 0) HigherSpell.push(pr, v.subtract(n.scale(2 * dot)).scale(0.8));
                        } else if (e instanceof LivingEntity le && !HigherSpell.friendly(caster, le)) {
                            HigherSpell.push(le, away.multiply(1, 0, 1).normalize().scale(0.55).add(0, 0.2, 0));
                        }
                    }
                    return true;
                }
            });
        }
        super.onCast(level, spellLevel, caster, source, md);
    }
}
