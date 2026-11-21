package ru.pohsmp.core.boss.erebhand;

import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.PathfinderMob;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import ru.pohsmp.core.fx.Fx;

/**
 * A reflection of Ereb, the Hand of Lies, drawn like him (same body, mask, rapier). Two kinds:
 * <ul>
 * <li>DOUBLE («Лживое слово», phase 1 and 3): walks at the nearest player and strikes once with «false flame»; a REAL one burns and
 * hurts (double_fire_damage, boss_attack, through the boss so the finisher and the dream know it), a FALSE one leaves only a faint glass
 * glint (ereb_hand_mirror_strike_fake). Breaks after double_hits hits (the T22 poof).</li>
 * <li>STRIKE («Тысяча отражений»): a see-through Ereb out of a mirror, ereb_hand_reflection_strike, one thrust on `hit`, gone at 1 s.</li>
 * </ul>
 * Not saved, no loot; gone with him.
 */
public class ErebHandReflection extends ErebHandBody {
    public enum Kind { DOUBLE, STRIKE, DECOY }

    private Kind kind = Kind.DOUBLE;
    private ErebHandEntity owner;
    private boolean real;
    private int life = 240, hits = 2, struck = -1;
    private ServerPlayer victim;

    public ErebHandReflection(EntityType<? extends PathfinderMob> type, Level level) {
        super(type, level);
        giveRapier();
    }

    public void setup(ErebHandEntity owner, Kind kind, boolean real, int life, int hits, ServerPlayer victim) {
        this.owner = owner;
        this.kind = kind;
        this.real = real;
        this.life = life;
        this.hits = hits;
        this.victim = victim;
        setMask(owner.mask());
        setMaskOff(owner.maskOff());
        if (kind == Kind.STRIKE) {
            setNoAi(true);
            setGhost(true);
        }
        if (kind == Kind.DECOY) {   // «Ложное отступление»: stands «opened up», no shadow (the hint)
            setNoAi(true);
            setNoShadow(true);
        }
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
            if (kind != Kind.DOUBLE) discard();
            else poof(sl);
            return;
        }
        setMask(owner.mask());
        setMaskOff(owner.maskOff());
        if (kind == Kind.STRIKE) strike(sl);
        else if (kind == Kind.DOUBLE) walkAndStrike(sl);
    }

    /** STRIKE: out of the glass already in the lunge; the thrust on REFL_HIT. */
    private void strike(ServerLevel sl) {
        if (tickCount == 1) serverTriggerAnimation("ereb_hand_reflection_strike");
        if (tickCount == ErebHandMath.REFL_HIT + 1 && victim != null && victim.isAlive() && victim.distanceTo(this) < 3.6) {
            owner.fight.reflectionHit(victim, ErebHandConfig.d(ErebHandConfig.THOUSAND_DAMAGE));
            Fx.play(sl, Fx.fx("ereb_thrust").caster(this).at(position()).yaw(getYRot()));
        }
    }

    /** DOUBLE: to the nearest player, one strike of «false flame». */
    private void walkAndStrike(ServerLevel sl) {
        if (struck >= 0) {   // the strike is out: on its hit, then it fades
            if (--struck == 0) {
                ServerPlayer t = victim;
                Fx.play(sl, Fx.fx("ereb_thrust").caster(this).at(position()).yaw(getYRot()));
                if (real) {
                    if (t != null && t.isAlive() && distanceTo(t) < 3.6) {
                        owner.fight.reflectionHit(t, ErebHandConfig.d(ErebHandConfig.DOUBLE_FIRE_DAMAGE));
                        t.setSecondsOnFire(3);
                    }
                    Fx.play(sl, Fx.fx("ereb_hand_false_flame_real").at(position().add(getLookAngle().multiply(1.5, 0, 1.5))).scale(0.5).duration(24));
                    sl.playSound(null, getX(), getY() + 1, getZ(), ru.pohsmp.core.boss.BossCore.sound("ereb_hand.changeling"), SoundSource.HOSTILE, 1.2f, 1);
                } else {   // a false one: only the faint glass glint
                    Fx.play(sl, Fx.fx("ereb_hand_mirror_strike_fake").caster(this).at(position().add(0, 1, 0)).yaw(getYRot()));
                }
                life = Math.min(life, 16);
            }
            return;
        }
        ServerPlayer t = nearest(sl, 28);
        if (t == null) return;
        getLookControl().setLookAt(t, 30, 30);
        double d = distanceTo(t);
        if (d <= 2.4) getNavigation().stop();
        else if (tickCount % 10 == 0 || getNavigation().isDone()) getNavigation().moveTo(t, 1.05);
        if (d < 2.8 && tickCount > 20) {
            victim = t;
            serverTriggerAnimation("ereb_hand_lunge");
            struck = ErebHandMath.LUNGE_HIT;
            getNavigation().stop();
        }
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

    /** Gone the way a T22 copy goes: the neutral poof. */
    public void poof(ServerLevel sl) {
        if (isRemoved()) return;
        Fx.play(sl, Fx.fx("illusion_poof").at(position()));
        sl.playSound(null, getX(), getY() + 1, getZ(), ru.pohsmp.core.boss.BossCore.sound("ereb.reflection_break"), SoundSource.HOSTILE, 1.2f, 1);
        discard();
    }

    // ---------------------------------------------------------------- not a real body

    @Override
    public boolean hurt(DamageSource src, float amount) {
        if (!(level() instanceof ServerLevel sl) || kind == Kind.STRIKE) return false;
        if (!(src.getEntity() instanceof Player)) return false;
        if (kind == Kind.DECOY) {
            level().broadcastDamageEvent(this, src);
            owner.fight.decoyStruck(sl, (Player) src.getEntity());
            return true;
        }
        if (invulnerableTime > 10) return false;
        invulnerableTime = 20;
        level().broadcastDamageEvent(this, src);   // the hurt flash and sound, like a real one
        if (--hits <= 0) poof(sl);
        return true;
    }

    @Override
    public boolean isPickable() {
        return kind != Kind.STRIKE && super.isPickable();
    }

    @Override
    public boolean canBeHitByProjectile() {
        return kind != Kind.STRIKE && super.canBeHitByProjectile();
    }

    @Override
    public boolean isPushable() {
        return kind == Kind.DOUBLE;
    }

    @Override
    public boolean shouldBeSaved() {
        return false;
    }

    @Override
    protected void dropAllDeathLoot(DamageSource src) {}

    @Override
    public boolean isAlliedTo(net.minecraft.world.entity.Entity e) {
        return e instanceof ErebHandBody || super.isAlliedTo(e);
    }
}
