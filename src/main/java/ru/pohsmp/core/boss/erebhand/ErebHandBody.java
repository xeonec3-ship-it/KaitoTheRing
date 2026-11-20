package ru.pohsmp.core.boss.erebhand;

import io.redspace.ironsspellbooks.entity.mobs.IAnimatedAttacker;
import io.redspace.ironsspellbooks.entity.mobs.abstract_spell_casting_mob.AbstractSpellCastingMob;
import java.util.Optional;
import java.util.UUID;
import net.minecraft.network.chat.Component;
import net.minecraft.network.syncher.EntityDataAccessor;
import net.minecraft.network.syncher.EntityDataSerializers;
import net.minecraft.network.syncher.SynchedEntityData;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.util.RandomSource;
import net.minecraft.world.DifficultyInstance;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.PathfinderMob;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import software.bernie.geckolib.core.animation.AnimatableManager;
import software.bernie.geckolib.core.animation.AnimationController;
import software.bernie.geckolib.core.animation.AnimationState;
import software.bernie.geckolib.core.animation.RawAnimation;
import software.bernie.geckolib.core.object.PlayState;

/**
 * The body of Ereb, the Hand of Lies — shared by the boss and his reflections (doubles of «Лживое слово», the reflections of «Тысяча
 * отражений»): Iron's casting mob (abstract_casting_mob bones, Iron's procedural walk and casting poses) with our model
 * (geo/entity/ereb_hand.geo.json: the mask, the cape, the ghost hand over the right shoulder), the «ereb_hand_*» animations started from
 * the server ({@link #serverTriggerAnimation}) and the synced looks: the mask's texture (own / mended / cracked), the mask torn off,
 * «hand only» (the intro: the hand forms before him), «ghost» (a see-through reflection), the false arena's victim.
 */
public abstract class ErebHandBody extends AbstractSpellCastingMob implements IAnimatedAttacker {
    /** 0 = ereb_hand.png (thin cracks), 1 = ereb_hand_mended.png (after «Падение маски»), 2 = ereb_hand_cracked.png (phase 3). */
    private static final EntityDataAccessor<Integer> MASK = SynchedEntityData.defineId(ErebHandBody.class, EntityDataSerializers.INT);
    private static final EntityDataAccessor<Boolean> MASK_OFF = SynchedEntityData.defineId(ErebHandBody.class, EntityDataSerializers.BOOLEAN);
    private static final EntityDataAccessor<Boolean> HAND_ONLY = SynchedEntityData.defineId(ErebHandBody.class, EntityDataSerializers.BOOLEAN);
    private static final EntityDataAccessor<Boolean> GHOST = SynchedEntityData.defineId(ErebHandBody.class, EntityDataSerializers.BOOLEAN);
    /** «Ложное отступление»: the double casts no shadow (the hint). */
    private static final EntityDataAccessor<Boolean> NO_SHADOW = SynchedEntityData.defineId(ErebHandBody.class, EntityDataSerializers.BOOLEAN);
    /** «Длань Лжи»: this player sees the false arena (its allies drawn as him) while it is set. */
    private static final EntityDataAccessor<Optional<UUID>> FALSE_ARENA = SynchedEntityData.defineId(ErebHandBody.class, EntityDataSerializers.OPTIONAL_UUID);

    protected ErebHandBody(EntityType<? extends PathfinderMob> type, Level level) {
        super(type, level);
    }

    @Override
    protected void defineSynchedData() {
        super.defineSynchedData();
        entityData.define(MASK, 0);
        entityData.define(MASK_OFF, false);
        entityData.define(HAND_ONLY, false);
        entityData.define(GHOST, false);
        entityData.define(NO_SHADOW, false);
        entityData.define(FALSE_ARENA, Optional.empty());
    }

    // ---------------------------------------------------------------- looks

    public int mask() {
        return entityData.get(MASK);
    }

    public void setMask(int state) {
        entityData.set(MASK, Math.max(0, Math.min(2, state)));
    }

    public boolean maskOff() {
        return entityData.get(MASK_OFF);
    }

    public void setMaskOff(boolean off) {
        entityData.set(MASK_OFF, off);
    }

    public boolean handOnly() {
        return entityData.get(HAND_ONLY);
    }

    public void setHandOnly(boolean on) {
        entityData.set(HAND_ONLY, on);
    }

    public boolean ghost() {
        return entityData.get(GHOST);
    }

    public void setGhost(boolean on) {
        entityData.set(GHOST, on);
    }

    public boolean noShadow() {
        return entityData.get(NO_SHADOW);
    }

    public void setNoShadow(boolean on) {
        entityData.set(NO_SHADOW, on);
    }

    public UUID falseArena() {
        return entityData.get(FALSE_ARENA).orElse(null);
    }

    public void setFalseArena(UUID victim) {
        entityData.set(FALSE_ARENA, Optional.ofNullable(victim));
    }

    @Override
    public Component getTypeName() {
        return Component.translatable("entity.pohsmp_core.ereb_hand");
    }

    // ---------------------------------------------------------------- the glass rapier

    @Override
    protected void populateDefaultEquipmentSlots(RandomSource r, DifficultyInstance d) {
        giveRapier();
    }

    public void giveRapier() {
        if (ErebHand.RAPIER != null && ErebHand.RAPIER.isPresent()) setItemSlot(EquipmentSlot.MAINHAND, new ItemStack(ErebHand.RAPIER.get()));
        setDropChance(EquipmentSlot.MAINHAND, 0);
    }

    public void dropRapier() {
        setItemSlot(EquipmentSlot.MAINHAND, ItemStack.EMPTY);
    }

    // ---------------------------------------------------------------- animations (Iron's SyncAnimationPacket → playAnimation)

    private RawAnimation toPlay;
    private final AnimationController<ErebHandBody> action = new AnimationController<>(this, "ereb_hand_action", 2, this::actionPredicate);

    @Override
    public void playAnimation(String name) {
        // the hold is a loop: the grab / squeeze go on into it (the visual letter: «хватка → удержание ↔ сжатие → отпустить»)
        if (name.equals("ereb_hand_grab") || name.equals("ereb_hand_squeeze"))
            toPlay = RawAnimation.begin().thenPlay(name).thenLoop("ereb_hand_grab_hold");
        else toPlay = RawAnimation.begin().thenPlay(name);
    }

    private PlayState actionPredicate(AnimationState<ErebHandBody> state) {
        AnimationController<ErebHandBody> c = state.getController();
        if (toPlay != null) {
            c.forceAnimationReset();
            c.setAnimation(toPlay);
            toPlay = null;
        }
        return PlayState.CONTINUE;
    }

    @Override
    public void registerControllers(AnimatableManager.ControllerRegistrar controllers) {
        controllers.add(action);
        super.registerControllers(controllers);
    }

    /** One of our ereb_hand_* animations is playing (client): Iron's procedural walk and arm poses step aside. */
    public boolean playingAction() {
        return action.getAnimationState() != AnimationController.State.STOPPED;
    }

    @Override
    public boolean isAnimating() {
        return super.isAnimating() || playingAction();
    }

    @Override
    public boolean shouldSheathSword() {
        return false;
    }

    @Override
    public boolean removeWhenFarAway(double d) {
        return false;
    }

    @Override
    public boolean canBeLeashed(Player p) {
        return false;
    }

    protected static boolean fighter(ServerPlayer p) {
        return p.isAlive() && !p.isSpectator() && !p.isCreative();
    }
}
