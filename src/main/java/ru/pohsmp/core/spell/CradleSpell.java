package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.util.Utils;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
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
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.DivineEvents;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.net.Net;

/** Dream mage: 2 s cast, the target sleeps 4 s; a hit wakes it with +50% damage, otherwise it wakes in dread and is thrown back. */
public class CradleSpell extends HigherSpell {
    public static final String PATH = "nightmare_cradle";
    private static final int CAST = 40, SLEEP = 80, DREAD = 120;
    private static final int COLOR = 0x8A4DFF;
    private static final Map<UUID, Integer> TELE = new HashMap<>();

    public CradleSpell() {
        super(PATH, CAST);
    }

    @Override public CastType getCastType() { return CastType.LONG; }
    @Override public Optional<SoundEvent> getCastStartSound() { return Optional.of(SoundEvents.ILLUSIONER_PREPARE_BLINDNESS); }
    @Override public Optional<SoundEvent> getCastFinishSound() { return Optional.empty(); }

    @Override
    public List<MutableComponent> getUniqueInfo(int spellLevel, LivingEntity caster) {
        return List.of(ui("sleep", SLEEP / 20), ui("bonus", "50%"), ui("dread", DREAD / 20));
    }

    @Override
    public boolean checkPreCastConditions(Level level, int spellLevel, LivingEntity entity, MagicData md) {
        return Utils.preCastTargetHelper(level, entity, md, this, 24, 0.35f);
    }

    @Override
    public void onServerPreCast(Level level, int spellLevel, LivingEntity entity, MagicData md) {
        super.onServerPreCast(level, spellLevel, entity, md);
        if (!(level instanceof ServerLevel sl)) return;
        LivingEntity t = target(sl, md);
        if (t == null) return;
        int k = key();
        TELE.put(entity.getUUID(), k);
        fx(sl, t.getX(), t.getY(), t.getZ(), new Net.HFx(Net.HFx.TELE, k, -1, t.getId(), CAST, t.getX(), t.getY(), t.getZ(), 1.6, COLOR));
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity entity, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            LivingEntity t = target(sl, md);
            if (t != null && t.isAlive()) sleep(sl, entity, t);
        }
        super.onCast(level, spellLevel, entity, source, md);
    }

    @Override
    public void onServerCastComplete(Level level, int spellLevel, LivingEntity entity, MagicData md, boolean cancelled) {
        Integer k = TELE.remove(entity.getUUID());
        if (k != null && level instanceof ServerLevel sl) stop(sl, entity.getX(), entity.getY(), entity.getZ(), k);
        super.onServerCastComplete(level, spellLevel, entity, md, cancelled);
    }

    private static void hide(LivingEntity t, boolean on) {
        if (!(t instanceof Player)) return;
        if (on) {
            t.addEffect(new MobEffectInstance(MobEffects.DARKNESS, SLEEP + 10, 0, false, false, false));
            t.addEffect(new MobEffectInstance(MobEffects.BLINDNESS, SLEEP + 10, 0, false, false, false));
        } else {
            t.removeEffect(MobEffects.DARKNESS);
            t.removeEffect(MobEffects.BLINDNESS);
        }
    }

    private static void sleep(ServerLevel sl, LivingEntity caster, LivingEntity t) {
        t.removeEffect(Reg.NIGHTMARE.get());
        t.addEffect(new MobEffectInstance(Reg.NIGHTMARE.get(), SLEEP + 10, 0, false, true, true));
        hide(t, true);
        int k = key();
        fx(sl, t.getX(), t.getY(), t.getZ(), new Net.HFx(Net.HFx.SLEEP, k, -1, t.getId(), SLEEP, t.getX(), t.getY(), t.getZ(), 0, COLOR));
        sl.playSound(null, t.getX(), t.getY(), t.getZ(), SoundEvents.ILLUSIONER_CAST_SPELL, SoundSource.PLAYERS, 1.5f, 0.6f);
        Tasks.add(new Tasks.Task() {
            int age;

            @Override
            public boolean tick() {
                age++;
                if (!t.isAlive() || t.isRemoved() || t.level() != sl) {
                    stop(sl, t.getX(), t.getY(), t.getZ(), k);
                    return false;
                }
                double cy = t.getY() + t.getBbHeight() + 0.3;
                if (!t.hasEffect(Reg.NIGHTMARE.get())) {
                    hide(t, false);
                    stop(sl, t.getX(), t.getY(), t.getZ(), k);
                    sl.playSound(null, t.getX(), t.getY(), t.getZ(), SoundEvents.GLASS_BREAK, SoundSource.PLAYERS, 1f, 0.6f);
                    DivineEvents.particle(sl, ParticleTypes.WITCH, t.getX(), cy, t.getZ(), 20, 0.4, 0.05);
                    return false;
                }
                if (age % 20 == 5) sl.playSound(null, t.getX(), t.getY(), t.getZ(), SoundEvents.SOUL_ESCAPE, SoundSource.PLAYERS, 1.2f, 0.5f + 0.1f * (age / 20));
                if (age % 4 == 0) DivineEvents.particle(sl, ParticleTypes.WITCH, t.getX(), cy, t.getZ(), 1, 0.3, 0.0);
                if (age < SLEEP) return true;
                t.removeEffect(Reg.NIGHTMARE.get());
                hide(t, false);
                t.addEffect(new MobEffectInstance(Reg.DREAD.get(), DREAD, 0, false, true, true));
                Vec3 d = new Vec3(t.getX() - caster.getX(), 0, t.getZ() - caster.getZ());
                d = d.lengthSqr() < 1e-4 ? new Vec3(1, 0, 0) : d.normalize();
                push(t, d.scale(1.3).add(0, 0.45, 0));
                stop(sl, t.getX(), t.getY(), t.getZ(), k);
                burst(sl, t.getX(), t.getY() + t.getBbHeight() / 2, t.getZ(), 2.5, COLOR);
                sl.playSound(null, t.getX(), t.getY(), t.getZ(), SoundEvents.WARDEN_ROAR, SoundSource.PLAYERS, 1f, 1.6f);
                return false;
            }
        });
    }
}
