package ru.pohsmp.core.trophy;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import net.minecraft.core.particles.DustParticleOptions;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.tags.DamageTypeTags;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.damagesource.DamageTypes;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.AnvilUpdateEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.living.LivingDamageEvent;
import net.minecraftforge.event.entity.living.LivingHurtEvent;
import net.minecraftforge.event.entity.living.LivingKnockBackEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import org.joml.Vector3f;
import ru.pohsmp.core.boss.BossGuard;
import ru.pohsmp.core.illusion.Copies;

/**
 * T35: full-set bonuses and the mantle / mask (numbers: {@link TrophyConfig}). Boss fights: the cult bosses are never made to lose their
 * target (Traitor's invisibility, the Mask's double), keep part of their knockback on the Smith (bossKnockback), and everything the
 * wearer does to a boss (tempered weapon, the jealous threads) is a player hit that goes through {@link BossGuard}'s filter as usual.
 */
public final class TrophyEvents {
    private TrophyEvents() {}

    private static final EquipmentSlot[] ARMOR = {EquipmentSlot.HEAD, EquipmentSlot.CHEST, EquipmentSlot.LEGS, EquipmentSlot.FEET};
    static final TrophyMath.Cooldowns CD = new TrophyMath.Cooldowns();
    private static final Map<UUID, Long> STAND_UNTIL = new HashMap<>();
    private static final Map<UUID, Vec3> LAST_POS = new HashMap<>();
    private static final Map<UUID, Decoy> DECOYS = new HashMap<>();
    private static final ThreadLocal<Boolean> REFLECTING = ThreadLocal.withInitial(() -> false);

    private record Decoy(LivingEntity owner, Vec3 pos, long until) {}

    /** The set whose four pieces the entity wears, or null. */
    public static TrophySet fullSet(LivingEntity e) {
        if (e == null) return null;
        String id = TrophyMath.fullSetOf(i -> {
            TrophySet s = TrophyArmor.setOf(e.getItemBySlot(ARMOR[i]));
            return s == null ? null : s.id;
        });
        return id == null ? null : TrophySet.byId(id);
    }

    private static long now(Entity e) {
        return e.level().getGameTime();
    }

    private static String key(Entity e, String what) {
        return e.getUUID() + ":" + what;
    }

    // ---------------------------------------------------------------- hits

    @SubscribeEvent
    public static void onHurt(LivingHurtEvent e) {
        LivingEntity t = e.getEntity();
        if (t.level().isClientSide) return;
        DamageSource src = e.getSource();
        // Smith's Plate: the wearer's weapon is tempered (melee hits only)
        if (src.getEntity() instanceof LivingEntity a && src.getDirectEntity() == a
                && (src.is(DamageTypes.PLAYER_ATTACK) || src.is(DamageTypes.MOB_ATTACK)) && fullSet(a) == TrophySet.SMITH)
            e.setAmount(TrophyMath.tempered(e.getAmount(), TrophyConfig.get(TrophyConfig.SMITH_WEAPON)));
        // Cult Head's Mantle: fire and lava of the world burn less
        if (src.is(DamageTypeTags.IS_FIRE) && src.getEntity() == null && TrophyCurios.wears(t, Trophies.mantle()))
            e.setAmount((float) (e.getAmount() * TrophyConfig.get(TrophyConfig.MANTLE_WORLD_FIRE)));
    }

    @SubscribeEvent(priority = EventPriority.LOW)
    public static void onDamage(LivingDamageEvent e) {
        LivingEntity t = e.getEntity();
        if (!(t.level() instanceof ServerLevel sl) || e.getAmount() <= 0) return;
        long now = now(t);
        TrophySet set = fullSet(t);
        // Warlord's Armor: «Стоять насмерть»
        if (set == TrophySet.WARLORD) {
            Long until = STAND_UNTIL.get(t.getUUID());
            boolean active = until != null && now < until;
            if (!active && TrophyMath.standFast(t.getHealth(), e.getAmount(), t.getMaxHealth(), TrophyConfig.get(TrophyConfig.WARLORD_THRESHOLD))
                    && CD.tryUse(key(t, "warlord"), now, TrophyConfig.get(TrophyConfig.WARLORD_COOLDOWN))) {
                STAND_UNTIL.put(t.getUUID(), now + TrophyConfig.get(TrophyConfig.WARLORD_TICKS));
                active = true;
                sl.playSound(null, t.getX(), t.getY(), t.getZ(), SoundEvents.ANVIL_LAND, SoundSource.PLAYERS, 0.8f, 0.7f);
                sl.sendParticles(ParticleTypes.TOTEM_OF_UNDYING, t.getX(), t.getY() + 1, t.getZ(), 30, 0.5, 0.8, 0.5, 0.2);
            }
            if (active) e.setAmount((float) (e.getAmount() * TrophyConfig.get(TrophyConfig.WARLORD_CUT)));
        }
        // Jealous Attire: the threads give part of the hit back to the attacker
        if (set == TrophySet.JEALOUS && !REFLECTING.get() && e.getSource().getEntity() instanceof LivingEntity a && a != t && a.isAlive()) {
            float back = TrophyMath.reflect(e.getAmount(), TrophyConfig.get(TrophyConfig.REFLECT_SHARE), TrophyConfig.get(TrophyConfig.REFLECT_CAP));
            if (back > 0) {
                REFLECTING.set(true);
                try {
                    a.hurt(t.damageSources().thorns(t), back);
                } finally {
                    REFLECTING.set(false);
                }
                thread(sl, t, a, TrophySet.JEALOUS.color);
            }
        }
        // Mask of Lies: a double stays behind
        if (TrophyCurios.wears(t, Trophies.mask())
                && TrophyMath.decoy(t.getRandom().nextDouble(), TrophyConfig.get(TrophyConfig.MASK_CHANCE), e.getAmount(), CD.ready(key(t, "mask"), now))) {
            CD.tryUse(key(t, "mask"), now, TrophyConfig.get(TrophyConfig.MASK_COOLDOWN));
            decoy(sl, t, now);
        }
    }

    /** A red thread from the wearer to the attacker. */
    private static void thread(ServerLevel sl, LivingEntity from, LivingEntity to, int color) {
        DustParticleOptions dust = new DustParticleOptions(new Vector3f((color >> 16 & 255) / 255f, (color >> 8 & 255) / 255f, (color & 255) / 255f), 0.8f);
        Vec3 a = from.position().add(0, from.getBbHeight() * 0.6, 0), b = to.position().add(0, to.getBbHeight() * 0.6, 0);
        int n = (int) Math.min(40, Math.max(4, a.distanceTo(b) * 4));
        for (int i = 0; i <= n; i++) {
            Vec3 p = a.lerp(b, i / (double) n);
            sl.sendParticles(dust, p.x, p.y, p.z, 1, 0, 0, 0, 0);
        }
    }

    /** The double: a false copy of the wearer where it stood (seen by the players around), the mobs hunting it go there instead. */
    private static void decoy(ServerLevel sl, LivingEntity t, long now) {
        int ticks = TrophyConfig.get(TrophyConfig.MASK_TICKS);
        List<ServerPlayer> see = new java.util.ArrayList<>();
        for (ServerPlayer p : sl.players()) if (p != t && !p.isSpectator() && p.distanceToSqr(t) < 48 * 48) see.add(p);
        Copies.Copy c = Copies.spawn(t, Copies.Mode.RUNNER, t.position(), Vec3.ZERO, ticks, 1, 0, see);
        c.ghost = true;   // strikes pass through it; it is only bait
        DECOYS.put(t.getUUID(), new Decoy(t, t.position(), now + ticks));
        sl.playSound(null, t.getX(), t.getY(), t.getZ(), SoundEvents.ILLUSIONER_MIRROR_MOVE, SoundSource.PLAYERS, 1f, 1.2f);
        sl.sendParticles(new DustParticleOptions(new Vector3f(0.91f, 0.76f, 0.35f), 1f), t.getX(), t.getY() + 1, t.getZ(), 20, 0.3, 0.6, 0.3, 0);
        lure(sl, t, t.position());
    }

    /** Mobs (not cult bosses) that hunt the owner lose it and walk to pos. */
    private static void lure(ServerLevel sl, LivingEntity owner, Vec3 pos) {
        double r = TrophyConfig.get(TrophyConfig.MASK_RADIUS);
        for (Mob m : sl.getEntitiesOfClass(Mob.class, owner.getBoundingBox().inflate(r), m -> m.getTarget() == owner && !BossGuard.isBoss(m))) {
            m.setTarget(null);
            m.getNavigation().moveTo(pos.x, pos.y, pos.z, 1.1);
        }
    }

    /** Mobs (not cult bosses) that hunt the wearer forget it (Traitor's invisibility). */
    private static void forget(ServerLevel sl, LivingEntity owner, double r) {
        for (Mob m : sl.getEntitiesOfClass(Mob.class, owner.getBoundingBox().inflate(r), m -> m.getTarget() == owner && !BossGuard.isBoss(m)))
            m.setTarget(null);
    }

    @SubscribeEvent(priority = EventPriority.LOW)
    public static void onKnockback(LivingKnockBackEvent e) {
        LivingEntity t = e.getEntity();
        if (t.level().isClientSide || fullSet(t) != TrophySet.SMITH) return;
        LivingEntity by = t.getLastHurtByMob();
        boolean boss = by != null && BossGuard.isBoss(by) && t.tickCount - t.getLastHurtByMobTimestamp() <= 1;
        if (!boss) e.setCanceled(true);
        else e.setStrength((float) (e.getStrength() * TrophyConfig.get(TrophyConfig.SMITH_BOSS_KNOCKBACK)));
    }

    // ---------------------------------------------------------------- every tick

    @SubscribeEvent
    public static void onPlayerTick(TickEvent.PlayerTickEvent e) {
        if (e.phase != TickEvent.Phase.END || !(e.player.level() instanceof ServerLevel sl)) return;
        Player p = e.player;
        long now = now(p);
        TrophySet set = fullSet(p);
        Vec3 pos = p.position(), last = LAST_POS.put(p.getUUID(), pos);
        if (set != null && TrophyConfig.get(TrophyConfig.SET_PARTICLES) && p.tickCount % 10 == 0 && !p.isInvisible()) {
            int c = set.color;
            sl.sendParticles(new DustParticleOptions(new Vector3f((c >> 16 & 255) / 255f, (c >> 8 & 255) / 255f, (c & 255) / 255f), 0.7f),
                    p.getX(), p.getY() + 1.0, p.getZ(), 2, 0.35, 0.5, 0.35, 0);
        }
        if (set == TrophySet.WARLORD && p.tickCount % 20 == 0) aura(sl, p);
        if (set == TrophySet.TRAITOR && last != null && !p.isPassenger() && !p.isFallFlying() && p.hurtTime == 0
                && TrophyMath.dash(pos.x - last.x, pos.z - last.z, TrophyConfig.get(TrophyConfig.DASH_MIN), TrophyConfig.get(TrophyConfig.DASH_MAX))
                && CD.tryUse(key(p, "traitor"), now, TrophyConfig.get(TrophyConfig.TRAITOR_COOLDOWN))) {
            p.addEffect(new MobEffectInstance(MobEffects.INVISIBILITY, TrophyConfig.get(TrophyConfig.TRAITOR_TICKS), 0, false, false, true));
            forget(sl, p, 24);
            sl.sendParticles(ParticleTypes.SMOKE, p.getX(), p.getY() + 1, p.getZ(), 15, 0.3, 0.6, 0.3, 0.02);
            sl.playSound(null, p.getX(), p.getY(), p.getZ(), SoundEvents.ILLUSIONER_PREPARE_BLINDNESS, SoundSource.PLAYERS, 0.6f, 1.5f);
        }
        // the mantle sheds ash on the run
        if (p.isSprinting() && last != null && pos.distanceToSqr(last) > 0.01 && p.tickCount % 3 == 0 && TrophyCurios.wears(p, Trophies.mantle()))
            sl.sendParticles(ParticleTypes.ASH, p.getX(), p.getY() + 1.2, p.getZ(), 6, 0.3, 0.4, 0.3, 0.01);
        Decoy d = DECOYS.get(p.getUUID());
        if (d != null) {
            if (now >= d.until()) DECOYS.remove(p.getUUID());
            else lure(sl, p, d.pos());
        }
        if (p.tickCount % 1200 == 0) {
            CD.prune(now);
            STAND_UNTIL.values().removeIf(u -> u <= now);
        }
    }

    /** Warlord: Resistance I to the allied players around (team mates; everybody if the wearer is in no team). */
    private static void aura(ServerLevel sl, Player w) {
        double r = TrophyConfig.get(TrophyConfig.WARLORD_RADIUS);
        if (r <= 0) return;
        for (ServerPlayer o : sl.players()) {
            if (o == w || o.isSpectator() || o.distanceToSqr(w) > r * r) continue;
            if (w.getTeam() != null && !w.isAlliedTo(o)) continue;
            MobEffectInstance had = o.getEffect(MobEffects.DAMAGE_RESISTANCE);
            if (had != null && (had.getAmplifier() > 0 || had.getDuration() > 60)) continue;   // a stronger / longer one is kept
            o.addEffect(new MobEffectInstance(MobEffects.DAMAGE_RESISTANCE, 50, 0, true, true, true));
        }
    }

    // ---------------------------------------------------------------- the spells inside the mantle and the mask (owner 21.11)

    /**
     * Iron's builds the spell wheel (client and server) from the hands, the armor slots and the Curios "spellbook" slot only; the mantle
     * ("back") and the mask ("head") add their spell here, level 3, locked. Taken off - the next rebuild has no such option.
     */
    @SubscribeEvent
    public static void onSpellWheel(io.redspace.ironsspellbooks.api.magic.SpellSelectionManager.SpellSelectionEvent e) {
        if (!TrophyCurios.ON) return;   // armor-slot fallback: Iron's reads the stack's own container
        for (TrophyWear w : Trophies.wearables()) {
            if (!TrophyCurios.inCurio(e.getEntity(), w)) continue;
            var spell = w.spell();
            if (spell != null)
                e.addSelectionOption(new io.redspace.ironsspellbooks.api.spells.SpellData(spell, TrophyWear.SPELL_LEVEL, true), "pohsmp_" + w.kind.id, 0);
        }
    }

    // ---------------------------------------------------------------- no anvil repair

    @SubscribeEvent
    public static void onAnvil(AnvilUpdateEvent e) {
        if (!TrophyConfig.get(TrophyConfig.NO_ANVIL)) return;
        boolean ours = e.getLeft().getItem() instanceof TrophyArmor || e.getLeft().getItem() instanceof TrophyWear;
        if (ours && e.getRight().is(e.getLeft().getItem())) e.setCanceled(true);
    }

    // ---------------------------------------------------------------- cleanup

    @SubscribeEvent
    public static void onLogout(PlayerEvent.PlayerLoggedOutEvent e) {
        UUID id = e.getEntity().getUUID();
        LAST_POS.remove(id);
        DECOYS.remove(id);
        STAND_UNTIL.remove(id);
    }

    @SubscribeEvent
    public static void onDimension(PlayerEvent.PlayerChangedDimensionEvent e) {
        LAST_POS.remove(e.getEntity().getUUID());
        DECOYS.remove(e.getEntity().getUUID());
    }

    @SubscribeEvent
    public static void onRespawn(PlayerEvent.PlayerRespawnEvent e) {
        LAST_POS.remove(e.getEntity().getUUID());
    }

    @SubscribeEvent
    public static void onStopping(ServerStoppingEvent e) {
        LAST_POS.clear();
        DECOYS.clear();
        STAND_UNTIL.clear();
        CD.clear("");
    }

}
