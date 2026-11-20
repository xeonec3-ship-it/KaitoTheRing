package ru.pohsmp.core.boss.ereb;

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
 * Ereb's body, shared by the boss and his reflections (they must not be told apart): Iron's casting mob (the bones of
 * abstract_casting_mob, Iron's procedural walk and cast poses), our model / textures / animations (client: ErebRenderer), the rapier in
 * the right hand, the «ereb_*» animations started from the server ({@link #serverTriggerAnimation}), and three synced looks: the smile
 * of the finale (ereb_smile.png), a borrowed face (a participant's skin and name: «Чужое лицо», «Ложный союзник»), nothing else.
 */
public abstract class ErebBody extends AbstractSpellCastingMob implements IAnimatedAttacker {
    private static final EntityDataAccessor<Boolean> SMILE = SynchedEntityData.defineId(ErebBody.class, EntityDataSerializers.BOOLEAN);
    private static final EntityDataAccessor<Optional<UUID>> FACE = SynchedEntityData.defineId(ErebBody.class, EntityDataSerializers.OPTIONAL_UUID);
    private static final EntityDataAccessor<String> FACE_NAME = SynchedEntityData.defineId(ErebBody.class, EntityDataSerializers.STRING);
    /** «Предательство» is on: every player of the fight sees the others as him (client: ErebClient). */
    private static final EntityDataAccessor<Boolean> BETRAYAL = SynchedEntityData.defineId(ErebBody.class, EntityDataSerializers.BOOLEAN);

    protected ErebBody(EntityType<? extends PathfinderMob> type, Level level) {
        super(type, level);
    }

    @Override
    protected void defineSynchedData() {
        super.defineSynchedData();
        entityData.define(SMILE, false);
        entityData.define(FACE, Optional.empty());
        entityData.define(FACE_NAME, "");
        entityData.define(BETRAYAL, false);
    }

    // ---------------------------------------------------------------- looks

    public boolean smiling() {
        return entityData.get(SMILE);
    }

    public void setSmile(boolean on) {
        entityData.set(SMILE, on);
    }

    public boolean betrayal() {
        return entityData.get(BETRAYAL);
    }

    public void setBetrayal(boolean on) {
        entityData.set(BETRAYAL, on);
    }

    /** The player whose look he wears now, or null (his own). */
    public UUID face() {
        return entityData.get(FACE).orElse(null);
    }

    public String faceName() {
        return entityData.get(FACE_NAME);
    }

    public void setFace(Player p) {
        entityData.set(FACE, p == null ? Optional.empty() : Optional.of(p.getUUID()));
        entityData.set(FACE_NAME, p == null ? "" : p.getGameProfile().getName());
    }

    public void setFace(UUID id, String name) {
        entityData.set(FACE, Optional.ofNullable(id));
        entityData.set(FACE_NAME, name == null ? "" : name);
    }

    /** The name everyone reads: his own, or the borrowed one. */
    @Override
    public Component getTypeName() {
        return Component.translatable("entity.pohsmp_core.ereb");
    }

    // ---------------------------------------------------------------- the rapier

    @Override
    protected void populateDefaultEquipmentSlots(RandomSource r, DifficultyInstance d) {
        giveRapier();
    }

    public void giveRapier() {
        if (Ereb.RAPIER != null && Ereb.RAPIER.isPresent()) setItemSlot(EquipmentSlot.MAINHAND, new ItemStack(Ereb.RAPIER.get()));
        setDropChance(EquipmentSlot.MAINHAND, 0);
    }

    // ---------------------------------------------------------------- animations (Iron's SyncAnimationPacket → playAnimation)

    private RawAnimation toPlay;
    private final AnimationController<ErebBody> action = new AnimationController<>(this, "ereb_action", 0, this::actionPredicate);

    @Override
    public void playAnimation(String name) {
        toPlay = RawAnimation.begin().thenPlay(name);
    }

    private PlayState actionPredicate(AnimationState<ErebBody> state) {
        AnimationController<ErebBody> c = state.getController();
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

    /** One of our ereb_* animations is playing (client): Iron's procedural walk and arm poses step aside. */
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
