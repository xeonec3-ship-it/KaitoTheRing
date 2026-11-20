package ru.pohsmp.core.boss.aris;

import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.damagesource.DamageTypes;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.entity.projectile.AbstractArrow;
import net.minecraftforge.event.entity.living.LivingEvent;
import net.minecraftforge.event.entity.living.LivingHurtEvent;
import net.minecraftforge.event.entity.player.AttackEntityEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;

/** Forge events of T28: «перековка» (weapon damage ×0.6), «Цепи кузни» (allies strike the chains; no jumping out of them). */
public final class ArisEvents {
    private ArisEvents() {}

    /** «Перековка»: the reforged player's weapon damage (melee, arrows / bolts / tridents) ×reforge_weapon_mult; spells as they are. */
    @SubscribeEvent(priority = EventPriority.LOW)
    public static void onHurt(LivingHurtEvent e) {
        if (!(e.getSource().getEntity() instanceof Player p) || Aris.REFORGED == null || !p.hasEffect(Aris.REFORGED.get())) return;
        boolean weapon = e.getSource().is(DamageTypes.PLAYER_ATTACK) && e.getSource().getDirectEntity() == p
                || e.getSource().getDirectEntity() instanceof AbstractArrow;
        if (weapon) e.setAmount((float) (e.getAmount() * ArisConfig.get(ArisConfig.REFORGE_MULT)));
    }

    /** A player strikes a chained player: the blow goes into the chains (no damage), 3 such break them. */
    @SubscribeEvent
    public static void onAttack(AttackEntityEvent e) {
        if (!(e.getEntity() instanceof ServerPlayer by) || !(e.getTarget() instanceof ServerPlayer victim) || by == victim) return;
        ArisFight f = ArisFight.CHAINED.get(victim.getUUID());
        if (f == null) return;
        e.setCanceled(true);
        f.chainHit(victim, by);
    }

    /** Chained: no jumping (both sides: the client would predict the jump). */
    @SubscribeEvent
    public static void onJump(LivingEvent.LivingJumpEvent e) {
        if (Aris.CHAINED == null || !e.getEntity().hasEffect(Aris.CHAINED.get())) return;
        var v = e.getEntity().getDeltaMovement();
        e.getEntity().setDeltaMovement(v.x, Math.min(0, v.y), v.z);
    }
}
