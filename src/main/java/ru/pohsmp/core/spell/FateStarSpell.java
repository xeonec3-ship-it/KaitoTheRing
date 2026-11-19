package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.util.Utils;
import java.util.Comparator;
import java.util.List;
import java.util.Optional;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.network.chat.Style;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.DivineEvents;
import ru.pohsmp.core.fx.Fx;

/**
 * Astrologer: a constellation lights up over the target for 3 s, then a star falls (20 in r3, thrown up).
 * A random tarot card bends it: Sun +50% and fire, Moon blindness, Tower double on the target but hurts the caster, World also strikes 2 more foes.
 */
public class FateStarSpell extends HigherSpell {
    public static final String PATH = "fate_star";
    private static final int FALL = 60;
    private static final double DMG = 20, R = 3;
    public static final int SUN = 0, MOON = 1, TOWER = 2, WORLD = 3;
    private static final String[] CARD = {"sun", "moon", "tower", "world"};
    public static final int[] CARD_COLOR = {0xFFC94D, 0xA8C8FF, 0xFF4D4D, 0x7DFFB0};

    public FateStarSpell() {
        super(PATH, 0);
    }

    @Override public CastType getCastType() { return CastType.INSTANT; }
    @Override public Optional<SoundEvent> getCastStartSound() { return Optional.empty(); }
    @Override public Optional<SoundEvent> getCastFinishSound() { return Optional.of(SoundEvents.AMETHYST_BLOCK_RESONATE); }

    @Override
    public List<MutableComponent> getUniqueInfo(int spellLevel, LivingEntity caster) {
        return List.of(ui("damage", num(DMG), (int) R), ui("delay", FALL / 20), ui("cards"));
    }

    @Override
    public boolean checkPreCastConditions(Level level, int spellLevel, LivingEntity entity, MagicData md) {
        return Utils.preCastTargetHelper(level, entity, md, this, 32, 0.35f);
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity entity, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            LivingEntity t = target(sl, md);
            if (t != null && t.isAlive()) cast(sl, entity, t);
        }
        super.onCast(level, spellLevel, entity, source, md);
    }

    private void cast(ServerLevel sl, LivingEntity caster, LivingEntity t) {
        int card = caster.getRandom().nextInt(4);
        Component msg = ui("card", ui("card." + CARD[card])).withStyle(Style.EMPTY.withColor(CARD_COLOR[card]).withBold(true));
        if (caster instanceof ServerPlayer sp) sp.displayClientMessage(msg, true);
        if (t instanceof ServerPlayer tp) tp.displayClientMessage(msg, true);
        sl.playSound(null, t.getX(), t.getY(), t.getZ(), SoundEvents.AMETHYST_BLOCK_CHIME, SoundSource.PLAYERS, 2f, 0.7f);
        star(sl, caster, t, card, true);
        if (card == WORLD) {
            around(sl, t.position(), 10, e -> e != t && foe(caster, e)).stream()
                    .sorted(Comparator.comparingDouble(e -> e.distanceToSqr(t))).limit(2)
                    .forEach(e -> star(sl, caster, e, WORLD, false));
        }
    }

    private void star(ServerLevel sl, LivingEntity caster, LivingEntity t, int card, boolean main) {
        // constellation over the target, the card under it, the falling star at FALL - 14 and the impact at FALL (fx/higher_fate_<card>.json)
        Fx.play(sl, Fx.fx("higher_fate_" + CARD[card]).at(t.position()).caster(caster).target(t));
        Tasks.add(new Tasks.Task() {
            int age;
            Vec3 last = t.position();

            @Override
            public boolean tick() {
                age++;
                if (t.isAlive() && !t.isRemoved() && t.level() == sl) last = t.position();
                if (age % 12 == 0) sl.playSound(null, last.x, last.y + 7, last.z, SoundEvents.AMETHYST_BLOCK_CHIME, SoundSource.PLAYERS, 1.5f, 0.8f + age / 60f);
                if (age < FALL) return true;
                impact(sl, caster, t, card, main, last);
                return false;
            }
        });
    }

    private void impact(ServerLevel sl, LivingEntity caster, LivingEntity main, int card, boolean primary, Vec3 c) {
        sl.playSound(null, c.x, c.y, c.z, SoundEvents.FIREWORK_ROCKET_LARGE_BLAST, SoundSource.PLAYERS, 3f, 0.7f);
        sl.playSound(null, c.x, c.y, c.z, SoundEvents.GENERIC_EXPLODE, SoundSource.PLAYERS, 1.5f, 1.5f);
        DivineEvents.particle(sl, ParticleTypes.END_ROD, c.x, c.y + 0.5, c.z, 60, 0.3, 0.35);
        DivineEvents.particle(sl, ParticleTypes.FIREWORK, c.x, c.y + 0.5, c.z, 40, 0.5, 0.25);
        for (LivingEntity e : around(sl, c, R, e -> !friendly(caster, e))) {
            double d = DMG;
            if (card == TOWER && e == main) d *= 2;
            if (card == SUN) d *= 1.5;
            hurt(sl, caster, e, dmg(d));
            if (card == SUN) e.setSecondsOnFire(5);
            if (card == MOON) e.addEffect(new MobEffectInstance(MobEffects.BLINDNESS, 80, 0));
            push(e, e.getDeltaMovement().add(0, 0.8, 0));
        }
        if (card == TOWER && primary && caster.isAlive()) {
            caster.invulnerableTime = 0;
            caster.hurt(src(sl, caster), dmg(DMG * 0.25));
        }
    }
}
