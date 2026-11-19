package ru.pohsmp.core.client;

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
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraftforge.fml.event.lifecycle.FMLClientSetupEvent;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.spell.TargetPose;

/**
 * T13, client: the looping pose pohsmp_held_target on a held target (server: spell/TargetPose). Players get it on an own
 * PlayerAnimator layer above Iron's cast layer, so a cast animation of the target does not cut it; other humanoids
 * (CustomNPCs NPCs, zombies) on their model through NpcCastClient.
 */
public final class TargetPoseClient {
    private TargetPoseClient() {}

    public static final ResourceLocation LAYER = new ResourceLocation(PohCore.MODID, "target_pose");
    /** Above Iron's cast layer (42). */
    private static final int PRIORITY = 1500;
    public static final ResourceLocation HELD = new ResourceLocation("irons_spellbooks", "pohsmp_held_target");

    public static void setup(FMLClientSetupEvent e) {
        e.enqueueWork(() -> PlayerAnimationFactory.ANIMATION_DATA_FACTORY.registerFactory(LAYER, PRIORITY, p -> new ModifierLayer<>()));
    }

    /** HFx.ANIM with b = TargetPose.HELD_START / HELD_STOP, a = entity id. */
    public static void handle(int entity, int what) {
        Minecraft mc = Minecraft.getInstance();
        if (mc.level == null) return;
        Entity e = mc.level.getEntity(entity);
        if (!(e instanceof LivingEntity le)) return;
        boolean start = what == TargetPose.HELD_START;
        if (le instanceof AbstractClientPlayer p) {
            ModifierLayer<IAnimation> layer = layer(p);
            if (layer == null) return;
            if (!start) {
                layer.replaceAnimationWithFade(AbstractFadeModifier.standardFadeIn(6, Ease.INOUTSINE), null);
                return;
            }
            KeyframeAnimation a = PlayerAnimationRegistry.getAnimation(HELD);
            if (a != null) layer.replaceAnimationWithFade(AbstractFadeModifier.standardFadeIn(4, Ease.INOUTSINE), new KeyframeAnimationPlayer(a));
        } else if (start) {
            NpcCastClient.loop(le, HELD);
        } else {
            NpcCastClient.stop(le);
        }
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
