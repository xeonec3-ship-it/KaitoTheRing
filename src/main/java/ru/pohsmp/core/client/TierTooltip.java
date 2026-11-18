package ru.pohsmp.core.client;

import java.util.List;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.network.chat.contents.TranslatableContents;
import net.minecraftforge.event.entity.player.ItemTooltipEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.Tier;

/** Replaces "(Legendary)" on the scroll's level line with the tier name and colors the scroll name. */
public final class TierTooltip {
    private TierTooltip() {}

    private static final String RARITY_KEY = "tooltip.irons_spellbooks.rarity";

    @SubscribeEvent(priority = EventPriority.LOW)
    public static void onTooltip(ItemTooltipEvent e) {
        Tier tier = Tier.of(e.getItemStack());
        if (tier == null) return;
        List<Component> lines = e.getToolTip();
        int rgb = tier.colorAt(System.currentTimeMillis());
        if (!lines.isEmpty()) lines.set(0, Component.literal(lines.get(0).getString()).withStyle(s -> s.withColor(rgb)));
        MutableComponent tierName = Component.translatable(RARITY_KEY, Component.translatable(tier.langKey())).withStyle(s -> s.withColor(rgb));
        for (int i = 1; i < lines.size(); i++) {
            if (!has(lines.get(i))) continue;
            lines.set(i, rebuild(lines.get(i), tierName));
            break;
        }
    }

    private static boolean has(Component c) {
        if (c.getContents() instanceof TranslatableContents tc && RARITY_KEY.equals(tc.getKey())) return true;
        for (Component s : c.getSiblings()) if (has(s)) return true;
        return false;
    }

    private static MutableComponent rebuild(Component c, MutableComponent tierName) {
        if (c.getContents() instanceof TranslatableContents tc && RARITY_KEY.equals(tc.getKey())) return tierName.copy();
        MutableComponent out = MutableComponent.create(c.getContents()).setStyle(c.getStyle());
        for (Component s : c.getSiblings()) out.append(rebuild(s, tierName));
        return out;
    }
}
