package ru.pohsmp.core.mixin;

import io.redspace.ironsspellbooks.capabilities.magic.SyncedSpellData;
import io.redspace.ironsspellbooks.gui.overlays.SpellSelection;
import io.redspace.ironsspellbooks.network.gui.SelectSpellPacket;
import net.minecraftforge.network.NetworkEvent;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;
import ru.pohsmp.core.spell.CastLock;

/** Owner 21.11: the spell wheel / spell bar selection does not change on the server while the window is open (the client blocks it first). */
@Mixin(value = SelectSpellPacket.class, remap = false)
public abstract class IronsSelectSpellMixin {
    @Redirect(method = "lambda$handle$0", remap = false, require = 0,
            at = @At(value = "INVOKE", remap = false,
                    target = "Lio/redspace/ironsspellbooks/capabilities/magic/SyncedSpellData;setSpellSelection(Lio/redspace/ironsspellbooks/gui/overlays/SpellSelection;)V"))
    private void pohsmp$keepSelection(SyncedSpellData data, SpellSelection sel, NetworkEvent.Context ctx) {
        if (ctx.getSender() != null && CastLock.selectionLocked(ctx.getSender())) return;
        data.setSpellSelection(sel);
    }
}
