package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.registry.SchoolRegistry;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.spells.SpellRarity;
import io.redspace.ironsspellbooks.api.util.Utils;
import java.util.List;
import net.minecraft.core.particles.DustParticleOptions;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.MobType;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import org.joml.Vector3f;
import ru.pohsmp.core.DivineEvents;
import ru.pohsmp.core.Reg;

/** Holy: a circle of light marks the target, a second later a beam strikes it from the sky. Undead take double. */
public class JudgementSpell extends PohSpell {
    public static final String PATH = "judgement";
    private static final int DELAY = 20;
    private static final DustParticleOptions GOLD = new DustParticleOptions(new Vector3f(1f, 0.92f, 0.55f), 2f);

    public JudgementSpell() {
        super(PATH, SchoolRegistry.HOLY_RESOURCE, SpellRarity.COMMON, 6, 10, 0, 30, 6);
    }

    @Override public CastType getCastType() { return CastType.INSTANT; }

    private double damage(int l, LivingEntity c) { return lv(l, 8, 20) * mult(c); }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("damage", n(damage(level, caster))), ui("undead"));
    }

    @Override
    public boolean checkPreCastConditions(Level level, int spellLevel, LivingEntity entity, MagicData md) {
        return Utils.preCastTargetHelper(level, entity, md, this, 32, 0.35f);
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            LivingEntity t = HigherSpell.target(sl, md);
            if (t != null && t.isAlive()) {
                float dmg = (float) damage(spellLevel, caster);
                sl.playSound(null, t.getX(), t.getY(), t.getZ(), SoundEvents.BELL_RESONATE, SoundSource.PLAYERS, 1.2f, 1.6f);
                Tasks.add(new Tasks.Task() {
                    int age;

                    @Override
                    public boolean tick() {
                        age++;
                        if (!t.isAlive()) return false;
                        Vec3 c = t.position();
                        double r = 1.6 - 0.9 * age / DELAY;
                        for (int i = 0; i < 14; i++) {
                            double a = i * Math.PI / 7 + age * 0.15;
                            DivineEvents.particle(sl, GOLD, c.x + Math.cos(a) * r, c.y + 0.1, c.z + Math.sin(a) * r, 1, 0, 0);
                        }
                        if (age % 4 == 0) DivineEvents.particle(sl, ParticleTypes.END_ROD, c.x, c.y + 12, c.z, 4, 0.3, 0.02);
                        if (age < DELAY) return true;
                        for (double y = 0; y < 24; y += 0.5) {
                            DivineEvents.particle(sl, ParticleTypes.END_ROD, c.x, c.y + y, c.z, 2, 0.25, 0.01);
                            DivineEvents.particle(sl, GOLD, c.x, c.y + y, c.z, 2, 0.35, 0);
                        }
                        DivineEvents.particle(sl, ParticleTypes.FLASH, c.x, c.y + 1, c.z, 1, 0, 0);
                        HigherSpell.burst(sl, c.x, c.y + 0.1, c.z, 2.5, 0xFFE9A0);
                        sl.playSound(null, c.x, c.y, c.z, SoundEvents.TRIDENT_THUNDER, SoundSource.PLAYERS, 2f, 1.3f);
                        sl.playSound(null, c.x, c.y, c.z, SoundEvents.BEACON_POWER_SELECT, SoundSource.PLAYERS, 2f, 1.8f);
                        hit(caster, t, t.getMobType() == MobType.UNDEAD ? dmg * 2 : dmg);
                        return false;
                    }
                });
            }
        }
        super.onCast(level, spellLevel, caster, source, md);
    }
}
