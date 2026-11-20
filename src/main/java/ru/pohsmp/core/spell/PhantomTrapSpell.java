package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.registry.SchoolRegistry;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.spells.SpellRarity;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import net.minecraft.core.particles.DustParticleOptions;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import org.joml.Vector3f;
import ru.pohsmp.core.DivineEvents;
import ru.pohsmp.core.Reg;

/** Evocation: an invisible trap where the caster looks; the first creature to step on it is seized by spectral chains and held. */
public class PhantomTrapSpell extends PohSpell {
    public static final String PATH = "phantom_trap";
    private static final int LIFE = 600, MAX = 3;
    private static final DustParticleOptions VIOLET = new DustParticleOptions(new Vector3f(0.6f, 0.45f, 1f), 1.2f);
    private static final Map<UUID, Integer> COUNT = new HashMap<>();

    public PhantomTrapSpell() {
        super(PATH, SchoolRegistry.EVOCATION_RESOURCE, SpellRarity.COMMON, 6, 6, 0, 25, 4);
    }

    @Override public CastType getCastType() { return CastType.INSTANT; }

    private int hold(int l) { return (int) (lv(l, 2, 4) * 20); }
    private double damage(int l, LivingEntity c) { return lv(l, 3, 8) * mult(c); }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("hold", n(hold(level) / 20.0), n(damage(level, caster))), ui("limit", MAX, LIFE / 20));
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl && COUNT.getOrDefault(caster.getUUID(), 0) < MAX) {
            Vec3 c = ground(sl, caster, lookPoint(sl, caster, 16));
            int hold = hold(spellLevel);
            float dmg = (float) damage(spellLevel, caster);
            UUID owner = caster.getUUID();
            COUNT.merge(owner, 1, Integer::sum);
            sl.playSound(null, c.x, c.y, c.z, SoundEvents.ILLUSIONER_PREPARE_MIRROR, SoundSource.PLAYERS, 0.8f, 1.4f);
            DivineEvents.particle(sl, VIOLET, c.x, c.y + 0.1, c.z, 20, 0.5, 0);
            Tasks.add(new Tasks.Task() {
                int age, held = -1, snare = -1;
                LivingEntity prey;

                private boolean end() {
                    COUNT.computeIfPresent(owner, (k, v) -> v <= 1 ? null : v - 1);
                    return false;
                }

                @Override
                public boolean tick() {
                    age++;
                    if (prey == null) {
                        if (age > LIFE || !caster.isAlive()) return end();
                        if (age % 30 == 0 && caster instanceof ServerPlayer sp)   // only the caster sees where it lies
                            sl.sendParticles(sp, VIOLET, true, c.x, c.y + 0.1, c.z, 3, 0.4, 0, 0.4, 0);
                        if (age < 10) return true;
                        for (LivingEntity e : HigherSpell.around(sl, c.add(0, 0.5, 0), 1.6, e -> !HigherSpell.friendly(caster, e))) {
                            if (hdist(e, c) > 1.1 || Math.abs(e.getY() - c.y) > 1) continue;
                            prey = e;
                            held = 0;
                            hit(caster, e, dmg);
                            sl.playSound(null, c.x, c.y, c.z, SoundEvents.CHAIN_PLACE, SoundSource.PLAYERS, 2f, 0.6f);
                            sl.playSound(null, c.x, c.y, c.z, SoundEvents.EVOKER_FANGS_ATTACK, SoundSource.PLAYERS, 1.5f, 0.8f);
                            DivineEvents.particle(sl, ParticleTypes.WITCH, c.x, c.y + 0.5, c.z, 40, 0.6, 0.1);
                            break;
                        }
                        return true;
                    }
                    held++;
                    if (held == 1) snare = ru.pohsmp.core.fx.Fx.play(sl, ru.pohsmp.core.fx.Fx.fx("phantom_trap_snare").at(c).target(prey).yaw(caster.getYRot()));
                    if (!prey.isAlive() || held > hold || !ru.pohsmp.core.boss.BossGuard.holding(prey, "phantom_trap", hold)) {   // cult bosses: x0.25, <= 2 s
                        if (snare >= 0) ru.pohsmp.core.fx.Fx.stop(sl, snare, "");
                        return end();
                    }
                    HigherSpell.place(prey, c.x, c.y, c.z);
                    prey.setDeltaMovement(Vec3.ZERO);
                    if (prey instanceof Mob m) m.getNavigation().stop();
                    if (held % 10 == 1 && !ru.pohsmp.core.boss.BossGuard.isBoss(prey)) prey.addEffect(new MobEffectInstance(Reg.PARALYSIS.get(), 15, 0, false, false, false));
                    return true;   // the chains are drawn by fx/phantom_trap_snare.json
                }
            });
        }
        super.onCast(level, spellLevel, caster, source, md);
    }
}
