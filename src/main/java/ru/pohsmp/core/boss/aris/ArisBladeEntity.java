package ru.pohsmp.core.boss.aris;

import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.ClipContext;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.HitResult;
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.fx.Fx;

/**
 * «Оружейная»: a hovering blade of her forging. Circles round Aris; every blade_attack_ticks it stops, turns to a player (a visible
 * pause and a ring of metal — the warning), darts at that player along a straight line and flies back. It can be struck down
 * (health blade_hp × the players multiplier): fx aris_blade_shatter. Drawn by fx aris_blade_sword / aris_blade_glaive (caster and
 * follow = this entity; yaw from the entity, pitch sent by Fx.move).
 */
public class ArisBladeEntity extends Mob {
    private enum State { ORBIT, AIM, DART, BACK }

    private int ownerId = -1, slot;
    private State state = State.ORBIT;
    private int timer, fx = -1;
    private LivingEntity target;
    private Vec3 dartDir = Vec3.ZERO;
    private boolean hitDone;
    private float lastPitch = 999;

    public ArisBladeEntity(EntityType<? extends Mob> type, Level level) {
        super(type, level);
        noPhysics = true;
        setNoGravity(true);
        setNoAi(true);
        xpReward = 0;
    }

    /** Server: after the entity was added. */
    void setup(ArisEntity owner, int slot, double hp, int firstAttack) {
        this.ownerId = owner.getId();
        this.slot = slot;
        var a = getAttribute(Attributes.MAX_HEALTH);
        if (a != null) a.setBaseValue(hp);
        setHealth((float) hp);
        timer = firstAttack;
        if (level() instanceof ServerLevel sl)
            fx = Fx.play(sl, Fx.fx(slot % 2 == 0 ? "aris_blade_sword" : "aris_blade_glaive").caster(this).at(position()).attach(this));
    }

    private ArisEntity owner() {
        return level().getEntity(ownerId) instanceof ArisEntity a && a.isAlive() ? a : null;
    }

    @Override
    public void tick() {
        super.tick();
        if (!(level() instanceof ServerLevel sl)) return;
        ArisEntity o = owner();
        if (o == null || o.bossCore().inFinale() || tickCount > 20 * 600) {
            shatter(sl);
            return;
        }
        int n = Math.max(1, o.fight.bladeCount());
        Vec3 home = o.position().add(Math.cos(ArisMath.bladeAngle(slot, n, sl.getGameTime())) * ArisMath.BLADE_ORBIT_R, ArisMath.BLADE_ORBIT_H,
                Math.sin(ArisMath.bladeAngle(slot, n, sl.getGameTime())) * ArisMath.BLADE_ORBIT_R);
        switch (state) {
            case ORBIT -> {
                glide(home, 0.35);
                if (--timer <= 0) {
                    target = o.fight.bladeTarget(this);
                    if (target != null) {
                        state = State.AIM;
                        timer = ArisMath.BLADE_AIM;
                        sl.playSound(null, getX(), getY(), getZ(), ru.pohsmp.core.boss.BossCore.sound("aris.blade"), SoundSource.HOSTILE, 1, 1.3f);
                    } else timer = 20;
                }
            }
            case AIM -> {
                setDeltaMovement(Vec3.ZERO);
                if (target == null || !target.isAlive()) {
                    back();
                    break;
                }
                Vec3 to = target.position().add(0, target.getBbHeight() * 0.6, 0).subtract(position());
                orient(to);
                if (--timer <= 0) {
                    dartDir = to.normalize();
                    state = State.DART;
                    timer = ArisMath.BLADE_DART;
                    hitDone = false;
                    sl.playSound(null, getX(), getY(), getZ(), ru.pohsmp.core.boss.BossCore.sound("aris.blade_dart"), SoundSource.HOSTILE, 1.2f, 1);
                }
            }
            case DART -> {
                Vec3 from = position(), next = from.add(dartDir.scale(ArisMath.BLADE_SPEED));
                HitResult hr = sl.clip(new ClipContext(from, next, ClipContext.Block.COLLIDER, ClipContext.Fluid.NONE, this));
                if (hr.getType() != HitResult.Type.MISS) {
                    back();
                    break;
                }
                setPos(next.x, next.y, next.z);
                orient(dartDir);
                for (LivingEntity e : sl.getEntitiesOfClass(LivingEntity.class, new AABB(next, next).inflate(0.9))) {
                    if (hitDone || !o.fight.canHurt(e)) continue;
                    hitDone = true;
                    sl.playSound(null, getX(), getY(), getZ(), ru.pohsmp.core.boss.BossCore.sound("aris.blade_hit"), SoundSource.HOSTILE, 1.2f, 1);
                    o.fight.bladeHit(this, e);
                }
                if (hitDone || --timer <= 0) back();
            }
            case BACK -> {
                glide(home, 0.8);
                if (position().distanceTo(home) < 1.0) {
                    state = State.ORBIT;
                    timer = ArisConfig.get(ArisConfig.BLADE_ATTACK) + slot * 7;
                }
            }
        }
    }

    private void back() {
        state = State.BACK;
        target = null;
    }

    /** Moves toward p at most `step` blocks this tick, facing where it goes (level while orbiting). */
    private void glide(Vec3 p, double step) {
        Vec3 d = p.subtract(position());
        double len = d.length();
        Vec3 move = len <= step ? d : d.scale(step / len);
        setPos(getX() + move.x, getY() + move.y, getZ() + move.z);
        if (move.horizontalDistanceSqr() > 1e-4) orient(new Vec3(move.x, 0, move.z));
    }

    private void orient(Vec3 dir) {
        if (dir.lengthSqr() < 1e-6) return;
        float yaw = (float) (Math.atan2(dir.z, dir.x) * 180 / Math.PI) - 90;
        float pitch = (float) (-Math.atan2(dir.y, Math.sqrt(dir.x * dir.x + dir.z * dir.z)) * 180 / Math.PI);
        setYRot(yaw);
        yRotO = yaw;
        setYHeadRot(yaw);
        setYBodyRot(yaw);
        setXRot(pitch);
        if (fx > 0 && Math.abs(pitch - lastPitch) > 4 && level() instanceof ServerLevel sl) {
            lastPitch = pitch;
            Fx.move(sl, fx, position(), yaw, pitch);
        }
    }

    @Override
    public boolean hurt(DamageSource src, float amount) {
        Entity by = src.getEntity();
        if (by instanceof ArisEntity || by instanceof ArisBladeEntity) return false;
        if (src.is(net.minecraft.tags.DamageTypeTags.IS_FALL) || src.is(net.minecraft.tags.DamageTypeTags.IS_FIRE)) return false;
        if (level() instanceof ServerLevel sl && amount > 0)
            sl.playSound(null, getX(), getY(), getZ(), ru.pohsmp.core.boss.BossCore.sound("aris.blade_hit"), SoundSource.HOSTILE, 0.8f, 1.25f);
        return super.hurt(src, amount);
    }

    @Override
    public void die(DamageSource src) {
        super.die(src);
        if (level() instanceof ServerLevel sl) shatter(sl);
    }

    /** Struck down (or her fight is over): the shatter fx, the sound, gone. */
    void shatter(ServerLevel sl) {
        if (fx > 0) Fx.stop(sl, fx, "");
        fx = -1;
        Fx.play(sl, Fx.fx("aris_blade_shatter").at(position()).yaw(getYRot()));
        sl.playSound(null, getX(), getY(), getZ(), ru.pohsmp.core.boss.BossCore.sound("aris.blade_break"), SoundSource.HOSTILE, 1.2f, 1);
        discard();
    }

    @Override
    public boolean isAlliedTo(Entity e) {
        return e instanceof ArisEntity || e instanceof ArisBladeEntity || super.isAlliedTo(e);
    }

    @Override
    public boolean isPushable() {
        return false;
    }

    @Override
    protected void doPush(Entity e) {}

    @Override
    public boolean causeFallDamage(float d, float m, DamageSource s) {
        return false;
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
    public boolean shouldBeSaved() {
        return false;
    }

    @Override
    public void addAdditionalSaveData(CompoundTag tag) {
        super.addAdditionalSaveData(tag);
    }

    @Override
    public boolean canBeLeashed(Player p) {
        return false;
    }
}
