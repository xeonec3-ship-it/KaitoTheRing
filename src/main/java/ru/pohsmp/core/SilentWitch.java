package ru.pohsmp.core;

import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.Items;
import net.minecraftforge.registries.ForgeRegistries;

/**
 * Silent Witch's staff (T18) and outfit (T19), checked by item id.
 * STUB until T18/T19 are done: an item that is not registered yet counts as present, so "Gate" can already be cast
 * (and tested) without them. As soon as items with these ids exist, the checks become real with no code change here.
 */
public final class SilentWitch {
    private SilentWitch() {}

    public static final ResourceLocation STAFF = new ResourceLocation(PohCore.MODID, "silent_witch_staff");
    public static final ResourceLocation HOOD = new ResourceLocation(PohCore.MODID, "silent_witch_hood");
    public static final ResourceLocation ROBE = new ResourceLocation(PohCore.MODID, "silent_witch_robe");
    public static final ResourceLocation SKIRT = new ResourceLocation(PohCore.MODID, "silent_witch_skirt");

    /** The item, or null while it is not registered (T18/T19 not done yet). */
    private static Item item(ResourceLocation id) {
        Item it = ForgeRegistries.ITEMS.getValue(id);
        return it == null || it == Items.AIR ? null : it;
    }

    /** True when the staff item exists (T18 done) - otherwise the staff check is a stub. */
    public static boolean staffExists() {
        return item(STAFF) != null;
    }

    /** True when all three outfit pieces exist (T19 done) - otherwise the outfit check is a stub. */
    public static boolean outfitExists() {
        return item(HOOD) != null && item(ROBE) != null && item(SKIRT) != null;
    }

    /** Staff of the Silent Witch in the main hand (stub: true while the staff is not registered). */
    public static boolean hasStaff(LivingEntity e) {
        Item staff = item(STAFF);
        return staff == null || e.getMainHandItem().is(staff);
    }

    /** Hood, robe and skirt all worn (stub: a piece that is not registered yet counts as worn). */
    public static boolean hasFullSet(LivingEntity e) {
        return worn(e, EquipmentSlot.HEAD, HOOD) && worn(e, EquipmentSlot.CHEST, ROBE) && worn(e, EquipmentSlot.LEGS, SKIRT);
    }

    private static boolean worn(LivingEntity e, EquipmentSlot slot, ResourceLocation id) {
        Item it = item(id);
        return it == null || e.getItemBySlot(slot).is(it);
    }
}
