package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.spells.SpellAnimations;
import io.redspace.ironsspellbooks.api.util.AnimationHolder;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.ServerConfig;
import ru.pohsmp.core.fx.Fx;

/**
 * "Silent Volley": during a 3 s cast 24 small seals rise around the caster in a fan (200° behind and to the sides, radius 2.5).
 * At the end every seal shoots an arrow of light at its own target: every enemy within 24 blocks, round robin (fewer enemies -
 * several arrows each, at most 6 into one). An arrow deals 6 damage, flies a homing arc and stops on a Barrier dome.
 * Look: fx/silent_volley.json (seals assembled from pieces, thin homing beams, sparks; ideas chat) - stand-in particles until then.
 */
public class SilentVolleySpell extends SilentSpell {
    public static final String PATH = "silent_volley";

    private static final class Cast {
        int age, fxInst = -1;
    }

    private static final Map<UUID, Cast> CASTS = new HashMap<>();

    public SilentVolleySpell() {
        super(PATH, 60, 100, 20, ServerConfig.VOLLEY_CAST, ServerConfig.VOLLEY_MANA, ServerConfig.VOLLEY_COOLDOWN);
    }

    @Override public CastType getCastType() { return CastType.LONG; }
    @Override public AnimationHolder getCastStartAnimation() { return SpellAnimations.CHARGE_RAISED_HAND; }
    @Override public AnimationHolder getCastFinishAnimation() { return SpellAnimations.ANIMATION_INSTANT_CAST; }

    private static int seals() { return cfg(ServerConfig.VOLLEY_SEALS::get, 24); }
    private static double radius() { return cfg(ServerConfig.VOLLEY_RADIUS::get, 24.0); }
    private static int perTarget() { return cfg(ServerConfig.VOLLEY_PER_TARGET::get, 6); }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("arrows", seals(), n(dmg(caster, cfg(ServerConfig.VOLLEY_DAMAGE::get, 6.0)))),
                ui("radius", n(radius()), perTarget()));
    }

    /** Enemies in the radius the caster can see, nearest first. */
    private static List<LivingEntity> enemies(ServerLevel sl, LivingEntity caster) {
        double r = radius();
        Vec3 c = caster.position();
        List<LivingEntity> out = new ArrayList<>();
        for (Entity e : sl.getEntities(caster, new AABB(c, c).inflate(r), e -> enemy(caster, e)))
            if (e.distanceToSqr(caster) <= r * r && caster.hasLineOfSight(e)) out.add((LivingEntity) e);
        out.sort((a, b) -> Double.compare(a.distanceToSqr(caster), b.distanceToSqr(caster)));
        return out;
    }

    @Override
    public boolean checkPreCastConditions(Level level, int spellLevel, LivingEntity entity, MagicData md) {
        if (!super.checkPreCastConditions(level, spellLevel, entity, md)) return false;
        if (level instanceof ServerLevel sl && enemies(sl, entity).isEmpty()) {
            if (entity instanceof Player p) p.displayClientMessage(Component.translatable("ui.pohsmp_core.silent_volley.no_target").withStyle(s -> s.withColor(COLOR)), true);
            return false;
        }
        return true;
    }

    /** Seal i of n: a fan from the left side over the back to the right side, two rows. */
    private static Vec3 seal(LivingEntity caster, int i, int n) {
        double arc = Math.toRadians(cfg(ServerConfig.VOLLEY_ARC::get, 200.0));
        double r = cfg(ServerConfig.VOLLEY_SEAL_RADIUS::get, 2.5);
        double k = n == 1 ? 0.5 : i / (double) (n - 1);
        double a = Math.PI - arc / 2 + arc * k;   // 0 = straight ahead, PI = straight behind
        double up = (i % 2 == 0 ? 1.15 : 2.15) + 0.25 * Math.sin(k * Math.PI);
        return local(caster, Math.sin(a) * r, up, Math.cos(a) * r);
    }

    @Override
    public void onServerPreCast(Level level, int spellLevel, LivingEntity caster, MagicData md) {
        super.onServerPreCast(level, spellLevel, caster, md);
        if (!(level instanceof ServerLevel sl)) return;
        Cast c = new Cast();
        c.fxInst = fx(sl, "silent_volley", Fx.fx("silent_volley").caster(caster).attach(caster).color(COLOR).duration(getCastTime(1) + 40));
        CASTS.put(caster.getUUID(), c);
    }

    @Override
    public void onServerCastTick(Level level, int spellLevel, LivingEntity caster, MagicData md) {
        super.onServerCastTick(level, spellLevel, caster, md);
        Cast c = CASTS.get(caster.getUUID());
        if (c == null || !(level instanceof ServerLevel sl)) return;
        c.age++;
        if (c.fxInst >= 0 || c.age % 3 != 0) return;
        int n = seals(), cast = Math.max(1, getCastTime(spellLevel));
        int shown = Math.min(n, (int) Math.ceil(n * Math.min(1.0, c.age / (cast * 0.8))));
        for (int i = 0; i < shown; i++) drawSeal(sl, caster, seal(caster, i, n), Math.min(1.0, (c.age - i * cast * 0.8 / n) / 10.0));
    }

    /** Stand-in seal: a small ring facing out from the caster, drawn in pieces as it assembles (part 0..1). */
    private static void drawSeal(ServerLevel sl, LivingEntity caster, Vec3 at, double part) {
        Vec3 out = at.subtract(caster.position().add(0, at.y - caster.getY(), 0)).normalize();
        Vec3 a = out.cross(new Vec3(0, 1, 0)).normalize(), b = new Vec3(0, 1, 0);
        int pts = Math.max(2, (int) (8 * part));
        for (int j = 0; j < pts; j++) {
            double t = j * Math.PI * 2 / 8;
            particles(sl, TURQUOISE_SMALL, at.add(a.scale(Math.cos(t) * 0.28)).add(b.scale(Math.sin(t) * 0.28)), 1, 0, 0);
        }
        if (part >= 1) particles(sl, WHITE_SMALL, at, 1, 0, 0);
    }

    @Override
    public void onServerCastComplete(Level level, int spellLevel, LivingEntity caster, MagicData md, boolean cancelled) {
        Cast c = CASTS.remove(caster.getUUID());
        if (cancelled && c != null && level instanceof ServerLevel sl) {
            if (c.fxInst >= 0) Fx.stop(sl, c.fxInst, "");
            else for (int i = 0; i < seals(); i++) particles(sl, ParticleTypes.END_ROD, seal(caster, i, seals()), 1, 0.05, 0.01);
        }
        super.onServerCastComplete(level, spellLevel, caster, md, cancelled);
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) fire(sl, caster);
        super.onCast(level, spellLevel, caster, source, md);
    }

    /** One arrow of light. */
    private static final class Arrow {
        LivingEntity target;
        Vec3 from, bend, pos;
        int delay, flight, t;
        boolean done;
    }

    private void fire(ServerLevel sl, LivingEntity caster) {
        List<LivingEntity> ts = enemies(sl, caster);
        int n = seals();
        if (ts.isEmpty()) {
            for (int i = 0; i < n; i++) particles(sl, ParticleTypes.END_ROD, seal(caster, i, n), 1, 0.05, 0.01);
            return;
        }
        int count = Math.min(n, perTarget() * ts.size());
        float damage = (float) dmg(caster, cfg(ServerConfig.VOLLEY_DAMAGE::get, 6.0));
        List<Arrow> arrows = new ArrayList<>();
        // seals used: spread evenly over the fan when fewer arrows than seals
        for (int j = 0; j < count; j++) {
            Arrow a = new Arrow();
            a.target = ts.get(j % ts.size());
            int si = count == n ? j : (int) Math.round(j * (n - 1) / (double) Math.max(1, count - 1));
            a.from = a.pos = seal(caster, si, n);
            Vec3 out = a.from.subtract(caster.position().add(0, a.from.y - caster.getY(), 0)).normalize();
            a.bend = a.from.add(out.scale(2.5)).add(0, 2.5 + sl.random.nextDouble(), 0);
            double d = a.from.distanceTo(aimPoint(a.target));
            a.flight = (int) Math.max(6, Math.min(22, d / 1.4));
            a.delay = j % 4;
            arrows.add(a);
        }
        sl.playSound(null, caster.getX(), caster.getY() + 1.5, caster.getZ(), SoundEvents.AMETHYST_BLOCK_CHIME, SoundSource.PLAYERS, 0.6f, 1.4f);
        Tasks.add(new Tasks.Task() {
            int age;

            @Override
            public boolean tick() {
                age++;
                boolean any = false;
                for (Arrow a : arrows) {
                    if (a.done) continue;
                    any = true;
                    if (age <= a.delay) continue;
                    if (!a.target.isAlive() || a.target.isRemoved() || a.target.level() != sl) {   // target fell: the arrow goes out
                        a.done = true;
                        particles(sl, ParticleTypes.END_ROD, a.pos, 2, 0.05, 0.01);
                        continue;
                    }
                    a.t++;
                    double k = Math.min(1.0, a.t / (double) a.flight);
                    Vec3 end = aimPoint(a.target);
                    // quadratic arc: from the seal, up and out, down onto the target (end follows it)
                    Vec3 p = a.from.scale((1 - k) * (1 - k)).add(a.bend.scale(2 * k * (1 - k))).add(end.scale(k * k));
                    SageBarrierSpell.Dome dome = SageBarrierSpell.crossed(sl, a.pos, p, caster);
                    if (dome != null && !dome.protects(caster)) {
                        Vec3 at = SageBarrierSpell.hitSphere(a.pos, p, dome.center(), dome.radius);
                        SageBarrierSpell.ripple(dome, at != null ? at : p);
                        a.done = true;
                        continue;
                    }
                    line(sl, a.t % 2 == 0 ? WHITE_SMALL : TURQUOISE_SMALL, a.pos, p, 0.45);
                    a.pos = p;
                    if (k >= 1) {
                        a.done = true;
                        hit(caster, a.target, damage);
                        particles(sl, ParticleTypes.ELECTRIC_SPARK, end, 5, 0.15, 0.08);
                        particles(sl, TURQUOISE, end, 3, 0.2, 0);
                    }
                }
                return any;
            }
        });
    }
}
