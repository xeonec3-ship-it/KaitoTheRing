package ru.pohsmp.core;

import com.google.common.collect.ImmutableMultimap;
import com.google.common.collect.Multimap;
import io.redspace.ironsspellbooks.api.registry.AttributeRegistry;
import io.redspace.ironsspellbooks.item.weapons.StaffItem;
import io.redspace.ironsspellbooks.item.weapons.StaffTier;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.ai.attributes.Attribute;
import net.minecraft.world.entity.ai.attributes.AttributeModifier;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.Rarity;

import java.nio.charset.StandardCharsets;
import java.util.UUID;
import java.util.function.Supplier;

/**
 * School staff: Iron's staff (cast pose, enchantable) with main-hand bonuses
 * school spell power, general spell power and mana regen (all MULTIPLY_BASE, like Iron's staffs).
 * Bonuses are built on first request, so attribute registration order does not matter.
 */
public class PohStaff extends StaffItem {
    private final Supplier<Attribute> school;
    private final double schoolPct, powerPct, regenPct;
    private Multimap<Attribute, AttributeModifier> mainHand;

    public PohStaff(Supplier<Attribute> school, double schoolPct, double powerPct, double regenPct) {
        super(new Item.Properties().stacksTo(1).rarity(Rarity.EPIC), new StaffTier(3f, -3f));
        this.school = school;
        this.schoolPct = schoolPct;
        this.powerPct = powerPct;
        this.regenPct = regenPct;
    }

    private static AttributeModifier mod(String key, double v) {
        UUID id = UUID.nameUUIDFromBytes(("pohsmp_core:staff/" + key).getBytes(StandardCharsets.UTF_8));
        return new AttributeModifier(id, "pohsmp staff " + key, v, AttributeModifier.Operation.MULTIPLY_BASE);
    }

    @Override
    public Multimap<Attribute, AttributeModifier> getDefaultAttributeModifiers(EquipmentSlot slot) {
        Multimap<Attribute, AttributeModifier> base = super.getDefaultAttributeModifiers(slot);
        if (slot != EquipmentSlot.MAINHAND) return base;
        if (mainHand == null) {
            ImmutableMultimap.Builder<Attribute, AttributeModifier> b = ImmutableMultimap.builder();
            b.putAll(base);
            if (school != null && schoolPct != 0) b.put(school.get(), mod("school", schoolPct));
            if (powerPct != 0) b.put(AttributeRegistry.SPELL_POWER.get(), mod("power", powerPct));
            if (regenPct != 0) b.put(AttributeRegistry.MANA_REGEN.get(), mod("regen", regenPct));
            mainHand = b.build();
        }
        return mainHand;
    }
}
