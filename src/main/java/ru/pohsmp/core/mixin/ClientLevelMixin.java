package ru.pohsmp.core.mixin;

import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.world.phys.Vec3;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/** T22 «Сон бабочки»: the dreamer's sky turns pearl (DreamScreen.sky). getSkyColor(Vec3, float) = m_171660_ (SRG, no refmap). */
@Mixin(ClientLevel.class)
public abstract class ClientLevelMixin {
    @Inject(method = "m_171660_(Lnet/minecraft/world/phys/Vec3;F)Lnet/minecraft/world/phys/Vec3;", at = @At("RETURN"), cancellable = true, remap = false, require = 0)
    private void pohsmp$sky(Vec3 pos, float pt, CallbackInfoReturnable<Vec3> cir) {
        cir.setReturnValue(ru.pohsmp.core.client.illusion.DreamScreen.sky(cir.getReturnValue(), pt));
    }
}
