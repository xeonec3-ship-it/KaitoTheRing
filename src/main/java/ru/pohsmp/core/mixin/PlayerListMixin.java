package ru.pohsmp.core.mixin;

import net.minecraft.network.chat.Component;
import net.minecraft.server.players.PlayerList;
import net.minecraft.world.entity.player.Player;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import ru.pohsmp.core.erased.Erased;

/**
 * T24: vanilla messages about an erased player do not go out - joined / left the game, death, advancement (the world forgot him).
 * broadcastSystemMessage (m_240416_), and the team versions of the death message (m_215621_ to the team, m_215649_ to the rest).
 */
@Mixin(PlayerList.class)
public abstract class PlayerListMixin {
    @Inject(method = "m_240416_(Lnet/minecraft/network/chat/Component;Z)V", at = @At("HEAD"), cancellable = true, remap = false, require = 0)
    private void pohsmp$mute(Component msg, boolean overlay, CallbackInfo ci) {
        if (!overlay && Erased.mute(msg)) ci.cancel();
    }

    @Inject(method = "m_215621_(Lnet/minecraft/world/entity/player/Player;Lnet/minecraft/network/chat/Component;)V", at = @At("HEAD"),
            cancellable = true, remap = false, require = 0)
    private void pohsmp$muteTeam(Player p, Component msg, CallbackInfo ci) {
        if (Erased.isErased(p) || Erased.mute(msg)) ci.cancel();
    }

    @Inject(method = "m_215649_(Lnet/minecraft/world/entity/player/Player;Lnet/minecraft/network/chat/Component;)V", at = @At("HEAD"),
            cancellable = true, remap = false, require = 0)
    private void pohsmp$muteOthers(Player p, Component msg, CallbackInfo ci) {
        if (Erased.isErased(p) || Erased.mute(msg)) ci.cancel();
    }
}
