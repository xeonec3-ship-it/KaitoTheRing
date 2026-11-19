package ru.pohsmp.core;

import io.redspace.ironsspellbooks.api.registry.SpellRegistry;
import io.redspace.ironsspellbooks.api.spells.AbstractSpell;
import io.redspace.ironsspellbooks.api.spells.ISpellContainer;
import io.redspace.ironsspellbooks.api.spells.SpellData;
import io.redspace.ironsspellbooks.item.Scroll;
import java.util.Map;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.world.item.ItemStack;
import ru.pohsmp.core.spell.DisintegrationSpell;

/**
 * Tiers above Iron's Legendary. Only a label on scrolls: Iron's itself still sees the spell as Legendary.
 * Tier comes from the "pohsmp_tier" NBT tag ("higher" / "mythic" / "divine" / "creation" / "unknown" / "none"), then from the spell's built-in tier,
 * then from how far the level is above the spell's max level (+1..2 higher, +3..4 mythic, +5 and more divine).
 */
public enum Tier {
    HIGHER("higher", 0xFF3B3B, false),
    MYTHIC("mythic", 0xB45CFF, true),
    DIVINE("divine", 0xFFD34D, true),
    CREATION("creation", 0xD4A017, true),
    /** Silent Witch staff spells (T18): no scrolls, only from the staff. */
    UNKNOWN("unknown", 0x7FFFD0, true);

    public static final String NBT = "pohsmp_tier";
    private static final Map<String, Tier> BUILTIN = builtin();

    private static Map<String, Tier> builtin() {
        Map<String, Tier> m = new java.util.HashMap<>();
        m.put(DisintegrationSpell.ID.toString(), DIVINE);
        for (String p : Reg.DIVINE_SPELLS) m.put(PohCore.MODID + ":" + p, DIVINE);
        for (String p : Reg.MYTHIC_SPELLS) m.put(PohCore.MODID + ":" + p, MYTHIC);
        for (String p : Reg.HIGHER_SPELLS) m.put(PohCore.MODID + ":" + p, HIGHER);
        for (String p : Reg.CREATION_SPELLS) m.put(PohCore.MODID + ":" + p, CREATION);
        for (String p : Reg.UNKNOWN_SPELLS) m.put(PohCore.MODID + ":" + p, UNKNOWN);
        return m;
    }

    public final String key;
    public final int color;
    public final boolean shimmer;

    Tier(String key, int color, boolean shimmer) {
        this.key = key;
        this.color = color;
        this.shimmer = shimmer;
    }

    public String langKey() {
        return "tier.pohsmp_core." + key;
    }

    /** Color for this moment: shimmering tiers pulse toward white. */
    public int colorAt(long millis) {
        if (!shimmer) return color;
        double k = 0.5 + 0.5 * Math.sin(millis / 260.0);
        k *= 0.55;
        int r = (color >> 16) & 255, g = (color >> 8) & 255, b = color & 255;
        r = (int) (r + (255 - r) * k);
        g = (int) (g + (255 - g) * k);
        b = (int) (b + (255 - b) * k);
        return (r << 16) | (g << 8) | b;
    }

    public static Tier byKey(String s) {
        for (Tier t : values()) if (t.key.equalsIgnoreCase(s)) return t;
        return null;
    }

    public static Tier of(ItemStack st) {
        if (st == null || st.isEmpty() || !(st.getItem() instanceof Scroll) || !ISpellContainer.isSpellContainer(st)) return null;
        CompoundTag tag = st.getTag();
        if (tag != null && tag.contains(NBT)) return byKey(tag.getString(NBT));
        SpellData sd = ISpellContainer.get(st).getSpellAtIndex(0);
        if (sd == null) return null;
        AbstractSpell sp = sd.getSpell();
        if (sp == null || sp == SpellRegistry.none()) return null;
        Tier b = BUILTIN.get(sp.getSpellId());
        if (b != null) return b;
        int over = sd.getLevel() - sp.getMaxLevel();
        if (over >= 5) return DIVINE;
        if (over >= 3) return MYTHIC;
        if (over >= 1) return HIGHER;
        return null;
    }

    /** Spell id stored in a scroll, or null. */
    public static String spellIdOf(ItemStack st) {
        if (st == null || st.isEmpty() || !(st.getItem() instanceof Scroll) || !ISpellContainer.isSpellContainer(st)) return null;
        SpellData sd = ISpellContainer.get(st).getSpellAtIndex(0);
        return sd == null || sd.getSpell() == null ? null : sd.getSpell().getSpellId();
    }
}
