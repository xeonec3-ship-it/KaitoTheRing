package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.registry.SchoolRegistry;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.spells.SpellRarity;
import io.redspace.ironsspellbooks.entity.spells.root.RootEntity;
import java.util.ArrayList;
import java.util.List;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.ai.goal.GoalSelector;
import net.minecraft.world.entity.monster.Creeper;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.fml.util.ObfuscationReflectionHelper;
import ru.pohsmp.core.DivineEvents;

/**
 * Nature: roots grab everyone in an area where the caster looks, and allied creepers grow out of the ground.
 * The creepers hunt the caster's enemies and burst without breaking blocks.
 */
public class GraspingGardenSpell extends PohSpell {
    public static final String PATH = "grasping_garden";
    public static final String CREEPER_TAG = "poh_creeper";
    private static final int CREEPER_LIFE = 400;

    public GraspingGardenSpell() {
        super(PATH, SchoolRegistry.NATURE_RESOURCE, SpellRarity.UNCOMMON, 6, 30, 0, 50, 10);
    }

    @Override public CastType getCastType() { return CastType.INSTANT; }

    private double radius(int l) { return lv(l, 4, 8); }
    private int creepers(int l) { return (int) Math.round(lv(l, 1, 4)); }
    private int rootTicks(int l) { return (int) (lv(l, 3, 5) * 20); }
    private double boom(int l, LivingEntity c) { return lv(l, 8, 14) * mult(c); }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("roots", n(radius(level)), n(rootTicks(level) / 20.0)), ui("creepers", creepers(level), n(boom(level, caster))));
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            Vec3 c = ground(sl, caster, lookPoint(sl, caster, 20));
            double r = radius(spellLevel);
            int rt = rootTicks(spellLevel);
            for (LivingEntity t : HigherSpell.around(sl, c, r, e -> !HigherSpell.friendly(caster, e) && !(e instanceof RootEntity) && !e.getTags().contains(CREEPER_TAG))) {
                if (t.getVehicle() instanceof RootEntity) continue;
                if (t.isPassenger()) t.stopRiding();
                RootEntity root = new RootEntity(sl, caster);
                root.setDuration(rt);
                root.setTarget(t);
                root.moveTo(t.getX(), t.getY(), t.getZ(), t.getYRot(), 0);
                sl.addFreshEntity(root);
                t.startRiding(root, true);
            }
            int n = (int) (r * 5);
            for (int i = 0; i < n; i++) {
                double a = i * Math.PI * 2 / n;
                DivineEvents.particle(sl, ParticleTypes.HAPPY_VILLAGER, c.x + Math.cos(a) * r, c.y + 0.2, c.z + Math.sin(a) * r, 2, 0.1, 0);
            }
            sl.playSound(null, c.x, c.y, c.z, SoundEvents.ROOTED_DIRT_BREAK, SoundSource.PLAYERS, 2f, 0.6f);
            float dmg = (float) boom(spellLevel, caster);
            int k = creepers(spellLevel);
            for (int i = 0; i < k; i++) {
                double a = i * Math.PI * 2 / k + 0.4;
                Vec3 p = ground(sl, caster, c.add(Math.cos(a) * 1.5, 1, Math.sin(a) * 1.5));
                spawnCreeper(sl, caster, p, dmg);
            }
        }
        super.onCast(level, spellLevel, caster, source, md);
    }

    private void spawnCreeper(ServerLevel sl, LivingEntity caster, Vec3 p, float dmg) {
        Creeper cr = EntityType.CREEPER.create(sl);
        if (cr == null) return;
        cr.moveTo(p.x, p.y, p.z, caster.getYRot(), 0);
        cr.addTag(CREEPER_TAG);
        cr.setPersistenceRequired();
        Disp.track(cr);
        try {
            GoalSelector ts = ObfuscationReflectionHelper.getPrivateValue(Mob.class, cr, "f_21346_");
            if (ts != null) ts.removeAllGoals(g -> true);
        } catch (Exception ignored) {
        }
        sl.addFreshEntity(cr);
        DivineEvents.particle(sl, ParticleTypes.COMPOSTER, p.x, p.y + 0.5, p.z, 20, 0.4, 0.05);
        List<Creeper> self = new ArrayList<>(List.of(cr));
        Tasks.add(new Tasks.Task() {
            int age;

            @Override
            public boolean tick() {
                age++;
                Creeper c = self.get(0);
                if (!c.isAlive() || c.isRemoved()) return false;
                if (age > CREEPER_LIFE || !caster.isAlive()) {
                    DivineEvents.particle(sl, ParticleTypes.COMPOSTER, c.getX(), c.getY() + 0.8, c.getZ(), 20, 0.4, 0.05);
                    c.discard();
                    return false;
                }
                if (age % 10 == 1) {
                    LivingEntity best = null;
                    double bd = 24 * 24;
                    for (LivingEntity e : HigherSpell.around(sl, c.position(), 24, e -> e != c && !e.getTags().contains(CREEPER_TAG) && HigherSpell.foe(caster, e))) {
                        double d = e.distanceToSqr(c);
                        if (d < bd) { bd = d; best = e; }
                    }
                    c.setTarget(best);
                    if (best == null && c.distanceToSqr(caster) > 16) c.getNavigation().moveTo(caster, 1.1);
                }
                if (c.getTarget() == caster || (c.getTarget() != null && HigherSpell.friendly(caster, c.getTarget()))) c.setTarget(null);
                if (c.getSwelling(1f) > 0.85f) {
                    Vec3 at = c.position();
                    c.discard();
                    DivineEvents.particle(sl, ParticleTypes.EXPLOSION_EMITTER, at.x, at.y + 0.5, at.z, 1, 0, 0);
                    DivineEvents.particle(sl, ParticleTypes.COMPOSTER, at.x, at.y + 0.5, at.z, 40, 1.2, 0.1);
                    sl.playSound(null, at.x, at.y, at.z, SoundEvents.GENERIC_EXPLODE, SoundSource.HOSTILE, 2f, 1.1f);
                    for (LivingEntity e : HigherSpell.around(sl, at, 3.5, e -> !HigherSpell.friendly(caster, e) && !e.getTags().contains(CREEPER_TAG))) {
                        double d = e.position().distanceTo(at);
                        hit(caster, e, (float) (dmg * (1 - 0.5 * Math.min(1, d / 3.5))));
                        Vec3 away = e.position().subtract(at).multiply(1, 0, 1);
                        if (away.lengthSqr() > 1e-4) HigherSpell.push(e, away.normalize().scale(0.8).add(0, 0.45, 0));
                    }
                    return false;
                }
                return true;
            }
        });
    }
}
