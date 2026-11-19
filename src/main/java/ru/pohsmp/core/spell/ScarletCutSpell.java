package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import java.util.List;
import java.util.Optional;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.ClipContext;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.HitResult;
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.ServerConfig;
import ru.pohsmp.core.fx.Fx;
import ru.pohsmp.core.fx.FxMath;

/**
 * Scarlet Cut (T02): instant. A series of [scarlet_cut] cutsMin..cutsMax cuts, one every `interval` ticks, each along the caster's
 * view at that moment: everyone `near`..`far` blocks ahead and within `width`/2 of the view line takes `damage` (higher magic).
 * Under every cut a crack opens on the ground; after `crackDelay` ticks it bursts with shards: `shardDamage` within
 * `shardRadius` of the crack line, pushed up by `knockUp`. Look: fx/scarlet_cut.json, one instance per cut.
 */
public class ScarletCutSpell extends HigherSpell {
    public static final String PATH = "scarlet_cut";
    public static final String FX = "scarlet_cut";

    public ScarletCutSpell() {
        super(PATH, 0);
    }

    @Override public CastType getCastType() { return CastType.INSTANT; }
    @Override public Optional<SoundEvent> getCastStartSound() { return Optional.empty(); }
    @Override public Optional<SoundEvent> getCastFinishSound() { return Optional.empty(); }

    @Override
    public List<MutableComponent> getUniqueInfo(int spellLevel, LivingEntity caster) {
        return List.of(ui("cuts", ServerConfig.SCARLET_CUTS_MIN.get(), ServerConfig.SCARLET_CUTS_MAX.get(), num(ServerConfig.SCARLET_DAMAGE.get())),
                ui("burst", num(ServerConfig.SCARLET_SHARD_DAMAGE.get())));
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity entity, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) start(sl, entity);
        super.onCast(level, spellLevel, entity, source, md);
    }

    /** Starts a series of cuts; also for scripts and NPC casters. */
    public static void start(ServerLevel sl, LivingEntity caster) {
        int lo = ServerConfig.SCARLET_CUTS_MIN.get(), hi = Math.max(lo, ServerConfig.SCARLET_CUTS_MAX.get());
        int cuts = lo + sl.random.nextInt(hi - lo + 1);
        int interval = ServerConfig.SCARLET_INTERVAL.get();
        cut(sl, caster, 0);
        if (cuts <= 1) return;
        Tasks.add(new Tasks.Task() {
            int age, done = 1;

            @Override
            public boolean tick() {
                if (!caster.isAlive() || caster.isRemoved() || caster.level() != sl) return false;
                if (++age % interval != 0) return true;
                cut(sl, caster, done++);
                return done < cuts;
            }
        });
    }

    private static void cut(ServerLevel sl, LivingEntity caster, int i) {
        double near = ServerConfig.SCARLET_NEAR.get(), far = Math.max(near + 0.5, ServerConfig.SCARLET_FAR.get());
        double half = ServerConfig.SCARLET_WIDTH.get() / 2;
        Vec3 eyes = caster.getEyePosition(), look = caster.getLookAngle();
        float yaw = caster.getYRot();
        Vec3 mid = eyes.add(look.scale((near + far) / 2)).add(0, -0.25, 0);

        float dmg = dmg(ServerConfig.SCARLET_DAMAGE.get());
        for (LivingEntity e : around(sl, mid, far + half + 2, e -> !friendly(caster, e))) {
            Vec3 rel = e.getBoundingBox().getCenter().subtract(eyes);
            double along = rel.dot(look), r = e.getBbWidth() / 2;
            if (along < near - r - 0.5 || along > far + r) continue;
            if (rel.subtract(look.scale(along)).length() > half + r) continue;
            hurt(sl, caster, e, dmg);
        }

        // crack on the ground under the middle of the cut, across the view
        BlockHitResult hit = sl.clip(new ClipContext(mid, mid.add(0, -8, 0), ClipContext.Block.COLLIDER, ClipContext.Fluid.NONE, caster));
        Vec3 ground = hit.getType() == HitResult.Type.MISS ? mid.add(0, -1.4, 0) : hit.getLocation().add(0, 0.02, 0);
        long seed = (sl.random.nextLong() & ~7L) | 4L | (i & 1) | ((i & 1) << 1);     // bits 0-1: tilt and sweep alternate
        Fx.play(sl, Fx.fx(FX).at(mid).yaw(yaw).point("ground", ground).seed(seed));
        sl.playSound(null, mid.x, mid.y, mid.z, SoundEvents.PLAYER_ATTACK_SWEEP, SoundSource.PLAYERS, 1.2f, 0.6f + 0.1f * (i % 3));
        sl.playSound(null, mid.x, mid.y, mid.z, SoundEvents.AMETHYST_BLOCK_BREAK, SoundSource.PLAYERS, 0.9f, 1.5f);

        int delay = ServerConfig.SCARLET_CRACK_DELAY.get();
        Tasks.add(new Tasks.Task() {
            int age;

            @Override
            public boolean tick() {
                if (++age < delay) return true;
                burst(sl, caster, ground, yaw);
                return false;
            }
        });
    }

    private static void burst(ServerLevel sl, LivingEntity caster, Vec3 ground, float yaw) {
        double half = ServerConfig.SCARLET_WIDTH.get() / 2, R = ServerConfig.SCARLET_SHARD_RADIUS.get();
        FxMath.Vec rv = FxMath.right(yaw);
        Vec3 right = new Vec3(rv.x(), 0, rv.z()).normalize();
        Vec3 a = ground.subtract(right.scale(half)), b = ground.add(right.scale(half));
        float dmg = dmg(ServerConfig.SCARLET_SHARD_DAMAGE.get());
        double up = ServerConfig.SCARLET_KNOCK_UP.get();
        for (LivingEntity e : around(sl, ground, half + R + 1, e -> !friendly(caster, e))) {
            if (e.getY() > ground.y + 2 || e.getY() + e.getBbHeight() < ground.y - 1) continue;
            Vec3 p = new Vec3(e.getX(), ground.y, e.getZ());
            if (toSegment(p, a, b) > R + e.getBbWidth() / 2) continue;
            hurt(sl, caster, e, dmg);
            if (up > 0) {
                Vec3 v = e.getDeltaMovement();
                push(e, new Vec3(v.x, Math.max(v.y, 0) + up, v.z));
            }
        }
        sl.playSound(null, ground.x, ground.y, ground.z, SoundEvents.GLASS_BREAK, SoundSource.PLAYERS, 1.3f, 0.7f);
        sl.playSound(null, ground.x, ground.y, ground.z, SoundEvents.GENERIC_EXPLODE, SoundSource.PLAYERS, 0.5f, 1.6f);
    }

    private static double toSegment(Vec3 p, Vec3 a, Vec3 b) {
        Vec3 ab = b.subtract(a);
        double t = Math.max(0, Math.min(1, p.subtract(a).dot(ab) / Math.max(1e-6, ab.lengthSqr())));
        return p.distanceTo(a.add(ab.scale(t)));
    }
}
