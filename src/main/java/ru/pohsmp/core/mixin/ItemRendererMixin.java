package ru.pohsmp.core.mixin;

import com.mojang.blaze3d.vertex.PoseStack;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.entity.ItemRenderer;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.item.ItemDisplayContext;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import ru.pohsmp.core.client.EmberWhipClient;

/**
 * T14: where the hand really holds the fire sword-whip, for the physics whip (client/EmberWhipClient). Every held item of a
 * living entity — the vanilla hand layer, the Epic Fight item renderer, the first-person hand — is drawn through
 * ItemRenderer.renderStatic(LivingEntity, ...) (SRG m_269491_, checked against the 1.20.1 mappings); before it draws, the pose
 * stack is that of the hand in this frame, whatever animation moved it. No refmap in the project: the SRG name for the
 * production jar, the Mojang name for a dev run, require = 0 (a miss only leaves the whip root estimated from the body).
 */
@Mixin(ItemRenderer.class)
public abstract class ItemRendererMixin {
    @Inject(method = {
            "m_269491_(Lnet/minecraft/world/entity/LivingEntity;Lnet/minecraft/world/item/ItemStack;Lnet/minecraft/world/item/ItemDisplayContext;ZLcom/mojang/blaze3d/vertex/PoseStack;Lnet/minecraft/client/renderer/MultiBufferSource;Lnet/minecraft/world/level/Level;III)V",
            "renderStatic(Lnet/minecraft/world/entity/LivingEntity;Lnet/minecraft/world/item/ItemStack;Lnet/minecraft/world/item/ItemDisplayContext;ZLcom/mojang/blaze3d/vertex/PoseStack;Lnet/minecraft/client/renderer/MultiBufferSource;Lnet/minecraft/world/level/Level;III)V"},
            at = @At("HEAD"), remap = false, require = 0)
    private void pohsmp$emberWhipRoot(LivingEntity entity, ItemStack stack, ItemDisplayContext ctx, boolean leftHand, PoseStack poseStack,
                                     MultiBufferSource buffers, Level level, int light, int overlay, int seed, CallbackInfo ci) {
        if (entity != null && !stack.isEmpty()) EmberWhipClient.capture(entity, stack, ctx, leftHand, poseStack);
    }
}
