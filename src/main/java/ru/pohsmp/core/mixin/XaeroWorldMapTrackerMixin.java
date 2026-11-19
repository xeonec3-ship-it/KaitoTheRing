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

/** Xaero's World Map: tracked-player markers on the big map skip full-set Silent Witches. */
@Pseudo
@Mixin(targets = "xaero.map.radar.tracker.PlayerTrackerMapElementCollector", remap = false)
public class XaeroWorldMapTrackerMixin {
    @Shadow
    private Map<UUID, ?> elements;

    @Inject(method = "update", at = @At("RETURN"), require = 0)
    private void pohsmp$silentWitch(Minecraft mc, CallbackInfo ci) {
        if (elements != null) elements.keySet().removeIf(id -> !id.equals(mc.player == null ? null : mc.player.getUUID()) && SilentWitch.namelessClient(id));
    }
}
