package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.events.SpellPreCastEvent;
import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.spells.SpellAnimations;
import io.redspace.ironsspellbooks.api.util.AnimationHolder;
import io.redspace.ironsspellbooks.api.util.Utils;
import io.redspace.ironsspellbooks.damage.SpellDamageSource;
import java.util.ArrayList;
import java.util.List;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.projectile.Projectile;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.EntityHitResult;
import net.minecraft.world.phys.HitResult;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.living.LivingAttackEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.ServerConfig;
import ru.pohsmp.core.fx.Fx;

/**
 * "Barrier" (after the Barrier Mage): a dome of radius 5 around the caster for 8 s, following it. Projectiles from outside
 * (arrows, fireballs, Iron's projectiles) stop and go out on its surface; ray and touch spells at those inside (the caster and
 * its allies) are cancelled. Melee and walking through the dome are free. Projectiles of those inside fly out freely.
 * Hits on the dome make a ripple at the point (stand-in until T08). Look: fx/silent_barrier_dome.json (ideas chat).
 */
public class SageBarrierSpell extends SilentSpell {
    public static final String PATH = "sage_barrier";
    /** How high the dome's center is over the caster's feet: the sphere then covers a standing player with room. */
    private static final double LIFT = 0.0;

    /** One dome. */
    public static final class Dome {
        final LivingEntity owner;
        final ServerLevel level;
        final double radius;
        final int life;
        int age, fxInst = -1;   // fxInst: data effect instance, -1 = stand-in particles

        Dome(LivingEntity owner, ServerLevel level, double radius, int life) {
            this.owner = owner;
            this.level = level;
            this.radius = radius;
            this.life = life;
        }

        public Vec3 center() {
            return owner.position().add(0, LIFT, 0);
        }

        boolean alive() {
            return age <= life && owner.isAlive() && !owner.isRemoved() && owner.level() == level;
        }

        /** The body (its middle) is inside the sphere. */
        public boolean inside(Entity e) {
            return e.level() == level && e.position().add(0, e.getBbHeight() * 0.5, 0).distanceToSqr(center()) <= radius * radius;
        }

        public boolean inside(Vec3 p) {
            return p.distanceToSqr(center()) <= radius * radius;
        }

        /** Inside and on the caster's side: the caster itself or its ally. */
        public boolean protects(Entity e) {
            return (e == owner || SilentSpell.friendly(owner, e)) && inside(e);
        }
    }

    private static final List<Dome> DOMES = new ArrayList<>();

    public SageBarrierSpell() {
        super(PATH, 30, 120, 40, ServerConfig.BARRIER_CAST, ServerConfig.BARRIER_MANA, ServerConfig.BARRIER_COOLDOWN);
    }

    @Override public CastType getCastType() { return CastType.LONG; }
    @Override public AnimationHolder getCastStartAnimation() { return SpellAnimations.CHARGE_RAISED_HAND; }
    @Override public AnimationHolder getCastFinishAnimation() { return SpellAnimations.SELF_CAST_ANIMATION; }

    private static double radius() { return cfg(ServerConfig.BARRIER_RADIUS::get, 5.0); }
    private static int seconds() { return cfg(ServerConfig.BARRIER_SECONDS::get, 8); }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("dome", n(radius()), seconds()), ui("stops"), ui("free"));
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) raise(sl, caster, radius(), seconds() * 20);
        super.onCast(level, spellLevel, caster, source, md);
    }

    /** Raises a dome around the entity (also for scripts and tests). A new dome of the same owner replaces the old one. */
    public static Dome raise(ServerLevel sl, LivingEntity owner, double radius, int ticks) {
        DOMES.removeIf(d -> {
            if (d.owner != owner) return false;
            if (d.fxInst >= 0) Fx.stop(sl, d.fxInst, "");
            return true;
        });
        Dome d = new Dome(owner, sl, radius, ticks);
        d.fxInst = fx(sl, "silent_barrier_dome", Fx.fx("silent_barrier_dome").caster(owner).attach(owner).scale(radius).color(COLOR).duration(ticks));
        DOMES.add(d);
        sl.playSound(null, owner.getX(), owner.getY(), owner.getZ(), SoundEvents.AMETHYST_BLOCK_CHIME, SoundSource.PLAYERS, 0.7f, 1.6f);
        return d;
    }

    /** The dome that shields this entity (it is inside and the owner's side), or null. */
    public static Dome shielding(Entity e) {
        for (Dome d : DOMES) if (d.alive() && d.protects(e)) return d;
        return null;
    }

    /** First dome the segment a-b enters from outside, ignoring the domes this side is inside of (shooter in the dome shoots out). */
    public static Dome crossed(Level level, Vec3 a, Vec3 b, Entity shooter) {
        for (Dome d : DOMES) {
            if (!d.alive() || d.level != level) continue;
            if (shooter != null && d.inside(shooter)) continue;
            if (d.inside(a) || hitSphere(a, b, d.center(), d.radius) != null) return d;
        }
        return null;
    }

    /** Point where the segment a-b enters the sphere, or null. */
    public static Vec3 hitSphere(Vec3 a, Vec3 b, Vec3 c, double r) {
        Vec3 d = b.subtract(a);
        double len2 = d.lengthSqr();
        if (len2 < 1e-9) return null;
        Vec3 f = a.subtract(c);
        double bb = f.dot(d), cc = f.lengthSqr() - r * r;
        double disc = bb * bb - len2 * cc;
        if (disc < 0) return null;
        double t = (-bb - Math.sqrt(disc)) / len2;
        if (t < 0 || t > 1) return null;
        return a.add(d.scale(t));
    }

    /** Ripple where something struck the dome (stand-in for the T08 sigil response). */
    public static void ripple(Dome d, Vec3 at) {
        ServerLevel sl = d.level;
        Vec3 n = at.subtract(d.center()).normalize();
        Vec3 u = Math.abs(n.y) > 0.9 ? new Vec3(1, 0, 0) : new Vec3(0, 1, 0);
        Vec3 a = n.cross(u).normalize(), b = n.cross(a).normalize();
        for (int ring = 1; ring <= 2; ring++) {
            double rr = 0.35 * ring;
            for (int i = 0; i < 12; i++) {
                double t = i * Math.PI / 6;
                particles(sl, ring == 1 ? TURQUOISE : TURQUOISE_SMALL, at.add(a.scale(Math.cos(t) * rr)).add(b.scale(Math.sin(t) * rr)), 1, 0, 0);
            }
        }
        particles(sl, ParticleTypes.END_ROD, at, 4, 0.08, 0.02);
        sl.playSound(null, at.x, at.y, at.z, SoundEvents.AMETHYST_BLOCK_HIT, SoundSource.PLAYERS, 0.8f, 1.4f);
    }

    /** Stand-in look of the dome: a lattice of turquoise points rising from the ground, then a slowly turning shell. */
    private static void draw(Dome d) {
        ServerLevel sl = d.level;
        Vec3 c = d.center();
        double r = d.radius;
        if (d.age <= 12) {   // assembles from the ground up
            double h = r * d.age / 12.0;
            double rr = Math.sqrt(Math.max(0, r * r - h * h));
            for (int i = 0; i < 28; i++) {
                double t = i * Math.PI * 2 / 28;
                particles(sl, TURQUOISE, c.add(Math.cos(t) * rr, h, Math.sin(t) * rr), 1, 0, 0);
            }
            return;
        }
        if (d.age % 3 != 0) return;
        double spin = d.age * 0.02;
        for (int lat = 1; lat <= 5; lat++) {   // hexagon-like lattice: rings of points, every other ring shifted
            double phi = lat * Math.PI / 12;   // 15..75 degrees above the ground
            double rr = r * Math.cos(phi), y = r * Math.sin(phi);
            int n = Math.max(6, (int) (rr * 2.4));
            for (int i = 0; i < n; i++) {
                double t = spin + (i + (lat % 2) * 0.5) * Math.PI * 2 / n;
                particles(sl, lat == 1 ? TURQUOISE : TURQUOISE_SMALL, c.add(Math.cos(t) * rr, y, Math.sin(t) * rr), 1, 0, 0);
            }
        }
        particles(sl, TURQUOISE_SMALL, c.add(0, r, 0), 1, 0, 0);
    }

    private static void fade(Dome d) {
        if (d.fxInst >= 0) Fx.stop(d.level, d.fxInst, "");
        else {
            Vec3 c = d.center();
            for (int i = 0; i < 40; i++) {
                double t = i * Math.PI * 2 / 40;
                particles(d.level, ParticleTypes.END_ROD, c.add(Math.cos(t) * d.radius, 0.2, Math.sin(t) * d.radius), 1, 0.05, 0.01);
            }
        }
    }

    public static final class BarrierEvents {
        private BarrierEvents() {}

        @SubscribeEvent
        public static void onLevelTick(TickEvent.LevelTickEvent e) {
            if (e.phase != TickEvent.Phase.END || DOMES.isEmpty() || !(e.level instanceof ServerLevel sl)) return;
            DOMES.removeIf(d -> {
                if (d.level != sl) return false;
                d.age++;
                if (!d.alive()) {
                    fade(d);
                    return true;
                }
                if (d.fxInst < 0) draw(d);
                stopProjectiles(d);
                return false;
            });
            clearSideEffects(sl);
        }

        /** Projectiles from outside that are inside or would enter this tick stop on the surface and go out. */
        private static void stopProjectiles(Dome d) {
            Vec3 c = d.center();
            double reach = d.radius + 20;
            for (Projectile p : d.level.getEntitiesOfClass(Projectile.class, new AABB(c, c).inflate(reach), p -> p.isAlive())) {
                Entity owner = p.getOwner();
                if (owner != null && d.inside(owner)) continue;   // shot from inside: flies out freely
                Vec3 pos = p.position(), next = pos.add(p.getDeltaMovement());
                Vec3 hit;
                if (d.inside(pos)) {
                    Vec3 back = new Vec3(p.xo, p.yo, p.zo);
                    hit = d.inside(back) ? null : hitSphere(back, pos, c, d.radius);
                    if (hit == null) {
                        if (d.inside(back) && p.tickCount > 1) continue;   // was already inside before the dome (or spawned in it long ago)
                        hit = c.add(pos.subtract(c).normalize().scale(d.radius));
                    }
                } else {
                    hit = hitSphere(pos, next, c, d.radius);
                    if (hit == null) continue;
                }
                ripple(d, hit);
                particles(d.level, ParticleTypes.CLOUD, hit, 3, 0.05, 0.01);
                p.setDeltaMovement(Vec3.ZERO);
                p.discard();
            }
        }

        /** Ray and touch spells cast from outside at someone the dome shields are cancelled before they start. */
        @SubscribeEvent
        public static void onPreCast(SpellPreCastEvent e) {
            if (DOMES.isEmpty() || !(e.getEntity().level() instanceof ServerLevel sl)) return;
            net.minecraft.world.entity.player.Player caster = e.getEntity();
            HitResult hr = Utils.raycastForEntity(sl, caster, 48f, true);
            if (!(hr instanceof EntityHitResult eh)) return;
            Entity t = eh.getEntity();
            Dome d = shielding(t);
            if (d == null || d.inside(caster)) return;
            e.setCanceled(true);
            Vec3 at = hitSphere(caster.getEyePosition(), eh.getLocation(), d.center(), d.radius);
            ripple(d, at != null ? at : eh.getLocation());
            caster.displayClientMessage(Component.translatable("ui.pohsmp_core.sage_barrier.blocked").withStyle(s -> s.withColor(COLOR)), true);
        }

        /**
         * Spell damage from outside (rays, touches, breath cones, beams sweeping over the dome: the caster and the thing that deals
         * the damage are both outside) to someone the dome shields does not get through, nor the fire or frost it brings.
         * Projectiles are already stopped at the surface; melee is not spell damage and passes; an area spell standing inside works.
         */
        @SubscribeEvent(priority = EventPriority.HIGH)
        public static void onAttack(LivingAttackEvent e) {
            if (DOMES.isEmpty() || !(e.getSource() instanceof SpellDamageSource src)) return;
            Entity attacker = src.getEntity(), direct = src.getDirectEntity();
            if (attacker == null) return;
            LivingEntity t = e.getEntity();
            Dome d = shielding(t);
            if (d == null || d.inside(attacker) || (direct != null && direct != attacker && d.inside(direct))) return;
            e.setCanceled(true);
            BLOCKED.put(t, t.level().getGameTime());
            Vec3 from = direct != null ? direct.position().add(0, direct.getBbHeight() * 0.5, 0) : attacker.getEyePosition();
            Vec3 at = hitSphere(from, SilentSpell.aimPoint(t), d.center(), d.radius);
            if (at != null && d.age % 4 == 0) ripple(d, at);
        }

        /** Shielded entities a spell from outside was stopped on lately: the fire or frost that spell put on them goes out. */
        private static final java.util.Map<LivingEntity, Long> BLOCKED = new java.util.WeakHashMap<>();

        private static void clearSideEffects(ServerLevel sl) {
            if (BLOCKED.isEmpty()) return;
            long now = sl.getGameTime();
            BLOCKED.entrySet().removeIf(en -> {
                LivingEntity t = en.getKey();
                if (t.level() != sl) return false;
                if (now - en.getValue() > 10 || shielding(t) == null) return true;
                if (t.getRemainingFireTicks() > 0) t.clearFire();
                if (t.getTicksFrozen() > 0) t.setTicksFrozen(0);
                return false;
            });
        }

        @SubscribeEvent
        public static void onStopping(ServerStoppingEvent e) {
            DOMES.clear();
        }
    }
}
