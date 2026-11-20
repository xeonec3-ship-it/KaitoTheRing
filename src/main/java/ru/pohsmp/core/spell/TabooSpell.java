package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.events.SpellPreCastEvent;
import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.spells.SpellAnimations;
import io.redspace.ironsspellbooks.api.spells.SpellRarity;
import io.redspace.ironsspellbooks.api.util.AnimationHolder;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import net.minecraft.core.particles.DustParticleOptions;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.effect.MobEffect;
import net.minecraft.world.effect.MobEffectCategory;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.registries.ForgeRegistries;
import org.joml.Vector3f;
import ru.pohsmp.core.DivineEvents;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.fx.Fx;

/**
 * Divine Taboo, levels 1-6. 25 s cast that cannot be interrupted, with a cutscene for everyone around. A zone of 128 blocks around the cast point:
 * nobody but the caster may cast Iron's spells inside (MNA magic is silenced too), and every 5 s all harmful effects
 * (except Divine Backlash) are washed off everyone inside. Lasts 1/5/10/20/30/60 min. Not kept across a server restart.
 */
public class TabooSpell extends PohSpell implements ru.pohsmp.core.spell.FixedCastSpell {
    public static final String PATH = "divine_taboo";
    public static final double R = 128;
    private static final int[] MINUTES = {1, 5, 10, 20, 30, 60};
    private static final ResourceLocation MNA_SILENCE = new ResourceLocation("mna", "silence");
    private static final DustParticleOptions GOLD = new DustParticleOptions(new Vector3f(1f, 0.85f, 0.35f), 2f);

    private static final class Zone {
        ResourceKey<Level> dim;
        Vec3 c;
        UUID caster;
        long until;
        int fx = -1;
    }

    /** The seal over the field (fx taboo_zone); players who come closer later get it from Fx with its current age. */
    private static void sendSeal(ServerLevel sl, Zone z, float yaw) {
        int left = (int) Math.max(1, z.until - sl.getGameTime());
        z.fx = Fx.play(sl, Fx.fx("taboo_zone").at(z.c).yaw(yaw).duration(left));
    }

    private static final List<Zone> ZONES = new ArrayList<>();

    public static final int CAST = 500;

    /** The 25 s cast: cutscene for everyone around and the rising seals (fx taboo_cast). */
    private static final class Casting {
        Vec3 at;
        int fx, cutKey;
        List<UUID> watchers = new ArrayList<>();
    }

    private static final java.util.Map<UUID, Casting> CASTING = new java.util.HashMap<>();

    public TabooSpell() {
        super(PATH, Reg.DIVINE_ID, SpellRarity.LEGENDARY, 6, 0, CAST, 0, 0);
    }

    @Override
    public void onServerPreCast(Level level, int spellLevel, LivingEntity caster, MagicData md) {
        super.onServerPreCast(level, spellLevel, caster, md);
        if (level instanceof ServerLevel sl) begin(sl, caster);
    }

    private static Casting begin(ServerLevel sl, LivingEntity caster) {
        Casting c = new Casting();
        c.at = caster.position();
        c.cutKey = HigherSpell.key();
        Vec3 look = caster.getLookAngle();
        double ang = Math.atan2(look.z, look.x);
        c.watchers = Cutscene.start(sl, caster, c.cutKey, Cutscene.TABOO, CAST, c.at.add(0, 56, 0), ang);
        c.fx = Fx.play(sl, Fx.fx("taboo_cast").at(c.at).caster(caster));
        CASTING.put(caster.getUUID(), c);
        return c;
    }

    @Override
    public void onServerCastComplete(Level level, int spellLevel, LivingEntity caster, MagicData md, boolean cancelled) {
        Casting c = CASTING.remove(caster.getUUID());
        if (c != null && level instanceof ServerLevel sl) {
            Fx.stop(sl, c.fx, "");
            Cutscene.end(sl, caster, c.watchers, c.cutKey);
        }
        super.onServerCastComplete(level, spellLevel, caster, md, cancelled);
    }

    @Override public CastType getCastType() { return CastType.LONG; }
    @Override public boolean canBeInterrupted(Player player) { return false; }
    @Override public boolean allowCrafting() { return false; }
    @Override public Optional<SoundEvent> getCastStartSound() { return Optional.of(SoundEvents.BEACON_ACTIVATE); }
    @Override public Optional<SoundEvent> getCastFinishSound() { return Optional.of(SoundEvents.BELL_RESONATE); }
    private static final AnimationHolder ANIM_CAST = CastAnims.of("taboo_cast"), ANIM_FINISH = CastAnims.of("taboo_finish");
    @Override public AnimationHolder getCastStartAnimation() { return ANIM_CAST; }
    @Override public AnimationHolder getCastFinishAnimation() { return ANIM_FINISH; }
    @Override
    public void onClientPreCast(Level level, int spellLevel, LivingEntity entity, net.minecraft.world.InteractionHand hand, @javax.annotation.Nullable MagicData md) {
        super.onClientPreCast(level, spellLevel, entity, hand, md);
        CastAnims.hideHands(level, entity, getEffectiveCastTime(spellLevel, entity));
    }

    private static int minutes(int l) {
        return MINUTES[Math.max(0, Math.min(MINUTES.length - 1, l - 1))];
    }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("cast", CAST / 20), ui("zone", (int) R), ui("time", minutes(level)), ui("cleanse"));
    }

    @Override
    public void onServerCastTick(Level level, int spellLevel, LivingEntity entity, MagicData md) {
        super.onServerCastTick(level, spellLevel, entity, md);
        if (level instanceof ServerLevel sl && !CASTING.containsKey(entity.getUUID())) begin(sl, entity);
        if (level instanceof ServerLevel sl && entity.tickCount % 60 == 0)
            sl.playSound(null, entity.getX(), entity.getY(), entity.getZ(), SoundEvents.BELL_RESONATE, SoundSource.PLAYERS, 3f, 0.5f + (entity.tickCount % 300) / 600f);
        if (level instanceof ServerLevel sl && entity.tickCount % 2 == 0) {
            for (int i = 0; i < 6; i++) {
                double a = entity.tickCount * 0.1 + i * Math.PI / 3;
                DivineEvents.particle(sl, GOLD, entity.getX() + Math.cos(a) * 1.6, entity.getY() + 0.1 + (entity.tickCount % 40) / 20.0, entity.getZ() + Math.sin(a) * 1.6, 1, 0, 0);
            }
        }
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            Casting cs = CASTING.get(caster.getUUID());
            if (cs != null) Cutscene.flash(sl, cs.watchers, 20, 0xFFF0B0);
            Zone z = new Zone();
            z.dim = sl.dimension();
            z.c = caster.position();
            z.caster = caster.getUUID();
            z.until = sl.getGameTime() + minutes(spellLevel) * 1200L;
            for (Zone o : new ArrayList<>(ZONES))
                if (o.caster.equals(z.caster)) {
                    ZONES.remove(o);
                    if (o.fx >= 0) Fx.stop(sl, o.fx, "");
                }
            ZONES.add(z);
            sendSeal(sl, z, caster.getYRot());
            sl.playSound(null, z.c.x, z.c.y, z.c.z, SoundEvents.BEACON_POWER_SELECT, SoundSource.PLAYERS, 4f, 0.5f);
            sl.playSound(null, z.c.x, z.c.y, z.c.z, SoundEvents.BELL_BLOCK, SoundSource.PLAYERS, 4f, 0.6f);
            DivineEvents.particle(sl, ParticleTypes.END_ROD, z.c.x, z.c.y + 1, z.c.z, 150, 0.5, 0.6);
            Tasks.add(new Tasks.Task() {
                int age;

                @Override
                public boolean tick() {
                    age++;
                    if (!ZONES.contains(z)) return false;
                    if (sl.getGameTime() > z.until) {
                        ZONES.remove(z);
                        Fx.stop(sl, z.fx, "");
                        sl.playSound(null, z.c.x, z.c.y, z.c.z, SoundEvents.BEACON_DEACTIVATE, SoundSource.PLAYERS, 4f, 0.6f);
                        return false;
                    }
                    if (age % 100 == 1) cleanse(sl, z);
                    if (age % 10 == 0) {   // golden column at the center and a glimmer around players inside
                        DivineEvents.particle(sl, GOLD, z.c.x, z.c.y + 1 + (age % 60) / 10.0, z.c.z, 2, 0.2, 0);
                        for (ServerPlayer p : sl.players())
                            if (p.position().distanceToSqr(z.c) < R * R && !p.getUUID().equals(z.caster))
                                DivineEvents.particle(sl, GOLD, p.getX(), p.getY() + p.getBbHeight() + 0.4, p.getZ(), 1, 0.15, 0);
                    }
                    return true;
                }
            });
        }
        super.onCast(level, spellLevel, caster, source, md);
    }

    private static void cleanse(ServerLevel sl, Zone z) {
        MobEffect silence = ForgeRegistries.MOB_EFFECTS.getValue(MNA_SILENCE);
        for (ServerPlayer p : sl.players()) {
            if (p.position().distanceToSqr(z.c) >= R * R) continue;
            List<MobEffect> bad = new ArrayList<>();
            for (MobEffectInstance i : p.getActiveEffects())
                if (i.getEffect().getCategory() == MobEffectCategory.HARMFUL && i.getEffect() != Reg.BACKLASH.get() && i.getEffect() != silence) bad.add(i.getEffect());
            if (!bad.isEmpty()) {
                for (MobEffect m : bad) p.removeEffect(m);
                DivineEvents.particle(sl, ParticleTypes.END_ROD, p.getX(), p.getY() + 1, p.getZ(), 8, 0.4, 0.05);
            }
            if (silence != null && !p.getUUID().equals(z.caster)) p.addEffect(new MobEffectInstance(silence, 120, 0, false, false, false));
        }
    }

    public static boolean blocked(Player p) {
        if (ZONES.isEmpty()) return false;
        long now = p.level().getGameTime();
        for (Zone z : ZONES)
            if (z.dim == p.level().dimension() && now <= z.until && !p.getUUID().equals(z.caster) && p.position().distanceToSqr(z.c) < R * R) return true;
        return false;
    }

    public static final class TabooEvents {
        private TabooEvents() {}

        @SubscribeEvent
        public static void onPreCast(SpellPreCastEvent e) {
            if (!e.getEntity().level().isClientSide && blocked(e.getEntity())) e.setCanceled(true);
        }

        @SubscribeEvent
        public static void onStopping(ServerStoppingEvent e) {
            ZONES.clear();
            CASTING.clear();
        }
    }
}
