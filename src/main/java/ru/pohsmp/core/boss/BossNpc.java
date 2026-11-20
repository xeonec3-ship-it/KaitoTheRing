package ru.pohsmp.core.boss;

import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.PathfinderMob;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.ai.goal.LookAtPlayerGoal;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import software.bernie.geckolib.animatable.GeoEntity;
import software.bernie.geckolib.core.animatable.instance.AnimatableInstanceCache;
import software.bernie.geckolib.core.animation.AnimatableManager;
import software.bernie.geckolib.core.animation.AnimationController;
import software.bernie.geckolib.core.animation.RawAnimation;
import software.bernie.geckolib.util.GeckoLibUtil;

/**
 * The peaceful NPC a boss becomes after it surrenders (T28 Aris, T29 Martin; owner 20.11: «своя мирная сущность того же вида», no
 * dialogues): stands in its pose <boss>_npc_idle (from the boss's own animation file), looks at players, cannot be hurt (but /kill
 * and creative players still remove it), a click does nothing. One entity type per boss: pohsmp_core:<boss>_npc, registered with
 * {@link Bosses#npc}; drawn by boss/client/BossNpcRenderer with the boss's model.
 */
public class BossNpc extends PathfinderMob implements GeoEntity {
    public final String bossId;
    private final AnimatableInstanceCache cache = GeckoLibUtil.createInstanceCache(this);

    public BossNpc(EntityType<? extends PathfinderMob> type, Level level, String bossId) {
        super(type, level);
        this.bossId = bossId;
        setPersistenceRequired();
    }

    public static AttributeSupplier.Builder attributes() {
        return Mob.createMobAttributes().add(Attributes.MAX_HEALTH, 100).add(Attributes.MOVEMENT_SPEED, 0).add(Attributes.KNOCKBACK_RESISTANCE, 1);
    }

    @Override
    protected void registerGoals() {
        goalSelector.addGoal(1, new LookAtPlayerGoal(this, Player.class, 10f));
    }

    @Override
    public boolean isInvulnerableTo(DamageSource src) {
        if (src.getEntity() instanceof Player p && p.isCreative()) return false;
        return !src.is(net.minecraft.tags.DamageTypeTags.BYPASSES_INVULNERABILITY);
    }

    @Override
    public boolean isPushable() {
        return false;
    }

    @Override
    public boolean removeWhenFarAway(double d) {
        return false;
    }

    @Override
    protected InteractionResult mobInteract(Player p, InteractionHand hand) {
        return InteractionResult.PASS;   // no dialogues (owner 20.11)
    }

    @Override
    protected boolean shouldDropLoot() {
        return false;
    }

    /** Animation name of its pose (in the boss's own animation file). */
    public String idleAnimation() {
        return bossId + "_npc_idle";
    }

    @Override
    public void registerControllers(AnimatableManager.ControllerRegistrar r) {
        r.add(new AnimationController<>(this, "pose", 6, s -> s.setAndContinue(RawAnimation.begin().thenLoop(idleAnimation()))));
    }

    @Override
    public AnimatableInstanceCache getAnimatableInstanceCache() {
        return cache;
    }
}
