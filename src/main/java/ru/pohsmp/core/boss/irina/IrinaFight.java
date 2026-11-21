package ru.pohsmp.core.boss.irina;

import io.redspace.ironsspellbooks.api.events.SpellPreCastEvent;
import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.util.Utils;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.CopyOnWriteArrayList;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.util.Mth;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.damagesource.DamageType;
import net.minecraft.world.effect.MobEffect;
import net.minecraft.world.effect.MobEffectCategory;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.ai.attributes.AttributeModifier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.entity.living.LivingAttackEvent;
import net.minecraftforge.event.entity.living.LivingDamageEvent;
import net.minecraftforge.event.entity.living.LivingEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.boss.BossConfig;
import ru.pohsmp.core.boss.BossCore;
import ru.pohsmp.core.boss.BossNet;
import ru.pohsmp.core.boss.BossTimeline;
import ru.pohsmp.core.fx.Fx;

/**
 * The fight of T27 (server). Her own chase and staff hook, the «Нитяной укол» at range; phase 1 «Зависть» (the mark of jealousy on
 * the top damage, everyone else ×0.5, she hunts the marked one), phase 2 «Красные нити» (pairs: the damage of one is shared with
 * the other, apart > 12 the thread snaps), phase 3 «Ярость ревности» (stealing good effects, the whip of threads round her); the
 * specials «Чужое счастье» (66%) and «Только мой» (15%) with their scenes (the fight is not frozen); her four spells «Ревнивый
 * взгляд», «Узлы», «Подмена любимого», «Марионетка». No line or beam goes from her to anyone; every strong attack has a visible
 * warning. Numbers: [irina] of pohsmp_core-bosses-server.toml ({@link IrinaConfig}).
 */
public final class IrinaFight {
    private static final UUID HUNT_ID = UUID.fromString("5b2e8c71-0d4f-4a3e-8b6c-1f9a7e2d3c41");
    /** Fights in progress (normally 0 or 1), for the event handlers. */
    private static final List<IrinaFight> LIVE = new CopyOnWriteArrayList<>();
    /** Set while the share of a bonded player's damage is being dealt to the partner (no ping-pong). */
    private static boolean sharing;
    /** Set while the cocoon crushes its victim (the cocoon itself lets that damage through). */
    private static boolean crushing;

    private final IrinaEntity boss;
    private final BossCore core;

    // phase 1: the mark
    private UUID marked;
    private int markFx = -1, markIn = 60;

    // phase 2: bonds
    private static final class Bond {
        UUID a, b;
        int fxA = -1, fxB = -1, num, reformIn, strainCd;
        boolean snapped;
    }

    private final List<Bond> bonds = new ArrayList<>();
    private int reshuffleIn = -1, bondCounter;

    // phase 3
    private int furyFx = -1, stealIn = -1, whipIn = -1;

    // own attacks
    private final Map<String, Integer> cooldown = new HashMap<>();
    private int gcd = 100, meleeIn = 20, boltIn = 60;
    private final Map<UUID, Integer> gaze = new HashMap<>();

    private static final class Knot {
        Vec3 at;
        int fx, life;
    }

    private final List<Knot> knots = new ArrayList<>();

    // «Марионетка»
    private UUID puppet;
    private int puppetLeft, puppetFx = -1;
    private double puppetDamage;

    // «Только мой»
    private UUID cocoon;
    private Vec3 cocoonAt;
    private double cocoonHp;
    private int cocoonFx = -1;
    private boolean cocoonOver;
    private BossTimeline mineScript;

    IrinaFight(IrinaEntity boss) {
        this.boss = boss;
        this.core = boss.bossCore();
    }

    private static double cfg(net.minecraftforge.common.ForgeConfigSpec.DoubleValue v) {
        return BossConfig.get(v);
    }

    private static int cfg(net.minecraftforge.common.ForgeConfigSpec.IntValue v) {
        return BossConfig.get(v);
    }

    private static MutableComponent ui(String key, Object... args) {
        return Component.translatable("ui.pohsmp_core.irina." + key, args).withStyle(s -> s.withColor(Irina.COLOR));
    }

    private ServerLevel sl() {
        return (ServerLevel) boss.level();
    }

    private ServerPlayer player(UUID u) {
        if (u == null) return null;
        ServerPlayer p = sl().getServer().getPlayerList().getPlayer(u);
        return p != null && p.isAlive() && p.level() == boss.level() ? p : null;
    }

    /** Her damage types: pohsmp_core:irina_threads / irina_cocoon (through armour, data/pohsmp_core/damage_type), else boss_mechanic. */
    private DamageSource source(String type) {
        ServerLevel sl = sl();
        ResourceKey<DamageType> k = ResourceKey.create(Registries.DAMAGE_TYPE, new ResourceLocation(PohCore.MODID, type));
        return sl.registryAccess().registryOrThrow(Registries.DAMAGE_TYPE).getHolder(k).map(h -> new DamageSource(h, boss))
                .orElseGet(core::mechanicDamage);
    }

    private static boolean isThreads(DamageSource src) {
        return src.typeHolder().unwrapKey().map(k -> k.location().getNamespace().equals(PohCore.MODID)
                && (k.location().getPath().equals("irina_threads") || k.location().getPath().equals("irina_cocoon"))).orElse(false);
    }

    private void hit(LivingEntity e, double dmg) {
        e.hurt(core.attackDamage(), (float) dmg);
    }

    // ---------------------------------------------------------------- damage to her (from IrinaEntity.hurt)

    /** Before the framework: the mark of phase 1 — everyone but the marked one deals ×mark_damage_mult. */
    float incoming(DamageSource src, float amount) {
        boolean markOn = core.phase() == IrinaMath.ENVY && marked != null;
        boolean byMarked = src.getEntity() != null && src.getEntity().getUUID().equals(marked);
        return IrinaMath.markFilter(amount, markOn, byMarked, cfg(IrinaConfig.MARK_DAMAGE_MULT));
    }

    /** After the damage went in: the others' damage counts to free the puppet. */
    void onDamaged(DamageSource src, float amount) {
        if (puppet != null && src.getEntity() instanceof Player p && !p.getUUID().equals(puppet)) puppetDamage += amount;
    }

    // ---------------------------------------------------------------- tick

    void tick(ServerLevel sl) {
        if (!LIVE.contains(this)) LIVE.add(this);
        if (!core.started() || core.inFinale()) return;
        int phase = core.phase();
        if (phase == IrinaMath.ENVY) tickMark(sl);
        if (phase == IrinaMath.THREADS) tickBonds(sl);
        tickKnots(sl);
        tickPuppet(sl);
        tickCocoon(sl);
        tickGaze();
        cooldown.replaceAll((k, v) -> Math.max(0, v - 1));
        if (meleeIn > 0) meleeIn--;
        if (boltIn > 0) boltIn--;
        if (stealIn > 0) stealIn--;
        if (whipIn > 0) whipIn--;
        if (core.locked() || core.inScene() || boss.isNoAi()) return;
        LivingEntity t = target();
        boss.setTarget(t);
        hunt(t != null && phase == IrinaMath.ENVY && t.getUUID().equals(marked));
        if (t == null) return;
        boss.getLookControl().setLookAt(t, 30, 30);
        double d = boss.distanceTo(t);
        double reach = cfg(IrinaConfig.MELEE_REACH);
        if (d > reach * 0.8) {
            if (boss.tickCount % 5 == 0) boss.getNavigation().moveTo(t, 1.0);
        } else boss.getNavigation().stop();
        if (gcd > 0) gcd--;
        else if (castSpell(sl, t)) {
            gcd = cfg(BossConfig.ABILITY_GCD) * 20;
            return;
        } else gcd = 10;
        if (d <= reach && meleeIn <= 0) staff(sl, t);
        else if (d > 5 && d < 32 && boltIn <= 0 && boss.hasLineOfSight(t)) bolt(sl, t);
    }

    /** Phase 1: the marked one while it is in the fight; else the current target if it is a fighter; else the nearest fighter. */
    private LivingEntity target() {
        List<ServerPlayer> fighters = fightersNow();
        if (core.phase() == IrinaMath.ENVY) {
            ServerPlayer m = player(marked);
            if (m != null && fighters.contains(m)) return m;
        }
        if (boss.getTarget() instanceof ServerPlayer p && fighters.contains(p) && !p.getUUID().equals(cocoon)) return p;
        return fighters.stream().filter(p -> !p.getUUID().equals(cocoon)).min(Comparator.comparingDouble(p -> p.distanceToSqr(boss))).orElse(null);
    }

    private List<ServerPlayer> fightersNow() {
        List<ServerPlayer> out = core.playersNear(core.arenaRadius() + 16);
        out.removeIf(Player::isCreative);
        return out;
    }

    private void hunt(boolean on) {
        var speed = boss.getAttribute(Attributes.MOVEMENT_SPEED);
        if (speed == null) return;
        boolean has = speed.getModifier(HUNT_ID) != null;
        if (on && !has)
            speed.addTransientModifier(new AttributeModifier(HUNT_ID, "irina_hunt", cfg(IrinaConfig.HUNT_SPEED_MULT) - 1, AttributeModifier.Operation.MULTIPLY_TOTAL));
        else if (!on && has) speed.removeModifier(HUNT_ID);
    }

    private float yawTo(Vec3 p) {
        return (float) (Mth.atan2(p.z - boss.getZ(), p.x - boss.getX()) * Mth.RAD_TO_DEG) - 90;
    }

    private void face(Vec3 p) {
        float yaw = yawTo(p);
        boss.setYRot(yaw);
        boss.setYHeadRot(yaw);
        boss.setYBodyRot(yaw);
    }

    static Vec3 ground(ServerLevel sl, Vec3 p) {
        int y = sl.getHeight(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES, Mth.floor(p.x), Mth.floor(p.z));
        return Math.abs(y - p.y) <= 6 ? new Vec3(p.x, y, p.z) : p;
    }

    /** Living things she may hurt near p (horizontal radius r): not her, not creative / spectators. */
    private List<LivingEntity> targets(ServerLevel sl, Vec3 p, double r) {
        List<LivingEntity> out = new ArrayList<>();
        for (LivingEntity e : sl.getEntitiesOfClass(LivingEntity.class, new AABB(p, p).inflate(r, 8, r))) {
            if (e == boss || !e.isAlive()) continue;
            if (e instanceof Player pl && (pl.isCreative() || pl.isSpectator())) continue;
            if (e.distanceToSqr(p.x, e.getY(), p.z) > r * r) continue;
            out.add(e);
        }
        return out;
    }

    // ---------------------------------------------------------------- base attacks

    /** The staff hook (1.2 s, hit 0.55): attack_damage to the target if it is still in reach. */
    private void staff(ServerLevel sl, LivingEntity t) {
        meleeIn = cfg(IrinaConfig.MELEE_INTERVAL);
        face(t.position());
        core.lock(IrinaMath.STAFF, true, false);
        boss.serverTriggerAnimation("irina_staff_attack");
        core.play(new BossTimeline("staff", IrinaMath.STAFF_HIT + 1).at(IrinaMath.STAFF_HIT, () -> {
            core.sound("irina.staff", 1.5f, 1.1f);
            if (t.isAlive() && boss.isAlive() && boss.distanceTo(t) <= cfg(IrinaConfig.MELEE_REACH) + 0.8)
                hit(t, boss.getAttributeValue(Attributes.ATTACK_DAMAGE));
        }));
    }

    /** «Нитяной укол» (balance thread_bolt): a knot appears under the target, 0.8 s later threads stab up there — step aside. */
    private void bolt(ServerLevel sl, LivingEntity t) {
        boltIn = cfg(IrinaConfig.THREAD_BOLT_INTERVAL);
        boss.serverTriggerAnimation("irina_cast_short");
        Vec3 at = ground(sl, t.position());
        Fx.play(sl, Fx.fx("irina_knot_trap").at(at).duration(IrinaMath.BOLT_WARN + 4));
        core.play(new BossTimeline("bolt", IrinaMath.BOLT_WARN + 1).at(IrinaMath.BOLT_WARN, () -> {
            Fx.play(sl, Fx.fx("irina_yank").at(at));
            core.sound(at, "irina.snare", 1.2f, 1.2f);
            for (LivingEntity e : targets(sl, at, IrinaMath.BOLT_RADIUS))
                if (Math.abs(e.getY() - at.y) < 2.5) hit(e, cfg(IrinaConfig.THREAD_BOLT_DAMAGE));
        }));
    }

    // ---------------------------------------------------------------- phases

    void onPhase(int from, int to) {
        ServerLevel sl = sl();
        if (to >= IrinaMath.THREADS) clearMark(sl);
        if (to == IrinaMath.THREADS) {
            core.actionbar(core.arenaRadius() + 8, ui("phase2"));
            if (!BossConfig.get(BossConfig.SPECIALS)) {   // no «Чужое счастье»: the short transition and the pairs at once
                Fx.play(sl, Fx.fx("irina_phase2").caster(boss).at(boss.position()).yaw(boss.getYRot()));
                boss.serverTriggerAnimation("irina_phase2");
                core.sound("irina.phase", 3, 1);
                core.play(new BossTimeline("phase2", IrinaMath.PHASE2).then(() -> formBonds(sl)));
            }
        }
        if (to == IrinaMath.FURY) phase3(sl);
    }

    private void phase3(ServerLevel sl) {
        clearBonds(sl);
        core.setPulse(false);
        boss.setFury(true);
        core.actionbar(core.arenaRadius() + 8, ui("phase3"));
        core.sound("irina.phase", 4, 0.9f);
        if (!core.locked()) boss.serverTriggerAnimation("irina_phase3");
        Fx.play(sl, Fx.fx("irina_phase3").caster(boss).at(boss.position()).yaw(boss.getYRot()));
        core.play(new BossTimeline("phase3", IrinaMath.PHASE3_FURY + 1).at(IrinaMath.PHASE3_FURY, () -> {
            if (furyFx < 0 && boss.isAlive()) furyFx = Fx.play(sl, Fx.fx("irina_fury").caster(boss).at(boss.position()).attach(boss));
        }));
        stealIn = 100;
        whipIn = 60;
    }

    // ---------------------------------------------------------------- phase 1: «Предмет ревности»

    private void tickMark(ServerLevel sl) {
        ServerPlayer m = player(marked);
        if (marked != null && (m == null || !fightersNow().contains(m))) {
            clearMark(sl);
            markIn = Math.min(markIn, 20);
        }
        if (m != null && boss.tickCount % 20 == 0) m.addEffect(new MobEffectInstance(Irina.JEALOUSY_MARK.get(), 60, 0, false, false, true));
        if (--markIn > 0) return;
        markIn = cfg(IrinaConfig.MARK_REASSIGN) * 20;
        ServerPlayer top = core.strongestEnemy();
        if (top != null && !top.getUUID().equals(marked)) setMark(sl, top);
    }

    private void setMark(ServerLevel sl, ServerPlayer p) {
        clearMark(sl);
        marked = p.getUUID();
        Fx.play(sl, Fx.fx("irina_mark_apply").caster(p).at(p.position()).attach(p));
        markFx = Fx.play(sl, Fx.fx("irina_mark").caster(p).at(p.position()).attach(p));
        p.addEffect(new MobEffectInstance(Irina.JEALOUSY_MARK.get(), 60, 0, false, false, true));
        p.displayClientMessage(ui("mark_self"), true);
        for (ServerPlayer o : fightersNow()) if (o != p) o.displayClientMessage(ui("mark_others", p.getDisplayName()), true);
        core.sysLine(core.playersNear(core.arenaRadius() + 8), "ui.pohsmp_core.irina.mark", p.getName().getString());
        core.sound("irina.mark", 2, 1);
        if (!core.locked() && !core.inScene()) {
            face(p.position());
            boss.serverTriggerAnimation("irina_mark");
        }
    }

    private void clearMark(ServerLevel sl) {
        if (markFx > 0) Fx.stop(sl, markFx, "");
        markFx = -1;
        ServerPlayer old = player(marked);
        if (old != null) old.removeEffect(Irina.JEALOUSY_MARK.get());
        marked = null;
        hunt(false);
    }

    // ---------------------------------------------------------------- phase 2: «Красные нити»

    private void formBonds(ServerLevel sl) {
        clearBonds(sl);
        if (core.phase() != IrinaMath.THREADS || !boss.isAlive()) return;
        List<UUID> ids = new ArrayList<>();
        for (ServerPlayer p : fightersNow()) ids.add(p.getUUID());
        for (List<UUID> pair : IrinaMath.pairs(ids, boss.getRandom().nextLong())) {
            Bond b = new Bond();
            b.a = pair.get(0);
            b.b = pair.get(1);
            b.num = bondCounter++ % 4 + 1;
            bonds.add(b);
            link(sl, b);
        }
        reshuffleIn = cfg(IrinaConfig.BOND_RESHUFFLE) * 20;
        core.setPulse(!bonds.isEmpty());
        if (!bonds.isEmpty()) {
            core.sound("irina.bind", 3, 1);
            if (!core.locked() && !core.inScene()) {
                core.lock(IrinaMath.BIND, true, false);
                boss.serverTriggerAnimation("irina_bind");
            }
        }
    }

    /** Threads on both of a pair (the same sign over both heads, no line between them). */
    private void link(ServerLevel sl, Bond b) {
        ServerPlayer a = player(b.a), c = player(b.b);
        if (a == null || c == null) return;
        b.snapped = false;
        b.fxA = Fx.play(sl, Fx.fx("irina_bond_" + b.num).caster(a).at(a.position()).attach(a));
        b.fxB = Fx.play(sl, Fx.fx("irina_bond_" + b.num).caster(c).at(c.position()).attach(c));
        int dur = (cfg(IrinaConfig.BOND_RESHUFFLE) + 5) * 20;
        a.addEffect(new MobEffectInstance(Irina.THREAD_BOND.get(), dur, 0, false, false, true));
        c.addEffect(new MobEffectInstance(Irina.THREAD_BOND.get(), dur, 0, false, false, true));
        core.sysLine(List.of(a), "ui.pohsmp_core.irina.bond", c.getName().getString());
        core.sysLine(List.of(c), "ui.pohsmp_core.irina.bond", a.getName().getString());
    }

    private void unlink(ServerLevel sl, Bond b) {
        if (b.fxA > 0) Fx.stop(sl, b.fxA, "");
        if (b.fxB > 0) Fx.stop(sl, b.fxB, "");
        b.fxA = b.fxB = -1;
        for (UUID u : new UUID[] {b.a, b.b}) {
            ServerPlayer p = player(u);
            if (p != null) p.removeEffect(Irina.THREAD_BOND.get());
        }
    }

    private void clearBonds(ServerLevel sl) {
        for (Bond b : bonds) unlink(sl, b);
        bonds.clear();
        reshuffleIn = -1;
    }

    private void tickBonds(ServerLevel sl) {
        if (reshuffleIn > 0 && --reshuffleIn == 0) formBonds(sl);
        double breakAt = cfg(IrinaConfig.BOND_BREAK_DISTANCE);
        for (int i = 0; i < bonds.size(); i++) {
            Bond b = bonds.get(i);
            ServerPlayer a = player(b.a), c = player(b.b);
            if (a == null || c == null) {   // one left / died: the thread is gone
                unlink(sl, b);
                bonds.remove(i--);
                continue;
            }
            if (b.snapped) {
                if (b.reformIn > 0 && --b.reformIn == 0) link(sl, b);
                continue;
            }
            if (b.strainCd > 0) b.strainCd--;
            int st = IrinaMath.bondState(a.distanceTo(c), breakAt);
            if (st == 1 && b.strainCd == 0) {
                b.strainCd = 20;
                Fx.play(sl, Fx.fx("irina_bond_strain").caster(a).at(a.position()).attach(a));
                Fx.play(sl, Fx.fx("irina_bond_strain").caster(c).at(c.position()).attach(c));
                a.displayClientMessage(ui("bond_strain", c.getDisplayName()), true);
                c.displayClientMessage(ui("bond_strain", a.getDisplayName()), true);
            } else if (st == 2) snap(sl, b, a, c);
        }
        core.setPulse(!bonds.isEmpty());
    }

    /** Apart farther than bond_break_distance: the thread snaps, both lose bond_snap_share of their max health (through armour). */
    private void snap(ServerLevel sl, Bond b, ServerPlayer a, ServerPlayer c) {
        unlink(sl, b);
        b.snapped = true;
        b.reformIn = Math.max(1, cfg(IrinaConfig.BOND_REFORM) * 20);
        double share = cfg(IrinaConfig.BOND_SNAP_SHARE);
        for (ServerPlayer p : new ServerPlayer[] {a, c}) {
            Fx.play(sl, Fx.fx("irina_bond_snap").caster(p).at(p.position()));
            p.displayClientMessage(ui("bond_snap"), true);
            p.invulnerableTime = 0;
            p.hurt(source("irina_threads"), (float) (p.getMaxHealth() * share));
            core.sound(p.position(), "irina.snap", 2, 1);
        }
    }

    private Bond bondOf(UUID u) {
        for (Bond b : bonds) if (!b.snapped && (u.equals(b.a) || u.equals(b.b))) return b;
        return null;
    }

    /** The damage of a bonded player: bond_share of it goes to the partner (after armour; as threads, through the partner's armour). */
    void onPlayerDamage(LivingDamageEvent e, ServerPlayer p) {
        if (sharing || core.phase() != IrinaMath.THREADS || isThreads(e.getSource())) return;
        Bond b = bondOf(p.getUUID());
        if (b == null) return;
        ServerPlayer partner = player(p.getUUID().equals(b.a) ? b.b : b.a);
        if (partner == null || partner.isCreative() || partner.isSpectator()) return;
        float[] s = IrinaMath.split(e.getAmount(), cfg(IrinaConfig.BOND_SHARE));
        if (s[1] <= 0) return;
        e.setAmount(s[0]);
        sharing = true;
        try {
            partner.invulnerableTime = 0;
            partner.hurt(source("irina_threads"), s[1]);
        } finally {
            sharing = false;
        }
        Fx.play(sl(), Fx.fx("irina_bond_share").caster(partner).at(partner.position()).attach(partner));
    }

    // ---------------------------------------------------------------- phase 3: steal and whip (in castSpell)

    private static boolean stealable(MobEffectInstance i) {
        MobEffect e = i.getEffect();
        return e.getCategory() == MobEffectCategory.BENEFICIAL && e != MobEffects.INVISIBILITY;
    }

    /** Takes up to max good effects off p (strongest first), into pool (the highest level and the type). Returns their names. */
    private List<Component> take(ServerPlayer p, int max, Map<MobEffect, Integer> pool) {
        List<MobEffectInstance> good = new ArrayList<>();
        for (MobEffectInstance i : p.getActiveEffects()) if (stealable(i)) good.add(i);
        good.sort(Comparator.comparingInt(MobEffectInstance::getAmplifier).reversed());
        List<Component> names = new ArrayList<>();
        for (int k = 0; k < Math.min(max, good.size()); k++) {
            MobEffectInstance i = good.get(k);
            pool.merge(i.getEffect(), i.getAmplifier(), Math::max);
            names.add(i.getEffect().getDisplayName());
            p.removeEffect(i.getEffect());
        }
        return names;
    }

    /** The stolen effects on her: stolen levels capped (resistance lower), for seconds. */
    private void wear(Map<MobEffect, Integer> pool, int seconds) {
        for (var en : pool.entrySet()) {
            boolean res = en.getKey() == MobEffects.DAMAGE_RESISTANCE;
            int amp = IrinaMath.stolenAmplifier(en.getValue(), res, cfg(IrinaConfig.STOLEN_MAX_AMP), cfg(IrinaConfig.STOLEN_RESISTANCE_MAX));
            boss.addEffect(new MobEffectInstance(en.getKey(), seconds * 20, amp, false, true, false));
        }
    }

    private static Component list(List<Component> names) {
        MutableComponent c = Component.empty();
        for (int i = 0; i < names.size(); i++) {
            if (i > 0) c.append(", ");
            c.append(names.get(i));
        }
        return c;
    }

    /** Phase 3: every steal_interval the steal_targets nearest lose steal_per_target good effects; she wears them steal_seconds. */
    private boolean steal(ServerLevel sl) {
        List<ServerPlayer> near = new ArrayList<>(fightersNow());
        near.removeIf(p -> p.getActiveEffects().stream().noneMatch(IrinaFight::stealable) || p.distanceTo(boss) > 24);
        if (near.isEmpty()) return false;
        near.sort(Comparator.comparingDouble(p -> p.distanceToSqr(boss)));
        List<ServerPlayer> who = near.subList(0, Math.min(cfg(IrinaConfig.STEAL_TARGETS), near.size()));
        List<ServerPlayer> victims = new ArrayList<>(who);
        core.lock(IrinaMath.STEAL, true, false);
        boss.serverTriggerAnimation("irina_steal");
        core.play(new BossTimeline("steal", IrinaMath.STEAL_ABSORB + 1)
                .at(IrinaMath.STEAL_PULL, () -> {
                    for (ServerPlayer p : victims) if (p.isAlive()) Fx.play(sl, Fx.fx("irina_steal_lose").caster(p).at(p.position()).attach(p));
                })
                .at(IrinaMath.STEAL_ABSORB, () -> {
                    Map<MobEffect, Integer> pool = new HashMap<>();
                    int secs = cfg(IrinaConfig.STEAL_SECONDS);
                    for (ServerPlayer p : victims) {
                        if (!p.isAlive()) continue;
                        List<Component> names = take(p, cfg(IrinaConfig.STEAL_PER_TARGET), pool);
                        if (names.isEmpty()) continue;
                        p.displayClientMessage(ui("steal", list(names)), true);
                        p.addEffect(new MobEffectInstance(Irina.STOLEN_HAPPINESS.get(), secs * 20, 0, false, false, true));
                    }
                    wear(pool, secs);
                    Fx.play(sl, Fx.fx("irina_steal_gather").caster(boss).at(boss.position()));
                    core.sound("irina.steal", 3, 1);
                }));
        return true;
    }

    /** Phase 3: the whip of threads — warning ring 0.8 s, then whip_damage + slowness II in the ring 1.5–7 round her. */
    private void whip(ServerLevel sl) {
        core.lock(IrinaMath.WHIP, true, false);
        Vec3 o = boss.position();
        float yaw = boss.getYRot();
        Fx.play(sl, Fx.fx("irina_whip_warn").caster(boss).at(o).yaw(yaw));
        core.actionbar(14, ui("whip_warn"));
        core.play(new BossTimeline("whip", IrinaMath.WHIP)
                .at(IrinaMath.WHIP_WARN, () -> {
                    boss.serverTriggerAnimation("irina_whip");
                    Fx.play(sl, Fx.fx("irina_whip").caster(boss).at(boss.position()).yaw(yaw));
                })
                .at(IrinaMath.WHIP_LASH, () -> {
                    core.sound("irina.whip", 3, 1);
                    Vec3 c = boss.position();
                    for (LivingEntity e : targets(sl, c, IrinaMath.WHIP_OUT + 0.5)) {
                        double d = Math.sqrt(e.distanceToSqr(c.x, e.getY(), c.z));
                        if (!IrinaMath.whipHits(d) || Math.abs(e.getY() - c.y) > 3) continue;
                        hit(e, cfg(IrinaConfig.WHIP_DAMAGE));
                        e.addEffect(new MobEffectInstance(MobEffects.MOVEMENT_SLOWDOWN, cfg(IrinaConfig.WHIP_SLOW_SECONDS) * 20, 1));
                    }
                }));
    }

    // ---------------------------------------------------------------- her spells (one at a time, gcd between)

    private boolean ready(String id) {
        return cooldown.getOrDefault(id, 0) <= 0;
    }

    private boolean castSpell(ServerLevel sl, LivingEntity t) {
        if (cocoon != null) return false;
        List<ServerPlayer> fighters = fightersNow();
        if (core.phase() == IrinaMath.FURY) {
            if (whipIn <= 0) {
                Vec3 c = boss.position();
                boolean someone = fighters.stream().anyMatch(p -> IrinaMath.whipHits(Math.sqrt(p.distanceToSqr(c.x, p.getY(), c.z))));
                if (someone) {
                    whip(sl);
                    whipIn = cfg(IrinaConfig.WHIP_COOLDOWN) * 20;
                    return true;
                }
            }
            if (stealIn <= 0) {
                stealIn = cfg(IrinaConfig.STEAL_INTERVAL) * 20;
                if (steal(sl)) return true;
            }
        }
        List<String> can = new ArrayList<>();
        if (ready("gaze") && gaze.values().stream().anyMatch(v -> IrinaMath.gazeCaught(v, cfg(IrinaConfig.GAZE_SECONDS)))) can.add("gaze");
        if (ready("knots") && !fighters.isEmpty()) can.add("knots");
        if (ready("swap") && fighters.size() >= 2) can.add("swap");
        if (ready("puppet") && puppet == null && !fighters.isEmpty()) can.add("puppet");
        if (can.isEmpty()) return false;
        String id = can.contains("gaze") ? "gaze" : can.get(boss.getRandom().nextInt(can.size()));   // a caught gaze first
        switch (id) {
            case "gaze" -> {
                gazeSpell(sl);
                cooldown.put("gaze", cfg(IrinaConfig.GAZE_COOLDOWN) * 20);
            }
            case "knots" -> {
                knotsSpell(sl, fighters);
                cooldown.put("knots", cfg(IrinaConfig.KNOTS_COOLDOWN) * 20);
            }
            case "swap" -> {
                swapSpell(sl, fighters);
                cooldown.put("swap", cfg(IrinaConfig.SWAP_COOLDOWN) * 20);
            }
            default -> {
                puppetSpell(sl, fighters);
                cooldown.put("puppet", cfg(IrinaConfig.PUPPET_COOLDOWN) * 20);
            }
        }
        return true;
    }

    // ---- «Ревнивый взгляд»

    /** Who looks at her (eyes within gaze_angle of her chest, line of sight, within 32): ticks of looking. */
    private void tickGaze() {
        Vec3 chest = boss.position().add(0, boss.getBbHeight() * 0.7, 0);
        double cone = cfg(IrinaConfig.GAZE_ANGLE);
        Set<UUID> seen = new HashSet<>();
        for (ServerPlayer p : fightersNow()) {
            seen.add(p.getUUID());
            Vec3 look = p.getViewVector(1), to = chest.subtract(p.getEyePosition());
            double angle = to.lengthSqr() > 32 * 32 || !p.hasLineOfSight(boss) ? 180 : IrinaMath.angleDeg(look.x, look.y, look.z, to.x, to.y, to.z);
            gaze.put(p.getUUID(), IrinaMath.gazeTick(gaze.getOrDefault(p.getUUID(), 0), angle, cone));
        }
        gaze.keySet().retainAll(seen);
    }

    private void gazeSpell(ServerLevel sl) {
        core.lock(IrinaMath.GAZE, true, false);
        boss.serverTriggerAnimation("irina_gaze");
        Fx.play(sl, Fx.fx("irina_gaze_cast").caster(boss).at(boss.position()).yaw(boss.getYRot()));
        core.play(new BossTimeline("gaze", IrinaMath.GAZE_AT + 1).at(IrinaMath.GAZE_AT, () -> {
            core.sound("irina.gaze", 2, 1);
            int secs = cfg(IrinaConfig.GAZE_SLOW_SECONDS);
            for (ServerPlayer p : fightersNow()) {
                if (!IrinaMath.gazeCaught(gaze.getOrDefault(p.getUUID(), 0), cfg(IrinaConfig.GAZE_SECONDS))) continue;
                p.addEffect(new MobEffectInstance(Irina.JEALOUS_GAZE.get(), secs * 20, cfg(IrinaConfig.GAZE_SLOW_AMP), false, false, true));
                Fx.play(sl, Fx.fx("irina_gaze_mark").caster(p).at(p.position()).attach(p).duration(secs * 20));
                p.displayClientMessage(ui("gaze"), true);
            }
            gaze.clear();
        }));
    }

    // ---- «Узлы»

    private void knotsSpell(ServerLevel sl, List<ServerPlayer> fighters) {
        int n = IrinaMath.knotCount(fighters.size(), cfg(IrinaConfig.KNOTS_BASE), cfg(IrinaConfig.KNOTS_MAX));
        core.lock(IrinaMath.KNOTS, true, false);
        boss.serverTriggerAnimation("irina_knots");
        Fx.play(sl, Fx.fx("irina_knots_cast").caster(boss).at(boss.position()).yaw(boss.getYRot()));
        List<ServerPlayer> around = new ArrayList<>(fighters);
        core.play(new BossTimeline("knots", IrinaMath.KNOTS_AT + 1).at(IrinaMath.KNOTS_AT, () -> {
            core.sound("irina.knots", 2, 1);
            int life = cfg(IrinaConfig.KNOT_LIFE) * 20;
            for (int i = 0; i < n; i++) {
                ServerPlayer p = around.get(i % around.size());
                double a = boss.getRandom().nextDouble() * Math.PI * 2, d = 1.5 + boss.getRandom().nextDouble() * 2.5;
                Knot k = new Knot();
                k.at = ground(sl, p.position().add(Math.cos(a) * d, 0, Math.sin(a) * d));
                k.life = life;
                k.fx = Fx.play(sl, Fx.fx("irina_knot_trap").at(k.at).duration(life));
                knots.add(k);
            }
            core.actionbar(core.arenaRadius() + 8, ui("knots_warn"));
        }));
    }

    private void tickKnots(ServerLevel sl) {
        for (int i = 0; i < knots.size(); i++) {
            Knot k = knots.get(i);
            if (--k.life <= 0) {
                Fx.stop(sl, k.fx, "");
                knots.remove(i--);
                continue;
            }
            for (ServerPlayer p : fightersNow()) {
                if (p.distanceToSqr(k.at.x, p.getY(), k.at.z) > IrinaMath.KNOT_RADIUS * IrinaMath.KNOT_RADIUS || Math.abs(p.getY() - k.at.y) > 1.5) continue;
                Fx.stop(sl, k.fx, "");
                int snare = cfg(IrinaConfig.KNOT_SNARE) * 20;
                Fx.play(sl, Fx.fx("irina_knot_snare").caster(p).at(p.position()).attach(p).duration(snare));
                p.addEffect(new MobEffectInstance(Irina.THREAD_SNARE.get(), snare, 0, false, false, true));
                hit(p, cfg(IrinaConfig.KNOT_DAMAGE));
                p.displayClientMessage(ui("snared"), true);
                core.sound(k.at, "irina.snare", 1.5f, 1);
                knots.remove(i--);
                break;
            }
        }
        for (ServerPlayer p : fightersNow())   // held in place: no jumping out of a snare either
            if (p.hasEffect(Irina.THREAD_SNARE.get()) && p.getDeltaMovement().y > 0) {
                p.setDeltaMovement(0, Math.min(0, p.getDeltaMovement().y), 0);
                p.hurtMarked = true;
            }
    }

    // ---- «Подмена любимого»

    private void swapSpell(ServerLevel sl, List<ServerPlayer> fighters) {
        List<ServerPlayer> l = new ArrayList<>(fighters);
        l.removeIf(p -> p.getUUID().equals(cocoon));
        if (l.size() < 2) return;
        Collections.shuffle(l, new java.util.Random(boss.getRandom().nextLong()));
        ServerPlayer a = l.get(0), b = l.get(1);
        core.lock(IrinaMath.SWAP, true, false);
        boss.serverTriggerAnimation("irina_swap");
        core.play(new BossTimeline("swap", IrinaMath.SWAP_AT + 1).at(IrinaMath.SWAP_AT, () -> {
            if (!a.isAlive() || !b.isAlive() || a.level() != sl || b.level() != sl) return;
            Vec3 pa = a.position(), pb = b.position();
            Fx.play(sl, Fx.fx("irina_swap").caster(a).at(pa));
            Fx.play(sl, Fx.fx("irina_swap").caster(b).at(pb));
            a.teleportTo(sl, pb.x, pb.y, pb.z, a.getYRot(), a.getXRot());
            b.teleportTo(sl, pa.x, pa.y, pa.z, b.getYRot(), b.getXRot());
            Fx.play(sl, Fx.fx("irina_swap").caster(a).at(pb));
            Fx.play(sl, Fx.fx("irina_swap").caster(b).at(pa));
            int nausea = cfg(IrinaConfig.SWAP_NAUSEA) * 20;
            if (nausea > 0) {
                a.addEffect(new MobEffectInstance(MobEffects.CONFUSION, nausea + 40, 0));   // nausea needs a little more to show
                b.addEffect(new MobEffectInstance(MobEffects.CONFUSION, nausea + 40, 0));
            }
            a.displayClientMessage(ui("swap", b.getDisplayName()), true);
            b.displayClientMessage(ui("swap", a.getDisplayName()), true);
            core.sound(pa, "irina.swap", 2, 1);
            core.sound(pb, "irina.swap", 2, 1);
        }));
    }

    // ---- «Марионетка»

    private void puppetSpell(ServerLevel sl, List<ServerPlayer> fighters) {
        List<ServerPlayer> l = new ArrayList<>(fighters);
        l.removeIf(p -> p.getUUID().equals(cocoon));
        if (l.isEmpty()) return;
        ServerPlayer v = l.get(boss.getRandom().nextInt(l.size()));
        face(v.position());
        core.lock(IrinaMath.PUPPET, true, false);
        boss.serverTriggerAnimation("irina_puppet");
        core.play(new BossTimeline("puppet", IrinaMath.PUPPET_AT + 1).at(IrinaMath.PUPPET_AT, () -> {
            if (!v.isAlive() || v.level() != sl) return;
            int ticks = cfg(IrinaConfig.PUPPET_SECONDS) * 20;
            puppet = v.getUUID();
            puppetLeft = ticks;
            puppetDamage = 0;
            v.addEffect(new MobEffectInstance(Irina.MARIONETTE.get(), ticks, 0, false, false, true));
            puppetFx = Fx.play(sl, Fx.fx("irina_puppet").caster(v).at(v.position()).attach(v).duration(ticks));
            v.displayClientMessage(ui("puppet_self"), true);
            for (ServerPlayer o : fightersNow()) if (o != v) o.displayClientMessage(ui("puppet", v.getDisplayName()), true);
            core.sound(v.position(), "irina.puppet", 2, 1);
            boss.serverTriggerAnimation("irina_puppet_hold");
            if (MagicData.getPlayerMagicData(v).isCasting()) Utils.serverSideCancelCast(v);
        }));
    }

    /** The puppet walks to her (its own legs do nothing: speed −100%), until the time is up or the others hurt her enough. */
    private void tickPuppet(ServerLevel sl) {
        if (puppet == null) return;
        ServerPlayer v = player(puppet);
        boolean broken = IrinaMath.puppetBroken(puppetDamage, boss.getMaxHealth(), cfg(IrinaConfig.PUPPET_BREAK_SHARE));
        if (v == null || --puppetLeft <= 0 || broken) {
            endPuppet(sl, v, broken);
            return;
        }
        Vec3 to = boss.position().subtract(v.position()).multiply(1, 0, 1);
        if (to.lengthSqr() < 2.5 * 2.5) return;
        double speed = 0.216 * cfg(IrinaConfig.PUPPET_WALK_MULT);   // a walk is ≈ 4.3 blocks/s
        Vec3 step = to.normalize().scale(speed);
        v.setDeltaMovement(step.x, v.getDeltaMovement().y, step.z);
        v.hurtMarked = true;
    }

    private void endPuppet(ServerLevel sl, ServerPlayer v, boolean broken) {
        if (puppetFx > 0) Fx.stop(sl, puppetFx, "");
        puppetFx = -1;
        if (v != null) {
            v.removeEffect(Irina.MARIONETTE.get());
            if (broken) {
                Fx.play(sl, Fx.fx("irina_puppet_break").caster(v).at(v.position()));
                for (ServerPlayer o : fightersNow()) o.displayClientMessage(ui("puppet_break"), true);
            }
        }
        puppet = null;
        if (boss.isAlive()) boss.serverTriggerAnimation("-");
    }

    // ---------------------------------------------------------------- specials

    /** Returns false while it cannot start (another scene / attack is on): the core asks again next tick. */
    boolean special(String id) {
        if (core.inScene() || core.locked() || cocoon != null) return false;
        if (id.equals("happiness")) happiness(sl());
        else if (id.equals("only_mine")) onlyMine(sl());
        return true;
    }

    /**
     * «Чужое счастье» (66%, 6 s): the sigil r24, every good effect of everyone in happiness_radius is taken (spread 1.4 s), gathered
     * to her as golden sparks (from all around, not from the players) and worn by her for stolen_seconds (absorb 5.2 s); then the pairs.
     */
    private void happiness(ServerLevel sl) {
        clearMark(sl);
        core.lock(IrinaMath.HAPPY, true, false);
        boss.getNavigation().stop();
        boss.serverTriggerAnimation("irina_others_happiness");
        Vec3 c = boss.position();
        Fx.play(sl, Fx.fx("irina_others_happiness").caster(boss).at(c).yaw(boss.getYRot()));
        core.sound("irina.happiness", 4, 1);
        core.actionbar(core.arenaRadius() + 8, ui("happiness_warn"));
        List<ServerPlayer> who = core.scene("irina.happiness", IrinaMath.HAPPY, BossNet.SCENE_BARS, BossConfig.get(BossConfig.SCENE_RADIUS), c, boss.getYRot(), -1);
        Map<MobEffect, Integer> pool = new HashMap<>();
        core.play(new BossTimeline("scene:happiness", IrinaMath.HAPPY)
                .at(IrinaMath.HAPPY_TITLE, () -> core.title(who, "irina_happiness", IrinaMath.HAPPY_TITLE_HOLD, null))
                .at(IrinaMath.HAPPY_SPREAD, () -> {
                    double r = cfg(IrinaConfig.HAPPINESS_RADIUS);
                    int secs = cfg(IrinaConfig.STOLEN_SECONDS);
                    for (ServerPlayer p : core.playersNear(r + 2)) {
                        if (p.isCreative() || p.distanceToSqr(c.x, p.getY(), c.z) > r * r) continue;
                        Fx.play(sl, Fx.fx("irina_steal_lose").caster(p).at(p.position()).attach(p));
                        List<Component> names = take(p, Integer.MAX_VALUE, pool);
                        if (names.isEmpty()) continue;
                        p.displayClientMessage(ui("steal", list(names)), true);
                        p.addEffect(new MobEffectInstance(Irina.STOLEN_HAPPINESS.get(), secs * 20, 0, false, false, true));
                    }
                })
                .at(IrinaMath.HAPPY_ABSORB, () -> {
                    wear(pool, cfg(IrinaConfig.STOLEN_SECONDS));
                    core.sound("irina.steal", 4, 1);
                })
                .then(() -> formBonds(sl)));
    }

    /**
     * «Только мой» (15%, 6.2 s): the strongest enemy (most damage in 30 s) is yanked 2 blocks before her into a cocoon of threads
     * for cocoon_seconds; the allies tear it with damage (hits on the victim go to the cocoon); not torn — cocoon_crush_share of the
     * victim's max health (through armour; if that kills, it is her finisher).
     */
    private void onlyMine(ServerLevel sl) {
        ServerPlayer v = core.strongestEnemy();
        if (v == null) return;
        int crushAt = IrinaMath.MINE_COCOON + cfg(IrinaConfig.COCOON_SECONDS) * 20 - 4;   // 4 s → 5.4 s, as the plan
        int length = Math.max(IrinaMath.MINE, crushAt + 1);
        face(v.position());
        core.lock(length, true, false);
        boss.getNavigation().stop();
        boss.serverTriggerAnimation("irina_only_mine");
        Fx.play(sl, Fx.fx("irina_only_mine").caster(boss).at(boss.position()).yaw(boss.getYRot()).duration(length));
        core.sound("irina.cocoon", 3, 0.8f);
        List<ServerPlayer> all = core.playersNear(BossConfig.get(BossConfig.SCENE_RADIUS));
        List<ServerPlayer> others = new ArrayList<>(all);
        others.remove(v);
        for (ServerPlayer p : others) core.sceneFor(p, "irina.only_mine", IrinaMath.MINE_CAM_END, BossNet.SCENE_BARS, boss.position(), boss.getYRot(), v.getId());
        cocoonOver = false;
        mineScript = core.play(new BossTimeline("scene:only_mine", length)
                .at(IrinaMath.MINE_TITLE, () -> core.title(all, "irina_only_mine", IrinaMath.MINE_TITLE_HOLD, null))
                .at(IrinaMath.MINE_YANK, () -> {
                    if (!v.isAlive() || v.level() != sl) {
                        cocoonOver = true;
                        core.unlock();
                        return;
                    }
                    Fx.play(sl, Fx.fx("irina_yank").caster(v).at(v.position()));
                    Vec3 fwd = Vec3.directionFromRotation(0, boss.getYRot());
                    Vec3 to = ground(sl, boss.position().add(fwd.scale(IrinaMath.MINE_YANK_DIST)));
                    v.teleportTo(sl, to.x, to.y, to.z, boss.getYRot() + 180, 0);
                    v.setDeltaMovement(Vec3.ZERO);
                    Fx.play(sl, Fx.fx("irina_yank").caster(v).at(to));
                    if (MagicData.getPlayerMagicData(v).isCasting()) Utils.serverSideCancelCast(v);
                    core.sceneFor(v, "irina.only_mine_victim", crushAt - IrinaMath.MINE_YANK, BossNet.SCENE_NO_HUD, boss.position(), boss.getYRot(), v.getId());
                    cocoon = v.getUUID();   // held from the yank on
                    cocoonAt = to;
                    cocoonHp = Double.MAX_VALUE;
                })
                .at(IrinaMath.MINE_COCOON, () -> {
                    if (cocoon == null) return;
                    cocoonHp = IrinaMath.cocoonHealth(fightersNow().size(), cfg(IrinaConfig.COCOON_HP_PER_ALLY), cfg(IrinaConfig.COCOON_HP_MIN));
                    cocoonFx = Fx.play(sl, Fx.fx("irina_cocoon").caster(v).at(v.position()).attach(v).duration(crushAt - IrinaMath.MINE_COCOON + 2));
                    core.sound(v.position(), "irina.cocoon", 3, 1);
                    core.actionbar(core.arenaRadius() + 8, ui("only_mine_warn", v.getDisplayName()));
                })
                .at(crushAt, () -> {
                    if (cocoon == null || cocoonOver) return;
                    ServerPlayer x = player(cocoon);
                    endCocoon(sl);
                    if (x == null) return;
                    Fx.play(sl, Fx.fx("irina_cocoon_crush").caster(x).at(x.position()));
                    core.sound(x.position(), "irina.cocoon_crush", 3, 1);
                    core.actionbar(core.arenaRadius() + 8, ui("only_mine_crush"));
                    crushing = true;
                    try {
                        x.invulnerableTime = 0;
                        x.hurt(source("irina_cocoon"), (float) (x.getMaxHealth() * cfg(IrinaConfig.COCOON_CRUSH_SHARE)));
                    } finally {
                        crushing = false;
                    }
                }));
    }

    /** The victim stays in the cocoon; torn by the allies → free at once. */
    private void tickCocoon(ServerLevel sl) {
        if (cocoon == null) return;
        ServerPlayer v = player(cocoon);
        if (v == null) {
            endCocoon(sl);
            return;
        }
        if (cocoonHp <= 0) {
            breakCocoon(sl, v);
            return;
        }
        if (v.position().distanceToSqr(cocoonAt) > 0.09) v.teleportTo(sl, cocoonAt.x, cocoonAt.y, cocoonAt.z, v.getYRot(), v.getXRot());
        v.setDeltaMovement(Vec3.ZERO);
        v.fallDistance = 0;
    }

    private void breakCocoon(ServerLevel sl, ServerPlayer v) {
        endCocoon(sl);
        Fx.play(sl, Fx.fx("irina_cocoon_break").caster(v).at(v.position()));
        core.sound(v.position(), "irina.cocoon_break", 3, 1);
        core.actionbar(core.arenaRadius() + 8, ui("only_mine_broken"));
        core.sceneStop(List.of(v), "irina.only_mine_victim");
        if (mineScript != null) mineScript.cancel();   // torn early: she fights on at once
        core.unlock();
        boss.serverTriggerAnimation("irina_only_mine_broken");
    }

    private void endCocoon(ServerLevel sl) {
        if (cocoonFx > 0) Fx.stop(sl, cocoonFx, "");
        cocoonFx = -1;
        cocoon = null;
        cocoonOver = true;
    }

    // ---------------------------------------------------------------- end

    /** Death / removal: every thread of hers goes, the players are free. */
    void cleanup(ServerLevel sl) {
        clearMark(sl);
        clearBonds(sl);
        core.setPulse(false);
        for (Knot k : knots) Fx.stop(sl, k.fx, "");
        knots.clear();
        if (puppet != null) {
            ServerPlayer v = player(puppet);
            if (puppetFx > 0) Fx.stop(sl, puppetFx, "");
            puppetFx = -1;
            if (v != null) v.removeEffect(Irina.MARIONETTE.get());
            puppet = null;
        }
        if (cocoon != null) {
            ServerPlayer v = player(cocoon);
            endCocoon(sl);
            if (v != null) core.sceneStop(List.of(v), "irina.only_mine_victim");
        }
        if (furyFx > 0) Fx.stop(sl, furyFx, "");
        furyFx = -1;
        LIVE.remove(this);
    }

    private boolean holds(UUID u) {
        return u.equals(cocoon) || u.equals(puppet);
    }

    // ---------------------------------------------------------------- events

    public static final class Events {
        private Events() {}

        private static List<IrinaFight> live() {
            LIVE.removeIf(f -> f.boss.isRemoved());
            return LIVE;
        }

        /** Phase 2: a bonded player's damage is shared with the partner (after armour, before the finisher's last word). */
        @SubscribeEvent(priority = EventPriority.LOW)
        public static void onDamage(LivingDamageEvent e) {
            if (LIVE.isEmpty() || !(e.getEntity() instanceof ServerPlayer p) || e.isCanceled()) return;
            for (IrinaFight f : live()) f.onPlayerDamage(e, p);
        }

        /** The cocoon: hits on its victim go to the cocoon (from the allies), nothing else hurts it; the victim / the puppet hurt no one. */
        @SubscribeEvent(priority = EventPriority.HIGH)
        public static void onAttack(LivingAttackEvent e) {
            if (LIVE.isEmpty()) return;
            Entity by = e.getSource().getEntity();
            for (IrinaFight f : live()) {
                if (f.cocoon != null && e.getEntity().getUUID().equals(f.cocoon) && !crushing) {
                    e.setCanceled(true);
                    if (by instanceof Player p && !p.getUUID().equals(f.cocoon) && f.cocoonHp != Double.MAX_VALUE) f.cocoonHp -= e.getAmount();
                    return;
                }
                if (by instanceof ServerPlayer p && f.holds(p.getUUID())) {
                    e.setCanceled(true);
                    return;
                }
            }
        }

        @SubscribeEvent
        public static void onCast(SpellPreCastEvent e) {
            if (LIVE.isEmpty()) return;
            for (IrinaFight f : live())
                if (f.holds(e.getEntity().getUUID())) {
                    e.setCanceled(true);
                    return;
                }
        }

        /** Snared / in the cocoon: no jumping. */
        @SubscribeEvent
        public static void onJump(LivingEvent.LivingJumpEvent e) {
            if (!(e.getEntity() instanceof ServerPlayer p)) return;
            boolean held = p.hasEffect(Irina.THREAD_SNARE.get()) || p.hasEffect(Irina.MARIONETTE.get());
            for (IrinaFight f : LIVE) held |= p.getUUID().equals(f.cocoon);
            if (held) {
                p.setDeltaMovement(p.getDeltaMovement().multiply(1, 0, 1));
                p.hurtMarked = true;
            }
        }

        @SubscribeEvent
        public static void onStopping(ServerStoppingEvent e) {
            LIVE.clear();
        }
    }
}
