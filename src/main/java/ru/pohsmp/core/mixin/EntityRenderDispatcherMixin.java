package ru.pohsmp.core.mixin;

import net.minecraft.client.renderer.culling.Frustum;
import net.minecraft.client.renderer.entity.EntityRenderDispatcher;
import net.minecraft.world.entity.Entity;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
import ru.pohsmp.core.client.HiddenEntities;

/**
 * Hidden entities that are not living ones (ru.pohsmp.core.Hidden): Forge has no render event for them, so RenderLivingEvent in
 * client/HiddenEntities never sees them. Example: the Iron's shields of "Eight Shields" stood visible next to their seals
 * (owner's screenshot 19.11). EntityRenderDispatcher.shouldRender (SRG m_114397_, no refmap in the project) says "not drawn" for them.
 */
@Mixin(EntityRenderDispatcher.class)
public abstract class EntityRenderDispatcherMixin {
    @Inject(method = "m_114397_(Lnet/minecraft/world/entity/Entity;Lnet/minecraft/client/renderer/culling/Frustum;DDD)Z",
            at = @At("HEAD"), cancellable = true, remap = false, require = 0)
    private void pohsmp$hidden(Entity e, Frustum frustum, double x, double y, double z, CallbackInfoReturnable<Boolean> cir) {
        if (HiddenEntities.hidden(e)) cir.setReturnValue(false);
    }
}
