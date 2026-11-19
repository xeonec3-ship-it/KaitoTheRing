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
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.monster.Enemy;
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
import ru.pohsmp.core.fx.FxMath;
import ru.pohsmp.core.spell.CastAnims;
import ru.pohsmp.core.spell.CnpcHooks;
import io.redspace.ironsspellbooks.api.util.AnimationHolder;
import ru.pohsmp.core.spell.Cutscene;
import ru.pohsmp.core.spell.HigherSpell;

/**
 * "Gate" (T03): Silent school, Unknown tier, only from the Silent Witch's staff and only in her full outfit (T18/T19, see {@link SilentWitch}).
 * A 50 s cast that nothing interrupts, all of it to the music track: every player within 128 blocks of the caster or of the strike point
 * hears it (not positional, client: SilentMusic) with every other game sound muted, and watches the camera scene (Cutscene 7).
 * No cast point: the gate stands in the sky 26 blocks ahead, 48 up; the area (radius 40) is under it. From 50 s (the spell is cast)
 * to 63 s aimed beam volleys hit every foe in the area (no main beam - owner's decision). The scene ends at 65 s. Cancel = the track fades in 1 s.
 * Damage: Silent magic (through armor, Silent power, Silent resistance), numbers in [silent_gate]. Afterwards "Silence": the spell's own
 * cooldown, 3 min. Only hostile entities are hit (see {@link #target}); players never.
 */
public class SilentGateSpell extends SilentStaffSpell {
    public static final String PATH = "silent_gate";
    /** Ticks: cast (= 50 s in the track), first rays, last rays, crystal, end of the scene, crystal life. */
    public static final int CAST = 1000, RAYS_FROM = 1000, RAYS_TO = 1260, END = 1300;   // no ice mountain any more (owner 19.11)
    /** Ticks from an aimed beam's launch to its strike (fx/silent_gate_beam.json hits on the 6th tick). */
    private static final int HIT_DELAY = 6;
    /**
     * No cast point (owner): the gate stands in the sky FWD blocks ahead of the caster (by the view at the cast start), GATE_H over the area;
     * the area of the rays is under it. Same numbers as tools/gen_silent_gate_fx.py (FWD, GATE_UP); the camera uses them too.
     * GATE_H: "much higher" (owner 19.11, was 16).
     */
    public static final double FWD = 26, GATE_H = 48;
    /** Sky seals of the field the aimed beams start from (as in fx/silent_gate.json): height over the area and radius. */
    private static final double SKY_LO = 17, SKY_HI = 32, SKY_R = 44;   // ×2 with the area (owner 19.11): the field covers the whole area
    /** Effects of the ideas chat (T03): the whole scene and one aimed beam; placeholders while they are missing. */
    private static final String FX_SCENE = "silent_gate", FX_BEAM = "silent_gate_beam";

    private static final class Cast {
        LivingEntity caster;
        ServerLevel sl;
        Vec3 at, hit;
        float yaw;
        int age, cutKey, scene = -1;
        boolean cast, done;
        List<UUID> watchers = new ArrayList<>();
        final Map<UUID, Integer> lastHit = new HashMap<>();
        boolean placeholder;
    }

    private static final Map<UUID, Cast> CASTS = new HashMap<>();
    /** Running scenes (cast or strike phase), for the tick loop. */
    private static final List<Cast> RUNNING = new ArrayList<>();

    public SilentGateSpell() {
        super(PATH, 180, CAST, 0);
    }

    @Override protected boolean ready() { return true; }
    @Override public CastType getCastType() { return CastType.LONG; }
    @Override public boolean canBeInterrupted(Player player) { return false; }
    /** No spell sounds: only the music (T03). */
    @Override public Optional<SoundEvent> getCastStartSound() { return Optional.empty(); }
    @Override public Optional<SoundEvent> getCastFinishSound() { return Optional.empty(); }
    /** The witch's gestures (tools/gen_player_anims.py): point, look up, "shh" taking the staff, finger up; the finish holds the arm out. */
    private static final AnimationHolder ANIM_CAST = CastAnims.of("silent_gate_cast"), ANIM_FINISH = CastAnims.of("silent_gate_finish");
    /** Length of the finish animation (the strike, 50-64 s). */
    private static final int FINISH_TICKS = 280;
    @Override public AnimationHolder getCastStartAnimation() { return ANIM_CAST; }
    @Override public AnimationHolder getCastFinishAnimation() { return ANIM_FINISH; }

    /** The staff is not in the hands for the scene: it floats before the witch, then she holds it in the left hand (client: GateStaff). */
    @Override
    public void onClientPreCast(Level level, int spellLevel, LivingEntity entity, net.minecraft.world.InteractionHand hand, @javax.annotation.Nullable MagicData md) {
        super.onClientPreCast(level, spellLevel, entity, hand, md);
        CastAnims.hideHands(level, entity, CAST, FINISH_TICKS, true);
    }

    /** The cast is bound to the music: nothing shortens it (cast time reduction, the robe's Silent Reading). */
    @Override public int getEffectiveCastTime(int spellLevel, LivingEntity entity) { return CAST; }
    /** "Silence": Gate's own cooldown. */
    @Override public int getSpellCooldown() { return ServerConfig.GATE_SILENCE_SECONDS.get() * 20; }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("cast", CAST / 20),
                ui("rays", n(ServerConfig.GATE_RAY_DAMAGE.get() * ServerConfig.GATE_SET_BONUS.get()), n(ServerConfig.GATE_AREA.get())),
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
        FxMath.Vec f = FxMath.forward(c.yaw);
        c.hit = c.at.add(f.x() * FWD, 0, f.z() * FWD);   // the centre of the area, as "caster+0,0,FWD" in the effect
        c.cutKey = HigherSpell.key();
        Vec3 d = c.hit.subtract(c.at);
        float ang = (float) Math.atan2(-d.z, -d.x);
        // camera + music + silence for everyone within 128 of the caster or of the strike point
        c.watchers = Cutscene.start(sl, caster, c.cutKey, Cutscene.SILENT_GATE, END, c.hit, ang, Cutscene.R_GATE, sl, c.hit);
        c.placeholder = FxLib.fx(FX_SCENE) == null;
        // anchored at the caster's feet with the start yaw, not to the caster entity: its head turns would swing the whole sky.
        // The ideas chat's effect runs its own length (the crystal stays 30 s after the scene); the placeholder ends with the scene.
        Fx.Spec spec = Fx.fx(c.placeholder ? FX_SCENE + "_placeholder" : FX_SCENE).at(c.at).yaw(c.yaw).target(c.hit).point("c", c.at)
                .point("hit", c.hit).point("gate", c.hit.add(0, GATE_H, 0));
        c.scene = Fx.play(sl, c.placeholder ? spec.duration(END) : spec);
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
        ru.pohsmp.core.PohCore.LOG.info("[gate] {} cancelled at {} s", c.caster.getName().getString(), c.age / 20);
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
        if (t >= END) {
            c.done = true;
            RUNNING.remove(c);
            Cutscene.end(c.sl, c.caster, c.watchers, c.cutKey);
        }
    }

    /**
     * Aimed volleys (as in the mod video): every aimedInterval ticks each foe in the area gets 3-5 beams from different seals of the sky
     * field; the hit (rayRadius around the foe) counts once per volley and at most once per hitCooldownTicks per creature. The random rain
     * of the effect (beam_rain) is only a look.
     */
    private static void rays(Cast c, int t) {
        if ((t - RAYS_FROM) % ServerConfig.GATE_AIM_INTERVAL.get() != 0) return;
        double area = ServerConfig.GATE_AREA.get();
        int lo = ServerConfig.GATE_BEAMS_MIN.get(), hi = Math.max(lo, ServerConfig.GATE_BEAMS_MAX.get());
        for (LivingEntity e : HigherSpell.around(c.sl, c.hit, area + 0.5, e -> hdist(e, c.hit) <= area && target(c.caster, e))) {
            int n = lo + c.sl.random.nextInt(hi - lo + 1);
            for (int i = 0; i < n; i++) beam(c, e);
            // the beam (fx/silent_gate_beam.json) locks on for 4 ticks and strikes on the 6th: the damage comes then, where the foe is then
            ru.pohsmp.core.spell.Tasks.add(new ru.pohsmp.core.spell.Tasks.Task() {
                int left = HIT_DELAY;

                @Override
                public boolean tick() {
                    if (--left > 0) return true;
                    if (!c.done && e.isAlive()) strike(c, e.position(), c.age);
                    return false;
                }
            });
        }
    }

    /** One beam from a random seal of the sky field into the foe (look only). */
    private static void beam(Cast c, LivingEntity e) {
        double a = c.sl.random.nextDouble() * Math.PI * 2, r = Math.sqrt(c.sl.random.nextDouble()) * SKY_R;
        Vec3 from = c.hit.add(Math.cos(a) * r, SKY_LO + c.sl.random.nextDouble() * (SKY_HI - SKY_LO), Math.sin(a) * r);
        if (c.placeholder) {
            Fx.play(c.sl, Fx.fx(FX_BEAM + "_placeholder").at(e.position()).yaw(c.yaw).point("p", e.position()).point("from", from));
            return;
        }
        Fx.play(c.sl, Fx.fx(FX_BEAM).at(from).yaw(c.yaw).point("from", from).target(e));
    }

    /** The damage of a volley: every foe within rayRadius of the point, not more often than hitCooldownTicks. */
    private static void strike(Cast c, Vec3 p, int t) {
        double r = ServerConfig.GATE_RAY_RADIUS.get();
        float dmg = (float) (ServerConfig.GATE_RAY_DAMAGE.get() * ServerConfig.GATE_SET_BONUS.get() * power(c));
        int cd = ServerConfig.GATE_HIT_COOLDOWN.get();
        for (LivingEntity e : HigherSpell.around(c.sl, p, r + 1.5, e -> target(c.caster, e))) {
            if (!e.getBoundingBox().inflate(r).contains(p.add(0, Math.min(1, e.getBbHeight() / 2), 0)) && e.position().distanceToSqr(p) > r * r) continue;
            Integer last = c.lastHit.get(e.getUUID());
            if (last != null && t - last < cd) continue;
            c.lastHit.put(e.getUUID(), t);
            hurt(c, e, dmg);
        }
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
        g.hit(c.caster, e, dmg);
    }

    /**
     * Owner's decision (19.11): only hostile creatures, the rule of all Silent Witch magic ({@link SilentSpell#enemy}): monsters,
     * mobs hunting the caster or its allies, hostile CNPC factions, and a player only for a minute after hitting the caster.
     * Peaceful animals, villagers, pets, the caster's team - never.
     */
    public static boolean target(LivingEntity caster, LivingEntity e) {
        return SilentSpell.enemy(caster, e);
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
