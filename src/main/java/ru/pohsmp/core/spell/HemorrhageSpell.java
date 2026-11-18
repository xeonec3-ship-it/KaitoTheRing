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

/** Blood: the target bleeds; every block it moves hurts it. Standing still does not. */
public class HemorrhageSpell extends PohSpell {
    public static final String PATH = "hemorrhage";

    public HemorrhageSpell() {
        super(PATH, SchoolRegistry.BLOOD_RESOURCE, SpellRarity.COMMON, 6, 14, 0, 30, 5);
    }

    @Override public CastType getCastType() { return CastType.INSTANT; }

    private double perBlock(int l, LivingEntity c) { return lv(l, 0.5, 1.5) * mult(c); }
    private int seconds(int l) { return (int) Math.round(lv(l, 6, 12)); }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("damage", n(perBlock(level, caster))), ui("time", seconds(level)));
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
                Marks.put(Marks.HEMORRHAGE, this, caster, t, ticks, perBlock(spellLevel, caster), 0);
                t.addEffect(new MobEffectInstance(Reg.HEMORRHAGE.get(), ticks, 0, false, true, true));
                sl.playSound(null, t.getX(), t.getY(), t.getZ(), SoundEvents.PLAYER_HURT_SWEET_BERRY_BUSH, SoundSource.PLAYERS, 1.5f, 0.6f);
                DivineEvents.particle(sl, Marks.BLOOD, t.getX(), t.getY() + 1, t.getZ(), 25, 0.4, 0);
            }
        }
        super.onCast(level, spellLevel, caster, source, md);
    }
}
