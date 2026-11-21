package ru.pohsmp.core;

import io.redspace.ironsspellbooks.api.registry.SpellRegistry;
import io.redspace.ironsspellbooks.api.spells.AbstractSpell;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.core.registries.Registries;
import net.minecraft.world.item.CreativeModeTab;
import net.minecraft.world.item.ItemStack;
import net.minecraftforge.event.BuildCreativeModeTabContentsEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/**
 * Owner 21.11: our spell scrolls leave Iron's "Scrolls" tab and live in our own tab, every level of every spell.
 * Iron's tab lists every enabled spell at every level; here its entries holding one of our spells are removed.
 * Our tab gets the scrolls from {@link #ourScrolls()}: the tier lists first (as the tab had them), then every other spell of ours.
 */
@Mod.EventBusSubscriber(modid = PohCore.MODID, bus = Mod.EventBusSubscriber.Bus.MOD)
public final class ScrollTab {
    private ScrollTab() {}

    static final ResourceKey<CreativeModeTab> IRONS_SCROLLS =
            ResourceKey.create(Registries.CREATIVE_MODE_TAB, new ResourceLocation("irons_spellbooks", "spellbook_scrolls"));

    @SubscribeEvent
    public static void onBuild(BuildCreativeModeTabContentsEvent e) {
        if (!e.getTabKey().equals(IRONS_SCROLLS)) return;
        List<ItemStack> ours = new ArrayList<>();
        for (Map.Entry<ItemStack, CreativeModeTab.TabVisibility> en : e.getEntries()) {
            if (NoLoot.ours(en.getKey())) ours.add(en.getKey());
        }
        for (ItemStack s : ours) e.getEntries().remove(s);
    }

    /** Full ids of our spells in tab order: the tier lists, then the rest of ours by id. Item-only spells are left out. */
    static List<String> orderedSpellIds() {
        Set<String> ids = new LinkedHashSet<>();
        for (String p : Reg.COMMON_SPELLS) ids.add(PohCore.MODID + ":" + p);
        for (String p : Reg.HIGHER_SPELLS) ids.add(PohCore.MODID + ":" + p);
        ids.add(ru.pohsmp.core.spell.DisintegrationSpell.ID.toString());
        for (String p : Reg.MYTHIC_SPELLS) ids.add(PohCore.MODID + ":" + p);
        for (String p : Reg.DIVINE_SPELLS) ids.add(PohCore.MODID + ":" + p);
        List<String> rest = new ArrayList<>();
        for (AbstractSpell s : SpellRegistry.getEnabledSpells()) {
            String id = s.getSpellId();
            if (id.startsWith(PohCore.MODID + ":") && !ids.contains(id)) rest.add(id);
        }
        rest.sort(null);
        ids.addAll(rest);
        ids.removeIf(ru.pohsmp.core.spell.MagicRules::itemOnly);
        return new ArrayList<>(ids);
    }

    /** Every level (min..max) of every scroll of ours, in tab order. */
    static List<ItemStack> ourScrolls() {
        List<ItemStack> out = new ArrayList<>();
        for (String id : orderedSpellIds()) {
            AbstractSpell s = SpellRegistry.getSpell(id);
            if (s == null || s == SpellRegistry.none() || !s.isEnabled()) continue;
            ResourceLocation rl = new ResourceLocation(id);
            for (int lvl = s.getMinLevel(); lvl <= s.getMaxLevel(); lvl++) {
                ItemStack st = Scrolls.make(rl, lvl, null);
                if (!st.isEmpty()) out.add(st);
            }
        }
        return out;
    }
}
