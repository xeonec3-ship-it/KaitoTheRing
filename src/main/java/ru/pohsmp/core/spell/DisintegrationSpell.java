package ru.pohsmp.core.spell;

import org.jetbrains.annotations.Nullable;
import net.minecraft.world.InteractionHand;
import io.redspace.ironsspellbooks.api.config.DefaultConfig;
import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.AbstractSpell;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.spells.SpellRarity;
import io.redspace.ironsspellbooks.api.util.AnimationHolder;
import io.redspace.ironsspellbooks.api.util.Utils;
import io.redspace.ironsspellbooks.capabilities.magic.TargetEntityCastData;
import java.util.EnumSet;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import net.minecraft.core.particles.DustParticleOptions;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.RelativeMovement;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.living.LivingEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import org.joml.Vector3f;
import ru.pohsmp.core.DivineEvents;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.ServerConfig;
import ru.pohsmp.core.net.Net;

/**
 * Divine school, level 1 (subclass {@link DisintegrationReplicaSpell} — the Higher copy with other damage, colors and a chant). 10 s long cast on a locked target: the target is frozen and lifted, magic circles close around it,
 * then it takes damagePercent (1.0) * max HP + damageFlat ignoring armor and, with alwaysKill (default), dies no matter what
 * is left (absorption, resistances, totems). The cast cannot be interrupted by damage.
 */
public class DisintegrationSpell extends AbstractSpell {
    public static final ResourceLocation ID = new ResourceLocation(PohCore.MODID, "disintegration");
    public static final int CAST_TICKS = 200;

    private final ResourceLocation id;
    private final DefaultConfig config;
    /** Client look: 0 golden (Divine), 1 scarlet (Replica). Sent in the high bits of {@link Net.Fx#type}. */
    protected final int variant;
    protected final DustParticleOptions primary, core;

    public DisintegrationSpell() {
        this(ID, Reg.DIVINE_ID, 0);
    }

    protected DisintegrationSpell(ResourceLocation id, ResourceLocation school, int variant) {
        this.id = id;
        this.variant = variant;
        this.config = new DefaultConfig()
                .setMinRarity(SpellRarity.LEGENDARY)
                .setSchoolResource(school)
                .setMaxLevel(1)
                .setCooldownSeconds(0)
                .setAllowCrafting(false)
                .build();
        this.primary = variant == 1 ? new DustParticleOptions(new Vector3f(1f, 0.16f, 0.22f), 1.5f) : GOLD;
        this.core = variant == 1 ? new DustParticleOptions(new Vector3f(1f, 0.85f, 0.85f), 1.2f) : WHITE;
        this.manaCostPerLevel = 0;
        this.baseSpellPower = 0;
        this.spellPowerPerLevel = 0;
        this.castTime = CAST_TICKS;
        this.baseManaCost = 0;
    }

    @Override public ResourceLocation getSpellResource() { return id; }
    @Override public DefaultConfig getDefaultConfig() { return config; }
    /** Black = invisible: Iron's target box is drawn additively, the circles already mark the target. */
    @Override public Vector3f getTargetingColor() { return new Vector3f(0, 0, 0); }
    @Override public CastType getCastType() { return CastType.LONG; }
    @Override public boolean canBeInterrupted(Player player) { return false; }
    @Override public Optional<SoundEvent> getCastStartSound() { return Optional.of(SoundEvents.BEACON_ACTIVATE); }
    @Override public Optional<SoundEvent> getCastFinishSound() { return Optional.empty(); }
    /** Молитва, как у Хинаты и Шуны в «Слизи» (tools/gen_player_anims.py); ладони сложены — предмет в руках на время каста не рисуется. */
    private static final AnimationHolder ANIM_CAST = CastAnims.of("disintegration_cast"), ANIM_FINISH = CastAnims.of("disintegration_finish");

    @Override public AnimationHolder getCastStartAnimation() { return ANIM_CAST; }
    @Override public AnimationHolder getCastFinishAnimation() { return ANIM_FINISH; }

    @Override
    public void onClientPreCast(Level level, int spellLevel, LivingEntity entity, InteractionHand hand, @Nullable MagicData md) {
        super.onClientPreCast(level, spellLevel, entity, hand, md);
        CastAnims.hideHands(level, entity, getEffectiveCastTime(spellLevel, entity));
    }

    @Override
    public List<MutableComponent> getUniqueInfo(int spellLevel, LivingEntity caster) {
        int pct = (int) Math.round(ServerConfig.DIS_PERCENT.get() * 100);
        if (ServerConfig.DIS_KILL.get()) return List.of(Component.translatable("ui.pohsmp_core.disintegration.kill"));
        return List.of(Component.translatable("ui.pohsmp_core.disintegration.damage", pct + "%", fmt(ServerConfig.DIS_FLAT.get())),
                Component.translatable("ui.pohsmp_core.disintegration.armor"));
    }

    private static String fmt(double d) {
        return d == Math.floor(d) ? String.valueOf((long) d) : String.valueOf(d);
    }

    @Override
    public boolean checkPreCastConditions(Level level, int spellLevel, LivingEntity entity, MagicData md) {
        return Utils.preCastTargetHelper(level, entity, md, this, ServerConfig.DIS_RANGE.get(), 0.35f);
    }

    @Override
    public void onServerPreCast(Level level, int spellLevel, LivingEntity entity, MagicData md) {
        super.onServerPreCast(level, spellLevel, entity, md);
        if (level instanceof ServerLevel sl) startHold(sl, entity, md);
    }

    @Override
    public void onServerCastTick(Level level, int spellLevel, LivingEntity entity, MagicData md) {
        super.onServerCastTick(level, spellLevel, entity, md);
        if (!(level instanceof ServerLevel sl)) return;
        Hold h = HOLDS.get(entity.getUUID());
        if (h == null) h = startHold(sl, entity, md);
        if (h != null) tickHold(sl, entity, h);
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity entity, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            Hold h = HOLDS.remove(entity.getUUID());
            if (h != null) finish(sl, entity, h);
        }
        super.onCast(level, spellLevel, entity, source, md);
    }

    @Override
    public void onServerCastComplete(Level level, int spellLevel, LivingEntity entity, MagicData md, boolean cancelled) {
        Hold h = HOLDS.remove(entity.getUUID());
        if (h != null && level instanceof ServerLevel sl) {
            release(h);
            Net.sendNear(sl, entity.getX(), entity.getY(), entity.getZ(), h.x, h.y, h.z, fx(2, entity.getId(), h.target.getId(), 0, h.x, h.y, h.z));
        }
        super.onServerCastComplete(level, spellLevel, entity, md, cancelled);
    }

    private Net.Fx fx(int type, int caster, int target, int duration, double x, double y, double z) {
        return new Net.Fx(type | variant << 4, caster, target, duration, x, y, z);
    }

    /** Called every hold tick (age from 1 to the cast length). Replica speaks its chant here. */
    protected void chant(ServerLevel sl, LivingEntity caster, int age) {}

    /** The hit itself, after the column. Default: share of max HP + flat (100% + 0), through armor; with alwaysKill the target dies anyway. */
    protected void strike(ServerLevel sl, LivingEntity caster, LivingEntity t) {
        float dmg = (float) (t.getMaxHealth() * ServerConfig.DIS_PERCENT.get() + ServerConfig.DIS_FLAT.get());
        DamageSource src = new DamageSource(sl.registryAccess().registryOrThrow(Registries.DAMAGE_TYPE).getHolderOrThrow(Reg.DIVINE_DAMAGE), caster);
        t.invulnerableTime = 0;
        t.hurt(src, dmg);
        boolean exempt = t instanceof Player p && (p.isCreative() || p.isSpectator());
        if (ServerConfig.DIS_KILL.get() && t.isAlive() && !exempt) {
            // absorption, resistance, totem or another mod kept it alive: finish it, bypassing the totem
            t.setAbsorptionAmount(0);
            t.setHealth(0);
            t.die(src);
        }
        if (!t.isAlive() && !(t instanceof Player)) t.setInvisible(true);
    }

    // ---- target hold ----

    private static final class Hold {
        LivingEntity caster, target;
        int startTick;
        double x, y, z;
        int age;
        boolean noGravity;
    }

    private static final Map<UUID, Hold> HOLDS = new HashMap<>();
    private static final DustParticleOptions GOLD = new DustParticleOptions(new Vector3f(1f, 0.85f, 0.35f), 1.5f);
    private static final DustParticleOptions WHITE = new DustParticleOptions(new Vector3f(1f, 1f, 0.95f), 1.2f);

    private Hold startHold(ServerLevel sl, LivingEntity caster, MagicData md) {
        if (!(md.getAdditionalCastData() instanceof TargetEntityCastData td)) return null;
        LivingEntity t = td.getTarget(sl);
        if (t == null) return null;
        if (t.isPassenger()) t.stopRiding();
        Hold h = new Hold();
        h.caster = caster;
        h.startTick = caster.tickCount;
        h.target = t;
        h.x = t.getX();
        h.y = t.getY();
        h.z = t.getZ();
        h.noGravity = t.isNoGravity();
        HOLDS.put(caster.getUUID(), h);
        int dur = caster instanceof Player p ? getEffectiveCastTime(1, p) : CAST_TICKS;
        Net.sendNear(sl, caster.getX(), caster.getY(), caster.getZ(), h.x, h.y, h.z, fx(0, caster.getId(), t.getId(), dur, h.x, h.y, h.z));
        sl.playSound(null, h.x, h.y, h.z, SoundEvents.BEACON_ACTIVATE, SoundSource.PLAYERS, 2f, 0.6f);
        return h;
    }

    private void tickHold(ServerLevel sl, LivingEntity caster, Hold h) {
        LivingEntity t = h.target;
        if (!t.isAlive() || t.isRemoved() || t.level() != sl) {
            HOLDS.remove(caster.getUUID());
            release(h);
            Net.sendNear(sl, caster.getX(), caster.getY(), caster.getZ(), h.x, h.y, h.z, fx(2, caster.getId(), t.getId(), 0, h.x, h.y, h.z));
            if (caster instanceof ServerPlayer sp) Utils.serverSideCancelCast(sp);
            return;
        }
        h.age++;
        chant(sl, caster, h.age);
        double lift = 0.75 * Math.min(1.0, h.age / 25.0) + 0.08 * Math.sin(h.age * 0.15);
        double y = h.y + lift;
        t.setNoGravity(true);
        if (t instanceof ServerPlayer p) p.connection.teleport(h.x, y, h.z, 0f, 0f, EnumSet.of(RelativeMovement.X_ROT, RelativeMovement.Y_ROT));
        else {
            t.teleportTo(h.x, y, h.z);
            if (t instanceof Mob m) m.getNavigation().stop();
        }
        t.setDeltaMovement(Vec3.ZERO);
        t.fallDistance = 0;

        double cy = y + t.getBbHeight() / 2;
        double p = Math.min(1.0, h.age / (double) CAST_TICKS);
        if (h.age % 2 == 0) {
            double r = 2.6 - 2.0 * p;
            for (int i = 0; i < 3; i++) {
                double a = h.age * 0.25 + i * Math.PI * 2 / 3;
                DivineEvents.particle(sl, primary, h.x + Math.cos(a) * r, cy - 1 + ((h.age * 0.05 + i * 0.33) % 2), h.z + Math.sin(a) * r, 1, 0, 0);
            }
            DivineEvents.particle(sl, ParticleTypes.END_ROD, h.x, cy, h.z, 1, 1.2 * (1 - p) + 0.2, 0.0);
        }
        if (h.age % 40 == 0) sl.playSound(null, h.x, cy, h.z, SoundEvents.AMETHYST_BLOCK_RESONATE, SoundSource.PLAYERS, 2f, 0.5f + (float) p);
        if (h.age == CAST_TICKS - 40) sl.playSound(null, h.x, cy, h.z, SoundEvents.BEACON_POWER_SELECT, SoundSource.PLAYERS, 3f, 0.5f);
        if (p > 0.8) DivineEvents.particle(sl, core, h.x, cy, h.z, 4, 0.15, 0.0);
    }

    private static void release(Hold h) {
        h.target.setNoGravity(h.noGravity);
        h.target.fallDistance = 0;
    }

    private void finish(ServerLevel sl, LivingEntity caster, Hold h) {
        LivingEntity t = h.target;
        release(h);
        double cx = t.getX(), cy = t.getY() + t.getBbHeight() / 2, cz = t.getZ();
        Net.sendNear(sl, caster.getX(), caster.getY(), caster.getZ(), cx, cy, cz, fx(1, caster.getId(), t.getId(), 0, cx, cy, cz));
        sl.playSound(null, cx, cy, cz, SoundEvents.WARDEN_SONIC_BOOM, SoundSource.PLAYERS, 4f, 0.6f);
        sl.playSound(null, cx, cy, cz, SoundEvents.BEACON_DEACTIVATE, SoundSource.PLAYERS, 4f, 0.5f);
        sl.playSound(null, cx, cy, cz, SoundEvents.GENERIC_EXPLODE, SoundSource.PLAYERS, 2f, 1.4f);
        DivineEvents.particle(sl, ParticleTypes.FLASH, cx, cy, cz, 2, 0, 0);
        DivineEvents.particle(sl, ParticleTypes.END_ROD, cx, cy, cz, 140, 0.2, 0.6);
        DivineEvents.particle(sl, core, cx, cy, cz, 120, t.getBbWidth() / 2 + 0.2, 0.0);
        DivineEvents.particle(sl, ParticleTypes.WHITE_ASH, cx, cy, cz, 200, 0.8, 0.05);
        if (!t.isAlive() || t.level() != sl) return;
        strike(sl, caster, t);
    }

    /** Safety: if the caster disappears mid-cast, free the target. */
    public static final class Events {
        private Events() {}

        @SubscribeEvent
        public static void onServerTick(TickEvent.ServerTickEvent e) {
            if (e.phase != TickEvent.Phase.END || HOLDS.isEmpty()) return;
            HOLDS.entrySet().removeIf(en -> {
                Hold h = en.getValue();
                boolean stale = !h.target.isAlive() || h.target.isRemoved() || !h.caster.isAlive() || h.caster.isRemoved()
                        || h.caster.tickCount - h.startTick > CAST_TICKS * 3;
                if (stale) release(h);
                return stale;
            });
        }

        @SubscribeEvent
        public static void onLivingTick(LivingEvent.LivingTickEvent e) {
            if (!(e.getEntity() instanceof ServerPlayer le)) return;
            Hold h = HOLDS.get(le.getUUID());
            if (h != null && !MagicData.getPlayerMagicData(le).isCasting()) {
                HOLDS.remove(le.getUUID());
                release(h);
            }
        }
    }
}
