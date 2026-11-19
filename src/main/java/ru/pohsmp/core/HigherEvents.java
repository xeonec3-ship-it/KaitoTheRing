package ru.pohsmp.core;

import io.redspace.ironsspellbooks.api.events.SpellPreCastEvent;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.UseAnim;
import net.minecraftforge.event.entity.living.LivingEntityUseItemEvent;
import net.minecraftforge.event.entity.living.LivingEvent;
import net.minecraftforge.event.entity.living.LivingFallEvent;
import net.minecraftforge.event.entity.living.LivingHurtEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;

/** Effects of the Higher school. Registered on both sides: jumping and elytra are predicted by the client. */
public final class HigherEvents {
    private HigherEvents() {}

    /** Seal and nightmare sleep: no Iron's casting. */
    @SubscribeEvent
    public static void onPreCast(SpellPreCastEvent e) {
        Player p = e.getEntity();
        if (p.hasEffect(Reg.SEAL.get()) || p.hasEffect(Reg.NIGHTMARE.get()) || p.hasEffect(Reg.SPENT.get())
                || p.hasEffect(Reg.CREATION_BACKLASH.get())) e.setCanceled(true);
    }

    /** Seal: no drinking (potions, milk, mana potions). */
    @SubscribeEvent
    public static void onUseStart(LivingEntityUseItemEvent.Start e) {
        if (e.getEntity().hasEffect(Reg.SEAL.get()) && e.getItem().getUseAnimation() == UseAnim.DRINK) e.setCanceled(true);
    }

    @SubscribeEvent
    public static void onJump(LivingEvent.LivingJumpEvent e) {
        LivingEntity le = e.getEntity();
        if (le.hasEffect(Reg.HEAVY.get()) || le.hasEffect(Reg.NIGHTMARE.get()))
            le.setDeltaMovement(le.getDeltaMovement().x, Math.min(0, le.getDeltaMovement().y), le.getDeltaMovement().z);
    }

    @SubscribeEvent
    public static void onLivingTick(LivingEvent.LivingTickEvent e) {
        LivingEntity le = e.getEntity();
        if (le instanceof Player p && p.isFallFlying() && le.hasEffect(Reg.HEAVY.get())) p.stopFallFlying();
        if (!le.level().isClientSide && le instanceof Mob m && le.hasEffect(Reg.NIGHTMARE.get())) {
            m.getNavigation().stop();
            m.setTarget(null);
        }
    }

    /** A hit wakes the sleeper and lands 50% harder. */
    @SubscribeEvent(priority = EventPriority.LOW)
    public static void onHurt(LivingHurtEvent e) {
        LivingEntity le = e.getEntity();
        if (le.level().isClientSide || !le.hasEffect(Reg.NIGHTMARE.get())) return;
        e.setAmount(e.getAmount() * 1.5f);
        le.removeEffect(Reg.NIGHTMARE.get());
    }

    @SubscribeEvent
    public static void onFall(LivingFallEvent e) {
        if (e.getEntity().hasEffect(Reg.ASCENSION.get())) e.setCanceled(true);
    }
}
