package ru.pohsmp.core.boss.martin;

import io.redspace.ironsspellbooks.api.entity.IMagicEntity;
import io.redspace.ironsspellbooks.api.magic.MagicData;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.CopyOnWriteArraySet;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.util.Mth;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.damagesource.DamageType;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.MobSpawnType;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.ClipContext;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.HitResult;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.entity.living.LivingAttackEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.boss.BossConfig;
import ru.pohsmp.core.boss.BossCore;
import ru.pohsmp.core.boss.BossNet;
import ru.pohsmp.core.boss.BossTimeline;
import ru.pohsmp.core.fx.Fx;
import ru.pohsmp.core.spell.NpcCast;

/**
 * The fight of T29 on top of the framework: his melee (swing, overhead, thrust; phase 3 the shield dash), the three phases («Строй» —
 * ghost soldiers cover him, damage through the line ×0.5; «Знамя» — a banner entity that buffs soldiers in r8 and can be cut;
 * «Последний полководец» — the army is gone, he hits harder and faster), the specials «Приказ стоять насмерть» (50%) and «Атака
 * конницы» (25%) with their scenes, the four spells («Стена щитов», «Залп лучников», «Вызов на дуэль», «Боевой клич»), the
 * surrender through a block. Every strong blow has a visible warning (lanes, marks, rings, the wind-up); no beams or lines to a
 * target. Numbers: [martin] of pohsmp_core-bosses-server.toml ({@link MartinConfig}, balance_bosses.md section 5).
 */
public final class MartinFight {
    private final MartinEntity boss;
    private final BossCore core;

    private final List<UUID> soldiers = new ArrayList<>();
    private UUID banner;
    private int refillIn = -1, replantIn = -1, meleeIn = 60, gcd = 100, bashCd;
    private int formationFx = -1, furyFx = -1, holdFx = -1, duelFx = -1, duelMarkFx = -1;
    private final Map<String, Integer> cooldown = new HashMap<>();
    private long holdUntil = -1;
    private UUID duelist;
    private Vec3 duelAt;
    private long duelUntil = -1;
    private boolean yieldWait, yielding, recollect;
    private int yieldIn;
    private final Map<UUID, Long> notice = new HashMap<>();

    /** Fights with a duel going on (LivingAttackEvent: only the two may hurt each other). */
    private static final Set<MartinFight> DUELS = new CopyOnWriteArraySet<>();

    MartinFight(MartinEntity boss) {
        this.boss = boss;
        this.core = boss.bossCore();
    }

    private ServerLevel sl() {
        return (ServerLevel) boss.level();
    }

    static Component ui(String key, Object... args) {
        return Component.translatable("ui.pohsmp_core.martin." + key, args).withStyle(s -> s.withColor(Martin.COLOR));
    }

    private void status(int bit, boolean on) {
        if (((core.look() & bit) != 0) != on) core.lookFlag(bit, on);
    }

    /** pohsmp_core:boss_attack dealt by `by` (a soldier, the boss): no difficulty scaling, armour counts. */
    static DamageSource attackSource(ServerLevel sl, Entity by) {
        ResourceKey<DamageType> k = ResourceKey.create(Registries.DAMAGE_TYPE, new ResourceLocation(PohCore.MODID, "boss_attack"));
        return sl.registryAccess().registryOrThrow(Registries.DAMAGE_TYPE).getHolder(k).map(h -> new DamageSource(h, by))
                .orElseGet(() -> sl.damageSources().generic());
    }

    /** His strength now: the enrage of the framework (attack attribute over the config value) × phase 3. */
    private double mult() {
        BossConfig.PerBoss cfg = BossConfig.of(Martin.ID);
        double base = cfg != null ? BossConfig.get(cfg.attack) : 20;
        double enrage = base > 0 ? Math.max(1, boss.getAttributeValue(Attributes.ATTACK_DAMAGE) / base) : 1;
        return enrage * (core.phase() >= 2 ? MartinConfig.d(MartinConfig.P3_DAMAGE_MULT) : 1);
    }

    private void hit(LivingEntity e, double dmg) {
        if (e.hurt(core.attackDamage(), (float) (dmg * mult()))) core.sound(e.position(), "martin.hit", 1.5f, 1);
    }

    /** T32 «Сломать блок»: his strongest melee hit now — swing, overhead, thrust (phase 3: the shield dash too), ×phase 3, enrage. */
    double guardBreakDamage() {
        BossConfig.PerBoss cfg = BossConfig.of(Martin.ID);
        double swing = (cfg != null ? BossConfig.get(cfg.attack) : 20) + MartinConfig.d(MartinConfig.SWORD_DAMAGE);
        double dash = core.phase() >= 2 ? MartinConfig.d(MartinConfig.SHIELD_DASH_DAMAGE) : 0;
        return ru.pohsmp.core.boss.BossGuardBreakMath.heavy(swing, MartinConfig.d(MartinConfig.OVERHEAD_DAMAGE), MartinConfig.d(MartinConfig.THRUST_DAMAGE), dash)
                * mult();
    }

    /** A notice in the action bar of one player, not more often than once a second. */
    private void tell(Entity e, Component c) {
        if (!(e instanceof ServerPlayer p)) return;
        long now = sl().getGameTime();
        if (now - notice.getOrDefault(p.getUUID(), Long.MIN_VALUE / 2) < 20) return;
        notice.put(p.getUUID(), now);
        p.displayClientMessage(c, true);
    }

    // ---------------------------------------------------------------- tick

    void tick(ServerLevel sl) {
        if (recollect) recollect(sl);
        if (core.inFinale()) {
            if (yieldWait && --yieldIn <= 0) {
                ServerPlayer p = sl.getNearestPlayer(boss, 48) instanceof ServerPlayer sp ? sp : null;
                block(sl, p);
            }
            return;
        }
        if (!core.started()) return;
        long now = sl.getGameTime();
        soldiers.removeIf(u -> !(sl.getEntity(u) instanceof MartinSoldierEntity s && s.isAlive() && !s.vanishing()));
        if (boss.tickCount % 10 == 0) auras(sl);
        if (duelUntil >= 0) duelTick(sl, now);
        if (holdUntil >= 0 && now >= holdUntil) holdUntil = -1;
        if (core.phase() < 2) {
            if (refillIn > 0) refillIn--;
            else if (refillIn == 0 && !core.locked() && !core.inScene()) {
                refillIn = MartinConfig.i(MartinConfig.SOLDIERS_REFILL) * 20;
                int missing = wantSoldiers() - soldiers.size();
                if (missing > 0) summon(sl, missing, true);
            }
        }
        if (core.phase() == 1 && replantIn > 0 && --replantIn == 0) {
            if (core.locked() || core.inScene()) replantIn = 20;
            else replant(sl);
        }
        cooldown.replaceAll((k, v) -> Math.max(0, v - 1));
        if (bashCd > 0) bashCd--;
        if (meleeIn > 0) meleeIn--;
        if (core.locked() || core.inScene()) return;
        LivingEntity t = target(sl);
        if (t == null) return;
        boss.getLookControl().setLookAt(t, 30, 30);
        if (gcd > 0) gcd--;
        else if (castSpell(sl, t)) {
            gcd = BossConfig.get(BossConfig.ABILITY_GCD) * 20;
            return;
        } else gcd = 10;
        double d = Math.sqrt(boss.distanceToSqr(t.getX(), boss.getY(), t.getZ()));
        if (meleeIn <= 0 && melee(sl, t, d)) return;
        if (d > 3.2 && boss.tickCount % 10 == 0) boss.getNavigation().moveTo(t, 1.0);
        else if (d <= 3.2) boss.getNavigation().stop();
    }

    /** His target: the duelist while a duel lasts, else the AI's target (players only). */
    private LivingEntity target(ServerLevel sl) {
        if (duelist != null && sl.getEntity(duelist) instanceof ServerPlayer p && p.isAlive()) {
            boss.setTarget(p);
            return p;
        }
        LivingEntity t = boss.getTarget();
        if (t instanceof Player p && (p.isCreative() || p.isSpectator())) {
            boss.setTarget(null);
            return null;
        }
        return t != null && t.isAlive() ? t : null;
    }

    // ---------------------------------------------------------------- damage to him

    /** Formation, «Приказ стоять насмерть» from the front, the duel. Returns the damage to apply (0 = none). */
    float filterHit(DamageSource src, float amount) {
        ServerLevel sl = sl();
        Entity by = src.getEntity();
        Vec3 from = src.getSourcePosition() != null ? src.getSourcePosition() : by != null ? by.position() : null;
        if (holdUntil >= 0 && sl.getGameTime() < holdUntil && from != null
                && MartinMath.inFront(boss.getYRot(), from.x - boss.getX(), from.z - boss.getZ(), MartinConfig.d(MartinConfig.HOLD_ARC))) {
            Vec3 dir = from.subtract(boss.position()).multiply(1, 0, 1);
            Vec3 at = boss.position().add(dir.lengthSqr() > 1e-4 ? dir.normalize().scale(3.2) : Vec3.ZERO).add(0, 1.6, 0);
            Fx.play(sl, Fx.fx("martin_hold_deflect").at(at).yaw(boss.getYRot()));
            core.sound(at, "martin.shield_hit", 2, 1);
            if (by != null) tell(by, ui("hold_blocked"));
            return 0;
        }
        if (duelUntil >= 0 && by != null && !by.getUUID().equals(duelist)) {
            tell(by, ui("duel_blocked"));
            return 0;
        }
        if (by != null && formationActive()) {
            double r = MartinConfig.d(MartinConfig.FORMATION_RADIUS);
            Vec3 a = by.position();
            for (UUID u : soldiers) {
                if (!(sl.getEntity(u) instanceof MartinSoldierEntity s) || s.distanceToSqr(boss) > r * r) continue;
                if (!MartinMath.blocksLine(a.x, a.z, boss.getX(), boss.getZ(), s.getX(), s.getZ(), 0.9)) continue;
                Fx.play(sl, Fx.fx("martin_formation_block").at(s.position().add(0, 1.2, 0)).yaw(s.getYRot()));
                s.brace(20);
                tell(by, ui("formation_block"));
                return amount * (float) MartinConfig.d(MartinConfig.FORMATION_MULT);
            }
        }
        return amount;
    }

    boolean formationActive() {
        if (soldiers.isEmpty() || core.phase() >= 2) return false;
        return core.phase() == 0 || MartinConfig.b(MartinConfig.FORMATION_P2);
    }

    // ---------------------------------------------------------------- army

    private int wantSoldiers() {
        return MartinMath.soldiers(core.fighters().size(), MartinConfig.i(MartinConfig.SOLDIERS_BASE), MartinConfig.i(MartinConfig.SOLDIERS_MAX));
    }

    void onFightStart(ServerLevel sl) {
        formationFx = Fx.play(sl, Fx.fx("martin_formation").caster(boss).at(boss.position()).attach(boss));
        core.actionbar(core.arenaRadius() + 8, ui("formation"));
        summon(sl, wantSoldiers(), true);
        refillIn = MartinConfig.i(MartinConfig.SOLDIERS_REFILL) * 20;
    }

    /** n soldiers rise around him (two rows behind him at the start, a ring later); with the «в атаку!» gesture first. */
    private void summon(ServerLevel sl, int n, boolean command) {
        if (n <= 0) return;
        int at = 0;
        if (command) {
            boss.face(boss.getYRot());
            core.lock(MartinMath.COMMAND, true, false);
            boss.anim("martin_command");
            at = MartinMath.COMMAND_AT;
        }
        BossTimeline t = new BossTimeline("summon", at + MartinMath.SOLDIER_SPAWN_AT + 3);
        t.at(at, () -> {
            if (command) {
                Fx.play(sl, Fx.fx("martin_command").caster(boss).at(boss.position()).yaw(boss.getYRot()));
                core.sound("martin.command", 3, 1);
                core.actionbar(24, ui("command"));
            }
            List<Vec3> places = new ArrayList<>();
            Vec3 fwd = Vec3.directionFromRotation(0, boss.getYRot()), right = new Vec3(-fwd.z, 0, fwd.x);
            for (int i = 0; i < n; i++) {
                int row = i % 2, col = i / 2, cols = (n + 1) / 2;
                double side = (col - (cols - 1) / 2.0) * 1.8;
                Vec3 p = boss.position().subtract(fwd.scale(2.5 + row * 1.8)).add(right.scale(side));
                places.add(ground(sl, p));
            }
            for (Vec3 p : places) Fx.play(sl, Fx.fx("martin_soldier_spawn").at(p).yaw(boss.getYRot()));
            core.sound("martin.soldier", 2, 1);
            List<MartinSoldierEntity> made = new ArrayList<>();
            core.play(new BossTimeline("summon_rise", MartinMath.SOLDIER_SPAWN_AT + 3)
                    .at(MartinMath.SOLDIER_SPAWN_AT, () -> {
                        if (!boss.isAlive() || core.inFinale() || core.phase() >= 2) return;
                        for (Vec3 p : places) {
                            MartinSoldierEntity s = Martin.SOLDIER.get().create(sl);
                            if (s == null) continue;
                            s.moveTo(p.x, p.y, p.z, boss.getYRot(), 0);
                            s.setYHeadRot(boss.getYRot());
                            s.setYBodyRot(boss.getYRot());
                            s.finalizeSpawn(sl, sl.getCurrentDifficultyAt(s.blockPosition()), MobSpawnType.MOB_SUMMONED, null, null);
                            s.setup(boss.getUUID(), MartinConfig.d(MartinConfig.SOLDIER_HP) * core.playerMultiplier(), MartinConfig.d(MartinConfig.SOLDIER_ARMOR));
                            sl.addFreshEntity(s);
                            soldiers.add(s.getUUID());
                            made.add(s);
                        }
                        reslot(sl);
                    })
                    .at(MartinMath.SOLDIER_SPAWN_AT + 2, () -> made.forEach(MartinSoldierEntity::riseAnim)));
        });
        core.play(t);
    }

    private void reslot(ServerLevel sl) {
        int i = 0;
        for (UUID u : soldiers)
            if (sl.getEntity(u) instanceof MartinSoldierEntity s) {
                s.slot = i++;
            }
        for (UUID u : soldiers) if (sl.getEntity(u) instanceof MartinSoldierEntity s) s.slots = i;
    }

    /** Banner aura, the formation icon, slots. */
    private void auras(ServerLevel sl) {
        MartinBannerEntity b = banner(sl);
        double r = MartinConfig.d(MartinConfig.BANNER_RADIUS);
        for (UUID u : soldiers)
            if (sl.getEntity(u) instanceof MartinSoldierEntity s) s.setBanner(sl, b != null && s.distanceToSqr(b) <= r * r);
        status(Martin.ST_FORMATION, formationActive());
        status(Martin.ST_BANNER, b != null);
        if (boss.tickCount % 40 == 0) reslot(sl);
    }

    void braceAll(int ticks) {
        for (UUID u : soldiers) if (sl().getEntity(u) instanceof MartinSoldierEntity s) s.brace(ticks);
    }

    private void vanishAll(ServerLevel sl) {
        for (UUID u : soldiers) if (sl.getEntity(u) instanceof MartinSoldierEntity s) s.vanish(sl);
        soldiers.clear();
    }

    private MartinBannerEntity banner(ServerLevel sl) {
        return banner != null && sl.getEntity(banner) instanceof MartinBannerEntity b && b.standing() ? b : null;
    }

    /** The banner left-front of him, exactly where the held banner of martin_banner_plant touches the ground (MartinMath.BANNER_*):
     *  by the body yaw — the model is drawn by it, so the entity replaces the held banner without a jump. */
    private void plantBanner(ServerLevel sl) {
        float yaw = boss.yBodyRot;
        Vec3 fwd = Vec3.directionFromRotation(0, yaw), left = new Vec3(fwd.z, 0, -fwd.x);
        Vec3 p = ground(sl, boss.position().add(fwd.scale(MartinMath.BANNER_FWD)).add(left.scale(MartinMath.BANNER_LEFT)));
        MartinBannerEntity b = Martin.BANNER.get().create(sl);
        if (b == null) return;
        b.moveTo(p.x, p.y, p.z, yaw, 0);
        b.setYBodyRot(yaw);
        b.setup(boss.getUUID(), MartinConfig.d(MartinConfig.BANNER_HP) * core.playerMultiplier());
        sl.addFreshEntity(b);
        banner = b.getUUID();
        core.sound(p, "martin.banner_plant", 3, 1);
        core.play(new BossTimeline("banner_fx", 3).at(1, () -> b.plantFx(sl)));
    }

    private void replant(ServerLevel sl) {
        core.lock(MartinMath.PLANT_ANIM, true, false);
        boss.anim("martin_banner_plant");
        core.play(new BossTimeline("replant", MartinMath.PLANT_AT + 1).at(MartinMath.PLANT_AT, () -> {
            if (core.phase() == 1 && !core.inFinale()) plantBanner(sl);
        }));
    }

    void onBannerCut(ServerLevel sl) {
        core.actionbar(core.arenaRadius() + 8, ui("banner_cut"));
        for (UUID u : soldiers) if (sl.getEntity(u) instanceof MartinSoldierEntity s) s.setBanner(sl, false);
        int re = MartinConfig.i(MartinConfig.BANNER_REPLANT);
        replantIn = core.phase() == 1 && re > 0 ? re * 20 : -1;
    }

    private void cutBanner(ServerLevel sl) {
        MartinBannerEntity b = banner(sl);
        if (b != null) b.cut(sl);
        replantIn = -1;
    }

    // ---------------------------------------------------------------- phases

    void onPhase(int from, int to) {
        ServerLevel sl = sl();
        if (to == 1 && from < 1) phase2(sl);
        if (to == 2) phase3(sl);
    }

    /** 66% «Знамя»: martin_phase2 (3 s), at 2.4 s martin_banner_plant, the banner on its plant (3.7 s). */
    private void phase2(ServerLevel sl) {
        if (formationFx > 0 && !MartinConfig.b(MartinConfig.FORMATION_P2)) {
            Fx.stop(sl, formationFx, "");
            formationFx = -1;
        }
        core.lock(MartinMath.P2_LOCK, true, false);
        boss.anim("martin_phase2");
        Fx.play(sl, Fx.fx("martin_phase2").caster(boss).at(boss.position()).yaw(boss.getYRot()));
        core.sound("martin.phase", 4, 1);
        core.actionbar(core.arenaRadius() + 8, ui("phase2"));
        core.play(new BossTimeline("phase2", MartinMath.P2_PLANT + 1)
                .at(MartinMath.P2_PLANT_ANIM, () -> boss.anim("martin_banner_plant"))
                .at(MartinMath.P2_PLANT, () -> {
                    if (core.phase() == 1) plantBanner(sl);
                }));
    }

    /** 33% «Последний полководец»: martin_phase3 (3.2 s), the army vanishes, the banner falls, fury from the roar (2.0 s). */
    private void phase3(ServerLevel sl) {
        core.lock(MartinMath.P3_ANIM, true, false);
        boss.anim("martin_phase3");
        Fx.play(sl, Fx.fx("martin_phase3").caster(boss).at(boss.position()).yaw(boss.getYRot()));
        core.sound("martin.phase", 4, 0.85f);
        core.actionbar(core.arenaRadius() + 8, ui("phase3"));
        vanishAll(sl);
        cutBanner(sl);
        refillIn = -1;
        if (formationFx > 0) Fx.stop(sl, formationFx, "");
        formationFx = -1;
        core.play(new BossTimeline("phase3", MartinMath.P3_ROAR + 1).at(MartinMath.P3_ROAR, () -> {
            if (furyFx < 0) furyFx = Fx.play(sl, Fx.fx("martin_fury").caster(boss).at(boss.position()).attach(boss));
            status(Martin.ST_LAST, true);
        }));
    }

    // ---------------------------------------------------------------- melee

    private boolean melee(ServerLevel sl, LivingEntity t, double d) {
        boolean p3 = core.phase() >= 2;
        String pick;
        if (p3 && d > 5 && d < 11 && bashCd <= 0) pick = "bash";
        else if (d <= 3.6) pick = boss.getRandom().nextInt(3) == 0 ? "overhead" : "swing";
        else if (d <= 5.2) pick = boss.getRandom().nextBoolean() ? "thrust" : "overhead";
        else return false;
        boss.getNavigation().stop();
        float yaw = boss.yawTo(t.position());
        boss.face(yaw);
        Vec3 o = boss.position(), fwd = Vec3.directionFromRotation(0, yaw);
        switch (pick) {
            case "swing" -> {
                core.lock(MartinMath.SWING, true, false);
                boss.anim("martin_swing");
                core.play(new BossTimeline("atk:swing", MartinMath.SWING_HIT + 1)
                        .at(MartinMath.SWING_SWING, () -> {
                            core.sound("martin.swing", 2, 1);
                            Fx.play(sl, Fx.fx("martin_swing_trail").caster(boss).at(boss.position()).yaw(boss.getYRot()));
                        })
                        .at(MartinMath.SWING_HIT, () -> {
                            double reach = MartinConfig.d(MartinConfig.SWING_REACH);
                            double dmg = BossConfig.get(BossConfig.of(Martin.ID).attack) + MartinConfig.d(MartinConfig.SWORD_DAMAGE);
                            for (LivingEntity e : targets(sl, boss.position(), reach))
                                if (MartinMath.inFront(boss.getYRot(), e.getX() - boss.getX(), e.getZ() - boss.getZ(), 200)
                                        && Math.abs(e.getY() - boss.getY()) < 4) hit(e, dmg);
                        }));
            }
            case "overhead" -> {
                core.lock(MartinMath.OVERHEAD, true, false);
                boss.anim("martin_overhead");
                core.play(new BossTimeline("atk:overhead", MartinMath.OVERHEAD_HIT + 1)
                        .at(MartinMath.OVERHEAD_SWING, () -> core.sound("martin.swing", 2, 0.8f))
                        .at(MartinMath.OVERHEAD_HIT, () -> {
                            Vec3 p = ground(sl, o.add(fwd.scale(4.5)));
                            Fx.play(sl, Fx.fx("martin_slam").at(p).yaw(yaw));
                            core.sound(p, "martin.slam", 3, 1);
                            for (LivingEntity e : targets(sl, p, 2.2)) if (Math.abs(e.getY() - p.y) < 3) hit(e, MartinConfig.d(MartinConfig.OVERHEAD_DAMAGE));
                        }));
            }
            case "thrust" -> {
                core.lock(MartinMath.THRUST, true, false);
                boss.anim("martin_thrust");
                core.play(new BossTimeline("atk:thrust", MartinMath.THRUST_HIT + 1)
                        .at(MartinMath.THRUST_HIT - 1, () -> {
                            core.sound("martin.swing", 2, 1.2f);
                            Fx.play(sl, Fx.fx("martin_swing_trail").caster(boss).at(boss.position()).yaw(yaw));
                        })
                        .at(MartinMath.THRUST_HIT, () -> {
                            Vec3 b = o.add(fwd.scale(5.6));
                            for (LivingEntity e : targets(sl, o.lerp(b, 0.5), 3.5)) {
                                double[] l = MartinMath.local(o.x, o.z, yaw, e.getX(), e.getZ());
                                if (l[1] > 0 && l[1] < 5.8 && Math.abs(l[0]) < 1.1 && Math.abs(e.getY() - o.y) < 4) hit(e, MartinConfig.d(MartinConfig.THRUST_DAMAGE));
                            }
                        }));
            }
            default -> bash(sl, t, yaw);
        }
        int min = MartinConfig.i(MartinConfig.MELEE_MIN), max = Math.max(min, MartinConfig.i(MartinConfig.MELEE_MAX));
        double k = core.phase() >= 2 ? MartinConfig.d(MartinConfig.P3_INTERVAL_MULT) : 1;
        meleeIn = (int) Math.round((min + boss.getRandom().nextInt(max - min + 1)) * k) + lockOf(pick);
        return true;
    }

    private static int lockOf(String pick) {
        return switch (pick) {
            case "swing" -> MartinMath.SWING;
            case "overhead" -> MartinMath.OVERHEAD;
            case "thrust" -> MartinMath.THRUST;
            default -> MartinMath.BASH;
        };
    }

    /** Phase 3: a dash with the shield up (0.45–0.75 s) along his facing, stopped by walls; who it meets is hit and thrown. */
    private void bash(ServerLevel sl, LivingEntity t, float yaw) {
        bashCd = 120;
        Vec3 o = boss.position(), dir = Vec3.directionFromRotation(0, yaw);
        double len = Math.min(8, Math.sqrt(boss.distanceToSqr(t)) + 1);
        HitResult hr = sl.clip(new ClipContext(o.add(0, 1, 0), o.add(0, 1, 0).add(dir.scale(len)), ClipContext.Block.COLLIDER, ClipContext.Fluid.NONE, boss));
        if (hr.getType() != HitResult.Type.MISS) len = Math.max(1, hr.getLocation().distanceTo(o.add(0, 1, 0)) - 1);
        Vec3 end = o.add(dir.scale(len));
        core.lock(MartinMath.BASH, true, false);
        boss.anim("martin_shield_bash");
        Set<UUID> hitSet = new HashSet<>();
        int dashTicks = MartinMath.BASH_HIT - MartinMath.BASH_DASH;
        core.play(new BossTimeline("atk:bash", MartinMath.BASH_HIT + 1)
                .at(MartinMath.BASH_DASH, () -> {
                    Fx.play(sl, Fx.fx("martin_dash").caster(boss).at(boss.position()).yaw(yaw).attach(boss));
                    core.sound("martin.bash", 3, 1);
                })
                .during(MartinMath.BASH_DASH + 1, MartinMath.BASH_HIT, k -> {
                    Vec3 p = o.lerp(end, (k - MartinMath.BASH_DASH) / (double) dashTicks);
                    boss.moveTo(p.x, p.y, p.z, yaw, 0);
                    for (LivingEntity e : targets(sl, p.add(dir.scale(0.8)), 1.8))
                        if (hitSet.add(e.getUUID()) && Math.abs(e.getY() - p.y) < 3.5) {
                            hit(e, MartinConfig.d(MartinConfig.SHIELD_DASH_DAMAGE));
                            double push = MartinConfig.d(MartinConfig.SHIELD_DASH_PUSH);
                            e.push(dir.x * push, 0.4, dir.z * push);
                            e.hurtMarked = true;
                        }
                }));
    }

    // ---------------------------------------------------------------- specials

    boolean special(String id) {
        if (core.inScene() || core.locked() || yielding || yieldWait) return false;
        if (id.equals("hold_the_line")) hold(sl());
        else if (id.equals("cavalry")) cavalry(sl());
        return true;
    }

    /** «Приказ стоять насмерть»: shield into the ground; from `wall` (1.1 s) 10 s he and the soldiers take nothing from the front. */
    private void hold(ServerLevel sl) {
        int dur = MartinConfig.i(MartinConfig.HOLD_SECONDS) * 20;
        LivingEntity t = boss.getTarget();
        if (t != null) boss.face(boss.yawTo(t.position()));
        core.lock(MartinMath.HOLD_WALL + dur + MartinMath.HOLD_END_ANIM, true, false);
        boss.anim("martin_hold_the_line");
        List<ServerPlayer> who = core.scene("martin.hold", MartinMath.HOLD_SCENE, BossNet.SCENE_BARS, BossConfig.get(BossConfig.SCENE_RADIUS),
                boss.position(), boss.getYRot(), -1);
        core.play(new BossTimeline("scene:hold", MartinMath.HOLD_SCENE)
                .at(MartinMath.HOLD_TITLE, () -> core.title(who, "martin_hold", 50, null)));
        core.play(new BossTimeline("hold", MartinMath.HOLD_WALL + dur + 1)
                .at(MartinMath.HOLD_WALL, () -> {
                    long until = sl.getGameTime() + dur;
                    holdUntil = until;
                    core.sound("martin.hold", 4, 1);
                    holdFx = Fx.play(sl, Fx.fx("martin_hold_the_line").caster(boss).at(boss.position()).yaw(boss.getYRot()).attach(boss).duration(dur));
                    for (UUID u : soldiers)
                        if (sl.getEntity(u) instanceof MartinSoldierEntity s) {
                            s.holdUntil = until;
                            s.holdFx = Fx.play(sl, Fx.fx("martin_hold_soldier").caster(s).at(s.position()).yaw(s.getYRot()).attach(s).duration(dur));
                        }
                    core.actionbar(core.arenaRadius() + 8, ui("hold", dur / 20));
                    status(Martin.ST_HOLD, true);
                })
                .at(MartinMath.HOLD_SCENE, () -> boss.anim("martin_hold_loop"))
                .at(MartinMath.HOLD_WALL + dur, () -> {
                    boss.anim("martin_hold_end");
                    status(Martin.ST_HOLD, false);
                    holdFx = -1;
                    core.actionbar(core.arenaRadius() + 8, ui("hold_end"));
                }));
    }

    private record Lane(Vec3 start, float yaw, Set<UUID> hit) {}

    /** «Атака конницы»: the sword to the sky, the horn; 3–5 lanes across the arena glow 2 s, then three riders gallop down each. */
    private void cavalry(ServerLevel sl) {
        LivingEntity t = boss.getTarget();
        if (t != null) boss.face(boss.yawTo(t.position()));
        float yaw = boss.getYRot();
        core.lock(MartinMath.CAV_ANIM, true, false);
        boss.anim("martin_cavalry");
        Fx.play(sl, Fx.fx("martin_cavalry_cast").caster(boss).at(boss.position()).yaw(yaw));
        List<ServerPlayer> who = core.scene("martin.cavalry", MartinMath.CAV_SCENE, BossNet.SCENE_BARS, BossConfig.get(BossConfig.SCENE_RADIUS),
                core.arena(), yaw, -1);
        List<Lane> lanes = new ArrayList<>();
        int riders = MartinMath.LANE_WARN + 2 * (MartinMath.RIDERS - 1) + MartinMath.RIDER_TICKS;
        core.play(new BossTimeline("scene:cavalry", MartinMath.CAV_CALL + riders + 2)
                .at(MartinMath.CAV_TITLE, () -> core.title(who, "martin_cavalry", 50, null))
                .at(MartinMath.CAV_CALL, () -> {
                    core.sound("martin.horn", 5, 1);
                    lanes.addAll(laneStarts(sl, yaw));
                    for (Lane l : lanes) Fx.play(sl, Fx.fx("martin_cavalry_lane").at(l.start()).yaw(l.yaw()));
                    core.actionbar(core.arenaRadius() + 8, ui("cavalry_warn"));
                    status(Martin.ST_CAVALRY, true);
                })
                .at(MartinMath.CAV_CALL + MartinMath.LANE_WARN, () -> core.sound(core.arena(), "martin.gallop", 5, 1))
                .during(MartinMath.CAV_CALL + MartinMath.LANE_WARN, MartinMath.CAV_CALL + riders, k -> {
                    int lt = k - MartinMath.CAV_CALL;
                    double push = MartinConfig.d(MartinConfig.CAVALRY_PUSH);
                    for (Lane l : lanes) {
                        Vec3 fwd = Vec3.directionFromRotation(0, l.yaw());
                        Vec3 mid = l.start().add(fwd.scale(MartinMath.LANE_LENGTH / 2.0));
                        for (LivingEntity e : targets(sl, mid, MartinMath.LANE_LENGTH / 2.0 + 8)) {
                            if (l.hit().contains(e.getUUID()) || Math.abs(e.getY() - l.start().y) > 3) continue;
                            double[] p = MartinMath.local(l.start().x, l.start().z, l.yaw(), e.getX(), e.getZ());
                            if (!MartinMath.laneHit(p[0], p[1], lt)) continue;
                            l.hit().add(e.getUUID());
                            hit(e, MartinConfig.d(MartinConfig.CAVALRY_DAMAGE));
                            e.push(fwd.x * push, 0.5, fwd.z * push);
                            e.hurtMarked = true;
                        }
                    }
                })
                .then(() -> status(Martin.ST_CAVALRY, false)));
    }

    /** Parallel lanes along his facing through the arena: one on each player (merged when close), the rest spread evenly. */
    private List<Lane> laneStarts(ServerLevel sl, float yaw) {
        Vec3 c = core.arena();
        int n = MartinMath.lanes(core.fighters().size(), MartinConfig.i(MartinConfig.CAVALRY_LANES));
        double r = Math.max(6, core.arenaRadius() - 3);
        List<Double> xs = new ArrayList<>();
        for (ServerPlayer p : core.fighters()) {
            if (xs.size() >= n) break;
            double x = Mth.clamp(MartinMath.local(c.x, c.z, yaw, p.getX(), p.getZ())[0], -r, r);
            if (xs.stream().noneMatch(o -> Math.abs(o - x) < 3.5)) xs.add(x);
        }
        for (int i = 0; xs.size() < n && i < 40; i++) {
            double x = -r + 2 * r * boss.getRandom().nextDouble();
            if (xs.stream().noneMatch(o -> Math.abs(o - x) < 4)) xs.add(x);
        }
        double a = Math.toRadians(yaw);
        Vec3 fwd = Vec3.directionFromRotation(0, yaw), right = new Vec3(-Math.cos(a), 0, -Math.sin(a));   // as FxMath / MartinMath.local
        List<Lane> out = new ArrayList<>();
        for (double x : xs) {
            Vec3 s = ground(sl, c.add(right.scale(x)).subtract(fwd.scale(MartinMath.LANE_LENGTH / 2.0)));
            out.add(new Lane(new Vec3(s.x, c.y, s.z), yaw, new HashSet<>()));
        }
        return out;
    }

    // ---------------------------------------------------------------- the four spells (no scene; each with its warning)

    private boolean castSpell(ServerLevel sl, LivingEntity t) {
        if (duelUntil >= 0 || holdUntil >= 0) return false;
        List<String> can = new ArrayList<>();
        if (ready("shield_wall")) can.add("shield_wall");
        if (ready("volley")) can.add("volley");
        if (ready("duel") && t instanceof ServerPlayer && core.fighters().size() >= 2) can.add("duel");
        if (ready("warcry")) can.add("warcry");
        if (can.isEmpty() || boss.getRandom().nextInt(3) == 0) return false;   // not always: melee in between
        switch (can.get(boss.getRandom().nextInt(can.size()))) {
            case "shield_wall" -> {
                shieldWall(sl, t);
                cooldown.put("shield_wall", MartinConfig.i(MartinConfig.WALL_COOLDOWN) * 20);
            }
            case "volley" -> {
                volley(sl);
                cooldown.put("volley", MartinConfig.i(MartinConfig.VOLLEY_COOLDOWN) * 20);
            }
            case "duel" -> {
                duel(sl, t);
                cooldown.put("duel", MartinConfig.i(MartinConfig.DUEL_COOLDOWN) * 20);
            }
            default -> {
                warcry(sl);
                cooldown.put("warcry", MartinConfig.i(MartinConfig.WARCRY_COOLDOWN) * 20);
            }
        }
        return true;
    }

    private boolean ready(String id) {
        return cooldown.getOrDefault(id, 0) <= 0;
    }

    /** «Стена щитов»: shield slammed (1.0 s) — a ghost wall with three gaps rises 4 blocks behind him and walks 18 blocks at the players. */
    private void shieldWall(ServerLevel sl, LivingEntity t) {
        float yaw = boss.yawTo(t.position());
        boss.face(yaw);
        core.lock(MartinMath.WALL_ANIM, true, false);
        boss.anim("martin_shield_wall");
        core.actionbar(core.arenaRadius() + 8, ui("shield_wall"));
        Vec3 fwd = Vec3.directionFromRotation(0, yaw);
        Vec3[] start = {null};
        Set<UUID> hurt = new HashSet<>();
        int end = MartinMath.WALL_SLAM + MartinMath.WALL_RISE + MartinMath.WALL_MOVE;
        core.play(new BossTimeline("spell:shield_wall", end + 1)
                .at(MartinMath.WALL_SLAM, () -> {
                    start[0] = ground(sl, boss.position().subtract(fwd.scale(4)));
                    Fx.play(sl, Fx.fx("martin_shield_wall").at(start[0]).yaw(yaw));
                    core.sound("martin.shield_wall", 4, 1);
                    status(Martin.ST_SHIELD_WALL, true);
                })
                .during(MartinMath.WALL_SLAM + 1, end, k -> {
                    if (start[0] == null) return;
                    double wz = MartinMath.wallZ(k - MartinMath.WALL_SLAM);
                    Vec3 mid = start[0].add(fwd.scale(wz));
                    double push = MartinConfig.d(MartinConfig.WALL_PUSH);
                    for (LivingEntity e : targets(sl, mid, MartinMath.WALL_HALF_WIDTH + 1)) {
                        if (!(e instanceof Player) || Math.abs(e.getY() - start[0].y) > 3) continue;
                        double[] p = MartinMath.local(start[0].x, start[0].z, yaw, e.getX(), e.getZ());
                        if (!MartinMath.wallPushes(p[0], p[1], wz)) continue;
                        e.push(fwd.x * push * 0.5, 0.1, fwd.z * push * 0.5);
                        e.hurtMarked = true;
                        if (hurt.add(e.getUUID())) {
                            e.push(fwd.x * push * 0.5, 0.2, fwd.z * push * 0.5);
                            hit(e, MartinConfig.d(MartinConfig.WALL_DAMAGE));
                        }
                    }
                })
                .then(() -> status(Martin.ST_SHIELD_WALL, false)));
    }

    /** «Залп лучников»: ghost archers rise behind him (draw 0.8 s); on loose (1.2 s) red marks under the players, arrows 1.5 s later. */
    private void volley(ServerLevel sl) {
        core.lock(MartinMath.VOLLEY, true, false);
        boss.anim("martin_volley");
        List<Vec3> marks = new ArrayList<>();
        int impact = MartinMath.VOLLEY_LOOSE + MartinMath.VOLLEY_IMPACT;
        core.play(new BossTimeline("spell:volley", impact + 1)
                .at(MartinMath.VOLLEY_DRAW, () -> {
                    Fx.play(sl, Fx.fx("martin_volley").caster(boss).at(boss.position()).yaw(boss.getYRot()));
                    core.sound("martin.volley", 3, 1);
                    core.actionbar(core.arenaRadius() + 8, ui("volley"));
                    status(Martin.ST_VOLLEY, true);
                })
                .at(MartinMath.VOLLEY_LOOSE, () -> {
                    List<ServerPlayer> fighters = core.fighters();
                    if (fighters.isEmpty()) return;
                    int n = MartinMath.volleyMarks(fighters.size(), MartinConfig.i(MartinConfig.VOLLEY_BASE), MartinConfig.i(MartinConfig.VOLLEY_MAX));
                    for (int i = 0; i < n; i++) {
                        ServerPlayer p = fighters.get(i % fighters.size());
                        double a = boss.getRandom().nextDouble() * Math.PI * 2, d = i < fighters.size() ? 0 : 1.6 + boss.getRandom().nextDouble() * 1.8;
                        Vec3 q = ground(sl, p.position().add(Math.cos(a) * d, 0, Math.sin(a) * d));
                        marks.add(q);
                        Fx.play(sl, Fx.fx("martin_volley_mark").at(q));
                    }
                    core.actionbar(core.arenaRadius() + 8, ui("volley_warn"));
                })
                .at(impact, () -> {
                    double r = MartinConfig.d(MartinConfig.VOLLEY_RADIUS);
                    for (Vec3 q : marks)
                        for (LivingEntity e : targets(sl, q, r)) if (Math.abs(e.getY() - q.y) < 3) hit(e, MartinConfig.d(MartinConfig.VOLLEY_DAMAGE));
                    if (!marks.isEmpty()) core.sound(marks.get(0), "martin.arrow_hit", 3, 1);
                    status(Martin.ST_VOLLEY, false);
                }));
    }

    /** «Вызов на дуэль»: the sword at the strongest player (0.9 s) — a ring r6 for 6 s: only the two of them deal damage inside. */
    private void duel(ServerLevel sl, LivingEntity fallback) {
        ServerPlayer p = core.strongestEnemy();
        if (p == null && fallback instanceof ServerPlayer sp) p = sp;
        if (p == null) return;
        ServerPlayer target = p;
        boss.face(boss.yawTo(target.position()));
        core.lock(MartinMath.DUEL, true, false);
        boss.anim("martin_duel");
        core.play(new BossTimeline("spell:duel", MartinMath.DUEL_CHALLENGE + 1).at(MartinMath.DUEL_CHALLENGE, () -> {
            if (!target.isAlive() || target.level() != sl) return;
            int dur = MartinConfig.i(MartinConfig.DUEL_SECONDS) * 20;
            duelist = target.getUUID();
            duelAt = ground(sl, boss.position().lerp(target.position(), 0.5));
            duelUntil = sl.getGameTime() + dur;
            DUELS.add(this);
            duelFx = Fx.play(sl, Fx.fx("martin_duel").at(duelAt).yaw(boss.getYRot()).duration(dur));
            duelMarkFx = Fx.play(sl, Fx.fx("martin_duel_mark").caster(target).at(target.position()).attach(target).duration(dur));
            core.sound("martin.duel", 4, 1);
            core.actionbar(core.arenaRadius() + 8, ui("duel", target.getDisplayName()));
            status(Martin.ST_DUEL, true);
            boss.setTarget(target);
        }));
    }

    private void duelTick(ServerLevel sl, long now) {
        ServerPlayer d = duelist != null && sl.getEntity(duelist) instanceof ServerPlayer p ? p : null;
        double r = MartinConfig.d(MartinConfig.DUEL_RADIUS);
        if (now >= duelUntil || d == null || !d.isAlive() || d.distanceToSqr(duelAt) > (r + 8) * (r + 8)) {
            endDuel(sl, true);
            return;
        }
        double push = MartinConfig.d(MartinConfig.DUEL_PUSH);
        for (ServerPlayer p : sl.players()) {
            if (p == d || p.isCreative() || p.isSpectator()) continue;
            Vec3 out = p.position().subtract(duelAt).multiply(1, 0, 1);
            double dist = out.length();
            if (dist >= r || Math.abs(p.getY() - duelAt.y) > 6) continue;
            Vec3 n = dist < 1e-3 ? new Vec3(1, 0, 0) : out.scale(1 / dist);
            p.push(n.x * push, 0.25, n.z * push);
            p.hurtMarked = true;
            if (now % 10 == 0) Fx.play(sl, Fx.fx("martin_duel_push").at(duelAt.add(n.scale(r)).add(0, 1, 0)));
            tell(p, ui("duel_blocked"));
        }
    }

    private void endDuel(ServerLevel sl, boolean say) {
        if (duelUntil < 0) return;
        duelUntil = -1;
        duelist = null;
        DUELS.remove(this);
        if (duelFx > 0) Fx.stop(sl, duelFx, "");
        if (duelMarkFx > 0) Fx.stop(sl, duelMarkFx, "");
        duelFx = duelMarkFx = -1;
        status(Martin.ST_DUEL, false);
        if (say) core.actionbar(core.arenaRadius() + 8, ui("duel_end"));
    }

    /** «Боевой клич» (cry 0.6 s): every cast in r12 is broken (no mana back), his soldiers hit ×1.25 for 6 s. */
    private void warcry(ServerLevel sl) {
        core.lock(MartinMath.WARCRY, true, false);
        boss.anim("martin_warcry");
        core.play(new BossTimeline("spell:warcry", MartinMath.WARCRY_CRY + 1).at(MartinMath.WARCRY_CRY, () -> {
            double r = MartinConfig.d(MartinConfig.WARCRY_RADIUS);
            Fx.play(sl, Fx.fx("martin_warcry").caster(boss).at(boss.position()).yaw(boss.getYRot()));
            core.sound("martin.warcry", 5, 1);
            core.actionbar(r + 8, ui("warcry"));
            for (LivingEntity e : sl.getEntitiesOfClass(LivingEntity.class, boss.getBoundingBox().inflate(r))) {
                if (e == boss || e instanceof MartinSoldierEntity || e.distanceToSqr(boss) > r * r) continue;
                boolean casting = e instanceof Player ? MagicData.getPlayerMagicData(e).isCasting() : e instanceof IMagicEntity m ? m.isCasting() : NpcCast.isCasting(e);
                if (!casting) continue;
                NpcCast.cancelAny(e);
                Fx.play(sl, Fx.fx("martin_warcry_interrupt").caster(e).at(e.position()));
                if (e instanceof ServerPlayer sp) sp.displayClientMessage(ui("warcry_interrupt"), true);
            }
            int dur = MartinConfig.i(MartinConfig.WARCRY_SECONDS) * 20;
            long until = sl.getGameTime() + dur;
            for (UUID u : soldiers)
                if (sl.getEntity(u) instanceof MartinSoldierEntity s) {
                    s.warcryUntil = until;
                    if (s.warcryFx < 0) s.warcryFx = Fx.play(sl, Fx.fx("martin_warcry_buff").caster(s).at(s.position()).attach(s).duration(dur));
                }
            status(Martin.ST_WARCRY, true);
            core.play(new BossTimeline("warcry_end", dur + 1).at(dur, () -> status(Martin.ST_WARCRY, false)));
        }));
    }

    // ---------------------------------------------------------------- surrender (5%: the next blow is blocked)

    /** Health reached 5%: the framework locked him (invulnerable, no AI) and took the bar; he raises his guard and waits for a blow. */
    void startYield() {
        ServerLevel sl = sl();
        stopRunning(sl);
        yieldWait = true;
        yieldIn = MartinMath.YIELD_WAIT;
        boss.anim("martin_hold_loop");
    }

    /** Called from hurt() while the finale is on. */
    void onHitInFinale(DamageSource src) {
        if (yieldWait && src.getEntity() instanceof ServerPlayer p) block(sl(), p);
    }

    /** The blow is taken on the shield; he lowers his sword, the army fades, the phrase; then the peaceful NPC takes his place. */
    private void block(ServerLevel sl, ServerPlayer by) {
        if (!yieldWait) return;
        yieldWait = false;
        yielding = true;
        if (by != null) boss.face(boss.yawTo(by.position()));
        float yaw = boss.getYRot();
        boss.anim("martin_block_yield");
        List<ServerPlayer> who = core.scene("martin.yield", MartinMath.YIELD_CAM, BossNet.SCENE_LOCK_INPUT | BossNet.SCENE_BARS | BossNet.SCENE_NO_HUD,
                BossConfig.get(BossConfig.INTRO_RADIUS), boss.position(), yaw, by != null ? by.getId() : -1);
        core.play(new BossTimeline("yield", MartinMath.YIELD_END)
                .at(MartinMath.YIELD_BLOCK, () -> {
                    core.sound("martin.block", 4, 1);   // shield clang layered in (no vanilla SHIELD_BLOCK on top)
                    Fx.play(sl, Fx.fx("martin_block").caster(boss).at(boss.position()).yaw(yaw));
                })
                .at(MartinMath.YIELD_LOWER, () -> {
                    vanishAll(sl);
                    cutBanner(sl);
                    stopAuras(sl);
                    Fx.play(sl, Fx.fx("martin_yield").caster(boss).at(boss.position()).yaw(yaw));
                })
                .at(MartinMath.YIELD_SPEAK, () -> core.say("ui.pohsmp_core.martin.yield", 48, 80, 4.6))
                .at(MartinMath.YIELD_TO_NPC, () -> boss.anim("martin_to_npc"))
                .at(MartinMath.YIELD_CAM, () -> core.sceneStop(who, "martin.yield"))
                .then(() -> {
                    DUELS.remove(this);
                    core.endFinale();
                }));
    }

    // ---------------------------------------------------------------- cleanup

    /** Stops what runs (duel, hold, statuses) — the army stays (the surrender fades it on `lower`). */
    private void stopRunning(ServerLevel sl) {
        endDuel(sl, false);
        holdUntil = -1;
        if (holdFx > 0) Fx.stop(sl, holdFx, "");
        holdFx = -1;
        for (UUID u : soldiers)
            if (sl.getEntity(u) instanceof MartinSoldierEntity s) {
                s.holdUntil = 0;
                s.stopFx(sl);
            }
        for (int bit : Martin.STATUS_BITS) status(bit, false);
        refillIn = replantIn = -1;
    }

    private void stopAuras(ServerLevel sl) {
        if (formationFx > 0) Fx.stop(sl, formationFx, "");
        if (furyFx > 0) Fx.stop(sl, furyFx, "");
        formationFx = furyFx = -1;
    }

    /** Killed or removed: the army, the banner and the effects go with him. */
    void cleanup(ServerLevel sl) {
        stopRunning(sl);
        stopAuras(sl);
        vanishAll(sl);
        MartinBannerEntity b = banner(sl);
        if (b != null) b.cut(sl);
        DUELS.remove(this);
    }

    /** After a reload: find his soldiers and banner again, restart the auras of the current phase. */
    void afterLoad() {
        recollect = true;
    }

    private void recollect(ServerLevel sl) {
        recollect = false;
        for (MartinSoldierEntity s : sl.getEntitiesOfClass(MartinSoldierEntity.class, boss.getBoundingBox().inflate(64)))
            if (boss.getUUID().equals(s.leader) && !soldiers.contains(s.getUUID())) soldiers.add(s.getUUID());
        for (MartinBannerEntity b : sl.getEntitiesOfClass(MartinBannerEntity.class, boss.getBoundingBox().inflate(64)))
            if (boss.getUUID().equals(b.leader) && b.standing()) {
                banner = b.getUUID();
                if (b.auraFx < 0) b.auraFx = Fx.play(sl, Fx.fx("martin_banner_aura").caster(b).at(b.position()).attach(b));
            }
        if (core.phase() < 2) {
            refillIn = 100;
            if (formationFx < 0 && (core.phase() == 0 || MartinConfig.b(MartinConfig.FORMATION_P2)))
                formationFx = Fx.play(sl, Fx.fx("martin_formation").caster(boss).at(boss.position()).attach(boss));
            if (core.phase() == 1 && banner(sl) == null) replantIn = 100;
        } else {
            furyFx = Fx.play(sl, Fx.fx("martin_fury").caster(boss).at(boss.position()).attach(boss));
            status(Martin.ST_LAST, true);
        }
    }

    // ---------------------------------------------------------------- helpers

    static Vec3 ground(ServerLevel sl, Vec3 p) {
        int y = sl.getHeight(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES, Mth.floor(p.x), Mth.floor(p.z));
        return Math.abs(y - p.y) <= 6 ? new Vec3(p.x, y, p.z) : p;
    }

    /** Living things he may hurt near p (horizontal radius r): not his side, not creative / spectators. */
    private List<LivingEntity> targets(ServerLevel sl, Vec3 p, double r) {
        List<LivingEntity> out = new ArrayList<>();
        for (LivingEntity e : sl.getEntitiesOfClass(LivingEntity.class, new AABB(p, p).inflate(r, 10, r))) {
            if (e == boss || e instanceof MartinSoldierEntity || e instanceof MartinBannerEntity || !e.isAlive()) continue;
            if (e instanceof Player pl && (pl.isCreative() || pl.isSpectator())) continue;
            if (e.distanceToSqr(p.x, e.getY(), p.z) > r * r) continue;
            out.add(e);
        }
        return out;
    }

    // ---------------------------------------------------------------- events

    public static final class Events {
        private Events() {}

        /** «Вызов на дуэль»: inside the duel only Martin may hurt the duelist (soldiers, other players and their spells may not). */
        @SubscribeEvent
        public static void onAttack(LivingAttackEvent e) {
            if (DUELS.isEmpty() || e.getEntity().level().isClientSide) return;
            Entity by = e.getSource().getEntity();
            if (by == null) return;
            for (MartinFight f : DUELS) {
                if (f.duelist == null || !f.duelist.equals(e.getEntity().getUUID())) continue;
                if (by == f.boss) return;
                e.setCanceled(true);
                f.tell(by, ui("duel_blocked"));
                return;
            }
        }
    }
}
