package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.util.Utils;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.damagesource.DamageType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.entity.living.LivingDamageEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.DivineEvents;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.ServerConfig;
import ru.pohsmp.core.fx.Fx;

/**
 * Countdown (T04): 1 s cast on a target up to 32 blocks away. A clock face hangs over its head for 10 s and records all damage it takes
 * (after armor and resistances, any source). When the time is up, the sum is repeated as one higher-magic hit that ignores armor,
 * times damageMult, capped at [countdown] maxRepeat of the target's max health. Nothing happens if the target dies first.
 * The number in the lower part of the clock face (text slot {@value #COUNTER} of time_clock, T07) shows the hit that will come back.
 */
public class CountdownSpell extends HigherSpell {
    public static final String PATH = "countdown";
    public static final String SIGIL = "time_clock";
    private static final int CAST = 20, LIFE = 200;
    private static final double RANGE = 32;
    public static final int COLOR = 0xF2D27A;
    /** Text slot of the counter in time_clock.json (docs/sigils.md «Надписи»). */
    public static final String COUNTER = "count";
    /** Same death message as higher_magic, but goes through armor (tags/damage_type/bypasses_armor). */
    public static final ResourceKey<DamageType> DAMAGE = ResourceKey.create(Registries.DAMAGE_TYPE, new ResourceLocation(PohCore.MODID, "countdown_magic"));

    private static final class Clock {
        LivingEntity caster, target;
        double sum;
        int inst, hits;
        long flashAt = -1;
    }

    private static final Map<UUID, List<Clock>> CLOCKS = new HashMap<>();

    public CountdownSpell() {
        super(PATH, CAST);
    }

    @Override public CastType getCastType() { return CastType.LONG; }
    @Override public Optional<SoundEvent> getCastStartSound() { return Optional.of(SoundEvents.ENCHANTMENT_TABLE_USE); }
    @Override public Optional<SoundEvent> getCastFinishSound() { return Optional.empty(); }

    @Override
    public List<MutableComponent> getUniqueInfo(int spellLevel, LivingEntity caster) {
        return List.of(ui("time", LIFE / 20), ui("cap", (int) Math.round(ServerConfig.COUNTDOWN_MAX.get() * 100)));
    }

    @Override
    public boolean checkPreCastConditions(Level level, int spellLevel, LivingEntity entity, MagicData md) {
        return Utils.preCastTargetHelper(level, entity, md, this, (int) RANGE, 0.35f);
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity entity, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            LivingEntity t = target(sl, md);
            if (t != null && t.isAlive() && t.distanceToSqr(entity) <= (RANGE + 4) * (RANGE + 4)) start(sl, entity, t);
        }
        super.onCast(level, spellLevel, entity, source, md);
    }

    private static Vec3 above(LivingEntity t) {
        return t.position().add(0, t.getBbHeight() + 1.25, 0);
    }

    /** Starts a countdown on t; also used by scripts and NPC casters. */
    public static void start(ServerLevel sl, LivingEntity caster, LivingEntity t) {
        Clock c = new Clock();
        c.caster = caster;
        c.target = t;
        Vec3 p = above(t);
        c.inst = Fx.play(sl, Fx.sigil(SIGIL).at(p).attach(t).yaw(caster.getYRot()).orientation("facing").scale(0.45).duration(LIFE + 40)
                .text(COUNTER, "0"));
        CLOCKS.computeIfAbsent(t.getUUID(), k -> new ArrayList<>()).add(c);
        sl.playSound(null, p.x, p.y, p.z, SoundEvents.BEACON_ACTIVATE, SoundSource.PLAYERS, 1.2f, 1.8f);
        sl.playSound(null, p.x, p.y, p.z, SoundEvents.NOTE_BLOCK_CHIME.get(), SoundSource.PLAYERS, 1.2f, 0.7f);
        Tasks.add(new Tasks.Task() {
            int age;

            @Override
            public boolean tick() {
                age++;
                boolean gone = !t.isAlive() || t.isRemoved() || t.level() != sl;
                if (gone || age >= LIFE) {
                    forget(c);
                    if (gone) Fx.stop(sl, c.inst, "fade");
                    else repeat(sl, c);
                    return false;
                }
                if (age % 20 == 0) {          // quiet clockwork each second
                    Vec3 q = above(t);
                    sl.playSound(null, q.x, q.y, q.z, SoundEvents.NOTE_BLOCK_HAT.get(), SoundSource.PLAYERS, 0.35f, 1.9f);
                }
                return true;
            }
        });
    }

    private static void forget(Clock c) {
        List<Clock> l = CLOCKS.get(c.target.getUUID());
        if (l == null) return;
        l.remove(c);
        if (l.isEmpty()) CLOCKS.remove(c.target.getUUID());
    }

    /** The hit that will come back: sum × damageMult, capped at maxRepeat of the target's max health. */
    private static double amount(Clock c) {
        return Math.min(c.sum * ServerConfig.HIGHER_MULT.get(), ServerConfig.COUNTDOWN_MAX.get() * c.target.getMaxHealth());
    }

    /** Counter text: whole numbers from 10 up, one decimal below (4.5), never "-0". */
    static String counter(double v) {
        if (v < 9.95) {
            String s = String.format(java.util.Locale.ROOT, "%.1f", Math.max(0, v));
            return s.endsWith(".0") ? s.substring(0, s.length() - 2) : s;
        }
        return Long.toString(Math.round(v));
    }

    private static void repeat(ServerLevel sl, Clock c) {
        LivingEntity t = c.target;
        Vec3 p = above(t);
        Fx.stop(sl, c.inst, "shatter");
        burst(sl, p.x, p.y, p.z, 3.0, COLOR);
        sl.playSound(null, p.x, p.y, p.z, SoundEvents.BELL_BLOCK, SoundSource.PLAYERS, 2.5f, 0.8f);
        sl.playSound(null, p.x, p.y, p.z, SoundEvents.GLASS_BREAK, SoundSource.PLAYERS, 1.4f, 0.6f);
        DivineEvents.particle(sl, ParticleTypes.END_ROD, p.x, p.y, p.z, 30, 0.6, 0.15);
        float amount = (float) amount(c);
        if (amount <= 0.01f) return;
        t.invulnerableTime = 0;
        DamageSource src = new DamageSource(sl.registryAccess().registryOrThrow(Registries.DAMAGE_TYPE).getHolderOrThrow(DAMAGE), c.caster);
        t.hurt(src, amount);
        DivineEvents.particle(sl, ParticleTypes.CRIT, t.getX(), t.getY() + t.getBbHeight() * 0.5, t.getZ(), 40, 0.4, 0.4);
    }

    public static final class CountdownEvents {
        private CountdownEvents() {}

        @SubscribeEvent(priority = EventPriority.LOWEST)
        public static void onDamage(LivingDamageEvent e) {
            if (CLOCKS.isEmpty()) return;
            LivingEntity t = e.getEntity();
            if (t.level().isClientSide || e.getAmount() <= 0) return;
            List<Clock> l = CLOCKS.get(t.getUUID());
            if (l == null) return;
            ServerLevel sl = (ServerLevel) t.level();
            long now = sl.getGameTime();
            Vec3 p = above(t);
            boolean sound = false;
            for (Clock c : l) {
                c.sum += e.getAmount();
                c.hits++;
                Fx.text(sl, c.inst, COUNTER, counter(amount(c)));    // the number on the face writes itself in with a flare
                if (c.flashAt == now) continue;      // several hits in one tick: one flash
                c.flashAt = now;
                sound = true;
            }
            if (sound) {
                burst(sl, p.x, p.y, p.z, 1.1, COLOR);
                sl.playSound(null, p.x, p.y, p.z, SoundEvents.NOTE_BLOCK_HAT.get(), SoundSource.PLAYERS, 1.0f, 1.2f);
                sl.playSound(null, p.x, p.y, p.z, SoundEvents.AMETHYST_BLOCK_HIT, SoundSource.PLAYERS, 0.8f, 1.6f);
            }
        }

        @SubscribeEvent
        public static void onStopping(ServerStoppingEvent e) {
            CLOCKS.clear();
        }
    }
}
