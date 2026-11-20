package ru.pohsmp.core.boss.ereb.client;

import com.mojang.authlib.GameProfile;
import com.mojang.blaze3d.vertex.PoseStack;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.player.RemotePlayer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import ru.pohsmp.core.boss.ereb.ErebBody;

/**
 * «Чужое лицо» of a mob (T22's disguise is for player casters: a mixin on the player's skin): Ereb wearing a participant's look is drawn
 * as a player — a client-only RemotePlayer with that participant's profile (so its skin, model and name come from the tab list like
 * any player's), dressed in that participant's armour and hands if this client sees it, posed and moved like Ereb. Not added to the
 * level; one per Ereb body, dropped when the face is gone.
 */
final class ErebDisguise {
    private ErebDisguise() {}

    private record Fake(UUID face, RemotePlayer body) {}

    private static final Map<Integer, Fake> FAKES = new HashMap<>();

    /** Draws b as the player it wears; false if it cannot (no level yet): then it is drawn as itself. */
    static boolean render(ErebBody b, float yaw, float pt, PoseStack ps, MultiBufferSource buf, int light) {
        Minecraft mc = Minecraft.getInstance();
        if (!(b.level() instanceof ClientLevel lvl)) return false;
        UUID face = b.face();
        Fake f = FAKES.get(b.getId());
        if (f == null || !f.face().equals(face) || f.body().level() != lvl) {
            f = new Fake(face, new RemotePlayer(lvl, new GameProfile(face, b.faceName())));
            FAKES.put(b.getId(), f);
            if (FAKES.size() > 32) FAKES.keySet().removeIf(id -> lvl.getEntity(id) == null);
        }
        RemotePlayer p = f.body();
        pose(p, b, lvl);
        mc.getEntityRenderDispatcher().getRenderer(p).render(p, Mth.lerp(pt, b.yRotO, b.getYRot()), pt, ps, buf, light);
        return true;
    }

    /** The fake stands where b stands, turns, walks and swings as b does; wears what the real participant wears (if seen). */
    private static void pose(RemotePlayer p, LivingEntity b, ClientLevel lvl) {
        p.setPos(b.getX(), b.getY(), b.getZ());
        p.xo = b.xo;
        p.yo = b.yo;
        p.zo = b.zo;
        p.xOld = b.xOld;
        p.yOld = b.yOld;
        p.zOld = b.zOld;
        p.setYRot(b.getYRot());
        p.yRotO = b.yRotO;
        p.setXRot(b.getXRot());
        p.xRotO = b.xRotO;
        p.yBodyRot = b.yBodyRot;
        p.yBodyRotO = b.yBodyRotO;
        p.yHeadRot = b.yHeadRot;
        p.yHeadRotO = b.yHeadRotO;
        p.tickCount = b.tickCount;
        p.hurtTime = b.hurtTime;
        p.attackAnim = b.attackAnim;
        p.oAttackAnim = b.oAttackAnim;
        p.swinging = b.swinging;
        copyWalk(p, b);
        Player real = lvl.getPlayerByUUID(p.getUUID());
        for (EquipmentSlot s : EquipmentSlot.values()) {
            ItemStack want = real != null ? real.getItemBySlot(s) : s == EquipmentSlot.MAINHAND ? b.getMainHandItem() : ItemStack.EMPTY;
            if (!ItemStack.matches(want, p.getItemBySlot(s))) p.setItemSlot(s, want.copy());
        }
    }

    /** Walk animation: the same speed and phase as the source entity. */
    static void copyWalk(LivingEntity to, LivingEntity from) {
        float target = from.walkAnimation.speed();
        float pos = from.walkAnimation.position();
        // WalkAnimationState has no setter of its position: step it until it matches (it only moves forward)
        to.walkAnimation.setSpeed(target);
        float d = pos - to.walkAnimation.position();
        if (d > 0) to.walkAnimation.update(d, 1f);
        to.walkAnimation.setSpeed(target);
    }

    static void clear() {
        FAKES.clear();
    }
}
