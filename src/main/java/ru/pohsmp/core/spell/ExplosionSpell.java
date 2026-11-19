package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.registry.SchoolRegistry;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.spells.SpellAnimations;
import io.redspace.ironsspellbooks.api.spells.SpellRarity;
import io.redspace.ironsspellbooks.api.util.AnimationHolder;
import io.redspace.ironsspellbooks.api.util.CameraShakeData;
import io.redspace.ironsspellbooks.api.util.CameraShakeManager;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import net.minecraft.ChatFormatting;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.DivineEvents;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.fx.Fx;

/**
 * Mythic, level 1. "Explosion!": a 15 s chant that cannot be interrupted. Seven magic circles light up one by one in the sky above
 * the point the caster looked at; then a flash, a pillar of flame, a shock wave and a smoke cloud. 60 + 25% of max health
 * in 24 blocks (owner 19.11: x2; weaker toward the edge), everyone but the caster, no blocks broken. The caster collapses for 10 s afterwards.
 */
public class ExplosionSpell extends PohSpell {
    public static final String PATH = "explosion";
    public static final int CAST = 300, SPENT_TICKS = 200;
    private static final double R = 24, FLAT = 60, PCT = 0.25, RANGE = 48;
    private static final int COLOR = 0xFF5A1E, CIRCLES = 7;
    private static final String[] CHANT = {
            "Алое пламя, что старше самих звёзд, — услышь мой зов.",
            "Пусть небо треснет, а земля забудет своё имя.",
            "Семь кругов зажжены, семь печатей сорваны.",
            "Всё, что у меня есть, я отдаю ради одного мгновения.",
            "Сожги горизонт и не оставь даже пепла!",
    };

    private static final class Cast {
        Vec3 at;
        int age, fx = -1;
    }

    private static final Map<UUID, Cast> CASTS = new HashMap<>();

    public ExplosionSpell() {
        super(PATH, SchoolRegistry.FIRE_RESOURCE, SpellRarity.LEGENDARY, 1, 0, CAST, 0, 0);
    }

    @Override public CastType getCastType() { return CastType.LONG; }
    @Override public boolean canBeInterrupted(Player player) { return false; }
    @Override public boolean allowCrafting() { return false; }
    @Override public Optional<SoundEvent> getCastStartSound() { return Optional.of(SoundEvents.BLAZE_AMBIENT); }
    @Override public Optional<SoundEvent> getCastFinishSound() { return Optional.empty(); }
    @Override public AnimationHolder getCastStartAnimation() { return SpellAnimations.ANIMATION_LONG_CAST; }
    @Override public AnimationHolder getCastFinishAnimation() { return SpellAnimations.ANIMATION_LONG_CAST_FINISH; }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("damage", n(FLAT), (int) (PCT * 100), n(R)), ui("time", CAST / 20), ui("spent", SPENT_TICKS / 20));
    }

    @Override
    public void onServerPreCast(Level level, int spellLevel, LivingEntity entity, MagicData md) {
        super.onServerPreCast(level, spellLevel, entity, md);
        if (level instanceof ServerLevel sl) {
            Cast c = new Cast();
            c.at = ground(sl, entity, lookPoint(sl, entity, RANGE));
            CASTS.put(entity.getUUID(), c);
        }
    }

    @Override
    public void onServerCastTick(Level level, int spellLevel, LivingEntity caster, MagicData md) {
        super.onServerCastTick(level, spellLevel, caster, md);
        if (!(level instanceof ServerLevel sl)) return;
        Cast c = CASTS.get(caster.getUUID());
        if (c == null) {
            onServerPreCast(level, spellLevel, caster, md);
            c = CASTS.get(caster.getUUID());
        }
        c.age++;
        if (c.age == 1) c.fx = Fx.play(sl, Fx.fx("explosion_cast").at(c.at).yaw(caster.getYRot()));   // seven circles light up one by one
        int step = CAST / (CIRCLES + 1);
        if (c.age % step == 0 && c.age / step <= CIRCLES) {   // one more circle in the sky (drawn by explosion_cast)
            int i = c.age / step - 1;
            double y = c.at.y + 14 + i * 2.6;
            sl.playSound(null, c.at.x, y, c.at.z, SoundEvents.BEACON_POWER_SELECT, SoundSource.PLAYERS, 6f, 0.5f + i * 0.12f);
            sl.playSound(null, caster.getX(), caster.getY(), caster.getZ(), SoundEvents.FIRECHARGE_USE, SoundSource.PLAYERS, 1.5f, 0.5f + i * 0.1f);
        }
        int line = c.age / (CAST / (CHANT.length + 1));
        if (c.age % (CAST / (CHANT.length + 1)) == 0 && line >= 1 && line <= CHANT.length) say(sl, caster, CHANT[line - 1]);
        double p = c.age / (double) CAST;
        if (c.age % 2 == 0) {
            double a = c.age * 0.2;
            for (int i = 0; i < 2; i++)
                DivineEvents.particle(sl, ParticleTypes.FLAME, caster.getX() + Math.cos(a + i * Math.PI) * 1.2, caster.getY() + 0.1, caster.getZ() + Math.sin(a + i * Math.PI) * 1.2, 1, 0.02, 0.02);
            DivineEvents.particle(sl, ParticleTypes.SMALL_FLAME, c.at.x, c.at.y + 0.2, c.at.z, 1 + (int) (p * 6), R * 0.4, 0.02);
        }
        if (c.age % 40 == 0) sl.playSound(null, c.at.x, c.at.y, c.at.z, SoundEvents.FIRE_AMBIENT, SoundSource.PLAYERS, 4f, 0.5f);
    }

    private static void say(ServerLevel sl, LivingEntity caster, String text) {
        if (ru.pohsmp.core.silent.SilentWitch.muted(caster)) return;   // Silent Witch robe: silent chanting
        Component msg = Component.literal("").append(caster.getDisplayName()).append(Component.literal(": ").withStyle(ChatFormatting.GRAY))
                .append(Component.literal("«" + text + "»").withStyle(ChatFormatting.RED, ChatFormatting.ITALIC));
        for (ServerPlayer p : sl.players()) if (p.distanceToSqr(caster) < 64 * 64) p.sendSystemMessage(msg);
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            Cast c = CASTS.remove(caster.getUUID());
            if (c != null) {
                say(sl, caster, "ВЗРЫВ!");
                if (c.fx >= 0) Fx.stop(sl, c.fx, "");
                boom(sl, caster, c.at);
                spend(caster, md);
            }
        }
        super.onCast(level, spellLevel, caster, source, md);
    }

    @Override
    public void onServerCastComplete(Level level, int spellLevel, LivingEntity entity, MagicData md, boolean cancelled) {
        Cast c = CASTS.remove(entity.getUUID());
        if (c != null && c.fx >= 0 && level instanceof ServerLevel sl) Fx.stop(sl, c.fx, "");
        super.onServerCastComplete(level, spellLevel, entity, md, cancelled);
    }

    private static void spend(LivingEntity caster, MagicData md) {
        caster.addEffect(new MobEffectInstance(Reg.SPENT.get(), SPENT_TICKS, 0, false, true, true));
        if (md != null) md.setMana(0);
        if (caster instanceof ServerPlayer sp) MagicData.getPlayerMagicData(sp).setMana(0);
    }

    private static void boom(ServerLevel sl, LivingEntity caster, Vec3 c) {
        Fx.play(sl, Fx.fx("explosion_boom").at(c));   // white-out, fire column, bubble, ground wave, cracks, embers
        CameraShakeManager.addCameraShake(new CameraShakeData(sl, 60, c, 64));
        sl.playSound(null, c.x, c.y, c.z, SoundEvents.GENERIC_EXPLODE, SoundSource.PLAYERS, 12f, 0.5f);
        sl.playSound(null, c.x, c.y, c.z, SoundEvents.DRAGON_FIREBALL_EXPLODE, SoundSource.PLAYERS, 10f, 0.6f);
        sl.playSound(null, c.x, c.y, c.z, SoundEvents.LIGHTNING_BOLT_THUNDER, SoundSource.PLAYERS, 10f, 0.5f);
        DivineEvents.particle(sl, ParticleTypes.FLASH, c.x, c.y + 2, c.z, 3, 0, 0);
        DivineEvents.particle(sl, ParticleTypes.EXPLOSION_EMITTER, c.x, c.y + 1, c.z, 6, 3, 0);
        DivineEvents.particle(sl, ParticleTypes.FLAME, c.x, c.y + 1, c.z, 400, R * 0.35, 0.4);
        DivineEvents.particle(sl, ParticleTypes.LAVA, c.x, c.y + 1, c.z, 80, R * 0.3, 0.2);
        for (LivingEntity e : HigherSpell.around(sl, c, R + 2, e -> e != caster && !e.isSpectator())) {
            double d = e.position().distanceTo(c);
            if (d > R + e.getBbWidth() / 2) continue;
            double k = 1 - 0.5 * Math.min(1, d / R);
            e.invulnerableTime = 0;
            io.redspace.ironsspellbooks.damage.DamageSources.applyDamage(e, (float) ((FLAT + e.getMaxHealth() * PCT) * k),
                    io.redspace.ironsspellbooks.api.registry.SpellRegistry.getSpell("pohsmp_core:" + PATH).getDamageSource(caster));
            e.setSecondsOnFire(8);
            Vec3 away = e.position().subtract(c).multiply(1, 0, 1);
            Vec3 v = away.lengthSqr() < 1e-4 ? new Vec3(0, 1.2, 0) : away.normalize().scale(1.6 * k).add(0, 0.9 * k, 0);
            HigherSpell.push(e, v);
        }
        Tasks.add(new Tasks.Task() {   // shock wave on the ground and the rising smoke cloud
            int age;

            @Override
            public boolean tick() {
                age++;
                double r = Math.min(R * 1.6, age * 2.2);
                int n = (int) (r * 4) + 8;
                if (age <= 18) for (int i = 0; i < n; i++) {
                    double a = i * Math.PI * 2 / n;
                    DivineEvents.particle(sl, ParticleTypes.CAMPFIRE_COSY_SMOKE, c.x + Math.cos(a) * r, c.y + 0.3, c.z + Math.sin(a) * r, 1, 0.1, 0.01);
                    if (i % 3 == 0) DivineEvents.particle(sl, ParticleTypes.FLAME, c.x + Math.cos(a) * r, c.y + 0.3, c.z + Math.sin(a) * r, 1, 0.1, 0.02);
                }
                double h = Math.min(26, age * 0.8);
                DivineEvents.particle(sl, ParticleTypes.LARGE_SMOKE, c.x, c.y + h * 0.5, c.z, 6, 1.2, 0.02);
                DivineEvents.particle(sl, ParticleTypes.FLAME, c.x, c.y + h * 0.4, c.z, 4, 0.8, 0.05);
                if (age > 10) DivineEvents.particle(sl, ParticleTypes.CAMPFIRE_SIGNAL_SMOKE, c.x, c.y + h, c.z, 10, 3 + age * 0.08, 0.01);
                return age < 50;
            }
        });
    }
}
