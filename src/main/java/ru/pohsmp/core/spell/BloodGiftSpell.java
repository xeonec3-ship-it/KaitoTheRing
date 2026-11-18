package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.registry.SchoolRegistry;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.spells.SpellRarity;
import io.redspace.ironsspellbooks.api.util.Utils;
import java.util.List;
import net.minecraft.core.particles.DustParticleOptions;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import org.joml.Vector3f;
import ru.pohsmp.core.DivineEvents;

/** Blood: the caster gives its own health to the target (never below 1 HP). Works on anyone. */
public class BloodGiftSpell extends PohSpell {
    public static final String PATH = "blood_gift";
    private static final DustParticleOptions RED = new DustParticleOptions(new Vector3f(0.75f, 0.05f, 0.1f), 1.2f);

    public BloodGiftSpell() {
        super(PATH, SchoolRegistry.BLOOD_RESOURCE, SpellRarity.COMMON, 6, 8, 0, 20, 5);
    }

    @Override public CastType getCastType() { return CastType.INSTANT; }

    private double amount(int level, LivingEntity caster) {
        return lv(level, 4, 14) * mult(caster);
    }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("amount", n(amount(level, caster))), ui("floor"));
    }

    @Override
    public boolean checkPreCastConditions(Level level, int spellLevel, LivingEntity entity, MagicData md) {
        return Utils.preCastTargetHelper(level, entity, md, this, 16, 0.35f);
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            LivingEntity t = HigherSpell.target(sl, md);
            if (t != null && t.isAlive() && t != caster) {
                float give = (float) Math.min(amount(spellLevel, caster), caster.getHealth() - 1);
                if (give > 0) {
                    caster.setHealth(caster.getHealth() - give);
                    t.heal(give);
                    Vec3 a = caster.position().add(0, caster.getBbHeight() * 0.6, 0), b = t.position().add(0, t.getBbHeight() * 0.6, 0);
                    int steps = (int) (a.distanceTo(b) * 3) + 1;
                    for (int i = 0; i <= steps; i++) {
                        Vec3 p = a.lerp(b, i / (double) steps);
                        DivineEvents.particle(sl, RED, p.x, p.y + Math.sin(i * 0.6) * 0.15, p.z, 1, 0.03, 0);
                    }
                    DivineEvents.particle(sl, RED, b.x, b.y, b.z, 20, 0.4, 0);
                    sl.playSound(null, t.getX(), t.getY(), t.getZ(), SoundEvents.HONEY_DRINK, SoundSource.PLAYERS, 1f, 0.6f);
                    sl.playSound(null, caster.getX(), caster.getY(), caster.getZ(), SoundEvents.PLAYER_HURT_SWEET_BERRY_BUSH, SoundSource.PLAYERS, 0.8f, 0.7f);
                }
            }
        }
        super.onCast(level, spellLevel, caster, source, md);
    }
}
