package ru.pohsmp.core.spell.illusion;

import io.redspace.ironsspellbooks.api.spells.SpellRarity;
import java.util.function.Supplier;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.common.ForgeConfigSpec;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.fx.Fx;
import ru.pohsmp.core.fx.FxLib;
import ru.pohsmp.core.spell.PohSpell;

/**
 * T22: a spell of the Illusions school. Ordinary ones grow by Iron's levels like any school spell; Higher and Mythic ones are level 1,
 * Legendary for Iron's (the tier comes from Reg.HIGHER_SPELLS / MYTHIC_SPELLS), no mana, no cooldown, not crafted (admins give the scrolls).
 * Mana and cooldown of the ordinary ones come from the [illusion] section of the server config.
 */
public abstract class IllusionBase extends PohSpell {
    public enum Rank { COMMON, HIGHER, MYTHIC }

    public static final int COLOR = Reg.ILLUSION_COLOR;

    protected final Rank rank;
    private final ForgeConfigSpec.IntValue manaCfg;
    private final ForgeConfigSpec.DoubleValue cooldownCfg;

    /** Ordinary spell: levels 1..maxLevel from minRarity. */
    protected IllusionBase(String path, SpellRarity minRarity, int maxLevel, int castTicks,
                           ForgeConfigSpec.IntValue manaCfg, ForgeConfigSpec.DoubleValue cooldownCfg) {
        super(path, Reg.ILLUSION_ID, minRarity, maxLevel, cfg(cooldownCfg::getDefault, 10.0), castTicks, cfg(manaCfg::getDefault, 50), 0);
        this.rank = Rank.COMMON;
        this.manaCfg = manaCfg;
        this.cooldownCfg = cooldownCfg;
    }

    /** Higher or Mythic spell. */
    protected IllusionBase(String path, Rank rank, int castTicks) {
        this(path, rank, castTicks, Reg.ILLUSION_ID);
    }

    /** Higher or Mythic spell of another school that works on the same rules (T25 «Кошмары»). */
    protected IllusionBase(String path, Rank rank, int castTicks, net.minecraft.resources.ResourceLocation school) {
        super(path, school, SpellRarity.LEGENDARY, 1, 0, castTicks, 0, 0);
        this.rank = rank;
        this.manaCfg = null;
        this.cooldownCfg = null;
    }

    public static <T> T cfg(Supplier<T> v, T def) {
        try {
            T t = v.get();
            return t == null ? def : t;
        } catch (RuntimeException e) {
            return def;
        }
    }

    @Override public boolean allowCrafting() { return rank == Rank.COMMON; }
    @Override public int getManaCost(int level) { return manaCfg == null ? 0 : cfg(manaCfg::get, manaCfg.getDefault()); }
    @Override public int getSpellCooldown() { return cooldownCfg == null ? 0 : (int) Math.round(cfg(cooldownCfg::get, cooldownCfg.getDefault()) * 20); }

    /** Time (seconds in the config) in ticks. */
    protected static int ticks(ForgeConfigSpec.DoubleValue seconds) {
        return (int) Math.round(cfg(seconds::get, seconds.getDefault()) * 20);
    }

    protected static double d(ForgeConfigSpec.DoubleValue v) {
        return cfg(v::get, v.getDefault());
    }

    protected static int i(ForgeConfigSpec.IntValue v) {
        return cfg(v::get, v.getDefault());
    }

    /** Data effect fx/&lt;id&gt;.json if it is in the mod; -1 otherwise. */
    public static int fx(ServerLevel sl, Fx.Spec spec, String id) {
        if (FxLib.fx(id) == null) return -1;
        return Fx.play(sl, spec);
    }

    public static int fx(ServerLevel sl, String id, Vec3 at, LivingEntity caster) {
        return fx(sl, Fx.fx(id).at(at).caster(caster), id);
    }

    /** The caster's spell power for this school x base. */
    protected double power(LivingEntity caster, double base) {
        return base * mult(caster);
    }
}
