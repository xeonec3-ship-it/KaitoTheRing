package ru.pohsmp.core.mythic;

import io.redspace.ironsspellbooks.api.registry.SchoolRegistry;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.Mth;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.ServerConfig;
import ru.pohsmp.core.fx.Fx;
import ru.pohsmp.core.net.IlluMsg;
import ru.pohsmp.core.spell.Cutscene;

/**
 * T23 «Око бездны» (eldritch, Mythic). 12 s: the sky over the caster darkens, the clouds turn and a giant eye opens 32 blocks up. Then
 * [abyss_eye] seconds every enemy player under the open sky (nothing solid over its head) within the radius hears whispers, sees the edges
 * darken and the view sway, and loses its mind: magic damage every second. Looking at the Eye: a strong strike and a 1 s freeze, at most
 * once per cooldown. A roof over the head or a cave saves.
 */
public class AbyssEyeSpell extends MythicT23 {
    public static final String PATH = "abyss_eye";
    private static final int CAST = 240, FX_ZONE = 300, PUPIL_AT = 228;
    private static final double EYE = 32, SLIT = 29.3, PUPIL_SHIFT = 3;

    public AbyssEyeSpell() {
        super(PATH, SchoolRegistry.ELDRITCH_RESOURCE, CAST, Cutscene.ABYSS_EYE);
    }

    @Override public Optional<SoundEvent> getCastStartSound() { return Optional.of(SoundEvents.AMBIENT_CAVE.get()); }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(castLine(), line("abyss_eye.zone", n(d(ServerConfig.AE_RADIUS)), n(d(ServerConfig.AE_SECONDS))),
                line("abyss_eye.sanity", n(d(ServerConfig.AE_SANITY) * mult(caster))), line("abyss_eye.gaze", n(d(ServerConfig.AE_GAZE) * mult(caster))));
    }

    @Override
    protected void aim(ServerLevel sl, LivingEntity caster, Cast c) {
        c.point = caster.position();
    }

    @Override
    protected Vec3 focus(Cast c) {
        return c.point.add(0, EYE, 0);
    }

    @Override
    protected int castFx(ServerLevel sl, LivingEntity caster, Cast c) {
        return Fx.play(sl, Fx.fx("abyss_eye_cast").at(c.point).caster(caster));
    }

    @Override
    protected void castTick(ServerLevel sl, LivingEntity caster, Cast c) {
        Vec3 p = c.point, e = p.add(0, EYE, 0);
        switch (c.age) {
            case 1 -> sl.playSound(null, p.x, p.y + 1, p.z, SoundEvents.AMBIENT_SOUL_SAND_VALLEY_MOOD.get(), SoundSource.PLAYERS, 3f, 0.6f);
            case 100 -> sl.playSound(null, e.x, e.y - 10, e.z, SoundEvents.LIGHTNING_BOLT_THUNDER, SoundSource.WEATHER, 6f, 0.5f);
            case 160 -> sl.playSound(null, e.x, e.y - 10, e.z, SoundEvents.WARDEN_HEARTBEAT, SoundSource.PLAYERS, 6f, 0.5f);
            case PUPIL_AT -> c.extra = Fx.play(sl, Fx.fx("abyss_eye_pupil").at(p.add(0, SLIT, 0)));
            case 230 -> {
                Cutscene.flash(sl, c.watchers, 14, 0x8E5BD9);
                sl.playSound(null, p.x, p.y + 4, p.z, SoundEvents.WARDEN_SONIC_BOOM, SoundSource.PLAYERS, 4f, 0.5f);
            }
            default -> {}
        }
        if (c.age > 40 && c.age < 220 && c.age % 45 == 0)
            sl.playSound(null, e.x, e.y - 8, e.z, SoundEvents.LIGHTNING_BOLT_THUNDER, SoundSource.WEATHER, 3f, 0.7f + sl.random.nextFloat() * 0.3f);
    }

    @Override
    protected void release(ServerLevel sl, LivingEntity caster, Cast c) {
        if (c.extra < 0) c.extra = Fx.play(sl, Fx.fx("abyss_eye_pupil").at(c.point.add(0, SLIT, 0)));
        Eye z = new Eye(this, sl, caster, c.point, c.fx, c.extra);
        c.extra = -1;   // the zone owns the pupil now
        ZONES.add(z);
    }

    /** Nothing solid between the head and the sky. */
    static boolean exposed(ServerLevel sl, LivingEntity e) {
        return e.getEyeY() >= sl.getHeight(Heightmap.Types.MOTION_BLOCKING, Mth.floor(e.getX()), Mth.floor(e.getZ()));
    }

    private static final class Eye implements Zone {
        final AbyssEyeSpell spell;
        final ServerLevel sl;
        final LivingEntity caster;
        final Vec3 c, eye;
        final int castFx, pupil, life;
        final double r;
        final Map<UUID, Long> nextGaze = new HashMap<>();
        final Set<UUID> warned = new HashSet<>();
        int age;

        Eye(AbyssEyeSpell spell, ServerLevel sl, LivingEntity caster, Vec3 c, int castFx, int pupil) {
            this.spell = spell;
            this.sl = sl;
            this.caster = caster;
            this.c = c;
            this.eye = c.add(0, SLIT, 0);
            this.castFx = castFx;
            this.pupil = pupil;
            this.life = ticks(ServerConfig.AE_SECONDS);
            this.r = d(ServerConfig.AE_RADIUS);
        }

        @Override
        public boolean tick() {
            age++;
            if (age >= life) {
                stop();
                return false;
            }
            long now = sl.getGameTime();
            float m = spell.mult(caster);
            double cosGaze = Math.cos(Math.toRadians(d(ServerConfig.AE_GAZE_ANGLE)));
            ServerPlayer nearest = null;
            double best = Double.MAX_VALUE;
            for (ServerPlayer p : sl.players()) {
                if (p.distanceToSqr(c) > r * r || !enemy(caster, p) || !exposed(sl, p)) continue;
                double dd = p.distanceToSqr(c);
                if (dd < best) {
                    best = dd;
                    nearest = p;
                }
                if (age % 20 == 1) {   // the whisper: damage to the mind
                    if (warned.add(p.getUUID())) say(p, "abyss_eye.warn");
                    spell.hit(caster, p, (float) (d(ServerConfig.AE_SANITY) * m));
                    p.addEffect(new MobEffectInstance(Reg.ABYSS_DREAD.get(), 30, 0, false, false, true));
                    sky(p, IlluMsg.SKY_DREAD, 30);
                    Fx.play(sl, Fx.fx("abyss_eye_whisper").at(p.position()).caster(p).attach(p));
                    p.playNotifySound(SoundEvents.AMBIENT_CAVE.get(), SoundSource.HOSTILE, 0.8f, 0.5f + sl.random.nextFloat() * 0.3f);
                }
                Vec3 to = eye.subtract(p.getEyePosition());
                if (to.lengthSqr() > 1e-4 && p.getViewVector(1).dot(to.normalize()) >= cosGaze && now >= nextGaze.getOrDefault(p.getUUID(), 0L)) {
                    nextGaze.put(p.getUUID(), now + ticks(ServerConfig.AE_GAZE_COOLDOWN));
                    spell.hit(caster, p, (float) (d(ServerConfig.AE_GAZE) * m));
                    p.addEffect(new MobEffectInstance(Reg.PARALYSIS.get(), 20, 0, false, false, false));
                    Fx.play(sl, Fx.fx("abyss_eye_gaze").at(p.position()).caster(p).attach(p));
                    p.playNotifySound(SoundEvents.WARDEN_ROAR, SoundSource.HOSTILE, 1f, 1.4f);
                }
            }
            if (pupil >= 0 && age % 2 == 0) {   // the pupil turns to the nearest one under the sky
                Vec3 at = eye;
                float yaw = 0;
                if (nearest != null) {
                    Vec3 h = nearest.position().subtract(c).multiply(1, 0, 1);
                    if (h.lengthSqr() > 1e-4) {
                        at = eye.add(h.normalize().scale(Math.min(PUPIL_SHIFT, h.length() / 8)));
                        yaw = (float) Math.toDegrees(Math.atan2(-h.x, h.z));
                    }
                }
                Fx.move(sl, pupil, at, yaw);
            }
            if (age % 60 == 0) sl.playSound(null, eye.x, eye.y - 6, eye.z, SoundEvents.WARDEN_HEARTBEAT, SoundSource.PLAYERS, 5f, 0.5f);
            return true;
        }

        @Override
        public void stop() {
            if (pupil >= 0) Fx.stop(sl, pupil, "");
            if (life != FX_ZONE && castFx >= 0) Fx.stop(sl, castFx, "");
        }
    }
}
