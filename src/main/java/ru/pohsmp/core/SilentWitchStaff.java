package ru.pohsmp.core;

import io.redspace.ironsspellbooks.api.spells.AbstractSpell;
import io.redspace.ironsspellbooks.api.spells.IPresetSpellContainer;
import io.redspace.ironsspellbooks.api.spells.ISpellContainer;
import io.redspace.ironsspellbooks.api.spells.ISpellContainerMutable;
import io.redspace.ironsspellbooks.api.spells.SpellData;
import java.util.List;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.level.Level;
import net.minecraftforge.registries.RegistryObject;

/**
 * Staff of the Silent Witch ("Silent" school, T18): five locked slots from the start - Gate (T03), Wind Spears, Silent Volley,
 * Barrier, Black Flame of Worgan (T20); chosen with Iron's spell wheel, cast from the hand with Iron's cast key.
 * Bonuses: +25% Silent spell power, +10% spell power, +25% mana regen.
 * Drawn by GeckoLib (geo/item/silent_witch_staff.geo.json from tools/gen_silent_staff.py): "idle" sways the head parts,
 * "cast" lights the sphere and spins the ring, "flash" bursts the sphere (driven by the generic staff cast tracker).
 */
public class SilentWitchStaff extends AnimatedStaff implements IPresetSpellContainer {
    public static final String NAME = "silent_witch_staff";

    public SilentWitchStaff() {
        super(NAME, Reg.SILENT_POWER, 0.25, 0.10, 0.25);
        fallbackModel = "divine_staff";   // until tools/gen_silent_staff.py output is in the branch
    }

    private static ISpellContainer preset() {
        List<RegistryObject<AbstractSpell>> spells = Reg.SILENT_STAFF_SPELLS;
        ISpellContainerMutable m = ISpellContainer.create(spells.size(), true, false).mutableCopy();
        for (RegistryObject<AbstractSpell> s : spells) m.addSpell(s.get(), 1, true);
        return m.toImmutable();
    }

    /** Whether the stack holds exactly the staff's slots in order (an older staff may miss one added later). */
    private static boolean matches(ItemStack stack) {
        if (!ISpellContainer.isSpellContainer(stack)) return false;
        ISpellContainer c = ISpellContainer.get(stack);
        List<RegistryObject<AbstractSpell>> spells = Reg.SILENT_STAFF_SPELLS;
        if (c.getMaxSpellCount() != spells.size()) return false;
        for (int i = 0; i < spells.size(); i++) {
            SpellData sd = c.getSpellAtIndex(i);
            if (sd == null || sd.getSpell() != spells.get(i).get()) return false;
        }
        return true;
    }

    @Override
    public void initializeSpellContainer(ItemStack stack) {
        if (stack == null || ISpellContainer.isSpellContainer(stack)) return;
        ISpellContainer.set(stack, preset());
    }

    /** Server, once a second: brings the slots of an old staff up to the current list. */
    @Override
    public void inventoryTick(ItemStack stack, Level level, Entity holder, int slot, boolean selected) {
        super.inventoryTick(stack, level, holder, slot, selected);
        if (level.isClientSide || holder.tickCount % 20 != 0 || matches(stack)) return;
        ISpellContainer.set(stack, preset());
    }

    @Override
    public void appendHoverText(ItemStack stack, Level level, List<Component> tip, TooltipFlag flag) {
        super.appendHoverText(stack, level, tip, flag);
        int rgb = Tier.UNKNOWN.colorAt(System.currentTimeMillis());
        tip.add(Component.translatable("tooltip.irons_spellbooks.rarity", Component.translatable(Tier.UNKNOWN.langKey())).withStyle(s -> s.withColor(rgb)));
    }
}
