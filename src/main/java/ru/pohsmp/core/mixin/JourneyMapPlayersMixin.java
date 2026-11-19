package ru.pohsmp.core.mixin;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import net.minecraft.client.Minecraft;
import net.minecraft.world.entity.LivingEntity;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
import ru.pohsmp.core.silent.SilentWitch;

/**
 * JourneyMap (the minimap of the server pack, owner 19.11): a full-set Silent Witch is not on anyone's minimap or full map - the player
 * list JourneyMap draws (nearby players and the ones its server radar sends) skips her.
 */
@Pseudo
@Mixin(targets = "journeymap.client.model.EntityHelper", remap = false)
public class JourneyMapPlayersMixin {
    @Inject(method = "getPlayersNearby", at = @At("RETURN"), cancellable = true, require = 0)
    private static void pohsmp$silentWitch(CallbackInfoReturnable<List<?>> cir) {
        List<?> in = cir.getReturnValue();
        if (in == null || in.isEmpty()) return;
        Minecraft mc = Minecraft.getInstance();
        UUID me = mc.player == null ? null : mc.player.getUUID();
        List<Object> out = new ArrayList<>(in.size());
        boolean cut = false;
        for (Object o : in) {
            UUID id = idOf(o);
            if (id != null && !id.equals(me) && SilentWitch.namelessClient(id)) {
                cut = true;
                continue;
            }
            out.add(o);
        }
        if (cut) cir.setReturnValue(out);
    }

    private static UUID idOf(Object dto) {
        try {
            Object ref = dto.getClass().getField("entityLivingRef").get(dto);
            if (ref instanceof java.lang.ref.WeakReference<?> w && w.get() instanceof LivingEntity le) return le.getUUID();
            Object id = dto.getClass().getField("entityId").get(dto);
            return id == null ? null : UUID.fromString(id.toString());
        } catch (ReflectiveOperationException | IllegalArgumentException e) {
            return null;
        }
    }
}
