package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.config.DefaultConfig;
import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.AbstractSpell;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.spells.SpellAnimations;
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
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.ServerConfig;
import ru.pohsmp.core.fx.Fx;

/**
 * Divine school, level 1 (subclass {@link DisintegrationReplicaSpell} - the Higher copy with other damage, colors and a chant).
 * 10 s long cast on a locked target: the target is frozen and lifted, magic circles close around it, then it takes
 * damagePercent (1.0) * max HP + damageFlat ignoring armor and, with alwaysKill (default), dies no matter what is left
 * (absorption, resistances, totems). The cast cannot be interrupted by damage.
 * <p>Look: the data effect {@code fx/disintegration.json} (Replica: {@code disintegration_replica.json}), started at the
 * cast start with the target's feet as the "target" anchor; it is timed for {@link #CAST_TICKS} with the hit on tick 200,
 * so the cast time is fixed (cast speed does not change it) and the hit always lands with the column.
 */
public class DisintegrationSpell extends AbstractSpell {
    public static final ResourceLocation ID = new ResourceLocation(PohCore.MODID, "disintegration");
    public static final int CAST_TICKS = 200;

    private final ResourceLocation id;
    private final DefaultConfig config;
    /** Look: 0 golden (Divine, fx "disintegration"), 1 scarlet (Replica, fx "disintegration_replica"). */
    protected final int variant;

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
    /** Fixed: the effect is timed for 200 ticks, a faster or slower cast would hit before or after the column. */
    @Override public int getEffectiveCastTime(int spellLevel, @javax.annotation.Nullable LivingEntity entity) { return getCastTime(spellLevel); }
    @Override public boolean canBeInterrupted(Player player) { return false; }
    @Override public Optional<SoundEvent> getCastStartSound() { return Optional.of(SoundEvents.BEACON_ACTIVATE); }
    @Override public Optional<SoundEvent> getCastFinishSound() { return Optional.empty(); }
    /** Prayer pose (tools/gen_player_anims.py); hands folded, so the held item is not drawn for the cast. */
    private static final AnimationHolder ANIM_CAST = CastAnims.of("disintegration_cast"), ANIM_FINISH = CastAnims.of("disintegration_finish");

    @Override public AnimationHolder getCastStartAnimation() { return ANIM_CAST; }
    @Override public AnimationHolder getCastFinishAnimation() { return ANIM_FINISH; }

    @Override
    public void onClientPreCast(Level level, int spellLevel, LivingEntity entity, net.minecraft.world.InteractionHand hand, @javax.annotation.Nullable MagicData md) {
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
        if (h != null) {
            release(h);
            if (level instanceof ServerLevel sl) stopFx(sl, h);
        }
        super.onServerCastComplete(level, spellLevel, entity, md, cancelled);
    }

    /** Effect id in assets/pohsmp_core/fx/. */
    protected String fxId() {
        return variant == 1 ? "disintegration_replica" : "disintegration";
    }

    /** Sound pitch: the Replica sounds a little lower ("dirtier"). */
    protected float pitch(float p) {
        return variant == 1 ? p - 0.1f : p;
    }

    /** Cast cancelled or broken: the seals dissolve, the rest fades out. */
    private static void stopFx(ServerLevel sl, Hold h) {
        if (h.fx > 0) Fx.stop(sl, h.fx, "");
        h.fx = -1;
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
            // absorption, resistance, a totem or another mod kept it alive: finish it, bypassing the totem
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
        int fx = -1;
    }

    private static final Map<UUID, Hold> HOLDS = new HashMap<>();

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
        // "target" anchor = the target's feet at the start; the hold keeps it on this x/z, lifted above the ground seal
        h.fx = Fx.play(sl, Fx.fx(fxId()).caster(caster).target(new Vec3(h.x, h.y, h.z)));
        sl.playSound(null, h.x, h.y, h.z, SoundEvents.BEACON_ACTIVATE, SoundSource.PLAYERS, 2f, pitch(0.6f));
        return h;
    }

    private void tickHold(ServerLevel sl, LivingEntity caster, Hold h) {
        LivingEntity t = h.target;
        if (!t.isAlive() || t.isRemoved() || t.level() != sl) {
            HOLDS.remove(caster.getUUID());
            release(h);
            stopFx(sl, h);
            NpcCast.cancelAny(caster);
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

        // sounds on the effect's timeline: seals forming (20, 60, tower 88, 112), rising hum from 140, the shower at 170
        double cy = y + t.getBbHeight() / 2;
        float p = (float) Math.min(1.0, h.age / (double) CAST_TICKS);
        if (h.age == 20 || h.age == 60 || h.age == 88 || h.age == 112)
            sl.playSound(null, h.x, h.y + 4.8, h.z, SoundEvents.AMETHYST_BLOCK_CHIME, SoundSource.PLAYERS, 3f, pitch(0.6f + p));
        if (h.age % 40 == 0) sl.playSound(null, h.x, cy, h.z, SoundEvents.AMETHYST_BLOCK_RESONATE, SoundSource.PLAYERS, 2f, pitch(0.5f + p));
        if (h.age >= 140 && h.age % 10 == 0)
            sl.playSound(null, h.x, cy, h.z, SoundEvents.BEACON_AMBIENT, SoundSource.PLAYERS, 2f + p * 2, pitch(0.5f + (h.age - 140) / 60f));
        if (h.age == CAST_TICKS - 40) sl.playSound(null, h.x, cy, h.z, SoundEvents.BEACON_POWER_SELECT, SoundSource.PLAYERS, 3f, pitch(0.5f));
        if (h.age == 170) sl.playSound(null, h.x, h.y + 4.8, h.z, SoundEvents.TRIDENT_THUNDER, SoundSource.PLAYERS, 2f, pitch(1.6f));
    }

    private static void release(Hold h) {
        h.target.setNoGravity(h.noGravity);
        h.target.fallDistance = 0;
    }

    private void finish(ServerLevel sl, LivingEntity caster, Hold h) {
        LivingEntity t = h.target;
        release(h);
        double cx = t.getX(), cy = t.getY() + t.getBbHeight() / 2, cz = t.getZ();
        // column, flash and dust are in the effect (tick 200); the server only plays the sounds and hits
        sl.playSound(null, cx, cy, cz, SoundEvents.WARDEN_SONIC_BOOM, SoundSource.PLAYERS, 4f, pitch(0.6f));
        sl.playSound(null, cx, cy, cz, SoundEvents.BEACON_DEACTIVATE, SoundSource.PLAYERS, 4f, pitch(0.5f));
        sl.playSound(null, cx, cy, cz, SoundEvents.GENERIC_EXPLODE, SoundSource.PLAYERS, 2f, pitch(1.4f));
        if (!t.isAlive() || t.level() != sl) return;
        strike(sl, caster, t);
    }

    /** Safety: if the caster disappears mid-cast, free the target. */
    public static final class DisintegrationEvents {
        private DisintegrationEvents() {}

        @SubscribeEvent
        public static void onServerTick(TickEvent.ServerTickEvent e) {
            if (e.phase != TickEvent.Phase.END || HOLDS.isEmpty()) return;
            HOLDS.entrySet().removeIf(en -> {
                Hold h = en.getValue();
                boolean stale = !h.target.isAlive() || h.target.isRemoved() || !h.caster.isAlive() || h.caster.isRemoved()
                        || h.caster.tickCount - h.startTick > CAST_TICKS * 3;
                if (stale) {
                    release(h);
                    if (h.caster.level() instanceof ServerLevel sl) stopFx(sl, h);
                }
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
                stopFx(le.serverLevel(), h);
            }
        }
    }
}
