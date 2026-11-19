package ru.pohsmp.core.spell.silent;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.spells.SpellRarity;
import io.redspace.ironsspellbooks.api.util.Utils;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.decoration.ArmorStand;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.entity.projectile.ProjectileUtil;
import net.minecraft.world.level.ClipContext;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.EntityHitResult;
import net.minecraft.world.phys.HitResult;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.ServerConfig;
import ru.pohsmp.core.SilentWitch;
import ru.pohsmp.core.fx.Fx;
import ru.pohsmp.core.fx.FxLib;
import ru.pohsmp.core.spell.CnpcHooks;
import ru.pohsmp.core.spell.Cutscene;
import ru.pohsmp.core.spell.HigherSpell;

/**
 * "Gate" (T03): Silent school, Unknown tier, only from the Silent Witch's staff and only in her full outfit (T18/T19, see {@link SilentWitch}).
 * A 50 s cast that nothing interrupts, all of it to the music track: every player within 64 blocks of the caster or of the strike point
 * hears it (not positional, client: SilentMusic) with every other game sound muted, and watches the camera scene (Cutscene 6).
 * From 50 s (the spell is cast) to 63 s rays fall on the area (radius 20) and on every foe in it; at 52 s the main beam hits the aimed
 * creature (or the centre); at 64 s an ice crystal mountain rises (only a look). The scene ends at 65 s. Cancel = the track fades in 1 s.
 * Damage: Silent magic (through armor, Silent power, Silent resistance), numbers in [silent_gate]. Afterwards "Silence": the spell's own
 * cooldown, 3 min. The caster, the caster's team, its pets and allied CNPC NPCs are never hit.
 */
public class SilentGateSpell extends SilentStaffSpell {
    public static final String PATH = "silent_gate";
    /** Ticks: cast (= 50 s in the track), first rays, main beam, last rays, crystal, end of the scene, crystal life. */
    public static final int CAST = 1000, RAYS_FROM = 1000, MAIN = 1040, RAYS_TO = 1260, CRYSTAL = 1280, END = 1300, CRYSTAL_LIFE = 600;
    /** Height of the gate over the strike point (the placeholder effect and the main beam start there). */
    public static final double GATE_H = 26;
    /** Effect ids of the ideas chat (T03); while they are not in the mod the placeholders built from the existing seals are used. */
    private static final String FX_SCENE = "silent_gate", FX_RAY = "silent_gate_ray", FX_MAIN = "silent_gate_main", FX_CRYSTAL = "silent_gate_crystal";

    private static final class Cast {
        LivingEntity caster;
        ServerLevel sl;
        Vec3 at, hit;
        float yaw;
        LivingEntity aim;
        int age, cutKey, scene = -1;
        boolean cast, done;
        List<UUID> watchers = new ArrayList<>();
        final Map<UUID, Integer> lastHit = new HashMap<>();
        double rayDebt;
    }

    private static final Map<UUID, Cast> CASTS = new HashMap<>();
    /** Running scenes (cast or strike phase), for the tick loop. */
    private static final List<Cast> RUNNING = new ArrayList<>();
    private static boolean hitting;

    public SilentGateSpell() {
        super(PATH, 180, CAST, 0);
    }

    @Override protected boolean ready() { return true; }
    @Override public CastType getCastType() { return CastType.LONG; }
    @Override public boolean canBeInterrupted(Player player) { return false; }
    /** No spell sounds: only the music (T03). */
    @Override public Optional<SoundEvent> getCastStartSound() { return Optional.empty(); }
    @Override public Optional<SoundEvent> getCastFinishSound() { return Optional.empty(); }
    /** The cast is bound to the music: nothing shortens it (cast time reduction, the robe's Silent Reading). */
    @Override public int getEffectiveCastTime(int spellLevel, LivingEntity entity) { return CAST; }
    /** "Silence": Gate's own cooldown. */
    @Override public int getSpellCooldown() { return ServerConfig.GATE_SILENCE_SECONDS.get() * 20; }

    /** True while the Gate is dealing its damage (Cutscene lets it through to the frozen watchers). */
    public static boolean hitting() {
        return hitting;
    }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("cast", CAST / 20),
                ui("rays", n(ServerConfig.GATE_RAY_DAMAGE.get() * ServerConfig.GATE_SET_BONUS.get()), n(ServerConfig.GATE_AREA.get())),
                ui("main", (int) Math.round(ServerConfig.GATE_MAIN_PERCENT.get() * 100) + "%", n(ServerConfig.GATE_MAIN_FLAT.get())),
                ui("silence", ServerConfig.GATE_SILENCE_SECONDS.get() / 60));
    }

    /** Staff: checked by {@link SilentStaffSpell}. Outfit: the full Silent Witch set (stub until T19 registers the pieces). */
    @Override
    protected String whyNot(Level level, LivingEntity entity) {
        return SilentWitch.hasFullSet(entity) ? null : "need_set";
    }

    /** Why the Gate must stop mid-cast (staff dropped or a piece taken off), or null. */
    private static String why(LivingEntity e) {
        if (!SilentWitch.hasStaff(e)) return "need_staff";
        if (!SilentWitch.hasFullSet(e)) return "need_set";
        return null;
    }

    @Override
    public void onServerPreCast(Level level, int spellLevel, LivingEntity caster, MagicData md) {
        super.onServerPreCast(level, spellLevel, caster, md);
        if (level instanceof ServerLevel sl && !CASTS.containsKey(caster.getUUID())) start(sl, caster);
    }

    private void start(ServerLevel sl, LivingEntity caster) {
        Cast c = new Cast();
        c.caster = caster;
        c.sl = sl;
        c.at = caster.position();
        c.yaw = caster.getYRot();
        double range = ServerConfig.GATE_RANGE.get();
        Vec3 eye = caster.getEyePosition(), end = eye.add(caster.getLookAngle().scale(range));
        BlockHitResult bh = sl.clip(new ClipContext(eye, end, ClipContext.Block.COLLIDER, ClipContext.Fluid.NONE, caster));
        if (bh.getType() != HitResult.Type.MISS) end = bh.getLocation();
        EntityHitResult eh = ProjectileUtil.getEntityHitResult(sl, caster, eye, end, new AABB(eye, end).inflate(1),
                e -> e instanceof LivingEntity && e != caster && !e.isSpectator() && e.isPickable() && !(e instanceof ArmorStand));
        if (eh != null && eh.getEntity() instanceof LivingEntity le && !friendly(caster, le)) c.aim = le;
        Vec3 p = eh != null ? eh.getEntity().position() : end;
        if (hdist(caster, p) < 8) {
            Vec3 fw = caster.getLookAngle().multiply(1, 0, 1);
            fw = fw.lengthSqr() < 1e-4 ? new Vec3(0, 0, 1) : fw.normalize();
            p = c.at.add(fw.scale(12)).add(0, 1, 0);
        }
        c.hit = ground(sl, caster, p);
        c.cutKey = HigherSpell.key();
        Vec3 d = c.hit.subtract(c.at);
        float ang = (float) Math.atan2(-d.z, -d.x);
        // camera + music + silence for everyone within 64 of the caster or of the strike point
        c.watchers = Cutscene.start(sl, caster, c.cutKey, Cutscene.SILENT_GATE, END, c.hit, ang, Cutscene.R, sl, c.hit);
        String scene = FxLib.fx(FX_SCENE) != null ? FX_SCENE : FX_SCENE + "_placeholder";
        // fixed points, not the caster (its head turns would swing the offsets): c - the caster's feet, hit, gate
        c.scene = Fx.play(sl, Fx.fx(scene).at(c.at).yaw(c.yaw).target(c.hit).point("c", c.at).point("hit", c.hit)
                .point("gate", c.hit.add(0, GATE_H, 0)).duration(END));
        CASTS.put(caster.getUUID(), c);
        RUNNING.add(c);
    }

    @Override
    public void onServerCastTick(Level level, int spellLevel, LivingEntity caster, MagicData md) {
        super.onServerCastTick(level, spellLevel, caster, md);
        if (!(level instanceof ServerLevel sl)) return;
        Cast c = CASTS.get(caster.getUUID());
        if (c == null) {
            start(sl, caster);
            return;
        }
        // took off a piece of the outfit or dropped the staff: the cast stops (music fades, sound returns)
        if (why(caster) != null && caster instanceof ServerPlayer sp) Utils.serverSideCancelCast(sp);
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        Cast c = CASTS.get(caster.getUUID());
        if (c != null) c.cast = true;
        super.onCast(level, spellLevel, caster, source, md);
    }

    @Override
    public void onServerCastComplete(Level level, int spellLevel, LivingEntity caster, MagicData md, boolean cancelled) {
        Cast c = CASTS.remove(caster.getUUID());
        if (c != null && (cancelled || !c.cast)) cancel(c);
        super.onServerCastComplete(level, spellLevel, caster, md, cancelled);
    }

    /** Cast stopped before 50 s: the scene, effects and music end (the client fades the track in 1 s). */
    private static void cancel(Cast c) {
        if (c.done) return;
        c.done = true;
        RUNNING.remove(c);
        if (c.scene >= 0) Fx.stop(c.sl, c.scene, "collapse");
        Cutscene.end(c.sl, c.caster, c.watchers, c.cutKey);
    }

    // ---- the scene clock: the Iron's cast covers 0-50 s, the strike runs on here until 65 s ----

    private static void tick(Cast c) {
        c.age++;
        int t = c.age;
        if (!c.cast && t > CAST + 40) {   // the cast never reported back (caster gone): drop the scene
            cancel(c);
            return;
        }
        if (t < RAYS_FROM) return;
        if (!c.caster.isAlive() || c.caster.level() != c.sl) {   // caster died or left during the strike: stop quietly
            cancel(c);
            return;
        }
        if (t <= RAYS_TO) rays(c, t);
        if (t == MAIN) mainBeam(c);
        if (t == CRYSTAL) crystal(c);
        if (t >= END) {
            c.done = true;
            RUNNING.remove(c);
            Cutscene.end(c.sl, c.caster, c.watchers, c.cutKey);
        }
    }

    private static void rays(Cast c, int t) {
        double area = ServerConfig.GATE_AREA.get();
        c.rayDebt += ServerConfig.GATE_RAYS_PER_SECOND.get() / 20.0;
        while (c.rayDebt >= 1) {
            c.rayDebt -= 1;
            double a = c.sl.random.nextDouble() * Math.PI * 2, r = Math.sqrt(c.sl.random.nextDouble()) * area;
            Vec3 p = ground(c.sl, c.caster, c.hit.add(Math.cos(a) * r, 8, Math.sin(a) * r));
            ray(c, p, t);
        }
        if ((t - RAYS_FROM) % ServerConfig.GATE_AIM_INTERVAL.get() == 0)
            for (LivingEntity e : HigherSpell.around(c.sl, c.hit, area + 0.5, e -> hdist(e, c.hit) <= area && !friendly(c.caster, e)))
                ray(c, e.position(), t);
    }

    /** One ray: the look for everyone near, the damage in its radius. */
    private static void ray(Cast c, Vec3 p, int t) {
        String id = FxLib.fx(FX_RAY) != null ? FX_RAY : FX_RAY + "_placeholder";
        Fx.play(c.sl, Fx.fx(id).at(p).yaw(c.yaw).point("p", p).point("gate", c.hit.add(0, GATE_H, 0)));
        double r = ServerConfig.GATE_RAY_RADIUS.get();
        float dmg = (float) (ServerConfig.GATE_RAY_DAMAGE.get() * ServerConfig.GATE_SET_BONUS.get() * power(c));
        int cd = ServerConfig.GATE_HIT_COOLDOWN.get();
        for (LivingEntity e : HigherSpell.around(c.sl, p, r + 1.5, e -> !friendly(c.caster, e))) {
            if (e.getBoundingBox().inflate(r).contains(p.add(0, Math.min(1, e.getBbHeight() / 2), 0)) || e.position().distanceToSqr(p) <= r * r) {
                Integer last = c.lastHit.get(e.getUUID());
                if (last != null && t - last < cd) continue;
                c.lastHit.put(e.getUUID(), t);
                hurt(c, e, dmg);
            }
        }
    }

    private static void mainBeam(Cast c) {
        LivingEntity a = c.aim;
        boolean onAim = a != null && a.isAlive() && a.level() == c.sl && hdist(a, c.hit) <= ServerConfig.GATE_AREA.get() + 8;
        Vec3 p = onAim ? a.position() : c.hit;
        String id = FxLib.fx(FX_MAIN) != null ? FX_MAIN : FX_MAIN + "_placeholder";
        Fx.play(c.sl, Fx.fx(id).at(p).yaw(c.yaw).point("p", p).point("gate", c.hit.add(0, GATE_H, 0)));
        Cutscene.flash(c.sl, c.watchers, 16, 0xE8FFFF);
        double r = ServerConfig.GATE_MAIN_RADIUS.get();
        double mult = ServerConfig.GATE_SET_BONUS.get() * power(c);
        for (LivingEntity e : HigherSpell.around(c.sl, p, r + 2, e -> !friendly(c.caster, e))) {
            if (e != a && e.position().distanceToSqr(p) > r * r && !e.getBoundingBox().inflate(r).contains(p)) continue;
            float dmg = (float) ((e.getMaxHealth() * ServerConfig.GATE_MAIN_PERCENT.get() + ServerConfig.GATE_MAIN_FLAT.get()) * mult);
            hurt(c, e, dmg);
        }
    }

    private static void crystal(Cast c) {
        String id = FxLib.fx(FX_CRYSTAL) != null ? FX_CRYSTAL : FX_CRYSTAL + "_placeholder";
        Fx.play(c.sl, Fx.fx(id).at(c.hit).yaw(c.yaw).point("p", c.hit).duration(CRYSTAL_LIFE));
    }

    /** The registered spell (Iron's damage source and power multiplier). */
    private static SilentGateSpell spell() {
        return Reg.SILENT_GATE.get() instanceof SilentGateSpell g ? g : null;
    }

    /** Silent spell power of the caster (Iron's: school power x general power). */
    private static double power(Cast c) {
        SilentGateSpell g = spell();
        return g == null ? 1 : g.mult(c.caster);
    }

    private static void hurt(Cast c, LivingEntity e, float dmg) {
        SilentGateSpell g = spell();
        if (g == null || !e.isAlive() || dmg <= 0) return;
        hitting = true;
        try {
            g.hit(c.caster, e, dmg);
        } finally {
            hitting = false;
        }
    }

    /** Never hit: the caster, its team, its pets, armor stands, spectators, and NPCs of a CNPC faction friendly to the caster. */
    public static boolean friendly(LivingEntity caster, Entity e) {
        if (HigherSpell.friendly(caster, e)) return true;
        if (e instanceof Player p && (p.isCreative() || p.isSpectator())) return true;
        return CnpcHooks.friendlyTo(e, caster) || CnpcHooks.friendlyTo(caster, e);
    }

    public static final class SilentGateEvents {
        private SilentGateEvents() {}

        @SubscribeEvent
        public static void onServerTick(TickEvent.ServerTickEvent e) {
            if (e.phase != TickEvent.Phase.END || RUNNING.isEmpty()) return;
            for (Cast c : new ArrayList<>(RUNNING)) tick(c);
        }

        @SubscribeEvent
        public static void onStopping(ServerStoppingEvent e) {
            CASTS.clear();
            RUNNING.clear();
        }
    }
}
