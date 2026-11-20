package ru.pohsmp.core.boss;

import io.redspace.ironsspellbooks.api.entity.IMagicEntity;
import io.redspace.ironsspellbooks.api.registry.SpellRegistry;
import io.redspace.ironsspellbooks.api.spells.AbstractSpell;
import io.redspace.ironsspellbooks.entity.mobs.abstract_spell_casting_mob.AbstractSpellCastingMob;
import io.redspace.ironsspellbooks.entity.mobs.goals.SpellBarrageGoal;
import io.redspace.ironsspellbooks.entity.mobs.wizards.fire_boss.FireBossEntity;
import io.redspace.ironsspellbooks.entity.spells.root.PreventDismount;
import java.lang.reflect.Field;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.WeakHashMap;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.tags.DamageTypeTags;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.damagesource.DamageTypes;
import net.minecraft.world.effect.MobEffect;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.AreaEffectCloud;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.OwnableEntity;
import net.minecraft.world.entity.ai.goal.GoalSelector;
import net.minecraft.world.entity.ai.goal.WrappedGoal;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.entity.projectile.AbstractArrow;
import net.minecraft.world.entity.projectile.Projectile;
import net.minecraft.world.entity.projectile.ThrownPotion;
import net.minecraft.world.level.ClipContext;
import net.minecraft.world.level.pathfinder.Path;
import net.minecraft.world.phys.HitResult;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.entity.EntityJoinLevelEvent;
import net.minecraftforge.event.entity.EntityMountEvent;
import net.minecraftforge.event.entity.living.LivingKnockBackEvent;
import net.minecraftforge.event.entity.living.MobEffectEvent;
import net.minecraftforge.eventbus.api.Event;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.util.ObfuscationReflectionHelper;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.Reg;

/**
 * Protection of the cult bosses against cheese and control (balance_bosses.md 1.2 / 1.3, keys in [bosses_common]): the damage
 * rules (range, line of sight, pillar, poisons, world hazards, hit cut, phase clamp) are applied by {@link BossCore#filterDamage},
 * the timed ones (recount of players, leash, regen, pillar watch, seal) by {@link BossCore#tick}; control and displacement through
 * the events below and the few hooks the spells call ({@link #holding}, {@link #frozenHourTicks}, {@link #immovable}...). Every
 * hook is a no-op for anything that is not a {@link PohBoss}.
 */
public final class BossGuard {
    private BossGuard() {}

    // ---------------------------------------------------------------- who

    /** The core of a cult boss, or null. */
    public static BossCore core(Entity e) {
        return e instanceof PohBoss b ? b.bossCore() : null;
    }

    public static boolean isBoss(Entity e) {
        return core(e) != null;
    }

    static boolean on() {
        return BossConfig.get(BossConfig.PROTECTION);
    }

    private static int secs(double s) {
        return (int) Math.round(s * 20);
    }

    /** Per-boss protection state (owned by BossCore, not saved except the counted players). */
    static final class State {
        final BossGuardMath.CcWindows cc = new BossGuardMath.CcWindows();
        BossGuardMath.PlayerCount count;
        long nextRecount;
        long lastDamage = -1;
        final Map<UUID, BossGuardMath.PillarWatch> pillar = new HashMap<>();
        final Set<UUID> onPillar = new HashSet<>();
        long mountUntil = -1;
        boolean tuned;
    }

    // ---------------------------------------------------------------- hooks for the spells (all: no-op on non-bosses)

    /**
     * A spell holding e in place (trap, roots...) asks every tick whether it may still hold it. On a boss the first call opens a
     * window of fullTicks × cc_duration_mult (≤ cc_max_seconds); then false and cc_immunity_seconds of immunity to that kind.
     * Never during a boss's scene.
     */
    public static boolean holding(LivingEntity e, String kind, int fullTicks) {
        BossCore c = core(e);
        if (c == null || !on()) return true;
        if (c.inScene()) return false;
        return cc(c, kind, fullTicks) > 0;
    }

    private static int cc(BossCore c, String kind, int ticks) {
        return c.guard.cc.allow(kind, c.mob.level().getGameTime(), ticks, BossConfig.get(BossConfig.CC_MULT),
                secs(BossConfig.get(BossConfig.CC_MAX_SECONDS)), secs(BossConfig.get(BossConfig.CC_IMMUNITY)));
    }

    /** «Застывший час»: how long this entity stays frozen (a boss: frozen_hour_seconds, then immune; 0 = not at all). */
    public static int frozenHourTicks(Entity e, int ticks) {
        BossCore c = core(e);
        if (c == null || !on()) return ticks;
        if (c.inScene()) return 0;
        int t = secs(BossConfig.get(BossConfig.FROZEN_HOUR_SECONDS));
        return c.guard.cc.allow("frozen_hour", c.mob.level().getGameTime(), ticks, 1, t, BossConfig.get(BossConfig.FROZEN_HOUR_IMMUNITY) * 20);
    }

    /** «Зеркальная тюрьма»: how long the cell holds this entity (a boss: mirror_prison_seconds; 0 = not at all). */
    public static int mirrorPrisonTicks(LivingEntity e, int ticks) {
        BossCore c = core(e);
        if (c == null || !on()) return ticks;
        if (c.inScene()) return 0;
        return c.guard.cc.allow("mirror_prison", c.mob.level().getGameTime(), ticks, 1, secs(BossConfig.get(BossConfig.MIRROR_PRISON_SECONDS)), 0);
    }

    /** What the AI of a boss should be after a freeze let it go (its own locks decide), or the saved value for anything else. */
    public static boolean noAiAfterFreeze(Mob m, boolean saved) {
        BossCore c = core(m);
        return c == null ? saved : c.aiLocked();
    }

    /** Displacement (teleports, swaps, banishment, pulls, pushes, knockback) does not work on it. */
    public static boolean immovable(Entity e) {
        BossCore c = core(e);
        return c != null && on() && BossConfig.get(BossConfig.DISPLACEMENT_IMMUNE);
    }

    /** Multiplier of the «% of the target's max health» part of our spells (a boss: percent_damage_mult). */
    public static double percentMult(LivingEntity e) {
        return isBoss(e) && on() ? BossConfig.get(BossConfig.PERCENT_DAMAGE_MULT) : 1;
    }

    /** «Обратный отсчёт»: the cap of the repeat as a share of max health (a boss: countdown_max_share). */
    public static double countdownShare(LivingEntity e, double normal) {
        return isBoss(e) && on() ? Math.min(normal, BossConfig.get(BossConfig.COUNTDOWN_MAX_SHARE)) : normal;
    }

    /** [barrier]: the share of max health a boss pressed against a shell loses per second (ours: barrier_push_share). */
    public static double barrierShare(LivingEntity e, double normal) {
        return isBoss(e) && on() ? BossConfig.get(BossConfig.BARRIER_PUSH_SHARE) : normal;
    }

    /** Illusions (T22) on a boss last × illusion_duration_mult (Ereb is immune by his own code). */
    public static double illusionMult(LivingEntity e) {
        return isBoss(e) && on() ? BossConfig.get(BossConfig.ILLUSION_DURATION_MULT) : 1;
    }

    private static final ThreadLocal<Boolean> DOT = ThreadLocal.withInitial(() -> false);

    /** Runs r with its damage counted as damage over time (bleeding...): × dot_mult on a boss. */
    public static void dot(Runnable r) {
        boolean was = DOT.get();
        DOT.set(true);
        try {
            r.run();
        } finally {
            DOT.set(was);
        }
    }

    // ---------------------------------------------------------------- damage (from BossCore.filterDamage)

    /** The protection rules for one hit on the boss; returns the damage left. */
    static float filter(BossCore c, DamageSource src, float amount) {
        if (amount <= 0 || !on()) return amount;
        Mob mob = c.mob;
        // world hazards: suffocation, drowning, falls, attacker-less fire (lava, fire blocks, burning)
        if (src.is(DamageTypes.IN_WALL) || src.is(DamageTypes.DROWN) || src.is(DamageTypeTags.IS_FALL) || src.is(DamageTypes.CRAMMING)) return 0;
        if (src.getEntity() == null && src.is(DamageTypeTags.IS_FIRE) && BossConfig.get(BossConfig.WORLD_FIRE_IMMUNE)) return 0;
        Entity direct = src.getDirectEntity(), attacker = src.getEntity();
        // its own hits on itself («Зеркальная тюрьма» turns them back)
        if (attacker == mob) amount *= BossConfig.get(BossConfig.MIRROR_PRISON_SELF);
        // poisons and the like
        boolean magic = src.is(DamageTypes.MAGIC) || src.is(DamageTypes.INDIRECT_MAGIC);
        boolean dot = DOT.get() || src.is(DamageTypes.WITHER)
                || magic && attacker == null && direct == null && mob.hasEffect(MobEffects.POISON);
        if (dot) amount *= BossConfig.get(BossConfig.DOT_MULT);
        else if (magic && (direct == null || direct instanceof ThrownPotion || direct instanceof AreaEffectCloud || direct instanceof AbstractArrow))
            amount *= BossConfig.get(BossConfig.HARMING_MULT);   // «Мгновенный урон»: drunk, splash, lingering, tipped arrows
        // where it was hit from
        if (attacker != null && attacker != mob && playerSide(attacker)) amount *= fromWhere(c, attacker, direct);
        // the big hit cut (Tyros does it himself in FireBossEntity.hurt)
        if (!(mob instanceof FireBossEntity))
            amount = BossGuardMath.hitCap(amount, mob.getMaxHealth(), BossConfig.get(BossConfig.HIT_CAP_SHARE), BossConfig.get(BossConfig.HIT_CAP_EXCESS));
        // no skipping a phase
        if (BossConfig.get(BossConfig.PHASE_CLAMP) && c.started() && !c.inFinale())
            amount = BossGuardMath.phaseClamp(mob.getHealth(), mob.getMaxHealth(), amount, c.def.phases, c.phase());
        return Math.max(0, amount);
    }

    /** A player, or a pet / summon owned by a player. */
    private static boolean playerSide(Entity e) {
        if (e instanceof Player) return true;
        return e instanceof OwnableEntity o && o.getOwner() instanceof Player;
    }

    /** Range, line of sight and pillar multipliers for a hit by attacker (direct: the projectile, if any). */
    private static double fromWhere(BossCore c, Entity attacker, Entity direct) {
        Mob mob = c.mob;
        Vec3 a = c.arena();
        double dx = attacker.getX() - a.x, dz = attacker.getZ() - a.z;
        double k = BossGuardMath.rangeMult(attacker.distanceTo(mob), Math.sqrt(dx * dx + dz * dz), c.arenaRadius(),
                BossConfig.get(BossConfig.ARENA_MARGIN), BossConfig.get(BossConfig.MAX_DAMAGE_DISTANCE), BossConfig.get(BossConfig.OUTSIDE_ARENA_MULT));
        if (k <= 0) return 0;
        Vec3 from = direct instanceof Projectile && direct != attacker ? LAUNCH.getOrDefault(direct, null) : null;
        if (from == null) from = attacker.getEyePosition();
        if (!sees(mob, from, attacker, direct)) k *= BossConfig.get(BossConfig.NO_LOS_MULT);
        if (c.guard.onPillar.contains(attacker.getUUID())) k *= BossConfig.get(BossConfig.PILLAR_MULT);
        return k;
    }

    /** A line from `from` to the boss's centre or eyes not blocked by colliding blocks. */
    private static boolean sees(Mob mob, Vec3 from, Entity attacker, Entity direct) {
        Entity by = direct != null ? direct : attacker;
        for (Vec3 to : new Vec3[] {mob.getBoundingBox().getCenter(), mob.getEyePosition()}) {
            if (from.distanceToSqr(to) < 1e-4) return true;
            HitResult r = mob.level().clip(new ClipContext(from, to, ClipContext.Block.COLLIDER, ClipContext.Fluid.NONE, by));
            if (r.getType() == HitResult.Type.MISS) return true;
        }
        return false;
    }

    /** Where each live projectile was launched (line of sight is checked from there, balance 1.3). */
    private static final Map<Entity, Vec3> LAUNCH = new WeakHashMap<>();

    // ---------------------------------------------------------------- tick (from BossCore.tick, server, fight started)

    static void tick(BossCore c, PohBoss boss) {
        if (!on()) return;
        Mob mob = c.mob;
        ServerLevel sl = (ServerLevel) mob.level();
        long now = sl.getGameTime();
        State g = c.guard;
        if (!g.tuned) {
            g.tuned = true;
            tuneRaiseHell(c);
        }
        // «Печать»: its Iron's casts are cut while sealed
        if (mob.hasEffect(Reg.SEAL.get()) && mob instanceof AbstractSpellCastingMob m && m.isCasting()) m.cancelCast();
        // Iron's roots / ice tombs (also «Ледяные гробницы», «Хватающий сад»): let go at the end of the window
        if (mob.getVehicle() instanceof PreventDismount && (now >= g.mountUntil || c.inScene())) mob.stopRiding();
        if (c.inFinale()) return;
        recount(c, now);
        if (mob.tickCount % 10 == 0) pillars(c, now);
        if (mob.tickCount % 10 == 5 && !c.locked() && !c.inScene()) leash(c, boss);
        if (mob.tickCount % 20 == 0) regen(c, now);
    }

    /** Players are counted again every recount_seconds: up at once, down only after count_drop_delay_seconds; % health kept. */
    private static void recount(BossCore c, long now) {
        State g = c.guard;
        if (g.count == null || now < g.nextRecount) return;
        g.nextRecount = now + BossConfig.get(BossConfig.RECOUNT_SECONDS) * 20L;
        int before = g.count.get();
        int n = g.count.update(c.countPlayers(), now, BossConfig.get(BossConfig.COUNT_DROP_DELAY) * 20L, BossConfig.get(BossConfig.MAX_COUNTED));
        if (n != before) c.rescale(n);
    }

    /** «Столб»: who stands high above the boss where it cannot walk. */
    private static void pillars(BossCore c, long now) {
        State g = c.guard;
        Mob mob = c.mob;
        long need = BossConfig.get(BossConfig.PILLAR_SECONDS) * 20L;
        double h = BossConfig.get(BossConfig.PILLAR_HEIGHT);
        Set<UUID> seen = new HashSet<>();
        for (ServerPlayer p : c.fighters()) {
            seen.add(p.getUUID());
            boolean high = p.getY() - mob.getY() > h;
            boolean unreachable = false;
            if (high) {
                Path path = mob.getNavigation().createPath(p, 0);
                unreachable = path == null || !path.canReach() || path.getEndNode() != null && path.getEndNode().y < p.getBlockY() - h / 2;
            }
            boolean on = g.pillar.computeIfAbsent(p.getUUID(), k -> new BossGuardMath.PillarWatch()).update(high, unreachable, now, need);
            if (on) g.onPillar.add(p.getUUID());
            else g.onPillar.remove(p.getUUID());
        }
        g.pillar.keySet().retainAll(seen);
        g.onPillar.retainAll(seen);
    }

    /** Kited out of the arena: back to the spawn point with the appear fx, +leash_heal_share of max health. */
    private static void leash(BossCore c, PohBoss boss) {
        Mob mob = c.mob;
        Vec3 a = c.arena();
        if (!BossGuardMath.leashed(mob.getX() - a.x, mob.getZ() - a.z, c.arenaRadius(), BossConfig.get(BossConfig.LEASH_EXTRA))) return;
        Vec3 from = mob.position();
        if (mob.isPassenger()) mob.stopRiding();
        mob.getNavigation().stop();
        mob.setDeltaMovement(Vec3.ZERO);
        mob.teleportTo(a.x, a.y, a.z);
        mob.fallDistance = 0;
        mob.setHealth(Math.min(mob.getMaxHealth(), mob.getHealth() + (float) (BossConfig.get(BossConfig.LEASH_HEAL) * mob.getMaxHealth())));
        c.lock(20, true, false);   // 1 s to come back
        boss.onBossLeash(from);
        PohCore.LOG.info("[boss] {} leashed back to its arena from {}", c.def.id, from);
    }

    /** The default leash look: smoke where it was, its appear fx (or portal sparks) where it comes back. */
    static void leashFx(BossCore c, Vec3 from) {
        if (!(c.mob.level() instanceof ServerLevel sl)) return;
        Mob mob = c.mob;
        sl.sendParticles(ParticleTypes.LARGE_SMOKE, from.x, from.y + 1, from.z, 30, 0.4, 0.8, 0.4, 0.02);
        String id = c.def.id + "_appear";
        if (ru.pohsmp.core.fx.FxLib.fx(id) != null)
            ru.pohsmp.core.fx.Fx.play(sl, ru.pohsmp.core.fx.Fx.fx(id).caster(mob).at(mob.position()).yaw(mob.getYRot()));
        else sl.sendParticles(ParticleTypes.REVERSE_PORTAL, mob.getX(), mob.getY() + 1, mob.getZ(), 60, 0.5, 1.0, 0.5, 0.05);
        sl.playSound(null, mob.getX(), mob.getY(), mob.getZ(), SoundEvents.ENDERMAN_TELEPORT, SoundSource.HOSTILE, 1.5f, 0.6f);
    }

    /** 20 s without damage: 1 %/s, never above the start of the current phase. */
    private static void regen(BossCore c, long now) {
        Mob mob = c.mob;
        long since = now - Math.max(c.guard.lastDamage, c.fightStart());
        float r = BossGuardMath.regen(mob.getHealth(), mob.getMaxHealth(), BossConfig.get(BossConfig.REGEN_SHARE), since,
                BossConfig.get(BossConfig.REGEN_DELAY) * 20L, c.def.phases, c.phase());
        if (r > 0) mob.setHealth(mob.getHealth() + r);
    }

    // ---------------------------------------------------------------- Raise Hell of the Head of the Cult (Tyros's goal)

    private static Field barrageSpell;

    /** [cult_leader] raise_hell_level / _cd_min / _cd_max: Tyros's Raise Hell goal is replaced by one with these numbers. */
    private static void tuneRaiseHell(BossCore c) {
        if (!(c.mob instanceof FireBossEntity fb) || !"cult_leader".equals(c.def.id)) return;
        try {
            GoalSelector gs = ObfuscationReflectionHelper.getPrivateValue(net.minecraft.world.entity.Mob.class, fb, "f_21345_");
            AbstractSpell raise = SpellRegistry.RAISE_HELL_SPELL.get();
            if (barrageSpell == null) {
                barrageSpell = SpellBarrageGoal.class.getDeclaredField("spell");
                barrageSpell.setAccessible(true);
            }
            for (WrappedGoal w : new ArrayList<>(gs.getAvailableGoals())) {
                if (!(w.getGoal() instanceof SpellBarrageGoal g) || barrageSpell.get(g) != raise) continue;
                int lvl = BossConfig.get(BossConfig.CL_RAISE_HELL_LEVEL), min = BossConfig.get(BossConfig.CL_RAISE_HELL_MIN),
                        max = Math.max(min, BossConfig.get(BossConfig.CL_RAISE_HELL_MAX));
                gs.removeGoal(g);
                gs.addGoal(w.getPriority(), new SpellBarrageGoal((IMagicEntity) fb, raise, lvl, lvl, min, max, 1));
                PohCore.LOG.info("[boss] cult_leader: Raise Hell level {}, every {}-{} ticks", lvl, min, max);
            }
        } catch (ReflectiveOperationException | RuntimeException e) {
            PohCore.LOG.warn("[boss] cult_leader: Raise Hell not tuned ({})", e.toString());
        }
    }

    // ---------------------------------------------------------------- events

    /** Our control effects: paralysis (stuns, «Ударная волна», «Фантомная ловушка»), sleep («Колыбель»), exhaustion. */
    private static String ccKind(MobEffect e) {
        if (e == Reg.PARALYSIS.get()) return "paralysis";
        if (e == Reg.NIGHTMARE.get()) return "sleep";
        if (e == Reg.SPENT.get()) return "spent";
        return null;
    }

    private static final ThreadLocal<Boolean> REAPPLY = ThreadLocal.withInitial(() -> false);

    public static final class Events {
        private Events() {}

        /** Control effects: shortened (deny + the same effect again for the allowed time); displacement effects denied. */
        @SubscribeEvent(priority = EventPriority.HIGH)
        public static void onEffect(MobEffectEvent.Applicable e) {
            BossCore c = core(e.getEntity());
            if (c == null || REAPPLY.get() || !on() || e.getEntity().level().isClientSide) return;
            MobEffectInstance i = e.getEffectInstance();
            MobEffect eff = i.getEffect();
            if (eff == Reg.TOSS.get() || eff == MobEffects.LEVITATION) {   // «Метка ветра», levitation: throws it around
                if (BossConfig.get(BossConfig.DISPLACEMENT_IMMUNE)) e.setResult(Event.Result.DENY);
                return;
            }
            String kind = ccKind(eff);
            int ticks;
            if (kind != null) {
                ticks = c.inScene() ? 0 : cc(c, kind, i.getDuration());
            } else if (eff == Reg.SEAL.get()) {
                ticks = c.inScene() ? 0 : c.guard.cc.allow("seal", c.mob.level().getGameTime(), i.getDuration(), 1,
                        secs(BossConfig.get(BossConfig.SEAL_SECONDS)), 0);
            } else return;
            e.setResult(Event.Result.DENY);
            if (ticks <= 0) return;
            LivingEntity le = e.getEntity();
            REAPPLY.set(true);
            try {
                le.addEffect(new MobEffectInstance(eff, ticks, i.getAmplifier(), i.isAmbient(), i.isVisible(), i.showIcon()));
            } finally {
                REAPPLY.set(false);
            }
        }

        /** Iron's roots and ice tombs (they hold by riding): a control window, then immunity. */
        @SubscribeEvent
        public static void onMount(EntityMountEvent e) {
            if (!e.isMounting() || !(e.getEntityBeingMounted() instanceof PreventDismount)) return;
            BossCore c = core(e.getEntityMounting());
            if (c == null || !on() || e.getLevel().isClientSide) return;
            String kind = e.getEntityBeingMounted().getClass().getSimpleName();
            int ticks = c.inScene() ? 0 : cc(c, kind, holdTicks(e.getEntityBeingMounted()));
            if (ticks <= 0) {
                e.setCanceled(true);
                return;
            }
            c.guard.mountUntil = c.mob.level().getGameTime() + ticks;
        }

        @SubscribeEvent
        public static void onKnockback(LivingKnockBackEvent e) {
            if (immovable(e.getEntity())) e.setCanceled(true);
        }

        @SubscribeEvent
        public static void onJoin(EntityJoinLevelEvent e) {
            if (!e.getLevel().isClientSide && e.getEntity() instanceof Projectile p && !e.loadedFromDisk()) LAUNCH.put(p, p.position());
        }
    }

    /** How long an Iron's root / ice tomb would hold (its private duration / lifetime), 8 s if unknown. */
    private static int holdTicks(Entity holder) {
        for (String f : new String[] {"duration", "lifetime", "lifetimeDuration"}) {
            for (Class<?> k = holder.getClass(); k != null && k != Entity.class; k = k.getSuperclass()) {
                try {
                    Field fd = k.getDeclaredField(f);
                    if (fd.getType() != int.class) continue;
                    fd.setAccessible(true);
                    int v = fd.getInt(holder);
                    if (v > 0) return v;
                } catch (ReflectiveOperationException | RuntimeException ignored) {
                    // next name
                }
            }
        }
        return 160;
    }
}
