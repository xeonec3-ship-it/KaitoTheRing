package ru.pohsmp.core.mixin;

import io.redspace.ironsspellbooks.gui.arcane_anvil.ArcaneAnvilMenu;
import io.redspace.ironsspellbooks.item.Scroll;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.item.ItemStack;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import ru.pohsmp.core.spell.SpellBans;

/**
 * Owner 20.11: magic above Higher (Mythic, Divine, Creation, Unknown) is not imbued into items by players.
 * The Arcane Anvil block itself works as before (scroll merging, upgrade orbs, shriving, spell slots): only a result made from
 * an item + a scroll of such a spell is cleared, with an actionbar message. Our staffs that come with their spells built in
 * are not affected - nothing is imbued into them here.
 * T34: two scrolls of a boss reward spell are not merged into a higher level (levels come only from the admin).
 * Slots of ItemCombinerMenu: 0 = item, 1 = scroll, 2 = result. createResult is m_6640_ in the production jar (SRG),
 * createResult in dev (Iron's deobfuscated by ForgeGradle).
 */
@Mixin(value = ArcaneAnvilMenu.class, remap = false)
public abstract class ArcaneAnvilMenuMixin {
    @Unique private Player pohsmp$player;

    @Inject(method = "<init>(ILnet/minecraft/world/entity/player/Inventory;Lnet/minecraft/world/inventory/ContainerLevelAccess;)V",
            at = @At("RETURN"), remap = false, require = 0)
    private void pohsmp$init(int id, Inventory inv, net.minecraft.world.inventory.ContainerLevelAccess access, CallbackInfo ci) {
        pohsmp$player = inv.player;
    }

    @Inject(method = {"m_6640_", "createResult"}, at = @At("TAIL"), remap = false, require = 0)
    private void pohsmp$noImbue(CallbackInfo ci) {
        AbstractContainerMenu menu = (AbstractContainerMenu) (Object) this;
        ItemStack item = menu.getSlot(0).getItem();
        ItemStack scroll = menu.getSlot(1).getItem();
        if (item.getItem() instanceof Scroll && scroll.getItem() instanceof Scroll) {   // T34: merging reward scrolls -> no result
            if (!menu.getSlot(2).getItem().isEmpty() && (SpellBans.copyBanned(item) || SpellBans.copyBanned(scroll))) {
                menu.getSlot(2).set(ItemStack.EMPTY);
                SpellBans.tell(pohsmp$player, "no_copy");
            }
            return;
        }
        if (item.isEmpty() || item.getItem() instanceof Scroll || !(scroll.getItem() instanceof Scroll)) return;
        if (menu.getSlot(2).getItem().isEmpty() || !SpellBans.bindBanned(scroll)) return;
        menu.getSlot(2).set(ItemStack.EMPTY);
        SpellBans.tell(pohsmp$player, "no_imbue");
    }
}
