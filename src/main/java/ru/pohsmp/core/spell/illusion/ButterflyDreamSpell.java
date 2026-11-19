package ru.pohsmp.core.spell.illusion;

import io.redspace.ironsspellbooks.api.events.SpellPreCastEvent;
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
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.network.protocol.game.ClientboundHurtAnimationPacket;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.living.LivingAttackEvent;
import net.minecraftforge.event.entity.living.LivingDamageEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.network.PacketDistributor;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.ServerConfig;
import ru.pohsmp.core.fx.Fx;
import ru.pohsmp.core.illusion.Illusions;
import ru.pohsmp.core.net.HideMsg;
import ru.pohsmp.core.net.IlluMsg;
import ru.pohsmp.core.net.Net;
import ru.pohsmp.core.spell.CastAnims;
import ru.pohsmp.core.spell.Cutscene;
import ru.pohsmp.core.spell.HigherSpell;

/**
 * T22 «Сон бабочки» (Mythic): a 12 s cast with the camera scene (Cutscene.BUTTERFLY_DREAM). Then for [butterfly_dream] seconds every enemy
 * player within its radius is in the mirror world: the caster and its allies are not drawn for it (a strike or a cast shows the one who did it
 * for 1 s with a flickering outline); hits on it are full, but [butterfly_dream] share of each is written down as illusory; at the waking the
 * butterflies break and that illusory part never comes back - it is real, with one shard strike (fx wake_hit, tick 8). Blessing before the
 * waking: the dream is over for that one and its illusory part comes back as usual.
 */
public class ButterflyDreamSpell extends IllusionBase {
    public static final String PATH = "butterfly_dream";
    private static final int CAST = 240, TAIL = 20, REVEAL = 20, WAKE_HIT = 8, WAKE_ANIM_LEAD = 5;

    public ButterflyDreamSpell() {
        super(PATH, Rank.MYTHIC, CAST);
    }

    @Override public CastType getCastType() { return CastType.LONG; }
    @Override public boolean canBeInterrupted(Player player) { return false; }
    @Override public AnimationHolder getCastStartAnimation() { return CastAnims.of("illusion_butterfly_cast"); }
    @Override public AnimationHolder getCastFinishAnimation() { return CastAnims.of("illusion_butterfly_finish"); }
    @Override public Optional<SoundEvent> getCastStartSound() { return Optional.of(SoundEvents.AMETHYST_BLOCK_RESONATE); }
    @Override public Optional<SoundEvent> getCastFinishSound() { return Optional.empty(); }

    @Override
    public void onClientPreCast(Level level, int spellLevel, LivingEntity entity, net.minecraft.world.InteractionHand hand, @javax.annotation.Nullable MagicData md) {
        super.onClientPreCast(level, spellLevel, entity, hand, md);
        CastAnims.hideHands(level, entity, getEffectiveCastTime(spellLevel, entity));
    }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("cast", CAST / 20), ui("zone", n(d(ServerConfig.BD_RADIUS)), n(d(ServerConfig.BD_SECONDS))),
                ui("half"));
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
        c.watchers = Cutscene.start(sl, caster, c.cutKey, Cutscene.BUTTERFLY_DREAM, CAST + TAIL, caster.position().add(dir.scale(5)), Math.atan2(dir.z, dir.x));
        Vec3 touch = caster.position().add(dir.scale(0.65)).add(0, 1.4, 0);
        c.fx = fx(sl, Fx.fx("illusion_butterfly_cast").at(caster.position()).caster(caster).point("touch", touch), "illusion_butterfly_cast");
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
        Vec3 a = caster.position();
        switch (c.age) {
            case 40 -> sl.playSound(null, a.x, a.y + 1, a.z, SoundEvents.AMETHYST_CLUSTER_BREAK, SoundSource.PLAYERS, 1.5f, 1.6f);
            case 86 -> sl.playSound(null, a.x, a.y + 1, a.z, SoundEvents.GLASS_BREAK, SoundSource.PLAYERS, 2f, 0.6f);
            case 160 -> sl.playSound(null, a.x, a.y + 1, a.z, SoundEvents.BEACON_POWER_SELECT, SoundSource.PLAYERS, 3f, 0.5f);
            case 180 -> {
                Cutscene.flash(sl, c.watchers, 16, Reg.ILLUSION_COLOR);
                sl.playSound(null, a.x, a.y + 1, a.z, SoundEvents.GLASS_BREAK, SoundSource.PLAYERS, 3f, 0.4f);
            }
            case 236 -> Cutscene.flash(sl, c.watchers, 14, 0xFFFFFF);
            default -> {}
        }
        if (c.age % 40 == 0) sl.playSound(null, a.x, a.y + 1, a.z, SoundEvents.AMETHYST_BLOCK_RESONATE, SoundSource.PLAYERS, 2f, 0.5f + c.age / 480f);
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) dream(sl, caster);
        super.onCast(level, spellLevel, caster, source, md);
    }

    @Override
    public void onServerCastComplete(Level level, int spellLevel, LivingEntity caster, MagicData md, boolean cancelled) {
        Cast c = CASTS.remove(caster.getUUID());
        if (c != null && level instanceof ServerLevel sl) {
            if (cancelled) {
                if (c.fx >= 0) Fx.stop(sl, c.fx, "");
                Cutscene.end(sl, caster, c.watchers, c.cutKey);
            } else {   // the scene keeps its 1 s tail (the camera comes back after it)
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

    // ---------------------------------------------------------------- the dream

    private static final class Dream {
        final LivingEntity caster;
        final ServerLevel sl;
        final List<LivingEntity> hidden = new ArrayList<>();
        /** victim -> its waking time */
        final Map<UUID, Long> victims = new HashMap<>();
        final Map<UUID, Integer> worldFx = new HashMap<>();
        /** hidden one's id -> shown till */
        final Map<Integer, Long> revealed = new HashMap<>();
        /** victim -> the held back part of the hits on it (strikes at the waking) */
        final Map<UUID, Double> deferred = new HashMap<>();
        final int tag;
        long wakeAll;
        boolean woke;

        Dream(LivingEntity caster, ServerLevel sl, int tag) {
            this.caster = caster;
            this.sl = sl;
            this.tag = tag;
        }
    }

    private static final List<Dream> DREAMS = new ArrayList<>();
    private static int TAG = 5_000_000;

    private static void dream(ServerLevel sl, LivingEntity caster) {
        double r = d(ServerConfig.BD_RADIUS);
        int ticks = ticks(ServerConfig.BD_SECONDS);
        Dream d = new Dream(caster, sl, ++TAG);
        d.hidden.add(caster);
        for (ServerPlayer p : sl.players())
            if (p != caster && !p.isSpectator() && p.distanceToSqr(caster) <= r * r && Illusions.ally(caster, p)) d.hidden.add(p);
        long now = Illusions.now();
        for (ServerPlayer v : Illusions.victims(sl, caster, r)) {
            if (v.isCreative()) continue;
            int t = Illusions.duration(v, ticks);
            d.victims.put(v.getUUID(), now + t);
            d.wakeAll = Math.max(d.wakeAll, now + t);
            Net.CH.send(PacketDistributor.PLAYER.with(() -> v), new IlluMsg(IlluMsg.ZONE, caster.getId(), t, IlluMsg.Z_DREAM, null, "",
                    caster.getX(), caster.getY(), caster.getZ(), (float) r, 0));
            for (LivingEntity h : d.hidden) Net.CH.send(PacketDistributor.PLAYER.with(() -> v), new HideMsg(h.getId(), t + 2));
            int f = fx(sl, Fx.fx("illusion_butterfly_world").at(v.position()).caster(v).attach(v).duration(t).only(v), "illusion_butterfly_world");
            if (f >= 0) d.worldFx.put(v.getUUID(), f);
            v.addEffect(new MobEffectInstance(Reg.BUTTERFLY_DREAM.get(), t, 0, false, false, true));
        }
        if (d.victims.isEmpty()) d.wakeAll = now + ticks;
        sl.playSound(null, caster.getX(), caster.getY() + 1, caster.getZ(), SoundEvents.AMETHYST_BLOCK_CHIME, SoundSource.PLAYERS, 3f, 0.5f);
        DREAMS.add(d);
    }

    private static ServerPlayer player(Dream d, UUID id) {
        return d.sl.getServer().getPlayerList().getPlayer(id);
    }

    /** The dream is over for v (waking, Blessing, gone): the hidden ones are drawn again, its mirror world goes; the held back part is
     * dropped here (Blessing, logout, death: it burns) - the waking takes it before. */
    private static void release(Dream d, UUID id) {
        Integer f = d.worldFx.remove(id);
        if (f != null) Fx.stop(d.sl, f, "");
        d.deferred.remove(id);
        ServerPlayer v = player(d, id);
        if (v == null) return;
        Net.CH.send(PacketDistributor.PLAYER.with(() -> v), IlluMsg.of(IlluMsg.ZONE_END, d.caster.getId(), 0));
        Net.CH.send(PacketDistributor.PLAYER.with(() -> v), new IlluMsg(IlluMsg.FAKE_HP, v.getId(), 0, 0, null, "", 0, 0, 0, 0, 0));
        for (LivingEntity h : d.hidden) Net.CH.send(PacketDistributor.PLAYER.with(() -> v), new HideMsg(h.getId(), 0));
        v.removeEffect(Reg.BUTTERFLY_DREAM.get());
    }

    /**
     * Waking of v (owner 19.11): the shards fly in, on tick 8 the held back part of every hit in the dream strikes at once as real damage
     * (it can kill). Till then the victim's hearts show the full damage (FAKE_HP), so the strike looks like nothing new on its bar.
     */
    private static void wake(Dream d, UUID id) {
        double owed = d.deferred.getOrDefault(id, 0.0);
        d.deferred.remove(id);
        ServerPlayer v = player(d, id);
        // the dream goes, but the hearts keep showing the full damage until the strike lands
        Integer f = d.worldFx.remove(id);
        if (f != null) Fx.stop(d.sl, f, "");
        if (v != null) {
            Net.CH.send(PacketDistributor.PLAYER.with(() -> v), IlluMsg.of(IlluMsg.ZONE_END, d.caster.getId(), 0));
            for (LivingEntity h : d.hidden) Net.CH.send(PacketDistributor.PLAYER.with(() -> v), new HideMsg(h.getId(), 0));
            v.removeEffect(Reg.BUTTERFLY_DREAM.get());
        }
        if (v == null || !v.isAlive()) return;
        fx(d.sl, Fx.fx("illusion_butterfly_wake_hit").at(v.position()).caster(d.caster).target(v).attach(v), "illusion_butterfly_wake_hit");
        int[] t = {0};
        LivingEntity caster = d.caster;
        ServerLevel sl = d.sl;
        ru.pohsmp.core.spell.Tasks.add(() -> {
            if (++t[0] < WAKE_HIT) return true;
            Net.CH.send(PacketDistributor.PLAYER.with(() -> v), new IlluMsg(IlluMsg.FAKE_HP, v.getId(), 0, 0, null, "", 0, 0, 0, 0, 0));
            if (!v.isAlive() || v.hasDisconnected()) return false;
            if (owed > 0.01) {
                if (owed < v.getHealth()) {   // the part already went through armour once: straight off the health
                    v.setHealth((float) (v.getHealth() - owed));
                    sl.getChunkSource().broadcastAndSend(v, new ClientboundHurtAnimationPacket(v));
                } else {
                    v.invulnerableTime = 0;
                    v.hurt(Illusions.source(sl, caster), 1_000_000f);
                }
                sl.playSound(null, v.getX(), v.getY() + 1, v.getZ(), SoundEvents.PLAYER_HURT, SoundSource.PLAYERS, 1f, 1f);
                v.displayClientMessage(net.minecraft.network.chat.Component.translatable("ui.pohsmp_core.butterfly_dream.wake", n(Math.round(owed * 10) / 10.0))
                        .withStyle(s -> s.withColor(Reg.ILLUSION_COLOR)), true);
            }
            sl.playSound(null, v.getX(), v.getY() + 1, v.getZ(), SoundEvents.GLASS_BREAK, SoundSource.PLAYERS, 1.2f, 1.3f);
            return false;
        });
    }

    private static void reveal(LivingEntity who) {
        for (Dream d : DREAMS) {
            if (!d.hidden.contains(who)) continue;
            d.revealed.put(who.getId(), Illusions.now() + REVEAL);
            for (UUID id : d.victims.keySet()) {
                ServerPlayer v = player(d, id);
                if (v == null) continue;
                Net.CH.send(PacketDistributor.PLAYER.with(() -> v), new HideMsg(who.getId(), 0));
                Net.CH.send(PacketDistributor.PLAYER.with(() -> v), IlluMsg.of(IlluMsg.GHOST, who.getId(), REVEAL + 2));
                fx(d.sl, Fx.fx("illusion_butterfly_reveal").at(who.position()).caster(who).attach(who).only(v), "illusion_butterfly_reveal");
            }
        }
    }

    /** speaker/listener -> the point (around the listener) it hears the hidden one from, new every 3 s */
    private static final Map<String, Vec3> VOICE_AT = new HashMap<>();
    private static long voiceRoll;

    static {
        ru.pohsmp.core.illusion.Voices.provider(out -> {
            if (DREAMS.isEmpty()) {
                VOICE_AT.clear();
                return;
            }
            long now = Illusions.now();
            boolean roll = now >= voiceRoll;
            if (roll) {
                VOICE_AT.clear();
                voiceRoll = now + 60;
            }
            for (Dream d : DREAMS)
                for (UUID id : d.victims.keySet()) {
                    ServerPlayer v = player(d, id);
                    if (v == null) continue;
                    for (LivingEntity h : d.hidden) {
                        Vec3 at = VOICE_AT.computeIfAbsent(h.getUUID() + "/" + id, k -> {
                            double a = v.getRandom().nextDouble() * Math.PI * 2, r = 3 + v.getRandom().nextDouble() * 3;
                            return new Vec3(Math.cos(a) * r, 1.4, Math.sin(a) * r);
                        });
                        ru.pohsmp.core.illusion.Voices.put(out, h.getUUID(), id, v.position().add(at));
                    }
                }
        });
        Illusions.onDispel(t -> {
            boolean any = false;
            for (Dream d : DREAMS)
                if (d.victims.remove(t.getUUID()) != null) {
                    release(d, t.getUUID());   // the held back part burns (owner 19.11)
                    any = true;
                }
            return any;
        });
    }

    public static final class Events {
        private Events() {}

        @SubscribeEvent
        public static void onTick(TickEvent.ServerTickEvent e) {
            if (e.phase != TickEvent.Phase.END || DREAMS.isEmpty()) return;
            long now = Illusions.now();
            for (var it = DREAMS.iterator(); it.hasNext(); ) {
                Dream d = it.next();
                if (!d.woke && now >= d.wakeAll - WAKE_ANIM_LEAD && d.caster instanceof ServerPlayer cp) {
                    d.woke = true;
                    Net.CH.send(PacketDistributor.TRACKING_ENTITY_AND_SELF.with(() -> cp),
                            new IlluMsg(IlluMsg.ANIM, cp.getId(), 0, 0, null, "pohsmp_illusion_butterfly_wake", 0, 0, 0, 0, 0));
                }
                if (now == d.wakeAll) {
                    fx(d.sl, Fx.fx("illusion_butterfly_wake").at(d.caster.position()).caster(d.caster), "illusion_butterfly_wake");
                    d.sl.playSound(null, d.caster.getX(), d.caster.getY() + 1, d.caster.getZ(), SoundEvents.GLASS_BREAK, SoundSource.PLAYERS, 4f, 0.5f);
                }
                for (var vi = d.victims.entrySet().iterator(); vi.hasNext(); ) {
                    var en = vi.next();
                    ServerPlayer v = player(d, en.getKey());
                    if (now >= en.getValue() || v == null || !v.isAlive() || v.level() != d.sl) {
                        vi.remove();
                        if (v != null && v.isAlive() && now >= en.getValue()) wake(d, en.getKey());
                        else release(d, en.getKey());
                    }
                }
                // a shown one is hidden again after its second
                for (var ri = d.revealed.entrySet().iterator(); ri.hasNext(); ) {
                    var en = ri.next();
                    if (now < en.getValue()) continue;
                    ri.remove();
                    for (var v : d.victims.entrySet()) {
                        ServerPlayer p = player(d, v.getKey());
                        if (p != null) Net.CH.send(PacketDistributor.PLAYER.with(() -> p), new HideMsg(en.getKey(), (int) Math.max(1, v.getValue() - now + 2)));
                    }
                }
                if (d.victims.isEmpty() && now >= d.wakeAll) it.remove();
            }
        }

        /** A strike by a hidden one shows it for a second. */
        @SubscribeEvent
        public static void onAttack(LivingAttackEvent e) {
            if (DREAMS.isEmpty() || e.getEntity().level().isClientSide) return;
            Entity src = e.getSource().getEntity();
            if (src instanceof LivingEntity le) reveal(le);
        }

        /** So does a cast. */
        @SubscribeEvent
        public static void onPreCast(SpellPreCastEvent e) {
            if (!DREAMS.isEmpty() && !e.getEntity().level().isClientSide) reveal(e.getEntity());
        }

        /**
         * Owner 19.11: «половина сейчас, половина при пробуждении». Of each hit on a dreamer only (1 - share) really goes through; the
         * rest is held back and strikes at the waking. The victim's own hearts show the full damage (FAKE_HP: the held back sum).
         */
        @SubscribeEvent(priority = EventPriority.LOWEST)
        public static void onDamage(LivingDamageEvent e) {
            if (DREAMS.isEmpty() || e.isCanceled() || e.getAmount() <= 0) return;
            if (!(e.getEntity() instanceof ServerPlayer v)) return;
            for (Dream d : DREAMS) {
                if (!d.victims.containsKey(v.getUUID())) continue;
                double share = Math.max(0, Math.min(1, IllusionBase.cfg(ServerConfig.BD_SHARE::get, 0.5)));
                float held = (float) (e.getAmount() * share);
                e.setAmount(e.getAmount() - held);
                double sum = d.deferred.merge(v.getUUID(), (double) held, Double::sum);
                Net.CH.send(PacketDistributor.PLAYER.with(() -> v), new IlluMsg(IlluMsg.FAKE_HP, v.getId(), 0, 0, null, "", sum, 0, 0, 0, 0));
                return;
            }
        }

        @SubscribeEvent
        public static void onStopping(ServerStoppingEvent e) {
            DREAMS.clear();
            CASTS.clear();
        }
    }
}
