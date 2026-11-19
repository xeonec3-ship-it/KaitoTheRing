package ru.pohsmp.core.mixin;

import net.minecraft.client.model.HumanoidModel;
import net.minecraft.world.entity.LivingEntity;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import ru.pohsmp.core.client.NpcCastClient;

/**
 * Player-style cast animations on NPC models (client/NpcCastClient). The project has no mixin refmap, so the target is
 * written with its SRG name (production jar); in a dev run the injection is simply skipped (require = 0).
 * Priority above default: applied after CustomNPCs' own setupAnim hook on the same method.
 */
@Mixin(value = HumanoidModel.class, priority = 1500)
public abstract class HumanoidModelMixin<T extends LivingEntity> {
    @Inject(method = "m_6973_(Lnet/minecraft/world/entity/LivingEntity;FFFFF)V", at = @At("TAIL"), remap = false, require = 0)
    private void pohsmp$npcCastPose(T entity, float limbSwing, float limbSwingAmount, float ageInTicks, float netHeadYaw, float headPitch,
                                    CallbackInfo ci) {
        NpcCastClient.apply((HumanoidModel<?>) (Object) this, entity);
        ru.pohsmp.core.client.OutfitAnim.legs((HumanoidModel<?>) (Object) this, entity);   // Silent Witch skirt: half steps
    }
}
