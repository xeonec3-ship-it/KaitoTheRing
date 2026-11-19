package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import java.util.List;
import java.util.Optional;
import net.minecraft.core.particles.DustParticleOptions;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import org.joml.Vector3f;
import ru.pohsmp.core.DivineEvents;
import ru.pohsmp.core.fx.Fx;

/** Higher: a crimson moon hangs over the caster for 20 s; enemies within 16 lose 1% of max health each second, the caster heals by the sum. */
public class BloodMoonSpell extends HigherSpell {
    public static final String PATH = "blood_moon";
    private static final int LIFE = 400;
    private static final double R = 16, PCT = 0.01;
    public static final int COLOR = 0xD0101E;
    private static final DustParticleOptions RED = new DustParticleOptions(new Vector3f(0.75f, 0.02f, 0.06f), 1.4f);

    public BloodMoonSpell() {
        super(PATH, 0);
    }

    @Override public CastType getCastType() { return CastType.INSTANT; }
    @Override public Optional<SoundEvent> getCastStartSound() { return Optional.empty(); }
    @Override public Optional<SoundEvent> getCastFinishSound() { return Optional.of(SoundEvents.WITHER_SPAWN); }

    @Override
    public List<MutableComponent> getUniqueInfo(int spellLevel, LivingEntity caster) {
        return List.of(ui("drain", num(PCT * 100), (int) R), ui("time", LIFE / 20), ui("heal"));
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            int k = Fx.play(sl, Fx.fx("blood_moon").caster(caster).duration(LIFE));   // red moon overhead, blood seal underfoot, world turns red
            Tasks.add(new Tasks.Task() {
                int age;

                @Override
                public boolean tick() {
                    age++;
                    if (!caster.isAlive() || caster.isRemoved()) {
                        Fx.stop(sl, k, "");
                        return false;
                    }
                    Vec3 c = caster.position();
                    if (age % 4 == 0)
                        for (int i = 0; i < 8; i++) {
                            double a = sl.random.nextDouble() * Math.PI * 2, r = 2 + sl.random.nextDouble() * (R - 2);
                            DivineEvents.particle(sl, RED, c.x + Math.cos(a) * r, c.y + 0.2 + sl.random.nextDouble() * 3, c.z + Math.sin(a) * r, 1, 0, 0);
                        }
                    if (age % 20 == 0) {
                        float sum = 0;
                        int threads = 0;
                        for (LivingEntity e : around(sl, c, R, e -> !friendly(caster, e))) {
                            float before = e.getHealth();
                            hurt(sl, caster, e, dmg(e.getMaxHealth() * PCT));
                            float lost = Math.max(0, before - e.getHealth());
                            sum += lost;
                            if (lost > 0 && threads++ < 8)   // a thread of blood to the caster
                                Fx.play(sl, Fx.fx("blood_drain").at(e.position()).caster(caster).target(e));
                        }
                        if (sum > 0) caster.heal(sum);
                        sl.playSound(null, c.x, c.y, c.z, SoundEvents.WARDEN_HEARTBEAT, SoundSource.PLAYERS, 2f, 0.6f);
                    }
                    return age < LIFE;
                }
            });
        }
        super.onCast(level, spellLevel, caster, source, md);
    }
}
