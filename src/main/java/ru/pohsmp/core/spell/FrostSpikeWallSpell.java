package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.registry.SchoolRegistry;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.spells.SpellRarity;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.DivineEvents;

/**
 * Ice: a wall of ice spikes across the caster's view, 3 blocks ahead (sneaking: a ring around the caster).
 * Touching it hurts, slows and pushes back.
 */
public class FrostSpikeWallSpell extends PohSpell {
    public static final String PATH = "frost_spike_wall";
    private static final double HEIGHT = 2.2;

    public FrostSpikeWallSpell() {
        super(PATH, SchoolRegistry.ICE_RESOURCE, SpellRarity.COMMON, 6, 20, 0, 35, 6);
    }

    @Override public CastType getCastType() { return CastType.INSTANT; }

    private int length(int l) { return (int) Math.round(lv(l, 5, 10)); }
    private int ticks(int l) { return (int) (lv(l, 8, 20) * 20); }
    private double damage(int l, LivingEntity c) { return lv(l, 3, 6) * mult(c); }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("length", length(level)), ui("time", n(ticks(level) / 20.0)), ui("damage", n(damage(level, caster))), ui("ring"));
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) build(sl, caster, length(spellLevel), ticks(spellLevel), (float) damage(spellLevel, caster));
        super.onCast(level, spellLevel, caster, source, md);
    }

    private void build(ServerLevel sl, LivingEntity caster, int len, int dur, float dmg) {
        List<Vec3> pts = new ArrayList<>();
        if (caster.isShiftKeyDown()) {
            double r = Math.max(2.5, len / Math.PI);
            int n = (int) Math.ceil(2 * Math.PI * r / 0.9);
            for (int i = 0; i < n; i++) {
                double a = i * Math.PI * 2 / n;
                pts.add(ground(sl, caster, caster.position().add(Math.cos(a) * r, 1, Math.sin(a) * r)));
            }
        } else {
            Vec3 f = caster.getLookAngle().multiply(1, 0, 1);
            f = f.lengthSqr() < 1e-4 ? new Vec3(0, 0, 1) : f.normalize();
            Vec3 side = new Vec3(-f.z, 0, f.x);
            Vec3 c = caster.position().add(f.scale(3));
            int n = (int) Math.ceil(len / 0.9);
            for (int i = 0; i < n; i++) {
                double o = -len / 2.0 + (i + 0.5) * len / (double) n;
                pts.add(ground(sl, caster, c.add(side.scale(o)).add(0, 1, 0)));
            }
        }
        List<Entity> spikes = new ArrayList<>();
        for (int i = 0; i < pts.size(); i++) {
            Vec3 p = pts.get(i);
            float h = (float) (HEIGHT * (0.75 + 0.25 * ((i * 7) % 4) / 3.0));
            spikes.add(Disp.block(sl, i % 3 == 0 ? "minecraft:blue_ice" : "minecraft:packed_ice", p.x, p.y - h, p.z, 0.55f, h, 0.55f, i * 37 % 90));
        }
        sl.playSound(null, caster.getX(), caster.getY(), caster.getZ(), SoundEvents.GLASS_PLACE, SoundSource.PLAYERS, 2f, 0.5f);
        sl.playSound(null, caster.getX(), caster.getY(), caster.getZ(), SoundEvents.AMETHYST_BLOCK_BREAK, SoundSource.PLAYERS, 2f, 0.6f);
        Map<UUID, Integer> cd = new HashMap<>();
        Tasks.add(new Tasks.Task() {
            int age;

            @Override
            public boolean tick() {
                age++;
                if (age <= 6) {   // spikes grow out of the ground
                    for (int i = 0; i < spikes.size(); i++) {
                        Vec3 p = pts.get(i);
                        Entity s = spikes.get(i);
                        Disp.move(s, p.x, p.y - HEIGHT * (1 - age / 6.0) + 0.0, p.z, s == null ? 0 : s.getYRot());
                    }
                }
                if (age > dur) {
                    for (int i = 0; i < spikes.size(); i++) {
                        Vec3 p = pts.get(i);
                        DivineEvents.particle(sl, ParticleTypes.SNOWFLAKE, p.x, p.y + 1, p.z, 4, 0.2, 0.02);
                        Disp.kill(spikes.get(i));
                    }
                    sl.playSound(null, pts.get(0).x, pts.get(0).y, pts.get(0).z, SoundEvents.GLASS_BREAK, SoundSource.PLAYERS, 1.5f, 0.8f);
                    return false;
                }
                if (age % 2 != 0) return true;
                cd.replaceAll((k, v) -> v - 2);
                for (Vec3 p : pts) {
                    for (LivingEntity e : HigherSpell.around(sl, p.add(0, 1, 0), 1.6, e -> !HigherSpell.friendly(caster, e))) {
                        if (hdist(e, p) > 0.45 + e.getBbWidth() / 2 || e.getY() > p.y + HEIGHT || e.getY() + e.getBbHeight() < p.y) continue;
                        if (cd.getOrDefault(e.getUUID(), 0) > 0) continue;
                        cd.put(e.getUUID(), 12);
                        hit(caster, e, dmg);
                        e.addEffect(new MobEffectInstance(MobEffects.MOVEMENT_SLOWDOWN, 40, 2));
                        Vec3 away = new Vec3(e.getX() - p.x, 0, e.getZ() - p.z);
                        if (away.lengthSqr() < 1e-4) away = new Vec3(e.getX() - caster.getX(), 0, e.getZ() - caster.getZ());
                        if (away.lengthSqr() > 1e-4) HigherSpell.push(e, away.normalize().scale(0.6).add(0, 0.25, 0));
                        DivineEvents.particle(sl, ParticleTypes.SNOWFLAKE, e.getX(), e.getY() + 1, e.getZ(), 8, 0.3, 0.05);
                    }
                }
                return true;
            }
        });
    }
}
