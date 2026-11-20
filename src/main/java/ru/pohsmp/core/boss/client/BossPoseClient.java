package ru.pohsmp.core.boss.client;

import dev.kosmx.playerAnim.api.layered.IAnimation;
import dev.kosmx.playerAnim.api.layered.KeyframeAnimationPlayer;
import dev.kosmx.playerAnim.api.layered.ModifierLayer;
import dev.kosmx.playerAnim.api.layered.modifier.AbstractFadeModifier;
import dev.kosmx.playerAnim.core.data.KeyframeAnimation;
import dev.kosmx.playerAnim.core.util.Ease;
import dev.kosmx.playerAnim.minecraftApi.PlayerAnimationAccess;
import dev.kosmx.playerAnim.minecraftApi.PlayerAnimationFactory;
import dev.kosmx.playerAnim.minecraftApi.PlayerAnimationRegistry;
import net.minecraft.client.Minecraft;
import net.minecraft.client.player.AbstractClientPlayer;
import net.minecraft.resources.ResourceLocation;
import net.minecraftforge.fml.event.lifecycle.FMLClientSetupEvent;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.boss.BossNet;

/**
 * Named PlayerAnimator animations on players for the bosses (the finisher victim pose pohsmp_cult_finisher_victim...) on an own layer
 * above Iron's cast layer and TargetPose's. Sent to everyone who sees the player and to the player itself.
 */
public final class BossPoseClient {
    private BossPoseClient() {}

    public static final ResourceLocation LAYER = new ResourceLocation(PohCore.MODID, "boss_pose");
    private static final int PRIORITY = 1600;

    public static void setup(FMLClientSetupEvent e) {
        e.enqueueWork(() -> PlayerAnimationFactory.ANIMATION_DATA_FACTORY.registerFactory(LAYER, PRIORITY, p -> new ModifierLayer<>()));
    }

    static void onMsg(BossNet.Msg m) {
        var mc = Minecraft.getInstance();
        if (mc.level == null) return;
        if (!(mc.level.getEntity(m.a) instanceof AbstractClientPlayer p)) return;
        ModifierLayer<IAnimation> layer = layer(p);
        if (layer == null) return;
        if (m.b == 0) {
            layer.replaceAnimationWithFade(AbstractFadeModifier.standardFadeIn(6, Ease.INOUTSINE), null);
            return;
        }
        ResourceLocation id = m.s1.contains(":") ? new ResourceLocation(m.s1) : new ResourceLocation("irons_spellbooks", m.s1);
        KeyframeAnimation a = PlayerAnimationRegistry.getAnimation(id);
        if (a != null) layer.replaceAnimationWithFade(AbstractFadeModifier.standardFadeIn(3, Ease.INOUTSINE), new KeyframeAnimationPlayer(a));
    }

    @SuppressWarnings("unchecked")
    private static ModifierLayer<IAnimation> layer(AbstractClientPlayer p) {
        try {
            return (ModifierLayer<IAnimation>) PlayerAnimationAccess.getPlayerAssociatedData(p).get(LAYER);
        } catch (RuntimeException ex) {
            return null;
        }
    }
}
