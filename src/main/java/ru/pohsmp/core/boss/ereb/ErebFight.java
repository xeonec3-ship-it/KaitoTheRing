package ru.pohsmp.core.boss.ereb;

import io.redspace.ironsspellbooks.api.registry.SpellRegistry;
import io.redspace.ironsspellbooks.api.spells.AbstractSpell;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.capabilities.magic.TargetEntityCastData;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.Set;
import java.util.UUID;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.util.Mth;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.entity.living.LivingHurtEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.ServerConfig;
import ru.pohsmp.core.boss.BossConfig;
import ru.pohsmp.core.boss.BossCore;
import ru.pohsmp.core.boss.BossNet;
import ru.pohsmp.core.boss.BossTimeline;
import ru.pohsmp.core.fx.Fx;
import ru.pohsmp.core.spell.illusion.ButterflyDreamSpell;
import ru.pohsmp.core.spell.illusion.MirrorLabyrinthSpell;

/**
 * T30 Ereb's fight (docs/specs/tasks/T30_ereb_boss.md): magic by hand (a fan of glass shards — projectiles, no line to anyone) and the
 * rapier; the phases on the T22 mechanics — 1 «Две правды» («Отражения» with swaps, «Фантомная боль», «Ложный шаг»), 2 «Чужое лицо»
 * (a participant's look, «Пелена»), 3 «Предательство» (the allies look like him for 6 s; a hit on such an ally is a real hit on the
 * ally); the specials «Ложный союзник» (50%) and «Зеркальный лабиринт» (20%); the four spells «Танец клинков», «Обманная брешь»,
 * «Стеклянный дождь», «Шаг сквозь отражение»; the finale at 5%: «Сон бабочки» from his point and he is gone. Every strong attack
 * has a visible warning (glints behind the victim, marks on the ground, the open stance). Numbers: [ereb] (ErebConfig).
 */
public final class ErebFight {
    private final ErebEntity boss;
    private final BossCore core;

    /** He is in the middle of something of his own (ticks). */
    private int busy;
    /** Not hittable for a moment (vanished in a ripple): his own, so a soft lock is not turned into a hard one. */
    private int invuln;
    private int meleeIn = 20, shardsIn = 40, gcd = 100;
    private final Map<String, Integer> cooldown = new HashMap<>();
    // phase 1
    private int mirrorIn = 20, phantomIn = 200, falseStepIn = 140, swapIn = -1;
    private final List<ErebReflection> reflections = new ArrayList<>();
    // phase 2
    private int disguiseIn = -1, disguiseLeft, veilIn = -1, veilLeft, flickerIn = -1, flickerLeft;
    private int veilFx = -1;
    // phase 3
    private int betrayalIn = -1, betrayalLeft;
    private boolean betrayalHinted;
    private final List<Integer> betrayalFx = new ArrayList<>();
    final Set<UUID> deceived = new HashSet<>();
    // «Обманная брешь»
    private boolean feintOpen, countered;
    private int hiddenLeft;
    private static int TAG = 7_000_000;

    ErebFight(ErebEntity boss) {
        this.boss = boss;
        this.core = boss.bossCore();
        cooldown.put("blade_dance", 20 * 15);   // the first ones come a little into the fight
        cooldown.put("feint", 20 * 10);
        cooldown.put("glass_rain", 20 * 8);
        cooldown.put("mirror_step", 20 * 12);
    }

    // ---------------------------------------------------------------- helpers

    static SoundEvent sound(String id) {
        return BossCore.sound(id);
    }

    private static Component ui(String key, Object... args) {
        return Component.translatable("ui.pohsmp_core.ereb." + key, args).withStyle(s -> s.withColor(Ereb.COLOR));
    }

    private double arenaR() {
        return core.arenaRadius() + 8;
    }

    private List<ServerPlayer> fighters() {
        List<ServerPlayer> out = new ArrayList<>(core.playersNear(core.arenaRadius() + 8));
        out.removeIf(p -> p.isCreative() || p.isSpectator());
        return out;
    }

    private void face(LivingEntity t) {
        face(ErebMath.yawTo(boss.getX(), boss.getZ(), t.getX(), t.getZ()));
    }

    private void face(float yaw) {
        boss.setYRot(yaw);
        boss.setYHeadRot(yaw);
        boss.setYBodyRot(yaw);
    }

    private void anim(String name) {
        boss.serverTriggerAnimation(name);
    }

    /** His own hit (pohsmp_core:boss_attack: not scaled by difficulty, armour counts); one hit per tick at most per target. */
    private void hit(LivingEntity e, double dmg) {
        if (!e.isAlive()) return;
        e.invulnerableTime = 0;
        e.hurt(core.attackDamage(), (float) dmg);
    }

    /** A rapier thrust's own number: attack_damage (with the rapier and the enrage). */
    private double thrustDamage() {
        return boss.getAttributeValue(net.minecraft.world.entity.ai.attributes.Attributes.ATTACK_DAMAGE);
    }

    private void thrustFx() {
        Fx.play(sl(), Fx.fx("ereb_thrust").caster(boss).at(boss.position()).yaw(boss.getYRot()));
        core.sound("ereb.thrust", 1.5f, 1);
    }

    private ServerLevel sl() {
        return (ServerLevel) boss.level();
    }

    private static Vec3 ground(ServerLevel sl, Vec3 p) {
        int y = sl.getHeight(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES, Mth.floor(p.x), Mth.floor(p.z));
        return Math.abs(y - p.y) <= 6 ? new Vec3(p.x, y, p.z) : p;
    }

    /** A free spot for his body near p (not in a wall), else p. */
    private Vec3 free(ServerLevel sl, Vec3 p) {
        for (double up = 0; up <= 2; up += 1) {
            Vec3 q = p.add(0, up, 0);
            if (sl.noCollision(boss, boss.getDimensions(boss.getPose()).makeBoundingBox(q))) return q;
        }
        return p;
    }

    private void blinkTo(ServerLevel sl, Vec3 to, float yaw) {
        Fx.play(sl, Fx.fx("ereb_blink").caster(boss).at(boss.position()).yaw(boss.getYRot()));
        core.sound("ereb.vanish", 1.5f, 1.2f);
        Vec3 q = free(sl, to);
        boss.moveTo(q.x, q.y, q.z, yaw, 0);
        face(yaw);
        boss.getNavigation().stop();
        Fx.play(sl, Fx.fx("ereb_blink").at(q).yaw(yaw));   // no caster: just moved, the client still lerps him from the old spot and would draw it there (FX audit 21.11)
        core.sound(q, "ereb.appear", 1.5f, 1.2f);
    }

    private List<LivingEntity> targets(ServerLevel sl, Vec3 p, double r) {
        List<LivingEntity> out = new ArrayList<>();
        for (LivingEntity e : sl.getEntitiesOfClass(LivingEntity.class, new AABB(p, p).inflate(r, 6, r))) {
            if (e instanceof ErebBody || e instanceof ErebDreamPoint || !e.isAlive()) continue;
            if (e instanceof Player pl && (pl.isCreative() || pl.isSpectator())) continue;
            if (e.distanceToSqr(p.x, e.getY(), p.z) > r * r) continue;
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

    /** The scripts of his attacks (cancelled on the finale by the core). */
    private void play(BossTimeline t) {
        core.play(t);
    }

    /** True while the shards are ready: he keeps his distance (Chase). */
    boolean wantsRange() {
        return shardsIn <= 0 && busy <= 0;
    }

    // ---------------------------------------------------------------- tick

    void begin() {
        core.actionbar(arenaR(), ui("phase1"));
    }

    void tick(ServerLevel sl) {
        reflections.removeIf(r -> r.isRemoved() || !r.isAlive());
        if (!core.started() || core.inFinale()) return;
        if (invuln > 0) invuln--;
        if (hiddenLeft > 0 && --hiddenLeft == 0) hide(false);
        tickPhaseStates(sl);
        cooldown.replaceAll((k, v) -> Math.max(0, v - 1));
        if (gcd > 0) gcd--;
        if (meleeIn > 0) meleeIn--;
        if (shardsIn > 0) shardsIn--;
        if (busy > 0) {
            busy--;
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
        if (shardsIn <= 0 && d > 3.5 && d < 24) {
            shards(sl, t);
            return;
        }
        if (meleeIn <= 0 && d < 3.0) melee(sl, t);
    }

    /** The phase's illusions that run by themselves: copies and swaps, the disguise's time, the veil, the betrayal. */
    private void tickPhaseStates(ServerLevel sl) {
        if (mirrorIn > 0) mirrorIn--;
        if (phantomIn > 0) phantomIn--;
        if (falseStepIn > 0) falseStepIn--;
        if (disguiseIn > 0) disguiseIn--;
        if (veilIn > 0) veilIn--;
        if (betrayalIn > 0) betrayalIn--;
        // «Отражения»: about every swapEverySeconds he swaps places with a random copy, quietly
        List<ErebReflection> mirrors = new ArrayList<>();
        for (ErebReflection r : reflections) if (r.kind() == ErebReflection.Kind.MIRROR) mirrors.add(r);
        if (!mirrors.isEmpty() && swapIn > 0 && --swapIn == 0 && busy <= 0) {
            ErebReflection r = mirrors.get(boss.getRandom().nextInt(mirrors.size()));
            Vec3 a = boss.position(), b = r.position();
            float ya = boss.getYRot(), yb = r.getYRot();
            boss.moveTo(b.x, b.y, b.z, yb, 0);
            r.moveTo(a.x, a.y, a.z, ya, 0);
            for (ErebReflection x : reflections) x.moved();
            swapIn = ErebMath.swapGap(ServerConfig.get(ServerConfig.MI_SWAP_EVERY), boss.getRandom().nextDouble());
        }
        if (disguiseLeft > 0 && --disguiseLeft == 0) unmask(sl);
        if (veilLeft > 0) {
            if (--veilLeft == 0) {
                if (veilFx >= 0) Fx.stop(sl, veilFx, "");
                veilFx = -1;
            } else if (--flickerIn <= 0) {   // now and then the real model is gone for a moment, the false one stays
                flickerIn = 40 + boss.getRandom().nextInt(50);
                hide(true);
                hiddenLeft = Math.max(hiddenLeft, 8);
            }
        }
        if (betrayalLeft > 0 && --betrayalLeft == 0) endBetrayal(sl);
    }

    // ---------------------------------------------------------------- phases

    void onPhase(int from, int to) {
        ServerLevel sl = sl();
        act(ErebMath.PHASE);
        anim("ereb_phase");
        Fx.play(sl, Fx.fx(to == 1 ? "ereb_phase2" : "ereb_phase3").caster(boss).at(boss.position()).yaw(boss.getYRot()));
        core.actionbar(arenaR(), ui(to == 1 ? "phase2" : "phase3"));
        play(new BossTimeline("phase", ErebMath.PHASE).at(ErebMath.PHASE_AT, () -> core.sound("ereb.phase", 4, 1)));
        if (to >= 1) {   // the copies were phase 1's
            for (ErebReflection r : new ArrayList<>(reflections)) if (r.kind() == ErebReflection.Kind.MIRROR) r.poof(sl);
            swapIn = -1;
        }
        if (to == 1) {
            disguiseIn = ErebMath.PHASE + 4;
            veilIn = 20 * 12;
        }
        if (to == 2) {
            if (disguiseLeft > 0) unmask(sl);
            disguiseIn = veilIn = -1;
            betrayalIn = ErebMath.PHASE + 40;
        }
    }

    /** The phase's own illusion if one is due now. */
    private boolean phaseCast(ServerLevel sl, LivingEntity t, double d) {
        int phase = core.phase();
        if (phase == 0) {
            boolean anyMirror = reflections.stream().anyMatch(r -> r.kind() == ErebReflection.Kind.MIRROR);
            if (mirrorIn <= 0 && !anyMirror) {
                mirrorImages(sl);
                return true;
            }
            if (phantomIn <= 0 && t instanceof ServerPlayer) {
                phantomPain(sl, t);
                return true;
            }
            if (falseStepIn <= 0 && d < 12) {
                falseStep(sl, t);
                return true;
            }
        } else if (phase == 1) {
            if (disguiseIn == 0 && disguiseLeft <= 0) {
                disguise(sl);
                return true;
            }
            if (veilIn == 0 && veilLeft <= 0) {
                veil(sl);
                return true;
            }
        } else if (betrayalIn == 0 && betrayalLeft <= 0 && fighters().size() >= 2) {
            betrayal(sl);
            return true;
        }
        return false;
    }

    // ---------------------------------------------------------------- magic by hand and the rapier

    /** ereb_shard_cast: the left palm forward, on `release` a fan of shards along the look at the target. */
    private void shards(ServerLevel sl, LivingEntity t) {
        face(t);
        act(ErebMath.SHARD_CAST);
        anim("ereb_shard_cast");
        Fx.play(sl, Fx.fx("ereb_shards").caster(boss).at(boss.position()).yaw(boss.getYRot()));
        shardsIn = ErebConfig.i(ErebConfig.SHARDS_COOLDOWN) * 20;
        play(new BossTimeline("act:shards", ErebMath.SHARD_CAST).at(ErebMath.SHARD_RELEASE, () -> {
            if (!t.isAlive()) return;
            unmaskOnAttack(sl);
            face(t);
            core.sound("ereb.shards", 2, 1);
            double yaw = boss.getYRot();
            double[] f = ErebMath.forward(yaw);
            Vec3 palm = boss.position().add(f[0] * 0.6 + Math.cos(Math.toRadians(yaw)) * 0.3, 1.3, f[1] * 0.6 + Math.sin(Math.toRadians(yaw)) * 0.3);
            Vec3 aim = t.position().add(0, t.getBbHeight() * 0.55, 0).subtract(palm);
            double flat = Math.sqrt(aim.x * aim.x + aim.z * aim.z);
            double pitch = Math.atan2(aim.y, Math.max(0.01, flat));
            Map<UUID, Integer> tally = new HashMap<>();
            float dmg = (float) ErebConfig.d(ErebConfig.SHARD_DAMAGE);
            int cap = ErebConfig.i(ErebConfig.SHARDS_PER_TARGET);
            for (double off : ErebMath.fan(ErebConfig.i(ErebConfig.SHARDS_COUNT), 50)) {
                ErebShard s = Ereb.SHARD.get().create(sl);
                if (s == null) continue;
                double[] g = ErebMath.forward(ErebMath.yawTo(palm.x, palm.z, palm.x + aim.x, palm.z + aim.z) + off);
                s.setOwner(boss);
                s.setPos(palm.x, palm.y, palm.z);
                s.setup(dmg, tally, cap);
                s.shoot(g[0] * Math.cos(pitch), Math.sin(pitch), g[1] * Math.cos(pitch), 1.3f, 0);
                sl.addFreshEntity(s);
            }
        }));
    }

    /** A rapier lunge (one thrust) or a flurry (three). */
    private void melee(ServerLevel sl, LivingEntity t) {
        face(t);
        boolean flurry = boss.getRandom().nextFloat() < 0.35f;
        int len = flurry ? ErebMath.FLURRY : ErebMath.LUNGE;
        act(len);
        anim(flurry ? "ereb_flurry" : "ereb_lunge");
        meleeIn = len + ErebMath.meleePause(ErebConfig.i(ErebConfig.MELEE_MIN), ErebConfig.i(ErebConfig.MELEE_MAX), boss.getRandom().nextDouble());
        BossTimeline tl = new BossTimeline("act:melee", len);
        int[] hits = flurry ? ErebMath.FLURRY_HITS : new int[] {ErebMath.LUNGE_HIT};
        for (int h : hits)
            tl.at(h, () -> {
                unmaskOnAttack(sl);
                thrustFx();
                if (t.isAlive() && boss.distanceTo(t) < 3.4
                        && ErebMath.inArc(t.getX() - boss.getX(), t.getZ() - boss.getZ(), boss.getYRot(), 70)) hit(t, thrustDamage());
            });
        play(tl);
    }

    // ---------------------------------------------------------------- phase 1 «Две правды»

    /** «Отражения» (T22 rules: [illusion.mirror_images] copies, seconds, hitsToBreak, swapEverySeconds), his copies look like him. */
    private void mirrorImages(ServerLevel sl) {
        act(ErebMath.CAST_ILLUSION);
        anim("ereb_cast_illusion");
        Fx.play(sl, Fx.fx("ereb_cast_illusion").caster(boss).at(boss.position()).yaw(boss.getYRot()));
        mirrorIn = ErebConfig.i(ErebConfig.MIRROR_IMAGES_INTERVAL) * 20;
        play(new BossTimeline("act:mirror", ErebMath.CAST_ILLUSION).at(ErebMath.CAST_AT, () -> {
            core.sound("ereb.cast", 2, 1);
            Fx.play(sl, Fx.fx("illusion_mirror_images_cast").at(boss.position()).caster(boss));
            int n = ServerConfig.get(ServerConfig.MI_COPIES);
            int life = (int) Math.round(ServerConfig.get(ServerConfig.MI_SECONDS) * 20);
            int back = (int) Math.round(ServerConfig.get(ServerConfig.MI_DAMAGE_RETURN) * 20);
            int tag = ++TAG;
            double yaw0 = Math.toRadians(boss.getYRot());
            for (int k = 0; k < n; k++) {
                double a = yaw0 + Math.PI * 2 * (k + 0.5) / n;
                Vec3 at = free(sl, boss.position().add(-Math.sin(a) * 2.5, 0, Math.cos(a) * 2.5));
                ErebReflection r = spawnReflection(sl, at, ErebReflection.Kind.MIRROR, life, ServerConfig.get(ServerConfig.MI_HITS),
                        (float) ErebConfig.d(ErebConfig.COPIES_DAMAGE), back, tag);
                if (r != null) Fx.play(sl, Fx.fx("illusion_mirror_image_spawn").at(at));
            }
            Fx.play(sl, Fx.fx("illusion_mirror_image_spawn").at(boss.position()).caster(boss));   // the same flash on him
            swapIn = ErebMath.swapGap(ServerConfig.get(ServerConfig.MI_SWAP_EVERY), boss.getRandom().nextDouble());
        }));
    }

    private ErebReflection spawnReflection(ServerLevel sl, Vec3 at, ErebReflection.Kind kind, int life, int hits, float dmg, int back, int tag) {
        ErebReflection r = Ereb.REFLECTION.get().create(sl);
        if (r == null) return null;
        r.moveTo(at.x, at.y, at.z, boss.getYRot(), 0);
        r.setYHeadRot(boss.getYRot());
        r.setYBodyRot(boss.getYRot());
        r.setup(boss, kind, life, hits, dmg, back, tag);
        var hp = r.getAttribute(net.minecraft.world.entity.ai.attributes.Attributes.MAX_HEALTH);
        if (hp != null) hp.setBaseValue(boss.getMaxHealth());   // the same «health» if someone looks closely
        r.setHealth(r.getMaxHealth());
        sl.addFreshEntity(r);
        reflections.add(r);
        return r;
    }

    /** «Фантомная боль» (the T22 spell itself: the mark, the illusory share of every hit). */
    private void phantomPain(ServerLevel sl, LivingEntity t) {
        face(t);
        act(ErebMath.CAST_ILLUSION);
        anim("ereb_cast_illusion");
        Fx.play(sl, Fx.fx("ereb_cast_illusion").caster(boss).at(boss.position()).yaw(boss.getYRot()));
        phantomIn = ErebConfig.i(ErebConfig.PHANTOM_PAIN_INTERVAL) * 20;
        play(new BossTimeline("act:phantom", ErebMath.CAST_ILLUSION).at(ErebMath.CAST_AT, () -> {
            if (!t.isAlive()) return;
            core.sound("ereb.cast", 2, 1.1f);
            castT22("phantom_pain", t);
        }));
    }

    /** Casts a T22 spell of ours with him as the caster (no Iron's cast: its onCast only), level 1. */
    private void castT22(String path, LivingEntity target) {
        AbstractSpell spell = SpellRegistry.getSpell(new ResourceLocation(PohCore.MODID, path));
        if (spell == null || spell == SpellRegistry.none()) return;
        var md = boss.getMagicData();
        if (target != null) md.setAdditionalCastData(new TargetEntityCastData(target));
        try {
            spell.onCast(sl(), 1, boss, CastSource.MOB, md);
        } catch (RuntimeException e) {
            PohCore.LOG.error("[boss] ereb: {} failed", path, e);
        }
        md.resetAdditionalCastData();
    }

    /** «Ложный шаг»: he is gone for a moment while a reflection runs on along his course and thrusts; he steps aside. */
    private void falseStep(ServerLevel sl, LivingEntity t) {
        falseStepIn = ErebConfig.i(ErebConfig.FALSE_STEP_INTERVAL) * 20;
        face(t);
        int ticks = Math.max(10, (int) Math.round(ServerConfig.get(ServerConfig.FS_SECONDS) * 20));
        Vec3 o = boss.position();
        double[] f = ErebMath.forward(boss.getYRot());
        ErebReflection r = spawnReflection(sl, o, ErebReflection.Kind.RUNNER, ticks, 1, (float) ErebConfig.d(ErebConfig.COPIES_DAMAGE),
                (int) Math.round(ServerConfig.get(ServerConfig.MI_DAMAGE_RETURN) * 20), ++TAG);
        if (r != null) r.course(new Vec3(f[0] * 0.32, 0, f[1] * 0.32));
        hide(true);
        hiddenLeft = ticks;
        double side = boss.getRandom().nextBoolean() ? 1 : -1, dash = Math.min(6, ServerConfig.get(ServerConfig.FS_DASH));
        double a = Math.toRadians(boss.getYRot());
        Vec3 to = ground(sl, o.add(Math.cos(a) * side * dash * 0.7 + f[0] * dash * 0.3, 0, Math.sin(a) * side * dash * 0.7 + f[1] * dash * 0.3));
        Vec3 q = free(sl, to);
        boss.moveTo(q.x, q.y, q.z, boss.getYRot(), 0);   // T22: the enemies see nothing but the runner
        boss.getNavigation().stop();
        act(6);
    }

    // ---------------------------------------------------------------- phase 2 «Чужое лицо»

    /** He takes the look of a random participant (skin and name; T22 «Чужое лицо») for disguise_seconds or until his attack. */
    private void disguise(ServerLevel sl) {
        List<ServerPlayer> who = fighters();
        disguiseIn = ErebConfig.i(ErebConfig.DISGUISE_INTERVAL) * 20;
        if (who.isEmpty()) return;
        ServerPlayer face = who.get(boss.getRandom().nextInt(who.size()));
        act(ErebMath.DISGUISE);
        anim("ereb_disguise");
        Fx.play(sl, Fx.fx("ereb_disguise").caster(boss).at(boss.position()).yaw(boss.getYRot()));
        play(new BossTimeline("act:disguise", ErebMath.DISGUISE).at(ErebMath.DISGUISE_SWAP, () -> {
            core.sound("ereb.disguise", 2, 1);
            if (face.isAlive()) boss.setFace(face);
            disguiseLeft = ErebConfig.i(ErebConfig.DISGUISE_SECONDS) * 20;
        }));
    }

    /** The borrowed look falls (time, his attack, the phase): the same gesture backwards. */
    private void unmask(ServerLevel sl) {
        disguiseLeft = 0;
        if (boss.face() == null) return;
        anim("ereb_disguise");
        Fx.play(sl, Fx.fx("ereb_disguise").caster(boss).at(boss.position()).yaw(boss.getYRot()));
        play(new BossTimeline("unmask", ErebMath.DISGUISE).at(ErebMath.DISGUISE_SWAP, () -> {
            core.sound("ereb.disguise", 2, 0.9f);
            boss.setFace(null);
        }));
    }

    /** T32 «Сломать блок»: not busy with his own move. */
    boolean guardBreakFree() {
        return busy <= 0 && !core.locked() && !core.inScene();
    }

    /** T32: the Guard Break is an attack — a disguise falls as with any of his. */
    void onGuardBreak() {
        unmaskOnAttack(sl());
    }

    private void unmaskOnAttack(ServerLevel sl) {
        if (disguiseLeft > 0 && boss.face() != null) unmask(sl);
    }

    /** «Пелена»: a haze where he stands; a false silhouette beside him (strikes go through it), his own model now and then gone. */
    private void veil(ServerLevel sl) {
        veilIn = ErebConfig.i(ErebConfig.VEIL_INTERVAL) * 20;
        act(ErebMath.CAST_ILLUSION);
        anim("ereb_cast_illusion");
        Fx.play(sl, Fx.fx("ereb_cast_illusion").caster(boss).at(boss.position()).yaw(boss.getYRot()));
        int ticks = ErebConfig.i(ErebConfig.VEIL_SECONDS) * 20;
        play(new BossTimeline("act:veil", ErebMath.CAST_ILLUSION).at(ErebMath.CAST_AT, () -> {
            Vec3 c = boss.position();
            veilFx = Fx.play(sl, Fx.fx("illusion_veil").at(c).scale(ErebConfig.d(ErebConfig.VEIL_RADIUS) / 6.0).duration(ticks));
            core.sound("ereb.cast", 2, 1.3f);
            double[] f = ErebMath.forward(boss.getYRot() + 90);
            spawnReflection(sl, free(sl, c.add(f[0] * 1.3, 0, f[1] * 1.3)), ErebReflection.Kind.GHOST, ticks, 1, 0, 0, 0);
            veilLeft = ticks;
            flickerIn = 30;
        }));
    }

    // ---------------------------------------------------------------- phase 3 «Предательство»

    /** For betrayal_seconds every player of the fight sees the others as him (client: ErebClient); a hit on one is a real hit. */
    private void betrayal(ServerLevel sl) {
        betrayalIn = ErebConfig.i(ErebConfig.BETRAYAL_INTERVAL) * 20;
        act(ErebMath.CAST_ILLUSION);
        anim("ereb_cast_illusion");
        Fx.play(sl, Fx.fx("ereb_cast_illusion").caster(boss).at(boss.position()).yaw(boss.getYRot()));
        play(new BossTimeline("act:betrayal", ErebMath.CAST_ILLUSION).at(ErebMath.CAST_AT, () -> {
            List<ServerPlayer> who = fighters();
            int ticks = ErebConfig.i(ErebConfig.BETRAYAL_SECONDS) * 20;
            betrayalLeft = ticks;
            deceived.clear();
            for (ServerPlayer p : who) deceived.add(p.getUUID());
            boss.setBetrayal(true);
            core.sound("ereb.disguise", 3, 0.8f);
            for (ServerPlayer viewer : who)   // the faint glass glint on each «Ereb» who is really an ally: only for the deceived one
                for (ServerPlayer ally : who)
                    if (ally != viewer)
                        betrayalFx.add(Fx.play(sl, Fx.fx("ereb_false_face").caster(ally).at(ally.position()).attach(ally).duration(ticks).only(viewer)));
            if (!betrayalHinted) {
                betrayalHinted = true;
                for (ServerPlayer p : who) p.displayClientMessage(ui("betrayal_hint"), true);
            }
        }));
    }

    private void endBetrayal(ServerLevel sl) {
        betrayalLeft = 0;
        boss.setBetrayal(false);
        deceived.clear();
        for (int f : betrayalFx) if (f >= 0) Fx.stop(sl, f, "");
        betrayalFx.clear();
    }

    /** A player of the betrayal hits another one of it: the hit is real (×betrayal_friendly_mult). */
    boolean betrayed(Player victim, Player attacker) {
        return betrayalLeft > 0 && victim != attacker && deceived.contains(victim.getUUID()) && deceived.contains(attacker.getUUID());
    }

    // ---------------------------------------------------------------- specials

    /** Returns false while it cannot start (busy, another scene): the core asks again next tick. */
    boolean special(String id) {
        if (busy > 0 || core.locked() || core.inScene()) return false;
        if (id.equals("false_ally")) falseAlly(sl());
        else if (id.equals("labyrinth")) labyrinth(sl());
        return true;
    }

    /**
     * «Ложный союзник» (once, ≈2.6 s, the fight goes on): a glint of glass behind the player who hurt him most, he vanishes, appears
     * behind it in the look of one of its allies and stabs it in the back; the mask falls. Only the victim gets the camera.
     */
    private void falseAlly(ServerLevel sl) {
        ServerPlayer victim = core.strongestEnemy();
        if (victim == null) return;
        act(ErebMath.FA);
        core.lock(ErebMath.FA, true, false);
        Fx.play(sl, Fx.fx("ereb_false_ally_glint").caster(victim).at(victim.position()).attach(victim));
        core.sound(victim.position(), "ereb.glint", 2, 1);
        victim.displayClientMessage(ui("false_ally_warn"), true);
        anim("ereb_vanish");
        Fx.play(sl, Fx.fx("ereb_vanish").caster(boss).at(boss.position()).yaw(boss.getYRot()));
        core.sound("ereb.vanish", 2, 1);
        ServerPlayer[] mask = {null};
        play(new BossTimeline("scene:false_ally", ErebMath.FA)
                .at(ErebMath.FA_GONE, () -> {
                    hide(true);
                    hiddenLeft = 0;
                    invuln = ErebMath.FA_APPEAR - ErebMath.FA_GONE + 2;
                })
                .at(ErebMath.FA_APPEAR, () -> {
                    if (!victim.isAlive() || victim.level() != sl) {
                        hide(false);
                        return;
                    }
                    List<ServerPlayer> allies = fighters();
                    allies.remove(victim);
                    if (!allies.isEmpty()) mask[0] = allies.get(boss.getRandom().nextInt(allies.size()));
                    boss.setFace(mask[0]);
                    double[] p = ErebMath.behind(victim.getX(), victim.getZ(), victim.getYRot(), 1.1);
                    Vec3 to = free(sl, new Vec3(p[0], victim.getY(), p[1]));
                    float yaw = ErebMath.yawTo(to.x, to.z, victim.getX(), victim.getZ());
                    boss.moveTo(to.x, to.y, to.z, yaw, 0);
                    face(yaw);
                    hide(false);
                    anim("ereb_backstab");
                    Fx.play(sl, Fx.fx("ereb_appear").at(to).yaw(yaw));   // no caster: just moved, the client still lerps him from the old spot and would draw it there (FX audit 21.11)
                    core.sound("ereb.appear", 2, 1);
                    core.sceneFor(victim, "ereb.false_ally", ErebMath.FA_CAM, 0, victim.position(), victim.getYRot(), victim.getId());
                })
                .at(ErebMath.FA_STAB, () -> {
                    thrustFx();
                    if (victim.isAlive() && boss.distanceTo(victim) < 4) hit(victim, ErebConfig.d(ErebConfig.FALSE_ALLY_DAMAGE));
                    core.title(List.of(victim), "ereb_false_ally", 30, null);
                    core.actionbar(arenaR(), ui("false_ally"));
                })
                .at(ErebMath.FA_MASK, () -> {
                    anim("ereb_disguise");
                    Fx.play(sl, Fx.fx("ereb_disguise").caster(boss).at(boss.position()).yaw(boss.getYRot()));
                })
                .at(ErebMath.FA_SWAP, () -> {
                    core.sound("ereb.disguise", 2, 1);
                    if (disguiseLeft <= 0) boss.setFace(null);
                }));
    }

    /** «Зеркальный лабиринт» over the whole arena (T22 dome with the arena radius), title for everyone in the fight. */
    private void labyrinth(ServerLevel sl) {
        act(ErebMath.CAST_ILLUSION);
        anim("ereb_cast_illusion");
        Fx.play(sl, Fx.fx("ereb_cast_illusion").caster(boss).at(boss.position()).yaw(boss.getYRot()));
        play(new BossTimeline("scene:labyrinth", ErebMath.CAST_ILLUSION).at(ErebMath.CAST_AT, () -> {
            core.sound("ereb.cast", 3, 0.8f);
            MirrorLabyrinthSpell.raise(sl, boss, core.arena(), ErebConfig.d(ErebConfig.LABYRINTH_RADIUS), ErebConfig.i(ErebConfig.LABYRINTH_SECONDS) * 20,
                    (float) ErebConfig.d(ErebConfig.LABYRINTH_WALL_DAMAGE));
            core.title(core.playersNear(BossConfig.get(BossConfig.SCENE_RADIUS)), "ereb_labyrinth", 50, null);
            core.actionbar(arenaR(), ui("labyrinth"));
        }));
    }

    // ---------------------------------------------------------------- the four spells (no scene, each with its warning)

    private boolean castSpell(ServerLevel sl, LivingEntity t, double d) {
        List<String> can = new ArrayList<>();
        int players = fighters().size();
        if (ready("blade_dance") && players >= 1) can.add("blade_dance");
        if (ready("feint") && d < 6) can.add("feint");
        if (ready("glass_rain")) can.add("glass_rain");
        if (ready("mirror_step")) can.add("mirror_step");
        if (can.isEmpty()) return false;
        switch (can.get(boss.getRandom().nextInt(can.size()))) {
            case "blade_dance" -> {
                bladeDance(sl);
                cooldown.put("blade_dance", ErebConfig.i(ErebConfig.BLADE_DANCE_COOLDOWN) * 20);
            }
            case "feint" -> {
                feint(sl, t);
                cooldown.put("feint", ErebConfig.i(ErebConfig.FEINT_COOLDOWN) * 20);
            }
            case "glass_rain" -> {
                glassRain(sl);
                cooldown.put("glass_rain", ErebConfig.i(ErebConfig.GLASS_RAIN_COOLDOWN) * 20);
            }
            default -> {
                mirrorStep(sl, t);
                cooldown.put("mirror_step", ErebConfig.i(ErebConfig.MIRROR_STEP_COOLDOWN) * 20);
            }
        }
        return true;
    }

    private boolean ready(String id) {
        return cooldown.getOrDefault(id, 100) <= 0;
    }

    /** «Танец клинков»: 4 thrusts, between them instant steps through a glass ripple to another player (3 blocks before it). */
    private void bladeDance(ServerLevel sl) {
        List<ServerPlayer> who = fighters();
        if (who.isEmpty()) return;
        Collections.shuffle(who, new Random(boss.getRandom().nextLong()));
        act(ErebMath.BLADE_DANCE);
        anim("ereb_blade_dance");
        core.actionbar(arenaR(), ui("blade_dance"));
        ServerPlayer[] cur = {null};
        BossTimeline tl = new BossTimeline("act:blade_dance", ErebMath.BLADE_DANCE);
        for (int i = 0; i < 4; i++) {
            int k = i;
            tl.at(ErebMath.BD_BLINK[i], () -> {
                ServerPlayer p = who.get(ErebMath.danceTarget(k, who.size()));
                cur[0] = p.isAlive() && p.level() == sl ? p : null;
                if (cur[0] == null) return;
                Vec3 dir = boss.position().subtract(p.position()).multiply(1, 0, 1);
                dir = dir.lengthSqr() < 1e-4 ? new Vec3(0, 0, 1) : dir.normalize();
                Vec3 to = p.position().add(dir.scale(2.4));
                blinkTo(sl, to, ErebMath.yawTo(to.x, to.z, p.getX(), p.getZ()));
            });
            tl.at(ErebMath.BD_HIT[i], () -> {
                unmaskOnAttack(sl);
                thrustFx();
                ServerPlayer p = cur[0];
                if (p != null && p.isAlive() && boss.distanceTo(p) < 4) hit(p, ErebConfig.d(ErebConfig.BLADE_DANCE_DAMAGE));
            });
        }
        play(tl);
    }

    /** «Обманная брешь»: an open stance for 1.5 s (a faint glint — a hint); whoever strikes then is parried and countered. */
    private void feint(ServerLevel sl, LivingEntity t) {
        face(t);
        act(ErebMath.FEINT);
        anim("ereb_feint");
        countered = false;
        play(new BossTimeline("act:feint", ErebMath.FEINT)
                .at(ErebMath.FEINT_OPEN, () -> {
                    feintOpen = true;
                    Fx.play(sl, Fx.fx("ereb_feint_open").caster(boss).at(boss.position()).yaw(boss.getYRot()));
                    core.actionbar(16, ui("feint"));
                })
                .at(ErebMath.FEINT_CLOSE, () -> feintOpen = false));
    }

    /** Called from his hurt: in the feint window the strike is cancelled and countered. Returns the damage to take. */
    float onHurt(DamageSource src, float amount) {
        if (invuln > 0) return 0;
        if (feintOpen && !countered && src.getEntity() instanceof LivingEntity att && !(att instanceof ErebBody)) {
            countered = true;
            feintOpen = false;
            counter(sl(), att);
            return 0;
        }
        return amount;
    }

    private void counter(ServerLevel sl, LivingEntity att) {
        face(att);
        busy = Math.max(busy, ErebMath.COUNTER);
        core.lock(ErebMath.COUNTER, true, false);
        anim("ereb_feint_counter");
        if (att instanceof ServerPlayer sp) sp.displayClientMessage(ui("feint_counter"), true);
        play(new BossTimeline("act:counter", ErebMath.COUNTER)
                .at(ErebMath.COUNTER_PARRY, () -> {
                    Fx.play(sl, Fx.fx("ereb_parry").caster(boss).at(boss.position()).yaw(boss.getYRot()));
                    core.sound("ereb.parry", 2, 1);
                })
                .at(ErebMath.COUNTER_HIT, () -> {
                    Fx.play(sl, Fx.fx("ereb_feint_counter").caster(boss).at(boss.position()).yaw(boss.getYRot()).target(att));
                    core.sound("ereb.thrust", 2, 0.9f);
                    if (att.isAlive() && boss.distanceTo(att) < 5) hit(att, ErebConfig.d(ErebConfig.FEINT_COUNTER_DAMAGE));
                }));
    }

    /** «Стеклянный дождь»: marks on the ground by the players (1.2 s), then mirror shards fall on them. */
    private void glassRain(ServerLevel sl) {
        List<ServerPlayer> who = fighters();
        if (who.isEmpty()) return;
        act(ErebMath.RAIN);
        anim("ereb_glass_rain");
        List<Vec3> marks = new ArrayList<>();
        play(new BossTimeline("act:glass_rain", ErebMath.RAIN_FALL + 1)
                .at(ErebMath.RAIN_MARKS, () -> {
                    int[] per = ErebMath.rainMarks(who.size(), ErebConfig.i(ErebConfig.GLASS_RAIN_PER_PLAYER), ErebConfig.i(ErebConfig.GLASS_RAIN_MAX));
                    for (int i = 0; i < who.size(); i++) {
                        ServerPlayer p = who.get(i);
                        for (int k = 0; k < per[i]; k++) {
                            double a = boss.getRandom().nextDouble() * Math.PI * 2, dd = k == 0 ? 0 : 1.5 + boss.getRandom().nextDouble() * 2.5;
                            Vec3 q = ground(sl, p.position().add(Math.cos(a) * dd, 0, Math.sin(a) * dd));
                            marks.add(q);
                            Fx.play(sl, Fx.fx("ereb_glass_rain_mark").at(q).scale(ErebConfig.d(ErebConfig.GLASS_RAIN_RADIUS) / 2.0));
                        }
                    }
                    core.actionbar(arenaR(), ui("glass_rain"));
                    core.sound("ereb.glint", 2, 0.8f);
                })
                .at(ErebMath.RAIN_FALL, () -> {
                    Set<UUID> hitSet = new HashSet<>();
                    double r = ErebConfig.d(ErebConfig.GLASS_RAIN_RADIUS);
                    for (Vec3 q : marks) {
                        Fx.play(sl, Fx.fx("ereb_glass_rain_hit").at(q));
                        core.sound(q, "ereb.rain", 1.5f, 1);
                        for (LivingEntity e : targets(sl, q, r))
                            if (Math.abs(e.getY() - q.y) < 3 && hitSet.add(e.getUUID())) hit(e, ErebConfig.d(ErebConfig.GLASS_RAIN_DAMAGE));
                    }
                }));
    }

    /** «Шаг сквозь отражение»: gone in a ripple, a glint behind another player (0.6 s), out of the glass behind it, a thrust. */
    private void mirrorStep(ServerLevel sl, LivingEntity t) {
        List<ServerPlayer> who = fighters();
        if (who.isEmpty()) return;
        List<ServerPlayer> others = new ArrayList<>(who);
        others.remove(t);
        ServerPlayer p = others.isEmpty() ? who.get(0) : others.get(boss.getRandom().nextInt(others.size()));
        act(ErebMath.STEP);
        anim("ereb_mirror_step_out");
        Fx.play(sl, Fx.fx("ereb_blink").caster(boss).at(boss.position()).yaw(boss.getYRot()));
        core.sound("ereb.vanish", 2, 1);
        core.actionbar(arenaR(), ui("mirror_step"));
        play(new BossTimeline("act:mirror_step", ErebMath.STEP)
                .at(ErebMath.STEP_GONE, () -> {
                    hide(true);
                    hiddenLeft = 0;
                    invuln = ErebMath.STEP_WARN + 2;
                    if (!p.isAlive()) return;
                    Fx.play(sl, Fx.fx("ereb_mirror_step_warn").caster(p).at(p.position()).attach(p));
                    core.sound(p.position(), "ereb.glint", 2, 1.1f);
                })
                .at(ErebMath.STEP_APPEAR, () -> {
                    hide(false);
                    if (!p.isAlive() || p.level() != sl) return;
                    double[] b = ErebMath.behind(p.getX(), p.getZ(), p.getYRot(), 1.2);
                    Vec3 to = new Vec3(b[0], p.getY(), b[1]);
                    Vec3 q = free(sl, to);
                    float yaw = ErebMath.yawTo(q.x, q.z, p.getX(), p.getZ());
                    boss.moveTo(q.x, q.y, q.z, yaw, 0);
                    face(yaw);
                    boss.getNavigation().stop();
                    anim("ereb_mirror_step_in");
                    Fx.play(sl, Fx.fx("ereb_blink").at(q).yaw(yaw));   // no caster: just moved, the client still lerps him from the old spot and would draw it there (FX audit 21.11)
                    core.sound("ereb.appear", 2, 1);
                })
                .at(ErebMath.STEP_APPEAR + ErebMath.STEP_STAB, () -> {
                    unmaskOnAttack(sl);
                    thrustFx();
                    if (p.isAlive() && boss.distanceTo(p) < 3.5) hit(p, ErebConfig.d(ErebConfig.MIRROR_STEP_DAMAGE));
                }));
    }

    /**
     * The finisher ereb_finisher (the framework holds the victim where it was struck and kills it at FIN_KILL with «%1$s поверил
     * Эребу»): on `vanish` he is gone (invulnerable) and moved 1.3 blocks behind the victim, facing it; `appear`; the thrust on `stab`;
     * the victim breaks into glass and butterflies (fx ereb_finisher, tick 38). Its camera: a close-up on him from beside it.
     */
    void finisher(ServerLevel sl, ServerPlayer victim) {
        anim("ereb_finisher");
        Fx.play(sl, Fx.fx("ereb_finisher").caster(boss).at(boss.position()).yaw(boss.getYRot()).target(victim));
        core.sound("ereb.vanish", 2, 1);
        play(new BossTimeline("finisher", ErebMath.FINISHER)
                .at(ErebMath.FIN_VANISH, () -> {
                    hide(true);
                    hiddenLeft = 0;
                    invuln = ErebMath.FIN_APPEAR - ErebMath.FIN_VANISH + 1;
                    double[] p = ErebMath.behind(victim.getX(), victim.getZ(), victim.getYRot(), ErebMath.FIN_BEHIND);
                    Vec3 to = free(sl, new Vec3(p[0], victim.getY(), p[1]));
                    float yaw = ErebMath.yawTo(to.x, to.z, victim.getX(), victim.getZ());
                    boss.moveTo(to.x, to.y, to.z, yaw, 0);
                    face(yaw);
                    boss.getNavigation().stop();
                })
                .at(ErebMath.FIN_APPEAR, () -> {
                    hide(false);
                    core.sound("ereb.appear", 2, 1);
                    core.sceneFor(victim, "ereb.finisher", ErebMath.FIN_CAM, BossNet.SCENE_LOCK_INPUT | BossNet.SCENE_NO_HUD, victim.position(),
                            victim.getYRot(), victim.getId());
                })
                .at(ErebMath.FIN_STAB, () -> core.sound("ereb.thrust", 2, 0.9f))
                .at(ErebMath.FIN_KILL, () -> core.sound(victim.position(), "ereb.dissolve", 2, 1.1f)));
    }

    /** «Дезинтеграция: Реплика» broke in: the feint window closes. */
    void interrupt() {
        feintOpen = false;
    }

    // ---------------------------------------------------------------- the finale (5%): «Сон бабочки» and gone

    void finale() {
        ServerLevel sl = sl();
        cleanup(sl);
        hiddenLeft = 0;   // FX audit 21.11: tick() stops counting in the finale - hidden by the veil / a vanish he stayed unseen all the scene
        hide(false);
        boss.setFace(null);
        boss.getNavigation().stop();
        Vec3 at = boss.position();
        float yaw = boss.getYRot();
        List<ServerPlayer> who = core.scene("ereb.finale", ErebMath.FINALE_CAST + 2, BossNet.SCENE_LOCK_INPUT | BossNet.SCENE_BARS | BossNet.SCENE_NO_HUD,
                BossConfig.get(BossConfig.INTRO_RADIUS), at, yaw, -1);
        anim("ereb_finale");
        Fx.play(sl, Fx.fx("ereb_finale").caster(boss).at(at).yaw(yaw));
        double r = core.arenaRadius();
        int dream = ErebConfig.i(ErebConfig.FINALE_DREAM_SECONDS) * 20;
        core.play(new BossTimeline("scene:finale", ErebMath.FINALE)
                .at(ErebMath.FINALE_SMILE, () -> {
                    boss.setSmile(true);
                    core.actionbar(BossConfig.get(BossConfig.INTRO_RADIUS), ui("finale"));
                })
                .at(ErebMath.FINALE_BUTTERFLY, () -> core.sound("ereb.butterfly", 2, 1))
                .at(ErebMath.FINALE_SPEAK, () -> core.say("ui.pohsmp_core.ereb.farewell", 48, 60, boss.getBbHeight() + 0.6))
                .at(ErebMath.FINALE_CAST, () -> {
                    ErebDreamPoint point = Ereb.DREAM_POINT.get().create(sl);
                    if (point == null) return;
                    point.moveTo(at.x, at.y, at.z, yaw, 0);
                    point.setYHeadRot(yaw);
                    point.lifeTicks(240 + 20 + dream + 200);
                    sl.addFreshEntity(point);
                    ButterflyDreamSpell.castFromPoint(sl, point, r, dream);
                    core.title(who, "ereb_butterfly", 40, null);
                })
                .at(ErebMath.FINALE_VANISH, () -> core.sound("ereb.dissolve", 3, 1))
                .at(ErebMath.FINALE_HIDE, () -> {
                    hide(true);
                    Component line = ui("vanish");
                    for (ServerPlayer p : core.playersNear(BossConfig.get(BossConfig.INTRO_RADIUS))) p.sendSystemMessage(line);
                })
                .then(core::endFinale));
    }

    /** Everything of his that lives in the world goes with him (reflections, the veil, the betrayal). */
    void cleanup(ServerLevel sl) {
        for (ErebReflection r : new ArrayList<>(reflections)) r.poof(sl);
        reflections.clear();
        if (veilFx >= 0) Fx.stop(sl, veilFx, "");
        veilFx = -1;
        veilLeft = 0;
        if (betrayalLeft > 0 || boss.betrayal()) endBetrayal(sl);
        feintOpen = false;
        disguiseLeft = 0;
    }

    // ---------------------------------------------------------------- events

    public static final class Events {
        private Events() {}

        /** «Предательство»: a hit on an ally who looked like him is a real hit on the ally (×betrayal_friendly_mult). */
        @SubscribeEvent(priority = EventPriority.LOW)
        public static void onHurt(LivingHurtEvent e) {
            if (!(e.getEntity() instanceof ServerPlayer victim) || !(e.getSource().getEntity() instanceof ServerPlayer att)) return;
            for (ErebEntity b : victim.serverLevel().getEntitiesOfClass(ErebEntity.class, victim.getBoundingBox().inflate(64))) {
                if (b.fight.betrayed(victim, att)) {
                    e.setAmount((float) (e.getAmount() * ErebConfig.d(ErebConfig.BETRAYAL_FRIENDLY_MULT)));
                    return;
                }
            }
        }
    }
}
