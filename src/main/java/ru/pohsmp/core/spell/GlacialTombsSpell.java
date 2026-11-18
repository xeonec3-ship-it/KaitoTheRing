package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.registry.SchoolRegistry;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.spells.SpellRarity;
import io.redspace.ironsspellbooks.entity.spells.ice_tomb.IceTombEntity;
import java.util.List;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.Level;
import ru.pohsmp.core.DivineEvents;

/** Ice: everyone around the caster (not the caster, its allies and pets) is locked in an ice tomb. */
public class GlacialTombsSpell extends PohSpell {
    public static final String PATH = "glacial_tombs";

    public GlacialTombsSpell() {
        super(PATH, SchoolRegistry.ICE_RESOURCE, SpellRarity.UNCOMMON, 6, 25, 0, 50, 10);
    }

    @Override public CastType getCastType() { return CastType.INSTANT; }

    private double radius(int l) { return lv(l, 4, 9); }
    private int ticks(int l) { return (int) (lv(l, 2, 5) * 20); }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("radius", n(radius(level))), ui("time", n(ticks(level) / 20.0)));
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            double r = radius(spellLevel);
            int dur = ticks(spellLevel);
            for (LivingEntity t : HigherSpell.around(sl, caster.position(), r, e -> !HigherSpell.friendly(caster, e))) {
                if (t.getVehicle() instanceof IceTombEntity) continue;
                if (t.isPassenger()) t.stopRiding();
                IceTombEntity tomb = new IceTombEntity(sl, caster);
                tomb.moveTo(t.getX(), t.getY(), t.getZ(), t.getYRot(), 0);
                tomb.setLifetime(dur);
                tomb.setEvil();
                sl.addFreshEntity(tomb);
                t.startRiding(tomb, true);
                DivineEvents.particle(sl, ParticleTypes.SNOWFLAKE, t.getX(), t.getY() + 1, t.getZ(), 25, 0.6, 0.05);
            }
            int n = (int) (r * 6);
            for (int i = 0; i < n; i++) {
                double a = i * Math.PI * 2 / n;
                DivineEvents.particle(sl, ParticleTypes.SNOWFLAKE, caster.getX() + Math.cos(a) * r, caster.getY() + 0.2, caster.getZ() + Math.sin(a) * r, 2, 0.1, 0.01);
            }
            sl.playSound(null, caster.getX(), caster.getY(), caster.getZ(), SoundEvents.GLASS_BREAK, SoundSource.PLAYERS, 1.5f, 0.5f);
            sl.playSound(null, caster.getX(), caster.getY(), caster.getZ(), SoundEvents.POWDER_SNOW_PLACE, SoundSource.PLAYERS, 2f, 0.6f);
        }
        super.onCast(level, spellLevel, caster, source, md);
    }
}
