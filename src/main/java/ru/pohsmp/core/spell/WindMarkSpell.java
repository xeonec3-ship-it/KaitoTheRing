package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.spells.SpellRarity;
import java.util.List;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.ClipContext;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.HitResult;
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.DivineEvents;
import ru.pohsmp.core.Reg;

/** Wind: a gust flies forward; the first creature hit gets the Wind Mark and is thrown about 5 blocks up every 2 s. Fall damage stays. */
public class WindMarkSpell extends PohSpell {
    public static final String PATH = "wind_mark";
    private static final double SPEED = 1.6, RANGE = 40;

    public WindMarkSpell() {
        super(PATH, GaleWardSpell.WIND, SpellRarity.COMMON, 6, 18, 0, 30, 6);
    }

    @Override public CastType getCastType() { return CastType.INSTANT; }

    private int ticks(int l) { return (int) (lv(l, 4, 14) * 20); }
    private double damage(int l, LivingEntity c) { return lv(l, 2, 5) * mult(c); }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("time", n(ticks(level) / 20.0)), ui("damage", n(damage(level, caster))));
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            int dur = ticks(spellLevel);
            float dmg = (float) damage(spellLevel, caster);
            Vec3 dir = caster.getLookAngle().normalize();
            sl.playSound(null, caster.getX(), caster.getY(), caster.getZ(), SoundEvents.ENDER_DRAGON_FLAP, SoundSource.PLAYERS, 0.8f, 1.6f);
            Tasks.add(new Tasks.Task() {
                Vec3 p = caster.getEyePosition().add(dir.scale(0.6));
                double gone;

                @Override
                public boolean tick() {
                    Vec3 next = p.add(dir.scale(SPEED));
                    BlockHitResult bh = sl.clip(new ClipContext(p, next, ClipContext.Block.COLLIDER, ClipContext.Fluid.NONE, caster));
                    Vec3 end = bh.getType() == HitResult.Type.MISS ? next : bh.getLocation();
                    LivingEntity hitE = null;
                    double best = Double.MAX_VALUE;
                    for (LivingEntity e : sl.getEntitiesOfClass(LivingEntity.class, new AABB(p, end).inflate(0.6), e -> e.isAlive() && !HigherSpell.friendly(caster, e))) {
                        var o = e.getBoundingBox().inflate(0.4).clip(p, end);
                        if (o.isPresent() && o.get().distanceToSqr(p) < best) { best = o.get().distanceToSqr(p); hitE = e; }
                    }
                    for (int i = 0; i < 4; i++) {
                        Vec3 q = p.lerp(end, i / 4.0);
                        DivineEvents.particle(sl, ParticleTypes.CLOUD, q.x, q.y, q.z, 1, 0.05, 0.01);
                    }
                    DivineEvents.particle(sl, ParticleTypes.SWEEP_ATTACK, end.x, end.y, end.z, 1, 0, 0);
                    if (hitE != null) {
                        hit(caster, hitE, dmg);
                        hitE.addEffect(new MobEffectInstance(Reg.TOSS.get(), dur, 0, false, true, true));
                        PohEvents.toss(hitE);
                        sl.playSound(null, hitE.getX(), hitE.getY(), hitE.getZ(), SoundEvents.PHANTOM_FLAP, SoundSource.PLAYERS, 1.5f, 0.6f);
                        DivineEvents.particle(sl, ParticleTypes.CLOUD, hitE.getX(), hitE.getY() + 0.5, hitE.getZ(), 25, 0.5, 0.05);
                        return false;
                    }
                    p = end;
                    gone += SPEED;
                    return bh.getType() == HitResult.Type.MISS && gone < RANGE;
                }
            });
        }
        super.onCast(level, spellLevel, caster, source, md);
    }
}
