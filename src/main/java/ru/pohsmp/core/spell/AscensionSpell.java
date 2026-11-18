package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import java.util.Comparator;
import java.util.List;
import java.util.Optional;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import ru.pohsmp.core.DivineEvents;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.net.Net;

/**
 * Holy mage: the caster rises ~6 blocks and hangs 3 s in a column of light; every 0.5 s a beam from the sky hits the nearest foe within 12 (5).
 * Then a slow descent; on landing the caster and allies within 5 heal 4.
 */
public class AscensionSpell extends HigherSpell {
    public static final String PATH = "wind_ascension";
    private static final int RISE = 20, HOVER = 60, FALL_MAX = 120;
    private static final double BEAM_R = 12, BEAM_DMG = 5, HEAL = 4, HEAL_R = 5;
    public static final int COLOR = 0xFFF2B0;

    public AscensionSpell() {
        super(PATH, 0);
    }

    @Override public CastType getCastType() { return CastType.INSTANT; }
    @Override public Optional<SoundEvent> getCastStartSound() { return Optional.empty(); }
    @Override public Optional<SoundEvent> getCastFinishSound() { return Optional.of(SoundEvents.BEACON_ACTIVATE); }

    @Override
    public List<MutableComponent> getUniqueInfo(int spellLevel, LivingEntity caster) {
        return List.of(ui("hover", HOVER / 20), ui("beam", num(BEAM_DMG), (int) BEAM_R), ui("heal", num(HEAL), (int) HEAL_R));
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity entity, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) rise(sl, entity);
        super.onCast(level, spellLevel, entity, source, md);
    }

    private static void hidden(LivingEntity e, net.minecraft.world.effect.MobEffect eff, int ticks, int amp) {
        e.removeEffect(eff);
        e.addEffect(new MobEffectInstance(eff, ticks, amp, false, false, false));
    }

    private static boolean ally(LivingEntity caster, LivingEntity e) {
        return friendly(caster, e) || (caster instanceof Player && e instanceof Player);
    }

    private void rise(ServerLevel sl, LivingEntity c) {
        c.removeEffect(Reg.ASCENSION.get());
        c.addEffect(new MobEffectInstance(Reg.ASCENSION.get(), RISE + HOVER + FALL_MAX + 20, 0, false, true, true));
        hidden(c, MobEffects.LEVITATION, RISE, 6);
        int k = key();
        fx(sl, c.getX(), c.getY(), c.getZ(), new Net.HFx(Net.HFx.ASC, k, c.getId(), -1, RISE + HOVER, c.getX(), c.getY(), c.getZ(), 0, COLOR));
        sl.playSound(null, c.getX(), c.getY(), c.getZ(), SoundEvents.PHANTOM_FLAP, SoundSource.PLAYERS, 2f, 0.6f);
        DivineEvents.particle(sl, ParticleTypes.CLOUD, c.getX(), c.getY() + 0.2, c.getZ(), 30, 0.6, 0.1);
        Tasks.add(new Tasks.Task() {
            int age;

            @Override
            public boolean tick() {
                age++;
                if (!c.isAlive() || c.isRemoved() || c.level() != sl) {
                    stop(sl, c.getX(), c.getY(), c.getZ(), k);
                    return false;
                }
                c.fallDistance = 0;
                if (age == RISE) hidden(c, MobEffects.LEVITATION, HOVER, -1);
                if (age > RISE && age <= RISE + HOVER) {
                    if (age % 3 == 0) DivineEvents.particle(sl, ParticleTypes.END_ROD, c.getX(), c.getY() + 0.5, c.getZ(), 1, 0.4, 0.02);
                    if ((age - RISE) % 10 == 0) beam(sl, c);
                }
                if (age == RISE + HOVER) {
                    c.removeEffect(MobEffects.LEVITATION);
                    hidden(c, MobEffects.SLOW_FALLING, FALL_MAX, 0);
                    stop(sl, c.getX(), c.getY(), c.getZ(), k);
                }
                if (age <= RISE + HOVER) return true;
                if (!c.onGround() && !c.isInWater() && age < RISE + HOVER + FALL_MAX) return true;
                land(sl, c);
                return false;
            }
        });
    }

    private static void beam(ServerLevel sl, LivingEntity c) {
        LivingEntity t = around(sl, c.position(), BEAM_R, e -> foe(c, e) && c.hasLineOfSight(e)).stream()
                .min(Comparator.comparingDouble(e -> e.distanceToSqr(c))).orElse(null);
        if (t == null) return;
        fx(sl, t.getX(), t.getY(), t.getZ(), new Net.HFx(Net.HFx.PILLAR, key(), -1, -1, 14, t.getX(), t.getY() - 0.5, t.getZ(), 0.45, COLOR));
        burst(sl, t.getX(), t.getY() + 0.1, t.getZ(), 1.5, COLOR);
        sl.playSound(null, t.getX(), t.getY(), t.getZ(), SoundEvents.AMETHYST_CLUSTER_BREAK, SoundSource.PLAYERS, 2f, 1.4f);
        sl.playSound(null, t.getX(), t.getY(), t.getZ(), SoundEvents.FIREWORK_ROCKET_TWINKLE, SoundSource.PLAYERS, 1f, 1.2f);
        DivineEvents.particle(sl, ParticleTypes.END_ROD, t.getX(), t.getY() + 1, t.getZ(), 15, 0.2, 0.15);
        hurt(sl, c, t, dmg(BEAM_DMG));
    }

    private static void land(ServerLevel sl, LivingEntity c) {
        c.removeEffect(MobEffects.SLOW_FALLING);
        c.removeEffect(MobEffects.LEVITATION);
        c.fallDistance = 0;
        burst(sl, c.getX(), c.getY() + 0.1, c.getZ(), HEAL_R, COLOR);
        sl.playSound(null, c.getX(), c.getY(), c.getZ(), SoundEvents.BEACON_DEACTIVATE, SoundSource.PLAYERS, 2f, 1.3f);
        sl.playSound(null, c.getX(), c.getY(), c.getZ(), SoundEvents.AMETHYST_BLOCK_CHIME, SoundSource.PLAYERS, 2f, 1.0f);
        for (LivingEntity e : around(sl, c.position(), HEAL_R, e -> ally(c, e))) {
            e.heal(dmg(HEAL));
            DivineEvents.particle(sl, ParticleTypes.HEART, e.getX(), e.getY() + e.getBbHeight() + 0.3, e.getZ(), 3, 0.3, 0);
        }
        Tasks.add(new Tasks.Task() {
            int age;

            @Override
            public boolean tick() {
                if (++age < 10) return true;
                c.removeEffect(Reg.ASCENSION.get());
                return false;
            }
        });
    }
}
