package ru.pohsmp.core.boss.erebhand;

import java.util.Optional;
import java.util.UUID;
import net.minecraft.network.syncher.EntityDataAccessor;
import net.minecraft.network.syncher.EntityDataSerializers;
import net.minecraft.network.syncher.SynchedEntityData;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.PathfinderMob;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import ru.pohsmp.core.fx.Fx;

/**
 * «Отражение-предатель»: a glass copy of one player out of a mirror (the client draws it as that player — its skin, its weapon — in
 * glass). For traitor_reflection_seconds it attacks that player's allies (none — the player itself). Its original breaks it with one hit,
 * anyone else with three; not broken in time — it bursts into shards (an area hit). Its hits are Ereb's (the dream and the finisher see
 * him). Not saved.
 */
public class ErebHandTraitor extends PathfinderMob {
    private static final EntityDataAccessor<Optional<UUID>> ORIGINAL = SynchedEntityData.defineId(ErebHandTraitor.class, EntityDataSerializers.OPTIONAL_UUID);
    private static final EntityDataAccessor<String> NAME = SynchedEntityData.defineId(ErebHandTraitor.class, EntityDataSerializers.STRING);
    private ErebHandEntity boss;
    private int life = 120, hitsByOthers = 3, swingIn = 20;
    private boolean burst, warned;
    private int copyFx = -1;

    public ErebHandTraitor(EntityType<? extends PathfinderMob> type, Level level) {
        super(type, level);
    }

    public static AttributeSupplier.Builder attributes() {
        return Mob.createMobAttributes().add(Attributes.MAX_HEALTH, 40).add(Attributes.MOVEMENT_SPEED, 0.32).add(Attributes.FOLLOW_RANGE, 32)
                .add(Attributes.KNOCKBACK_RESISTANCE, 1.0);
    }

    @Override
    protected void defineSynchedData() {
        super.defineSynchedData();
        entityData.define(ORIGINAL, Optional.empty());
        entityData.define(NAME, "");
    }

    public void setup(ErebHandEntity boss, ServerPlayer original, int life) {
        this.boss = boss;
        this.life = life;
        this.hitsByOthers = ErebHandMath.traitorHits(false, 1, ErebHandConfig.i(ErebHandConfig.TRAITOR_HITS_OTHERS));
        entityData.set(ORIGINAL, Optional.of(original.getUUID()));
        entityData.set(NAME, original.getGameProfile().getName());
        setItemSlot(EquipmentSlot.MAINHAND, original.getMainHandItem().copy());   // his weapon, seen by everyone
        setDropChance(EquipmentSlot.MAINHAND, 0);
    }

    @Override
    public void onAddedToWorld() {
        super.onAddedToWorld();
        if (level() instanceof ServerLevel sl && copyFx < 0)
            copyFx = Fx.play(sl, Fx.fx("ereb_hand_traitor_copy").caster(this).at(position()).attach(this).duration(life + 2));
    }

    /** The player it reflects. */
    public UUID original() {
        return entityData.get(ORIGINAL).orElse(null);
    }

    public String originalName() {
        return entityData.get(NAME);
    }

    @Override
    protected void registerGoals() {}

    /** The swing timer (getAttackAnim, the renderer's attackTime) runs only where aiStep calls updateSwingTime — Monster and Player do,
     *  PathfinderMob does not: without this the copy's swing() never animated (its weapon stayed still while it hit). */
    @Override
    public void aiStep() {
        updateSwingTime();
        super.aiStep();
    }

    @Override
    public void tick() {
        super.tick();
        if (!(level() instanceof ServerLevel sl)) return;
        if (boss == null || !boss.isAlive() || boss.bossCore().inFinale()) {
            shatter(sl, false);
            return;
        }
        if (--life <= 0) {
            shatter(sl, true);
            return;
        }
        if (life <= ErebHandMath.TRAITOR_BURST_WARN && !warned) {   // its last second: gold cracks and the ring r3 on the ground
            warned = true;
            Fx.play(sl, Fx.fx("ereb_hand_traitor_burst_warn").caster(this).at(position()).attach(this));
        }
        ServerPlayer t = victim(sl);
        if (t == null) return;
        getLookControl().setLookAt(t, 30, 30);
        double d = distanceTo(t);
        if (d > 2.0 && (tickCount % 8 == 0 || getNavigation().isDone())) getNavigation().moveTo(t, 1.1);
        if (--swingIn <= 0 && d < 2.4) {
            swingIn = ErebHandMath.TRAITOR_SWING;
            swing(InteractionHand.MAIN_HAND, true);
            boss.fight.reflectionHit(t, ErebHandConfig.d(ErebHandConfig.TRAITOR_DAMAGE));
            sl.playSound(null, getX(), getY() + 1, getZ(), ru.pohsmp.core.boss.BossCore.sound("ereb.swish"), SoundSource.HOSTILE, 1.2f, 1);
        }
    }

    /** The nearest ally of its original (not the original); none — the original itself. */
    private ServerPlayer victim(ServerLevel sl) {
        UUID orig = original();
        ServerPlayer best = null, self = null;
        double bd = 32 * 32;
        for (ServerPlayer p : sl.players()) {
            if (!p.isAlive() || p.isSpectator() || p.isCreative()) continue;
            if (p.getUUID().equals(orig)) {
                self = p;
                continue;
            }
            double d = p.distanceToSqr(this);
            if (d < bd) {
                bd = d;
                best = p;
            }
        }
        return best != null ? best : self != null && self.distanceToSqr(this) < 32 * 32 ? self : null;
    }

    /** FX audit 21.11: discarded by the fight's cleanup (false death, /kill) or unloaded - its aura snapped back to where it appeared. */
    @Override
    public void remove(RemovalReason reason) {
        if (copyFx >= 0 && level() instanceof ServerLevel sl) Fx.stop(sl, copyFx, "");
        copyFx = -1;
        super.remove(reason);
    }

    /** Broken (by hits) or burst (time is up: shards round it). */
    private void shatter(ServerLevel sl, boolean explode) {
        if (isRemoved()) return;
        if (explode && !burst && boss != null && boss.isAlive()) {
            burst = true;
            boss.fight.traitorBurst(sl, this);
        }
        sl.playSound(null, getX(), getY() + 1, getZ(), ru.pohsmp.core.boss.BossCore.sound(explode ? "ereb_hand.shard_burst" : "ereb.reflection_break"), SoundSource.HOSTILE, 1.5f, 1);
        if (copyFx >= 0) Fx.stop(sl, copyFx, "");
        copyFx = -1;
        if (!explode) Fx.play(sl, Fx.fx("ereb_hand_traitor_shatter").caster(this).at(position()));
        discard();
    }

    @Override
    public boolean hurt(DamageSource src, float amount) {
        if (!(level() instanceof ServerLevel sl) || isRemoved()) return false;
        if (!(src.getEntity() instanceof Player p)) return false;
        if (invulnerableTime > 10) return false;
        invulnerableTime = 20;
        level().broadcastDamageEvent(this, src);
        Fx.play(sl, Fx.fx("ereb_hand_traitor_hit").caster(this).at(position()));
        if (p.getUUID().equals(original())) {
            if (ErebHandConfig.i(ErebHandConfig.TRAITOR_HITS_ORIGINAL) <= 1) shatter(sl, false);
            else if (--hitsByOthers <= 0) shatter(sl, false);
        } else if (--hitsByOthers <= 0) shatter(sl, false);
        return true;
    }

    @Override
    public boolean isPushable() {
        return true;
    }

    @Override
    public boolean shouldBeSaved() {
        return false;
    }

    @Override
    protected void dropAllDeathLoot(DamageSource src) {}

    @Override
    public boolean removeWhenFarAway(double d) {
        return false;
    }

    @Override
    public boolean isAlliedTo(net.minecraft.world.entity.Entity e) {
        return e instanceof ErebHandBody || super.isAlliedTo(e);
    }
}
