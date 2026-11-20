package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.registry.SchoolRegistry;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.spells.SpellAnimations;
import io.redspace.ironsspellbooks.api.spells.SpellRarity;
import io.redspace.ironsspellbooks.api.util.AnimationHolder;
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
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.entity.projectile.Projectile;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.living.LivingAttackEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import org.joml.Vector3f;
import ru.pohsmp.core.DivineEvents;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.fx.Fx;

/**
 * Mythic, level 1. "Frozen Hour": everything within 24 blocks except the caster stops for 8 s: creatures, projectiles, dropped
 * items, burning. Damage dealt to the frozen is not felt at once: it is stored with +50% and lands all together when time moves again.
 */
public class FrozenHourSpell extends PohSpell {
    public static final String PATH = "frozen_hour";
    public static final int CAST = 40, LIFE = 160;
    private static final double R = 24, BONUS = 1.5;
    private static final int COLOR = 0x9FD8FF;
    private static final DustParticleOptions PALE = new DustParticleOptions(new Vector3f(0.75f, 0.9f, 1f), 1.2f);

    private static final class Frozen {
        Entity e;
        Vec3 pos, vel;
        float yRot, xRot;
        boolean noAi, noGravity;
        int fire;
        float stored;
        DamageSource last;
        long until;
        int prism = -1;
    }

    private static final Map<UUID, Frozen> FROZEN = new HashMap<>();
    private static final ThreadLocal<Boolean> RELEASE = ThreadLocal.withInitial(() -> false);

    public FrozenHourSpell() {
        super(PATH, SchoolRegistry.ENDER_RESOURCE, SpellRarity.LEGENDARY, 1, 0, CAST, 0, 0);
    }

    @Override public CastType getCastType() { return CastType.LONG; }
    @Override public boolean canBeInterrupted(Player player) { return false; }
    @Override public boolean allowCrafting() { return false; }
    @Override public Optional<SoundEvent> getCastStartSound() { return Optional.of(SoundEvents.BELL_RESONATE); }
    @Override public Optional<SoundEvent> getCastFinishSound() { return Optional.empty(); }
    @Override public AnimationHolder getCastStartAnimation() { return SpellAnimations.ANIMATION_LONG_CAST; }
    @Override public AnimationHolder getCastFinishAnimation() { return SpellAnimations.ANIMATION_LONG_CAST_FINISH; }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("time", (int) R, LIFE / 20), ui("stored", (int) Math.round((BONUS - 1) * 100)));
    }

    @Override
    public void onServerCastTick(Level level, int spellLevel, LivingEntity caster, MagicData md) {
        super.onServerCastTick(level, spellLevel, caster, md);
        if (level instanceof ServerLevel sl && caster.tickCount % 2 == 0) {
            double a = caster.tickCount * 0.3;
            for (int i = 0; i < 12; i++)   // clock face around the caster
                DivineEvents.particle(sl, PALE, caster.getX() + Math.cos(i * Math.PI / 6) * 1.5, caster.getY() + 0.1, caster.getZ() + Math.sin(i * Math.PI / 6) * 1.5, 1, 0, 0);
            DivineEvents.particle(sl, ParticleTypes.END_ROD, caster.getX() + Math.cos(a) * 1.2, caster.getY() + 0.12, caster.getZ() + Math.sin(a) * 1.2, 1, 0, 0);
        }
    }

    /** The cast clock under the caster's feet (2 s), by caster. */
    private static final Map<UUID, Integer> CAST_FX = new HashMap<>();

    @Override
    public void onServerPreCast(Level level, int spellLevel, LivingEntity caster, MagicData md) {
        super.onServerPreCast(level, spellLevel, caster, md);
        if (level instanceof ServerLevel sl) {
            Integer old = CAST_FX.put(caster.getUUID(), Fx.play(sl, Fx.fx("frozen_hour_cast").caster(caster)));
            if (old != null) Fx.stop(sl, old, "");
        }
    }

    @Override
    public void onServerCastComplete(Level level, int spellLevel, LivingEntity caster, MagicData md, boolean cancelled) {
        Integer id = CAST_FX.remove(caster.getUUID());
        if (id != null && level instanceof ServerLevel sl) Fx.stop(sl, id, "");
        super.onServerCastComplete(level, spellLevel, caster, md, cancelled);
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) stop(sl, caster);
        super.onCast(level, spellLevel, caster, source, md);
    }

    private static void stop(ServerLevel sl, LivingEntity caster) {
        Vec3 c = caster.position();
        long until = sl.getGameTime() + LIFE;
        int prisms = 0;
        Fx.play(sl, Fx.fx("frozen_hour").at(c).yaw(caster.getYRot()));   // grey world, clocks in the sky, golden column, flash
        sl.playSound(null, c.x, c.y, c.z, SoundEvents.BELL_BLOCK, SoundSource.PLAYERS, 4f, 0.5f);
        sl.playSound(null, c.x, c.y, c.z, SoundEvents.BEACON_DEACTIVATE, SoundSource.PLAYERS, 4f, 0.5f);
        for (Entity e : sl.getEntities(caster, new AABB(c, c).inflate(R), e -> e.position().distanceToSqr(c) < R * R)) {
            if (e instanceof Player p && (p.isCreative() || p.isSpectator())) continue;
            if (!(e instanceof LivingEntity || e instanceof Projectile || e instanceof ItemEntity)) continue;
            if (e.getTags().contains(Disp.TAG) || FROZEN.containsKey(e.getUUID())) continue;
            int life = ru.pohsmp.core.boss.BossGuard.frozenHourTicks(e, LIFE);   // cult bosses: 1.5 s, then 30 s immune
            if (life <= 0) continue;
            Frozen f = new Frozen();
            f.e = e;
            f.pos = e.position();
            f.vel = e.getDeltaMovement();
            f.yRot = e.getYRot();
            f.xRot = e.getXRot();
            f.noGravity = e.isNoGravity();
            f.fire = e.getRemainingFireTicks();
            f.until = sl.getGameTime() + life;
            if (e instanceof Mob m) {
                f.noAi = m.isNoAi();
                m.setNoAi(true);
            }
            e.getPersistentData().putBoolean(KEY_AI, f.noAi);   // restored on load if the chunk unloads mid-freeze
            e.getPersistentData().putBoolean(KEY_NG, f.noGravity);
            e.setNoGravity(true);
            e.setDeltaMovement(Vec3.ZERO);
            FROZEN.put(e.getUUID(), f);
            if (e instanceof LivingEntity le && prisms++ < MAX_PRISMS) {   // a glass prism around each frozen creature
                double h = le.getBbHeight() + 0.3;
                f.prism = Fx.play(sl, Fx.fx("frozen_hour_prism").at(le.position()).yaw(le.getYRot()).scale(Math.max(0.5, h / 2.3))
                        .point("top", le.position().add(0, h, 0)).duration(life));
            }
        }
    }

    private static final int MAX_PRISMS = 16;

    private static void hold(Frozen f) {
        Entity e = f.e;
        if (e instanceof LivingEntity le) {
            if (Math.abs(e.getX() - f.pos.x) + Math.abs(e.getY() - f.pos.y) + Math.abs(e.getZ() - f.pos.z) > 0.05)
                HigherSpell.place(le, f.pos.x, f.pos.y, f.pos.z);
            if (e.tickCount % 10 == 0 && !ru.pohsmp.core.boss.BossGuard.isBoss(le))   // a boss is held by the freeze itself (its paralysis would count as control)
                le.addEffect(new MobEffectInstance(Reg.PARALYSIS.get(), 15, 0, false, false, false));
        } else {
            e.setPos(f.pos.x, f.pos.y, f.pos.z);
        }
        e.setDeltaMovement(Vec3.ZERO);
        e.setRemainingFireTicks(f.fire);
        if (e instanceof ItemEntity it) it.setPickUpDelay(10);
        if (e.tickCount % 8 == 0 && e.level() instanceof ServerLevel sl)
            DivineEvents.particle(sl, PALE, e.getX(), e.getY() + e.getBbHeight() * 0.5, e.getZ(), 1, e.getBbWidth() * 0.5, 0);
    }

    private static final String KEY_AI = "poh_fz_ai", KEY_NG = "poh_fz_ng";

    private static void free(Frozen f) {
        Entity e = f.e;
        if (f.prism >= 0 && e.level() instanceof ServerLevel sl && sl.getGameTime() < f.until - 4) Fx.stop(sl, f.prism, "");   // died or left early
        if (e instanceof Mob m) m.setNoAi(ru.pohsmp.core.boss.BossGuard.noAiAfterFreeze(m, f.noAi));   // a cult boss: as its own locks say
        e.setNoGravity(f.noGravity);
        e.getPersistentData().remove(KEY_AI);
        e.getPersistentData().remove(KEY_NG);
        if (e.isRemoved()) return;
        e.setDeltaMovement(f.vel);
        e.hurtMarked = true;
        if (e instanceof LivingEntity le && f.stored > 0 && f.last != null) {
            RELEASE.set(true);
            try {
                le.invulnerableTime = 0;
                le.hurt(f.last, f.stored);
            } finally {
                RELEASE.set(false);
            }
            if (e.level() instanceof ServerLevel sl) {
                DivineEvents.particle(sl, ParticleTypes.CRIT, e.getX(), e.getY() + 1, e.getZ(), 30, 0.5, 0.3);
                sl.playSound(null, e.getX(), e.getY(), e.getZ(), SoundEvents.PLAYER_ATTACK_CRIT, SoundSource.PLAYERS, 1.5f, 0.6f);
            }
        }
    }

    public static final class FrozenHourEvents {
        private FrozenHourEvents() {}

        @SubscribeEvent
        public static void onServerTick(TickEvent.ServerTickEvent e) {
            if (e.phase != TickEvent.Phase.END || FROZEN.isEmpty()) return;
            List<Frozen> done = new ArrayList<>();
            FROZEN.values().removeIf(f -> {
                if (f.e.isRemoved() || (f.e instanceof LivingEntity le && !le.isAlive()) || f.e.level().getGameTime() > f.until) {
                    done.add(f);
                    return true;
                }
                hold(f);
                return false;
            });
            boolean sound = false;
            for (Frozen f : done) {
                free(f);
                if (!sound && f.e.level() instanceof ServerLevel sl) {
                    sl.playSound(null, f.e.getX(), f.e.getY(), f.e.getZ(), SoundEvents.BELL_RESONATE, SoundSource.PLAYERS, 3f, 1.4f);
                    sound = true;
                }
            }
        }

        @SubscribeEvent(priority = EventPriority.HIGH)
        public static void onAttack(LivingAttackEvent e) {
            if (FROZEN.isEmpty() || RELEASE.get()) return;
            if (e.getSource().getEntity() != null && FROZEN.containsKey(e.getSource().getEntity().getUUID())) {   // the frozen do not act
                e.setCanceled(true);
                return;
            }
            Frozen f = FROZEN.get(e.getEntity().getUUID());
            if (f == null) return;
            e.setCanceled(true);
            f.stored += (float) (e.getAmount() * BONUS);
            f.last = e.getSource();
            if (e.getEntity().level() instanceof ServerLevel sl)
                DivineEvents.particle(sl, ParticleTypes.ENCHANTED_HIT, e.getEntity().getX(), e.getEntity().getY() + 1, e.getEntity().getZ(), 6, 0.3, 0.1);
        }

        @SubscribeEvent
        public static void onStopping(ServerStoppingEvent e) {
            for (Frozen f : FROZEN.values()) {
                if (f.e instanceof Mob m) m.setNoAi(f.noAi);
                f.e.setNoGravity(f.noGravity);
            }
            FROZEN.clear();
        }

        @SubscribeEvent
        public static void onJoin(net.minecraftforge.event.entity.EntityJoinLevelEvent e) {
            Entity en = e.getEntity();
            if (e.getLevel().isClientSide || !en.getPersistentData().contains(KEY_NG) || FROZEN.containsKey(en.getUUID())) return;
            if (en instanceof Mob m) m.setNoAi(en.getPersistentData().getBoolean(KEY_AI));
            en.setNoGravity(en.getPersistentData().getBoolean(KEY_NG));
            en.getPersistentData().remove(KEY_AI);
            en.getPersistentData().remove(KEY_NG);
        }
    }
}
