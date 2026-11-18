package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.registry.SchoolRegistry;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.spells.SpellRarity;
import io.redspace.ironsspellbooks.api.util.Utils;
import java.util.List;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.Level;
import ru.pohsmp.core.DivineEvents;
import ru.pohsmp.core.Reg;

/** Blood: marks the target; everyone who hurts it heals for a share of the damage dealt. */
public class BloodMarkSpell extends PohSpell {
    public static final String PATH = "blood_mark";

    public BloodMarkSpell() {
        super(PATH, SchoolRegistry.BLOOD_RESOURCE, SpellRarity.UNCOMMON, 6, 20, 0, 35, 6);
    }

    @Override public CastType getCastType() { return CastType.INSTANT; }

    private double share(int l) { return lv(l, 0.15, 0.4); }
    private int seconds(int l) { return (int) Math.round(lv(l, 6, 16)); }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("share", (int) Math.round(share(level) * 100)), ui("time", seconds(level)));
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
                int ticks = seconds(spellLevel) * 20;
                Marks.put(Marks.BLOOD_MARK, this, caster, t, ticks, share(spellLevel), 0);
                t.addEffect(new MobEffectInstance(Reg.BLOOD_MARK.get(), ticks, 0, false, true, true));
                sl.playSound(null, t.getX(), t.getY(), t.getZ(), SoundEvents.WARDEN_HEARTBEAT, SoundSource.PLAYERS, 1.5f, 1.4f);
                DivineEvents.particle(sl, Marks.BLOOD, t.getX(), t.getY() + 1, t.getZ(), 30, 0.5, 0);
            }
        }
        super.onCast(level, spellLevel, caster, source, md);
    }
}
