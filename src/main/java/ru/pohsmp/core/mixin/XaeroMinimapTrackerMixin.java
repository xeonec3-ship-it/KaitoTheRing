package ru.pohsmp.core.mixin;

import java.util.Map;
import java.util.UUID;
import net.minecraft.client.Minecraft;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import ru.pohsmp.core.silent.SilentWitch;

/** Xaero's Minimap: tracked-player markers (players out of entity range, synced by the server or a party mod) skip full-set Silent Witches. */
@Pseudo
@Mixin(targets = "xaero.hud.minimap.player.tracker.PlayerTrackerMinimapElementCollector", remap = false)
public class XaeroMinimapTrackerMixin {
    @Shadow
    private Map<UUID, ?> elements;

    @Inject(method = "update", at = @At("RETURN"), require = 0)
    private void pohsmp$silentWitch(Minecraft mc, CallbackInfo ci) {
        if (elements != null) elements.keySet().removeIf(id -> !id.equals(mc.player == null ? null : mc.player.getUUID()) && SilentWitch.namelessClient(id));
    }
}
