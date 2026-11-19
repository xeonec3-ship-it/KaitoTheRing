package ru.pohsmp.core.nightmare;

import java.util.List;
import java.util.Optional;
import java.util.UUID;
import net.minecraft.core.Holder;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.protocol.game.ClientboundSoundPacket;
import net.minecraft.network.syncher.EntityDataAccessor;
import net.minecraft.network.syncher.EntityDataSerializers;
import net.minecraft.network.syncher.SynchedEntityData;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.tags.DamageTypeTags;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.PathfinderMob;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.ServerConfig;
import ru.pohsmp.core.fx.Fx;
import ru.pohsmp.core.illusion.Illusions;
import software.bernie.geckolib.animatable.GeoEntity;
import software.bernie.geckolib.core.animatable.instance.AnimatableInstanceCache;
import software.bernie.geckolib.core.animation.AnimatableManager;
import software.bernie.geckolib.core.animation.AnimationController;
import software.bernie.geckolib.core.animation.RawAnimation;
import software.bernie.geckolib.core.object.PlayState;
import software.bernie.geckolib.util.GeckoLibUtil;

/**
 * T25 bestiary: a nightmare of «Погружение» (models, animations and the vanilla sounds - visual letter 19.11,
 * docs/inbox/2026-11-19_mgr_T25_visuals.md). A real mob with its own simple AI, but only players immersed deep enough get it at all
 * (TrackedEntityMixin; Bestiary.hiddenFrom): the others have no model, shadow, hitbox or sound of it. It cannot be hurt or pushed, walks
 * through nobody, is never saved, hunts only its victim and strikes illusory (the health comes back if the victim lives).
 * It comes out of an ink puddle (appear) and goes as ink (vanish) when the victim wakes (the stage falls below its own) or is too far.
 */
public class NightmareMob extends PathfinderMob implements GeoEntity {
    /** id, the stage it needs, speed (blocks per tick, roughly), reach, hitbox, the animations its file has besides idle/walk/appear/vanish */
    public enum Kind {
        LURKER("nm_lurker", 1, 0.22, 2.2, 0.6f, 2.4f, "attack", "lunge", "dissolve"),
        HOLLOW_CHILD("nm_hollow_child", 2, 0.34, 1.8, 0.5f, 1.1f, "attack", "laugh"),
        WEEPER("nm_weeper", 2, 0.20, 0, 0.7f, 2.6f, "flee", "wail"),
        HANDS("nm_hands", 2, 0, 1.9, 2.0f, 0.6f, "grab"),
        MOTH("nm_moth", 2, 0.30, 1.6, 1.0f, 1.0f, "attack"),
        MAW("nm_maw", 3, 0.18, 3.0, 2.4f, 3.8f, "attack", "roar"),
        CRAWLER("nm_crawler", 3, 0.32, 1.9, 1.2f, 0.9f, "attack", "pounce"),
        MIMIC("nm_mimic", 3, 0.26, 2.0, 0.6f, 2.0f, "attack", "call", "reveal"),
        DREAD("nm_dread", 3, 0.25, 2.6, 0.8f, 3.2f, "attack", "scream");

        public final String id;
        public final int stage;
        public final double speed, reach;
        public final float width, height;
        public final List<String> anims;

        Kind(String id, int stage, double speed, double reach, float width, float height, String... anims) {
            this.id = id;
            this.stage = stage;
            this.speed = speed;
            this.reach = reach;
            this.width = width;
            this.height = height;
            this.anims = List.of(anims);
        }

        public String anim(String name) {
            return "animation." + id + "." + name;
        }
    }

    public static final int MAX_LIFE = 20 * 90, APPEAR = 14, VANISH = 16;
    private static final double BASE_SPEED = 0.25;
    /** the moment of the blow in the attack animations (0.45 s) */
    private static final int HIT_AT = 9;

    private static final EntityDataAccessor<Boolean> GOING = SynchedEntityData.defineId(NightmareMob.class, EntityDataSerializers.BOOLEAN);
    private static final EntityDataAccessor<Optional<UUID>> FACE = SynchedEntityData.defineId(NightmareMob.class, EntityDataSerializers.OPTIONAL_UUID);

    public final Kind kind;
    UUID victim;
    private int life, strikeCd = 20, hitIn = -1, watchedFor, unseenFor, roarCd = 100, weepCd = 40, goneIn = -1, blinkIn = -1, aura = -1;
    private final AnimatableInstanceCache cache = GeckoLibUtil.createInstanceCache(this);
    private static final EntityDataAccessor<Integer> COMES = SynchedEntityData.defineId(NightmareMob.class, EntityDataSerializers.INT);
    /** when the last appear began, in this side's own tickCount */
    private int seenComes, cameAt;

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

    @Override
    protected void defineSynchedData() {
        super.defineSynchedData();
        entityData.define(GOING, false);
        entityData.define(FACE, Optional.empty());
        entityData.define(COMES, 0);
    }

    /** True while it comes out of the puddle (the appear animation; the pool bone shown). */
    public boolean appearing() {
        int c = entityData.get(COMES);
        if (c != seenComes) {
            seenComes = c;
            cameAt = tickCount;
        }
        return tickCount - cameAt < APPEAR;
    }

    public UUID victim() {
        return victim;
    }

    /** Mimic: whose face, skin and name it wears. */
    public Optional<UUID> face() {
        return entityData.get(FACE);
    }

    /** Mimic: wears someone the victim knows (another player nearby, else the victim itself); the client takes the skin by the UUID. */
    void wear(ServerPlayer v) {
        ServerPlayer who = v;
        double best = 64 * 64;
        for (ServerPlayer p : ((ServerLevel) level()).players()) {
            if (p == v || p.isSpectator()) continue;
            double d = p.distanceToSqr(v);
            if (d < best) {
                best = d;
                who = p;
            }
        }
        entityData.set(FACE, Optional.of(who.getUUID()));
        setCustomName(who.getDisplayName());
        setCustomNameVisible(true);
    }

    /** True while it goes as ink (the client hides nothing then: the vanish animation plays). */
    public boolean going() {
        return entityData.get(GOING);
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
    @Override public boolean isNoGravity() { return kind == Kind.MOTH || super.isNoGravity(); }

    @Override
    public boolean hurt(DamageSource src, float amount) {
        if (src.is(DamageTypeTags.BYPASSES_INVULNERABILITY)) return super.hurt(src, amount);   // /kill
        return false;   // the victim's strike goes through the dark: only the swing
    }

    // ---------------------------------------------------------------- animations (GeckoLib)

    @Override
    public void registerControllers(AnimatableManager.ControllerRegistrar reg) {
        AnimationController<NightmareMob> c = new AnimationController<>(this, "main", 3, st -> {
            if (going()) return st.setAndContinue(RawAnimation.begin().thenPlayAndHold(kind.anim("vanish")));
            if (appearing()) return st.setAndContinue(RawAnimation.begin().thenPlay(kind.anim("appear")));
            boolean moving = kind != Kind.HANDS && st.isMoving();
            String loop = !moving ? "idle" : kind == Kind.WEEPER ? "flee" : "walk";   // the Weeper only moves to get away
            return st.setAndContinue(RawAnimation.begin().thenLoop(kind.anim(loop)));
        });
        for (String a : kind.anims) c.triggerableAnim(a, RawAnimation.begin().thenPlay(kind.anim(a)));
        reg.add(c);
    }

    @Override
    public AnimatableInstanceCache getAnimatableInstanceCache() {
        return cache;
    }

    private void play(String anim) {
        if (kind.anims.contains(anim)) triggerAnim("main", anim);
    }

    // ---------------------------------------------------------------- AI

    @Override
    protected void customServerAiStep() {
        super.customServerAiStep();
        if (!(level() instanceof ServerLevel sl)) return;
        ServerPlayer v = victim == null ? null : sl.getServer().getPlayerList().getPlayer(victim);
        if (goneIn >= 0) {   // going as ink
            getNavigation().stop();
            if (--goneIn <= 0) discard();
            return;
        }
        if (v == null || !v.isAlive() || v.level() != sl || v.isSpectator() || distanceToSqr(v) > 56 * 56
                || Immersion.stage(v) < kind.stage || ++life > MAX_LIFE) {
            vanish(v);
            return;
        }
        if (life == 1) {
            fx(v, "nm_spawn");
            sound(v, NmSounds.INK_RISE, 1f, 1f);
            if (kind == Kind.MIMIC) wear(v);
            if (kind == Kind.WEEPER) aura = Fx.play(sl, Fx.fx("nm_weeper_aura").at(position()).caster(this).attach(this).only(v));
        }
        getLookControl().setLookAt(v, 40, 40);
        if (appearing()) return;   // still coming out of the puddle
        if (blinkIn >= 0 && --blinkIn == 0) {   // Hollow Child: gone a moment ago, now behind the victim
            behind(v, 2.4);
            entityData.set(GOING, false);
            entityData.set(COMES, entityData.get(COMES) + 1);
            fx(v, "nm_spawn");
            play("laugh");
            sound(v, NmSounds.CHILD_LAUGH, 1f, 1f);
            return;
        }
        if (blinkIn >= 0) return;
        double d = Math.sqrt(distanceToSqr(v));
        boolean watched = watched(v);
        if (strikeCd > 0) strikeCd--;
        if (hitIn >= 0 && --hitIn == 0) land(v, d);
        switch (kind) {
            case LURKER -> {   // stands still under the eye and melts if stared at; comes on when not looked at, lunges at a turned back
                if (watched) {
                    getNavigation().stop();
                    if (++watchedFor > 40) {
                        play("dissolve");
                        fx(v, "nm_lurker_dissolve");
                        sound(v, SoundEvents.SOUL_ESCAPE, 1f, 0.6f);
                        goneIn = 14;
                        return;
                    }
                } else {
                    watchedFor = Math.max(0, watchedFor - 2);
                    unseenFor++;
                    if (unseenFor > 60 && d < 6 && strikeCd <= 0) {
                        unseenFor = 0;
                        Vec3 to = v.position().subtract(position()).normalize().scale(0.9);
                        setDeltaMovement(to.x, 0.25, to.z);
                        strike(v, "lunge");
                        sound(v, SoundEvents.ENDERMAN_SCREAM, 1f, 0.5f);
                    } else chase(v, d);
                }
            }
            case HOLLOW_CHILD -> {   // runs at you; while your back is turned for 3 s it is behind you, laughing
                chase(v, d);
                unseenFor = watched ? 0 : unseenFor + 1;
                if (unseenFor > 60 && d > 5) {
                    unseenFor = 0;
                    entityData.set(GOING, true);
                    fx(v, "nm_despawn");
                    sound(v, NmSounds.INK_FALL, 0.7f, 1.2f);
                    blinkIn = 8;
                }
            }
            case WEEPER -> {   // keeps away and weeps; the others are quicker while it is heard (Bestiary.speedFor)
                if (d < 7) getNavigation().moveTo(getX() + (getX() - v.getX()), getY(), getZ() + (getZ() - v.getZ()), speed(1.2));
                else getNavigation().stop();
                if (--weepCd <= 0) {
                    weepCd = 80 + random.nextInt(60);
                    if (random.nextInt(3) == 0) {
                        play("wail");
                        sound(v, NmSounds.WEEPER_WAIL, 1f, 1f);
                    } else sound(v, NmSounds.WEEPER_CRY, 0.8f, 1f);
                }
            }
            case HANDS -> {   // out of the ground under the feet: grab, hold 1.5 s, one strike, gone
                if (life == APPEAR + 2) {
                    play("grab");
                    fx(v, "nm_hands_grab");
                    v.addEffect(new MobEffectInstance(MobEffects.MOVEMENT_SLOWDOWN, 30, 6, false, false, false));
                    v.addEffect(new MobEffectInstance(MobEffects.JUMP, 30, 128, false, false, false));   // 128+: no jump
                    sound(v, NmSounds.HANDS_GRAB, 1f, 1f);
                }
                if (life == APPEAR + 14) land(v, 0);
                if (life > APPEAR + 32) vanish(v);
            }
            case MOTH -> {   // a swarm at the head: circles it, now and then covers the eyes
                Vec3 eye = v.getEyePosition().add(new Vec3(Math.cos(life * 0.12), 0, Math.sin(life * 0.12)).scale(1.4)).subtract(0, 0.5, 0);
                getMoveControl().setWantedPosition(eye.x, eye.y, eye.z, speed(1));
                setDeltaMovement(eye.subtract(position()).scale(0.25));
                if (life % 30 == 0) sound(v, NmSounds.MOTHS, 0.6f, 1f);
                if (strikeCd <= 0 && d < 3) {
                    strike(v, "attack");
                    v.addEffect(new MobEffectInstance(MobEffects.DARKNESS, 50, 0, false, false, false));   // the wings over the eyes
                }
            }
            case MAW -> {   // slow; a roar now and then that shakes the victim
                chase(v, d);
                if (--roarCd <= 0 && d < 16) {
                    roarCd = 180 + random.nextInt(80);
                    play("roar");
                    fx(v, "nm_maw_roar");
                    sound(v, NmSounds.MAW_ROAR, 1f, 1f);
                    v.addEffect(new MobEffectInstance(MobEffects.MOVEMENT_SLOWDOWN, 40, 1, false, false, false));
                    v.addEffect(new MobEffectInstance(MobEffects.CONFUSION, 50, 0, false, false, false));
                }
                if (life % 48 == 0 && getNavigation().isInProgress()) sound(v, SoundEvents.SKELETON_STEP, 1f, 0.4f);
            }
            case CRAWLER -> {
                chase(v, d);
                if (life % 70 == 0) sound(v, NmSounds.CRAWLER_HISS, 0.8f, 1f);
                if (life % 7 == 0 && getNavigation().isInProgress()) sound(v, NmSounds.CRAWLER_STEP, 0.5f, 1f);
                if (life % 200 == 100) sound(v, NmSounds.SCRAPE, 0.7f, 1f);
            }
            case MIMIC -> {
                chase(v, d);
                if (life % 160 == 40 && d > 5) {
                    play("call");
                    sound(v, SoundEvents.VILLAGER_AMBIENT, 0.8f, 0.6f);
                }
            }
            default -> chase(v, d);
        }
    }

    private void chase(ServerPlayer v, double d) {
        if (d > kind.reach * 0.8) getNavigation().moveTo(v, speed(1));
        else getNavigation().stop();
        if (d <= kind.reach && strikeCd <= 0 && hasLineOfSight(v)) {
            if (kind == Kind.MIMIC && random.nextInt(2) == 0) {
                play("reveal");
                sound(v, SoundEvents.WARDEN_ROAR, 0.6f, 1.6f);
                strikeCd = 30;
                return;
            }
            strike(v, kind == Kind.CRAWLER && !onGround() ? "pounce" : "attack");
        }
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

    /** The swing starts; the blow lands on the animation's hit moment. */
    private void strike(ServerPlayer v, String anim) {
        strikeCd = 26 + random.nextInt(12);
        play(anim);
        hitIn = HIT_AT;
    }

    /** An illusory blow from the nightmare: health that comes back after [nightmare] illusoryReturnSeconds if the victim lives. */
    private void land(ServerPlayer v, double d) {
        if (d > kind.reach * 1.6) return;   // it stepped away meanwhile
        // not real damage (owner 19.11): nothing is taken - the victim alone sees the flinch, hears the hurt and has fewer hearts for a while
        v.connection.send(new net.minecraft.network.protocol.game.ClientboundHurtAnimationPacket(v));
        sound(v, SoundEvents.PLAYER_HURT, 1f, 1f);
        Bestiary.fakeHit(v, (float) (double) ServerConfig.get(ServerConfig.IM_DAMAGE), (int) Math.round(ServerConfig.get(ServerConfig.IM_RETURN) * 20));
        switch (kind) {
            case MAW -> sound(v, NmSounds.MAW_BITE, 1f, 1f);
            case HANDS -> sound(v, SoundEvents.MUD_BREAK, 1f, 0.5f);
            case CRAWLER -> sound(v, NmSounds.CRAWLER_HISS, 1f, 1.1f);
            default -> sound(v, SoundEvents.PHANTOM_BITE, 0.9f, 0.7f);
        }
        Immersion.touch(v);
    }

    void sound(ServerPlayer v, SoundEvent s, float vol, float pitch) {
        v.connection.send(new ClientboundSoundPacket(Holder.direct(s), SoundSource.HOSTILE, getX(), getY() + 1, getZ(), vol, pitch, random.nextLong()));
    }

    private void fx(ServerPlayer v, String name) {
        if (level() instanceof ServerLevel sl) Fx.play(sl, Fx.fx(name).at(position()).caster(this).only(v));
    }

    /** Goes as ink (the vanish animation, then gone); no death, no drops. */
    void vanish(ServerPlayer v) {
        if (goneIn >= 0) return;
        if (aura >= 0 && level() instanceof ServerLevel sl) Fx.stop(sl, aura, "");
        entityData.set(GOING, true);
        goneIn = VANISH;
        if (v != null) {
            fx(v, "nm_despawn");
            sound(v, NmSounds.INK_FALL, 1f, 1f);
        }
    }
}
