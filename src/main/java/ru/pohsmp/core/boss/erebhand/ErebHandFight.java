package ru.pohsmp.core.boss.erebhand;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.Set;
import java.util.UUID;
import net.minecraft.network.chat.Component;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.util.Mth;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.RelativeMovement;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.entity.projectile.AbstractHurtingProjectile;
import net.minecraft.world.entity.projectile.Projectile;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.boss.BossConfig;
import ru.pohsmp.core.boss.BossCore;
import ru.pohsmp.core.boss.BossNet;
import ru.pohsmp.core.boss.BossTimeline;
import ru.pohsmp.core.fx.Fx;
import ru.pohsmp.core.spell.illusion.ButterflyDreamSpell;

/**
 * T31 «Эреб, Длань Лжи» — the fight (docs/specs/tasks/T31_ereb_hand_of_lies.md). The rapier, the ghost hand's slam on an area (every
 * phase), and by phase: 1 «Лживое слово» — doubles that carry real and false strikes of false flame; 2 «Длань» — the hand grabs a player
 * and squeezes it (the allies free it by hurting him), mirror walls round him send the players' projectiles back; 3 «Глава Культа» —
 * false flame and doubles at once, a mirror wall of fire on the arena edge. Specials: «Длань Лжи» (66%: the giant hand from the sky
 * catches one player, 6 s of the false arena), «Падение маски» (45%: one shard per player, break your own in 8 s), «Сон Бабочки:
 * Полное Раскрытие» (20%: the rest of the fight is fought inside the dream — on ButterflyDreamSpell, he is seen there, the giant hand
 * slams the dream). The four spells «Ложное пламя», «Стеклянная хватка», «Чужая клятва», «Тысяча отражений». The false death: the
 * phrase, butterflies, the dream breaks. Every strong attack has a visible warning, no line to any target. Numbers: [ereb_hand].
 */
public final class ErebHandFight {
    private final ErebHandEntity boss;
    private final BossCore core;

    private int busy, invuln;
    private int meleeIn = 20, slamIn = 60, gcd = 100;
    private final Map<String, Integer> cooldown = new HashMap<>();
    // phase 1 / 3: the doubles
    private int doublesIn = 60;
    private final List<ErebHandReflection> doubles = new ArrayList<>();
    // phase 2: the grab, the mirror walls
    private int grabIn = 40, grabLeft, squeezeIn, grabFx = -1;
    private double grabDealt;
    private ServerPlayer grabbed;
    private boolean grabbedNoGravity;
    private int wallsIn = 60, wallsLeft;
    private double wallTurn;
    private final List<Integer> wallFx = new ArrayList<>();
    private final Set<Integer> reflected = new HashSet<>();
    // phase 3: the wall of fire
    private int firewallFx = -1;
    private final Map<UUID, Double> wallDist = new HashMap<>();
    private final Map<UUID, Long> wallHit = new HashMap<>();
    // «Длань Лжи»
    private ErebHandGiant giant;
    private ServerPlayer holVictim;
    private boolean holNoGravity;
    private int holT = -1, holHold;
    private Vec3 holRoot = Vec3.ZERO;
    private float holYaw;
    private int holFx = -1;
    // «Падение маски»
    private final Map<UUID, ErebHandShard> shards = new LinkedHashMap<>();
    private final Map<Integer, Integer> shardFx = new HashMap<>();
    private final Map<UUID, Integer> arrows = new HashMap<>();
    private int maskT = -1, maskLeft, maskCount;
    /** Each shard keeps its place in the circle when others break. */
    private final Map<UUID, Integer> shardIndex = new HashMap<>();
    private boolean maskReturnDue;
    // «Чужая клятва»
    private ServerPlayer oathVictim, oathAlly;
    private int oathLeft;
    // «Полное Раскрытие»
    private boolean dreamOn;
    private int dreamSlamIn;
    private final Map<UUID, Integer> dreamFx = new HashMap<>();
    // the second four: things in flight («Пламя-подменыш», «Рой лжи»), the copies, the double of «Ложное отступление»; the mythic
    private final List<Flight> flights = new ArrayList<>();
    private final List<ErebHandTraitor> traitors = new ArrayList<>();
    private ErebHandReflection decoy;
    private int retreatLeft, decoyFx = -1;
    private boolean dawnDone;

    /** A fireball / glass butterfly simulated by the server: its fx follows it by Fx.move (no line to anyone). */
    private static final class Flight {
        final boolean swarm;
        Vec3 pos, dir;
        LivingEntity target, swapTo;
        boolean real = true, butterfly, passed;
        int t, swapAt = Integer.MAX_VALUE, flickerAt = Integer.MAX_VALUE, fx = -1;

        Flight(boolean swarm, Vec3 pos, Vec3 dir, LivingEntity target) {
            this.swarm = swarm;
            this.pos = pos;
            this.dir = dir;
            this.target = target;
        }
    }

    ErebHandFight(ErebHandEntity boss) {
        this.boss = boss;
        this.core = boss.bossCore();
        cooldown.put("false_flame", 20 * 10);   // the first ones come a little into the fight
        cooldown.put("glass_grip", 20 * 6);
        cooldown.put("foreign_oath", 20 * 16);
        cooldown.put("thousand", 20 * 14);
        cooldown.put("changeling_flame", 20 * 8);
        cooldown.put("false_retreat", 20 * 12);
        cooldown.put("traitor_reflection", 20 * 18);
        cooldown.put("swarm_of_lies", 20 * 12);
    }

    // ---------------------------------------------------------------- helpers

    private static Component ui(String key, Object... args) {
        return Component.translatable("ui.pohsmp_core.ereb_hand." + key, args).withStyle(s -> s.withColor(ErebHand.COLOR));
    }

    private ServerLevel sl() {
        return (ServerLevel) boss.level();
    }

    private double arenaR() {
        return core.arenaRadius() + 8;
    }

    private List<ServerPlayer> fighters() {
        List<ServerPlayer> out = new ArrayList<>(core.playersNear(core.arenaRadius() + 8));
        out.removeIf(p -> p.isCreative() || p.isSpectator() || !p.isAlive());
        return out;
    }

    private void face(LivingEntity t) {
        face(ErebHandMath.yawTo(boss.getX(), boss.getZ(), t.getX(), t.getZ()));
    }

    private void face(float yaw) {
        boss.setYRot(yaw);
        boss.setYHeadRot(yaw);
        boss.setYBodyRot(yaw);
    }

    private void anim(String name) {
        boss.serverTriggerAnimation(name);
    }

    private void fx(String id) {
        Fx.play(sl(), Fx.fx(id).caster(boss).at(boss.position()).yaw(boss.getYRot()));
    }

    /** His own hit (pohsmp_core:boss_attack: not scaled by difficulty, armour counts). Inside the dream it is a dream hit (T22). */
    private void hit(LivingEntity e, double dmg) {
        if (!e.isAlive()) return;
        e.invulnerableTime = 0;
        e.hurt(core.attackDamage(), (float) dmg);
    }

    /** T32 «Сломать блок»: not busy, nothing held, no mask scene. */
    boolean guardBreakFree() {
        return busy <= 0 && !core.locked() && !core.inScene() && grabbed == null && holVictim == null && maskT < 0 && !maskReturnDue;
    }

    /** T32: his heavy hit — the rapier (attack_damage with the enrage) or the ghost hand's slam, whichever is stronger. */
    double guardBreakDamage() {
        return ru.pohsmp.core.boss.BossGuardBreakMath.heavy(thrustDamage(), ErebHandConfig.d(ErebHandConfig.SLAM_DAMAGE));
    }

    /** A reflection's strike: his hit (the finisher and the dream see the boss behind it). */
    void reflectionHit(LivingEntity e, double dmg) {
        hit(e, dmg);
    }

    private double thrustDamage() {
        return boss.getAttributeValue(net.minecraft.world.entity.ai.attributes.Attributes.ATTACK_DAMAGE);
    }

    private static Vec3 ground(ServerLevel sl, Vec3 p) {
        int y = sl.getHeight(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES, Mth.floor(p.x), Mth.floor(p.z));
        return Math.abs(y - p.y) <= 6 ? new Vec3(p.x, y, p.z) : p;
    }

    private Vec3 free(ServerLevel sl, Vec3 p) {
        for (double up = 0; up <= 2; up += 1) {
            Vec3 q = p.add(0, up, 0);
            if (sl.noCollision(boss, boss.getDimensions(boss.getPose()).makeBoundingBox(q))) return q;
        }
        return p;
    }

    private List<LivingEntity> targets(ServerLevel sl, Vec3 p, double r) {
        List<LivingEntity> out = new ArrayList<>();
        for (LivingEntity e : sl.getEntitiesOfClass(LivingEntity.class, new AABB(p, p).inflate(r, 6, r))) {
            if (e instanceof ErebHandBody || !e.isAlive()) continue;
            if (e instanceof Player pl && (pl.isCreative() || pl.isSpectator())) continue;
            if (e.distanceToSqr(p.x, e.getY(), p.z) > r * r || Math.abs(e.getY() - p.y) > 3) continue;
            out.add(e);
        }
        return out;
    }

    private void hide(boolean on) {
        core.lookFlag(BossNet.LOOK_HIDDEN, on);
    }

    /** Busy with something of his own for `ticks`: AI off (the fight goes on, he can be hit). */
    private void act(int ticks) {
        busy = Math.max(busy, ticks);
        core.lock(ticks, true, false);
    }

    private void play(BossTimeline t) {
        core.play(t);
    }

    private static void holdAt(ServerPlayer p, Vec3 feet) {
        p.connection.teleport(feet.x, feet.y, feet.z, 0, 0, java.util.EnumSet.of(RelativeMovement.X_ROT, RelativeMovement.Y_ROT));
        p.setDeltaMovement(Vec3.ZERO);
        p.fallDistance = 0;
    }

    private boolean gone(ServerPlayer p) {
        return p == null || !p.isAlive() || p.hasDisconnected() || p.level() != boss.level();
    }

    // ---------------------------------------------------------------- tick

    void begin() {
        core.actionbar(arenaR(), ui("phase1"));
    }

    void tick(ServerLevel sl) {
        doubles.removeIf(r -> r.isRemoved() || !r.isAlive());
        if (!core.started() || core.inFinale()) return;
        if (invuln > 0) invuln--;
        tickGrab(sl);
        tickHandOfLies(sl);
        tickMask(sl);
        tickWalls(sl);
        if (firewallFx >= 0) firewall(sl);
        if (oathLeft > 0 && --oathLeft == 0) oathVictim = oathAlly = null;
        if (dreamOn) tickDream(sl);
        tickFlights(sl);
        traitors.removeIf(x -> x.isRemoved() || !x.isAlive());
        if (retreatLeft > 0) tickRetreat(sl);
        cooldown.replaceAll((k, v) -> Math.max(0, v - 1));
        if (gcd > 0) gcd--;
        if (meleeIn > 0) meleeIn--;
        if (slamIn > 0) slamIn--;
        if (doublesIn > 0) doublesIn--;
        if (grabIn > 0) grabIn--;
        if (wallsIn > 0) wallsIn--;
        if (busy > 0) {
            busy--;
            return;
        }
        if (maskReturnDue) {   // «Падение маски» is over: the mask comes back on his face (he waits for a free moment)
            maskReturn(sl);
            return;
        }
        if (core.locked() || core.inScene()) return;
        LivingEntity t = boss.getTarget();
        if (t == null || !t.isAlive()) return;
        double d = boss.distanceTo(t);
        if (phaseCast(sl, t, d)) return;
        if (gcd <= 0) {
            if (castSpell(sl, t, d)) {
                gcd = BossConfig.get(BossConfig.ABILITY_GCD) * 20;
                return;
            }
            gcd = 10;
        }
        if (core.onPillar(t)) return;   // BossGuard: one he cannot reach is hit only by ranged spells
        if (slamIn <= 0 && d < 4.5) {
            slam(sl, t);
            return;
        }
        if (meleeIn <= 0 && d < 3.0) melee(sl, t);
    }

    /** The phase's own move if one is due now. */
    private boolean phaseCast(ServerLevel sl, LivingEntity t, double d) {
        int phase = core.phase();
        if (phase == 0) {
            if (doublesIn <= 0 && doubles.isEmpty()) {
                lyingWord(sl);
                return true;
            }
        } else if (phase == 1) {
            if (grabIn <= 0 && grabbed == null && d < 3.6 && !core.onPillar(t) && t instanceof ServerPlayer p && p != holVictim
                    && ErebHandMath.inArc(t.getX() - boss.getX(), t.getZ() - boss.getZ(), boss.getYRot(), 60)) {
                grab(sl, p);
                return true;
            }
            if (wallsIn <= 0 && wallsLeft <= 0) {
                mirrorWalls(sl);
                return true;
            }
        } else {
            if (doublesIn <= 0 && doubles.isEmpty()) {
                cultHead(sl);
                return true;
            }
            if (grabIn <= 0 && grabbed == null && d < 3.6 && !core.onPillar(t) && t instanceof ServerPlayer p && p != holVictim
                    && ErebHandMath.inArc(t.getX() - boss.getX(), t.getZ() - boss.getZ(), boss.getYRot(), 60)) {
                grab(sl, p);
                return true;
            }
        }
        return false;
    }

    // ---------------------------------------------------------------- the rapier and the hand

    private void melee(ServerLevel sl, LivingEntity t) {
        face(t);
        boolean flurry = boss.getRandom().nextFloat() < 0.35f;
        int len = flurry ? ErebHandMath.FLURRY : ErebHandMath.LUNGE;
        act(len);
        anim(flurry ? "ereb_hand_flurry" : "ereb_hand_lunge");
        meleeIn = len + ErebHandMath.meleePause(ErebHandConfig.i(ErebHandConfig.MELEE_MIN), ErebHandConfig.i(ErebHandConfig.MELEE_MAX), boss.getRandom().nextDouble());
        BossTimeline tl = new BossTimeline("act:melee", len);
        int[] hits = flurry ? ErebHandMath.FLURRY_HITS : new int[] {ErebHandMath.LUNGE_HIT};
        for (int h : hits)
            tl.at(h, () -> {
                fx("ereb_thrust");
                core.sound("ereb.thrust", 1.5f, 0.9f);
                if (t.isAlive() && boss.distanceTo(t) < 3.4
                        && ErebHandMath.inArc(t.getX() - boss.getX(), t.getZ() - boss.getZ(), boss.getYRot(), 70)) hit(t, thrustDamage());
            });
        play(tl);
    }

    /** The ghost hand slams the ground ≈0.9 forward, 0.6 to his right: the raised hand + a mark on the ground are the warning. */
    private void slam(ServerLevel sl, LivingEntity t) {
        face(t);
        act(ErebHandMath.SLAM);
        anim("ereb_hand_slam");
        slamIn = ErebHandConfig.i(ErebHandConfig.SLAM_COOLDOWN) * 20;
        double r = ErebHandConfig.d(ErebHandConfig.SLAM_RADIUS);
        double[] o = ErebHandMath.local(boss.getYRot(), ErebHandMath.SLAM_RIGHT, ErebHandMath.SLAM_FWD);
        Vec3 at = ground(sl, boss.position().add(o[0], 0, o[1]));
        Fx.play(sl, Fx.fx("ereb_glass_rain_mark").at(at).scale(r / 2.0));   // T30's ground mark: 1.2 s of glass where it lands
        play(new BossTimeline("act:slam", ErebHandMath.SLAM).at(ErebHandMath.SLAM_HIT, () -> {
            fx("ereb_hand_slam");
            core.sound(at, "ereb_hand.slam", 2.5f, 1);
            for (LivingEntity e : targets(sl, at, r)) hit(e, ErebHandConfig.d(ErebHandConfig.SLAM_DAMAGE));
        }));
    }

    // ---------------------------------------------------------------- phase 1 «Лживое слово»: the doubles

    private void lyingWord(ServerLevel sl) {
        act(ErebHandMath.CAST);
        anim("ereb_hand_cast");
        fx("ereb_hand_cast");
        doublesIn = ErebHandConfig.i(ErebHandConfig.DOUBLES_INTERVAL) * 20;
        play(new BossTimeline("act:doubles", ErebHandMath.CAST).at(ErebHandMath.CAST_AT, () -> spawnDoubles(sl)));
    }

    /** n doubles round him: some carry a real strike of false flame, the rest only a glass glint. */
    private void spawnDoubles(ServerLevel sl) {
        core.sound("ereb.cast", 2, 1);
        int n = ErebHandConfig.i(ErebHandConfig.DOUBLES_COUNT);
        double[] rnd = new double[n];
        for (int i = 0; i < n; i++) rnd[i] = boss.getRandom().nextDouble();
        boolean[] real = ErebHandMath.pickReal(n, ErebHandConfig.i(ErebHandConfig.DOUBLES_REAL), rnd);
        int life = ErebHandConfig.i(ErebHandConfig.DOUBLES_SECONDS) * 20;
        double yaw0 = Math.toRadians(boss.getYRot());
        for (int k = 0; k < n; k++) {
            double a = yaw0 + Math.PI * 2 * (k + 0.5) / n;
            Vec3 at = free(sl, boss.position().add(-Math.sin(a) * 2.5, 0, Math.cos(a) * 2.5));
            ErebHandReflection r = ErebHand.REFLECTION.get().create(sl);
            if (r == null) continue;
            r.moveTo(at.x, at.y, at.z, boss.getYRot(), 0);
            r.setYHeadRot(boss.getYRot());
            r.setYBodyRot(boss.getYRot());
            r.setup(boss, ErebHandReflection.Kind.DOUBLE, real[k], life, ErebHandConfig.i(ErebHandConfig.DOUBLE_HITS), null);
            var hp = r.getAttribute(net.minecraft.world.entity.ai.attributes.Attributes.MAX_HEALTH);
            if (hp != null) hp.setBaseValue(boss.getMaxHealth());
            r.setHealth(r.getMaxHealth());
            sl.addFreshEntity(r);
            doubles.add(r);
            Fx.play(sl, Fx.fx("illusion_mirror_image_spawn").at(at));
        }
        Fx.play(sl, Fx.fx("illusion_mirror_image_spawn").at(boss.position()).caster(boss));
    }

    // ---------------------------------------------------------------- phase 2 «Длань»: the grab, the mirror walls

    private void grab(ServerLevel sl, ServerPlayer p) {
        face(p);
        act(ErebHandMath.GRAB);
        anim("ereb_hand_grab");
        grabIn = ErebHandConfig.i(ErebHandConfig.GRAB_COOLDOWN) * 20;
        core.sound("ereb_hand.grip", 1.5f, 1.2f);
        play(new BossTimeline("act:grab", ErebHandMath.GRAB).at(ErebHandMath.GRAB_AT, () -> {
            Fx.play(sl, Fx.fx("ereb_hand_grab").caster(boss).at(boss.position()).yaw(boss.getYRot()));
            core.sound("ereb_hand.grab", 2, 1);
            if (gone(p) || p == holVictim || boss.distanceTo(p) > 4.2
                    || !ErebHandMath.inArc(p.getX() - boss.getX(), p.getZ() - boss.getZ(), boss.getYRot(), 75)) return;   // missed: the hand closes on air
            grabbed = p;
            grabbedNoGravity = p.isNoGravity();
            p.setNoGravity(true);
            grabLeft = ErebHandConfig.i(ErebHandConfig.GRAB_SECONDS) * 20;
            grabDealt = 0;
            squeezeIn = 24;
            grabFx = Fx.play(sl, Fx.fx("ereb_hand_hold").caster(p).at(p.position()).attach(p));
            busy = Math.max(busy, grabLeft);
            core.lock(grabLeft, true, false);
            core.actionbar(arenaR(), ui("phase2"));   // «Длань» — рука хватает. Бейте по руке, чтобы освободить союзника.
        }));
    }

    private Vec3 holdPoint() {
        double[] o = ErebHandMath.local(boss.getYRot(), ErebHandMath.HOLD_RIGHT, ErebHandMath.HOLD_FWD);
        return new Vec3(boss.getX() + o[0], boss.getY() + ErebHandMath.HOLD_UP, boss.getZ() + o[1]);
    }

    private void tickGrab(ServerLevel sl) {
        if (grabbed == null) return;
        if (gone(grabbed) || ru.pohsmp.core.boss.BossFinisher.held(grabbed)) {
            dropGrab(sl, false);
            return;
        }
        holdAt(grabbed, holdPoint());
        if (--squeezeIn == 0) {
            anim("ereb_hand_squeeze");
            ServerPlayer p = grabbed;
            play(new BossTimeline("act:squeeze", ErebHandMath.SQUEEZE).at(ErebHandMath.SQUEEZE_AT, () -> {
                if (p != grabbed || gone(p)) return;
                Fx.play(sl, Fx.fx("ereb_hand_squeeze").caster(p).at(p.position()));
                core.sound(p.position(), "ereb_hand.squeeze", 2, 1);
                hit(p, ErebHandConfig.d(ErebHandConfig.SQUEEZE_DAMAGE));
            }));
            squeezeIn = 30;
        }
        if (grabbed != null && --grabLeft <= 0) releaseGrab(sl, false);
    }

    /** The hand opens (time is up, or the allies broke it): ereb_hand_grab_release, the player falls free. */
    private void releaseGrab(ServerLevel sl, boolean broken) {
        ServerPlayer p = grabbed;
        dropGrab(sl, true);
        anim("ereb_hand_grab_release");
        core.unlock();
        busy = ErebHandMath.RELEASE;
        core.lock(ErebHandMath.RELEASE, true, false);
        if (p != null && !gone(p)) {
            Fx.play(sl, Fx.fx("ereb_hand_release").caster(p).at(p.position()));
            if (broken) core.sound(p.position(), "ereb_hand.shard_break", 2, 0.8f);
        }
    }

    /** Lets the held player go without the gesture (it died, the finisher took it, the fight ended). */
    private void dropGrab(ServerLevel sl, boolean gesture) {
        if (grabbed == null) return;
        ServerPlayer p = grabbed;
        grabbed = null;
        grabLeft = 0;
        if (grabFx >= 0) Fx.stop(sl, grabFx, "");
        grabFx = -1;
        p.setNoGravity(grabbedNoGravity);
        p.fallDistance = 0;
        if (!gesture) busy = 0;
    }

    /** Mirror walls round him: projectiles of the players that fly into one go back (now his). */
    private void mirrorWalls(ServerLevel sl) {
        act(ErebHandMath.CAST);
        anim("ereb_hand_cast");
        fx("ereb_hand_cast");
        wallsIn = ErebHandConfig.i(ErebHandConfig.MIRROR_WALLS_INTERVAL) * 20;
        play(new BossTimeline("act:walls", ErebHandMath.CAST).at(ErebHandMath.CAST_AT, () -> {
            stopWalls(sl);
            wallsLeft = ErebHandConfig.i(ErebHandConfig.MIRROR_WALLS_SECONDS) * 20;
            wallTurn = boss.getYRot() + 45;
            reflected.clear();
            core.sound("ereb_hand.mirror", 2, 1);
            for (double y : ErebHandMath.mirrorYaws(ErebHandConfig.i(ErebHandConfig.MIRROR_WALLS_COUNT), wallTurn))
                wallFx.add(Fx.play(sl, Fx.fx("ereb_hand_mirror").at(wallPos(y)).yaw((float) y)));
        }));
    }

    private Vec3 wallPos(double yaw) {
        double[] f = ErebHandMath.forward(yaw);
        double r = ErebHandConfig.d(ErebHandConfig.MIRROR_WALLS_RADIUS);
        return boss.position().add(f[0] * r, 0, f[1] * r);
    }

    private void tickWalls(ServerLevel sl) {
        if (wallsLeft <= 0) return;
        if (--wallsLeft == 0) {
            double[] ys = ErebHandMath.mirrorYaws(wallFx.size(), wallTurn);
            for (double y : ys) Fx.play(sl, Fx.fx("ereb_hand_mirror_break").at(wallPos(y)));
            stopWalls(sl);
            return;
        }
        wallTurn += 0.6;   // they turn slowly round him and keep up with him
        double[] yaws = ErebHandMath.mirrorYaws(wallFx.size(), wallTurn);
        if (boss.tickCount % 2 == 0)
            for (int i = 0; i < wallFx.size(); i++) Fx.move(sl, wallFx.get(i), wallPos(yaws[i]), (float) yaws[i]);
        double r = ErebHandConfig.d(ErebHandConfig.MIRROR_WALLS_RADIUS);
        Vec3 c = boss.position().add(0, boss.getBbHeight() * 0.5, 0);
        for (Projectile pr : sl.getEntitiesOfClass(Projectile.class, boss.getBoundingBox().inflate(r + 6))) {
            if (!(pr.getOwner() instanceof Player) || reflected.contains(pr.getId())) continue;
            Vec3 p = pr.position(), v = pr.getDeltaMovement(), n = p.add(v);
            double d0 = Math.sqrt((p.x - c.x) * (p.x - c.x) + (p.z - c.z) * (p.z - c.z));
            double d1 = Math.sqrt((n.x - c.x) * (n.x - c.x) + (n.z - c.z) * (n.z - c.z));
            if (!(d0 >= r - 0.4 && d1 <= r + 0.4 && d1 < d0) || Math.abs(p.y - c.y) > 2.5) continue;   // crossing the ring inwards this tick
            if (!ErebHandMath.facesMirror(ErebHandMath.yawTo(c.x, c.z, p.x, p.z), yaws, 24)) continue;
            reflected.add(pr.getId());
            pr.setDeltaMovement(v.scale(-1));
            if (pr instanceof AbstractHurtingProjectile h) {
                h.xPower = -h.xPower;
                h.yPower = -h.yPower;
                h.zPower = -h.zPower;
            }
            pr.setOwner(boss);
            pr.hurtMarked = true;
            Fx.play(sl, Fx.fx("ereb_hand_mirror_strike_fake").at(p));
            core.sound(p, "ereb_hand.shard_ring", 1.5f, 1.3f);
        }
    }

    private void stopWalls(ServerLevel sl) {
        for (int f : wallFx) if (f >= 0) Fx.stop(sl, f, "");
        wallFx.clear();
        wallsLeft = 0;
    }

    // ---------------------------------------------------------------- phase 3 «Глава Культа»

    /** The flame of Mellisto and the illusions at once: false flame circles and the doubles in one cast. */
    private void cultHead(ServerLevel sl) {
        doublesIn = (int) (ErebHandConfig.i(ErebHandConfig.DOUBLES_INTERVAL) * 20 * 0.8);
        falseFlame(sl);
        play(new BossTimeline("act:cult_head", ErebHandMath.FLAME_MARKS + 1).at(ErebHandMath.FLAME_MARKS, () -> spawnDoubles(sl)));
    }

    /** The mirror wall of fire on the arena edge (cult_leader_firewall in the ereb_hand style): crossing it burns. */
    private void firewall(ServerLevel sl) {
        double r = core.arenaRadius();
        Vec3 c = core.arena();
        long now = sl.getGameTime();
        for (LivingEntity e : sl.getEntitiesOfClass(LivingEntity.class, new AABB(c, c).inflate(r + 4, 12, r + 4))) {
            if (e instanceof ErebHandBody || e instanceof Player p && (p.isCreative() || p.isSpectator())) continue;
            double d = Math.sqrt(e.distanceToSqr(c.x, e.getY(), c.z));
            Double before = wallDist.put(e.getUUID(), d);
            if (before == null || !ErebHandMath.wallCrossed(before, d, r)) continue;
            if (now - wallHit.getOrDefault(e.getUUID(), Long.MIN_VALUE / 2) < 10) continue;
            wallHit.put(e.getUUID(), now);
            e.hurt(core.mechanicDamage(), (float) (e.getMaxHealth() * ErebHandConfig.d(ErebHandConfig.FIREWALL_SHARE)));
            e.setSecondsOnFire(ErebHandConfig.i(ErebHandConfig.FIREWALL_BURN));
            Vec3 in = c.subtract(e.position()).multiply(1, 0, 1);
            if (in.lengthSqr() > 1e-4) {
                double push = ErebHandConfig.d(ErebHandConfig.FIREWALL_PUSH);
                e.push(in.normalize().x * push, 0.3, in.normalize().z * push);
                e.hurtMarked = true;
            }
            Fx.play(sl, Fx.fx("cult_leader_firewall_burn").style("ereb_hand").caster(e).at(e.position()));
        }
    }

    // ---------------------------------------------------------------- phases

    void onPhase(int from, int to) {
        ServerLevel sl = sl();
        if (to == 1) {
            act(ErebHandMath.PHASE2);
            anim("ereb_hand_phase2");
            fx("ereb_hand_phase2");
            core.actionbar(arenaR(), ui("phase2"));
            play(new BossTimeline("phase", ErebHandMath.PHASE2).at(ErebHandMath.PHASE2_AT, () -> core.sound("ereb.phase", 4, 0.9f)));
            for (ErebHandReflection r : new ArrayList<>(doubles)) r.poof(sl);   // the doubles were phase 1's
            grabIn = ErebHandMath.PHASE2 + 40;
            wallsIn = ErebHandMath.PHASE2 + 20 * 6;
        } else if (to == 2) {
            stopWalls(sl);
            doublesIn = ErebHandMath.DAWN + ErebHandMath.PHASE3 + 20 * 4;
            if (!dawnDone) falseDawn(sl);   // mythic «Ложный рассвет» first, the mask cracks after it
            else phase3Crack(sl);
        }
    }

    /** ereb_hand_phase3: «Длань» to the mask, it cracks (ereb_hand_cracked); the mirror wall of fire rises on the arena edge. */
    private void phase3Crack(ServerLevel sl) {
        act(ErebHandMath.PHASE3);
        anim("ereb_hand_phase3");
        fx("ereb_hand_phase3");
        core.actionbar(arenaR(), ui("phase3"));
        play(new BossTimeline("phase", ErebHandMath.PHASE3).at(ErebHandMath.PHASE3_CRACK, () -> {
            boss.setMask(2);   // the mask cracks: ereb_hand_cracked
            core.sound("ereb_hand.crack", 3, 1);
            core.sound("ereb.phase", 4, 0.8f);
            if (firewallFx < 0) {
                double r = core.arenaRadius();
                firewallFx = Fx.play(sl, Fx.fx("cult_leader_firewall").style("ereb_hand").at(core.arena()).yaw(0).scale(r / 28.0));
                core.sound(core.arena(), "ereb_hand.flame", 4, 0.8f);
            }
        }));
    }

    // ---------------------------------------------------------------- specials

    /** Returns false while it cannot start (busy, a scene, something held): the core asks again next tick. */
    boolean special(String id) {
        if (busy > 0 || core.locked() || core.inScene() || grabbed != null || holVictim != null || maskT >= 0 || maskReturnDue) return false;
        switch (id) {
            case "hand_of_lies" -> handOfLies(sl());
            case "mask_fall" -> maskFall(sl());
            case "full_reveal" -> fullReveal(sl());
            default -> {}
        }
        return true;
    }

    /**
     * «Длань Лжи» (66%, once, the fight goes on): «Длань» to the sky, the hand flies up; on `descend` the giant hand comes down from the
     * clouds over the player who hurt him most (its shadow grows on the ground — the warning; it follows the player for the first
     * 0.7 s, then falls where it is), catches it in its fist, lifts it 2.5 blocks and shows it the false arena for 6 s.
     */
    private void handOfLies(ServerLevel sl) {
        ServerPlayer victim = core.strongestEnemy();
        if (victim == null) return;
        act(ErebHandMath.HOL);
        anim("ereb_hand_hand_of_lies");
        fx("ereb_hand_cast");
        core.sound("ereb.cast", 3, 0.8f);
        List<ServerPlayer> who = core.playersNear(BossConfig.get(BossConfig.SCENE_RADIUS));
        core.title(who, "ereb_hand_hand_of_lies", 50, null);
        core.actionbar(arenaR(), ui("hand_of_lies"));
        core.scene("ereb_hand.hand_of_lies", ErebHandMath.HOL_CATCH + 14, BossNet.SCENE_BARS, BossConfig.get(BossConfig.SCENE_RADIUS),
                victim.position(), boss.getYRot(), victim.getId());
        play(new BossTimeline("scene:hand_of_lies", ErebHandMath.HOL).at(ErebHandMath.HOL_DESCEND, () -> {
            if (gone(victim)) return;
            ErebHandGiant g = ErebHand.GIANT.get().create(sl);
            if (g == null) return;
            holVictim = victim;
            holT = 0;
            holYaw = ErebHandMath.yawTo(boss.getX(), boss.getZ(), victim.getX(), victim.getZ());
            holRoot = giantRoot(victim.position());
            g.setScale((float) ErebHandMath.GIANT_SCALE);
            g.setPose(ErebHandGiant.DESCEND);
            g.moveTo(holRoot.x, holRoot.y + ErebHandMath.GIANT_FROM, holRoot.z, holYaw, 0);
            g.lifeTicks(20 * 30);
            sl.addFreshEntity(g);
            giant = g;
            Fx.play(sl, Fx.fx("ereb_hand_dream_slam_warn").at(ground(sl, victim.position())).duration(ErebHandMath.HOL_FALL + 4));   // the palm's shadow
            core.sound(victim.position(), "ereb_hand.sky_hand", 4, 1);
        }));
    }

    /** The giant wrist for a held one whose feet are at `feet` (the fist ×5: feet 1.6 below the wrist and 2.5 forward of it). */
    private Vec3 giantRoot(Vec3 feet) {
        double[] f = ErebHandMath.forward(holYaw);
        return feet.add(-f[0] * ErebHandMath.FIST_FWD, ErebHandMath.FIST_DOWN, -f[1] * ErebHandMath.FIST_FWD);
    }

    private Vec3 fistFeet(Vec3 root) {
        double[] f = ErebHandMath.forward(holYaw);
        return root.add(f[0] * ErebHandMath.FIST_FWD, -ErebHandMath.FIST_DOWN, f[1] * ErebHandMath.FIST_FWD);
    }

    private void tickHandOfLies(ServerLevel sl) {
        if (holT < 0) return;
        holT++;
        ServerPlayer v = holVictim;
        int hold = ErebHandConfig.i(ErebHandConfig.HAND_OF_LIES_SECONDS) * 20;
        if (giant == null || giant.isRemoved()) {
            endHandOfLies(sl);
            return;
        }
        giant.lifeTicks(40);
        if (holT < ErebHandMath.HOL_FALL) {   // the fall: it follows the player for 14 ticks, then commits
            if (holT <= 14 && !gone(v)) holRoot = giantRoot(v.position());
            giant.moveTo(holRoot.x, holRoot.y + ErebHandMath.giantFall(holT), holRoot.z, holYaw, 0);
            return;
        }
        if (holT == ErebHandMath.HOL_FALL) {   // the catch
            giant.moveTo(holRoot.x, holRoot.y, holRoot.z, holYaw, 0);
            giant.setPose(ErebHandGiant.GRAB);
            core.sound(holRoot, "ereb_hand.grab", 4, 0.6f);
            if (gone(v) || v.position().distanceTo(fistFeet(holRoot)) > 2.6) {   // it got away: the fist closes on air and melts
                holVictim = null;
                endHandOfLies(sl);
                return;
            }
            holNoGravity = v.isNoGravity();
            v.setNoGravity(true);
            holHold = hold;
            hit(v, ErebHandConfig.d(ErebHandConfig.HAND_OF_LIES_DAMAGE));
            boss.setFalseArena(v.getUUID());
            Fx.play(sl, Fx.fx("ereb_hand_false_arena").caster(v).at(v.position()).attach(v).duration(hold + 4).only(v));
            holFx = Fx.play(sl, Fx.fx("ereb_hand_hold").caster(v).at(v.position()).attach(v));
            v.displayClientMessage(ui("false_arena"), true);
        }
        if (gone(v) || ru.pohsmp.core.boss.BossFinisher.held(v)) {
            endHandOfLies(sl);
            return;
        }
        int t = holT - ErebHandMath.HOL_FALL;
        Vec3 root = holRoot.add(0, ErebHandMath.GIANT_LIFT * ErebHandMath.ease(t / 20.0), 0);
        giant.moveTo(root.x, root.y, root.z, holYaw, 0);
        holdAt(v, fistFeet(root));
        if (t >= holHold) endHandOfLies(sl);
    }

    /** The fist opens and melts, the player falls free (2.5 blocks: no fall damage), the false arena is over. */
    private void endHandOfLies(ServerLevel sl) {
        ServerPlayer v = holVictim;
        holVictim = null;
        holT = -1;
        boss.setFalseArena(null);
        if (holFx >= 0) Fx.stop(sl, holFx, "");
        holFx = -1;
        if (giant != null && !giant.isRemoved()) {
            giant.setPose(ErebHandGiant.RELEASE);
            giant.lifeTicks(ErebHandMath.GIANT_RELEASE + 4);
        }
        giant = null;
        if (v != null) {
            v.setNoGravity(holNoGravity);
            v.fallDistance = 0;
            if (!gone(v)) Fx.play(sl, Fx.fx("ereb_hand_release").caster(v).at(v.position()));
        }
    }

    /**
     * «Падение маски» (45%, once, the fight goes on): «Длань» tears the mask off, it shatters — one shard per player of the fight,
     * circling the arena (1.5–3 blocks up, slowly), each with that player's reflection and name. 8 s to break one's own (one hit); a
     * hit on another's only rings; not broken — a strong hit (a share of max health, boss_mechanic). The arrow to one's own shard: 2 s.
     */
    private void maskFall(ServerLevel sl) {
        List<ServerPlayer> who = fighters();
        if (who.isEmpty()) return;
        act(ErebHandMath.MASK_FALL);
        anim("ereb_hand_mask_fall");
        fx("ereb_hand_mask_tear");
        List<ServerPlayer> watch = core.playersNear(BossConfig.get(BossConfig.SCENE_RADIUS));
        core.title(watch, "ereb_hand_mask_fall", 50, null);
        core.scene("ereb_hand.mask_fall", 40, BossNet.SCENE_BARS, BossConfig.get(BossConfig.SCENE_RADIUS), boss.position(), boss.getYRot(), -1);
        play(new BossTimeline("scene:mask_fall", ErebHandMath.MASK_FALL)
                .at(ErebHandMath.MASK_TEAR, () -> core.sound("ereb_hand.crack", 2, 1.2f))
                .at(ErebHandMath.MASK_SHATTER, () -> {
                    boss.setMaskOff(true);
                    core.sound("ereb_hand.mask_shatter", 3, 1);
                    List<ServerPlayer> now = fighters();
                    int n = now.size();
                    maskCount = n;
                    shardIndex.clear();
                    for (int i = 0; i < n; i++) {
                        ServerPlayer p = now.get(i);
                        ErebHandShard s = ErebHand.SHARD.get().create(sl);
                        if (s == null) continue;
                        Vec3 at = shardPos(i, n, 0);
                        s.moveTo(at.x, at.y, at.z, 0, 0);
                        s.setOwner(p);
                        s.fight = this;
                        sl.addFreshEntity(s);
                        shards.put(p.getUUID(), s);
                        shardIndex.put(p.getUUID(), i);
                        shardFx.put(s.getId(), Fx.play(sl, Fx.fx("ereb_hand_mask_shard").caster(s).at(at).attach(s)));
                        arrows.put(p.getUUID(), Fx.play(sl, Fx.fx("ereb_hand_mask_arrow").caster(p).at(arrowPos(p)).only(p)));
                        p.displayClientMessage(ui("mask_fall_hint"), true);
                    }
                    maskT = 0;
                    maskLeft = ErebHandConfig.i(ErebHandConfig.MASK_SECONDS) * 20;
                }));
    }

    private Vec3 shardPos(int i, int n, int t) {
        double r = Math.min(core.arenaRadius() * 0.6, 10);
        double[] o = ErebHandMath.shardOrbit(i, n, t, r);
        Vec3 c = core.arena();
        return new Vec3(c.x + o[0], ground(sl(), new Vec3(c.x + o[0], c.y, c.z + o[2])).y + o[1], c.z + o[2]);
    }

    private static Vec3 arrowPos(ServerPlayer p) {
        Vec3 look = Vec3.directionFromRotation(0, p.getYRot());
        return p.position().add(look.scale(1.2)).add(0, 1.2, 0);
    }

    private void tickMask(ServerLevel sl) {
        if (maskT < 0) return;
        maskT++;
        for (var en : new ArrayList<>(shards.entrySet())) {
            ErebHandShard s = en.getValue();
            Vec3 at = shardPos(shardIndex.getOrDefault(en.getKey(), 0), Math.max(maskCount, 1), maskT);
            s.moveTo(at.x, at.y, at.z, s.getYRot() + 2, 0);
            Integer ar = arrows.get(en.getKey());
            ServerPlayer p = sl.getServer().getPlayerList().getPlayer(en.getKey());
            if (ar != null && p != null && maskT <= ErebHandMath.MASK_ARROW) {   // the arrow in front of its chest turns to its shard
                Vec3 from = arrowPos(p);
                Vec3 to = at.subtract(from);
                float yaw = ErebHandMath.yawTo(from.x, from.z, at.x, at.z);
                float pitch = (float) -Math.toDegrees(Math.atan2(to.y, Math.sqrt(to.x * to.x + to.z * to.z)));
                Fx.move(sl, ar, from, yaw, pitch);
            }
        }
        if (maskT == ErebHandMath.MASK_ARROW) arrows.clear();
        if (--maskLeft > 0 && !shards.isEmpty()) return;
        // time is up: the shards not broken fly into their players
        for (var en : new ArrayList<>(shards.entrySet())) {
            ServerPlayer p = sl.getServer().getPlayerList().getPlayer(en.getKey());
            if (p != null && !gone(p) && !p.isCreative() && !p.isSpectator()) {
                Fx.play(sl, Fx.fx("ereb_hand_mask_shard_burst").caster(p).at(p.position()));
                core.sound(p.position(), "ereb_hand.shard_burst", 2, 1);
                p.invulnerableTime = 0;
                p.hurt(core.mechanicDamage(), (float) (p.getMaxHealth() * ErebHandConfig.d(ErebHandConfig.MASK_FAIL_SHARE)));
            }
            removeShard(sl, en.getValue());
        }
        maskT = -1;
        maskReturnDue = true;
    }

    /** Its own player broke it. */
    void shardBroken(ServerLevel sl, ErebHandShard s) {
        Fx.play(sl, Fx.fx("ereb_hand_mask_shard_break").caster(s).at(s.position()));
        core.sound(s.position(), "ereb_hand.shard_break", 2, 1);
        removeShard(sl, s);
    }

    /** Someone else's hit: it only rings. */
    void shardRing(ServerLevel sl, ErebHandShard s) {
        Fx.play(sl, Fx.fx("ereb_hand_mask_shard_ring").caster(s).at(s.position()));
        core.sound(s.position(), "ereb_hand.shard_ring", 1.5f, 1);
    }

    private void removeShard(ServerLevel sl, ErebHandShard s) {
        shards.values().remove(s);
        Integer f = shardFx.remove(s.getId());
        if (f != null) Fx.stop(sl, f, "");
        s.discard();
    }

    /** ereb_hand_mask_return: the shards fly back, on `mend` the mask is on his face again (mended, or cracked after phase 3). */
    private void maskReturn(ServerLevel sl) {
        maskReturnDue = false;
        act(ErebHandMath.MASK_RETURN);
        anim("ereb_hand_mask_return");
        fx("ereb_hand_mask_return");
        play(new BossTimeline("act:mask_return", ErebHandMath.MASK_RETURN).at(ErebHandMath.MASK_MEND, () -> {
            boss.setMaskOff(false);
            boss.setMask(ErebHandMath.maskAfterMend(core.phase()));
            core.sound("ereb_hand.crack", 2, 1.4f);
        }));
    }

    /**
     * «Сон Бабочки: Полное Раскрытие» (20%): the cast scene, then the dream (ButterflyDreamSpell, no hostile mobs as in T22) falls on
     * every player of the fight and lasts to the end of the fight. He is there (not hidden): the fight goes on inside the dream, his hits
     * there are dream hits (not real; a «death» wakes the dreamer elsewhere in the dream), the giant hand over the mirror world slams.
     */
    private void fullReveal(ServerLevel sl) {
        act(ErebHandMath.REVEAL);
        core.lock(ErebHandMath.REVEAL, true, true);
        anim("ereb_hand_full_reveal");
        fx("ereb_hand_full_reveal_cast");
        List<ServerPlayer> who = core.playersNear(BossConfig.get(BossConfig.SCENE_RADIUS));
        core.title(who, "ereb_hand_full_reveal", 60, null);
        core.scene("ereb_hand.full_reveal", ErebHandMath.REVEAL, BossNet.SCENE_BARS, BossConfig.get(BossConfig.SCENE_RADIUS), boss.position(),
                boss.getYRot(), -1);
        play(new BossTimeline("scene:full_reveal", ErebHandMath.REVEAL)
                .at(16, () -> core.sound("ereb.butterfly", 2, 0.9f))
                .at(ErebHandMath.REVEAL_CAST, () -> {
                    core.sound("ereb_hand.reveal", 4, 1);
                    double r = arenaR();
                    ButterflyDreamSpell.openDream(sl, boss, r, ErebHandConfig.i(ErebHandConfig.DREAM_MAX_MINUTES) * 20 * 60);
                    dreamOn = true;
                    dreamSlamIn = ErebHandConfig.i(ErebHandConfig.DREAM_SLAM_INTERVAL) * 20;
                    for (ServerPlayer p : ButterflyDreamSpell.dreamers(boss))
                        dreamFx.put(p.getUUID(), Fx.play(sl, Fx.fx("ereb_hand_dream_world").at(core.arena()).only(p)));
                    core.actionbar(arenaR(), ui("full_reveal"));
                }));
    }

    private void tickDream(ServerLevel sl) {
        if (boss.tickCount % 20 == 0) {   // a dreamer woke early (resisted, Blessing): its dream world goes
            Set<UUID> still = new HashSet<>();
            for (ServerPlayer p : ButterflyDreamSpell.dreamers(boss)) still.add(p.getUUID());
            for (var it = dreamFx.entrySet().iterator(); it.hasNext(); ) {
                var en = it.next();
                if (still.contains(en.getKey())) continue;
                Fx.stop(sl, en.getValue(), "");
                it.remove();
            }
        }
        if (--dreamSlamIn > 0) return;
        dreamSlamIn = ErebHandConfig.i(ErebHandConfig.DREAM_SLAM_INTERVAL) * 20;
        List<ServerPlayer> who = ButterflyDreamSpell.dreamers(boss);
        who.removeIf(this::gone);
        if (who.isEmpty()) return;
        ServerPlayer p = who.get(boss.getRandom().nextInt(who.size()));
        Vec3 at = ground(sl, p.position());
        double r = ErebHandConfig.d(ErebHandConfig.DREAM_SLAM_RADIUS);
        Fx.play(sl, Fx.fx("ereb_hand_dream_slam_warn").at(at).scale(r / 4.0));
        core.sound(at, "ereb_hand.sky_hand", 3, 1.2f);
        play(new BossTimeline("dream_slam", ErebHandMath.DREAM_SLAM_WARN + 1).at(ErebHandMath.DREAM_SLAM_WARN, () -> {
            Fx.play(sl, Fx.fx("ereb_hand_dream_slam").at(at).scale(r / 4.0));
            core.sound(at, "ereb_hand.slam", 4, 0.7f);
            for (LivingEntity e : targets(sl, at, r)) hit(e, ErebHandConfig.d(ErebHandConfig.DREAM_SLAM_DAMAGE));
        }));
    }

    /** The dream breaks: everyone wakes (the T22 waking scene), the dream worlds go. */
    private void endDream(ServerLevel sl) {
        if (!dreamOn && dreamFx.isEmpty()) return;
        dreamOn = false;
        ButterflyDreamSpell.wakeNow(boss);
        for (int f : dreamFx.values()) Fx.stop(sl, f, "");
        dreamFx.clear();
    }

    // ---------------------------------------------------------------- the four spells (no scene, each with its warning)

    private boolean castSpell(ServerLevel sl, LivingEntity t, double d) {
        List<String> can = new ArrayList<>();
        int players = fighters().size();
        boolean pillar = core.onPillar(t);
        for (String id : ErebHandMath.spellPool(core.phase())) {
            if (!ready(id) || pillar && !ErebHandMath.ranged(id)) continue;
            if (id.equals("glass_grip") && d >= ErebHandConfig.d(ErebHandConfig.GRIP_RANGE)) continue;
            if (id.equals("foreign_oath") && players < 2) continue;
            if (id.equals("false_retreat") && (d > 8 || retreatLeft > 0)) continue;
            if (id.equals("traitor_reflection") && !traitors.isEmpty()) continue;
            can.add(id);
        }
        if (can.isEmpty()) return false;
        String pick = can.get(boss.getRandom().nextInt(can.size()));
        boolean done = switch (pick) {
            case "false_flame" -> falseFlame(sl);
            case "glass_grip" -> glassGrip(sl, t);
            case "foreign_oath" -> foreignOath(sl);
            case "changeling_flame" -> changelingFlame(sl, t);
            case "false_retreat" -> falseRetreat(sl, t);
            case "traitor_reflection" -> traitorReflection(sl);
            case "swarm_of_lies" -> swarmOfLies(sl);
            default -> thousand(sl);
        };
        cooldown.put(pick, 20 * switch (pick) {
            case "false_flame" -> ErebHandConfig.i(ErebHandConfig.FLAME_COOLDOWN);
            case "glass_grip" -> ErebHandConfig.i(ErebHandConfig.GRIP_COOLDOWN);
            case "foreign_oath" -> ErebHandConfig.i(ErebHandConfig.OATH_COOLDOWN);
            case "changeling_flame" -> ErebHandConfig.i(ErebHandConfig.CHANGELING_COOLDOWN);
            case "false_retreat" -> ErebHandConfig.i(ErebHandConfig.RETREAT_COOLDOWN);
            case "traitor_reflection" -> ErebHandConfig.i(ErebHandConfig.TRAITOR_COOLDOWN);
            case "swarm_of_lies" -> ErebHandConfig.i(ErebHandConfig.SWARM_COOLDOWN);
            default -> ErebHandConfig.i(ErebHandConfig.THOUSAND_COOLDOWN);
        });
        return done;
    }

    private boolean ready(String id) {
        return cooldown.getOrDefault(id, 100) <= 0;
    }

    /**
     * «Ложное пламя»: 5 circles on the ground by the players (the first under each of them), marked for 1 s alike; then 3 burn (with a
     * faint golden rim) and 2 are decoys that burn nothing.
     */
    private boolean falseFlame(ServerLevel sl) {
        List<ServerPlayer> who = fighters();
        if (who.isEmpty()) return false;
        Collections.shuffle(who, new Random(boss.getRandom().nextLong()));
        act(ErebHandMath.FLAME);
        anim("ereb_hand_false_flame");
        int n = ErebHandConfig.i(ErebHandConfig.FLAME_CIRCLES);
        double r = ErebHandConfig.d(ErebHandConfig.FLAME_RADIUS);
        List<Vec3> at = new ArrayList<>();
        boolean[] real = new boolean[n];
        play(new BossTimeline("act:false_flame", ErebHandMath.FLAME_IGNITE + 1)
                .at(ErebHandMath.FLAME_MARKS, () -> {
                    for (int i = 0; i < n; i++) {
                        ServerPlayer p = who.get(ErebHandMath.flameOwner(i, who.size()));
                        double a = boss.getRandom().nextDouble() * Math.PI * 2, dd = i < who.size() ? 0 : 2.5 + boss.getRandom().nextDouble() * 2.5;
                        at.add(ground(sl, p.position().add(Math.cos(a) * dd, 0, Math.sin(a) * dd)));
                    }
                    double[] rnd = new double[n];
                    for (int i = 0; i < n; i++) rnd[i] = boss.getRandom().nextDouble();
                    boolean[] pick = ErebHandMath.pickReal(n, n - ErebHandConfig.i(ErebHandConfig.FLAME_DECOYS), rnd);
                    System.arraycopy(pick, 0, real, 0, n);
                    for (Vec3 q : at) Fx.play(sl, Fx.fx("ereb_hand_false_flame_mark").at(q).scale(r / 2.0));
                    core.actionbar(arenaR(), ui("false_flame"));
                    core.sound("ereb_hand.flame", 2, 1.2f);
                })
                .at(ErebHandMath.FLAME_IGNITE, () -> {
                    int burn = ErebHandConfig.i(ErebHandConfig.FLAME_SECONDS) * 20;
                    for (int i = 0; i < at.size(); i++)
                        Fx.play(sl, Fx.fx(real[i] ? "ereb_hand_false_flame_real" : "ereb_hand_false_flame_decoy").at(at.get(i)).scale(r / 2.0).duration(burn + 2));
                    core.sound("ereb_hand.flame", 3, 0.9f);
                    play(new BossTimeline("act:flame_burn", burn).during(0, burn, t -> {
                        if (t % 10 != 0) return;
                        for (int i = 0; i < at.size(); i++) {
                            if (!real[i]) continue;
                            for (LivingEntity e : targets(sl, at.get(i), r)) {
                                hit(e, ErebHandConfig.d(ErebHandConfig.FLAME_DAMAGE));
                                e.setSecondsOnFire(2);
                            }
                        }
                    }));
                }));
        return true;
    }

    /** «Стеклянная хватка»: a cone in front of him fills with glass for 1 s (the warning), then the hand closes it: damage and a pull. */
    private boolean glassGrip(ServerLevel sl, LivingEntity t) {
        face(t);
        act(ErebHandMath.GRIP);
        anim("ereb_hand_glass_grip");
        float yaw = boss.getYRot();
        Vec3 o = boss.position();
        double range = ErebHandConfig.d(ErebHandConfig.GRIP_RANGE), deg = ErebHandConfig.d(ErebHandConfig.GRIP_ANGLE);
        Fx.play(sl, Fx.fx("ereb_hand_glass_grip_warn").caster(boss).at(o).yaw(yaw).scale(range / 6.0));
        core.actionbar(16, ui("glass_grip"));
        play(new BossTimeline("act:glass_grip", ErebHandMath.GRIP).at(ErebHandMath.GRIP_AT, () -> {
            fx("ereb_hand_glass_grip");
            core.sound("ereb_hand.grip", 2, 1);
            for (LivingEntity e : targets(sl, o, range)) {
                if (!ErebHandMath.inCone(e.getX() - o.x, e.getZ() - o.z, yaw, deg, range)) continue;
                hit(e, ErebHandConfig.d(ErebHandConfig.GRIP_DAMAGE));
                Vec3 to = o.subtract(e.position()).multiply(1, 0, 1);
                if (to.lengthSqr() > 1e-3) {
                    double pull = ErebHandConfig.d(ErebHandConfig.GRIP_PULL);
                    e.push(to.normalize().x * pull, 0.2, to.normalize().z * pull);
                    e.hurtMarked = true;
                }
            }
        }));
        return true;
    }

    /** «Чужая клятва»: a mark on the one who hurts him most for 4 s — what it deals him goes half to its nearest ally (marked too). */
    private boolean foreignOath(ServerLevel sl) {
        ServerPlayer v = core.strongestEnemy();
        if (v == null) return false;
        ServerPlayer ally = null;
        double best = 16 * 16;
        for (ServerPlayer p : fighters()) {
            if (p == v) continue;
            double d = p.distanceToSqr(v);
            if (d < best) {
                best = d;
                ally = p;
            }
        }
        if (ally == null) return false;
        ServerPlayer a = ally;
        face(v);
        act(ErebHandMath.OATH);
        anim("ereb_hand_foreign_oath");
        play(new BossTimeline("act:oath", ErebHandMath.OATH).at(ErebHandMath.OATH_AT, () -> {
            if (gone(v) || gone(a)) return;
            int ticks = ErebHandConfig.i(ErebHandConfig.OATH_SECONDS) * 20;
            Fx.play(sl, Fx.fx("ereb_hand_oath_mark").caster(v).at(v.position()).attach(v).duration(ticks + 2));
            Fx.play(sl, Fx.fx("ereb_hand_oath_bound").caster(a).at(a.position()).attach(a).duration(ticks + 2));
            core.sound(v.position(), "ereb_hand.oath", 2, 1);
            oathVictim = v;
            oathAlly = a;
            oathLeft = ticks;
            v.displayClientMessage(ui("foreign_oath"), true);
            a.displayClientMessage(ui("foreign_oath"), true);
        }));
        return true;
    }

    /**
     * «Тысяча отражений»: mirrors rise round the fight; out of each in turn Ereb looks for a moment and thrusts at one player — from 2 of
     * the 6 a real reflection steps out beside its player (0.45 s before the thrust: the warning), the rest only glint.
     */
    private boolean thousand(ServerLevel sl) {
        List<ServerPlayer> who = fighters();
        if (who.isEmpty()) return false;
        act(ErebHandMath.THOUSAND);
        anim("ereb_hand_thousand_reflections");
        core.actionbar(arenaR(), ui("thousand_reflections"));
        int n = ErebHandConfig.i(ErebHandConfig.THOUSAND_MIRRORS);
        double cx = 0, cz = 0, cy = boss.getY();
        for (ServerPlayer p : who) {
            cx += p.getX() / who.size();
            cz += p.getZ() / who.size();
        }
        Vec3 centre = new Vec3(cx, cy, cz);
        List<Vec3> pts = new ArrayList<>();
        for (double[] q : ErebHandMath.ring(n, 9, cx, cz, boss.getRandom().nextDouble() * Math.PI * 2)) pts.add(ground(sl, new Vec3(q[0], cy, q[1])));
        double[] rnd = new double[n];
        for (int i = 0; i < n; i++) rnd[i] = boss.getRandom().nextDouble();
        boolean[] real = ErebHandMath.pickReal(n, ErebHandConfig.i(ErebHandConfig.THOUSAND_REAL), rnd);
        int[] fx = new int[n];
        int end = ErebHandMath.STRIKES_AT + n * ErebHandMath.STRIKE_GAP + ErebHandMath.REFL;
        BossTimeline tl = new BossTimeline("act:thousand", end + 1).at(ErebHandMath.MIRRORS_AT, () -> {
            core.sound("ereb_hand.mirror", 3, 1);
            for (int i = 0; i < n; i++) {
                Vec3 q = pts.get(i);
                fx[i] = Fx.play(sl, Fx.fx("ereb_hand_mirror").at(q).yaw(ErebHandMath.yawTo(q.x, q.z, centre.x, centre.z)));
            }
        });
        for (int i = 0; i < n; i++) {
            int k = i;
            tl.at(ErebHandMath.STRIKES_AT + i * ErebHandMath.STRIKE_GAP, () -> {
                Vec3 m = pts.get(k);
                List<ServerPlayer> alive = fighters();
                if (alive.isEmpty()) return;
                ServerPlayer p = alive.get(boss.getRandom().nextInt(alive.size()));
                if (!real[k]) {
                    Fx.play(sl, Fx.fx("ereb_hand_mirror_strike_fake").at(m).yaw(ErebHandMath.yawTo(m.x, m.z, p.getX(), p.getZ())));
                    return;
                }
                Fx.play(sl, Fx.fx("ereb_hand_mirror_strike_real").at(m).yaw(ErebHandMath.yawTo(m.x, m.z, p.getX(), p.getZ())).target(p));
                core.sound(m, "ereb_hand.mirror", 2, 1.4f);
                Vec3 dir = m.subtract(p.position()).multiply(1, 0, 1);
                dir = dir.lengthSqr() < 1e-4 ? new Vec3(0, 0, 1) : dir.normalize();
                Vec3 at = free(sl, p.position().add(dir.scale(1.6)));
                ErebHandReflection r = ErebHand.REFLECTION.get().create(sl);
                if (r == null) return;
                float yaw = ErebHandMath.yawTo(at.x, at.z, p.getX(), p.getZ());
                r.moveTo(at.x, at.y, at.z, yaw, 0);
                r.setYHeadRot(yaw);
                r.setYBodyRot(yaw);
                r.setup(boss, ErebHandReflection.Kind.STRIKE, true, ErebHandMath.REFL, 1, p);
                sl.addFreshEntity(r);
            });
        }
        tl.at(end, () -> {
            for (int i = 0; i < n; i++) {
                if (fx[i] >= 0) Fx.stop(sl, fx[i], "");
                Fx.play(sl, Fx.fx("ereb_hand_mirror_break").at(pts.get(i)));
            }
        });
        play(tl);
        return true;
    }

    // ---------------------------------------------------------------- the second four (owner 20.11; docs/inbox/2026-11-20_mgr_T31_spells2.md)

    /**
     * «Пламя-подменыш»: a fireball at a player (ereb_hand_changeling_flame_orb on the flying point); 0.5 s before half way it flickers gold
     * (…_warn — the hint), at half way it turns into a glass butterfly (…_swap, …_butterfly) and flies at the ally nearest that player (6
     * blocks; none — the player itself): …_hit and the damage.
     */
    private boolean changelingFlame(ServerLevel sl, LivingEntity t) {
        face(t);
        act(ErebHandMath.CHANGELING);
        anim("ereb_hand_changeling_flame");
        fx("ereb_hand_changeling_flame");
        core.actionbar(arenaR(), ui("changeling_flame"));
        play(new BossTimeline("act:changeling", ErebHandMath.CHANGELING).at(ErebHandMath.CHANGELING_AT, () -> {
            if (!t.isAlive()) return;
            double[] o = ErebHandMath.local(boss.getYRot(), -0.35, 0.6);   // out of «Длань» (his left hand)
            Vec3 from = boss.position().add(o[0], 1.5, o[1]);
            Vec3 aim = t.position().add(0, t.getBbHeight() * 0.5, 0);
            Flight f = new Flight(false, from, aim.subtract(from).normalize(), t);
            f.swapAt = ErebHandMath.changelingSwapTick(from.distanceTo(aim), ErebHandMath.CHANGELING_SPEED);
            f.flickerAt = ErebHandMath.changelingFlickerTick(f.swapAt);
            List<ServerPlayer> who = fighters();
            double[][] xz = new double[who.size()][];
            int ti = -1;
            for (int i = 0; i < who.size(); i++) {
                xz[i] = new double[] {who.get(i).getX(), who.get(i).getZ()};
                if (who.get(i) == t) ti = i;
            }
            f.swapTo = ti < 0 ? t : who.get(ErebHandMath.nearestAlly(xz, ti, ErebHandMath.CHANGELING_ALLY_R));
            f.fx = Fx.play(sl, Fx.fx("ereb_hand_changeling_flame_orb").at(from));
            flights.add(f);
            core.sound(from, "ereb_hand.changeling", 1.5f, 1);
        }));
        return true;
    }

    /**
     * «Рой лжи»: 12 glass butterflies at the players (…_swarm_true / …_swarm_false on each); 6 are false (they fly through: …_swarm_pass), 6
     * real — …_swarm_hit, a hit and blindness 1 s. The hint: the real ones ring quietly (ereb_hand.swarm_chime) and are gold-edged.
     */
    private boolean swarmOfLies(ServerLevel sl) {
        List<ServerPlayer> who = fighters();
        if (who.isEmpty()) return false;
        act(ErebHandMath.SWARM);
        anim("ereb_hand_swarm_of_lies");
        fx("ereb_hand_swarm_of_lies");
        core.actionbar(arenaR(), ui("swarm_of_lies"));
        play(new BossTimeline("act:swarm", ErebHandMath.SWARM).at(ErebHandMath.SWARM_AT, () -> {
            int n = ErebHandConfig.i(ErebHandConfig.SWARM_COUNT);
            double[] rnd = new double[n];
            for (int i = 0; i < n; i++) rnd[i] = boss.getRandom().nextDouble();
            boolean[] real = ErebHandMath.pickReal(n, ErebHandConfig.i(ErebHandConfig.SWARM_REAL), rnd);
            List<ServerPlayer> now = fighters();
            if (now.isEmpty()) return;
            double[] o = ErebHandMath.local(boss.getYRot(), 0.6, 0.9);   // out of the ghost hand
            Vec3 hand = boss.position().add(o[0], 2.2, o[1]);
            for (int i = 0; i < n; i++) {
                ServerPlayer p = now.get(i % now.size());
                double a = Math.PI * 2 * i / n;
                Vec3 from = hand.add(Math.cos(a) * 0.5, boss.getRandom().nextDouble() * 0.4, Math.sin(a) * 0.5);
                Flight f = new Flight(true, from, new Vec3(Math.cos(a), 0.6, Math.sin(a)).normalize(), p);
                f.real = real[i];
                f.butterfly = true;
                f.fx = Fx.play(sl, Fx.fx(f.real ? "ereb_hand_swarm_true" : "ereb_hand_swarm_false").at(from));
                flights.add(f);
            }
            core.sound(hand, "ereb_hand.swarm", 2, 1);
        }));
        return true;
    }

    private void endFlight(ServerLevel sl, Flight f) {
        if (f.fx >= 0) Fx.stop(sl, f.fx, "");
        f.fx = -1;
    }

    private void tickFlights(ServerLevel sl) {
        for (var it = flights.iterator(); it.hasNext(); ) {
            Flight f = it.next();
            f.t++;
            LivingEntity tgt = f.target;
            if (f.t > (f.swarm ? ErebHandMath.SWARM_LIFE : ErebHandMath.CHANGELING_LIFE) || tgt == null || !tgt.isAlive() || tgt.level() != sl) {
                endFlight(sl, f);
                it.remove();
                continue;
            }
            if (!f.swarm && !f.butterfly && f.t == f.flickerAt) Fx.play(sl, Fx.fx("ereb_hand_changeling_flame_warn").at(f.pos));   // the hint
            if (!f.swarm && !f.butterfly && f.t >= f.swapAt) {   // the swap: a glass butterfly now, at the ally
                f.butterfly = true;
                if (f.swapTo != null && f.swapTo.isAlive()) f.target = tgt = f.swapTo;
                endFlight(sl, f);
                Fx.play(sl, Fx.fx("ereb_hand_changeling_flame_swap").at(f.pos));
                f.fx = Fx.play(sl, Fx.fx("ereb_hand_changeling_flame_butterfly").at(f.pos));
                core.sound(f.pos, "ereb_hand.changeling", 1.2f, 1.4f);
            }
            Vec3 aim = tgt.position().add(0, tgt.getBbHeight() * 0.55, 0);
            Vec3 to = aim.subtract(f.pos);
            double speed = f.swarm ? ErebHandMath.SWARM_SPEED : f.butterfly ? ErebHandMath.BUTTERFLY_SPEED : ErebHandMath.CHANGELING_SPEED;
            if (!f.passed) {   // they home in (gently for the swarm: one can step aside)
                double turn = f.swarm ? (f.t < 12 ? 0.05 : 0.12) : 0.35;
                f.dir = f.dir.scale(1 - turn).add(to.normalize().scale(turn)).normalize();
            }
            f.pos = f.pos.add(f.dir.scale(speed));
            if (f.fx >= 0) Fx.move(sl, f.fx, f.pos, ErebHandMath.yawTo(0, 0, f.dir.x, f.dir.z),
                    (float) -Math.toDegrees(Math.asin(Math.max(-1, Math.min(1, f.dir.y)))));
            if (f.swarm && f.real && f.t % ErebHandMath.SWARM_CHIME == 0) core.sound(f.pos, "ereb_hand.swarm_chime", 0.35f, 1);
            double hitR = f.swarm ? ErebHandMath.SWARM_HIT_R : ErebHandMath.CHANGELING_HIT_R;
            if (f.passed || f.pos.distanceTo(aim) > hitR + tgt.getBbWidth() * 0.5) continue;
            if (f.swarm && !f.real) {   // a false one goes through
                f.passed = true;
                Fx.play(sl, Fx.fx("ereb_hand_swarm_pass").at(f.pos));
                f.t = Math.max(f.t, ErebHandMath.SWARM_LIFE - 8);
                continue;
            }
            if (!f.swarm && !f.butterfly) continue;   // the fireball only bites as a butterfly (it swaps half way anyway)
            hit(tgt, ErebHandConfig.d(f.swarm ? ErebHandConfig.SWARM_DAMAGE : ErebHandConfig.CHANGELING_DAMAGE));
            if (f.swarm) tgt.addEffect(new MobEffectInstance(MobEffects.BLINDNESS, ErebHandConfig.i(ErebHandConfig.SWARM_BLIND_TICKS), 0, false, false, true));
            Fx.play(sl, Fx.fx(f.swarm ? "ereb_hand_swarm_hit" : "ereb_hand_changeling_flame_hit").caster(tgt).at(tgt.position()));
            endFlight(sl, f);
            it.remove();
        }
    }

    /**
     * «Ложное отступление»: he leaps back (leap) and on landing (land) «opens up» — that is a double without a shadow
     * (ereb_hand_false_retreat_open, …_double). The real one is unseen 2 s and thrusts in the back of the first who comes within 3 blocks
     * of the double (ereb_hand_false_retreat_strike, hit 7); nobody — he comes out where the double stood (…_vanish).
     */
    private boolean falseRetreat(ServerLevel sl, LivingEntity t) {
        face(t);
        act(ErebHandMath.RETREAT_OPEN + ErebHandMath.RETREAT_WINDOW + 2);
        anim("ereb_hand_false_retreat");
        double[] fw = ErebHandMath.forward(boss.getYRot());
        Vec3 land = ground(sl, boss.position().add(-fw[0] * ErebHandMath.RETREAT_BACK, 0, -fw[1] * ErebHandMath.RETREAT_BACK));
        Fx.play(sl, Fx.fx("ereb_hand_false_retreat").caster(boss).at(boss.position()).yaw(boss.getYRot()).point("land", land));
        core.actionbar(arenaR(), ui("false_retreat"));
        play(new BossTimeline("act:false_retreat", ErebHandMath.RETREAT_OPEN + 1)
                .at(ErebHandMath.RETREAT_JUMP, () -> {
                    boss.setDeltaMovement(-fw[0] * 0.9, 0.35, -fw[1] * 0.9);
                    boss.hurtMarked = true;
                    core.sound("ereb_hand.retreat", 1.5f, 1);
                })
                .at(ErebHandMath.RETREAT_OPEN, () -> {
                    ErebHandReflection d = ErebHand.REFLECTION.get().create(sl);
                    if (d == null) return;
                    Vec3 at = boss.position();
                    d.moveTo(at.x, at.y, at.z, boss.getYRot(), 0);
                    d.setYHeadRot(boss.getYRot());
                    d.setYBodyRot(boss.getYRot());
                    d.setup(boss, ErebHandReflection.Kind.DECOY, false, ErebHandMath.RETREAT_WINDOW + 10, 1, null);
                    sl.addFreshEntity(d);
                    d.serverTriggerAnimation("ereb_hand_false_retreat_open");
                    decoy = d;
                    decoyFx = Fx.play(sl, Fx.fx("ereb_hand_false_retreat_double").caster(d).at(at).attach(d).duration(ErebHandMath.RETREAT_WINDOW + 2));
                    hide(true);
                    invuln = ErebHandMath.RETREAT_WINDOW + 2;
                    double[] f = ErebHandMath.forward(boss.getYRot());   // the real one stands unseen a little behind his double
                    Vec3 back = free(sl, at.add(-f[0] * 3, 0, -f[1] * 3));
                    boss.moveTo(back.x, back.y, back.z, boss.getYRot(), 0);
                    boss.getNavigation().stop();
                    boss.setDeltaMovement(Vec3.ZERO);
                    retreatLeft = ErebHandMath.RETREAT_WINDOW;
                }));
        return true;
    }

    private void tickRetreat(ServerLevel sl) {
        retreatLeft--;
        if (decoy == null || decoy.isRemoved()) {
            endRetreat(sl, null);
            return;
        }
        for (ServerPlayer p : fighters())
            if (p.distanceTo(decoy) < ErebHandMath.RETREAT_NEAR) {
                endRetreat(sl, p);
                return;
            }
        if (retreatLeft <= 0) endRetreat(sl, null);
    }

    /** The double was struck by someone: the trick is up — he strikes that one if near, else comes out. */
    void decoyStruck(ServerLevel sl, LivingEntity by) {
        if (retreatLeft <= 0) return;
        endRetreat(sl, by instanceof ServerPlayer p && decoy != null && p.distanceTo(decoy) < 6 ? p : null);
    }

    /** Out of hiding: behind `victim`'s back with the thrust in the back, or (null) where the double stood. */
    private void endRetreat(ServerLevel sl, ServerPlayer victim) {
        retreatLeft = 0;
        invuln = 0;
        Vec3 at = decoy != null ? decoy.position() : boss.position();
        float yaw = decoy != null ? decoy.getYRot() : boss.getYRot();
        if (decoyFx >= 0) Fx.stop(sl, decoyFx, "");
        decoyFx = -1;
        core.unlock();
        busy = 0;
        if (victim != null && !gone(victim)) {
            double[] b = ErebHandMath.forward(victim.getYRot());
            at = free(sl, victim.position().add(-b[0] * 1.2, 0, -b[1] * 1.2));
            yaw = ErebHandMath.yawTo(at.x, at.z, victim.getX(), victim.getZ());
        } else victim = null;
        ErebHandReflection d = decoy;
        decoy = null;
        boss.moveTo(at.x, at.y, at.z, yaw, 0);
        face(yaw);
        hide(false);
        if (victim == null) {   // nobody came: the double goes, he is there
            if (d != null && !d.isRemoved()) {
                Fx.play(sl, Fx.fx("ereb_hand_false_retreat_vanish").caster(d).at(d.position()));
                d.discard();
            }
            core.sound("ereb.appear", 2, 1);
            return;
        }
        ServerPlayer v = victim;
        act(ErebHandMath.RETREAT_STRIKE);
        anim("ereb_hand_false_retreat_strike");
        Fx.play(sl, Fx.fx("ereb_hand_false_retreat_strike").caster(boss).at(at).yaw(yaw).target(v));
        core.sound("ereb.appear", 2, 1.1f);
        play(new BossTimeline("act:retreat_strike", ErebHandMath.RETREAT_STRIKE).at(ErebHandMath.RETREAT_STRIKE_HIT, () -> {
            core.sound("ereb.thrust", 1.5f, 0.8f);
            if (d != null && !d.isRemoved()) {
                Fx.play(sl, Fx.fx("ereb_hand_false_retreat_vanish").caster(d).at(d.position()));
                d.discard();
            }
            if (!gone(v) && boss.distanceTo(v) < 3.6) hit(v, ErebHandConfig.d(ErebHandConfig.RETREAT_DAMAGE));
        }));
    }

    /**
     * «Отражение-предатель»: «Длань» at one player (mirror), a mirror rises 1.5 blocks before it (…_traitor_mirror); on emerge a glass copy
     * of that player (its skin and weapon) steps out (ErebHandTraitor) and attacks its allies for 6 s; its original breaks it with 1 hit,
     * the others with 3; not broken — it bursts into shards (r3).
     */
    private boolean traitorReflection(ServerLevel sl) {
        List<ServerPlayer> who = fighters();
        if (who.isEmpty()) return false;
        ServerPlayer orig = who.get(boss.getRandom().nextInt(who.size()));
        face(orig);
        act(ErebHandMath.TRAITOR);
        anim("ereb_hand_traitor_reflection");
        fx("ereb_hand_traitor_reflection");
        core.actionbar(arenaR(), ui("traitor_reflection"));
        Vec3[] at = {null};
        float[] yaw = {0};
        play(new BossTimeline("act:traitor", ErebHandMath.TRAITOR)
                .at(ErebHandMath.TRAITOR_MIRROR, () -> {
                    if (gone(orig)) return;
                    Vec3 look = Vec3.directionFromRotation(0, orig.getYRot());
                    at[0] = free(sl, ground(sl, orig.position().add(look.scale(ErebHandMath.TRAITOR_MIRROR_DIST))));
                    yaw[0] = ErebHandMath.yawTo(at[0].x, at[0].z, orig.getX(), orig.getZ());
                    Fx.play(sl, Fx.fx("ereb_hand_traitor_mirror").at(at[0]).yaw(yaw[0]));
                    core.sound(at[0], "ereb_hand.mirror", 2, 1.2f);
                })
                .at(ErebHandMath.TRAITOR_AT, () -> {
                    if (gone(orig) || at[0] == null) return;
                    ErebHandTraitor c = ErebHand.TRAITOR.get().create(sl);
                    if (c == null) return;
                    c.moveTo(at[0].x, at[0].y, at[0].z, yaw[0], 0);
                    c.setYHeadRot(yaw[0]);
                    c.setYBodyRot(yaw[0]);
                    c.setup(boss, orig, ErebHandConfig.i(ErebHandConfig.TRAITOR_SECONDS) * 20);
                    sl.addFreshEntity(c);
                    traitors.add(c);
                    orig.displayClientMessage(ui("traitor_hint"), true);
                    core.sound(at[0], "ereb_hand.reflection", 2, 1);
                }));
        return true;
    }

    /** A copy not broken in time: shards all round it. */
    void traitorBurst(ServerLevel sl, ErebHandTraitor c) {
        Fx.play(sl, Fx.fx("ereb_hand_traitor_burst").caster(c).at(c.position()));
        core.sound(c.position(), "ereb_hand.shard_burst", 2, 0.9f);
        for (LivingEntity e : targets(sl, c.position(), ErebHandConfig.d(ErebHandConfig.TRAITOR_BURST_RADIUS)))
            if (e != c) hit(e, ErebHandConfig.d(ErebHandConfig.TRAITOR_BURST_DAMAGE));
    }

    // ---------------------------------------------------------------- mythic «Ложный рассвет» (33%, once)

    /**
     * On entering «Глава Культа», before the mask cracks (ereb_hand_false_dawn 6 s, fx ereb_hand_false_dawn): he staggers; on kneel the bar
     * is hidden, he is invulnerable, the false victory sounds, the sky brightens — no title (the hint: the butterflies round him do not
     * fly away). On rise he stands; on wave the wave over the arena: within 6 blocks 60% of max health, the rest 20% (boss_mechanic); the
     * bar is back; then ereb_hand_phase3 (the mask cracks).
     */
    private void falseDawn(ServerLevel sl) {
        dawnDone = true;
        if (grabbed != null) releaseGrab(sl, false);
        if (retreatLeft > 0) endRetreat(sl, null);
        act(ErebHandMath.DAWN);
        anim("ereb_hand_false_dawn");
        fx("ereb_hand_false_dawn");
        core.scene("ereb_hand.false_dawn", ErebHandMath.DAWN_SCENE, BossNet.SCENE_BARS, BossConfig.get(BossConfig.SCENE_RADIUS), boss.position(),
                boss.getYRot(), -1);
        play(new BossTimeline("scene:false_dawn", ErebHandMath.DAWN)
                .at(ErebHandMath.DAWN_KNEEL, () -> {
                    core.setBar(false);
                    invuln = ErebHandMath.DAWN_INVULN;
                    core.sound("ereb_hand.false_victory", 3, 1);
                })
                .at(ErebHandMath.DAWN_RISE, () -> core.sound("ereb.appear", 3, 0.8f))
                .at(ErebHandMath.DAWN_WAVE, () -> {
                    core.sound("ereb_hand.dawn_wave", 4, 1);
                    double near = ErebHandConfig.d(ErebHandConfig.DAWN_NEAR_RADIUS);
                    for (ServerPlayer p : fighters()) {
                        double share = ErebHandMath.dawnShare(p.distanceTo(boss), near, ErebHandConfig.d(ErebHandConfig.DAWN_NEAR_SHARE),
                                ErebHandConfig.d(ErebHandConfig.DAWN_FAR_SHARE));
                        p.invulnerableTime = 0;
                        p.hurt(core.mechanicDamage(), (float) (p.getMaxHealth() * share));
                    }
                    core.setBar(true);
                })
                .then(() -> phase3Crack(sl)));
    }

    // ---------------------------------------------------------------- damage to him

    /** Called from his hurt (after the framework's filter). Returns the damage to take. */
    float onHurt(DamageSource src, float amount) {
        if (invuln > 0) return 0;
        ServerLevel sl = sl();
        if (grabbed != null && src.getEntity() instanceof Player p && p != grabbed) {   // «бейте по руке»: the allies break the grab
            grabDealt += amount;
            if (ErebHandMath.grabBroken(grabDealt, ErebHandConfig.d(ErebHandConfig.GRAB_BREAK_DAMAGE))) releaseGrab(sl, true);
        }
        if (oathLeft > 0 && oathVictim != null && src.getEntity() == oathVictim && oathAlly != null && !gone(oathAlly)) {
            double share = ErebHandMath.oathShare(amount, ErebHandConfig.d(ErebHandConfig.OATH_SHARE), ErebHandConfig.d(ErebHandConfig.OATH_MAX_HIT));
            if (share > 0) {
                oathAlly.invulnerableTime = 0;
                oathAlly.hurt(core.mechanicDamage(), (float) share);
                Fx.play(sl, Fx.fx("ereb_hand_oath_reflect").caster(oathAlly).at(oathAlly.position()));
            }
        }
        return amount;
    }

    // ---------------------------------------------------------------- the finisher

    /** The hand takes the victim by the torso, lifts it before him, squeezes; it cracks like glass and falls apart into butterflies. */
    void finisher(ServerLevel sl, ServerPlayer victim) {
        if (grabbed == victim) dropGrab(sl, false);
        if (holVictim == victim) endHandOfLies(sl);
        face(victim);
        anim("ereb_hand_finisher");
        Fx.play(sl, Fx.fx("ereb_hand_finisher").caster(boss).at(boss.position()).yaw(boss.getYRot()).target(victim));
        core.sceneFor(victim, "ereb_hand.finisher", ErebHandMath.FIN_CAM, BossNet.SCENE_LOCK_INPUT | BossNet.SCENE_NO_HUD, victim.position(),
                victim.getYRot(), victim.getId());
    }

    void finisherTick(ServerLevel sl, ServerPlayer victim, int t) {
        if (t == ErebHandMath.FIN_GRAB) core.sound("ereb_hand.grab", 2, 1);
        else if (t == ErebHandMath.FIN_SQUEEZE) core.sound(victim.position(), "ereb_hand.squeeze", 2, 0.9f);
        else if (t == ErebHandMath.FIN_SHATTER) core.sound(victim.position(), "ereb_hand.dissolve", 2, 1.2f);
    }

    // ---------------------------------------------------------------- the false death

    /**
     * Health is gone (LEAVE at a hair over zero; the framework already made him invulnerable and took the bar and the music): he
     * staggers, the hand breaks, «А вы...стали сильнее», a bow, he falls apart into butterflies; the dream breaks and everyone wakes.
     * No loot. Everyone near sees it (the camera on him).
     */
    void falseDeath() {
        ServerLevel sl = sl();
        cleanup(sl, false);
        boss.getNavigation().stop();
        anim("ereb_hand_false_death");
        fx("ereb_hand_false_death");
        double r = BossConfig.get(BossConfig.INTRO_RADIUS);
        core.scene("ereb_hand.false_death", ErebHandMath.DEATH, BossNet.SCENE_LOCK_INPUT | BossNet.SCENE_BARS | BossNet.SCENE_NO_HUD, r,
                boss.position(), boss.getYRot(), -1);
        core.play(new BossTimeline("scene:false_death", ErebHandMath.DEATH_END)
                .at(8, () -> core.sound("ereb_hand.crack", 2, 0.8f))
                .at(ErebHandMath.DEATH_HAND, () -> core.sound("ereb_hand.shard_break", 2, 0.7f))
                .at(ErebHandMath.DEATH_SPEAK, () -> core.say("ui.pohsmp_core.ereb_hand.defeat", 48, 60, boss.getBbHeight() + 1.2))
                .at(ErebHandMath.DEATH_VANISH, () -> {
                    core.sound("ereb_hand.dissolve", 4, 1);
                    endDream(sl);
                })
                .at(ErebHandMath.DEATH_HIDE, () -> {
                    hide(true);
                    Component line = ui("vanish");
                    for (ServerPlayer p : core.playersNear(r)) p.sendSystemMessage(line);
                })
                .then(core::endFinale));
    }

    /** Everything of his in the world goes (the doubles, the hold, the giant hand, the shards, the walls, the fire); endDream: the dream too. */
    void cleanup(ServerLevel sl, boolean endDream) {
        for (ErebHandReflection r : new ArrayList<>(doubles)) r.poof(sl);
        doubles.clear();
        dropGrab(sl, false);
        if (holVictim != null || giant != null) endHandOfLies(sl);
        for (ErebHandShard s : new ArrayList<>(shards.values())) removeShard(sl, s);
        shards.clear();
        arrows.clear();
        maskT = -1;
        maskReturnDue = false;
        stopWalls(sl);
        if (firewallFx >= 0) Fx.stop(sl, firewallFx, "");
        firewallFx = -1;
        oathLeft = 0;
        oathVictim = oathAlly = null;
        for (Flight f : flights) endFlight(sl, f);
        flights.clear();
        if (decoyFx >= 0) Fx.stop(sl, decoyFx, "");
        decoyFx = -1;
        for (ErebHandTraitor c : new ArrayList<>(traitors)) c.discard();
        traitors.clear();
        if (decoy != null && !decoy.isRemoved()) decoy.poof(sl);
        decoy = null;
        if (retreatLeft > 0) hide(false);
        retreatLeft = 0;
        if (endDream) endDream(sl);
    }
}
