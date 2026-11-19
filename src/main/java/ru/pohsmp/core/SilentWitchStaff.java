package ru.pohsmp.core;

import io.redspace.ironsspellbooks.api.spells.IPresetSpellContainer;
import io.redspace.ironsspellbooks.api.spells.ISpellContainer;
import io.redspace.ironsspellbooks.api.spells.ISpellContainerMutable;
import java.util.List;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.level.Level;
import net.minecraftforge.registries.RegistryObject;

/**
 * Staff of the Silent Witch (T18): Silent school, "Unknown" tier. Holds the staff spells in locked slots from the start
 * (Iron's spell wheel, cast from the hand with Iron's cast key): Wind Spears, Silent Volley, Barrier, Black Flame of Worgan (T20).
 * "Gate" (T03) becomes the first slot when it is made. +25% Silent spell power, +10% spell power, +25% mana regen.
 * Model, animations and textures (geo/animations/textures silent_witch_staff) come from the ideas chat; until then a stand-in.
 */
public class SilentWitchStaff extends AnimatedStaff implements IPresetSpellContainer {
    public SilentWitchStaff() {
        super("silent_witch_staff", Reg.SILENT_POWER, 0.25, 0.10, 0.25);
    }

    private static List<RegistryObject<io.redspace.ironsspellbooks.api.spells.AbstractSpell>> spells() {
        return List.of(Reg.WIND_SPEARS, Reg.SILENT_VOLLEY, Reg.SAGE_BARRIER, Reg.WORGAN_FLAME);
    }

    /** The staff in either hand. */
    public static boolean holds(LivingEntity e) {
        return e != null && (e.getMainHandItem().getItem() instanceof SilentWitchStaff || e.getOffhandItem().getItem() instanceof SilentWitchStaff);
    }

    @Override
    public void initializeSpellContainer(ItemStack stack) {
        if (stack == null) return;
        var list = spells();
        if (ISpellContainer.isSpellContainer(stack) && ISpellContainer.get(stack).getMaxSpellCount() >= list.size()) return;
        ISpellContainerMutable m = ISpellContainer.create(list.size(), true, false).mutableCopy();
        for (var s : list) m.addSpell(s.get(), 1, true);
        ISpellContainer.set(stack, m.toImmutable());
    }

    @Override
    public void appendHoverText(ItemStack stack, Level level, List<Component> tip, TooltipFlag flag) {
        super.appendHoverText(stack, level, tip, flag);
        int rgb = Tier.UNKNOWN.colorAt(System.currentTimeMillis());
        tip.add(Component.translatable("tooltip.irons_spellbooks.rarity", Component.translatable(Tier.UNKNOWN.langKey())).withStyle(s -> s.withColor(rgb)));
    }
}
