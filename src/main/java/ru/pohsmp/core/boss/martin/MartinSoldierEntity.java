package ru.pohsmp.core.boss.martin;

import io.redspace.ironsspellbooks.entity.mobs.IAnimatedAttacker;
import java.util.UUID;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.syncher.EntityDataAccessor;
import net.minecraft.network.syncher.EntityDataSerializers;
import net.minecraft.network.syncher.SynchedEntityData;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.util.Mth;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.ai.attributes.AttributeModifier;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.ai.goal.FloatGoal;
import net.minecraft.world.entity.monster.Monster;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.fx.Fx;
import software.bernie.geckolib.animatable.GeoEntity;
import software.bernie.geckolib.core.animatable.instance.AnimatableInstanceCache;
import software.bernie.geckolib.core.animation.AnimatableManager;
import software.bernie.geckolib.core.animation.AnimationController;
import software.bernie.geckolib.core.animation.AnimationState;
import software.bernie.geckolib.core.animation.RawAnimation;
import software.bernie.geckolib.core.object.PlayState;
import software.bernie.geckolib.util.GeckoLibUtil;

/**
 * A ghost soldier of Martin (geo/entity/martin_soldier.geo.json, drawn translucent α0.65 + glow mask): shield on the left forearm,
 * sword a bone. In «Строй» it holds a slot between Martin and his target (covering him with its shield: MartinFight.filterHit),
 * stabs players that come close; in «Знамя» it charges. Buffs: the banner aura, the war cry; «Приказ стоять насмерть» makes it
 * immune from the front. Dies with its leader (vanishes), no loot, no experience.
 */
public class MartinSoldierEntity extends Monster implements GeoEntity, IAnimatedAttacker {
    private static final EntityDataAccessor<Boolean> BRACE = SynchedEntityData.defineId(MartinSoldierEntity.class, EntityDataSerializers.BOOLEAN);
    private static final UUID BANNER_SPEED = UUID.fromString("b1f0c6a2-3d7e-4e51-9a0b-6c2e5f8d4a31");

    UUID leader;
    /** Slot in the line (index, count) for «Строй». */
    int slot, slots = 1;
    boolean banner;
    long warcryUntil, holdUntil;
    int braceTicks, attackIn, cooldown, vanishIn = -1;
    LivingEntity attacking;
    int bannerFx = -1, warcryFx = -1, holdFx = -1, auraFx = -1;
    private final AnimatableInstanceCache cache = GeckoLibUtil.createInstanceCache(this);

    public MartinSoldierEntity(EntityType<? extends Monster> type, Level level) {
        super(type, level);
        xpReward = 0;
        setPersistenceRequired();
    }

    public static AttributeSupplier.Builder attributes() {
        return Monster.createMonsterAttributes().add(Attributes.MAX_HEALTH, 45).add(Attributes.ARMOR, 10).add(Attributes.ATTACK_DAMAGE, 12)
                .add(Attributes.MOVEMENT_SPEED, 0.27).add(Attributes.KNOCKBACK_RESISTANCE, 0.6).add(Attributes.FOLLOW_RANGE, 32);
    }

    @Override
    protected void defineSynchedData() {
        super.defineSynchedData();
        entityData.define(BRACE, false);
    }

    @Override
    protected void registerGoals() {
        goalSelector.addGoal(0, new FloatGoal(this));   // the rest: tick (it follows its leader's orders)
    }

    void setup(UUID leader, double hp, double armor) {
        this.leader = leader;
        set(Attributes.MAX_HEALTH, hp);
        set(Attributes.ARMOR, armor);
        set(Attributes.MOVEMENT_SPEED, MartinConfig.d(MartinConfig.SOLDIER_SPEED));
        setHealth(getMaxHealth());
    }

    private void set(net.minecraft.world.entity.ai.attributes.Attribute a, double v) {
        var i = getAttribute(a);
        if (i != null) i.setBaseValue(v);
    }

    MartinEntity leader(ServerLevel sl) {
        return leader != null && sl.getEntity(leader) instanceof MartinEntity m && m.isAlive() ? m : null;
    }

    boolean vanishing() {
        return vanishIn >= 0;
    }

    /** Rises out of the ground (martin_soldier_spawn), on the clients a tick after it was added. */
    void riseAnim() {
        serverTriggerAnimation("martin_soldier_spawn");
    }

    /** Fades away (martin_soldier_vanish + fx), removed 0.8 s later. */
    void vanish(ServerLevel sl) {
        if (vanishing()) return;
        vanishIn = MartinMath.SOLDIER_VANISH;
        setNoAi(true);
        serverTriggerAnimation("martin_soldier_vanish");
        Fx.play(sl, Fx.fx("martin_soldier_vanish").caster(this).at(position()).yaw(getYRot()));
        sl.playSound(null, getX(), getY(), getZ(), ru.pohsmp.core.boss.BossCore.sound("martin.soldier_vanish"), net.minecraft.sounds.SoundSource.HOSTILE, 1, 1);
        stopFx(sl);
    }

    /** FX audit 21.11: unloaded / discarded without its own end (no save: the fight respawns it) - the endless fx stayed as a ghost. */
    @Override
    public void remove(RemovalReason reason) {
        if (level() instanceof ServerLevel sl) stopFx(sl);
        super.remove(reason);
    }

    void stopFx(ServerLevel sl) {
        for (int id : new int[] {bannerFx, warcryFx, holdFx, auraFx}) if (id > 0) Fx.stop(sl, id, "");
        bannerFx = warcryFx = holdFx = auraFx = -1;
    }

    void brace(int ticks) {
        braceTicks = Math.max(braceTicks, ticks);
    }

    double damageMult(long now) {
        double m = 1;
        if (banner) m *= MartinConfig.d(MartinConfig.BANNER_DAMAGE_MULT);
        if (now < warcryUntil) m *= MartinConfig.d(MartinConfig.WARCRY_MULT);
        return m;
    }

    void setBanner(ServerLevel sl, boolean on) {
        if (banner == on) return;
        banner = on;
        var sp = getAttribute(Attributes.MOVEMENT_SPEED);
        if (sp != null) {
            sp.removeModifier(BANNER_SPEED);
            if (on) sp.addTransientModifier(new AttributeModifier(BANNER_SPEED, "martin_banner", MartinConfig.d(MartinConfig.BANNER_SPEED_MULT) - 1,
                    AttributeModifier.Operation.MULTIPLY_TOTAL));
        }
        if (on && bannerFx < 0) bannerFx = Fx.play(sl, Fx.fx("martin_banner_buff").caster(this).at(position()).attach(this));
        if (!on && bannerFx > 0) {
            Fx.stop(sl, bannerFx, "");
            bannerFx = -1;
        }
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
        if (tickCount == 1 && auraFx < 0) auraFx = Fx.play(sl, Fx.fx("martin_soldier_aura").caster(this).at(position()).attach(this));
        MartinEntity m = leader(sl);
        if (m == null) {
            vanish(sl);
            return;
        }
        long now = sl.getGameTime();
        if (warcryFx > 0 && now >= warcryUntil) {
            Fx.stop(sl, warcryFx, "");
            warcryFx = -1;
        }
        if (holdFx > 0 && now >= holdUntil) {
            Fx.stop(sl, holdFx, "");
            holdFx = -1;
        }
        boolean brace = braceTicks > 0 || now < holdUntil;
        if (braceTicks > 0) braceTicks--;
        if (entityData.get(BRACE) != brace) entityData.set(BRACE, brace);
        if (cooldown > 0) cooldown--;
        if (attackIn > 0 && --attackIn == 0) strike(sl, m, now);
        if (attackIn > 0 || now < holdUntil || !m.bossCore().started() || m.bossCore().inFinale()) {
            getNavigation().stop();
            return;
        }
        think(sl, m, now);
    }

    /** Pick a target, hold the line or charge, stab. */
    private void think(ServerLevel sl, MartinEntity m, long now) {
        LivingEntity t = getTarget();
        if (t == null || !t.isAlive() || t.distanceToSqr(this) > 32 * 32 || t instanceof Player p && (p.isCreative() || p.isSpectator())) {
            t = m.getTarget() instanceof Player p && !p.isCreative() && !p.isSpectator() ? p : null;
            if (t == null) {
                Player p = sl.getNearestPlayer(this, 24);
                t = p != null && !p.isCreative() && !p.isSpectator() ? p : null;
            }
            setTarget(t);
        }
        if (t == null) return;
        double d = distanceTo(t);
        getLookControl().setLookAt(t, 30, 30);
        if (d < 2.6 && cooldown <= 0) {
            attacking = t;
            attackIn = MartinMath.SOLDIER_HIT;
            cooldown = MartinMath.SOLDIER_ATTACK + 10 + getRandom().nextInt(15);
            getNavigation().stop();
            serverTriggerAnimation("martin_soldier_attack");
            return;
        }
        if (tickCount % 8 != 0) return;
        if (m.fight.formationActive() && d > 3.5) {
            // «Строй»: a slot on an arc 3 blocks in front of Martin, towards his target
            Vec3 c = m.position();
            Vec3 to = (m.getTarget() != null ? m.getTarget().position() : t.position()).subtract(c).multiply(1, 0, 1);
            double base = to.lengthSqr() < 1e-3 ? Math.toRadians(m.getYRot() + 90) : Math.atan2(to.z, to.x);
            double spread = Math.toRadians(150);
            double a = base + (slots <= 1 ? 0 : -spread / 2 + spread * slot / (slots - 1));
            Vec3 goal = c.add(Math.cos(a) * 3.0, 0, Math.sin(a) * 3.0);
            if (goal.distanceToSqr(position()) > 0.8) getNavigation().moveTo(goal.x, goal.y, goal.z, 1.0);
            else getNavigation().stop();
        } else getNavigation().moveTo(t, 1.0);
    }

    private void strike(ServerLevel sl, MartinEntity m, long now) {
        LivingEntity t = attacking;
        attacking = null;
        if (t == null || !t.isAlive() || distanceTo(t) > 3.2) return;
        float dmg = (float) (MartinConfig.d(MartinConfig.SOLDIER_DAMAGE) * damageMult(now));
        t.hurt(MartinFight.attackSource(sl, this), dmg);
    }

    @Override
    public boolean hurt(DamageSource src, float amount) {
        if (level().isClientSide || vanishing()) return false;
        Entity by = src.getEntity();
        if (by instanceof MartinEntity || by instanceof MartinSoldierEntity) return false;
        if (level() instanceof ServerLevel sl && sl.getGameTime() < holdUntil) {
            Vec3 from = src.getSourcePosition();
            if (from != null && MartinMath.inFront(getYRot(), from.x - getX(), from.z - getZ(), MartinConfig.d(MartinConfig.HOLD_ARC))) {
                Fx.play(sl, Fx.fx("martin_hold_deflect").at(position().add(from.subtract(position()).multiply(1, 0, 1).normalize().scale(0.6)).add(0, 1.2, 0)));
                return false;
            }
        }
        if (banner) amount *= (float) MartinConfig.d(MartinConfig.BANNER_TAKEN_MULT);
        return super.hurt(src, amount);
    }

    @Override
    public void die(DamageSource src) {
        super.die(src);
        if (level() instanceof ServerLevel sl) stopFx(sl);
    }

    @Override
    public boolean isAlliedTo(Entity e) {
        return e instanceof MartinEntity || e instanceof MartinSoldierEntity || e instanceof MartinBannerEntity || super.isAlliedTo(e);
    }

    @Override
    protected boolean shouldDropLoot() {
        return false;
    }

    @Override
    public boolean removeWhenFarAway(double d) {
        return false;
    }

    @Override
    protected boolean shouldDespawnInPeaceful() {
        return false;   // summoned by an admin: stays on Peaceful too
    }

    @Override
    public boolean causeFallDamage(float d, float m, DamageSource s) {
        return false;
    }

    @Override
    public void addAdditionalSaveData(CompoundTag tag) {
        super.addAdditionalSaveData(tag);
        if (leader != null) tag.putUUID("martin", leader);
    }

    @Override
    public void readAdditionalSaveData(CompoundTag tag) {
        super.readAdditionalSaveData(tag);
        if (tag.hasUUID("martin")) leader = tag.getUUID("martin");
    }

    // ---------------------------------------------------------------- animations

    private final AnimationController<MartinSoldierEntity> action = new AnimationController<>(this, "action", 2, this::actionPredicate);
    private RawAnimation toPlay;

    @Override
    public void playAnimation(String name) {
        toPlay = RawAnimation.begin().thenPlay(name);
    }

    private PlayState actionPredicate(AnimationState<MartinSoldierEntity> s) {
        AnimationController<MartinSoldierEntity> c = s.getController();
        if (toPlay != null) {
            c.forceAnimationReset();
            c.setAnimation(toPlay);
            toPlay = null;
        }
        return c.getAnimationState() == AnimationController.State.STOPPED ? PlayState.STOP : PlayState.CONTINUE;
    }

    private static final RawAnimation IDLE = RawAnimation.begin().thenLoop("martin_soldier_idle"),
            WALK = RawAnimation.begin().thenLoop("martin_soldier_walk"), BRACE_LOOP = RawAnimation.begin().thenLoop("martin_soldier_brace");

    @Override
    public void registerControllers(AnimatableManager.ControllerRegistrar r) {
        r.add(new AnimationController<>(this, "body", 5, s -> {
            if (action.getAnimationState() != AnimationController.State.STOPPED) return PlayState.STOP;
            if (entityData.get(BRACE)) return s.setAndContinue(BRACE_LOOP);
            return s.setAndContinue(s.isMoving() ? WALK : IDLE);
        }));
        r.add(action);
    }

    @Override
    public AnimatableInstanceCache getAnimatableInstanceCache() {
        return cache;
    }

    /** Client: its translucency (0.65, fading in over the first 6 ticks). */
    public float ghostAlpha(float pt) {
        float a = 0.65f;
        if (tickCount < 6) a *= Mth.clamp((tickCount + pt) / 6f, 0, 1);
        return a;
    }
}
