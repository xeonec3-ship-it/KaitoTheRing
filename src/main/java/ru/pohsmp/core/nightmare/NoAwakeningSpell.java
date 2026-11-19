package ru.pohsmp.core.nightmare;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.util.AnimationHolder;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.living.LivingDeathEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.network.PacketDistributor;
import ru.pohsmp.core.ServerConfig;
import ru.pohsmp.core.fx.Fx;
import ru.pohsmp.core.illusion.Illusions;
import ru.pohsmp.core.net.IlluMsg;
import ru.pohsmp.core.net.Net;
import ru.pohsmp.core.spell.CastAnims;
import ru.pohsmp.core.spell.Cutscene;
import ru.pohsmp.core.spell.HigherSpell;

/**
 * T25 «Пробуждение не наступит» (Mythic): a 17 s cast with the camera scene (Cutscene.NO_AWAKENING) for everyone within 64 blocks. After
 * the title (13.1 s) the caster turns into nm_dread in the scene and the victims (enemy players within [no_awakening] radius) see it so from
 * then on; at 17 s they are all at stage 3 for
 * [no_awakening] seconds, in the world of the nightmare, and the real monsters round them look like nightmares on their clients (their
 * damage is real; the bestiary's is not). Every [no_awakening] thickenEverySeconds it thickens: 1 more nightmares, 2 the faces of friends
 * come to bite (mimics), 3 the names of real people are gone, 4 the deepest. Killing the caster ends it for all, Blessing for one.
 */
public class NoAwakeningSpell extends NightmareSpells.Base {
    public static final String PATH = NightmareSpells.NO_AWAKENING;
    /** Owner 19.11: the cast is 17 s; after the title (12 s) the caster turns into the Dread at MORPH_AT in front of the watchers. */
    public static final int CAST = 340, TAIL = 20, MORPH_AT = 262;

    public NoAwakeningSpell() {
        super(PATH, Rank.MYTHIC, CAST);
    }

    @Override public CastType getCastType() { return CastType.LONG; }
    @Override public boolean canBeInterrupted(Player player) { return false; }
    @Override public AnimationHolder getCastStartAnimation() { return CastAnims.of("nightmare_abyss_cast"); }
    @Override public AnimationHolder getCastFinishAnimation() { return CastAnims.of("nightmare_abyss_finish"); }
    @Override public Optional<SoundEvent> getCastStartSound() { return Optional.empty(); }
    @Override public Optional<SoundEvent> getCastFinishSound() { return Optional.empty(); }

    @Override
    public void onClientPreCast(Level level, int spellLevel, LivingEntity entity, net.minecraft.world.InteractionHand hand, @javax.annotation.Nullable MagicData md) {
        super.onClientPreCast(level, spellLevel, entity, hand, md);
        CastAnims.hideHands(level, entity, getEffectiveCastTime(spellLevel, entity));
    }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("cast"), ui("time", n(d(ServerConfig.NA_SECONDS))));
    }

    // ---------------------------------------------------------------- the cast and its scene

    private static final class Cast {
        int cutKey, fx = -1, age;
        List<UUID> watchers = List.of();
    }

    private static final Map<UUID, Cast> CASTS = new HashMap<>();

    @Override
    public void onServerPreCast(Level level, int spellLevel, LivingEntity caster, MagicData md) {
        super.onServerPreCast(level, spellLevel, caster, md);
        if (level instanceof ServerLevel sl) startCast(sl, caster);
    }

    private static Cast startCast(ServerLevel sl, LivingEntity caster) {
        Cast c = new Cast();
        Vec3 look = caster.getLookAngle().multiply(1, 0, 1);
        Vec3 dir = look.lengthSqr() < 1e-4 ? new Vec3(0, 0, 1) : look.normalize();
        c.cutKey = HigherSpell.key();
        c.watchers = Cutscene.start(sl, caster, c.cutKey, Cutscene.NO_AWAKENING, CAST + TAIL, caster.position().add(dir.scale(5)), Math.atan2(dir.z, dir.x));
        c.fx = fx(sl, Fx.fx("nightmare_no_awakening_cast").at(caster.position()).caster(caster), "nightmare_no_awakening_cast");
        sl.playSound(null, caster.getX(), caster.getY() + 1, caster.getZ(), NmSounds.CAST_NO_AWAKENING, SoundSource.PLAYERS, 1f, 1f);
        CASTS.put(caster.getUUID(), c);
        return c;
    }

    @Override
    public void onServerCastTick(Level level, int spellLevel, LivingEntity caster, MagicData md) {
        super.onServerCastTick(level, spellLevel, caster, md);
        if (!(level instanceof ServerLevel sl)) return;
        Cast c = CASTS.get(caster.getUUID());
        if (c == null) c = startCast(sl, caster);
        c.age++;
        switch (c.age) {
            case 180 -> Cutscene.flash(sl, c.watchers, 6, 0xB01030);   // 9.0 s: the heartbeat, the face breaks
            case 220 -> Cutscene.flash(sl, c.watchers, 4, 0x3A0A16);
            case 236 -> Cutscene.flash(sl, c.watchers, 4, 0xE0285A);
            case MORPH_AT -> {   // after the title: the caster turns into the Dread - for the watchers in the scene, for its victims from now on
                Cutscene.flash(sl, c.watchers, 8, 0x7A1040);
                Vec3 a = caster.position();
                fx(sl, Fx.fx("nightmare_no_awakening_morph").at(a).caster(caster).attach(caster), "nightmare_no_awakening_morph");
                sl.sendParticles(net.minecraft.core.particles.ParticleTypes.SQUID_INK, a.x, a.y + 1.2, a.z, 60, 0.5, 0.9, 0.5, 0.05);
                sl.sendParticles(new net.minecraft.core.particles.DustParticleOptions(new org.joml.Vector3f(0.7f, 0.05f, 0.2f), 1.6f),
                        a.x, a.y + 1.2, a.z, 40, 0.6, 1.0, 0.6, 0);
                sl.playSound(null, a.x, a.y + 1, a.z, net.minecraft.sounds.SoundEvents.WARDEN_EMERGE, SoundSource.PLAYERS, 2f, 0.8f);
                for (ServerPlayer p : victims(sl, caster)) dread(p, caster, CAST - MORPH_AT + ticks(ServerConfig.NA_SECONDS), 0);
            }
            case 300 -> sl.playSound(null, caster.getX(), caster.getY() + 1, caster.getZ(), net.minecraft.sounds.SoundEvents.WARDEN_ROAR,
                    SoundSource.PLAYERS, 2f, 0.7f);
            default -> {}
        }
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) begin(sl, caster);
        super.onCast(level, spellLevel, caster, source, md);
    }

    @Override
    public void onServerCastComplete(Level level, int spellLevel, LivingEntity caster, MagicData md, boolean cancelled) {
        Cast c = CASTS.remove(caster.getUUID());
        if (c != null && level instanceof ServerLevel sl) {
            if (cancelled) {
                if (c.fx >= 0) Fx.stop(sl, c.fx, "");
                Cutscene.end(sl, caster, c.watchers, c.cutKey);
                for (ServerPlayer p : victims(sl, caster)) end(p, caster, false);
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

    // ---------------------------------------------------------------- the nightmare

    private static final class Night {
        final LivingEntity caster;
        final ServerLevel sl;
        final long until;
        final Map<UUID, Integer> worldFx = new HashMap<>();
        int step;
        long nextStep;

        Night(LivingEntity caster, ServerLevel sl, long until) {
            this.caster = caster;
            this.sl = sl;
            this.until = until;
        }
    }

    private static final Map<UUID, Night> NIGHTS = new HashMap<>();

    /** Enemy players within the radius of the caster now (creative and spectators are not dreamers). */
    private static List<ServerPlayer> victims(ServerLevel sl, LivingEntity caster) {
        double r = d(ServerConfig.NA_RADIUS);
        List<ServerPlayer> out = new ArrayList<>();
        for (ServerPlayer p : sl.players())
            if (p != caster && !p.isSpectator() && !p.isCreative() && p.distanceToSqr(caster) <= r * r && !Illusions.ally(caster, p)) out.add(p);
        return out;
    }

    /** The zone that tells the victim's client: the caster is the Dread, real monsters are nightmares; text = the thickening step. */
    private static void dread(ServerPlayer p, LivingEntity caster, int ticks, int step) {
        Net.CH.send(PacketDistributor.PLAYER.with(() -> p), new IlluMsg(IlluMsg.ZONE, caster.getId(), ticks, IlluMsg.Z_NO_AWAKENING, null,
                Integer.toString(step), caster.getX(), caster.getY(), caster.getZ(), 0, 0));
    }

    private static void begin(ServerLevel sl, LivingEntity caster) {
        Night old = NIGHTS.remove(caster.getUUID());
        if (old != null) finish(old, false);
        int ticks = ticks(ServerConfig.NA_SECONDS);
        Night n = new Night(caster, sl, Immersion.now() + ticks);
        n.nextStep = Immersion.now() + Math.round(d(ServerConfig.NA_THICKEN) * 20);
        NIGHTS.put(caster.getUUID(), n);
        for (ServerPlayer p : victims(sl, caster)) take(n, p);
        Illusions.logZone("no_awakening", sl, caster, caster.position(), d(ServerConfig.NA_RADIUS));
    }

    private static void take(Night n, ServerPlayer p) {
        int left = (int) Math.max(1, n.until - Immersion.now());
        Immersion.hold(p, 3, left);
        Immersion.by(p, n.caster);
        Bestiary.allow(p, limit(n.step), left);
        dread(p, n.caster, left, n.step);
        n.worldFx.put(p.getUUID(), fx(n.sl, Fx.fx("nightmare_no_awakening_world").at(p.position()).caster(p).attach(p).duration(left).only(p),
                "nightmare_no_awakening_world"));
    }

    /** Nightmares round one victim: limitStage3, rising each step up to limitMythic. */
    private static int limit(int step) {
        int lo = i(ServerConfig.IM_LIMIT_3), hi = i(ServerConfig.IM_LIMIT_MYTHIC);
        return lo + (hi - lo) * Math.min(4, step) / 4;
    }

    private static void thicken(Night n) {
        n.step++;
        int left = (int) Math.max(1, n.until - Immersion.now());
        for (var it = n.worldFx.keySet().iterator(); it.hasNext(); ) {
            ServerPlayer p = n.sl.getServer().getPlayerList().getPlayer(it.next());
            if (p == null) {
                it.remove();
                continue;
            }
            fx(n.sl, Fx.fx("nightmare_no_awakening_thicken").at(p.position()).caster(p).attach(p).only(p), "nightmare_no_awakening_thicken");
            p.connection.send(new net.minecraft.network.protocol.game.ClientboundSoundPacket(net.minecraft.core.Holder.direct(NmSounds.THICKEN),
                    SoundSource.HOSTILE, p.getX(), p.getY(), p.getZ(), 1f, 1f, p.getRandom().nextLong()));
            p.displayClientMessage(Component.translatable("ui.pohsmp_core.no_awakening.thicken." + Math.min(4, n.step))
                    .withStyle(s -> s.withColor(0xE0285A)), true);
            Bestiary.allow(p, limit(n.step), left);
            dread(p, n.caster, left, n.step);
            if (n.step >= 2)   // the faces of friends come to bite
                for (int k = 0; k < 2; k++) Bestiary.spawnFor(p, NightmareMob.Kind.MIMIC, 8 + p.getRandom().nextInt(6));
        }
    }

    private static void end(ServerPlayer p, LivingEntity caster, boolean dispelFx) {
        if (dispelFx) fx(p.serverLevel(), Fx.fx("nightmare_no_awakening_dispel").at(p.position()).caster(p).attach(p).only(p), "nightmare_no_awakening_dispel");
        Net.CH.send(PacketDistributor.PLAYER.with(() -> p), new IlluMsg(IlluMsg.ZONE_END, caster.getId(), 0, IlluMsg.Z_NO_AWAKENING, null, "", 0, 0, 0, 0, 0));
    }

    /** All of it over: natural end (the stage then falls by itself) or broken (the caster died - the immersion goes too). */
    private static void finish(Night n, boolean broken) {
        for (var en : n.worldFx.entrySet()) {
            if (en.getValue() >= 0) Fx.stop(n.sl, en.getValue(), "");
            ServerPlayer p = n.sl.getServer().getPlayerList().getPlayer(en.getKey());
            if (p == null) continue;
            end(p, n.caster, broken);
            if (broken) Immersion.clear(p);
        }
        n.worldFx.clear();
    }

    static {
        Illusions.onDispel(t -> {   // Blessing: that one wakes up
            boolean any = false;
            if (!(t instanceof ServerPlayer p)) return false;
            for (Night n : NIGHTS.values()) {
                Integer f = n.worldFx.remove(p.getUUID());
                if (f == null) continue;
                if (f >= 0) Fx.stop(n.sl, f, "");
                end(p, n.caster, true);
                any = true;
            }
            return any;
        });
    }

    public static final class Events {
        private Events() {}

        /* driven by Illusions.onTick (TickHub) */
        public static void onTick(TickEvent.ServerTickEvent e) {
            if (e.phase != TickEvent.Phase.END || NIGHTS.isEmpty()) return;
            long now = Immersion.now();
            for (var it = NIGHTS.values().iterator(); it.hasNext(); ) {
                Night n = it.next();
                if (now >= n.until) {
                    finish(n, false);
                    it.remove();
                    continue;
                }
                if (!n.caster.isAlive() || n.caster.isRemoved()) {   // killed (or gone): the nightmare breaks for everyone
                    finish(n, true);
                    it.remove();
                    continue;
                }
                if (now >= n.nextStep) {
                    thicken(n);
                    n.nextStep = now + Math.round(d(ServerConfig.NA_THICKEN) * 20);
                }
                if (now % 20 == 0)
                    for (UUID id : n.worldFx.keySet()) {
                        ServerPlayer p = n.sl.getServer().getPlayerList().getPlayer(id);
                        if (p != null) Immersion.touch(p);
                    }
            }
        }

        @SubscribeEvent
        public static void onDeath(LivingDeathEvent e) {   // a victim that dies wakes up (its immersion goes with Immersion.onDeath)
            if (!(e.getEntity() instanceof ServerPlayer p)) return;
            for (Night n : NIGHTS.values()) {
                Integer f = n.worldFx.remove(p.getUUID());
                if (f == null) continue;
                if (f >= 0) Fx.stop(n.sl, f, "");
                end(p, n.caster, false);
            }
        }

        @SubscribeEvent
        public static void onStopping(ServerStoppingEvent e) {
            NIGHTS.clear();
            CASTS.clear();
        }
    }
}
