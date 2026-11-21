package ru.pohsmp.core.boss.aris;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.util.Mth;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.ai.attributes.AttributeModifier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.boss.BossConfig;
import ru.pohsmp.core.boss.BossCore;
import ru.pohsmp.core.boss.BossNet;
import ru.pohsmp.core.boss.BossNpc;
import ru.pohsmp.core.boss.BossTimeline;
import ru.pohsmp.core.fx.Fx;

/**
 * The fight of T28 Aris (docs/specs/tasks/T28_aris_boss.md; numbers: [aris] of pohsmp_core-bosses-server.toml, balance_bosses.md §4):
 * <ul>
 * <li>phase 1 «Ковка»: the hammer swing, the molten ring (slam, jump it), the fan of metal, anvils from the ground (collision
 * entities, cover from «Мехи» and billets);</li>
 * <li>phase 2 «Оружейная» (66%): hovering blades of her forging (they can be struck down);</li>
 * <li>phase 3 «Мифический сплав» (33%): armour white-hot (aris_mythic), damage ×1.3, swings faster, «перековка» (weapon damage of a
 * player ×0.6 for 10 s);</li>
 * <li>specials (once, with a scene; the fight is not frozen): «Горн» (75%: the floor burns, safe islands), «Последний удар молота»
 * (10%: a huge blow, 3.5 s of warning);</li>
 * <li>four spells: «Раскалённая заготовка», «Цепи кузни», «Закалка», «Мехи».</li>
 * </ul>
 * Every strong attack has a visible warning (fx on the ground + action bar); no beams or lines from her to anyone.
 * Directions: every hit zone and every directional fx is taken from her BODY yaw forward ({@link #fwd()}, getYRot after
 * {@link #face}), never from the model or the head: directional fx get .at(point).yaw(bodyYaw) without .caster(boss), because the
 * renderer would turn a caster's fx by its head yaw.
 */
public final class ArisFight {
    private static final UUID MYTHIC_ID = UUID.fromString("2e7b4c19-5a3d-4f60-8b21-9c0d7e4a6f13");
    /** Chained players → the fight holding them (ArisEvents: hits of allies, jumps). */
    static final Map<UUID, ArisFight> CHAINED = new ConcurrentHashMap<>();

    private final ArisEntity boss;
    private final BossCore core;

    private final Map<String, Integer> cooldown = new HashMap<>();
    private int gcd = 60;
    /** She swings / casts until this tick (melee goal stands still). */
    private int actingUntil;

    private static final class Anvil {
        ArisAnvilEntity e;
        int fx, left;
        final Set<UUID> hit = new HashSet<>();
    }

    private final List<Anvil> anvils = new ArrayList<>();
    private final List<UUID> blades = new ArrayList<>();
    private final List<ArisBilletEntity> billets = new ArrayList<>();

    private static final class Chain {
        ServerPlayer victim;
        Vec3 anchor;
        int hits, left, fx;
    }

    private final Map<UUID, Chain> chains = new HashMap<>();

    private Vec3 quenchAt;
    private long quenchUntil;

    private Vec3 forgeAt;
    private final List<Vec3> islands = new ArrayList<>();
    private long floorFrom, floorTo, forgeEnd;
    private final List<Integer> forgeFx = new ArrayList<>();
    private int mythicFx = -1;

    ArisFight(ArisEntity boss) {
        this.boss = boss;
        this.core = boss.bossCore();
        cooldown.put("slam", 80);
        cooldown.put("metal_wave", 160);
        cooldown.put("anvils", 200);
        cooldown.put("billet", 120);
        cooldown.put("chains", 240);
        cooldown.put("quench", 400);
        cooldown.put("bellows", 140);
    }

    private ServerLevel sl() {
        return (ServerLevel) boss.level();
    }

    static Component ui(String key, Object... args) {
        return Component.translatable("ui.pohsmp_core.aris." + key, args).withStyle(s -> s.withColor(Aris.COLOR));
    }

    private static double cfg(net.minecraftforge.common.ForgeConfigSpec.DoubleValue v) {
        return ArisConfig.get(v);
    }

    private static int cfg(net.minecraftforge.common.ForgeConfigSpec.IntValue v) {
        return ArisConfig.get(v);
    }

    boolean acting() {
        return boss.tickCount < actingUntil || core.locked();
    }

    /** T32 «Сломать блок»: her heavy hit = the hammer swing (attack_damage with the enrage), ×mythic_damage_mult in phase 3. */
    double guardBreakDamage() {
        double m = core.phase() >= 2 ? cfg(ArisConfig.MYTHIC_DAMAGE) : 1;
        return ru.pohsmp.core.boss.BossGuardBreakMath.heavy(boss.getAttributeValue(Attributes.ATTACK_DAMAGE)) * m;
    }

    /** Her own hit (pohsmp_core:boss_attack), ×1.3 in phase 3, optional fire. */
    private void hit(LivingEntity e, double dmg, int burnSeconds) {
        double m = core.phase() >= 2 ? cfg(ArisConfig.MYTHIC_DAMAGE) : 1;
        e.hurt(core.attackDamage(), (float) (dmg * m));
        if (burnSeconds > 0) e.setSecondsOnFire(burnSeconds);
    }

    /** Whom she may hurt: living, not her, her blades, peaceful NPCs; players not creative / spectator. */
    boolean canHurt(LivingEntity e) {
        if (e == boss || !e.isAlive() || e instanceof ArisBladeEntity || e instanceof ArisEntity || e instanceof BossNpc) return false;
        return !(e instanceof Player p && (p.isCreative() || p.isSpectator()));
    }

    private List<LivingEntity> targets(Vec3 p, double r, double dy) {
        List<LivingEntity> out = new ArrayList<>();
        for (LivingEntity e : sl().getEntitiesOfClass(LivingEntity.class, new AABB(p, p).inflate(r, dy, r)))
            if (canHurt(e) && e.distanceToSqr(p.x, e.getY(), p.z) <= r * r) out.add(e);
        return out;
    }

    static Vec3 ground(ServerLevel sl, Vec3 p) {
        int y = sl.getHeight(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES, Mth.floor(p.x), Mth.floor(p.z));
        return Math.abs(y - p.y) <= 6 ? new Vec3(p.x, y, p.z) : p;
    }

    private float yawTo(Vec3 p) {
        return (float) (Mth.atan2(p.z - boss.getZ(), p.x - boss.getX()) * Mth.RAD_TO_DEG) - 90;
    }

    void face(float yaw) {
        boss.setYRot(yaw);
        boss.setYHeadRot(yaw);
        boss.setYBodyRot(yaw);
    }

    private Vec3 fwd() {
        return Vec3.directionFromRotation(0, boss.getYRot());
    }

    /** The straight path a → b crosses an anvil (cover). */
    private boolean covered(Vec3 a, Vec3 b) {
        for (Anvil an : anvils) {
            ArisAnvilEntity e = an.e;
            if (e.isAlive() && b.y < e.getY() + ArisMath.ANVIL_HEIGHT + 0.5
                    && ArisMath.segmentHitsBox(a.x, a.z, b.x, b.z, e.getX(), e.getZ(), e.halfX(), e.halfZ())) return true;
        }
        return false;
    }

    /** Damage dealt to her: «Закалка» ×0.6 while she is in the steam. */
    float filterDamage(float amount) {
        if (quenchAt != null && boss.level().getGameTime() < quenchUntil) {
            double r = cfg(ArisConfig.QUENCH_RADIUS);
            if (boss.position().distanceToSqr(quenchAt) <= r * r) return (float) (amount * cfg(ArisConfig.QUENCH_MULT));
        }
        return amount;
    }

    // ---------------------------------------------------------------- tick

    void tick(ServerLevel sl) {
        if (pendingMythic) {
            pendingMythic = false;
            mythic(sl, false);
        }
        tickAnvils(sl);
        tickChains(sl);
        tickQuench(sl);
        tickForge(sl);
        if (!core.started() || core.inFinale()) return;
        cooldown.replaceAll((k, v) -> Math.max(0, v - 1));
        if (gcd > 0) gcd--;
        else if (castSpell(sl)) gcd = cfg(BossConfig.ABILITY_GCD) * 20 + boss.getRandom().nextInt(30);
        else gcd = 10;
    }

    /** Loaded mid-fight (phase 3): the aura and the damage come back on the first tick (the entity is in the world by then). */
    void afterLoad() {
        pendingMythic = core.phase() >= 2;
    }

    private boolean pendingMythic;

    // ---------------------------------------------------------------- melee

    /** The hammer swing (from her melee goal): windup, hit at 0.62 s in front of her. */
    boolean swing(LivingEntity t) {
        if (acting() || core.inScene() || !core.started()) return false;
        face(yawTo(t.position()));
        boss.play("swing");
        actingUntil = boss.tickCount + ArisMath.SWING;   // the swish: a sound keyframe of the animation at the windup (0.4 s)
        core.play(new BossTimeline("swing", ArisMath.SWING_HIT + 1).at(ArisMath.SWING_HIT, () -> {
            Vec3 c = boss.position().add(fwd().scale(1.6));
            for (LivingEntity e : targets(c, 2.2, 2.5)) {
                double m = core.phase() >= 2 ? cfg(ArisConfig.MYTHIC_DAMAGE) : 1;
                e.hurt(core.attackDamage(), (float) (boss.getAttributeValue(Attributes.ATTACK_DAMAGE) * m));
                Vec3 push = e.position().subtract(boss.position()).multiply(1, 0, 1);
                if (push.lengthSqr() > 1e-4) {
                    push = push.normalize().scale(0.6);
                    e.push(push.x, 0.2, push.z);
                    e.hurtMarked = true;
                }
            }
            core.sound("aris.anvil_ring", 1, 1.25f);   // the hammer connected
        }));
        return true;
    }

    // ---------------------------------------------------------------- phases

    void onPhase(int from, int to) {
        ServerLevel sl = sl();
        if (to >= 1 && from < 1) {
            core.actionbar(core.arenaRadius() + 8, ui("phase2"));
            cooldown.put("blades", to == 1 ? 50 : 100);
            if (to == 1 && !core.inScene()) {
                stand(ArisMath.PHASE2);
                boss.play("phase2");
                Fx.play(sl, Fx.fx("aris_phase2").caster(boss).at(boss.position()).yaw(boss.getYRot()).attach(boss));
                core.play(new BossTimeline("phase2", ArisMath.PHASE2_ROAR + 1).at(ArisMath.PHASE2_ROAR, () -> core.sound("aris.phase", 4, 1)));
            }
        }
        if (to >= 2 && from < 2) {
            core.actionbar(core.arenaRadius() + 8, ui("phase3"));
            cooldown.put("reforge", 120);
            if (!core.inScene()) {
                stand(ArisMath.PHASE3);
                boss.play("phase3");
            }
            Fx.play(sl, Fx.fx("aris_phase3").caster(boss).at(boss.position()).yaw(boss.getYRot()).attach(boss));
            core.sound("aris.phase", 4, 0.8f);
            core.play(new BossTimeline("phase3", ArisMath.PHASE3_IGNITE + 1).at(ArisMath.PHASE3_IGNITE, () -> mythic(sl, true)));
        }
    }

    /** «Мифический сплав»: white-hot armour (texture), the aura, damage ×1.3 (her swings through the attribute, the rest by hit()). */
    private void mythic(ServerLevel sl, boolean flash) {
        if (core.inFinale()) return;
        boss.setTex(ArisMath.TEX_MYTHIC);
        if (mythicFx < 0) mythicFx = Fx.play(sl, Fx.fx("aris_mythic_aura").caster(boss).at(boss.position()).attach(boss));
        var atk = boss.getAttribute(Attributes.ATTACK_DAMAGE);
        if (atk != null && atk.getModifier(MYTHIC_ID) == null)
            atk.addPermanentModifier(new AttributeModifier(MYTHIC_ID, "aris_mythic", cfg(ArisConfig.MYTHIC_DAMAGE) - 1, AttributeModifier.Operation.MULTIPLY_TOTAL));
        if (flash) core.sound("aris.forge", 3, 1.3f);
    }

    /** She stands for n ticks (AI off, not invulnerable — the fight goes on). */
    private void stand(int n) {
        core.lock(n, true, false);
        actingUntil = Math.max(actingUntil, boss.tickCount + n);
    }

    // ---------------------------------------------------------------- specials

    /** Returns false while it cannot start (a swing, a cast, another scene): the core asks again next tick. */
    boolean special(String id) {
        if (core.inScene() || acting()) return false;
        if (id.equals("forge")) forge(sl());
        else if (id.equals("last_blow")) lastBlow(sl());
        return true;
    }

    /**
     * «Горн» (4.0 s of animation): three strikes, the arena becomes a forge r24; from 3.3 s for 10 s the floor burns
     * (forge_floor_share_per_second of max health, through armour) everywhere but on 4–6 cold islands r2.2; 3 s of warning.
     */
    private void forge(ServerLevel sl) {
        Vec3 p = core.arena();
        stand(ArisMath.FORGE);
        boss.play("forge");
        List<ServerPlayer> who = core.scene("aris.forge", ArisMath.FORGE, BossNet.SCENE_BARS, BossConfig.get(BossConfig.SCENE_RADIUS), p, boss.getYRot(), -1);
        int n = ArisMath.islandCount(core.fighters().size(), cfg(ArisConfig.ISLANDS_MIN), cfg(ArisConfig.ISLANDS_MAX));
        double[][] off = ArisMath.islandOffsets(n, boss.getRandom().nextDouble() * Math.PI * 2, core.arenaRadius());
        core.play(new BossTimeline("scene:forge", ArisMath.FORGE)
                .at(0, () -> core.sound("aris.forge", 4, 1))
                .at(ArisMath.FORGE_FX, () -> {
                    clearForge(sl);
                    forgeAt = p;
                    forgeFx.add(Fx.play(sl, Fx.fx("aris_forge").at(p).yaw(0)));
                    for (double[] o : off) {
                        Vec3 q = ground(sl, p.add(o[0], 0, o[1]));
                        islands.add(q);
                        forgeFx.add(Fx.play(sl, Fx.fx("aris_island").at(q)));
                    }
                    long now = sl.getGameTime();
                    floorFrom = now + ArisMath.FORGE_FLOOR_FROM;
                    floorTo = floorFrom + Math.min(ArisMath.FORGE_FLOOR_TO - ArisMath.FORGE_FLOOR_FROM, cfg(ArisConfig.FORGE_SECONDS) * 20);
                    forgeEnd = now + ArisMath.FORGE_FLOOR_TO;
                    core.title(who, "aris_forge", ArisMath.FORGE_TITLE_HOLD, null);
                    core.actionbar(core.arenaRadius() + 8, ui("forge_warn"));
                })
                .at(ArisMath.FORGE_FX + 30, () -> core.actionbar(core.arenaRadius() + 8, ui("forge_warn")))
                .at(ArisMath.FORGE_STRIKES[0], this::forgeStrike)
                .at(ArisMath.FORGE_STRIKES[1], this::forgeStrike)
                .at(ArisMath.FORGE_STRIKES[2], this::forgeStrike)
                .at(ArisMath.FORGE_IGNITE, () -> {
                    core.sound(p, "aris.forge", 5, 0.8f);
                    core.actionbar(core.arenaRadius() + 8, ui("forge"));
                }));
    }

    private void forgeStrike() {
        Vec3 q = boss.position().add(fwd().scale(ArisMath.FORGE_FWD));
        Fx.play(sl(), Fx.fx("aris_slam").at(q).yaw(boss.getYRot()));
        core.sound("aris.slam", 3, 1);
    }

    private void tickForge(ServerLevel sl) {
        if (forgeAt == null) return;
        long now = sl.getGameTime();
        if (now >= forgeEnd) {
            core.actionbar(core.arenaRadius() + 8, ui("forge_end"));
            forgeAt = null;
            islands.clear();
            forgeFx.clear();   // they end by themselves (300 ticks)
            return;
        }
        if (now < floorFrom || now >= floorTo || (now - floorFrom) % 20 != 0 || core.inFinale()) return;
        double r = core.arenaRadius() + 2;
        for (LivingEntity e : targets(forgeAt, r, 6)) {
            if (!(e instanceof Player) || !onFloor(sl, e) || onIsland(e)) continue;
            e.hurt(core.mechanicDamage(), (float) (e.getMaxHealth() * cfg(ArisConfig.FLOOR_SHARE)));
            e.addEffect(new MobEffectInstance(Aris.SCORCHED.get(), 30, 0, false, true, true));
            Fx.play(sl, Fx.fx("aris_forge_burn").caster(e).at(e.position()));
        }
    }

    private static boolean onFloor(ServerLevel sl, LivingEntity e) {
        return e.onGround() || e.getY() - ground(sl, e.position()).y < 0.6;
    }

    private boolean onIsland(LivingEntity e) {
        for (Vec3 q : islands) if (e.distanceToSqr(q.x, e.getY(), q.z) <= ArisMath.ISLAND_R * ArisMath.ISLAND_R) return true;
        return false;
    }

    private void clearForge(ServerLevel sl) {
        for (int id : forgeFx) Fx.stop(sl, id, "");
        forgeFx.clear();
        islands.clear();
        forgeAt = null;
    }

    /**
     * «Последний удар молота» (5.0 s): a wide stance, the aim r14 on the ground before her and the giant ghost hammer over it
     * (3.5 s of warning), it falls at 4.0 s: centre 75 → edge 30 inside r14, a push wave r30.
     */
    private void lastBlow(ServerLevel sl) {
        Vec3 p = ground(sl, boss.position().add(fwd().scale(ArisMath.LAST_FWD)));
        stand(ArisMath.LAST);
        boss.play("last_blow");
        Fx.play(sl, Fx.fx("aris_last_blow").at(p).yaw(boss.getYRot()));
        List<ServerPlayer> who = core.scene("aris.last_blow", ArisMath.LAST, BossNet.SCENE_BARS, BossConfig.get(BossConfig.SCENE_RADIUS), p, boss.getYRot(), -1);
        double r = cfg(ArisConfig.LAST_RADIUS);
        BossTimeline t = new BossTimeline("scene:last_blow", ArisMath.LAST)
                .at(0, () -> core.sound("aris.last_blow", 4, 1))
                .at(ArisMath.LAST_TITLE, () -> core.title(who, "aris_last_blow", ArisMath.LAST_TITLE_HOLD, null))
                .at(ArisMath.LAST_PEAK, () -> core.sound("aris.forge", 3, 0.6f))
                .at(ArisMath.LAST_BLOW, () -> {
                    core.sound(p, "aris.slam", 6, 0.6f);
                    core.sound(p, "aris.billet_explode", 4, 0.7f);
                    for (LivingEntity e : targets(p, 30, 10)) {
                        double d = Math.sqrt(e.distanceToSqr(p.x, e.getY(), p.z));
                        double dmg = ArisMath.lastBlowDamage(d, r, cfg(ArisConfig.LAST_CENTER), cfg(ArisConfig.LAST_EDGE));
                        if (dmg > 0) e.hurt(core.attackDamage(), (float) dmg);   // the strongest blow: not ×1.3 (balance: 75 is the top)
                        Vec3 out = e.position().subtract(p).multiply(1, 0, 1);
                        out = out.lengthSqr() < 1e-4 ? fwd() : out.normalize();
                        double k = cfg(ArisConfig.LAST_PUSH) * (1 - d / 30) + 0.3;
                        e.push(out.x * k, 0.45, out.z * k);
                        e.hurtMarked = true;
                    }
                });
        for (int w = 0; w < ArisMath.LAST_FALL; w += 20) t.at(w, () -> core.actionbar(r + 24, ui("last_blow_warn")));
        core.play(t);
    }

    // ---------------------------------------------------------------- her attacks (each with its own cooldown; a common gap)

    private boolean castSpell(ServerLevel sl) {
        LivingEntity t = boss.getTarget();
        if (t == null || !t.isAlive() || acting() || core.inScene() || boss.isNoAi()) return false;
        double d = boss.distanceTo(t);
        int phase = core.phase();
        List<String> can = new ArrayList<>();
        if (d < 7 && ready("slam")) can.add("slam");
        if (d > 2.5 && d < 11 && ready("metal_wave")) can.add("metal_wave");
        if (ready("anvils") && cfg(ArisConfig.ANVILS) > 0) can.add("anvils");
        if (phase >= 1 && ready("blades") && aliveBlades(sl) < cfg(ArisConfig.BLADES_MAX)) can.add("blades");
        if (phase >= 2 && ready("reforge")) can.add("reforge");
        if (d > 4 && d < 18 && ready("billet")) can.add("billet");
        if (ready("chains")) can.add("chains");
        if (ready("quench") && core.healthFrac() < 0.95) can.add("quench");
        if (d < 8 && ready("bellows")) can.add("bellows");
        if (can.isEmpty()) return false;
        String s = can.contains("blades") ? "blades" : can.get(boss.getRandom().nextInt(can.size()));   // a new forging first
        switch (s) {
            case "slam" -> slam(sl, t);
            case "metal_wave" -> metalWave(sl, t);
            case "anvils" -> anvils(sl);
            case "blades" -> forgeBlades(sl);
            case "reforge" -> reforge(sl);
            case "billet" -> billet(sl, t);
            case "chains" -> chains(sl, t);
            case "quench" -> quench(sl);
            default -> bellows(sl, t);
        }
        cooldown.put(s, cooldownOf(s) * 20);
        return true;
    }

    private static int cooldownOf(String s) {
        return switch (s) {
            case "slam" -> cfg(ArisConfig.SLAM_CD);
            case "metal_wave" -> cfg(ArisConfig.WAVE_CD);
            case "anvils" -> cfg(ArisConfig.ANVILS_CD);
            case "blades" -> cfg(ArisConfig.BLADES_CD);
            case "reforge" -> cfg(ArisConfig.REFORGE_CD);
            case "billet" -> cfg(ArisConfig.BILLET_CD);
            case "chains" -> cfg(ArisConfig.CHAINS_CD);
            case "quench" -> cfg(ArisConfig.QUENCH_CD);
            default -> cfg(ArisConfig.BELLOWS_CD);
        };
    }

    private boolean ready(String id) {
        return cooldown.getOrDefault(id, 0) <= 0;
    }

    /** The molten ring: the hammer into the ground 1.25 before her, a ring r0 → r8 in 1.1 s (26; jump it). */
    private void slam(ServerLevel sl, LivingEntity t) {
        face(yawTo(t.position()));
        stand(ArisMath.SLAM);
        boss.play("slam");   // windup swish: animation sound keyframe (0.5 s)
        Set<UUID> hitSet = new HashSet<>();
        Vec3[] at = {null};
        core.play(new BossTimeline("spell:slam", ArisMath.SLAM_IMPACT + ArisMath.SLAM_WAVE + 1)
                .at(ArisMath.SLAM_IMPACT, () -> {
                    at[0] = ground(sl, boss.position().add(fwd().scale(ArisMath.SLAM_FWD)));
                    Fx.play(sl, Fx.fx("aris_slam").at(at[0]).yaw(boss.getYRot()));
                    core.sound(at[0], "aris.slam", 3, 1);
                })
                .during(ArisMath.SLAM_IMPACT, ArisMath.SLAM_IMPACT + ArisMath.SLAM_WAVE, k -> {
                    if (at[0] == null) return;
                    for (LivingEntity e : targets(at[0], ArisMath.SLAM_RADIUS + 1, 4)) {
                        double d = Math.sqrt(e.distanceToSqr(at[0].x, e.getY(), at[0].z));
                        if (ArisMath.slamHits(d, k - ArisMath.SLAM_IMPACT, e.getY() - at[0].y) && hitSet.add(e.getUUID())) hit(e, cfg(ArisConfig.SLAM_DAMAGE), 2);
                    }
                }));
    }

    /** The fan of molten metal: 5 crests 2..10 blocks ahead (the fx shows them on the ground), width 3, once per player. */
    private void metalWave(ServerLevel sl, LivingEntity t) {
        float yaw = yawTo(t.position());
        face(yaw);
        stand(ArisMath.SLAM);
        boss.play("slam");
        Vec3 o = boss.position(), f = Vec3.directionFromRotation(0, yaw), side = new Vec3(-f.z, 0, f.x);
        Set<UUID> hitSet = new HashSet<>();
        core.play(new BossTimeline("spell:metal_wave", ArisMath.SLAM_IMPACT + ArisMath.WAVE_CRESTS * ArisMath.WAVE_STEP + 1)
                .at(ArisMath.SLAM_IMPACT, () -> {
                    Fx.play(sl, Fx.fx("aris_metal_wave").at(o).yaw(yaw));
                    core.sound("aris.slam", 2.5f, 1.1f);
                })
                .during(ArisMath.SLAM_IMPACT, ArisMath.SLAM_IMPACT + ArisMath.WAVE_CRESTS * ArisMath.WAVE_STEP, k -> {
                    int crest = ArisMath.crestAt(k - ArisMath.SLAM_IMPACT);
                    if (crest == 0) return;
                    for (LivingEntity e : targets(o.add(f.scale(crest * ArisMath.WAVE_SPACING)), 3, 3)) {
                        Vec3 d = e.position().subtract(o);
                        if (ArisMath.crestHits(crest, d.dot(f), d.dot(side)) && e.getY() - o.y < 1.5 && hitSet.add(e.getUUID()))
                            hit(e, cfg(ArisConfig.WAVE_DAMAGE), 2);
                    }
                }));
    }

    /** Anvils grow from the ground (2, with 4+ players 3) for 8 s: obstacles; one grown under a player hurts and tosses. */
    private void anvils(ServerLevel sl) {
        List<ServerPlayer> fighters = core.fighters();
        if (fighters.isEmpty()) return;
        stand(ArisMath.CAST);
        boss.play("cast");
        int n = ArisMath.anvilCount(fighters.size(), cfg(ArisConfig.ANVILS), cfg(ArisConfig.ANVILS_BIG));
        core.play(new BossTimeline("spell:anvils", ArisMath.CAST_AT + 1).at(ArisMath.CAST_AT, () -> {
            core.actionbar(core.arenaRadius() + 8, ui("anvil"));
            core.sound("aris.anvil", 3, 1);
            for (int i = 0; i < n; i++) {
                ServerPlayer p = fighters.get(i % fighters.size());
                double a = boss.getRandom().nextDouble() * Math.PI * 2, d = i < fighters.size() ? boss.getRandom().nextDouble() * 1.2 : 2.5 + boss.getRandom().nextDouble() * 3;
                Vec3 q = ground(sl, p.position().add(Math.cos(a) * d, 0, Math.sin(a) * d));
                float yaw = boss.getRandom().nextBoolean() ? 0 : 90;
                ArisAnvilEntity e = Aris.ANVIL.get().create(sl);
                if (e == null) continue;
                e.moveTo(q.x, q.y, q.z, yaw, 0);
                sl.addFreshEntity(e);
                Anvil an = new Anvil();
                an.e = e;
                an.left = cfg(ArisConfig.ANVIL_SECONDS) * 20;
                an.fx = Fx.play(sl, Fx.fx("aris_anvil_rise").at(q).yaw(yaw));
                anvils.add(an);
            }
        }));
    }

    private void tickAnvils(ServerLevel sl) {
        for (int i = 0; i < anvils.size(); i++) {
            Anvil an = anvils.get(i);
            ArisAnvilEntity e = an.e;
            if (e.isAlive() && e.tickCount <= ArisMath.ANVIL_GROW && e.tickCount >= 6) {
                AABB box = e.getBoundingBox();
                for (LivingEntity v : sl.getEntitiesOfClass(LivingEntity.class, box.inflate(0.05))) {
                    if (!canHurt(v) || !an.hit.add(v.getUUID())) continue;
                    v.hurt(core.attackDamage(), (float) cfg(ArisConfig.ANVIL_RISE_DAMAGE));
                    Vec3 out = v.position().subtract(e.position()).multiply(1, 0, 1);
                    out = out.lengthSqr() < 1e-4 ? new Vec3(1, 0, 0) : out.normalize();
                    v.teleportTo(v.getX(), box.maxY + 0.05, v.getZ());
                    v.push(out.x * 0.5, 0.7, out.z * 0.5);
                    v.hurtMarked = true;
                }
            }
            if (--an.left <= 0 || !e.isAlive()) {
                removeAnvil(sl, an);
                anvils.remove(i--);
            }
        }
    }

    private static void removeAnvil(ServerLevel sl, Anvil an) {
        Fx.stop(sl, an.fx, "");
        if (an.e.isAlive()) {
            Fx.play(sl, Fx.fx("aris_anvil_break").at(an.e.position()).yaw(an.e.getYRot()));
            an.e.discard();
        }
    }

    // ---------------------------------------------------------------- phase 2: blades

    private int aliveBlades(ServerLevel sl) {
        blades.removeIf(u -> !(sl.getEntity(u) instanceof ArisBladeEntity b && b.isAlive()));
        return blades.size();
    }

    int bladeCount() {
        return blades.size();
    }

    /** A forging over her head: three blades on 1.0 / 1.3 / 1.6 s of the fx, alive at most blades_max. */
    private void forgeBlades(ServerLevel sl) {
        stand(ArisMath.CAST);
        boss.play("cast");
        Vec3[] at = {null};
        BossTimeline t = new BossTimeline("spell:blades", ArisMath.CAST_AT + ArisMath.BLADE_TICKS[2] + 1).at(ArisMath.CAST_AT, () -> {
            at[0] = boss.position().add(0, 3, 0);
            Fx.play(sl, Fx.fx("aris_blades_forge").at(at[0]));
            core.actionbar(core.arenaRadius() + 8, ui("blades"));
            core.sound("aris.blade", 2, 0.8f);
        });
        int per = cfg(ArisConfig.BLADES_PER);
        for (int i = 0; i < per; i++) {
            int k = i;
            t.at(ArisMath.CAST_AT + ArisMath.BLADE_TICKS[i], () -> {
                if (at[0] == null || core.inFinale() || aliveBlades(sl) >= cfg(ArisConfig.BLADES_MAX)) return;
                double a = 2 * Math.PI * k / 3;
                ArisBladeEntity b = Aris.BLADE.get().create(sl);
                if (b == null) return;
                b.moveTo(at[0].x + Math.cos(a) * 2, at[0].y, at[0].z + Math.sin(a) * 2, 0, 0);
                sl.addFreshEntity(b);
                b.setup(boss, blades.size(), cfg(ArisConfig.BLADE_HP) * core.playerMultiplier(), 40 + k * 15);
                blades.add(b.getUUID());
                core.sound(at[0], "aris.anvil_ring", 1.2f, 1.4f);
            });
        }
        core.play(t);
    }

    /** Whom a blade darts at: a fighter within 20 of it (the chained first — «Арис охотно бьёт скованного»). */
    LivingEntity bladeTarget(ArisBladeEntity b) {
        ServerPlayer best = null;
        double bd = 20 * 20;
        for (ServerPlayer p : core.fighters()) {
            double d = p.distanceToSqr(b) * (CHAINED.get(p.getUUID()) == this ? 0.25 : 1);
            if (d < bd) {
                bd = d;
                best = p;
            }
        }
        return best;
    }

    void bladeHit(ArisBladeEntity b, LivingEntity e) {
        hit(e, cfg(ArisConfig.BLADE_DAMAGE), 0);
        Fx.play(sl(), Fx.fx("aris_blade_strike").at(e.position().add(0, e.getBbHeight() * 0.6, 0)).yaw(b.getYRot()));
    }

    // ---------------------------------------------------------------- phase 3: «перековка»

    private void reforge(ServerLevel sl) {
        ServerPlayer first = core.strongestEnemy();
        if (first == null) return;
        face(yawTo(first.position()));
        stand(ArisMath.CAST);
        boss.play("cast");
        List<ServerPlayer> marks = new ArrayList<>();
        marks.add(first);
        List<ServerPlayer> others = new ArrayList<>(core.fighters());
        others.remove(first);
        if (core.fighters().size() >= 5 && !others.isEmpty())
            for (int i = 1; i < cfg(ArisConfig.REFORGE_TARGETS_BIG) && !others.isEmpty(); i++) marks.add(others.remove(boss.getRandom().nextInt(others.size())));
        int dur = cfg(ArisConfig.REFORGE_SECONDS) * 20;
        core.play(new BossTimeline("spell:reforge", ArisMath.CAST_AT + 1).at(ArisMath.CAST_AT, () -> {
            for (ServerPlayer p : marks) {
                if (!p.isAlive()) continue;
                p.addEffect(new MobEffectInstance(Aris.REFORGED.get(), dur, 0, false, true, true));
                Fx.play(sl, Fx.fx("aris_reforge").caster(p).at(p.position()).attach(p).duration(dur));
                Fx.play(sl, Fx.fx("aris_reforge_hit").caster(p).at(p.position()));
                p.displayClientMessage(ui("reforge", dur / 20), true);
                core.sound(p.position(), "aris.reforge", 2, 1);
            }
        }));
    }

    // ---------------------------------------------------------------- the four new spells

    /** «Раскалённая заготовка»: a glowing billet thrown at a player; it lies 3 s pulsing (zone r3 visible), then bursts (40, fire). */
    private void billet(ServerLevel sl, LivingEntity t) {
        float yaw = yawTo(t.position());
        face(yaw);
        stand(ArisMath.BILLET);
        boss.play("billet");
        double a = boss.getRandom().nextDouble() * Math.PI * 2, off = boss.getRandom().nextDouble();
        Vec3 land = ground(sl, t.position().add(Math.cos(a) * off, 0, Math.sin(a) * off));
        ArisBilletEntity[] b = {null};
        int[] mesh = {-1}, lie = {-1};
        double[][] ends = new double[2][];
        int landAt = ArisMath.BILLET_THROW + ArisMath.BILLET_FLIGHT, boom = landAt + cfg(ArisConfig.BILLET_DELAY) * 20;
        core.play(new BossTimeline("spell:billet", boom + 1)
                .at(ArisMath.BILLET_THROW, () -> {
                    Fx.play(sl, Fx.fx("aris_billet_throw").at(boss.position()).yaw(yaw));
                    core.sound("aris.swing", 1, 1.3f);
                    Vec3 from = boss.position().add(0, 1.6, 0).add(Vec3.directionFromRotation(0, yaw).scale(0.5));
                    b[0] = Aris.BILLET.get().create(sl);
                    if (b[0] == null) return;
                    b[0].moveTo(from.x, from.y, from.z, yaw, 0);
                    sl.addFreshEntity(b[0]);
                    billets.add(b[0]);
                    ends[0] = new double[] {from.x, from.y, from.z};
                    ends[1] = new double[] {land.x, land.y, land.z};
                    mesh[0] = Fx.play(sl, Fx.mesh("aris_billet").caster(b[0]).at(from).attach(b[0]));
                })
                .during(ArisMath.BILLET_THROW + 1, landAt, k -> {
                    if (b[0] == null || !b[0].isAlive()) return;
                    double[] p = ArisMath.billetArc(ends[0], ends[1], k - ArisMath.BILLET_THROW, ArisMath.BILLET_FLIGHT);
                    b[0].moveTo(p[0], p[1], p[2], b[0].getYRot() + 25, 0);
                })
                .at(landAt, () -> {
                    if (b[0] == null || !b[0].isAlive()) return;
                    if (mesh[0] > 0) Fx.stop(sl, mesh[0], "");
                    lie[0] = Fx.play(sl, Fx.fx("aris_billet").caster(b[0]).at(land).attach(b[0]));
                    core.sound(land, "aris.billet", 2, 1);
                    for (ServerPlayer p : core.playersNear(core.arenaRadius() + 8))
                        if (p.distanceToSqr(land) < 12 * 12) p.displayClientMessage(ui("billet"), true);
                })
                .at(boom, () -> {
                    if (b[0] == null || !b[0].isAlive()) return;
                    if (lie[0] > 0) Fx.stop(sl, lie[0], "");
                    Fx.play(sl, Fx.fx("aris_billet_explode").at(land));
                    core.sound(land, "aris.billet_explode", 3, 1);
                    double r = cfg(ArisConfig.BILLET_RADIUS);
                    Vec3 c = land.add(0, 0.5, 0);
                    for (LivingEntity e : targets(land, r, 3))
                        if (!covered(c, e.position())) hit(e, cfg(ArisConfig.BILLET_DAMAGE), 3);
                    b[0].discard();
                    billets.remove(b[0]);
                }));
    }

    /** «Цепи кузни»: chains from the ground hold a player in place for 4 s or until allies strike them 3 times. */
    private void chains(ServerLevel sl, LivingEntity t) {
        List<ServerPlayer> fighters = new ArrayList<>(core.fighters());
        fighters.removeIf(p -> chains.containsKey(p.getUUID()));
        if (fighters.isEmpty()) return;
        if (fighters.size() > 1) fighters.remove(t);   // not the one already at her hammer
        ServerPlayer victim = fighters.get(boss.getRandom().nextInt(fighters.size()));
        face(yawTo(victim.position()));
        stand(ArisMath.CHAINS);
        boss.play("chains");
        core.play(new BossTimeline("spell:chains", ArisMath.CHAINS_AT + 1).at(ArisMath.CHAINS_AT, () -> {
            if (!victim.isAlive() || victim.level() != sl) return;
            Chain c = new Chain();
            c.victim = victim;
            c.anchor = victim.position();
            c.left = cfg(ArisConfig.CHAINS_SECONDS) * 20;
            c.fx = Fx.play(sl, Fx.fx("aris_chains").caster(victim).at(victim.position()).attach(victim));
            chains.put(victim.getUUID(), c);
            CHAINED.put(victim.getUUID(), this);
            victim.addEffect(new MobEffectInstance(Aris.CHAINED.get(), c.left, 0, false, true, true));
            victim.displayClientMessage(ui("chains_self"), true);
            for (ServerPlayer p : core.playersNear(core.arenaRadius() + 8))
                if (p != victim) p.displayClientMessage(ui("chains", victim.getDisplayName()), true);
            core.sound(victim.position(), "aris.chains", 2, 1);
            boss.setTarget(victim);   // she gladly hits the chained one
        }));
    }

    private void tickChains(ServerLevel sl) {
        if (chains.isEmpty()) return;
        for (Chain c : new ArrayList<>(chains.values())) {
            ServerPlayer v = c.victim;
            if (--c.left <= 0 || !v.isAlive() || v.level() != sl || core.inFinale()) {
                release(sl, c);
                continue;
            }
            if (v.position().distanceToSqr(c.anchor) > 0.25 * 0.25) {
                v.connection.teleport(c.anchor.x, Math.min(v.getY(), c.anchor.y + 0.1), c.anchor.z, v.getYRot(), v.getXRot());
            }
            v.setDeltaMovement(0, Math.min(0, v.getDeltaMovement().y), 0);
        }
    }

    /** An ally struck the chains (ArisEvents: the attack on the chained player is cancelled). */
    void chainHit(ServerPlayer victim, ServerPlayer by) {
        Chain c = chains.get(victim.getUUID());
        if (c == null) return;
        ServerLevel sl = sl();
        c.hits++;
        Fx.play(sl, Fx.fx("aris_chains_hit").caster(victim).at(victim.position()));
        core.sound(victim.position(), "aris.chain_rattle", 1.2f, 1);
        if (c.hits >= cfg(ArisConfig.CHAINS_HITS)) {
            release(sl, c);
            by.displayClientMessage(ui("chains_break"), true);
        }
    }

    private void release(ServerLevel sl, Chain c) {
        chains.remove(c.victim.getUUID());
        CHAINED.remove(c.victim.getUUID(), this);
        Fx.stop(sl, c.fx, "");
        if (c.victim.isAlive()) {
            Fx.play(sl, Fx.fx("aris_chains_break").caster(c.victim).at(c.victim.position()));
            c.victim.removeEffect(Aris.CHAINED.get());
            c.victim.displayClientMessage(ui("chains_break"), true);
        }
        core.sound(c.victim.position(), "aris.chains_break", 1.5f, 1);
    }

    /** «Закалка»: she douses herself — 5 s of steam r5 where she stands: damage to her ×0.6 while she is in it, fog for players. */
    private void quench(ServerLevel sl) {
        stand(ArisMath.QUENCH);
        boss.play("quench");
        core.play(new BossTimeline("spell:quench", ArisMath.QUENCH_SPLASH + 1).at(ArisMath.QUENCH_SPLASH, () -> {
            quenchAt = boss.position();
            quenchUntil = sl.getGameTime() + cfg(ArisConfig.QUENCH_SECONDS) * 20L;
            Fx.play(sl, Fx.fx("aris_quench").at(quenchAt).yaw(boss.getYRot()).duration(cfg(ArisConfig.QUENCH_SECONDS) * 20));
            core.sound("aris.quench", 2, 1);
            core.actionbar(core.arenaRadius() + 8, ui("quench"));
        }));
    }

    private void tickQuench(ServerLevel sl) {
        if (quenchAt == null) return;
        if (sl.getGameTime() >= quenchUntil || core.inFinale()) {
            quenchAt = null;
            return;
        }
        double r = cfg(ArisConfig.QUENCH_RADIUS);
        int fog = Mth.clamp((int) Math.round(cfg(ArisConfig.QUENCH_FOG)) - 1, 0, 31);
        for (ServerPlayer p : core.playersNear(core.arenaRadius() + 16))
            if (p.distanceToSqr(quenchAt) <= r * r) p.addEffect(new MobEffectInstance(Aris.STEAMED.get(), 12, fog, false, false, true));
    }

    /** «Мехи»: a gust of hot air in a cone 60°×8 before her, 0.8 s of warning on the ground: 28, a push, fire. Anvils give cover. */
    private void bellows(ServerLevel sl, LivingEntity t) {
        float yaw = yawTo(t.position());
        face(yaw);
        stand(ArisMath.BELLOWS);
        boss.play("bellows");
        Vec3 o = boss.position();
        Fx.play(sl, Fx.fx("aris_bellows_warn").at(o).yaw(yaw));
        for (ServerPlayer p : core.playersNear(core.arenaRadius() + 8)) if (p.distanceToSqr(o) < 14 * 14) p.displayClientMessage(ui("bellows_warn"), true);
        core.play(new BossTimeline("spell:bellows", ArisMath.BELLOWS_GUST + 1).at(ArisMath.BELLOWS_GUST, () -> {
            Fx.play(sl, Fx.fx("aris_bellows").at(o).yaw(yaw));
            core.sound("aris.bellows", 2.5f, 1);
            Vec3 dir = Vec3.directionFromRotation(0, yaw);
            Vec3 from = o.add(0, 1.0, 0);
            for (LivingEntity e : targets(o, ArisMath.BELLOWS_LEN + 0.5, 3)) {
                Vec3 d = e.position().subtract(o);
                if (!ArisMath.inCone(d.x, d.z, yaw, ArisMath.BELLOWS_HALF_ANGLE, ArisMath.BELLOWS_LEN) || covered(from, e.position())) continue;
                hit(e, cfg(ArisConfig.BELLOWS_DAMAGE), cfg(ArisConfig.BELLOWS_BURN));
                double k = cfg(ArisConfig.BELLOWS_PUSH);
                e.push(dir.x * k, 0.35, dir.z * k);
                e.hurtMarked = true;
                Fx.play(sl, Fx.fx("aris_bellows_burn").caster(e).at(e.position()));
            }
        }));
    }

    /** A finisher began (the framework locked her): no swing / spell starts meanwhile. */
    void onFinisher() {
        actingUntil = Math.max(actingUntil, boss.tickCount + ArisMath.FINISHER);
    }

    // ---------------------------------------------------------------- the end

    /** Surrender / death: everything of hers goes (anvils, blades, billets, chains, the floor, the aura, the steam). */
    void cleanup(ServerLevel sl) {
        for (Anvil an : anvils) removeAnvil(sl, an);
        anvils.clear();
        for (UUID u : blades) if (sl.getEntity(u) instanceof ArisBladeEntity b && b.isAlive()) b.shatter(sl);
        blades.clear();
        for (ArisBilletEntity b : billets) if (b.isAlive()) b.discard();
        billets.clear();
        for (Chain c : new ArrayList<>(chains.values())) release(sl, c);
        clearForge(sl);
        if (mythicFx > 0) Fx.stop(sl, mythicFx, "");
        mythicFx = -1;
        quenchAt = null;
        actingUntil = 0;
    }
}
