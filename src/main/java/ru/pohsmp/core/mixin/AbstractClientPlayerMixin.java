package ru.pohsmp.core.mixin;

import net.minecraft.client.multiplayer.PlayerInfo;
import net.minecraft.client.player.AbstractClientPlayer;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
import ru.pohsmp.core.client.illusion.IllusionClient;

/**
 * T22 «Чужое лицо» and the copies: a player drawn with another player's face takes that player's tab entry - skin, slim arms, cape,
 * elytra - everywhere the game asks for it (Epic Fight's renderer too). SRG name: getPlayerInfo = m_108558_ (no refmap in this build).
 */
@Mixin(AbstractClientPlayer.class)
public abstract class AbstractClientPlayerMixin {
    @Inject(method = "m_108558_()Lnet/minecraft/client/multiplayer/PlayerInfo;", at = @At("HEAD"), cancellable = true, remap = false, require = 0)
    private void pohsmp$face(CallbackInfoReturnable<PlayerInfo> cir) {
        PlayerInfo other = IllusionClient.faceOf((AbstractClientPlayer) (Object) this);
        if (other != null) cir.setReturnValue(other);
    }
}
