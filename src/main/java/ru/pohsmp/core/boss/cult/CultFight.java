package ru.pohsmp.core.boss.cult;

import io.redspace.ironsspellbooks.api.events.SpellPreCastEvent;
import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.util.Utils;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.util.Mth;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.MobSpawnType;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.boss.BossConfig;
import ru.pohsmp.core.boss.BossCore;
import ru.pohsmp.core.boss.BossNet;
import ru.pohsmp.core.boss.BossTimeline;
import ru.pohsmp.core.fx.Fx;

/**
 * The cult mechanics of T26 on top of Tyros's moves: phase 2 «Приговор Меллисто» (no magic but his in r24 for 10 s every 25 s, a ring
 * seal 2 s before), phase 3 «Истинное пламя» (the wall of fire on the arena edge, fire cultists, the soul form as fury), the specials
 * «Первое Пламя» and «Пепел Меллисто» (scenes for everyone in the fight, the fight is not frozen), the four new attacks («Огненный
 * серп», «Пепельный след», «Клеймо культа», «Столпы пламени»). Every strong attack has a visible warning; no beams from him to anyone.
 */
public final class CultFight {
    private final CultLeaderEntity boss;
    private final BossCore core;

    private int verdictIn = -1;
    private long verdictUntil;
    private Vec3 verdictAt;
    private int firewallFx = -1, furyFx = -1, vortexFx = -1;
    private final Map<UUID, Double> wallDist = new HashMap<>();
    private final Map<UUID, Long> wallHit = new HashMap<>();
    private final List<UUID> cultists = new ArrayList<>();
    private int spellIn = 100;
    private final List<int[]> trails = new ArrayList<>();
    private final List<Vec3[]> trailLines = new ArrayList<>();

    CultFight(CultLeaderEntity boss) {
        this.boss = boss;
        this.core = boss.bossCore();
    }

    private ServerLevel sl() {
        return (ServerLevel) boss.level();
    }

    private Vec3 arena() {
        return core.arena();
    }

    private static double cfg(net.minecraftforge.common.ForgeConfigSpec.DoubleValue v) {
        return BossConfig.get(v);
    }

    private static int cfg(net.minecraftforge.common.ForgeConfigSpec.IntValue v) {
        return BossConfig.get(v);
    }

    private DamageSource fire() {
        return sl().damageSources().mobAttack(boss);
    }

    private static Component ui(String key, Object... args) {
        return Component.translatable("ui.pohsmp_core.cult_leader." + key, args).withStyle(s -> s.withColor(CultLeader.COLOR));
    }

    // ---------------------------------------------------------------- tick

    void tick(ServerLevel sl) {
        if (!core.started() || core.inFinale()) return;
        int phase = core.phase();
        if (phase == 1 && verdictIn >= 0 && !core.inScene() && --verdictIn == 0) verdict(sl);
        if (verdictActive(sl)) {
            for (ServerPlayer p : sl.players())
                if (inVerdict(p)) p.addEffect(new MobEffectInstance(CultLeader.VERDICT.get(), 25, 0, false, false, true));
        } else if (verdictAt != null && sl.getGameTime() >= verdictUntil) {
            verdictAt = null;
            core.setPulse(false);
            core.actionbar(cfg(BossConfig.CL_VERDICT_RADIUS) + 8, ui("verdict_end"));
            core.sound("cult_leader.verdict_end", 2, 1);
        }
        if (firewallFx > 0) firewall(sl);
        tickTrails(sl);
        if (--spellIn <= 0) {
            if (castSpell(sl)) spellIn = cfg(BossConfig.CL_SPELL_COOLDOWN) * 20;
            else spellIn = 20;
        }
    }

    // ---------------------------------------------------------------- phases

    void onPhase(int from, int to) {
        ServerLevel sl = sl();
        if (to >= 1 && from < 1 && !BossConfig.get(BossConfig.SPECIALS)) {   // no «Первое Пламя»: the short transition fx instead
            Fx.play(sl, Fx.fx("cult_leader_phase2").caster(boss).at(boss.position()).yaw(boss.getYRot()).attach(boss));
            core.sound("cult_leader.phase", 3, 1);
            verdictIn = 100;
        }
        if (to >= 1) core.actionbar(core.def.fightRadius, ui("phase2"));
        if (to == 2) phase3(sl);
    }

    private void phase3(ServerLevel sl) {
        verdictIn = -1;
        core.actionbar(core.def.fightRadius, ui("phase3"));
        core.sound("cult_leader.phase", 4, 0.9f);
        Fx.play(sl, Fx.fx("cult_leader_phase3").caster(boss).at(boss.position()).yaw(boss.getYRot()));
        core.play(new BossTimeline("phase3", 40)
                .at(30, () -> {
                    firewallFx = Fx.play(sl, Fx.fx("cult_leader_firewall").at(arena()).yaw(0));
                    core.sound(arena(), "cult_leader.firewall", 4, 1);
                    core.actionbar(core.def.fightRadius, ui("firewall"));
                })
                .at(36, () -> summonCultists(sl)));
        if (!boss.isSoulMode()) boss.setSoulMode(true);   // the soul form of Tyros as fury
        furyFx = Fx.play(sl, Fx.fx("cult_leader_fury").caster(boss).at(boss.position()).attach(boss));
    }

    // ---------------------------------------------------------------- «Приговор Меллисто»

    private void verdict(ServerLevel sl) {
        verdictIn = cfg(BossConfig.CL_VERDICT_INTERVAL) * 20;
        Vec3 c = boss.position();
        double r = cfg(BossConfig.CL_VERDICT_RADIUS);
        int dur = cfg(BossConfig.CL_VERDICT_SECONDS) * 20;
        boss.serverTriggerAnimation("charge_raised_hand");
        core.lock(CultMath.VERDICT_WARN, true, false);
        Fx.play(sl, Fx.fx("cult_leader_verdict").at(c).yaw(boss.getYRot()).duration(CultMath.VERDICT_WARN + dur));
        core.sound("cult_leader.verdict", 4, 1);
        core.actionbar(r + 8, ui("verdict_warn"));
        core.play(new BossTimeline("verdict", CultMath.VERDICT_WARN + 1).at(CultMath.VERDICT_WARN, () -> {
            verdictAt = c;
            verdictUntil = sl.getGameTime() + dur;
            core.setPulse(true);
            core.sound("cult_leader.verdict_lock", 4, 1);
            for (ServerPlayer p : sl.players()) {
                if (!inVerdict(p)) continue;
                p.displayClientMessage(ui("verdict", dur / 20), true);
                Fx.play(sl, Fx.fx("cult_leader_verdict_mark").caster(p).at(p.position()).attach(p).duration(dur));
                if (MagicData.getPlayerMagicData(p).isCasting()) Utils.serverSideCancelCast(p);
            }
        }));
    }

    private boolean verdictActive(ServerLevel sl) {
        return verdictAt != null && sl.getGameTime() < verdictUntil;
    }

    boolean inVerdict(LivingEntity e) {
        if (verdictAt == null || e == boss || !e.isAlive() || e.level() != boss.level()) return false;
        if (e.level().getGameTime() >= verdictUntil) return false;
        double r = cfg(BossConfig.CL_VERDICT_RADIUS);
        return e.position().distanceToSqr(verdictAt) <= r * r;
    }

    /** A cast tried under the verdict: it goes out in ash in the hand. */
    void fizzle(ServerPlayer p) {
        Fx.play(sl(), Fx.fx("cult_leader_verdict_fizzle").caster(p).at(p.position()));
        p.displayClientMessage(ui("verdict_blocked"), true);
    }

    // ---------------------------------------------------------------- phase 3: the wall of fire, the cultists

    private void firewall(ServerLevel sl) {
        double r = cfg(BossConfig.CL_ARENA_RADIUS);
        Vec3 c = arena();
        long now = sl.getGameTime();
        for (LivingEntity e : sl.getEntitiesOfClass(LivingEntity.class, new AABB(c, c).inflate(r + 4, 12, r + 4))) {
            if (e == boss || e instanceof FireCultistEntity || e instanceof Player p && (p.isCreative() || p.isSpectator())) continue;
            double d = Math.sqrt(e.distanceToSqr(c.x, e.getY(), c.z));
            Double before = wallDist.put(e.getUUID(), d);
            if (before == null || !CultMath.wallCrossed(before, d, r)) continue;
            if (now - wallHit.getOrDefault(e.getUUID(), Long.MIN_VALUE / 2) < 10) continue;
            wallHit.put(e.getUUID(), now);
            e.hurt(fire(), (float) cfg(BossConfig.CL_FIREWALL_DAMAGE));
            Fx.play(sl, Fx.fx("cult_leader_firewall_burn").caster(e).at(e.position()));
        }
    }

    private void summonCultists(ServerLevel sl) {
        int min = cfg(BossConfig.CL_CULTISTS_MIN), max = Math.max(min, cfg(BossConfig.CL_CULTISTS_MAX));
        int n = min + boss.getRandom().nextInt(max - min + 1);
        if (n <= 0) return;
        core.actionbar(core.def.fightRadius, ui("summon"));
        core.sound("cult_leader.summon", 3, 1);
        for (int i = 0; i < n; i++) {
            double a = boss.getYRot() * Mth.DEG_TO_RAD + Math.PI * 2 * i / n, d = 6 + boss.getRandom().nextDouble() * 4;
            Vec3 p = ground(sl, boss.position().add(Math.cos(a) * d, 0, Math.sin(a) * d));
            Fx.play(sl, Fx.fx("cult_leader_summon").at(p));
            core.play(new BossTimeline("summon" + i, 25).at(24, () -> {
                if (!boss.isAlive()) return;
                FireCultistEntity c = CultLeader.CULTIST.get().create(sl);
                if (c == null) return;
                c.moveTo(p.x, p.y, p.z, boss.getYRot(), 0);
                c.finalizeSpawn(sl, sl.getCurrentDifficultyAt(c.blockPosition()), MobSpawnType.MOB_SUMMONED, null, null);
                c.leader = boss.getUUID();
                sl.addFreshEntity(c);
                cultists.add(c.getUUID());
            }));
        }
    }

    static Vec3 ground(ServerLevel sl, Vec3 p) {
        int y = sl.getHeight(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES, Mth.floor(p.x), Mth.floor(p.z));
        return Math.abs(y - p.y) <= 6 ? new Vec3(p.x, y, p.z) : p;
    }

    /** Death: the wall goes out, the fury aura stops, the cultists go with him. */
    void stopFires(ServerLevel sl) {
        if (firewallFx > 0) Fx.stop(sl, firewallFx, "");
        if (furyFx > 0) Fx.stop(sl, furyFx, "");
        firewallFx = furyFx = -1;
    }

    void onDeath(ServerLevel sl) {
        verdictAt = null;
        verdictIn = -1;
        if (furyFx > 0) Fx.stop(sl, furyFx, "");
        furyFx = -1;
        if (vortexFx > 0) Fx.stop(sl, vortexFx, "");   // died while ash: seen again, the whirl stops
        vortexFx = -1;
        if ((core.look() & BossNet.LOOK_HIDDEN) != 0) core.lookFlag(BossNet.LOOK_HIDDEN, false);
        if (boss.getMainHandItem().isEmpty())   // died with the sickle in the air
            boss.setItemSlot(net.minecraft.world.entity.EquipmentSlot.MAINHAND, new net.minecraft.world.item.ItemStack(CultLeader.SCYTHE.get()));
        for (UUID u : cultists) if (sl.getEntity(u) instanceof LivingEntity c && c.isAlive()) c.kill();
        cultists.clear();
    }

    // ---------------------------------------------------------------- specials

    /** Returns false while it cannot start (another scene is on): the core asks again next tick. */
    boolean special(String id) {
        if (core.inScene() || core.locked() || boss.isStanceBroken() || boss.isHalfHealthAttacking()) return false;
        if (id.equals("first_flame")) firstFlame(sl());
        else if (id.equals("ash")) ash(sl());
        return true;
    }

    /** «Первое Пламя» (6 s): the scythe into the ground, the sky seal r22, after 4 s the pillar in the centre and a ring of fire 3 → 28. */
    private void firstFlame(ServerLevel sl) {
        Vec3 p = arena();
        core.lock(CultMath.FF, true, false);
        boss.castComplete();
        boss.attackGoal.stopMeleeAction();
        boss.serverTriggerAnimation("cult_leader_first_flame");
        Fx.play(sl, Fx.fx("cult_first_flame").caster(boss).at(boss.position()).yaw(boss.getYRot()).point("center", p));
        List<ServerPlayer> who = core.scene("cult_leader.first_flame", CultMath.FF, BossNet.SCENE_BARS, cfg(BossConfig.SCENE_RADIUS), p, boss.getYRot(), -1);
        Set<UUID> ringHit = new HashSet<>();
        core.play(new BossTimeline("scene:first_flame", CultMath.FF)
                .at(0, () -> core.sound("cult_leader.first_flame", 4, 1))
                .at(CultMath.FF_TITLE, () -> core.title(who, "cult_first_flame", CultMath.FF_TITLE_HOLD, null))
                .at(CultMath.FF_WARN, () -> core.actionbar(core.def.fightRadius, ui("first_flame_warn")))
                .at(CultMath.FF_PILLAR, () -> {
                    core.sound(p, "cult_leader.first_flame_impact", 5, 1);
                    for (LivingEntity e : targets(sl, p, 3.2))
                        if (Math.abs(e.getY() - p.y) < 6) e.hurt(fire(), (float) cfg(BossConfig.CL_PILLAR_DAMAGE));
                })
                .during(CultMath.FF_PILLAR, CultMath.FF_RING_END, t -> {
                    double r = CultMath.ringRadius(t);
                    for (LivingEntity e : targets(sl, p, r + 1)) {
                        if (ringHit.contains(e.getUUID())) continue;
                        double d = Math.sqrt(e.distanceToSqr(p.x, e.getY(), p.z));
                        if (CultMath.ringHits(d, r, e.getY() - ground(sl, e.position()).y)) {
                            ringHit.add(e.getUUID());
                            e.hurt(fire(), (float) cfg(BossConfig.CL_FIRST_FLAME_DAMAGE));
                            e.setSecondsOnFire(3);
                        }
                    }
                })
                .then(() -> {
                    if (core.phase() == 1) verdictIn = 100;
                }));
    }

    /**
     * «Пепел Меллисто» (≈6 s): he burns into an ash whirl (invisible, invulnerable), rushes over the arena, gathers 5 blocks before the
     * strongest enemy (by damage dealt to him) and cuts the whole arena along a straight line shown 1.5 s before.
     */
    private void ash(ServerLevel sl) {
        core.lock(CultMath.ASH, true, false);
        boss.castComplete();
        boss.attackGoal.stopMeleeAction();
        boss.serverTriggerAnimation("cult_leader_ash_dissolve");
        Fx.play(sl, Fx.fx("cult_ash_dissolve").caster(boss).at(boss.position()).yaw(boss.getYRot()));
        core.sound("cult_leader.ash", 4, 1);
        List<ServerPlayer> who = core.scene("cult_leader.ash", CultMath.ASH, BossNet.SCENE_BARS, cfg(BossConfig.SCENE_RADIUS), boss.position(), boss.getYRot(), -1);
        Vec3[] path = new Vec3[3];   // from, to, direction of the cut
        int[] vortex = {-1};
        core.play(new BossTimeline("scene:ash", CultMath.ASH)
                .at(CultMath.ASH_TITLE, () -> core.title(who, "cult_ash", CultMath.ASH_TITLE_HOLD, null))
                .at(CultMath.ASH_GONE, () -> {
                    core.lock(CultMath.ASH_REFORM - CultMath.ASH_GONE, true, true);   // invulnerable while he is ash
                    core.lookFlag(BossNet.LOOK_HIDDEN, true);
                    vortex[0] = vortexFx = Fx.play(sl, Fx.fx("cult_ash_vortex").caster(boss).at(boss.position()).attach(boss));
                    ServerPlayer enemy = core.strongestEnemy();
                    Vec3 from = boss.position();
                    Vec3 tp = enemy != null ? enemy.position() : arena();
                    Vec3 dir = tp.subtract(from).multiply(1, 0, 1);
                    dir = dir.lengthSqr() < 1e-4 ? Vec3.directionFromRotation(0, boss.getYRot()) : dir.normalize();
                    path[0] = from;
                    path[1] = ground(sl, tp.subtract(dir.scale(CultMath.ASH_BEFORE)));
                    path[2] = dir;
                    core.actionbar(core.def.fightRadius, ui("ash_warn"));
                })
                .during(CultMath.ASH_GONE + 1, CultMath.ASH_REFORM, t -> {
                    if (path[0] == null) return;
                    double k = ru.pohsmp.core.boss.BossMath.sine((t - CultMath.ASH_GONE) / (double) (CultMath.ASH_REFORM - CultMath.ASH_GONE));
                    Vec3 p = path[0].lerp(path[1], k);
                    float yaw = (float) (Mth.atan2(path[2].z, path[2].x) * Mth.RAD_TO_DEG) - 90;
                    boss.moveTo(p.x, p.y, p.z, yaw, 0);
                    boss.setYHeadRot(yaw);
                    boss.setYBodyRot(yaw);
                })
                .at(CultMath.ASH_REFORM, () -> {
                    if (vortex[0] > 0) Fx.stop(sl, vortex[0], "");
                    vortexFx = -1;
                    core.lookFlag(BossNet.LOOK_HIDDEN, false);
                    boss.serverTriggerAnimation("cult_leader_ash_reform");
                    Fx.play(sl, Fx.fx("cult_ash_reform").caster(boss).at(boss.position()).yaw(boss.getYRot()));
                    Fx.play(sl, Fx.fx("cult_ash_line").at(boss.position()).yaw(boss.getYRot()));
                })
                .at(CultMath.ASH_SLASH_ANIM, () -> boss.serverTriggerAnimation("cult_leader_ash_slash"))
                .at(CultMath.ASH_SLASH, () -> {
                    Vec3 a = boss.position(), dir = Vec3.directionFromRotation(0, boss.getYRot());
                    Vec3 b = a.add(dir.scale(CultMath.ASH_LINE));
                    core.sound("cult_leader.ash_slash", 5, 1);
                    Fx.play(sl, Fx.fx("cult_ash_slash").at(a).yaw(boss.getYRot()));
                    double half = cfg(BossConfig.CL_ASH_SLASH_WIDTH) / 2 + 0.3;
                    for (LivingEntity e : targets(sl, a.lerp(b, 0.5), CultMath.ASH_LINE / 2 + 2))
                        if (CultMath.toSegment(e.getX(), e.getZ(), a.x, a.z, b.x, b.z) <= half && Math.abs(e.getY() - a.y) < 4) {
                            e.hurt(fire(), (float) cfg(BossConfig.CL_ASH_SLASH_DAMAGE));
                            e.setSecondsOnFire(4);
                        }
                }));
    }

    // ---------------------------------------------------------------- the four new attacks (no scene, each with its warning)

    private boolean castSpell(ServerLevel sl) {
        LivingEntity t = boss.getTarget();
        if (t == null || !t.isAlive() || core.locked() || core.inScene() || boss.isAnimating() || boss.isCasting() || boss.isStanceBroken()
                || boss.isHalfHealthAttacking() || boss.isSpawning()) return false;
        double d = boss.distanceTo(t);
        List<Runnable> can = new ArrayList<>();
        if (d < 14) can.add(() -> sickle(sl, t));
        if (d > 4 && d < 14) can.add(() -> ashTrail(sl, t));
        can.add(() -> brand(sl, t));
        can.add(() -> pillars(sl));
        can.get(boss.getRandom().nextInt(can.size())).run();
        return true;
    }

    private float yawTo(Vec3 p) {
        return (float) (Mth.atan2(p.z - boss.getZ(), p.x - boss.getX()) * Mth.RAD_TO_DEG) - 90;
    }

    private void face(float yaw) {
        boss.setYRot(yaw);
        boss.setYHeadRot(yaw);
        boss.setYBodyRot(yaw);
    }

    /** «Огненный серп»: a flaming scythe thrown like a boomerang along an arc shown 1 s before on the ground; back in his hand. */
    private void sickle(ServerLevel sl, LivingEntity t) {
        float yaw = yawTo(t.position());
        face(yaw);
        core.lock(CultMath.SICKLE, true, false);
        boss.serverTriggerAnimation("cult_leader_sickle_throw");
        Vec3 o = boss.position();
        Fx.play(sl, Fx.fx("cult_sickle_warn").at(o).yaw(yaw));
        core.actionbar(20, ui("sickle"));
        CultSickleEntity[] s = {null};
        int[] spin = {-1};
        Set<UUID> hit = new HashSet<>();
        Vec3 fwd = Vec3.directionFromRotation(0, yaw), right = new Vec3(-fwd.z, 0, fwd.x);
        core.play(new BossTimeline("spell:sickle", CultMath.SICKLE)
                .at(CultMath.SICKLE_THROW, () -> {
                    boss.setItemSlot(net.minecraft.world.entity.EquipmentSlot.MAINHAND, net.minecraft.world.item.ItemStack.EMPTY);
                    s[0] = CultLeader.SICKLE.get().create(sl);
                    if (s[0] == null) return;
                    s[0].moveTo(o.x, o.y + 2.0, o.z, yaw, 0);
                    sl.addFreshEntity(s[0]);
                    spin[0] = Fx.play(sl, Fx.fx("cult_sickle_spin").caster(s[0]).at(s[0].position()).attach(s[0]));
                })
                .during(CultMath.SICKLE_THROW + 1, CultMath.SICKLE_CATCH - 1, k -> {
                    if (s[0] == null) return;
                    double[] xy = CultMath.sicklePath((k - CultMath.SICKLE_THROW) / (double) CultMath.SICKLE_FLIGHT);
                    Vec3 p = o.add(right.scale(xy[0])).add(fwd.scale(xy[1])).add(0, 2.0, 0);
                    s[0].moveTo(p.x, p.y, p.z, s[0].getYRot() + 40, 0);
                    for (LivingEntity e : targets(sl, p, 1.8))
                        if (hit.add(e.getUUID())) {
                            e.hurt(fire(), (float) cfg(BossConfig.CL_SICKLE_DAMAGE));
                            e.setSecondsOnFire(3);
                        }
                })
                .at(CultMath.SICKLE_CATCH, () -> {
                    if (s[0] != null) s[0].discard();
                    if (spin[0] > 0) Fx.stop(sl, spin[0], "");
                    boss.setItemSlot(net.minecraft.world.entity.EquipmentSlot.MAINHAND, new net.minecraft.world.item.ItemStack(CultLeader.SCYTHE.get()));
                    Fx.play(sl, Fx.fx("cult_sickle_catch").caster(boss).at(boss.position()));
                }));
    }

    /** «Пепельный след»: a dash through the players along a line shown 0.5 s before; a strip of burning ground behind for 4 s. */
    private void ashTrail(ServerLevel sl, LivingEntity t) {
        float yaw = yawTo(t.position());
        face(yaw);
        Vec3 o = boss.position(), dir = Vec3.directionFromRotation(0, yaw);
        double len = CultMath.TRAIL_LEN;
        var hitRes = sl.clip(new net.minecraft.world.level.ClipContext(o.add(0, 1, 0), o.add(0, 1, 0).add(dir.scale(len)),
                net.minecraft.world.level.ClipContext.Block.COLLIDER, net.minecraft.world.level.ClipContext.Fluid.NONE, boss));
        if (hitRes.getType() != net.minecraft.world.phys.HitResult.Type.MISS) len = Math.max(2, hitRes.getLocation().distanceTo(o.add(0, 1, 0)) - 1);
        double dist = len;
        Vec3 end = o.add(dir.scale(dist));
        core.lock(CultMath.TRAIL, true, false);
        boss.serverTriggerAnimation("cult_leader_ash_trail_dash");
        Fx.play(sl, Fx.fx("cult_ash_trail_warn").at(o).yaw(yaw).scale(dist / CultMath.TRAIL_LEN));
        core.actionbar(20, ui("ash_trail"));
        Set<UUID> hit = new HashSet<>();
        core.play(new BossTimeline("spell:ash_trail", CultMath.TRAIL)
                .at(CultMath.TRAIL_DASH, () -> {
                    Fx.play(sl, Fx.fx("cult_ash_trail_dash").caster(boss).at(o).yaw(yaw).attach(boss));
                    Fx.play(sl, Fx.fx("cult_ash_trail").at(o).yaw(yaw).scale(dist / CultMath.TRAIL_LEN));
                    trails.add(new int[] {CultMath.TRAIL_BURN});
                    trailLines.add(new Vec3[] {o, end});
                })
                .during(CultMath.TRAIL_DASH + 1, CultMath.TRAIL_DASH + CultMath.TRAIL_DASH_TICKS, k -> {
                    Vec3 p = o.lerp(end, (k - CultMath.TRAIL_DASH) / (double) CultMath.TRAIL_DASH_TICKS);
                    boss.moveTo(p.x, p.y, p.z, yaw, 0);
                    for (LivingEntity e : targets(sl, p, 1.6))
                        if (hit.add(e.getUUID())) e.hurt(fire(), (float) cfg(BossConfig.CL_TRAIL_DAMAGE) * 2);
                }));
    }

    private void tickTrails(ServerLevel sl) {
        for (int i = 0; i < trails.size(); i++) {
            int left = --trails.get(i)[0];
            Vec3[] l = trailLines.get(i);
            if (left % 20 == 0) {
                double half = cfg(BossConfig.CL_TRAIL_WIDTH) / 2;
                for (LivingEntity e : targets(sl, l[0].lerp(l[1], 0.5), CultMath.TRAIL_LEN / 2 + 2))
                    if (CultMath.toSegment(e.getX(), e.getZ(), l[0].x, l[0].z, l[1].x, l[1].z) <= half && Math.abs(e.getY() - l[0].y) < 2)
                        e.hurt(fire(), (float) cfg(BossConfig.CL_TRAIL_DAMAGE));
            }
            if (left <= 0) {
                trails.remove(i);
                trailLines.remove(i--);
            }
        }
    }

    /** «Клеймо культа»: a brand on a player; 3 s later it bursts r3 (the others: run from the branded one). */
    private void brand(ServerLevel sl, LivingEntity t) {
        List<ServerPlayer> fighters = core.fighters();
        LivingEntity mark = fighters.isEmpty() ? t : fighters.get(boss.getRandom().nextInt(fighters.size()));
        face(yawTo(mark.position()));
        core.lock(CultMath.BRAND, true, false);
        boss.serverTriggerAnimation("cult_leader_brand");
        int delay = cfg(BossConfig.CL_BRAND_DELAY) * 20;
        core.play(new BossTimeline("spell:brand", CultMath.BRAND_AT + delay + 1)
                .at(CultMath.BRAND_AT, () -> {
                    if (!mark.isAlive()) return;
                    mark.addEffect(new MobEffectInstance(CultLeader.BRAND.get(), delay, 0, false, true, true));
                    Fx.play(sl, Fx.fx("cult_brand").caster(mark).at(mark.position()).attach(mark).duration(delay));
                    if (mark instanceof ServerPlayer sp) sp.displayClientMessage(ui("brand_warn"), true);
                    core.actionbar(20, ui("brand"));
                })
                .at(CultMath.BRAND_AT + delay, () -> {
                    if (!mark.isAlive() || mark.level() != sl) return;
                    Vec3 c = mark.position();
                    Fx.play(sl, Fx.fx("cult_brand_explode").at(c));
                    double r = cfg(BossConfig.CL_BRAND_RADIUS);
                    for (LivingEntity e : targets(sl, c, r)) e.hurt(fire(), (float) cfg(BossConfig.CL_BRAND_DAMAGE));
                    sl.playSound(null, c.x, c.y, c.z, net.minecraft.sounds.SoundEvents.GENERIC_EXPLODE, net.minecraft.sounds.SoundSource.HOSTILE, 2, 1.2f);
                }));
    }

    /** «Столпы пламени»: 5 pillars of fire around the players, warning circles 1.5 s before. */
    private void pillars(ServerLevel sl) {
        List<ServerPlayer> fighters = core.fighters();
        if (fighters.isEmpty()) return;
        core.lock(CultMath.PILLARS, true, false);
        boss.serverTriggerAnimation("cult_leader_pillars");
        List<Vec3> at = new ArrayList<>();
        core.play(new BossTimeline("spell:pillars", CultMath.PILLARS)
                .at(CultMath.PILLARS_MARK, () -> {
                    for (int i = 0; i < CultMath.PILLARS_COUNT; i++) {
                        ServerPlayer p = fighters.get(i % fighters.size());
                        double a = boss.getRandom().nextDouble() * Math.PI * 2, d = i < fighters.size() ? 0.3 : 1.5 + boss.getRandom().nextDouble() * 2;
                        Vec3 q = ground(sl, p.position().add(Math.cos(a) * d, 0, Math.sin(a) * d));
                        at.add(q);
                        Fx.play(sl, Fx.fx("cult_pillar_warn").at(q));
                    }
                    core.actionbar(20, ui("pillars"));
                })
                .at(CultMath.PILLARS_ERUPT, () -> {
                    Set<UUID> hit = new HashSet<>();
                    for (Vec3 q : at) {
                        Fx.play(sl, Fx.fx("cult_pillar").at(q));
                        for (LivingEntity e : targets(sl, q, CultMath.PILLAR_R + 0.5))
                            if (e.getY() >= q.y - 1 && e.getY() <= q.y + CultMath.PILLAR_H && hit.add(e.getUUID())) {
                                e.hurt(fire(), (float) cfg(BossConfig.CL_PILLARS_DAMAGE));
                                e.setSecondsOnFire(3);
                            }
                    }
                    core.sound(at.get(0), "cult_leader.first_flame_impact", 2, 1.3f);
                }));
    }

    /** Living things he may hurt near p (horizontal radius r): not him, not his cultists, not creative / spectators. */
    private List<LivingEntity> targets(ServerLevel sl, Vec3 p, double r) {
        List<LivingEntity> out = new ArrayList<>();
        for (LivingEntity e : sl.getEntitiesOfClass(LivingEntity.class, new AABB(p, p).inflate(r, 10, r))) {
            if (e == boss || e instanceof FireCultistEntity || !e.isAlive()) continue;
            if (e instanceof Player pl && (pl.isCreative() || pl.isSpectator())) continue;
            if (e.distanceToSqr(p.x, e.getY(), p.z) > r * r) continue;
            out.add(e);
        }
        return out;
    }

    // ---------------------------------------------------------------- events

    public static final class Events {
        private Events() {}

        /** «Приговор Меллисто»: no one but him casts in the ring while it lasts (players; the cast goes out in ash). */
        @SubscribeEvent
        public static void onCast(SpellPreCastEvent e) {
            if (!(e.getEntity() instanceof ServerPlayer p)) return;
            for (CultLeaderEntity b : p.serverLevel().getEntitiesOfClass(CultLeaderEntity.class, p.getBoundingBox().inflate(48))) {
                if (b.fight.inVerdict(p)) {
                    e.setCanceled(true);
                    b.fight.fizzle(p);
                    return;
                }
            }
        }
    }
}
