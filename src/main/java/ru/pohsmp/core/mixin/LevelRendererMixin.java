package ru.pohsmp.core.mixin;

import net.minecraft.client.renderer.LevelRenderer;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import ru.pohsmp.core.client.nightmare.HouseClient;

/**
 * T25 «Дом, которого нет»: inside the corridor the victim's client draws none of the real world - no blocks, no sky, no clouds
 * (HouseClient draws the darkness instead). SRG, no refmap: renderChunkLayer = m_172993_, renderSky = m_202423_, renderClouds = m_253054_.
 */
@Mixin(LevelRenderer.class)
public abstract class LevelRendererMixin {
    @Inject(method = "m_172993_(Lnet/minecraft/client/renderer/RenderType;Lcom/mojang/blaze3d/vertex/PoseStack;DDDLorg/joml/Matrix4f;)V",
            at = @At("HEAD"), cancellable = true, remap = false, require = 0)
    private void pohsmp$chunks(CallbackInfo ci) {
        if (HouseClient.on()) ci.cancel();
    }

    @Inject(method = "m_202423_(Lcom/mojang/blaze3d/vertex/PoseStack;Lorg/joml/Matrix4f;FLnet/minecraft/client/Camera;ZLjava/lang/Runnable;)V",
            at = @At("HEAD"), cancellable = true, remap = false, require = 0)
    private void pohsmp$sky(CallbackInfo ci) {
        if (HouseClient.on()) ci.cancel();
    }

    /** T25: the red moon (stage 3 and «Ночь без рассвета») - the moon's texture in renderSky swapped, the call left as it is. */
    @org.spongepowered.asm.mixin.injection.ModifyArg(method = "m_202423_(Lcom/mojang/blaze3d/vertex/PoseStack;Lorg/joml/Matrix4f;FLnet/minecraft/client/Camera;ZLjava/lang/Runnable;)V",
            at = @At(value = "INVOKE", target = "Lcom/mojang/blaze3d/systems/RenderSystem;setShaderTexture(ILnet/minecraft/resources/ResourceLocation;)V"),
            index = 1, remap = false, require = 0)
    private net.minecraft.resources.ResourceLocation pohsmp$moon(net.minecraft.resources.ResourceLocation tex) {
        return ru.pohsmp.core.client.nightmare.NightmareWorld.moon(tex);
    }

    @Inject(method = "m_253054_(Lcom/mojang/blaze3d/vertex/PoseStack;Lorg/joml/Matrix4f;FDDD)V",
            at = @At("HEAD"), cancellable = true, remap = false, require = 0)
    private void pohsmp$clouds(CallbackInfo ci) {
        if (HouseClient.on()) ci.cancel();
    }
}
