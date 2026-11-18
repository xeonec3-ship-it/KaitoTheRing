package ru.pohsmp.core;

import java.util.List;
import net.minecraft.world.effect.MobEffect;
import net.minecraft.world.effect.MobEffectCategory;
import net.minecraft.world.item.ItemStack;

/** Plain effect of this mod: logic lives in event handlers, attribute modifiers are added at registration. Milk does not remove it. */
public class PohEffect extends MobEffect {
    public PohEffect(MobEffectCategory cat, int color) {
        super(cat, color);
    }

    @Override
    public List<ItemStack> getCurativeItems() {
        return List.of();
    }
}
