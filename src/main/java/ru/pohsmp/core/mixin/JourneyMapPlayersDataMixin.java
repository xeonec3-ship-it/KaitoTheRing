package ru.pohsmp.core.mixin;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import net.minecraft.client.Minecraft;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
import ru.pohsmp.core.silent.SilentWitch;

/** JourneyMap: the cached player map (what the minimap and the full map draw) skips full-set Silent Witches too. */
@Pseudo
@Mixin(targets = "journeymap.client.data.PlayersData", remap = false)
public class JourneyMapPlayersDataMixin {
    @Inject(method = "load(Ljava/lang/Class;)Ljava/util/Map;", at = @At("RETURN"), cancellable = true, require = 0)
    private void pohsmp$silentWitch(Class<?> c, CallbackInfoReturnable<Map<String, Object>> cir) {
        Map<String, Object> in = cir.getReturnValue();
        if (in == null || in.isEmpty()) return;
        Minecraft mc = Minecraft.getInstance();
        UUID me = mc.player == null ? null : mc.player.getUUID();
        Map<String, Object> out = new LinkedHashMap<>();
        boolean cut = false;
        for (var e : in.entrySet()) {
            UUID id = idOf(e.getKey(), e.getValue());
            if (id != null && !id.equals(me) && SilentWitch.namelessClient(id)) {
                cut = true;
                continue;
            }
            out.put(e.getKey(), e.getValue());
        }
        if (cut) cir.setReturnValue(out);
    }

    private static UUID idOf(String key, Object dto) {
        try {
            Object ref = dto.getClass().getField("entityLivingRef").get(dto);
            if (ref instanceof java.lang.ref.WeakReference<?> w && w.get() instanceof net.minecraft.world.entity.Entity en) return en.getUUID();
        } catch (ReflectiveOperationException | RuntimeException ignored) {}
        try {
            return UUID.fromString(key);
        } catch (IllegalArgumentException e) {
            return null;
        }
    }
}
