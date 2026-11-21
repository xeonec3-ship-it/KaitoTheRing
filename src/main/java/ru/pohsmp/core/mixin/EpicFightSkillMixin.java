package ru.pohsmp.core.mixin;

import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.player.Player;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
import ru.pohsmp.core.spell.CastLock;
import yesman.epicfight.world.capabilities.entitypatch.player.PlayerPatch;
import yesman.epicfight.world.entity.eventlistener.SkillCastEvent;

/**
 * Owner 21.11 (2): while the window of an animated spell is open, no Epic Fight skill runs — basic attacks, dodge, guard / parry,
 * the weapon's special. SkillContainer.canUse is asked on the client before the request and on the server before execution.
 * Epic Fight is optional: @Pseudo, the mixin is skipped without it.
 */
@Pseudo
@Mixin(targets = "yesman.epicfight.skill.SkillContainer", remap = false)
public abstract class EpicFightSkillMixin {
    @Inject(method = "canUse", at = @At("HEAD"), cancellable = true, remap = false, require = 0)
    private void pohsmp$castLock(PlayerPatch<?> patch, SkillCastEvent event, CallbackInfoReturnable<Boolean> cir) {
        Player p = patch == null ? null : patch.getOriginal();
        if (p == null) return;
        boolean held = p instanceof ServerPlayer sp ? CastLock.heldNow(sp) : p.level().isClientSide && CastLock.clientHeld(p);
        if (held) cir.setReturnValue(false);
    }
}
