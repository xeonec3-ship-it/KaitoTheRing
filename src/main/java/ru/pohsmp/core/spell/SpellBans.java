package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.events.InscribeSpellEvent;
import io.redspace.ironsspellbooks.api.registry.SpellRegistry;
import io.redspace.ironsspellbooks.api.spells.AbstractSpell;
import io.redspace.ironsspellbooks.api.spells.SpellData;
import io.redspace.ironsspellbooks.gui.inscription_table.InscriptionTableMenu;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.Tier;

/**
 * Owner 20.11 (docs/inbox/2026-11-20_mgr_fixed_cast_and_crafting.md): what our magic may not go through.
 * <ul>
 *   <li>crafting (Scroll Forge, which asks AbstractSpell.allowCrafting on the server): see {@link #craftBanned}, used by mixin/AbstractSpellMixin;</li>
 *   <li>Inscription Table (writing a scroll into a spell book): InscribeSpellEvent is cancelled here;</li>
 *   <li>Arcane Anvil imbue (scroll into a weapon / staff / any other spell container): the result is cleared by mixin/ArcaneAnvilMenuMixin.</li>
 * </ul>
 * The rules themselves are in {@link MagicRules}.
 */
@Mod.EventBusSubscriber(modid = PohCore.MODID)
public final class SpellBans {
    private SpellBans() {}

    /** True if this spell may never be crafted (our spells of Higher and above, all Silent ones). Iron's own spells are never touched. */
    public static boolean craftBanned(AbstractSpell sp) {
        if (sp == null) return false;
        String id;
        try {
            id = sp.getSpellId();
        } catch (RuntimeException e) {
            return false;
        }
        if (id == null || !id.startsWith(PohCore.MODID + ":")) return false;
        Tier t = Tier.builtin(id);
        boolean silent = false;
        try {
            silent = sp.getSchoolType() != null && Reg.SILENT_ID.equals(sp.getSchoolType().getId());
        } catch (RuntimeException ignored) {
            // school registry not ready yet: only the tier decides
        }
        return MagicRules.craftBanned(t == null ? null : t.key, silent);
    }

    /** Tier of a spell in some container: built in, else by how far the level is above the max (same as Tier.of for scrolls). */
    public static Tier tierOf(SpellData sd) {
        if (sd == null) return null;
        AbstractSpell sp = sd.getSpell();
        if (sp == null || sp == SpellRegistry.none()) return null;
        Tier b = Tier.builtin(sp.getSpellId());
        if (b != null) return b;
        int over = sd.getLevel() - sp.getMaxLevel();
        if (over >= 5) return Tier.DIVINE;
        if (over >= 3) return Tier.MYTHIC;
        if (over >= 1) return Tier.HIGHER;
        return null;
    }

    /** True if this scroll may not be written into a book / imbued into an item (Mythic and above, also by the scroll's NBT tier). */
    public static boolean bindBanned(ItemStack scroll) {
        Tier t = Tier.of(scroll);
        return MagicRules.bindBanned(t == null ? null : t.key);
    }

    /** Actionbar line to the player (server side only). */
    public static void tell(Player p, String key) {
        if (p instanceof ServerPlayer sp) sp.displayClientMessage(Component.translatable("message.pohsmp_core." + key), true);
    }

    @SubscribeEvent(priority = EventPriority.HIGH)
    public static void onInscribe(InscribeSpellEvent e) {
        Player p = e.getEntity();
        Tier t = null;
        if (p != null && p.containerMenu instanceof InscriptionTableMenu m) t = Tier.of(m.getScrollSlot().getItem());
        if (t == null) t = tierOf(e.getSpellData());
        if (MagicRules.bindBanned(t == null ? null : t.key)) {
            e.setCanceled(true);
            tell(p, "no_inscribe");
        }
    }
}
