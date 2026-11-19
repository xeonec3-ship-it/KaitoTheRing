package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.particle.SwirlingParticleOptions;
import io.redspace.ironsspellbooks.util.ParticleHelper;
import java.util.List;
import java.util.Optional;
import net.minecraft.core.particles.ParticleOptions;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.RandomSource;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.DivineEvents;
import ru.pohsmp.core.net.Net;

/**
 * Eternal Blizzard (Higher, instant): a ring of snowstorm r12 around the cast point for 15 s, walls 6 high.
 * Inside, enemies are slowed harder the closer they are to the wall (Slowness II at the center up to V at the edge),
 * freeze like in powder snow (the frost builds up; fully frozen = vanilla freeze damage), and the last 1.5 blocks
 * before the wall gently pull back inside: leaving is possible, but slow. The storm itself (snow wall at the edge, frost on the
 * ground by the wall, snowfall and haze inside) is drawn by each client from one HFx BLIZZARD packet (client/HigherFx).
 */
public class EternalBlizzardSpell extends HigherSpell {
    public static final String PATH = "eternal_blizzard";
    public static final int LIFE = 300, COLOR = 0x9FD8FF;
    public static final double R = 12, WALL_H = 6, EDGE = 1.5;
    private static final int FREEZE_ADD = 3;   // per tick; vanilla thaws 2 per tick outside powder snow, so the net build-up is +1/tick

    public EternalBlizzardSpell() {
        super(PATH, 0);
    }

    @Override public CastType getCastType() { return CastType.INSTANT; }
    @Override public Optional<SoundEvent> getCastStartSound() { return Optional.empty(); }
    @Override public Optional<SoundEvent> getCastFinishSound() { return Optional.of(SoundEvents.POWDER_SNOW_PLACE); }

    @Override
    public List<MutableComponent> getUniqueInfo(int spellLevel, LivingEntity caster) {
        return List.of(ui("zone", (int) R, LIFE / 20), ui("slow"), ui("freeze"), ui("edge"));
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity entity, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) open(sl, entity);
        super.onCast(level, spellLevel, entity, source, md);
    }

    private static boolean immune(LivingEntity caster, LivingEntity e) {
        return friendly(caster, e) || (e instanceof Player p && (p.isCreative() || p.isSpectator()));
    }

    private void open(ServerLevel sl, LivingEntity caster) {
        Vec3 c = caster.position();
        int k = key();
        fx(sl, c.x, c.y, c.z, new Net.HFx(Net.HFx.BLIZZARD, k, caster.getId(), -1, LIFE, c.x, c.y, c.z, (float) R, COLOR));
        sl.playSound(null, c.x, c.y, c.z, SoundEvents.POWDER_SNOW_BREAK, SoundSource.PLAYERS, 3f, 0.5f);
        sl.playSound(null, c.x, c.y, c.z, SoundEvents.GLASS_BREAK, SoundSource.PLAYERS, 2f, 0.6f);
        sl.playSound(null, c.x, c.y, c.z, SoundEvents.ELYTRA_FLYING, SoundSource.PLAYERS, 1.5f, 0.5f);
        RandomSource rnd = caster.getRandom();
        Tasks.add(new Tasks.Task() {
            int age;

            @Override
            public boolean tick() {
                age++;
                AABB box = new AABB(c, c).inflate(R + 1, 0, R + 1).expandTowards(0, WALL_H + 2, 0).expandTowards(0, -3, 0);
                for (LivingEntity e : sl.getEntitiesOfClass(LivingEntity.class, box, e -> e.isAlive() && !immune(caster, e))) {
                    double dx = e.getX() - c.x, dz = e.getZ() - c.z, d = Math.sqrt(dx * dx + dz * dz);
                    if (d > R) continue;
                    double kk = d / R;
                    if (age % 5 == 1) {
                        int amp = Math.min(4, 1 + (int) (kk * 4));   // II at the center ... V at the wall
                        e.addEffect(new MobEffectInstance(MobEffects.MOVEMENT_SLOWDOWN, 12, amp, false, false, true));
                    }
                    if (e.canFreeze()) e.setTicksFrozen(Math.min(e.getTicksRequiredToFreeze() + 40, e.getTicksFrozen() + FREEZE_ADD));
                    if (d > R - EDGE && d > 0.1) {   // the wall drags back inside: slow escape, not a cage
                        Vec3 v = e.getDeltaMovement().add(-dx / d * 0.015, 0, -dz / d * 0.015);
                        push(e, v);
                    }
                    if (age % 10 == 0) DivineEvents.particle(sl, ParticleTypes.SNOWFLAKE, e.getX(), e.getY() + e.getBbHeight() * 0.6, e.getZ(), 3, 0.3, 0.02);
                }
                if (age % 30 == 0) sl.playSound(null, c.x, c.y, c.z, SoundEvents.POWDER_SNOW_STEP, SoundSource.PLAYERS, 2f, 0.6f);
                if (age % 60 == 0) sl.playSound(null, c.x, c.y, c.z, SoundEvents.ELYTRA_FLYING, SoundSource.PLAYERS, 1f, 0.4f);
                if (age < LIFE) return true;
                stop(sl, c.x, c.y, c.z, k);
                sl.playSound(null, c.x, c.y, c.z, SoundEvents.POWDER_SNOW_BREAK, SoundSource.PLAYERS, 3f, 0.8f);
                return false;
            }
        });
    }

}
