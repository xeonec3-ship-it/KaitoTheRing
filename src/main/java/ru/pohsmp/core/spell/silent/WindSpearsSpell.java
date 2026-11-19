package ru.pohsmp.core.spell.silent;

import ru.pohsmp.core.spell.Tasks;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.util.AnimationHolder;
import java.util.ArrayList;
import java.util.List;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.ServerConfig;
import ru.pohsmp.core.fx.Fx;

/**
 * "Wind Spears": up to 5 targets in a 60° cone up to 32 blocks, nearest to the aim. Over the caster's shoulders a clear spear
 * of wind (turquoise outline) appears for each, hangs for 0.5 s, then all fly at once (3 blocks a tick) and strike the head:
 * 14 damage each, knockback 0.6. Spears follow the head, stop on a Barrier dome. Look: fx/silent_wind_spears.json (one instance per spear, moved and turned along
 * its flight) and silent_wind_spears_hit.json on the hit;
 * gesture: a snap of the right hand's fingers (pohsmp_finger_snap, pose library T12).
 */
public class WindSpearsSpell extends SilentSpell {
    public static final String PATH = "wind_spears";
    private static final int MAX_FLIGHT = 40;

    public WindSpearsSpell() {
        super(PATH, 20, 40, 6, ServerConfig.SPEARS_CAST, ServerConfig.SPEARS_MANA, ServerConfig.SPEARS_COOLDOWN);
    }

    @Override public CastType getCastType() { return CastType.LONG; }
    /** A snap of the right hand's fingers (T12); no finish: the snap plays to its end (1.1 s, the cast is 1 s). */
    private static final AnimationHolder ANIM_SNAP = ru.pohsmp.core.spell.CastAnims.of("finger_snap");
    @Override public AnimationHolder getCastStartAnimation() { return ANIM_SNAP; }
    @Override public AnimationHolder getCastFinishAnimation() { return AnimationHolder.pass(); }

    private static int targets() { return cfg(ServerConfig.SPEARS_TARGETS::get, 5); }
    private static double range() { return cfg(ServerConfig.SPEARS_RANGE::get, 32.0); }
    private static double coneDeg() { return cfg(ServerConfig.SPEARS_CONE::get, 60.0); }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("damage", n(dmg(caster, cfg(ServerConfig.SPEARS_DAMAGE::get, 14.0)))),
                ui("targets", targets(), n(coneDeg()), n(range())));
    }

    private static List<LivingEntity> pick(ServerLevel sl, LivingEntity caster) {
        List<LivingEntity> all = cone(sl, caster, caster.getEyePosition(), caster.getLookAngle(), range(), coneDeg(), true);
        return all.size() > targets() ? new ArrayList<>(all.subList(0, targets())) : all;
    }

    @Override
    public boolean checkPreCastConditions(Level level, int spellLevel, LivingEntity entity, MagicData md) {
        if (!super.checkPreCastConditions(level, spellLevel, entity, md)) return false;
        if (level instanceof ServerLevel sl && pick(sl, entity).isEmpty()) {
            if (entity instanceof Player p) p.displayClientMessage(Component.translatable("ui.pohsmp_core.wind_spears.no_target").withStyle(s -> s.withColor(COLOR)), true);
            return false;
        }
        return true;
    }

    /** One spear. */
    private static final class Spear {
        final LivingEntity target;
        final double side;   // shoulder slot: -1..1, left to right
        Vec3 pos, prev;
        boolean done;
        int fxInst = -1;

        Spear(LivingEntity target, double side) {
            this.target = target;
            this.side = side;
        }
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) launch(sl, caster);
        super.onCast(level, spellLevel, caster, source, md);
    }

    private void launch(ServerLevel sl, LivingEntity caster) {
        List<LivingEntity> ts = pick(sl, caster);
        if (ts.isEmpty()) return;
        int hover = cfg(ServerConfig.SPEARS_HOVER::get, 10);
        double speed = cfg(ServerConfig.SPEARS_SPEED::get, 3.0);
        float damage = (float) dmg(caster, cfg(ServerConfig.SPEARS_DAMAGE::get, 14.0));
        double kb = cfg(ServerConfig.SPEARS_KNOCKBACK::get, 0.6);
        List<Spear> spears = new ArrayList<>();
        for (int i = 0; i < ts.size(); i++) {
            double side = ts.size() == 1 ? 0.6 : -1 + 2.0 * i / (ts.size() - 1);
            Spear s = new Spear(ts.get(i), side);
            s.pos = s.prev = slot(caster, side);
            // its own instance, not tied to the caster: the server moves and turns it (Fx.move) along the flight
            Vec3 aim0 = head(s.target).subtract(s.pos);
            s.fxInst = fx(sl, "silent_wind_spears", Fx.fx("silent_wind_spears").at(s.pos).yaw(yawOf(aim0)).pitch(pitchOf(aim0))
                    .target(s.target).point("start", s.pos).seed(i + 1L));
            spears.add(s);
        }
        Tasks.add(new Tasks.Task() {
            int age;

            @Override
            public boolean tick() {
                age++;
                boolean any = false;
                for (Spear s : spears) {
                    if (s.done) continue;
                    any = true;
                    if (age <= hover) {   // hanging over the shoulders, pointing at the target
                        s.prev = s.pos;
                        s.pos = slot(caster, s.side);
                        Vec3 dir = s.target.isAlive() ? head(s.target).subtract(s.pos).normalize() : caster.getLookAngle();
                        drawSpear(sl, s, s.pos, dir, s.fxInst < 0);
                        if (s.fxInst >= 0) Fx.move(sl, s.fxInst, s.pos, yawOf(dir), pitchOf(dir));
                        if (age == hover) sl.playSound(null, s.pos.x, s.pos.y, s.pos.z, SoundEvents.PLAYER_ATTACK_SWEEP, SoundSource.PLAYERS, 0.35f, 1.8f);
                        continue;
                    }
                    if (!s.target.isAlive() || s.target.isRemoved() || s.target.level() != sl || age > hover + MAX_FLIGHT) {
                        vanish(sl, s);
                        continue;
                    }
                    Vec3 aim = head(s.target);
                    Vec3 to = aim.subtract(s.pos);
                    double d = to.length();
                    Vec3 next = d <= speed ? aim : s.pos.add(to.scale(speed / d));
                    SageBarrierSpell.Dome dome = SageBarrierSpell.crossed(sl, s.pos, next, caster);
                    if (dome != null && !dome.protects(caster)) {
                        Vec3 at = SageBarrierSpell.hitSphere(s.pos, next, dome.center(), dome.radius);
                        SageBarrierSpell.ripple(dome, at != null ? at : next);
                        vanish(sl, s);
                        continue;
                    }
                    s.prev = s.pos;
                    s.pos = next;
                    if (s.fxInst < 0) {
                        line(sl, TURQUOISE_SMALL, s.prev, s.pos, 0.5);   // the cut left in the air
                        drawSpear(sl, s, s.pos, to.normalize(), true);
                    } else {
                        Fx.move(sl, s.fxInst, s.pos, yawOf(to), pitchOf(to));
                    }
                    if (d <= speed) strike(sl, caster, s, damage, kb, to.normalize());
                }
                return any;
            }
        });
    }

    /** Over the shoulders: a fan from left to right, a little behind the head. */
    private static Vec3 slot(LivingEntity caster, double side) {
        return local(caster, side * 0.9, caster.getBbHeight() + 0.35 + 0.25 * (1 - Math.abs(side)), -0.35);
    }

    /** Stand-in spear: a long thin rhombus of turquoise points with a small swirl of wind around it. */
    private static void drawSpear(ServerLevel sl, Spear s, Vec3 at, Vec3 dir, boolean particles) {
        if (!particles) return;
        Vec3 tip = at.add(dir.scale(0.9)), tail = at.subtract(dir.scale(0.9));
        line(sl, TURQUOISE_SMALL, tail, tip, 0.18);
        particles(sl, WHITE_SMALL, tip, 1, 0, 0);
        if (sl.random.nextInt(3) == 0) particles(sl, ParticleTypes.CLOUD, tail, 1, 0.05, 0.0);
    }

    private void strike(ServerLevel sl, LivingEntity caster, Spear s, float damage, double kb, Vec3 dir) {
        s.done = true;
        LivingEntity t = s.target;
        if (hit(caster, t, damage) && kb > 0) t.knockback(kb, -dir.x, -dir.z);
        Vec3 h = head(t);
        if (s.fxInst >= 0) Fx.stop(sl, s.fxInst, "");
        if (!hitFx(sl, h, 1.0)) for (int i = 0; i < 14; i++) {   // stand-in ring of wind on the hit
            double a = i * Math.PI * 2 / 14;
            Vec3 u = Math.abs(dir.y) > 0.9 ? new Vec3(1, 0, 0) : new Vec3(0, 1, 0);
            Vec3 p = dir.cross(u).normalize(), q = dir.cross(p).normalize();
            particles(sl, TURQUOISE_SMALL, h.add(p.scale(Math.cos(a) * 0.6)).add(q.scale(Math.sin(a) * 0.6)), 1, 0, 0);
        }
        particles(sl, ParticleTypes.CLOUD, h, 4, 0.15, 0.04);
        sl.playSound(null, h.x, h.y, h.z, SoundEvents.AMETHYST_BLOCK_BREAK, SoundSource.PLAYERS, 0.6f, 1.7f);
    }

    private static void vanish(ServerLevel sl, Spear s) {
        s.done = true;
        if (s.fxInst >= 0) {
            Fx.stop(sl, s.fxInst, "");
            hitFx(sl, s.pos, 0.5);
        } else particles(sl, ParticleTypes.CLOUD, s.pos, 3, 0.1, 0.02);
    }
}
