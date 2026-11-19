package ru.pohsmp.core.spell.silent;

import ru.pohsmp.core.spell.Tasks;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.spells.SpellAnimations;
import io.redspace.ironsspellbooks.api.util.AnimationHolder;
import io.redspace.ironsspellbooks.damage.DamageSources;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import net.minecraft.core.particles.DustParticleOptions;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.effect.MobEffect;
import net.minecraft.world.effect.MobEffectCategory;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import org.joml.Vector3f;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.ServerConfig;
import ru.pohsmp.core.fx.Fx;

/**
 * "Black Flame of Worgan" (after Nero, the black dragon): during a 2 s cast a see-through shadow of a black dragon (head and neck)
 * rises over the caster's right shoulder, opens its jaws and breathes black flame in a 40° cone 12 blocks long for 3 s.
 * A target in the cone takes 3 damage every 10 ticks and burns with black flame for 8 s: 1.5 damage a second, water does not
 * put it out (it is an effect, not fire; milk does not cure it either). Then the shadow crumbles.
 * Look: fx/silent_worgan_flame.json with the dragon mesh (ideas chat) - stand-in particles until then.
 */
public class WorganFlameSpell extends SilentSpell {
    public static final String PATH = "worgan_flame";
    public static final int BLACK = 0x14101A;
    private static final DustParticleOptions SOOT = new DustParticleOptions(new Vector3f(0.04f, 0.03f, 0.06f), 1.6f);
    private static final DustParticleOptions SOOT_SMALL = new DustParticleOptions(new Vector3f(0.06f, 0.04f, 0.08f), 0.9f);
    private static final DustParticleOptions VIOLET = new DustParticleOptions(new Vector3f(0.55f, 0.2f, 0.85f), 0.9f);

    private static final class Cast {
        int age, fxInst = -1;
    }

    private static final Map<UUID, Cast> CASTS = new HashMap<>();

    public WorganFlameSpell() {
        super(PATH, 40, 150, 30, ServerConfig.FLAME_CAST, ServerConfig.FLAME_MANA, ServerConfig.FLAME_COOLDOWN);
    }

    @Override public CastType getCastType() { return CastType.LONG; }
    @Override public AnimationHolder getCastStartAnimation() { return SpellAnimations.CHARGE_RAISED_HAND; }
    @Override public AnimationHolder getCastFinishAnimation() { return SpellAnimations.ONE_HANDED_RAY_SHOOT; }

    private static int breath() { return cfg(ServerConfig.FLAME_BREATH::get, 60); }
    private static double range() { return cfg(ServerConfig.FLAME_RANGE::get, 12.0); }
    private static double coneDeg() { return cfg(ServerConfig.FLAME_CONE::get, 40.0); }
    private static int interval() { return cfg(ServerConfig.FLAME_INTERVAL::get, 10); }
    private static int burnSec() { return cfg(ServerConfig.FLAME_BURN::get, 8); }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("breath", n(breath() / 20.0), n(coneDeg()), n(range())),
                ui("damage", n(dmg(caster, cfg(ServerConfig.FLAME_DAMAGE::get, 3.0))), n(interval() / 20.0)),
                ui("burn", burnSec(), n(dmg(caster, cfg(ServerConfig.FLAME_BURN_DPS::get, 1.5)))));
    }

    /** The dragon's head: over the right shoulder, a little behind. */
    private static Vec3 headPos(LivingEntity c, double rise) {
        return local(c, 0.95, c.getBbHeight() + 0.2 + 0.9 * rise, -0.25);
    }

    /** The jaws, where the flame comes from: in front of the head along the look. */
    private static Vec3 mouth(LivingEntity c) {
        return headPos(c, 1).add(c.getLookAngle().scale(0.7));
    }

    @Override
    public void onServerPreCast(Level level, int spellLevel, LivingEntity caster, MagicData md) {
        super.onServerPreCast(level, spellLevel, caster, md);
        if (!(level instanceof ServerLevel sl)) return;
        Cast c = new Cast();
        c.fxInst = fx(sl, "silent_worgan_flame", Fx.fx("silent_worgan_flame").caster(caster).attach(caster)
                .duration(getCastTime(1) + breath() + 30));
        CASTS.put(caster.getUUID(), c);
    }

    @Override
    public void onServerCastTick(Level level, int spellLevel, LivingEntity caster, MagicData md) {
        super.onServerCastTick(level, spellLevel, caster, md);
        Cast c = CASTS.get(caster.getUUID());
        if (c == null || !(level instanceof ServerLevel sl)) return;
        c.age++;
        if (c.fxInst < 0 && c.age % 2 == 0) drawShadow(sl, caster, Math.min(1.0, c.age / (double) Math.max(1, getCastTime(spellLevel))), false);
    }

    /** Stand-in dragon shadow: a curved neck of soot rising from the shoulder, a head with violet eyes; jaws open when breathing. */
    private static void drawShadow(ServerLevel sl, LivingEntity c, double rise, boolean open) {
        Vec3 base = local(c, 0.45, c.getBbHeight() - 0.15, -0.2);
        Vec3 head = headPos(c, rise);
        Vec3 bend = base.add(0.0, 0.2, 0).add(local(c, 0.5, 0, -0.6).subtract(c.position()));
        for (int i = 0; i <= 8; i++) {   // neck
            double k = i / 8.0;
            Vec3 p = base.scale((1 - k) * (1 - k)).add(bend.scale(2 * k * (1 - k))).add(head.scale(k * k));
            particles(sl, SOOT, p, 1, 0.04, 0);
        }
        Vec3 look = c.getLookAngle();
        Vec3 snout = head.add(look.scale(0.55));
        particles(sl, SOOT, head, 2, 0.1, 0);
        particles(sl, SOOT_SMALL, snout, 1, 0.05, 0);
        Vec3 side = look.cross(new Vec3(0, 1, 0)).normalize().scale(0.14);
        particles(sl, VIOLET, head.add(look.scale(0.2)).add(0, 0.1, 0).add(side), 1, 0, 0);
        particles(sl, VIOLET, head.add(look.scale(0.2)).add(0, 0.1, 0).subtract(side), 1, 0, 0);
        if (open) particles(sl, SOOT_SMALL, snout.add(0, -0.25, 0), 1, 0.03, 0);   // lower jaw
    }

    @Override
    public void onServerCastComplete(Level level, int spellLevel, LivingEntity caster, MagicData md, boolean cancelled) {
        Cast c = CASTS.remove(caster.getUUID());
        if (cancelled && c != null && level instanceof ServerLevel sl) crumble(sl, caster, c.fxInst);
        super.onServerCastComplete(level, spellLevel, caster, md, cancelled);
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            Cast c = CASTS.get(caster.getUUID());
            breathe(sl, caster, c == null ? -1 : c.fxInst);
        }
        super.onCast(level, spellLevel, caster, source, md);
    }

    private static void crumble(ServerLevel sl, LivingEntity caster, int fxInst) {
        if (fxInst >= 0) {
            Fx.stop(sl, fxInst, "");
            return;
        }
        Vec3 h = headPos(caster, 1);
        particles(sl, ParticleTypes.LARGE_SMOKE, h, 12, 0.35, 0.02);
        particles(sl, SOOT_SMALL, h, 16, 0.5, 0);
        particles(sl, ParticleTypes.ASH, h, 20, 0.6, 0.02);
    }

    private void breathe(ServerLevel sl, LivingEntity caster, int fxInst) {
        int len = breath(), every = interval(), burn = burnSec() * 20;
        double range = range(), cone = coneDeg();
        float damage = (float) dmg(caster, cfg(ServerConfig.FLAME_DAMAGE::get, 3.0));
        float dps = (float) dmg(caster, cfg(ServerConfig.FLAME_BURN_DPS::get, 1.5));
        Map<UUID, Integer> lastHit = new HashMap<>();
        sl.playSound(null, caster.getX(), caster.getY() + 2, caster.getZ(), SoundEvents.ENDER_DRAGON_SHOOT, SoundSource.PLAYERS, 0.5f, 0.6f);
        Tasks.add(new Tasks.Task() {
            int age;

            @Override
            public boolean tick() {
                age++;
                if (!caster.isAlive() || caster.isRemoved() || caster.level() != sl || age > len) {
                    crumble(sl, caster, fxInst);
                    return false;
                }
                Vec3 from = mouth(caster), look = caster.getLookAngle();
                if (fxInst < 0) {
                    drawShadow(sl, caster, 1, true);
                    drawBreath(sl, from, look, range, cone, age);
                }
                if (age % 8 == 1) sl.playSound(null, from.x, from.y, from.z, SoundEvents.FIRE_AMBIENT, SoundSource.PLAYERS, 0.9f, 0.5f);
                // hits are aimed from the caster's eyes (where the player looks), the flame is drawn from the dragon's jaws
                for (LivingEntity t : cone(sl, caster, caster.getEyePosition(), look, range, cone, false)) {
                    if (!caster.hasLineOfSight(t)) continue;
                    SageBarrierSpell.Dome d = SageBarrierSpell.shielding(t);
                    if (d != null && !d.inside(caster)) continue;   // a Barrier shields it
                    Integer last = lastHit.get(t.getUUID());
                    if (last != null && age - last < every) continue;
                    lastHit.put(t.getUUID(), age);
                    hit(caster, t, damage);
                    ignite(t, caster, burn, dps);
                }
                return true;
            }
        });
    }

    /** Stand-in breath: black tongues with a violet edge and ash, filling the cone. */
    private static void drawBreath(ServerLevel sl, Vec3 from, Vec3 look, double range, double coneDeg, int age) {
        Vec3 up = Math.abs(look.y) > 0.95 ? new Vec3(1, 0, 0) : new Vec3(0, 1, 0);
        Vec3 a = look.cross(up).normalize(), b = look.cross(a).normalize();
        double tan = Math.tan(Math.toRadians(coneDeg / 2));
        for (int i = 0; i < 26; i++) {
            double d = range * Math.sqrt(sl.random.nextDouble());
            double rr = d * tan * Math.sqrt(sl.random.nextDouble());
            double t = sl.random.nextDouble() * Math.PI * 2;
            Vec3 p = from.add(look.scale(d)).add(a.scale(Math.cos(t) * rr)).add(b.scale(Math.sin(t) * rr));
            boolean edge = rr > d * tan * 0.75;
            particles(sl, edge ? VIOLET : SOOT, p, 1, 0.05, 0);
            if (i % 5 == 0) particles(sl, ParticleTypes.SQUID_INK, p, 1, 0.1, 0.01);
        }
        if (age % 3 == 0) particles(sl, ParticleTypes.ASH, from.add(look.scale(range * 0.6)), 6, range * 0.15, 0.02);
    }

    // ---------------------------------------------------------------- black flame

    /** Who lit the flame on whom and how hard it burns (for kill credit and spell power). */
    private static final Map<UUID, Object[]> BURNERS = new HashMap<>();

    /** Sets the target on black flame (refreshes the time). */
    public static void ignite(LivingEntity t, LivingEntity caster, int ticks, float dps) {
        if (ticks <= 0 || dps <= 0) return;
        BURNERS.put(t.getUUID(), new Object[] {caster == null ? null : caster.getUUID(), dps});
        t.addEffect(new MobEffectInstance(Reg.BLACK_FLAME.get(), ticks, 0, false, true, true), caster);
    }

    /** The effect: burns every second, not fire - water and rain do nothing to it, milk does not cure it. */
    public static class BlackFlame extends MobEffect {
        public BlackFlame() {
            super(MobEffectCategory.HARMFUL, 0x2A1240);
        }

        @Override
        public boolean isDurationEffectTick(int duration, int amplifier) {
            return duration % 4 == 0;
        }

        @Override
        public void applyEffectTick(LivingEntity e, int amplifier) {
            if (!(e.level() instanceof ServerLevel sl)) return;
            Vec3 p = e.position().add(0, e.getBbHeight() * 0.5, 0);
            particles(sl, SOOT_SMALL, p, 3, e.getBbWidth() * 0.4, 0);
            particles(sl, VIOLET, p.add(0, e.getBbHeight() * 0.3, 0), 1, e.getBbWidth() * 0.3, 0);
            particles(sl, ParticleTypes.LARGE_SMOKE, p.add(0, e.getBbHeight() * 0.4, 0), 1, 0.1, 0.01);
            MobEffectInstance inst = e.getEffect(this);
            if (inst == null || inst.getDuration() % 20 != 0) return;
            Object[] b = BURNERS.get(e.getUUID());
            float dps = b == null ? 1.5f : (float) b[1];
            Entity caster = b == null || b[0] == null ? null : sl.getEntity((UUID) b[0]);
            e.invulnerableTime = 0;
            if (caster instanceof LivingEntity lc && Reg.WORGAN_FLAME.get() instanceof WorganFlameSpell sp)
                DamageSources.applyDamage(e, dps, sp.getDamageSource(lc).setIFrames(0));
            else e.hurt(new net.minecraft.world.damagesource.DamageSource(sl.registryAccess().registryOrThrow(net.minecraft.core.registries.Registries.DAMAGE_TYPE).getHolderOrThrow(Reg.SILENT_DAMAGE)), dps);
            if (inst.getDuration() <= 20) BURNERS.remove(e.getUUID());
        }

        @Override
        public List<ItemStack> getCurativeItems() {
            return new java.util.ArrayList<>();
        }
    }
}
