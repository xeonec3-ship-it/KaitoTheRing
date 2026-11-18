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

/**
 * Staff of Downfall (Forbidden school): holds "Downfall" from the start (locked slot, cast from the hand with Iron's cast key).
 * Drawn by GeckoLib: the quasar spins in "idle", grows in "cast", bursts in "flash" (triggered by the Downfall spell itself).
 */
public class DownfallStaff extends AnimatedStaff implements IPresetSpellContainer {
    public DownfallStaff() {
        super("downfall_staff", Reg.FORBIDDEN_POWER, 0.25, 0.10, 0.25);
    }

    @Override
    protected boolean autoAnim() {
        return false;
    }

    @Override
    public void initializeSpellContainer(ItemStack stack) {
        if (stack == null || ISpellContainer.isSpellContainer(stack)) return;
        ISpellContainerMutable m = ISpellContainer.create(1, true, false).mutableCopy();
        m.addSpell(Reg.DOWNFALL.get(), 1, true);
        ISpellContainer.set(stack, m.toImmutable());
    }

    @Override
    public void appendHoverText(ItemStack stack, Level level, List<Component> tip, TooltipFlag flag) {
        super.appendHoverText(stack, level, tip, flag);
        int rgb = Tier.CREATION.colorAt(System.currentTimeMillis());
        tip.add(Component.translatable("tooltip.irons_spellbooks.rarity", Component.translatable(Tier.CREATION.langKey())).withStyle(s -> s.withColor(rgb)));
    }

    /** Server: play "cast", "flash" or stop the triggered one (anim null) - only for the Downfall staff. */
    public static void anim(LivingEntity holder, String anim) {
        if (holder.getMainHandItem().getItem() instanceof DownfallStaff) AnimatedStaff.play(holder, anim);
    }
}
