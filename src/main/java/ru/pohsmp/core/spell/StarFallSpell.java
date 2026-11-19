package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.spells.SpellAnimations;
import io.redspace.ironsspellbooks.api.util.AnimationHolder;
import io.redspace.ironsspellbooks.api.util.CameraShakeData;
import io.redspace.ironsspellbooks.api.util.CameraShakeManager;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.DivineEvents;
import ru.pohsmp.core.ServerConfig;
import ru.pohsmp.core.fx.Fx;

/**
 * Higher school and tier (T05, owner's decision). "Star Fall": an 8 s cast at the point the caster looks at (up to 48 blocks).
 * Everyone within 64 blocks watches a cutscene (client: DownfallCut scene 6): close-up, the camera climbs into the sky,
 * the falling star with its trail, then a side view of the impact. Impact: damage in radius 8 (full in the centre,
 * [star_fall] edgeShare at the edge; higher_magic, times [higher] damageMult), knockback, a crater decal and glowing "glass" for 30 s. No blocks change.
 *
 * Timeline (ticks from the cast start), shared with fx/star_fall.json and the camera: the star appears at FALL_AT
 * high over the target ({@link #sky}), falls along an ease-in-cubic path and lands at CAST; the camera stays 40 ticks more.
 * The impact runs on its own timer, so a shorter Iron's cast time does not break the sync.
 */
public class StarFallSpell extends HigherSpell {
    public static final String PATH = "star_fall";
    public static final int CAST = 160, FALL_AT = 100, AFTER = 40, CRATER = 600;
    public static final double RANGE = 48, R = 8;
    /** The star comes from behind the target (as seen by the caster): this far back and this high. Same numbers in DownfallCut. */
    public static final double SKY_BACK = 45, SKY_UP = 90;
    /** fx/star_fall.json (ideas chat, tools/gen_higher_fx.py). */
    public static final String FX = "star_fall";
    private static final int COLOR = 0xFF2A3A;

    private static final class Cast {
        Vec3 at, impact, dir;
        int age, fx = -1, cutKey;
        boolean cancelled;
        List<UUID> watchers = new ArrayList<>();
    }

    private static final Map<UUID, Cast> CASTS = new HashMap<>();

    public StarFallSpell() {
        super(PATH, CAST);
    }

    @Override public CastType getCastType() { return CastType.LONG; }
    @Override public boolean canBeInterrupted(Player player) { return false; }
    @Override public boolean allowLooting() { return false; }
    @Override public Optional<SoundEvent> getCastStartSound() { return Optional.of(SoundEvents.BEACON_ACTIVATE); }
    @Override public Optional<SoundEvent> getCastFinishSound() { return Optional.empty(); }
    // Temporary: the ideas chat makes the own animation (arms to the sky, then a sharp swing down), see T05.
    @Override public AnimationHolder getCastStartAnimation() { return SpellAnimations.ANIMATION_LONG_CAST; }
    @Override public AnimationHolder getCastFinishAnimation() { return SpellAnimations.ANIMATION_LONG_CAST_FINISH; }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("cast", CAST / 20, (int) RANGE), ui("damage", num(ServerConfig.STAR_FALL_DAMAGE.get()), (int) R), ui("crater", CRATER / 20));
    }

    /** Where the star starts: SKY_BACK behind the impact along dir (caster -> impact) and SKY_UP above it. */
    public static Vec3 sky(Vec3 impact, Vec3 dir) {
        return impact.add(dir.scale(SKY_BACK)).add(0, SKY_UP, 0);
    }

    @Override
    public void onServerPreCast(Level level, int spellLevel, LivingEntity caster, MagicData md) {
        super.onServerPreCast(level, spellLevel, caster, md);
        if (level instanceof ServerLevel sl) begin(sl, caster);
    }

    private static void begin(ServerLevel sl, LivingEntity caster) {
        Cast old = CASTS.remove(caster.getUUID());
        if (old != null) abort(sl, caster, old);
        Cast c = new Cast();
        c.at = caster.position();
        Vec3 look = caster.getLookAngle().multiply(1, 0, 1);
        look = look.lengthSqr() < 1e-4 ? new Vec3(0, 0, 1) : look.normalize();
        Vec3 p = PohSpell.lookPoint(sl, caster, RANGE);
        if (PohSpell.hdist(caster, p) < 8) p = c.at.add(look.scale(10)).add(0, 1, 0);   // too close: the star lands 10 blocks ahead
        c.impact = PohSpell.ground(sl, caster, p);
        Vec3 d = c.impact.subtract(c.at).multiply(1, 0, 1);
        c.dir = d.lengthSqr() < 1e-4 ? look : d.normalize();
        c.cutKey = HigherSpell.key();
        c.watchers = Cutscene.start(sl, caster, c.cutKey, Cutscene.STAR_FALL, CAST + AFTER, c.impact, Math.atan2(c.dir.z, c.dir.x));
        c.fx = Fx.play(sl, Fx.fx(FX).style("higher").caster(caster).at(c.impact).yaw(caster.getYRot())
                .point("impact", c.impact).point("sky", sky(c.impact, c.dir)));
        CASTS.put(caster.getUUID(), c);
        sl.playSound(null, c.at.x, c.at.y, c.at.z, SoundEvents.BEACON_ACTIVATE, SoundSource.PLAYERS, 3f, 0.6f);
        Tasks.add(() -> tick(sl, caster, c));
    }

    /** Runs the whole timeline on the server, independent of the Iron's cast. */
    private static boolean tick(ServerLevel sl, LivingEntity caster, Cast c) {
        if (c.cancelled) return false;
        c.age++;
        Vec3 i = c.impact;
        if (c.age < FALL_AT && c.age % 20 == 0)
            sl.playSound(null, i.x, i.y, i.z, SoundEvents.AMETHYST_BLOCK_CHIME, SoundSource.PLAYERS, 2f, 0.5f + c.age / 200f);
        if (c.age == FALL_AT) {
            Vec3 s = sky(i, c.dir);
            sl.playSound(null, i.x, i.y + 20, i.z, SoundEvents.FIREWORK_ROCKET_LAUNCH, SoundSource.PLAYERS, 6f, 0.4f);
            sl.playSound(null, s.x, s.y, s.z, SoundEvents.BEACON_POWER_SELECT, SoundSource.PLAYERS, 8f, 0.5f);
        }
        if (c.age == CAST - 25) sl.playSound(null, i.x, i.y + 10, i.z, SoundEvents.ELYTRA_FLYING, SoundSource.PLAYERS, 5f, 1.4f);
        if (c.age == CAST) {
            Cutscene.thaw(c.watchers);   // watchers stay in the cutscene camera but can be hit and thrown now
            impact(sl, caster, c);
        }
        if (c.age >= CAST + AFTER) {
            Cutscene.end(sl, caster, c.watchers, c.cutKey);
            if (CASTS.get(caster.getUUID()) == c) CASTS.remove(caster.getUUID());
            return false;
        }
        return true;
    }

    private static void impact(ServerLevel sl, LivingEntity caster, Cast c) {
        Vec3 i = c.impact;
        sl.playSound(null, i.x, i.y, i.z, SoundEvents.GENERIC_EXPLODE, SoundSource.PLAYERS, 8f, 0.5f);
        sl.playSound(null, i.x, i.y, i.z, SoundEvents.LIGHTNING_BOLT_THUNDER, SoundSource.PLAYERS, 6f, 0.6f);
        sl.playSound(null, i.x, i.y, i.z, SoundEvents.AMETHYST_CLUSTER_BREAK, SoundSource.PLAYERS, 4f, 0.5f);
        DivineEvents.particle(sl, ParticleTypes.EXPLOSION_EMITTER, i.x, i.y + 0.5, i.z, 2, 1, 0);
        DivineEvents.particle(sl, ParticleTypes.END_ROD, i.x, i.y + 1, i.z, 120, R * 0.3, 0.4);
        CameraShakeManager.addCameraShake(new CameraShakeData(sl, 40, i, 40));
        Cutscene.flash(sl, c.watchers, 14, COLOR);
        double base = ServerConfig.STAR_FALL_DAMAGE.get(), edge = ServerConfig.STAR_FALL_EDGE.get();
        for (LivingEntity e : HigherSpell.around(sl, i, R + 2, e -> e != caster && !HigherSpell.friendly(caster, e))) {
            double d = Math.sqrt(e.distanceToSqr(i.x, Math.max(i.y, Math.min(e.getY() + e.getBbHeight() / 2, i.y + 1)), i.z));
            d = Math.max(0, d - e.getBbWidth() / 2);
            if (d > R) continue;
            double k = d / R;                                  // 0 centre .. 1 edge
            hurt(sl, caster, e, dmg(base * (1 - (1 - edge) * k)));
            Vec3 away = e.position().subtract(i).multiply(1, 0, 1);
            away = away.lengthSqr() < 1e-4 ? c.dir : away.normalize();
            HigherSpell.push(e, away.scale(0.6 + 1.6 * (1 - k)).add(0, 0.45 + 0.5 * (1 - k), 0));
        }
    }

    @Override
    public void onServerCastComplete(Level level, int spellLevel, LivingEntity caster, MagicData md, boolean cancelled) {
        if (cancelled && level instanceof ServerLevel sl) {
            Cast c = CASTS.get(caster.getUUID());
            // A cancel after the impact (e.g. Iron's cast longer than CAST) changes nothing: the timeline is already done.
            if (c != null && c.age < CAST) {
                CASTS.remove(caster.getUUID());
                abort(sl, caster, c);
            }
        }
        super.onServerCastComplete(level, spellLevel, caster, md, cancelled);
    }

    private static void abort(ServerLevel sl, LivingEntity caster, Cast c) {
        c.cancelled = true;
        if (c.fx >= 0) Fx.stop(sl, c.fx, "fade");
        Cutscene.end(sl, caster, c.watchers, c.cutKey);
    }
}
