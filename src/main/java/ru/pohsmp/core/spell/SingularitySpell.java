package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import java.util.List;
import java.util.Optional;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.ClipContext;
import net.minecraft.world.level.Level;
import net.minecraft.world.entity.projectile.ProjectileUtil;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.EntityHitResult;
import net.minecraft.world.phys.HitResult;
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.DivineEvents;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.fx.Fx;

/** Gravity mage: a black sphere where the caster looks (up to 24 blocks) pulls everything within 8 for 4 s, pins it down, then collapses (16 in r4, thrown out). */
public class SingularitySpell extends HigherSpell {
    public static final String PATH = "singularity";
    private static final int LIFE = 80;
    private static final double RANGE = 24, PULL_R = 8, BOOM_R = 4, DMG = 16;
    public static final int COLOR = 0x9B4DFF;

    public SingularitySpell() {
        super(PATH, 0);
    }

    @Override public CastType getCastType() { return CastType.INSTANT; }
    @Override public Optional<SoundEvent> getCastStartSound() { return Optional.empty(); }
    @Override public Optional<SoundEvent> getCastFinishSound() { return Optional.of(SoundEvents.WARDEN_SONIC_CHARGE); }

    @Override
    public List<MutableComponent> getUniqueInfo(int spellLevel, LivingEntity caster) {
        return List.of(ui("pull", (int) PULL_R, LIFE / 20), ui("damage", num(DMG), (int) BOOM_R), ui("heavy"));
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity entity, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) open(sl, entity);
        super.onCast(level, spellLevel, entity, source, md);
    }

    private void open(ServerLevel sl, LivingEntity caster) {
        Vec3 eye = caster.getEyePosition(), look = caster.getLookAngle();
        BlockHitResult hr = sl.clip(new ClipContext(eye, eye.add(look.scale(RANGE)), ClipContext.Block.COLLIDER, ClipContext.Fluid.NONE, caster));
        Vec3 end = hr.getType() == HitResult.Type.MISS ? eye.add(look.scale(RANGE)) : hr.getLocation();
        EntityHitResult er = ProjectileUtil.getEntityHitResult(sl, caster, eye, end, caster.getBoundingBox().expandTowards(end.subtract(eye)).inflate(1),
                e -> e instanceof LivingEntity && e.isAlive() && !friendly(caster, e), 0.3f);
        Vec3 c = er != null ? new Vec3(er.getEntity().getX(), er.getEntity().getY() + 1, er.getEntity().getZ())
                : hr.getType() == HitResult.Type.MISS ? end : hr.getLocation().subtract(look.scale(0.8));
        Vec3 floor = PohSpell.ground(sl, caster, c);
        Fx.play(sl, Fx.fx("higher_singularity").at(c).point("floor", floor));
        sl.playSound(null, c.x, c.y, c.z, SoundEvents.BEACON_ACTIVATE, SoundSource.PLAYERS, 3f, 0.5f);
        Tasks.add(new Tasks.Task() {
            int age;

            @Override
            public boolean tick() {
                age++;
                for (LivingEntity e : around(sl, c, PULL_R, e -> !friendly(caster, e))) {
                    Vec3 h = new Vec3(c.x - e.getX(), 0, c.z - e.getZ());
                    double d = h.length();
                    Vec3 v = e.getDeltaMovement().multiply(0.85, 1, 0.85);
                    if (d > 0.5) v = v.add(h.scale((0.07 + 0.11 * (1 - d / PULL_R)) / d));
                    double hs = Math.sqrt(v.x * v.x + v.z * v.z);
                    if (hs > 0.7) v = new Vec3(v.x / hs * 0.7, v.y, v.z / hs * 0.7);
                    if (!e.onGround()) v = new Vec3(v.x, Math.min(v.y, 0) - 0.08, v.z);
                    push(e, v);
                    e.fallDistance = 0;
                    if (age % 10 == 1) e.addEffect(new MobEffectInstance(Reg.HEAVY.get(), 20, 0, false, true, true));
                }
                if (age % 2 == 0) {
                    for (int i = 0; i < 6; i++) {
                        double a = caster.getRandom().nextDouble() * Math.PI * 2, r = 2 + caster.getRandom().nextDouble() * (PULL_R - 2);
                        double px = c.x + Math.cos(a) * r, pz = c.z + Math.sin(a) * r, py = c.y + (caster.getRandom().nextDouble() - 0.5) * 3;
                        DivineEvents.particle(sl, ParticleTypes.REVERSE_PORTAL, px, py, pz, 0, 0, 0);
                    }
                    DivineEvents.particle(sl, ParticleTypes.PORTAL, c.x, c.y, c.z, 6, 0.6, 1.0);
                }
                if (age % 20 == 0) sl.playSound(null, c.x, c.y, c.z, SoundEvents.BEACON_AMBIENT, SoundSource.PLAYERS, 3f, 0.5f);
                if (age < LIFE) return true;
                collapse(sl, caster, c, floor);
                return false;
            }
        });
    }

    private void collapse(ServerLevel sl, LivingEntity caster, Vec3 c, Vec3 floor) {
        Fx.play(sl, Fx.fx("higher_singularity_collapse").at(c).point("floor", floor));
        sl.playSound(null, c.x, c.y, c.z, SoundEvents.GENERIC_EXPLODE, SoundSource.PLAYERS, 3f, 0.5f);
        sl.playSound(null, c.x, c.y, c.z, SoundEvents.ENDERMAN_TELEPORT, SoundSource.PLAYERS, 3f, 0.5f);
        DivineEvents.particle(sl, ParticleTypes.REVERSE_PORTAL, c.x, c.y, c.z, 150, 0.3, 0.8);
        DivineEvents.particle(sl, ParticleTypes.SQUID_INK, c.x, c.y, c.z, 40, 0.5, 0.2);
        for (LivingEntity e : around(sl, c, BOOM_R, e -> !friendly(caster, e))) {
            hurt(sl, caster, e, dmg(DMG));
            Vec3 d = new Vec3(e.getX() - c.x, 0, e.getZ() - c.z);
            d = d.lengthSqr() < 1e-4 ? new Vec3(1, 0, 0) : d.normalize();
            push(e, d.scale(1.5).add(0, 0.5, 0));
            e.addEffect(new MobEffectInstance(Reg.HEAVY.get(), 40, 0, false, true, true));
        }
    }
}
