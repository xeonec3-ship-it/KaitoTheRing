package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.spells.SpellAnimations;
import io.redspace.ironsspellbooks.api.util.AnimationHolder;
import io.redspace.ironsspellbooks.api.util.CameraShakeData;
import io.redspace.ironsspellbooks.api.util.CameraShakeManager;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import net.minecraft.core.particles.DustParticleOptions;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import org.joml.Vector3f;
import ru.pohsmp.core.DivineEvents;
import ru.pohsmp.core.net.Net;

/**
 * "Milky Way" (Higher): a 10 s cast with a cutscene for everyone around ("Birth of a galaxy": a great circle under the caster,
 * dark violet and silver stars circling him). Then "Galactic flow": a huge spiral of the Milky Way leaves the hand and travels
 * the chosen direction (where the caster looked when the cast began) for 8 s. Everything caught is drawn into it and carried,
 * takes magic damage twice a second, is slowed hard and every 1.5 s is thrown up by a star stream.
 */
public class MilkyWaySpell extends HigherSpell {
    public static final String PATH = "milky_way";
    public static final int CAST = 200, LIFE = 160, TOSS_EVERY = 30;
    public static final double SPEED = 0.3, RAD = 6, HEIGHT = 1.6, DMG = 3;
    public static final int COLOR = 0x8A5CFF, SILVER = 0xD8DCFF;
    private static final DustParticleOptions VIOLET = new DustParticleOptions(new Vector3f(0.45f, 0.2f, 0.85f), 1.4f);
    private static final DustParticleOptions SILVERD = new DustParticleOptions(new Vector3f(0.86f, 0.88f, 1f), 1.1f);

    private static final class Cast {
        Vec3 at, dir;
        int age, key, cutKey;
        List<UUID> watchers = new ArrayList<>();
    }

    private static final Map<UUID, Cast> CASTS = new HashMap<>();

    public MilkyWaySpell() {
        super(PATH, CAST);
    }

    @Override public CastType getCastType() { return CastType.LONG; }
    @Override public boolean canBeInterrupted(Player player) { return false; }
    @Override public Optional<SoundEvent> getCastStartSound() { return Optional.of(SoundEvents.BEACON_ACTIVATE); }
    @Override public Optional<SoundEvent> getCastFinishSound() { return Optional.empty(); }
    private static final AnimationHolder ANIM_CAST = CastAnims.of("milky_way_cast"), ANIM_FINISH = CastAnims.of("milky_way_finish");
    @Override public AnimationHolder getCastStartAnimation() { return ANIM_CAST; }
    @Override public AnimationHolder getCastFinishAnimation() { return ANIM_FINISH; }
    @Override
    public void onClientPreCast(Level level, int spellLevel, LivingEntity entity, net.minecraft.world.InteractionHand hand, @javax.annotation.Nullable MagicData md) {
        super.onClientPreCast(level, spellLevel, entity, hand, md);
        CastAnims.hideHands(level, entity, getEffectiveCastTime(spellLevel, entity));
    }

    @Override
    public List<MutableComponent> getUniqueInfo(int spellLevel, LivingEntity caster) {
        return List.of(ui("cast", CAST / 20), ui("flow", (int) (LIFE * SPEED), LIFE / 20), ui("damage", num(DMG * 2), (int) RAD), ui("slow"), ui("toss"));
    }

    @Override
    public void onServerPreCast(Level level, int spellLevel, LivingEntity caster, MagicData md) {
        super.onServerPreCast(level, spellLevel, caster, md);
        if (level instanceof ServerLevel sl) start(sl, caster);
    }

    private static Cast start(ServerLevel sl, LivingEntity caster) {
        Cast c = new Cast();
        c.at = caster.position();
        Vec3 look = caster.getLookAngle().multiply(1, 0, 1);
        c.dir = look.lengthSqr() < 1e-4 ? new Vec3(0, 0, 1) : look.normalize();
        c.key = key();
        c.cutKey = key();
        double ang = Math.atan2(c.dir.z, c.dir.x);
        c.watchers = Cutscene.start(sl, caster, c.cutKey, Cutscene.MILKY_WAY, CAST, c.at.add(c.dir.scale(14)).add(0, 3, 0), ang);
        fx(sl, c.at.x, c.at.y, c.at.z, new Net.HFx(Net.HFx.MILKY, c.key, caster.getId(), -1, CAST, c.at.x, c.at.y, c.at.z, ang, COLOR));
        CASTS.put(caster.getUUID(), c);
        sl.playSound(null, c.at.x, c.at.y, c.at.z, SoundEvents.BEACON_ACTIVATE, SoundSource.PLAYERS, 4f, 0.6f);
        return c;
    }

    @Override
    public void onServerCastTick(Level level, int spellLevel, LivingEntity caster, MagicData md) {
        super.onServerCastTick(level, spellLevel, caster, md);
        if (!(level instanceof ServerLevel sl)) return;
        Cast c = CASTS.get(caster.getUUID());
        if (c == null) c = start(sl, caster);
        c.age++;
        int t = c.age;
        Vec3 a = caster.position();
        if (t % 2 == 0) {   // violet and silver stars circling the body on tilted orbits
            for (int i = 0; i < 4; i++) {
                double ang = t * 0.12 + i * Math.PI / 2, tilt = 0.5 * Math.sin(i * 1.7), rad = 1.6 + 0.3 * i;
                double x = Math.cos(ang) * rad, z = Math.sin(ang) * rad, y = 1.1 + Math.sin(ang) * tilt * rad;
                DivineEvents.particle(sl, i % 2 == 0 ? VIOLET : SILVERD, a.x + x, a.y + y, a.z + z, 1, 0, 0);
            }
            DivineEvents.particle(sl, ParticleTypes.END_ROD, a.x, a.y + 1.2, a.z, 1, 1.4, 0.01);
        }
        if (t % 40 == 0) sl.playSound(null, a.x, a.y, a.z, SoundEvents.AMETHYST_BLOCK_RESONATE, SoundSource.PLAYERS, 3f, 0.5f + t / 400f);
        switch (t) {
            case 60 -> sl.playSound(null, a.x, a.y, a.z, SoundEvents.BEACON_POWER_SELECT, SoundSource.PLAYERS, 3f, 0.6f);
            case 120 -> {
                sl.playSound(null, a.x, a.y, a.z, SoundEvents.ELDER_GUARDIAN_CURSE, SoundSource.PLAYERS, 2f, 1.2f);
                CameraShakeManager.addCameraShake(new CameraShakeData(sl, 20, a, 40));
            }
            case 170 -> sl.playSound(null, a.x, a.y, a.z, SoundEvents.WARDEN_SONIC_CHARGE, SoundSource.PLAYERS, 3f, 0.8f);
            default -> {}
        }
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            Cast c = CASTS.get(caster.getUUID());
            if (c == null) c = start(sl, caster);
            c.age = CAST + 1;
            Cutscene.flash(sl, c.watchers, 16, 0xC8B0FF);
            launch(sl, caster, c.at, c.dir);
        }
        super.onCast(level, spellLevel, caster, source, md);
    }

    @Override
    public void onServerCastComplete(Level level, int spellLevel, LivingEntity caster, MagicData md, boolean cancelled) {
        Cast c = CASTS.remove(caster.getUUID());
        if (c != null && level instanceof ServerLevel sl) {
            stop(sl, c.at.x, c.at.y, c.at.z, c.key);
            Cutscene.end(sl, caster, c.watchers, c.cutKey);
        }
        super.onServerCastComplete(level, spellLevel, caster, md, cancelled);
    }

    /** Center of the spiral age ticks after it left the hand (the client draws the same path). */
    public static Vec3 center(Vec3 at, Vec3 dir, double age) {
        return at.add(dir.scale(3 + SPEED * age)).add(0, HEIGHT, 0);
    }

    private static void launch(ServerLevel sl, LivingEntity caster, Vec3 at, Vec3 dir) {
        int k = key();
        double ang = Math.atan2(dir.z, dir.x);
        fx(sl, at.x, at.y, at.z, new Net.HFx(Net.HFx.GALAXY, k, caster.getId(), -1, LIFE, at.x, at.y, at.z, ang, COLOR));
        sl.playSound(null, at.x, at.y, at.z, SoundEvents.END_PORTAL_SPAWN, SoundSource.PLAYERS, 4f, 1.3f);
        sl.playSound(null, at.x, at.y, at.z, SoundEvents.WARDEN_SONIC_BOOM, SoundSource.PLAYERS, 2f, 1.4f);
        Vec3 c0 = center(at, dir, 0);
        CameraShakeManager.addCameraShake(new CameraShakeData(sl, 20, c0, 30));
        Tasks.add(new Tasks.Task() {
            int age;

            @Override
            public boolean tick() {
                age++;
                Vec3 c = center(at, dir, age);
                boolean toss = age % TOSS_EVERY == TOSS_EVERY / 2;
                for (LivingEntity e : around(sl, c, RAD + 1, e -> !friendly(caster, e) && Math.abs(e.getY() + e.getBbHeight() / 2 - c.y) < 4.5)) {
                    Vec3 ec = e.position().add(0, e.getBbHeight() / 2, 0);
                    Vec3 to = c.subtract(ec);
                    double d = Math.max(0.3, to.length());
                    Vec3 swirl = dir.cross(to).normalize().scale(0.18);   // the arms carry them around the core
                    Vec3 v = e.getDeltaMovement().scale(0.55).add(dir.scale(SPEED * 0.95)).add(to.scale(Math.min(0.3, 0.05 + 0.03 * d) / d)).add(swirl);
                    if (toss) {
                        v = new Vec3(v.x, 0.95, v.z);
                        DivineEvents.particle(sl, ParticleTypes.END_ROD, e.getX(), e.getY() + 0.3, e.getZ(), 14, 0.25, 0.25);
                        sl.playSound(null, e.getX(), e.getY(), e.getZ(), SoundEvents.AMETHYST_CLUSTER_BREAK, SoundSource.PLAYERS, 1.2f, 1.4f);
                    } else if (v.y > 0.25) v = new Vec3(v.x, 0.25, v.z);
                    push(e, v);
                    e.fallDistance = 0;
                    if (age % 10 == 1) {
                        e.addEffect(new MobEffectInstance(MobEffects.MOVEMENT_SLOWDOWN, 30, 3, false, true, true));
                        hurt(sl, caster, e, dmg(DMG));
                        DivineEvents.particle(sl, VIOLET, ec.x, ec.y, ec.z, 6, 0.4, 0);
                    }
                }
                if (age % 2 == 0) {
                    for (int i = 0; i < 6; i++) {
                        double an = age * 0.2 + i * Math.PI / 3, r = 1 + (i % 3) * 1.8;
                        Vec3 side = new Vec3(-dir.z, 0, dir.x);
                        Vec3 q = c.add(side.scale(Math.cos(an) * r)).add(0, Math.sin(an) * r * 0.6, 0);
                        DivineEvents.particle(sl, i % 2 == 0 ? VIOLET : SILVERD, q.x, q.y, q.z, 1, 0, 0);
                    }
                    DivineEvents.particle(sl, ParticleTypes.END_ROD, c.x, c.y, c.z, 2, RAD * 0.5, 0.02);
                }
                if (age % 20 == 0) sl.playSound(null, c.x, c.y, c.z, SoundEvents.AMETHYST_BLOCK_RESONATE, SoundSource.PLAYERS, 3f, 0.6f);
                if (age < LIFE) return true;
                burst(sl, c.x, c.y, c.z, RAD, COLOR);
                DivineEvents.particle(sl, ParticleTypes.END_ROD, c.x, c.y, c.z, 80, 1.5, 0.3);
                sl.playSound(null, c.x, c.y, c.z, SoundEvents.AMETHYST_BLOCK_BREAK, SoundSource.PLAYERS, 4f, 0.5f);
                return false;
            }
        });
    }

    public static final class MilkyWayEvents {
        private MilkyWayEvents() {}

        @SubscribeEvent
        public static void onStopping(ServerStoppingEvent e) {
            CASTS.clear();
        }
    }
}
