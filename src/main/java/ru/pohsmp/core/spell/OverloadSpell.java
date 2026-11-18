package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.registry.SchoolRegistry;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.spells.SpellRarity;
import io.redspace.ironsspellbooks.api.util.Utils;
import java.util.List;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.Level;
import ru.pohsmp.core.DivineEvents;
import ru.pohsmp.core.Reg;

/** Lightning: a 3 s mark stores all damage the target takes, then discharges a share of it into the target and everyone near. */
public class OverloadSpell extends PohSpell {
    public static final String PATH = "overload";
    private static final int TICKS = 60;

    public OverloadSpell() {
        super(PATH, SchoolRegistry.LIGHTNING_RESOURCE, SpellRarity.UNCOMMON, 6, 14, 0, 30, 6);
    }

    @Override public CastType getCastType() { return CastType.INSTANT; }

    private double share(int l) { return lv(l, 0.5, 1.0); }
    private double base(int l, LivingEntity c) { return lv(l, 2, 6) * mult(c); }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("share", (int) Math.round(share(level) * 100), TICKS / 20), ui("base", n(base(level, caster))));
    }

    @Override
    public boolean checkPreCastConditions(Level level, int spellLevel, LivingEntity entity, MagicData md) {
        return Utils.preCastTargetHelper(level, entity, md, this, 24, 0.35f);
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            LivingEntity t = HigherSpell.target(sl, md);
            if (t != null && t.isAlive()) {
                Marks.put(Marks.OVERLOAD, this, caster, t, TICKS, share(spellLevel), base(spellLevel, caster));
                t.addEffect(new MobEffectInstance(Reg.OVERLOAD.get(), TICKS, 0, false, true, true));
                sl.playSound(null, t.getX(), t.getY(), t.getZ(), SoundEvents.BEACON_POWER_SELECT, SoundSource.PLAYERS, 1.2f, 1.8f);
                DivineEvents.particle(sl, ParticleTypes.ELECTRIC_SPARK, t.getX(), t.getY() + 1, t.getZ(), 30, 0.5, 0.1);
            }
        }
        super.onCast(level, spellLevel, caster, source, md);
    }
}
