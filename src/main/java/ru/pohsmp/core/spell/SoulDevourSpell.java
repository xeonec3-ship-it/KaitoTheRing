package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.spells.SpellAnimations;
import io.redspace.ironsspellbooks.api.spells.SpellRarity;
import io.redspace.ironsspellbooks.api.util.AnimationHolder;
import io.redspace.ironsspellbooks.api.util.CameraShakeData;
import io.redspace.ironsspellbooks.api.util.CameraShakeManager;
import io.redspace.ironsspellbooks.api.util.Utils;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import net.minecraft.core.particles.DustParticleOptions;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import org.joml.Vector3f;
import ru.pohsmp.core.DivineEvents;
import ru.pohsmp.core.Reg;

/**
 * Soul Devour (divine, level 1): a 25 s cast that cannot be interrupted, with a cutscene for everyone around and drawn circles
 * (HFx SOUL). The target is held in place in darkness while its soul is drawn out toward the caster; at the end it dies.
 * Nothing saves it: armor, effects, totem, creative mode.
 */
public class SoulDevourSpell extends PohSpell {
    public static final String PATH = "soul_devour";
    public static final int CAST = 500, COLOR = 0x46E0D8;
    private static final DustParticleOptions BLACK = new DustParticleOptions(new Vector3f(0.05f, 0.02f, 0.08f), 1.6f);

    private static final class Hold {
        LivingEntity caster, target;
        Vec3 at;
        int age, key, cutKey;
        List<UUID> watchers = new java.util.ArrayList<>();
    }

    private static final Map<UUID, Hold> HOLDS = new HashMap<>();

    public SoulDevourSpell() {
        super(PATH, Reg.DIVINE_ID, SpellRarity.LEGENDARY, 1, 0, CAST, 0, 0);
    }

    @Override public CastType getCastType() { return CastType.LONG; }
    @Override public boolean canBeInterrupted(Player player) { return false; }
    @Override public boolean allowCrafting() { return false; }
    @Override public Optional<SoundEvent> getCastStartSound() { return Optional.of(SoundEvents.SCULK_SHRIEKER_SHRIEK); }
    @Override public Optional<SoundEvent> getCastFinishSound() { return Optional.empty(); }
    private static final AnimationHolder ANIM_CAST = CastAnims.of("soul_devour_cast"), ANIM_FINISH = CastAnims.of("soul_devour_finish");
    @Override public AnimationHolder getCastStartAnimation() { return ANIM_CAST; }
    @Override public AnimationHolder getCastFinishAnimation() { return ANIM_FINISH; }
    @Override
    public void onClientPreCast(Level level, int spellLevel, LivingEntity entity, net.minecraft.world.InteractionHand hand, @javax.annotation.Nullable MagicData md) {
        super.onClientPreCast(level, spellLevel, entity, hand, md);
        CastAnims.hideHands(level, entity, getEffectiveCastTime(spellLevel, entity));
    }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("time", CAST / 20), ui("death"));
    }

    @Override
    public boolean checkPreCastConditions(Level level, int spellLevel, LivingEntity entity, MagicData md) {
        return Utils.preCastTargetHelper(level, entity, md, this, 24, 0.35f);
    }

    @Override
    public void onServerPreCast(Level level, int spellLevel, LivingEntity entity, MagicData md) {
        super.onServerPreCast(level, spellLevel, entity, md);
        if (level instanceof ServerLevel sl) start(sl, entity, md);
    }

    private Hold start(ServerLevel sl, LivingEntity caster, MagicData md) {
        LivingEntity t = HigherSpell.target(sl, md);
        if (t == null) return null;
        if (t.isPassenger()) t.stopRiding();
        Hold h = new Hold();
        h.caster = caster;
        h.target = t;
        h.at = t.position();
        HOLDS.put(caster.getUUID(), h);
        h.key = HigherSpell.key();
        h.cutKey = HigherSpell.key();
        Vec3 d = h.at.subtract(caster.position());
        double ang = Math.atan2(d.z, d.x);
        h.watchers = Cutscene.start(sl, caster, h.cutKey, Cutscene.SOUL_DEVOUR, CAST, h.at, ang);
        HigherSpell.fx(sl, h.at.x, h.at.y, h.at.z, new ru.pohsmp.core.net.Net.HFx(ru.pohsmp.core.net.Net.HFx.SOUL, h.key, caster.getId(), t.getId(), CAST, h.at.x, h.at.y, h.at.z, ang, COLOR));
        sl.playSound(null, h.at.x, h.at.y, h.at.z, SoundEvents.WARDEN_HEARTBEAT, SoundSource.PLAYERS, 3f, 0.5f);
        return h;
    }

    @Override
    public void onServerCastTick(Level level, int spellLevel, LivingEntity caster, MagicData md) {
        super.onServerCastTick(level, spellLevel, caster, md);
        if (!(level instanceof ServerLevel sl)) return;
        Hold h = HOLDS.get(caster.getUUID());
        if (h == null) h = start(sl, caster, md);
        if (h == null) return;
        LivingEntity t = h.target;
        if (!t.isAlive() || t.isRemoved() || t.level() != sl) {
            finish(sl, caster, HOLDS.remove(caster.getUUID()));
            NpcCast.cancelAny(caster);
            return;
        }
        h.age++;
        HigherSpell.place(t, h.at.x, h.at.y, h.at.z);
        t.setDeltaMovement(Vec3.ZERO);
        t.fallDistance = 0;
        if (t instanceof Mob m) {
            m.getNavigation().stop();
            m.setTarget(null);
        }
        if (h.age % 20 == 1) {
            t.addEffect(new MobEffectInstance(MobEffects.DARKNESS, 60, 0, false, false, false));
            t.addEffect(new MobEffectInstance(MobEffects.MOVEMENT_SLOWDOWN, 40, 6, false, false, false));
            t.addEffect(new MobEffectInstance(MobEffects.WEAKNESS, 40, 4, false, false, false));
        }
        double p = Math.min(1, h.age / (double) CAST);
        Vec3 tc = t.position().add(0, t.getBbHeight() * 0.6, 0);
        Vec3 cc = caster.position().add(0, caster.getBbHeight() * 0.7, 0);
        if (h.age % 2 == 0) {
            DivineEvents.particle(sl, BLACK, tc.x, tc.y, tc.z, 3, t.getBbWidth() * 0.6, 0);
            DivineEvents.particle(sl, ParticleTypes.SQUID_INK, tc.x, tc.y - 0.3, tc.z, 1, 0.3, 0.01);
            int n = 1 + (int) (p * 3);
            for (int i = 0; i < n; i++) {   // souls drift from the target to the caster
                double k = ((h.age * 0.02 + i / (double) n) % 1.0);
                Vec3 q = tc.lerp(cc, k);
                DivineEvents.particle(sl, ParticleTypes.SCULK_SOUL, q.x, q.y + Math.sin(k * Math.PI) * 0.8, q.z, 1, 0.05, 0);
            }
        }
        if (h.age % Math.max(10, 40 - (int) (p * 30)) == 0) sl.playSound(null, tc.x, tc.y, tc.z, SoundEvents.WARDEN_HEARTBEAT, SoundSource.PLAYERS, 2f + (float) p * 2, 0.5f + (float) p * 0.4f);
        if (h.age % 100 == 0) sl.playSound(null, tc.x, tc.y, tc.z, SoundEvents.SOUL_ESCAPE, SoundSource.PLAYERS, 2f, 0.5f);
        switch (h.age) {
            case 120 -> sl.playSound(null, tc.x, tc.y, tc.z, SoundEvents.SCULK_SHRIEKER_SHRIEK, SoundSource.PLAYERS, 3f, 0.5f);
            case 250 -> {
                sl.playSound(null, tc.x, tc.y, tc.z, SoundEvents.ELDER_GUARDIAN_CURSE, SoundSource.PLAYERS, 2f, 0.5f);
                CameraShakeManager.addCameraShake(new CameraShakeData(sl, 20, tc, 40));
            }
            case 420 -> sl.playSound(null, tc.x, tc.y, tc.z, SoundEvents.WARDEN_SONIC_CHARGE, SoundSource.PLAYERS, 3f, 0.5f);
            default -> {}
        }
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            Hold h = HOLDS.remove(caster.getUUID());
            if (h != null) {
                Cutscene.flash(sl, h.watchers, 20, 0xBFFFF8);
                finish(sl, caster, h);
                if (h.target.isAlive()) devour(sl, caster, h.target);
            }
        }
        super.onCast(level, spellLevel, caster, source, md);
    }

    @Override
    public void onServerCastComplete(Level level, int spellLevel, LivingEntity entity, MagicData md, boolean cancelled) {
        Hold h = HOLDS.remove(entity.getUUID());
        if (level instanceof ServerLevel sl) finish(sl, entity, h);
        super.onServerCastComplete(level, spellLevel, entity, md, cancelled);
    }

    /** Ends the cutscene and the circles (the camera comes back before the target dies). */
    private static void finish(ServerLevel sl, LivingEntity caster, Hold h) {
        if (h == null) return;
        HigherSpell.stop(sl, h.at.x, h.at.y, h.at.z, h.key);
        Cutscene.end(sl, caster, h.watchers, h.cutKey);
    }

    private static void devour(ServerLevel sl, LivingEntity caster, LivingEntity t) {
        Vec3 c = t.position().add(0, t.getBbHeight() / 2, 0);
        sl.playSound(null, c.x, c.y, c.z, SoundEvents.WARDEN_SONIC_BOOM, SoundSource.PLAYERS, 3f, 0.4f);
        sl.playSound(null, c.x, c.y, c.z, SoundEvents.SOUL_ESCAPE, SoundSource.PLAYERS, 4f, 0.4f);
        DivineEvents.particle(sl, ParticleTypes.SCULK_SOUL, c.x, c.y, c.z, 60, 0.4, 0.15);
        DivineEvents.particle(sl, BLACK, c.x, c.y, c.z, 80, 0.6, 0);
        DamageSource src = new DamageSource(sl.registryAccess().registryOrThrow(Registries.DAMAGE_TYPE).getHolderOrThrow(Reg.SOUL_DAMAGE), caster);
        t.invulnerableTime = 0;
        t.hurt(src, 1.0E9f);
        if (t.isAlive()) {   // something still refused the damage: finish it directly
            t.setHealth(0);
            t.die(src);
        }
    }

    /** Safety: drop holds whose caster or target is gone. */
    public static final class SoulDevourEvents {
        private SoulDevourEvents() {}

        @SubscribeEvent
        public static void onServerTick(TickEvent.ServerTickEvent e) {
            if (e.phase != TickEvent.Phase.END || HOLDS.isEmpty()) return;
            HOLDS.values().removeIf(h -> !h.caster.isAlive() || h.caster.isRemoved() || !h.target.isAlive() || h.target.isRemoved()
                    || (h.caster instanceof Player p && !MagicData.getPlayerMagicData(p).isCasting()) || h.age > CAST * 2);
        }
    }
}
