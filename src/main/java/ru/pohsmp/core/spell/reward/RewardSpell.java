package ru.pohsmp.core.spell.reward;

import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.util.AnimationHolder;
import java.util.Optional;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.Level;
import net.minecraftforge.common.Tags;
import ru.pohsmp.core.boss.BossGuard;
import ru.pohsmp.core.fx.Fx;
import ru.pohsmp.core.fx.FxLib;
import ru.pohsmp.core.spell.CastAnims;
import ru.pohsmp.core.spell.FixedCastSpell;
import ru.pohsmp.core.spell.HigherSpell;

/**
 * T34 boss reward spell: Higher school, built-in Higher tier (Reg.HIGHER_SPELLS), levels 1..3, fixed cast time (FixedCastSpell),
 * mana and cooldown (it goes into spell books). Given only by an admin: no crafting (HigherSpell), no loot (HigherSpell.allowLooting),
 * no scroll merging (MagicRules.copyBanned, mixin/ArcaneAnvilMenuMixin).
 * Player animations pohsmp_&lt;id&gt;_cast / pohsmp_&lt;id&gt;_finish (assets/irons_spellbooks/player_animation), fx &lt;id&gt; and &lt;id&gt;_*:
 * made by the visual helper; until a file exists, {@link #fx} plays the boss effect named as the fallback (or nothing).
 */
public abstract class RewardSpell extends HigherSpell implements FixedCastSpell {
    protected final String path;

    protected RewardSpell(String path, int castTicks, double cooldownSec, int baseMana, int manaPerLevel) {
        super(path, castTicks, RewardMath.MAX_LEVEL, cooldownSec, baseMana, manaPerLevel);
        this.path = path;
    }

    @Override public CastType getCastType() { return CastType.LONG; }
    @Override public AnimationHolder getCastStartAnimation() { return CastAnims.of(path + "_cast"); }
    @Override public AnimationHolder getCastFinishAnimation() { return CastAnims.of(path + "_finish"); }
    @Override public Optional<SoundEvent> getCastFinishSound() { return Optional.empty(); }

    /** Value of a level table (balance draft in RewardMath). */
    protected static double lv(double[] t, int level) {
        return RewardMath.at(t, level);
    }

    /** A cult boss (BossGuard) or any other boss (forge:bosses: the Wither, the Ender Dragon, Iron's bosses...): no pulls, no holds. */
    public static boolean bossLike(Entity e) {
        if (e == null) return false;
        if (BossGuard.isBoss(e)) return true;
        try {
            return e.getType().is(Tags.EntityTypes.BOSSES);
        } catch (RuntimeException ex) {
            return false;
        }
    }

    /** The fx `own` if its file exists, else `fallback` (a boss effect; null = nothing). No log line either way. */
    public static Fx.Spec fx(String own, String fallback) {
        if (FxLib.exists("fx/" + own + ".json")) return Fx.fx(own);
        if (fallback != null && FxLib.exists("fx/" + fallback + ".json")) return Fx.fx(fallback);
        return null;
    }

    /** Plays a spec from {@link #fx} (null = nothing), returns the instance or -1. */
    public static int play(Level level, Fx.Spec s) {
        return s != null && level instanceof ServerLevel sl ? Fx.play(sl, s) : -1;
    }

    /** Plays `own` (or the boss `fallback` until `own` is drawn) set up by `setup`; -1 if neither exists. */
    public static int play(Level level, String own, String fallback, java.util.function.UnaryOperator<Fx.Spec> setup) {
        Fx.Spec s = fx(own, fallback);
        return s == null ? -1 : play(level, setup.apply(s));
    }

    public static void stopFx(ServerLevel sl, int inst) {
        if (inst > 0) Fx.stop(sl, inst, "");
    }

    /** Someone the caster's spell may hit: alive, not the caster, its team or its pets, not a spectator / armor stand. */
    protected static boolean hittable(LivingEntity caster, LivingEntity e) {
        return e != caster && e.isAlive() && !friendly(caster, e);
    }
}
