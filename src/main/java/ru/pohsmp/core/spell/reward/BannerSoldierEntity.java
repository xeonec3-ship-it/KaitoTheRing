package ru.pohsmp.core.spell.reward;

import io.redspace.ironsspellbooks.entity.mobs.IAnimatedAttacker;
import java.util.UUID;
import javax.annotation.Nullable;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.Mth;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.OwnableEntity;
import net.minecraft.world.entity.PathfinderMob;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.ai.goal.FloatGoal;
import net.minecraft.world.entity.monster.Enemy;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import ru.pohsmp.core.spell.HigherSpell;
import software.bernie.geckolib.animatable.GeoEntity;
import software.bernie.geckolib.core.animatable.instance.AnimatableInstanceCache;
import software.bernie.geckolib.core.animation.AnimatableManager;
import software.bernie.geckolib.core.animation.AnimationController;
import software.bernie.geckolib.core.animation.AnimationState;
import software.bernie.geckolib.core.animation.RawAnimation;
import software.bernie.geckolib.core.object.PlayState;
import software.bernie.geckolib.util.GeckoLibUtil;

/**
 * T34 «Знамя Полководца»: a ghost soldier of Martin fighting for the player who planted the banner (pohsmp_core:warlord_banner_soldier).
 * Martin's soldier model and animations (geo/entity/martin_soldier.geo.json), its own class so that Martin's fight code
 * (instanceof MartinSoldierEntity) never takes it for one of his. Allied to its owner: never hits the owner, its team, its pets or
 * other soldiers of the owner (HigherSpell.friendly), takes no damage from them. Fights whoever the owner fights (its attackers and
 * victims), else monsters near the owner; players only in a fight with the owner. Vanishes with the banner (until), with its owner,
 * never saved (gone after a chunk unload / restart), no loot, no experience.
 */
public class BannerSoldierEntity extends PathfinderMob implements GeoEntity, IAnimatedAttacker, OwnableEntity {
    UUID owner;
    long until;
    float damage = 5;
    int attackIn, cooldown, vanishIn = -1, auraFx = -1;
    LivingEntity attacking;
    private final AnimatableInstanceCache cache = GeckoLibUtil.createInstanceCache(this);

    public BannerSoldierEntity(EntityType<? extends PathfinderMob> type, Level level) {
        super(type, level);
        xpReward = 0;
    }

    public static AttributeSupplier.Builder attributes() {
        return Mob.createMobAttributes().add(Attributes.MAX_HEALTH, 30).add(Attributes.ARMOR, 6).add(Attributes.ATTACK_DAMAGE, 5)
                .add(Attributes.MOVEMENT_SPEED, 0.3).add(Attributes.KNOCKBACK_RESISTANCE, 0.5).add(Attributes.FOLLOW_RANGE, 32);
    }

    @Override
    protected void registerGoals() {
        goalSelector.addGoal(0, new FloatGoal(this));   // the rest: tick
    }

    void setup(LivingEntity owner, long until, double hp, float damage) {
        this.owner = owner.getUUID();
        this.until = until;
        this.damage = damage;
        var a = getAttribute(Attributes.MAX_HEALTH);
        if (a != null) a.setBaseValue(hp);
        setHealth(getMaxHealth());
    }

    @Nullable @Override public UUID getOwnerUUID() { return owner; }

    LivingEntity ownerEntity(ServerLevel sl) {
        return owner != null && sl.getEntity(owner) instanceof LivingEntity o && o.isAlive() ? o : null;
    }

    boolean vanishing() {
        return vanishIn >= 0;
    }

    void vanish(ServerLevel sl) {
        if (vanishing()) return;
        vanishIn = RewardMath.BAN_SOLDIER_VANISH;
        setNoAi(true);
        serverTriggerAnimation("martin_soldier_vanish");
        RewardSpell.play(sl, "warlord_banner_soldier_vanish", "martin_soldier_vanish", s -> s.caster(this).at(position()).yaw(getYRot()));
        sl.playSound(null, getX(), getY(), getZ(), SoundEvents.SOUL_ESCAPE, SoundSource.PLAYERS, 1f, 0.8f);
        RewardSpell.stopFx(sl, auraFx);
        auraFx = -1;
    }

    /**
     * FX audit 21.11: killed, unloaded or discarded without vanish() - the endless aura was never stopped and stayed on clients where
     * the soldier had stood (an attached fx falls back to its start point when its entity is gone).
     */
    @Override
    public void remove(RemovalReason reason) {
        if (level() instanceof ServerLevel sl && auraFx > 0) {
            RewardSpell.stopFx(sl, auraFx);
            auraFx = -1;
        }
        super.remove(reason);
    }

    // ---------------------------------------------------------------- tick

    @Override
    public void tick() {
        super.tick();
        if (!(level() instanceof ServerLevel sl)) return;
        if (vanishing()) {
            setDeltaMovement(0, getDeltaMovement().y, 0);
            if (vanishIn-- <= 0) discard();
            return;
        }
        if (tickCount == 1 && auraFx < 0)
            auraFx = RewardSpell.play(sl, "warlord_banner_soldier", "martin_soldier_aura", s -> s.caster(this).at(position()).attach(this));
        LivingEntity o = ownerEntity(sl);
        if (o == null || o.level() != sl || sl.getGameTime() >= until) {
            vanish(sl);
            return;
        }
        if (cooldown > 0) cooldown--;
        if (attackIn > 0 && --attackIn == 0) strike(sl, o);
        if (attackIn > 0) {
            getNavigation().stop();
            return;
        }
        think(sl, o);
    }

    /** May this soldier attack e for its owner? */
    boolean enemy(LivingEntity o, LivingEntity e) {
        if (e == null || !e.isAlive() || e == this || e == o || HigherSpell.friendly(o, e) || e instanceof BannerSoldierEntity) return false;
        if (e instanceof Player p && (p.isCreative() || p.isSpectator())) return false;
        if (e instanceof Player) return HigherSpell.foe(o, e);   // PvP: only someone the owner is fighting
        return true;
    }

    private LivingEntity pick(ServerLevel sl, LivingEntity o) {
        LivingEntity t = getTarget();
        if (t != null && enemy(o, t) && t.distanceToSqr(o) <= 24 * 24) return t;
        if (enemy(o, o.getLastHurtByMob())) return o.getLastHurtByMob();
        if (enemy(o, o.getLastHurtMob())) return o.getLastHurtMob();
        LivingEntity best = null;
        double bd = Double.MAX_VALUE;
        for (LivingEntity e : HigherSpell.around(sl, o.position(), 12, e -> enemy(o, e)
                && (e instanceof Enemy || e instanceof Mob m && (m.getTarget() == o || m.getTarget() instanceof BannerSoldierEntity)))) {
            double d = e.distanceToSqr(this);
            if (d < bd) {
                bd = d;
                best = e;
            }
        }
        return best;
    }

    private void think(ServerLevel sl, LivingEntity o) {
        LivingEntity t = tickCount % 10 == 0 || getTarget() == null || !getTarget().isAlive() ? pick(sl, o) : getTarget();
        if (t != getTarget()) setTarget(t);
        if (t == null) {
            double d = distanceToSqr(o);
            if (d > 24 * 24) {
                teleportTo(o.getX(), o.getY(), o.getZ());
                getNavigation().stop();
            } else if (d > 9 && tickCount % 8 == 0) getNavigation().moveTo(o, 1.0);
            else if (d <= 9) getNavigation().stop();
            return;
        }
        getLookControl().setLookAt(t, 30, 30);
        double dist = distanceTo(t);
        if (dist < 2.6 && cooldown <= 0) {
            attacking = t;
            attackIn = RewardMath.BAN_SOLDIER_HIT;
            cooldown = 20 + getRandom().nextInt(10);
            getNavigation().stop();
            serverTriggerAnimation("martin_soldier_attack");
            return;
        }
        if (tickCount % 8 == 0) getNavigation().moveTo(t, 1.1);
    }

    private void strike(ServerLevel sl, LivingEntity o) {
        LivingEntity t = attacking;
        attacking = null;
        if (t == null || !enemy(o, t) || distanceTo(t) > 3.2) return;
        t.hurt(damageSources().mobAttack(this), damage);
    }

    // ---------------------------------------------------------------- allies

    @Override
    public boolean hurt(DamageSource src, float amount) {
        if (level().isClientSide || vanishing()) return false;
        Entity by = src.getEntity();
        if (by instanceof BannerSoldierEntity s && owner != null && owner.equals(s.owner)) return false;
        if (by != null && level() instanceof ServerLevel sl) {
            LivingEntity o = ownerEntity(sl);
            if (o != null && (by == o || HigherSpell.friendly(o, by))) return false;
        }
        return super.hurt(src, amount);
    }

    @Override
    public boolean isAlliedTo(Entity e) {
        if (owner != null) {
            if (owner.equals(e.getUUID())) return true;
            if (e instanceof OwnableEntity oe && owner.equals(oe.getOwnerUUID())) return true;
            if (level() instanceof ServerLevel sl) {
                LivingEntity o = ownerEntity(sl);
                if (o != null && o != e && o.isAlliedTo(e)) return true;
            }
        }
        return super.isAlliedTo(e);
    }

    @Override protected boolean shouldDropLoot() { return false; }
    @Override public boolean removeWhenFarAway(double d) { return false; }
    @Override public boolean shouldBeSaved() { return false; }
    @Override public boolean causeFallDamage(float d, float m, DamageSource s) { return false; }
    @Override protected boolean shouldDespawnInPeaceful() { return false; }

    // ---------------------------------------------------------------- animations (Martin's soldier set)

    private final AnimationController<BannerSoldierEntity> action = new AnimationController<>(this, "action", 2, this::actionPredicate);
    private RawAnimation toPlay;

    @Override
    public void playAnimation(String name) {
        toPlay = RawAnimation.begin().thenPlay(name);
    }

    private PlayState actionPredicate(AnimationState<BannerSoldierEntity> s) {
        AnimationController<BannerSoldierEntity> c = s.getController();
        if (toPlay != null) {
            c.forceAnimationReset();
            c.setAnimation(toPlay);
            toPlay = null;
        }
        return c.getAnimationState() == AnimationController.State.STOPPED ? PlayState.STOP : PlayState.CONTINUE;
    }

    private static final RawAnimation IDLE = RawAnimation.begin().thenLoop("martin_soldier_idle"),
            WALK = RawAnimation.begin().thenLoop("martin_soldier_walk");

    @Override
    public void registerControllers(AnimatableManager.ControllerRegistrar r) {
        r.add(new AnimationController<>(this, "body", 5, s -> {
            if (action.getAnimationState() != AnimationController.State.STOPPED) return PlayState.STOP;
            return s.setAndContinue(s.isMoving() ? WALK : IDLE);
        }));
        r.add(action);
    }

    @Override
    public AnimatableInstanceCache getAnimatableInstanceCache() {
        return cache;
    }

    /** Client: translucency like Martin's soldiers (0.65, fading in over the first 6 ticks). */
    public float ghostAlpha(float pt) {
        float a = 0.65f;
        if (tickCount < 6) a *= Mth.clamp((tickCount + pt) / 6f, 0, 1);
        return a;
    }
}
