package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.registry.SchoolRegistry;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.spells.SpellAnimations;
import io.redspace.ironsspellbooks.api.spells.SpellRarity;
import io.redspace.ironsspellbooks.api.util.AnimationHolder;
import io.redspace.ironsspellbooks.api.util.CameraShakeData;
import io.redspace.ironsspellbooks.api.util.CameraShakeManager;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import net.minecraft.core.particles.DustParticleOptions;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import org.joml.Vector3f;
import ru.pohsmp.core.DivineEvents;
import ru.pohsmp.core.fx.Fx;

/**
 * Mythic, level 1. "Heaven's Fall": a 10 s cast under a darkening sky, then for 20 s meteors rain within 20 blocks of the cast point.
 * Each one is marked by a burning circle a second before it lands. No blocks are broken.
 */
public class HeavenFallSpell extends PohSpell {
    public static final String PATH = "heaven_fall";
    public static final int CAST = 200, RAIN = 400;
    private static final double R = 20, HIT_R = 3, DMG = 14;
    private static final int COLOR = 0xB0301A, WARN = 20, FALL = 10;
    private static final DustParticleOptions ORANGE = new DustParticleOptions(new Vector3f(1f, 0.45f, 0.1f), 1.5f);

    private static final class Cast {
        Vec3 at;
        int age, fx = -1;
    }

    private static final Map<UUID, Cast> CASTS = new HashMap<>();

    public HeavenFallSpell() {
        super(PATH, SchoolRegistry.FIRE_RESOURCE, SpellRarity.LEGENDARY, 1, 0, CAST, 0, 0);
    }

    @Override public CastType getCastType() { return CastType.LONG; }
    @Override public boolean canBeInterrupted(Player player) { return false; }
    @Override public boolean allowCrafting() { return false; }
    @Override public Optional<SoundEvent> getCastStartSound() { return Optional.of(SoundEvents.WITHER_AMBIENT); }
    @Override public Optional<SoundEvent> getCastFinishSound() { return Optional.empty(); }
    @Override public AnimationHolder getCastStartAnimation() { return SpellAnimations.ANIMATION_LONG_CAST; }
    @Override public AnimationHolder getCastFinishAnimation() { return SpellAnimations.ANIMATION_LONG_CAST_FINISH; }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("time", CAST / 20, RAIN / 20), ui("damage", n(DMG), (int) R));
    }

    @Override
    public void onServerPreCast(Level level, int spellLevel, LivingEntity entity, MagicData md) {
        super.onServerPreCast(level, spellLevel, entity, md);
        if (level instanceof ServerLevel) {
            Cast c = new Cast();
            c.at = entity.position();
            CASTS.put(entity.getUUID(), c);
        }
    }

    @Override
    public void onServerCastTick(Level level, int spellLevel, LivingEntity caster, MagicData md) {
        super.onServerCastTick(level, spellLevel, caster, md);
        if (!(level instanceof ServerLevel sl)) return;
        Cast c = CASTS.get(caster.getUUID());
        if (c == null) {
            onServerPreCast(level, spellLevel, caster, md);
            c = CASTS.get(caster.getUUID());
        }
        c.age++;
        if (c.age == 1) c.fx = Fx.play(sl, Fx.fx("heaven_fall").at(c.at).yaw(caster.getYRot()));   // the sky closes in four rings of fire
        if (c.age % 50 == 1 && c.age <= 151) {
            sl.playSound(null, c.at.x, c.at.y, c.at.z, SoundEvents.AMBIENT_CAVE.value(), SoundSource.PLAYERS, 4f, 0.5f);
        }
        if (c.age % 3 == 0)
            for (int i = 0; i < 10; i++) {
                double a = sl.random.nextDouble() * Math.PI * 2, r = Math.sqrt(sl.random.nextDouble()) * R;
                DivineEvents.particle(sl, ParticleTypes.ASH, c.at.x + Math.cos(a) * r, c.at.y + 2 + sl.random.nextDouble() * 12, c.at.z + Math.sin(a) * r, 1, 0, 0);
            }
        if (c.age % 40 == 0) sl.playSound(null, c.at.x, c.at.y, c.at.z, SoundEvents.LIGHTNING_BOLT_THUNDER, SoundSource.PLAYERS, 3f, 0.4f);
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            Cast c = CASTS.remove(caster.getUUID());
            if (c != null) rain(sl, caster, c);
        }
        super.onCast(level, spellLevel, caster, source, md);
    }

    @Override
    public void onServerCastComplete(Level level, int spellLevel, LivingEntity entity, MagicData md, boolean cancelled) {
        Cast c = CASTS.remove(entity.getUUID());
        if (c != null && c.fx >= 0 && level instanceof ServerLevel sl) Fx.stop(sl, c.fx, "");
        super.onServerCastComplete(level, spellLevel, entity, md, cancelled);
    }

    private void rain(ServerLevel sl, LivingEntity caster, Cast cast) {
        Vec3 o = cast.at;
        sl.playSound(null, o.x, o.y, o.z, SoundEvents.WITHER_SPAWN, SoundSource.PLAYERS, 4f, 0.5f);
        Tasks.add(new Tasks.Task() {
            int age;

            @Override
            public boolean tick() {
                age++;
                if (age % 5 == 0 && age <= RAIN) {
                    Vec3 p;
                    List<LivingEntity> foes = HigherSpell.around(sl, o, R, e -> HigherSpell.foe(caster, e) || (e instanceof Player && !HigherSpell.friendly(caster, e)));
                    if (!foes.isEmpty() && sl.random.nextFloat() < 0.45f) {
                        LivingEntity t = foes.get(sl.random.nextInt(foes.size()));
                        p = t.position().add((sl.random.nextDouble() - 0.5) * 3, 0, (sl.random.nextDouble() - 0.5) * 3);
                    } else {
                        double a = sl.random.nextDouble() * Math.PI * 2, r = Math.sqrt(sl.random.nextDouble()) * R;
                        p = o.add(Math.cos(a) * r, 0, Math.sin(a) * r);
                    }
                    meteor(sl, caster, ground(sl, caster, p.add(0, 6, 0)));
                }
                if (age > RAIN + WARN + FALL) {
                    if (cast.fx >= 0) Fx.stop(sl, cast.fx, "");
                    return false;
                }
                return true;
            }
        });
    }

    private void meteor(ServerLevel sl, LivingEntity caster, Vec3 c) {
        Tasks.add(new Tasks.Task() {
            int age;
            Entity rock, core;

            @Override
            public boolean tick() {
                age++;
                if (age == 1) Fx.play(sl, Fx.fx("meteor").at(c).yaw(sl.random.nextFloat() * 360));   // mark, fiery trail, impact (in sync with the rock)
                if (age <= WARN) {
                    if (age % 2 == 0) {
                        int n = 18;
                        double rr = HIT_R * (1.2 - 0.2 * age / (double) WARN);
                        for (int i = 0; i < n; i++) {
                            double a = i * Math.PI * 2 / n;
                            DivineEvents.particle(sl, ORANGE, c.x + Math.cos(a) * rr, c.y + 0.1, c.z + Math.sin(a) * rr, 1, 0, 0);
                        }
                    }
                    if (age == WARN) {
                        rock = Disp.block(sl, "minecraft:magma_block", c.x, c.y + 26, c.z, 1.8f, 1.8f, 1.8f, sl.random.nextFloat() * 90);
                        core = Disp.block(sl, "minecraft:shroomlight", c.x, c.y + 26.2, c.z, 1.2f, 1.2f, 1.2f, 45);
                        sl.playSound(null, c.x, c.y + 20, c.z, SoundEvents.BLAZE_SHOOT, SoundSource.PLAYERS, 3f, 0.4f);
                    }
                    return true;
                }
                int f = age - WARN;
                double y = c.y + 26 * (1 - f / (double) FALL);
                Disp.move(rock, c.x, y, c.z, f * 25f);
                Disp.move(core, c.x, y + 0.3, c.z, -f * 25f);
                DivineEvents.particle(sl, ParticleTypes.FLAME, c.x, y + 1.5, c.z, 8, 0.5, 0.05);
                DivineEvents.particle(sl, ParticleTypes.LARGE_SMOKE, c.x, y + 2.5, c.z, 4, 0.4, 0.02);
                if (f < FALL) return true;
                Disp.kill(rock);
                Disp.kill(core);
                DivineEvents.particle(sl, ParticleTypes.EXPLOSION_EMITTER, c.x, c.y + 0.5, c.z, 1, 0, 0);
                DivineEvents.particle(sl, ParticleTypes.LAVA, c.x, c.y + 0.5, c.z, 25, HIT_R * 0.4, 0.1);
                sl.playSound(null, c.x, c.y, c.z, SoundEvents.GENERIC_EXPLODE, SoundSource.PLAYERS, 3f, 0.7f);
                CameraShakeManager.addCameraShake(new CameraShakeData(sl, 8, c, 12));
                for (LivingEntity e : HigherSpell.around(sl, c, HIT_R + 1, e -> !HigherSpell.friendly(caster, e))) {
                    double d = e.position().distanceTo(c);
                    if (d > HIT_R + e.getBbWidth() / 2) continue;
                    hit(caster, e, (float) (DMG * mult(caster) * (1 - 0.4 * Math.min(1, d / HIT_R))));
                    e.setSecondsOnFire(4);
                    Vec3 away = e.position().subtract(c).multiply(1, 0, 1);
                    if (away.lengthSqr() > 1e-4) HigherSpell.push(e, away.normalize().scale(0.7).add(0, 0.45, 0));
                }
                return false;
            }
        });
    }
}
