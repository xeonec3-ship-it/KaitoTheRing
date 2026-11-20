package ru.pohsmp.core.boss.ereb;

import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.PathfinderMob;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.fx.Fx;
import ru.pohsmp.core.illusion.Illusions;

/**
 * A reflection of Ereb, drawn exactly like him (same body, rapier, look). The T22 copies are false PLAYERS drawn by the victims'
 * clients; his copies must look like him, so they are entities of his own body. Three kinds:
 * <ul>
 * <li>MIRROR («Отражения», phase 1): walks at the players and thrusts (illusory damage, copies_damage, comes back after
 * [illusion.mirror_images] copyDamageReturnSeconds); breaks after hitsToBreak hits (the T22 poof); Ereb swaps places with one now and
 * then.</li>
 * <li>GHOST («Пелена»): a false silhouette beside him; strikes and arrows go through it as through air.</li>
 * <li>RUNNER («Ложный шаг»): runs on along a straight course and thrusts once while he is not drawn.</li>
 * </ul>
 * Not saved, no loot; gone with him.
 */
public class ErebReflection extends ErebBody {
    public enum Kind { MIRROR, GHOST, RUNNER }

    private Kind kind = Kind.MIRROR;
    private ErebEntity owner;
    private int life = 400, hits = 3, cooldown = 20, swingAt = -1, tag;
    private float damage = 6;
    private int damageReturn = 160;
    private Vec3 offset = Vec3.ZERO, course = Vec3.ZERO;
    private ServerPlayer swingAtWho;

    public ErebReflection(EntityType<? extends PathfinderMob> type, Level level) {
        super(type, level);
        giveRapier();
    }

    public void setup(ErebEntity owner, Kind kind, int life, int hits, float damage, int damageReturn, int tag) {
        this.owner = owner;
        this.kind = kind;
        this.life = life;
        this.hits = hits;
        this.damage = damage;
        this.damageReturn = damageReturn;
        this.tag = tag;
        this.offset = position().subtract(owner.position());
        if (kind != Kind.MIRROR) setNoAi(true);
        setFace(owner.face(), owner.faceName());
    }

    public void course(Vec3 velocityPerTick) {
        course = velocityPerTick;
    }

    public Kind kind() {
        return kind;
    }

    @Override
    protected void registerGoals() {}

    @Override
    public void tick() {
        super.tick();
        if (!(level() instanceof ServerLevel sl)) return;
        if (owner == null || !owner.isAlive() || owner.bossCore().inFinale() || --life <= 0) {
            poof(sl);
            return;
        }
        switch (kind) {
            case GHOST -> {   // keeps its place beside him, looks where he looks
                Vec3 p = owner.position().add(offset);
                moveTo(p.x, p.y, p.z, owner.getYRot(), owner.getXRot());
                setYHeadRot(owner.getYHeadRot());
                setYBodyRot(owner.yBodyRot);
            }
            case RUNNER -> {
                Vec3 p = position().add(course);
                setDeltaMovement(course);
                moveTo(p.x, p.y, p.z, getYRot(), 0);
                if (swingAt < 0) swingAt = life / 2;
                if (life == swingAt) {
                    serverTriggerAnimation("ereb_lunge");
                    swingAtWho = nearest(sl, 3.2);
                }
                if (life == swingAt - ErebMath.LUNGE_HIT && swingAtWho != null) thrust(swingAtWho);
            }
            default -> mirror(sl);
        }
    }

    /** MIRROR: walks at the nearest player, thrusts at it now and then (illusory). */
    private void mirror(ServerLevel sl) {
        ServerPlayer t = nearest(sl, 24);
        if (t == null) return;
        getLookControl().setLookAt(t, 30, 30);
        double d = distanceTo(t);
        if (d <= 2.4) getNavigation().stop();
        else if (tickCount % 10 == 0 || getNavigation().isDone()) getNavigation().moveTo(t, 1.0);
        if (swingAtWho != null && --swingAt == 0) {
            if (swingAtWho.isAlive() && distanceTo(swingAtWho) < 3.4) thrust(swingAtWho);
            swingAtWho = null;
        }
        if (--cooldown <= 0 && d < 2.8 && swingAtWho == null) {
            serverTriggerAnimation("ereb_lunge");
            swingAtWho = t;
            swingAt = ErebMath.LUNGE_HIT;
            cooldown = ErebMath.meleePause(ErebConfig.i(ErebConfig.MELEE_MIN), ErebConfig.i(ErebConfig.MELEE_MAX), random.nextDouble()) + ErebMath.LUNGE;
        }
    }

    private void thrust(ServerPlayer t) {
        if (!(level() instanceof ServerLevel sl) || owner == null) return;
        Illusions.illusory(owner, t, damage, damageReturn, tag);
        Fx.play(sl, Fx.fx("ereb_thrust").caster(this).at(position()).yaw(getYRot()));
        sl.playSound(null, getX(), getY() + 1, getZ(), ErebFight.sound("ereb.thrust"), SoundSource.HOSTILE, 1, 1);
    }

    private ServerPlayer nearest(ServerLevel sl, double r) {
        ServerPlayer best = null;
        double bd = r * r;
        for (ServerPlayer p : sl.players()) {
            if (!fighter(p)) continue;
            double d = p.distanceToSqr(this);
            if (d < bd) {
                bd = d;
                best = p;
            }
        }
        return best;
    }

    /** Swapped with Ereb: the ghost keeps its offset from where he is now. */
    void moved() {
        if (owner != null) offset = position().subtract(owner.position());
    }

    /** Gone the way a T22 copy goes: the neutral poof. */
    public void poof(ServerLevel sl) {
        if (isRemoved()) return;
        Fx.play(sl, Fx.fx("illusion_poof").at(position()));
        sl.playSound(null, getX(), getY() + 1, getZ(), SoundEvents.AMETHYST_CLUSTER_BREAK, SoundSource.HOSTILE, 0.8f, 1.4f);
        discard();
    }

    // ---------------------------------------------------------------- not a real body

    @Override
    public boolean hurt(DamageSource src, float amount) {
        if (!(level() instanceof ServerLevel sl) || kind == Kind.GHOST) return false;
        if (!(src.getEntity() instanceof Player)) return false;
        if (invulnerableTime > 10) return false;
        invulnerableTime = 20;
        level().broadcastDamageEvent(this, src);   // the hurt flash and sound, like a real one
        if (--hits <= 0) poof(sl);
        return true;
    }

    @Override
    public boolean isPickable() {
        return kind != Kind.GHOST && super.isPickable();
    }

    @Override
    public boolean canBeHitByProjectile() {
        return kind != Kind.GHOST && super.canBeHitByProjectile();
    }

    @Override
    public boolean isPushable() {
        return kind == Kind.MIRROR;
    }

    @Override
    public boolean shouldBeSaved() {
        return false;
    }

    @Override
    protected void dropAllDeathLoot(DamageSource src) {}

    @Override
    public boolean isAlliedTo(net.minecraft.world.entity.Entity e) {
        return e instanceof ErebBody || super.isAlliedTo(e);
    }
}
