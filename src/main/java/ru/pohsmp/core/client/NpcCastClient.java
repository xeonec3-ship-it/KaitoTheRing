package ru.pohsmp.core.client;

import dev.kosmx.playerAnim.api.TransformType;
import dev.kosmx.playerAnim.api.layered.KeyframeAnimationPlayer;
import dev.kosmx.playerAnim.core.data.KeyframeAnimation;
import dev.kosmx.playerAnim.core.util.Vec3f;
import dev.kosmx.playerAnim.minecraftApi.PlayerAnimationRegistry;
import io.redspace.ironsspellbooks.api.registry.SpellRegistry;
import io.redspace.ironsspellbooks.api.spells.AbstractSpell;
import io.redspace.ironsspellbooks.api.util.AnimationHolder;
import io.redspace.ironsspellbooks.player.ClientSpellCastHelper;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;
import net.minecraft.client.Minecraft;
import net.minecraft.client.model.HumanoidModel;
import net.minecraft.client.model.geom.ModelPart;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.level.LevelEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.net.Net;

/**
 * Client side of NPC casts (spell/NpcCast): the spell's client pre-cast (sound, own client effects) and the same player
 * animation a player would get (Iron's AnimationHolder, PlayerAnimator keyframes), played on any humanoid model
 * (CustomNPCs NPCs, zombies, ...) by mixin/HumanoidModelMixin right after the model's own pose.
 */
public final class NpcCastClient {
    private NpcCastClient() {}

    /** entity id -> animation running on its model. */
    private static final Map<Integer, KeyframeAnimationPlayer> ANIMS = new HashMap<>();

    public static void handle(Net.NpcCastMsg m) {
        Minecraft mc = Minecraft.getInstance();
        if (mc.level == null) return;
        Entity e = mc.level.getEntity(m.entity);
        AbstractSpell spell = SpellRegistry.getSpell(m.spell);
        if (!(e instanceof LivingEntity le) || le instanceof Player || spell == null || spell == SpellRegistry.none()) return;
        switch (m.phase) {
            case Net.NpcCastMsg.START -> {
                // Iron's base pre-cast may touch the local player's right-click suppression: keep it as it was
                boolean suppress = ClientSpellCastHelper.shouldSuppressRightClicks();
                try {
                    spell.onClientPreCast(mc.level, m.level, le, InteractionHand.MAIN_HAND, null);
                } catch (RuntimeException ex) {
                    ru.pohsmp.core.PohCore.LOG.debug("[pohsmp_core] NPC client pre-cast of {} failed: {}", m.spell, ex.toString());
                }
                ClientSpellCastHelper.setSuppressRightClicks(suppress);
                play(le, spell.getCastStartAnimation());
            }
            case Net.NpcCastMsg.FINISH -> {
                AnimationHolder fin = spell.getCastFinishAnimation();
                if (fin.isPass) return; // keep the start animation running to its end
                if (!play(le, fin)) ANIMS.remove(le.getId());
            }
            default -> ANIMS.remove(le.getId());
        }
    }

    private static boolean play(LivingEntity e, AnimationHolder h) {
        if (h == null || h.isPass) return false;
        Optional<ResourceLocation> rl = h.getForPlayer();
        if (rl.isEmpty()) return false;
        KeyframeAnimation a = PlayerAnimationRegistry.getAnimation(rl.get());
        if (a == null) return false;
        ANIMS.put(e.getId(), new KeyframeAnimationPlayer(a));
        return true;
    }

    public static boolean animating(LivingEntity e) {
        return ANIMS.containsKey(e.getId());
    }

    @SubscribeEvent
    public static void onTick(TickEvent.ClientTickEvent e) {
        if (e.phase != TickEvent.Phase.END || ANIMS.isEmpty()) return;
        Minecraft mc = Minecraft.getInstance();
        if (mc.level == null || mc.isPaused()) return;
        ANIMS.entrySet().removeIf(en -> {
            Entity ent = mc.level.getEntity(en.getKey());
            KeyframeAnimationPlayer p = en.getValue();
            if (ent == null || !ent.isAlive()) return true;
            p.tick();
            return !p.isActive();
        });
    }

    @SubscribeEvent
    public static void onUnload(LevelEvent.Unload e) {
        if (e.getLevel().isClientSide()) ANIMS.clear();
    }

    /** Called at the end of HumanoidModel.setupAnim for every humanoid that is not a player. */
    public static void apply(HumanoidModel<?> model, LivingEntity e) {
        if (ANIMS.isEmpty() || e instanceof Player) return;
        KeyframeAnimationPlayer p = ANIMS.get(e.getId());
        if (p == null || !p.isActive()) return;
        float td = Minecraft.getInstance().getFrameTime();
        p.setupAnim(td);
        part(p, "head", model.head, td);
        part(p, "torso", model.body, td);
        part(p, "rightArm", model.rightArm, td);
        part(p, "leftArm", model.leftArm, td);
        part(p, "rightLeg", model.rightLeg, td);
        part(p, "leftLeg", model.leftLeg, td);
        model.hat.copyFrom(model.head);
    }

    /** Same as PlayerAnimator's AnimationApplier.updatePart, without the bends (they need bendy-lib parts). */
    private static void part(KeyframeAnimationPlayer p, String name, ModelPart part, float td) {
        Vec3f pos = p.get3DTransform(name, TransformType.POSITION, td, new Vec3f(part.x, part.y, part.z));
        part.x = pos.getX();
        part.y = pos.getY();
        part.z = pos.getZ();
        Vec3f rot = p.get3DTransform(name, TransformType.ROTATION, td, new Vec3f(part.xRot, part.yRot, part.zRot));
        part.setRotation(rot.getX(), rot.getY(), rot.getZ());
    }
}
