package ru.pohsmp.core;

import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraftforge.registries.ForgeRegistries;

/** Iron's scroll stacks with an arbitrary spell and level. */
public final class Scrolls {
    private Scrolls() {}

    public static ItemStack make(ResourceLocation spell, int level, String tier) {
        Item scroll = ForgeRegistries.ITEMS.getValue(new ResourceLocation("irons_spellbooks", "scroll"));
        if (scroll == null || scroll == Items.AIR) return ItemStack.EMPTY;
        ItemStack st = new ItemStack(scroll);
        CompoundTag slot = new CompoundTag();
        slot.putString("id", spell.toString());
        slot.putInt("index", 0);
        slot.putInt("level", level);
        slot.putBoolean("locked", true);
        ListTag data = new ListTag();
        data.add(slot);
        CompoundTag box = new CompoundTag();
        box.put("data", data);
        box.putInt("maxSpells", 1);
        box.putBoolean("mustEquip", false);
        box.putBoolean("spellWheel", false);
        st.getOrCreateTag().put("irons_spellbooks:spell_container", box);
        if (tier != null) st.getOrCreateTag().putString(Tier.NBT, tier);
        return st;
    }
}
