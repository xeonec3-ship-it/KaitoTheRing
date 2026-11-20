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
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.DivineEvents;

/** Ender: the caster and the target trade places; the target is left dizzy for a moment. */
public class SwapSpell extends PohSpell {
    public static final String PATH = "swap";

    public SwapSpell() {
        super(PATH, SchoolRegistry.ENDER_RESOURCE, SpellRarity.COMMON, 6, 12, 0, 25, 3);
    }

    @Override public CastType getCastType() { return CastType.INSTANT; }

    private double range(int l) { return lv(l, 16, 32); }
    private int dizzy(int l) { return (int) (lv(l, 1, 3) * 20); }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("range", n(range(level))), ui("dizzy", n(dizzy(level) / 20.0)));
    }

    @Override
    public boolean checkPreCastConditions(Level level, int spellLevel, LivingEntity entity, MagicData md) {
        return Utils.preCastTargetHelper(level, entity, md, this, (int) range(spellLevel), 0.35f);
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            LivingEntity t = HigherSpell.target(sl, md);
            if (t != null && t.isAlive() && t != caster && t.level() == sl && !ru.pohsmp.core.boss.BossGuard.immovable(t)) {   // cult bosses: not swapped
                if (caster.isPassenger()) caster.stopRiding();
                if (t.isPassenger()) t.stopRiding();
                Vec3 a = caster.position(), b = t.position();
                for (Vec3 p : new Vec3[]{a, b}) {
                    DivineEvents.particle(sl, ParticleTypes.PORTAL, p.x, p.y + 1, p.z, 50, 0.4, 0.4);
                    DivineEvents.particle(sl, ParticleTypes.REVERSE_PORTAL, p.x, p.y + 1, p.z, 20, 0.3, 0.05);
                }
                HigherSpell.place(caster, b.x, b.y, b.z);
                HigherSpell.place(t, a.x, a.y, a.z);
                caster.fallDistance = 0;
                t.fallDistance = 0;
                caster.resetFallDistance();
                t.addEffect(new MobEffectInstance(MobEffects.CONFUSION, dizzy(spellLevel) + 40, 0, false, false, true));
                t.addEffect(new MobEffectInstance(MobEffects.MOVEMENT_SLOWDOWN, dizzy(spellLevel), 1, false, false, true));
                if (t instanceof Mob m) m.getNavigation().stop();
                sl.playSound(null, a.x, a.y, a.z, SoundEvents.ENDERMAN_TELEPORT, SoundSource.PLAYERS, 1.2f, 1.1f);
                sl.playSound(null, b.x, b.y, b.z, SoundEvents.ENDERMAN_TELEPORT, SoundSource.PLAYERS, 1.2f, 0.8f);
            }
        }
        super.onCast(level, spellLevel, caster, source, md);
    }
}
