package ru.pohsmp.core.trophy;

import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.world.item.ArmorItem;
import net.minecraft.world.item.ArmorMaterial;
import net.minecraft.world.item.crafting.Ingredient;
import ru.pohsmp.core.PohCore;

/** Netherite durability, a little more armor than netherite, no repair material (only Mending mends it). */
public final class TrophyMaterial implements ArmorMaterial {
    private final TrophySet set;

    TrophyMaterial(TrophySet set) {
        this.set = set;
    }

    @Override
    public int getDurabilityForType(ArmorItem.Type type) {
        return new int[] {13, 15, 16, 11}[type.getSlot().getIndex()] * 37;   // netherite: multiplier 37
    }

    @Override
    public int getDefenseForType(ArmorItem.Type type) {
        return set.defense[TrophySet.index(type)];
    }

    @Override
    public int getEnchantmentValue() {
        return 15;   // netherite
    }

    @Override
    public SoundEvent getEquipSound() {
        return SoundEvents.ARMOR_EQUIP_NETHERITE;
    }

    @Override
    public Ingredient getRepairIngredient() {
        return Ingredient.EMPTY;
    }

    @Override
    public String getName() {
        return PohCore.MODID + ":" + set.id;
    }

    @Override
    public float getToughness() {
        return set.toughness;
    }

    @Override
    public float getKnockbackResistance() {
        return set.knockback;
    }
}
