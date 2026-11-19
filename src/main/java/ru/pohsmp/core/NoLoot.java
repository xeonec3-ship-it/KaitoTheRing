package ru.pohsmp.core;

import com.google.common.base.Suppliers;
import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import io.redspace.ironsspellbooks.api.spells.ISpellContainer;
import io.redspace.ironsspellbooks.api.spells.SpellData;
import it.unimi.dsi.fastutil.objects.ObjectArrayList;
import java.util.function.Supplier;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.storage.loot.LootContext;
import net.minecraft.world.level.storage.loot.predicates.LootItemCondition;
import net.minecraftforge.common.loot.IGlobalLootModifier;
import net.minecraftforge.common.loot.LootModifier;
import net.minecraftforge.registries.ForgeRegistries;

/**
 * Owner 19.11: no item of this mod may appear in a chest. A global loot modifier (data/pohsmp_core/loot_modifiers/no_loot.json)
 * takes out of every generated loot our items (staffs, armour, the blade...) and every scroll or other spell container that holds
 * one of our spells. The first wall is allowLooting() = false on all our spells (PohSpell, HigherSpell, DisintegrationSpell), so
 * Iron's random scrolls never pick them; this one catches whatever else a loot table or another mod puts in.
 */
public final class NoLoot extends LootModifier {
    public static final Supplier<Codec<NoLoot>> CODEC = Suppliers.memoize(() -> RecordCodecBuilder.create(i -> codecStart(i).apply(i, NoLoot::new)));

    public NoLoot(LootItemCondition[] conditions) {
        super(conditions);
    }

    @Override
    protected ObjectArrayList<ItemStack> doApply(ObjectArrayList<ItemStack> loot, LootContext ctx) {
        loot.removeIf(NoLoot::ours);
        return loot;
    }

    /** An item of our mod, or a spell container with one of our spells. */
    public static boolean ours(ItemStack s) {
        if (s.isEmpty()) return false;
        ResourceLocation id = ForgeRegistries.ITEMS.getKey(s.getItem());
        if (id != null && PohCore.MODID.equals(id.getNamespace())) return true;
        try {
            if (!ISpellContainer.isSpellContainer(s)) return false;
            ISpellContainer c = ISpellContainer.get(s);
            for (int i = 0; i < c.getMaxSpellCount(); i++) {
                SpellData d = c.getSpellAtIndex(i);
                if (d != null && d.getSpell() != null && d.getSpell().getSpellId().startsWith(PohCore.MODID + ":")) return true;
            }
        } catch (RuntimeException ignored) {
        }
        return false;
    }

    @Override
    public Codec<? extends IGlobalLootModifier> codec() {
        return CODEC.get();
    }
}
