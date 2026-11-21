package ru.pohsmp.core.trophy;

import com.google.common.collect.Multimap;
import java.util.UUID;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.ai.attributes.Attribute;
import net.minecraft.world.entity.ai.attributes.AttributeModifier;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraftforge.fml.ModList;
import top.theillusivec4.curios.api.CuriosApi;
import top.theillusivec4.curios.api.SlotContext;
import top.theillusivec4.curios.api.type.capability.ICurioItem;

/**
 * T35: Curios for the mantle ("back") and the mask ("head"); soft - every Curios class is named only inside {@link Impl}.
 * The player gets both slots from data/pohsmp_core/curios/entities/poh_trophies.json, the items are in curios:back / curios:head.
 */
public final class TrophyCurios {
    private TrophyCurios() {}

    public static final boolean ON = ModList.get().isLoaded("curios");

    /** Common setup: the mantle and the mask become curios (attributes in their slot, right-click to put on). */
    public static void setup() {
        if (ON) Impl.register();
    }

    /** True if the entity wears the item, in a Curios slot or (without Curios) in its armor slot. */
    public static boolean wears(LivingEntity e, TrophyWear item) {
        if (e == null) return false;
        if (ON && Impl.equipped(e, item)) return true;
        return e.getItemBySlot(item.kind.fallbackSlot).is(item);
    }

    /** True if the item sits in one of its Curios slots (not the armor-slot fallback). */
    public static boolean inCurio(LivingEntity e, TrophyWear item) {
        return ON && e != null && Impl.equipped(e, item);
    }

    /** The worn stack (Curios first), or empty. */
    public static ItemStack worn(LivingEntity e, TrophyWear item) {
        if (ON) {
            ItemStack s = Impl.find(e, item);
            if (!s.isEmpty()) return s;
        }
        ItemStack s = e.getItemBySlot(item.kind.fallbackSlot);
        return s.is(item) ? s : ItemStack.EMPTY;
    }

    private static final class Impl {
        static void register() {
            for (TrophyWear w : Trophies.wearables()) CuriosApi.registerCurio(w, new Curio(w));
        }

        static boolean equipped(LivingEntity e, Item item) {
            return CuriosApi.getCuriosInventory(e).map(h -> h.isEquipped(item)).orElse(false);
        }

        static ItemStack find(LivingEntity e, Item item) {
            return CuriosApi.getCuriosInventory(e).resolve().flatMap(h -> h.findFirstCurio(item)).map(r -> r.stack()).orElse(ItemStack.EMPTY);
        }
    }

    private record Curio(TrophyWear item) implements ICurioItem {
        @Override
        public Multimap<Attribute, AttributeModifier> getAttributeModifiers(SlotContext ctx, UUID uuid, ItemStack stack) {
            return item.modifiers();
        }

        @Override
        public void curioTick(SlotContext ctx, ItemStack stack) {
            if (!ctx.entity().level().isClientSide && ctx.entity().tickCount % 20 == 0) item.ensureSpell(stack);
        }

        @Override
        public boolean canEquipFromUse(SlotContext ctx, ItemStack stack) {
            return true;
        }

        @Override
        public boolean canEquip(SlotContext ctx, ItemStack stack) {
            return item.kind.curioSlot.equals(ctx.identifier()) || ctx.identifier().equals("face") && item.kind == TrophyWear.Kind.MASK;
        }
    }
}
