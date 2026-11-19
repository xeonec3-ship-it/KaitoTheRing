package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.spells.SpellAnimations;
import io.redspace.ironsspellbooks.api.spells.SpellRarity;
import io.redspace.ironsspellbooks.api.util.AnimationHolder;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import net.minecraft.core.particles.DustParticleOptions;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.tags.DamageTypeTags;
import net.minecraft.world.effect.MobEffect;
import net.minecraft.world.effect.MobEffectCategory;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.monster.Enemy;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.entity.living.LivingDeathEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import org.joml.Vector3f;
import ru.pohsmp.core.DivineEvents;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.fx.Fx;

/**
 * Divine. "The Ark": after a 5 s cast a dome of light r32 stands for 60 s at the cast point. Players inside cannot die (health stays
 * at least 1), heal 1 HP a second and lose their harmful effects at the moment of the cast; enemies at its border are blinded.
 * Divine Backlash follows, as with every Divine spell.
 */
public class ArkSpell extends PohSpell {
    public static final String PATH = "ark";
    public static final int CAST = 100, LIFE = 1200;
    public static final double R = 32;
    private static final DustParticleOptions GOLD = new DustParticleOptions(new Vector3f(1f, 0.85f, 0.4f), 2.2f);

    private static final class Dome {
        ResourceKey<Level> dim;
        Vec3 c;
        long until;
    }

    private static final List<Dome> DOMES = new ArrayList<>();

    public ArkSpell() {
        super(PATH, Reg.DIVINE_ID, SpellRarity.LEGENDARY, 1, 0, CAST, 0, 0);
    }

    @Override public CastType getCastType() { return CastType.LONG; }
    @Override public boolean canBeInterrupted(Player player) { return false; }
    @Override public boolean allowCrafting() { return false; }
    @Override public Optional<SoundEvent> getCastStartSound() { return Optional.of(SoundEvents.BEACON_ACTIVATE); }
    @Override public Optional<SoundEvent> getCastFinishSound() { return Optional.of(SoundEvents.BELL_RESONATE); }
    @Override public AnimationHolder getCastStartAnimation() { return SpellAnimations.ANIMATION_LONG_CAST; }
    @Override public AnimationHolder getCastFinishAnimation() { return SpellAnimations.ANIMATION_LONG_CAST_FINISH; }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("zone", (int) R, LIFE / 20), ui("undying"), ui("heal"), ui("blind"));
    }

    /** caster -> its cast effect (fx/ark_cast.json: seal under the caster, rising lights), stopped on cast or cancel. */
    private static final java.util.Map<java.util.UUID, Integer> CASTING = new java.util.HashMap<>();

    @Override
    public void onServerPreCast(Level level, int spellLevel, LivingEntity caster, MagicData md) {
        super.onServerPreCast(level, spellLevel, caster, md);
        if (level instanceof ServerLevel sl) {
            Integer old = CASTING.put(caster.getUUID(), Fx.play(sl, Fx.fx("ark_cast").at(caster.position()).caster(caster).attach(caster)));
            if (old != null) Fx.stop(sl, old, "");
        }
    }

    @Override
    public void onServerCastComplete(Level level, int spellLevel, LivingEntity caster, MagicData md, boolean cancelled) {
        Integer k = CASTING.remove(caster.getUUID());
        if (k != null && level instanceof ServerLevel sl) Fx.stop(sl, k, "");
        super.onServerCastComplete(level, spellLevel, caster, md, cancelled);
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            Integer k = CASTING.remove(caster.getUUID());
            if (k != null) Fx.stop(sl, k, "");
            Dome d = new Dome();
            d.dim = sl.dimension();
            d.c = caster.position();
            d.until = sl.getGameTime() + LIFE;
            DOMES.add(d);
            Vec3 c = d.c;
            // the dome (owner, 19.11.2026: new circles and effects like the Closure dome): frame, latitudes, rune belt, seals on the shell, sun at the zenith
            int fx = Fx.play(sl, Fx.fx("ark").at(c).yaw(0).duration(LIFE));
            sl.playSound(null, c.x, c.y, c.z, SoundEvents.BEACON_POWER_SELECT, SoundSource.PLAYERS, 5f, 0.5f);
            sl.playSound(null, c.x, c.y, c.z, SoundEvents.BELL_BLOCK, SoundSource.PLAYERS, 5f, 0.5f);
            MobEffect silence = net.minecraftforge.registries.ForgeRegistries.MOB_EFFECTS.getValue(new net.minecraft.resources.ResourceLocation("mna", "silence"));
            for (ServerPlayer p : sl.players()) {
                if (p.position().distanceToSqr(c) >= R * R) continue;
                List<MobEffect> bad = new ArrayList<>();
                for (MobEffectInstance i : p.getActiveEffects())
                    if (i.getEffect().getCategory() == MobEffectCategory.HARMFUL && i.getEffect() != Reg.BACKLASH.get() && i.getEffect() != silence) bad.add(i.getEffect());
                for (MobEffect m : bad) p.removeEffect(m);
                DivineEvents.particle(sl, ParticleTypes.END_ROD, p.getX(), p.getY() + 1, p.getZ(), 20, 0.4, 0.08);
            }
            Tasks.add(new Tasks.Task() {
                int age;

                @Override
                public boolean tick() {
                    age++;
                    if (!DOMES.contains(d)) return false;
                    if (sl.getGameTime() > d.until) {
                        DOMES.remove(d);
                        Fx.stop(sl, fx, "");
                        sl.playSound(null, c.x, c.y, c.z, SoundEvents.BEACON_DEACTIVATE, SoundSource.PLAYERS, 5f, 0.5f);
                        return false;
                    }
                    if (age % 20 == 0) {
                        for (ServerPlayer p : sl.players()) {
                            if (p.position().distanceToSqr(c) >= R * R || p.isSpectator()) continue;
                            if (p.getHealth() < p.getMaxHealth()) p.heal(1);
                            DivineEvents.particle(sl, GOLD, p.getX(), p.getY() + p.getBbHeight() + 0.4, p.getZ(), 1, 0.15, 0);
                        }
                        for (LivingEntity e : HigherSpell.around(sl, c, R + 2.5, e -> e instanceof Enemy || HigherSpell.foe(caster, e))) {
                            double dist = e.position().distanceTo(c);
                            if (dist < R - 3) continue;
                            e.addEffect(new MobEffectInstance(MobEffects.BLINDNESS, 60, 0, false, true, true));
                            DivineEvents.particle(sl, ParticleTypes.END_ROD, e.getX(), e.getY() + 1.5, e.getZ(), 4, 0.3, 0.02);
                        }
                    }
                    return true;
                }
            });
        }
        super.onCast(level, spellLevel, caster, source, md);
    }

    static boolean inside(Player p) {
        if (DOMES.isEmpty()) return false;
        long now = p.level().getGameTime();
        for (Dome d : DOMES)
            if (d.dim == p.level().dimension() && now <= d.until && p.position().distanceToSqr(d.c) < R * R) return true;
        return false;
    }

    public static final class ArkEvents {
        private ArkEvents() {}

        @SubscribeEvent(priority = EventPriority.HIGHEST)
        public static void onDeath(LivingDeathEvent e) {
            if (!(e.getEntity() instanceof ServerPlayer p) || e.getSource().is(DamageTypeTags.BYPASSES_INVULNERABILITY) || !inside(p)) return;
            e.setCanceled(true);
            p.setHealth(1);
            p.invulnerableTime = 20;
            DivineEvents.particle(p.serverLevel(), ParticleTypes.TOTEM_OF_UNDYING, p.getX(), p.getY() + 1, p.getZ(), 30, 0.4, 0.3);
            p.serverLevel().playSound(null, p.getX(), p.getY(), p.getZ(), SoundEvents.BELL_BLOCK, SoundSource.PLAYERS, 1.5f, 1.6f);
        }

        @SubscribeEvent
        public static void onStopping(ServerStoppingEvent e) {
            DOMES.clear();
        }
    }
}
