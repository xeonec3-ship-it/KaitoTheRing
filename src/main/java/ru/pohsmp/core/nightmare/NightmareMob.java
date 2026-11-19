package ru.pohsmp.core.nightmare;

import java.util.UUID;
import net.minecraft.core.Holder;
import net.minecraft.core.registries.Registries;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.protocol.game.ClientboundSoundPacket;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundSource;
import net.minecraft.tags.DamageTypeTags;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.PathfinderMob;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.monster.RangedAttackMob;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.ServerConfig;
import ru.pohsmp.core.illusion.Illusions;

/**
 * T25 bestiary: a nightmare of «Погружение». A real mob with its own simple AI, but only players immersed deep enough get it at all
 * (TrackedEntityMixin; Bestiary.hiddenFrom): the others have no model, shadow, hitbox or sound of it. It cannot be hurt or pushed,
 * walks through nobody, is never saved, hunts only its victim and strikes illusory (the health comes back if the victim lives).
 * It goes as ink when the victim wakes (the stage falls below its own) or is too far.
 */
public class NightmareMob extends PathfinderMob implements RangedAttackMob {
    /** name, the stage it needs, speed (blocks per tick, roughly), reach, render scale */
    public enum Kind {
        LURKER("nm_lurker", 1, 0.22, 2.2, 1.0f),
        HOLLOW_CHILD("nm_hollow_child", 2, 0.34, 1.8, 0.7f),
        WEEPER("nm_weeper", 2, 0.20, 0, 1.05f),
        HANDS("nm_hands", 2, 0, 1.6, 0.55f),
        MAW("nm_maw", 3, 0.18, 2.8, 1.5f),
        CRAWLER("nm_crawler", 3, 0.32, 1.9, 0.9f),
        MIMIC("nm_mimic", 3, 0.26, 2.0, 1.0f),
        DREAD("nm_dread", 3, 0.25, 2.6, 1.3f);

        public final String id;
        public final int stage;
        public final double speed, reach;
        public final float scale;

        Kind(String id, int stage, double speed, double reach, float scale) {
            this.id = id;
            this.stage = stage;
            this.speed = speed;
            this.reach = reach;
            this.scale = scale;
        }
    }

    public static final int MAX_LIFE = 20 * 90;
    private static final double BASE_SPEED = 0.25;

    public final Kind kind;
    UUID victim;
    private int life, strikeCd = 20, watchedFor, unseenFor, roarCd = 100, weepCd = 40;

    public NightmareMob(EntityType<? extends NightmareMob> type, Level level, Kind kind) {
        super(type, level);
        this.kind = kind;
        setSilent(true);   // its sounds go to the victims only
        setPersistenceRequired();
        noCulling = true;
    }

    public static AttributeSupplier.Builder attributes() {
        return PathfinderMob.createMobAttributes().add(Attributes.MAX_HEALTH, 20).add(Attributes.MOVEMENT_SPEED, BASE_SPEED)
                .add(Attributes.FOLLOW_RANGE, 48).add(Attributes.ATTACK_DAMAGE, 0);
    }

    public UUID victim() {
        return victim;
    }

    // ---------------------------------------------------------------- not a body for anyone

    @Override public boolean shouldBeSaved() { return false; }
    @Override public boolean isPushable() { return false; }
    @Override protected void pushEntities() {}
    @Override public void push(Entity e) {}
    @Override public boolean canBeCollidedWith() { return false; }
    @Override public boolean canBeHitByProjectile() { return false; }
    @Override public boolean removeWhenFarAway(double d) { return false; }
    @Override protected boolean shouldDropLoot() { return false; }
    @Override public boolean shouldDropExperience() { return false; }
    @Override public boolean onClimbable() { return kind == Kind.CRAWLER && horizontalCollision || super.onClimbable(); }
    @Override public boolean causeFallDamage(float d, float m, DamageSource s) { return false; }
    @Override public void performRangedAttack(LivingEntity t, float f) {}

    @Override
    public boolean hurt(DamageSource src, float amount) {
        if (src.is(DamageTypeTags.BYPASSES_INVULNERABILITY)) return super.hurt(src, amount);   // /kill
        return false;   // the victim's strike goes through the dark: only the swing
    }

    // ---------------------------------------------------------------- AI

    @Override
    protected void customServerAiStep() {
        super.customServerAiStep();
        if (!(level() instanceof ServerLevel sl)) return;
        ServerPlayer v = victim == null ? null : sl.getServer().getPlayerList().getPlayer(victim);
        if (v == null || !v.isAlive() || v.level() != sl || v.isSpectator() || distanceToSqr(v) > 56 * 56
                || Immersion.stage(v) < kind.stage || ++life > MAX_LIFE) {
            vanish(v);
            return;
        }
        getLookControl().setLookAt(v, 40, 40);
        double d = Math.sqrt(distanceToSqr(v));
        boolean watched = watched(v);
        if (strikeCd > 0) strikeCd--;
        switch (kind) {
            case LURKER -> {   // stands still under the eye and melts if stared at long; comes on when not looked at
                if (watched) {
                    getNavigation().stop();
                    if (++watchedFor > 70) {
                        vanish(v);
                        return;
                    }
                } else {
                    watchedFor = Math.max(0, watchedFor - 2);
                    chase(v, d, 1);
                }
            }
            case HOLLOW_CHILD -> {   // runs at you; while your back is turned for 3 s it is behind you, laughing
                chase(v, d, 1);
                unseenFor = watched ? 0 : unseenFor + 1;
                if (unseenFor > 60 && d > 5) {
                    behind(v, 2.4);
                    unseenFor = 0;
                    sound(v, net.minecraft.sounds.SoundEvents.ALLAY_AMBIENT_WITHOUT_ITEM, 0.9f, 0.45f);
                }
            }
            case WEEPER -> {   // keeps away and weeps; the others are quicker while it is heard (Bestiary.speedFor)
                if (d < 7) getNavigation().moveTo(getX() + (getX() - v.getX()), getY(), getZ() + (getZ() - v.getZ()), speed(1));
                else getNavigation().stop();
                if (--weepCd <= 0) {
                    weepCd = 70 + random.nextInt(40);
                    sound(v, net.minecraft.sounds.SoundEvents.GHAST_AMBIENT, 0.7f, 0.45f);
                }
            }
            case HANDS -> {   // out of the ground under the feet: holds 1.5 s, one strike, gone
                setPos(v.getX(), v.getY(), v.getZ());
                if (life == 4) {
                    v.addEffect(new MobEffectInstance(MobEffects.MOVEMENT_SLOWDOWN, 30, 6, false, false, false));
                    v.addEffect(new MobEffectInstance(MobEffects.JUMP, 30, 128, false, false, false));   // 128+: no jump
                    sound(v, net.minecraft.sounds.SoundEvents.ROOTED_DIRT_BREAK, 1f, 0.5f);
                }
                if (life == 14) strike(v);
                if (life > 34) {
                    vanish(v);
                    return;
                }
            }
            case MAW -> {   // slow; a roar now and then that shakes the victim
                chase(v, d, 1);
                if (--roarCd <= 0 && d < 16) {
                    roarCd = 160 + random.nextInt(80);
                    sound(v, net.minecraft.sounds.SoundEvents.WARDEN_ROAR, 1f, 0.6f);
                    v.addEffect(new MobEffectInstance(MobEffects.MOVEMENT_SLOWDOWN, 40, 1, false, false, false));
                    v.addEffect(new MobEffectInstance(MobEffects.CONFUSION, 50, 0, false, false, false));
                }
            }
            default -> chase(v, d, 1);   // CRAWLER climbs (onClimbable), MIMIC and DREAD just come
        }
    }

    private void chase(ServerPlayer v, double d, double k) {
        if (d > kind.reach * 0.8) getNavigation().moveTo(v, speed(k));
        else getNavigation().stop();
        if (d <= kind.reach && strikeCd <= 0 && hasLineOfSight(v)) strike(v);
    }

    private double speed(double k) {
        return kind.speed * k * Bestiary.speedFor(this) / BASE_SPEED;
    }

    private boolean watched(ServerPlayer v) {
        Vec3 to = getEyePosition().subtract(v.getEyePosition());
        double len = to.length();
        return len > 1e-3 && to.scale(1 / len).dot(v.getViewVector(1)) > 0.86 && v.hasLineOfSight(this);
    }

    private void behind(ServerPlayer v, double dist) {
        Vec3 back = v.getViewVector(1).multiply(-1, 0, -1);
        if (back.lengthSqr() < 1e-4) return;
        Vec3 p = v.position().add(back.normalize().scale(dist));
        Vec3 g = Bestiary.ground((ServerLevel) level(), p.x, v.getY(), p.z);
        if (g != null) teleportTo(g.x, g.y, g.z);
    }

    /** An illusory strike from the nightmare: health that comes back after [nightmare] illusoryReturnSeconds if the victim lives. */
    private void strike(ServerPlayer v) {
        strikeCd = 22 + random.nextInt(12);
        swing(InteractionHand.MAIN_HAND);
        float before = v.getHealth();
        v.invulnerableTime = 0;
        v.hurt(new DamageSource(level().registryAccess().registryOrThrow(Registries.DAMAGE_TYPE).getHolderOrThrow(Reg.NIGHTMARE_DAMAGE), this),
                (float) (double) ServerConfig.get(ServerConfig.IM_DAMAGE));
        float lost = Math.max(0, before - v.getHealth());
        if (v.isAlive() && lost > 0) Illusions.owe(v, lost, (int) Math.round(ServerConfig.get(ServerConfig.IM_RETURN) * 20), 0);
        Immersion.touch(v);
    }

    void sound(ServerPlayer v, SoundEvent s, float vol, float pitch) {
        v.connection.send(new ClientboundSoundPacket(Holder.direct(s), SoundSource.HOSTILE, getX(), getY() + 1, getZ(), vol, pitch, random.nextLong()));
    }

    /** Gone as ink (the victim sees it), no death, no drops. */
    void vanish(ServerPlayer v) {
        if (v != null && level() instanceof ServerLevel sl)
            sl.sendParticles(v, ParticleTypes.SQUID_INK, true, getX(), getY() + getBbHeight() * 0.5, getZ(), 24, 0.3, getBbHeight() * 0.35, 0.3, 0.02);
        discard();
    }
}
