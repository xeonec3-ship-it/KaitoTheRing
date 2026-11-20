package ru.pohsmp.core.mythic;

import io.redspace.ironsspellbooks.api.events.SpellOnCastEvent;
import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.registry.SchoolRegistry;
import io.redspace.ironsspellbooks.api.registry.SpellRegistry;
import io.redspace.ironsspellbooks.api.spells.AbstractSpell;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.spells.SpellRarity;
import io.redspace.ironsspellbooks.api.util.AnimationHolder;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.decoration.ArmorStand;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.network.PacketDistributor;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.fx.Fx;
import ru.pohsmp.core.net.IlluMsg;
import ru.pohsmp.core.net.Net;
import ru.pohsmp.core.spell.CastAnims;
import ru.pohsmp.core.spell.Cutscene;
import ru.pohsmp.core.spell.HigherSpell;
import ru.pohsmp.core.spell.PohSpell;

/**
 * T23 Mythic (docs/specs/tasks/T23_mythic_four.md): a long cast with its own camera scene for everyone within 64, then a zone that lives on
 * by itself ({@link Zone}). The spell's own seal is in its cast effect, so no school sign and no tier seal on top (ownSeal). Scroll-only:
 * no mana, no cooldown, never crafted or looted.
 */
public abstract class MythicT23 extends PohSpell implements ru.pohsmp.core.spell.FixedCastSpell {
    public static final int TAIL = 20;
    protected final int cast, scene;
    private final String path;

    protected MythicT23(String path, ResourceLocation school, int cast, int scene) {
        super(path, school, SpellRarity.LEGENDARY, 1, 0, cast, 0, 0);
        this.path = path;
        this.cast = cast;
        this.scene = scene;
    }

    @Override public CastType getCastType() { return CastType.LONG; }
    @Override public boolean canBeInterrupted(Player player) { return false; }
    @Override public boolean allowCrafting() { return false; }
    @Override public boolean ownSeal() { return true; }
    @Override public Optional<SoundEvent> getCastFinishSound() { return Optional.empty(); }
    @Override public AnimationHolder getCastStartAnimation() { return CastAnims.of(path + "_cast"); }
    @Override public AnimationHolder getCastFinishAnimation() { return CastAnims.of(path + "_finish"); }

    @Override
    public void onClientPreCast(Level level, int spellLevel, LivingEntity entity, net.minecraft.world.InteractionHand hand, @javax.annotation.Nullable MagicData md) {
        super.onClientPreCast(level, spellLevel, entity, hand, md);
        CastAnims.hideHands(level, entity, getEffectiveCastTime(spellLevel, entity));
    }

    protected MutableComponent castLine() {
        return Component.translatable("ui.pohsmp_core.mythic_t23.cast", cast / 20);
    }

    protected static MutableComponent line(String key, Object... args) {
        return Component.translatable("ui.pohsmp_core." + key, args);
    }

    protected static double d(net.minecraftforge.common.ForgeConfigSpec.DoubleValue v) {
        return ru.pohsmp.core.spell.illusion.IllusionBase.cfg(v, v.getDefault());
    }

    protected static int i(net.minecraftforge.common.ForgeConfigSpec.IntValue v) {
        return ru.pohsmp.core.spell.illusion.IllusionBase.cfg(v, v.getDefault());
    }

    protected static int ticks(net.minecraftforge.common.ForgeConfigSpec.DoubleValue seconds) {
        return Math.max(1, (int) Math.round(d(seconds) * 20));
    }

    // ---------------------------------------------------------------- who is who

    /** Someone the zone acts against: players (not creative/spectator) that are not the caster's friends, and the caster's foes among mobs. */
    public static boolean enemy(LivingEntity caster, LivingEntity e) {
        if (!e.isAlive() || HigherSpell.friendly(caster, e)) return false;
        if (e instanceof Player p) return !p.isCreative() && !p.isSpectator();
        return HigherSpell.foe(caster, e);
    }

    /** The caster itself, its team, its pets. */
    public static boolean ally(LivingEntity caster, LivingEntity e) {
        return e.isAlive() && !(e instanceof ArmorStand) && !e.isSpectator() && HigherSpell.friendly(caster, e);
    }

    protected static void say(LivingEntity e, String key, Object... args) {
        if (e instanceof Player p) p.displayClientMessage(Component.translatable("ui.pohsmp_core." + key, args), true);
    }

    protected static void sky(ServerPlayer p, int kind, int ticks) {
        Net.CH.send(PacketDistributor.PLAYER.with(() -> p), new IlluMsg(IlluMsg.SKY, p.getId(), ticks, kind, null, "", 0, 0, 0, 0, 0));
    }

    // ---------------------------------------------------------------- the cast and its scene

    protected static final class Cast {
        int cutKey, fx = -1, age;
        List<UUID> watchers = List.of();
        Vec3 point, dir;
        int extra = -1;
        boolean released;
    }

    private static final Map<UUID, Cast> CASTS = new HashMap<>();

    /** Where the spell happens (the tree's foot, the caster...) - sets c.point and c.dir. */
    protected abstract void aim(ServerLevel sl, LivingEntity caster, Cast c);

    /** The camera's second point. */
    protected abstract Vec3 focus(Cast c);

    protected abstract int castFx(ServerLevel sl, LivingEntity caster, Cast c);

    protected void castTick(ServerLevel sl, LivingEntity caster, Cast c) {}

    /** The cast is done: start the zone. */
    protected abstract void release(ServerLevel sl, LivingEntity caster, Cast c);

    private Cast begin(ServerLevel sl, LivingEntity caster) {
        Cast c = new Cast();
        Vec3 look = caster.getLookAngle().multiply(1, 0, 1);
        c.dir = look.lengthSqr() < 1e-4 ? new Vec3(0, 0, 1) : look.normalize();
        c.point = caster.position();
        aim(sl, caster, c);
        c.cutKey = HigherSpell.key();
        c.watchers = Cutscene.start(sl, caster, c.cutKey, scene, cast + TAIL, focus(c), Math.atan2(c.dir.z, c.dir.x));
        c.fx = castFx(sl, caster, c);
        CASTS.put(caster.getUUID(), c);
        return c;
    }

    @Override
    public void onServerPreCast(Level level, int spellLevel, LivingEntity caster, MagicData md) {
        super.onServerPreCast(level, spellLevel, caster, md);
        if (level instanceof ServerLevel sl) begin(sl, caster);
    }

    @Override
    public void onServerCastTick(Level level, int spellLevel, LivingEntity caster, MagicData md) {
        super.onServerCastTick(level, spellLevel, caster, md);
        if (!(level instanceof ServerLevel sl)) return;
        Cast c = CASTS.get(caster.getUUID());
        if (c == null) c = begin(sl, caster);
        c.age++;
        castTick(sl, caster, c);
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            Cast c = CASTS.get(caster.getUUID());
            if (c == null) c = begin(sl, caster);
            if (!c.released) {
                c.released = true;
                release(sl, caster, c);
            }
        }
        super.onCast(level, spellLevel, caster, source, md);
    }

    @Override
    public void onServerCastComplete(Level level, int spellLevel, LivingEntity caster, MagicData md, boolean cancelled) {
        Cast c = CASTS.remove(caster.getUUID());
        if (c != null && level instanceof ServerLevel sl) {
            if (!c.released) {   // broken off: the scene glides back, the effect fades
                if (c.fx >= 0) Fx.stop(sl, c.fx, "");
                if (c.extra >= 0) Fx.stop(sl, c.extra, "");
                Cutscene.end(sl, caster, c.watchers, c.cutKey);
            } else {
                List<UUID> w = c.watchers;
                int key = c.cutKey;
                int[] left = {TAIL};
                ru.pohsmp.core.spell.Tasks.add(() -> {
                    if (--left[0] > 0) return true;
                    Cutscene.end(sl, caster, w, key);
                    return false;
                });
            }
        }
        super.onServerCastComplete(level, spellLevel, caster, md, cancelled);
    }

    // ---------------------------------------------------------------- zones

    /** What a spell leaves after its cast; ticks on the server until it says false. */
    public interface Zone {
        boolean tick();

        default void stop() {}
    }

    static final List<Zone> ZONES = new ArrayList<>();

    /** Players that cast a Blood or Forbidden spell, by the game time of that cast («Последний рассвет»). */
    static final Map<UUID, Long> DARK_CAST = new HashMap<>();

    public static final class Events {
        private Events() {}

        @SubscribeEvent
        public static void onTick(TickEvent.ServerTickEvent e) {
            if (e.phase != TickEvent.Phase.END || ZONES.isEmpty()) return;
            List<Zone> now = new ArrayList<>(ZONES);
            for (Zone z : now) {
                boolean on;
                try {
                    on = z.tick();
                } catch (RuntimeException ex) {
                    ru.pohsmp.core.PohCore.LOG.error("[pohsmp_core] T23 zone failed", ex);
                    on = false;
                }
                if (!on) ZONES.remove(z);
            }
        }

        @SubscribeEvent
        public static void onSpell(SpellOnCastEvent e) {
            AbstractSpell s = SpellRegistry.getSpell(e.getSpellId());
            if (s == null || s.getSchoolType() == null) return;
            ResourceLocation school = s.getSchoolType().getId();
            if (school.equals(SchoolRegistry.BLOOD_RESOURCE) || school.equals(Reg.FORBIDDEN_ID))
                DARK_CAST.put(e.getEntity().getUUID(), e.getEntity().level().getGameTime());
        }

        @SubscribeEvent
        public static void onStopping(ServerStoppingEvent e) {
            for (Zone z : ZONES) z.stop();
            ZONES.clear();
            CASTS.clear();
            DARK_CAST.clear();
        }
    }
}
