package ru.pohsmp.core.mixin;

import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.ColorResolver;
import net.minecraft.world.phys.Vec3;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
import ru.pohsmp.core.client.nightmare.NightmareWorld;

/**
 * T22 «Сон бабочки»: the dreamer's sky turns pearl (DreamScreen.sky). T25 stage 3: the sky and clouds blood-black, the biome tints rotten
 * (NightmareWorld). SRG, no refmap: getSkyColor(Vec3, float) = m_171660_, getCloudColor(float) = m_104808_, getBlockTint = m_6171_.
 */
@Mixin(ClientLevel.class)
public abstract class ClientLevelMixin {
    @Inject(method = "m_171660_(Lnet/minecraft/world/phys/Vec3;F)Lnet/minecraft/world/phys/Vec3;", at = @At("RETURN"), cancellable = true, remap = false, require = 0)
    private void pohsmp$sky(Vec3 pos, float pt, CallbackInfoReturnable<Vec3> cir) {
        cir.setReturnValue(NightmareWorld.sky(ru.pohsmp.core.client.illusion.DreamScreen.sky(cir.getReturnValue(), pt)));
    }

    @Inject(method = "m_104808_(F)Lnet/minecraft/world/phys/Vec3;", at = @At("RETURN"), cancellable = true, remap = false, require = 0)
    private void pohsmp$clouds(float pt, CallbackInfoReturnable<Vec3> cir) {
        cir.setReturnValue(NightmareWorld.clouds(cir.getReturnValue()));
    }

    @Inject(method = "m_6171_(Lnet/minecraft/core/BlockPos;Lnet/minecraft/world/level/ColorResolver;)I", at = @At("HEAD"), cancellable = true, remap = false, require = 0)
    private void pohsmp$tint(BlockPos pos, ColorResolver r, CallbackInfoReturnable<Integer> cir) {
        Integer c = NightmareWorld.tint(r);
        if (c != null) cir.setReturnValue(c);
    }
}
