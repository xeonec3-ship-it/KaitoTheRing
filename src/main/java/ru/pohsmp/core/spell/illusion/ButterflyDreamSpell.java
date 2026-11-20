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
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.tags.DamageTypeTags;
import net.minecraft.world.damagesource.CombatRules;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.living.LivingAttackEvent;
import net.minecraftforge.event.entity.living.LivingHurtEvent;
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
 * T22 «Сон бабочки» (Mythic, reworked by the owner 19.11): a 12 s cast with the camera scene (Cutscene.BUTTERFLY_DREAM) and the music.
 * Then for 2 minutes every enemy player within 64 blocks is in the mirror world (left and right swapped): the caster and its allies are not
 * drawn for it (a strike or a cast shows the one who did it for 1 s). Rework 19.11: no hunters - a quiet dream with whispers in its chat,
 * flowers blooming in its steps, and a cocoon of butterflies over it that everyone else sees. Every hit by the caster and its allies is not real: it takes illusory health only; at none left the victim «dies» in the dream and wakes up elsewhere in
 * it. The waking deals nothing - it was just a dream. Hits from outside the dream stay real.
 */
public class ButterflyDreamSpell extends IllusionBase implements ru.pohsmp.core.spell.FixedCastSpell {
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
                ui("fake"), ui("death"), ui("nightmare"));
    }

    // ---------------------------------------------------------------- the cast and its scene

    private static final class Cast {
        int cutKey, fx = -1, age;
        List<UUID> watchers = List.of();
        /** who hears the music (the caster, its allies and the victims within the dream radius at the start) */
        final List<UUID> music = new ArrayList<>();
    }

    /** The music track: 158 s; the waking falls on 132 s of it. */
    private static final int MUSIC_TICKS = 3160;

    private static void music(ServerLevel sl, UUID id, int i, int ticks) {
        ServerPlayer p = sl.getServer().getPlayerList().getPlayer(id);
        if (p != null) Net.CH.send(PacketDistributor.PLAYER.with(() -> p), new IlluMsg(IlluMsg.DREAM_MUSIC, p.getId(), ticks, i, null, "", 0, 0, 0, 0, 0));
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
        double r = d(ServerConfig.BD_RADIUS);
        for (ServerPlayer p : sl.players())
            if (!p.isSpectator() && p.distanceToSqr(caster) <= r * r) {
                c.music.add(p.getUUID());
                music(sl, p.getUUID(), 0, MUSIC_TICKS);
            }
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
            // 19.11 «Небесная бабочка»: no glass sounds - soft chimes, wing strokes at 180 and 234
            case 40 -> sl.playSound(null, a.x, a.y + 1, a.z, SoundEvents.AMETHYST_BLOCK_CHIME, SoundSource.PLAYERS, 1.5f, 1.6f);
            case 86 -> sl.playSound(null, a.x, a.y + 1, a.z, SoundEvents.AMETHYST_BLOCK_RESONATE, SoundSource.PLAYERS, 2f, 0.9f);
            case 160 -> sl.playSound(null, a.x, a.y + 1, a.z, SoundEvents.BEACON_POWER_SELECT, SoundSource.PLAYERS, 3f, 0.5f);
            case 180, 234 -> {
                if (c.age == 180) Cutscene.flash(sl, c.watchers, 16, Reg.ILLUSION_COLOR);
                sl.playSound(null, a.x, a.y + 1, a.z, SoundEvents.ELYTRA_FLYING, SoundSource.PLAYERS, 1.2f, 0.5f);
                sl.playSound(null, a.x, a.y + 1, a.z, SoundEvents.AMETHYST_BLOCK_RESONATE, SoundSource.PLAYERS, 2.5f, 0.6f);
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
                for (UUID id : c.music) music(sl, id, 1, 20);   // the track fades in 1 s
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

    // ---------------------------------------------------------------- T30: the whole spell from a point (Эреб's finale)

    /**
     * T30 «Эреб, Первый Предатель», finale: the spell cast by `point` — an invisible caster standing where the boss stood (the boss
     * itself vanishes during the scene, the point must live to the end of the dream). The same scene, music, fx and sounds as a real
     * cast; after CAST ticks the dream falls on every enemy player within `radius` for `dreamTicks`. No Iron's cast, no mana.
     */
    public static void castFromPoint(ServerLevel sl, LivingEntity point, double radius, int dreamTicks) {
        Cast c = startCast(sl, point);
        ru.pohsmp.core.spell.Tasks.add(() -> {
            if (point.isRemoved()) {   // the point is gone (server stop...): the scene ends
                CASTS.remove(point.getUUID());
                if (c.fx >= 0) Fx.stop(sl, c.fx, "");
                Cutscene.end(sl, point, c.watchers, c.cutKey);
                return false;
            }
            c.age++;
            Vec3 a = point.position();
            if (c.age == 40) sl.playSound(null, a.x, a.y + 1, a.z, SoundEvents.AMETHYST_BLOCK_CHIME, SoundSource.PLAYERS, 1.5f, 1.6f);
            if (c.age == 160) sl.playSound(null, a.x, a.y + 1, a.z, SoundEvents.BEACON_POWER_SELECT, SoundSource.PLAYERS, 3f, 0.5f);
            if (c.age == 180 || c.age == 234) {
                if (c.age == 180) Cutscene.flash(sl, c.watchers, 16, Reg.ILLUSION_COLOR);
                sl.playSound(null, a.x, a.y + 1, a.z, SoundEvents.ELYTRA_FLYING, SoundSource.PLAYERS, 1.2f, 0.5f);
                sl.playSound(null, a.x, a.y + 1, a.z, SoundEvents.AMETHYST_BLOCK_RESONATE, SoundSource.PLAYERS, 2.5f, 0.6f);
            }
            if (c.age == 236) Cutscene.flash(sl, c.watchers, 14, 0xFFFFFF);
            if (c.age % 40 == 0) sl.playSound(null, a.x, a.y + 1, a.z, SoundEvents.AMETHYST_BLOCK_RESONATE, SoundSource.PLAYERS, 2f, 0.5f + c.age / 480f);
            if (c.age < CAST) return true;
            CASTS.remove(point.getUUID());
            dream(sl, point, radius, dreamTicks);
            List<UUID> w = c.watchers;
            int key = c.cutKey;
            int[] left = {TAIL};
            ru.pohsmp.core.spell.Tasks.add(() -> {   // the scene keeps its 1 s tail
                if (--left[0] > 0) return true;
                Cutscene.end(sl, point, w, key);
                return false;
            });
            return false;
        });
    }

    // ---------------------------------------------------------------- the dream

    /**
     * «Death» in the dream (owner 19.11): the dark screen lasts DEATH_SCREEN, the victim is moved on DEATH_MOVE under it, and takes no dream
     * damage for DEATH_GRACE. The new place: random within the dream, on solid ground, not closer than MIN_FROM_CASTER to the caster.
     */
    private static final int DEATH_SCREEN = 30, DEATH_MOVE = 22, DEATH_GRACE = 50;
    /** The waking scene starts this long before the glass breaks at wakeAll (130.3 s of the track, visual letter 19.11). */
    private static final int WAKE_SCENE = 34;
    private static final double MIN_FROM_CASTER = 12;
    /** Rework 19.11: «шёпот сна» every WHISPER_MIN..MAX ticks, WHISPERS lines; a blooming step every STEP blocks walked. */
    private static final int WHISPER_MIN = 500, WHISPER_MAX = 900, WHISPERS = 10;
    private static final double STEP = 0.9;

    private static final class Dream {
        final LivingEntity caster;
        final ServerLevel sl;
        final Vec3 center;
        final double r;
        final List<LivingEntity> hidden = new ArrayList<>();
        /** victim -> its waking time */
        final Map<UUID, Long> victims = new HashMap<>();
        final Map<UUID, Integer> worldFx = new HashMap<>();
        /** hidden one's id -> shown till */
        final Map<Integer, Long> revealed = new HashMap<>();
        /** victim -> health it has «lost» in the dream (its real health is untouched; its hearts show real - lost) */
        final Map<UUID, Double> lost = new HashMap<>();
        /** victim -> no dream damage till (it has just «died») */
        final Map<UUID, Long> grace = new HashMap<>();
        /** victim -> its next whisper, the cocoon fx the others see over it, where its last flower bloomed */
        final Map<UUID, Long> nextWhisper = new HashMap<>();
        final Map<UUID, Integer> cocoon = new HashMap<>();
        final Map<UUID, Vec3> lastStep = new HashMap<>();
        int step;
        /** victim -> its dream wounds (the butterflies around it, up to 12) */
        final Map<UUID, Integer> wounds = new HashMap<>();
        final int tag;
        long wakeAll;
        boolean woke;

        Dream(LivingEntity caster, ServerLevel sl, int tag, double r) {
            this.caster = caster;
            this.sl = sl;
            this.tag = tag;
            this.center = caster.position();
            this.r = r;
        }
    }

    private static final List<Dream> DREAMS = new ArrayList<>();
    private static int TAG = 5_000_000;

    private static void dream(ServerLevel sl, LivingEntity caster) {
        dream(sl, caster, d(ServerConfig.BD_RADIUS), ticks(ServerConfig.BD_SECONDS));
    }

    /** The dream on every enemy player within r of the caster for `ticks` (T30: Эреб's finale gives its own radius and time). */
    private static void dream(ServerLevel sl, LivingEntity caster, double r, int ticks) {
        dream(sl, caster, r, ticks, true);
    }

    /** hideCaster false (T31 «Полное Раскрытие»): the caster is not hidden from the dreamers — it fights them inside the dream. */
    private static void dream(ServerLevel sl, LivingEntity caster, double r, int ticks, boolean hideCaster) {
        Dream d = new Dream(caster, sl, ++TAG, r);
        if (hideCaster) d.hidden.add(caster);
        for (ServerPlayer p : sl.players())
            if (p != caster && !p.isSpectator() && p.distanceToSqr(caster) <= r * r && Illusions.ally(caster, p)) d.hidden.add(p);
        long now = Illusions.now();
        for (ServerPlayer v : Illusions.victims(sl, caster, r)) {
            if (v.isCreative()) continue;
            if (ru.pohsmp.core.nightmare.Immersion.stage(v) >= 1) {   // owner 19.11: one in a nightmare does not dream - it does not wake up
                music(sl, v.getUUID(), 1, 40);
                ru.pohsmp.core.nightmare.NoAwakeningSpell.into(sl, caster, v);
                continue;
            }
            int t = Illusions.duration(v, ticks);
            UUID id = v.getUUID();
            d.victims.put(id, now + t);
            d.wakeAll = Math.max(d.wakeAll, now + t);
            Net.CH.send(PacketDistributor.PLAYER.with(() -> v), new IlluMsg(IlluMsg.ZONE, caster.getId(), t, IlluMsg.Z_DREAM, null, "",
                    caster.getX(), caster.getY(), caster.getZ(), (float) r, 0));
            for (LivingEntity h : d.hidden) Net.CH.send(PacketDistributor.PLAYER.with(() -> v), new HideMsg(h.getId(), t + 2));
            int f = fx(sl, Fx.fx("illusion_butterfly_world").at(v.position()).caster(v).attach(v).duration(t).only(v), "illusion_butterfly_world");
            if (f >= 0) d.worldFx.put(id, f);
            v.addEffect(new MobEffectInstance(Reg.BUTTERFLY_DREAM.get(), t, 0, false, false, true));
            fx(sl, Fx.fx("illusion_dream_enter").at(v.position()).caster(v).attach(v).only(v), "illusion_dream_enter");
            d.lost.put(id, 0.0);
            d.nextWhisper.put(id, now + 100 + sl.random.nextInt(200));
            d.lastStep.put(id, v.position());
            cocoon(d, v, t);   // a ring of butterflies and a small Heavenly butterfly over the sleeper, for everyone but it
        }
        if (d.victims.isEmpty()) d.wakeAll = now + ticks;
        sl.playSound(null, caster.getX(), caster.getY() + 1, caster.getZ(), SoundEvents.AMETHYST_BLOCK_CHIME, SoundSource.PLAYERS, 3f, 0.5f);
        DREAMS.add(d);
    }

    // ---------------------------------------------------------------- T31: «Сон Бабочки: Полное Раскрытие» (Эреб, Длань Лжи)

    /**
     * T31: the dream without the T22 cast (the boss plays its own cast scene): every enemy player within r of the caster dreams for
     * up to `ticks`; the caster is NOT hidden — it is there and fights the dreamers in the dream (its hits are dream hits as usual:
     * not real, a «death» wakes the dreamer elsewhere in the dream). Ended by {@link #wakeNow}.
     */
    public static void openDream(ServerLevel sl, LivingEntity caster, double r, int ticks) {
        dream(sl, caster, r, ticks, false);
    }

    /** T31: every dream of this caster breaks now: the waking scene, then everyone wakes (about WAKE_SCENE ticks). */
    public static void wakeNow(LivingEntity caster) {
        long at = Illusions.now() + WAKE_SCENE + 2;
        for (Dream d : DREAMS) {
            if (d.caster != caster || d.wakeAll <= at) continue;
            d.wakeAll = at;
            d.woke = true;   // no player's waking animation (the caster is a mob)
            for (var en : d.victims.entrySet()) en.setValue(Math.min(en.getValue(), at));
        }
    }

    /** T31: the players dreaming a dream of this caster now. */
    public static List<ServerPlayer> dreamers(LivingEntity caster) {
        List<ServerPlayer> out = new ArrayList<>();
        for (Dream d : DREAMS) {
            if (d.caster != caster) continue;
            for (UUID id : d.victims.keySet()) {
                ServerPlayer v = player(d, id);
                if (v != null) out.add(v);
            }
        }
        return out;
    }

    private static ServerPlayer player(Dream d, UUID id) {
        return d.sl.getServer().getPlayerList().getPlayer(id);
    }

    /** «Шёпот сна»: a quiet italic line in v's chat, no system colours. */
    private static void whisper(Dream d, ServerPlayer v) {
        int k = 1 + d.sl.random.nextInt(WHISPERS);
        v.sendSystemMessage(net.minecraft.network.chat.Component.translatable("ui.pohsmp_core.butterfly_dream.whisper." + k)
                .withStyle(net.minecraft.ChatFormatting.GRAY, net.minecraft.ChatFormatting.ITALIC));
    }

    /** A glowing flower where v stepped: it blooms and sheds its petals in a few seconds (v's dream only). */
    private static void bloom(Dream d, ServerPlayer v) {
        // the feet take turns: 0.16 blocks to the side of the centre (visual letter 19.11)
        Vec3 side = Vec3.directionFromRotation(0, v.getYRot() + 90).scale((d.step ^= 1) == 0 ? 0.16 : -0.16);
        fx(d.sl, Fx.fx("illusion_dream_bloom").at(v.position().add(side)).caster(v).only(v), "illusion_dream_bloom");
    }

    /** The cocoon over v (everyone but v sees it) from now till the dream ends for it, its «death» or ticks. */
    private static void cocoon(Dream d, ServerPlayer v, int ticks) {
        Integer old = d.cocoon.remove(v.getUUID());
        if (old != null) Fx.stop(d.sl, old, "");
        int cf = fx(d.sl, Fx.fx("illusion_dream_cocoon").at(v.position()).caster(v).attach(v).duration(ticks).not(v), "illusion_dream_cocoon");
        if (cf >= 0) d.cocoon.put(v.getUUID(), cf);
    }

    /** A standing place min..max blocks from around (same height +-4), or null. */
    private static Vec3 near(ServerLevel sl, Vec3 around, double min, double max) {
        var rnd = sl.random;
        for (int k = 0; k < 14; k++) {
            double a = rnd.nextDouble() * Math.PI * 2, dist = min + rnd.nextDouble() * (max - min);
            Vec3 p = ground(sl, around.x + Math.cos(a) * dist, around.z + Math.sin(a) * dist, around.y + 4, 8);
            if (p != null) return p;
        }
        return null;
    }

    /** From top down `span` blocks: the first block a player can stand in (solid top below, no liquid, room for the body). */
    private static Vec3 ground(ServerLevel sl, double x, double z, double top, int span) {
        int bx = net.minecraft.util.Mth.floor(x), bz = net.minecraft.util.Mth.floor(z), y0 = net.minecraft.util.Mth.floor(top);
        BlockPos.MutableBlockPos p = new BlockPos.MutableBlockPos(bx, y0, bz);
        if (!sl.isLoaded(p)) return null;
        for (int y = y0; y > y0 - span && y > sl.getMinBuildHeight(); y--) {
            p.set(bx, y, bz);
            BlockPos below = p.below();
            if (!sl.getBlockState(below).isFaceSturdy(sl, below, Direction.UP)) continue;
            if (!sl.getFluidState(p).isEmpty() || !sl.getFluidState(below).isEmpty() || !sl.getFluidState(p.above()).isEmpty()) continue;
            if (!sl.noCollision(new AABB(bx + 0.2, y + 0.01, bz + 0.2, bx + 0.8, y + 1.8, bz + 0.8))) continue;
            return new Vec3(bx + 0.5, y, bz + 0.5);
        }
        return null;
    }

    /** Where v wakes up inside the dream after a «death». */
    private static Vec3 respawnSpot(Dream d, ServerPlayer v) {
        var rnd = d.sl.random;
        boolean ceiling = d.sl.dimensionType().hasCeiling();
        for (int k = 0; k < 40; k++) {
            double a = rnd.nextDouble() * Math.PI * 2, dist = Math.sqrt(rnd.nextDouble()) * Math.max(4, d.r - 2);
            double x = d.center.x + Math.cos(a) * dist, z = d.center.z + Math.sin(a) * dist;
            double dx = x - d.caster.getX(), dz = z - d.caster.getZ();
            if (dx * dx + dz * dz < MIN_FROM_CASTER * MIN_FROM_CASTER) continue;
            BlockPos col = BlockPos.containing(x, d.center.y, z);
            if (!d.sl.isLoaded(col)) continue;
            Vec3 p;
            if (ceiling) p = ground(d.sl, x, z, d.center.y + 16, 48);
            else {
                int top = d.sl.getHeight(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES, col.getX(), col.getZ());
                if (Math.abs(top - d.center.y) > 40) continue;
                p = ground(d.sl, x, z, top, 2);
            }
            if (p != null) return p;
        }
        Vec3 p = near(d.sl, v.position(), 4, 10);
        return p != null ? p : v.position();
    }

    private static void fakeHp(ServerPlayer v, double lost) {
        Net.CH.send(PacketDistributor.PLAYER.with(() -> v), new IlluMsg(IlluMsg.FAKE_HP, v.getId(), 0, 0, null, "", lost, 0, 0, 0, 0));
    }

    /** The wound butterflies of v (to v and the caster). */
    private static void wounds(Dream d, ServerPlayer v, int n) {
        if (n <= 0 && d.wounds.getOrDefault(v.getUUID(), 0) <= 0) return;
        d.wounds.put(v.getUUID(), n);
        IlluMsg m = new IlluMsg(IlluMsg.WOUNDS, v.getId(), 0, n, null, "", 0, 0, 0, 0, 0);
        Net.CH.send(PacketDistributor.PLAYER.with(() -> v), m);
        if (d.caster instanceof ServerPlayer cp && cp != v) Net.CH.send(PacketDistributor.PLAYER.with(() -> cp), m);
    }

    /** A dream hit on v: the wound flash (to v and the caster) and one more butterfly. */
    private static void wound(Dream d, ServerPlayer v) {
        fx(d.sl, Fx.fx("illusion_dream_wound").at(v.position()).caster(v).attach(v).only(v), "illusion_dream_wound");
        if (d.caster instanceof ServerPlayer cp && cp != v)
            fx(d.sl, Fx.fx("illusion_dream_wound").at(v.position()).caster(v).attach(v).only(cp), "illusion_dream_wound");
        wounds(d, v, Math.min(12, d.wounds.getOrDefault(v.getUUID(), 0) + 1));
    }

    /** The ripple the others see where a dreamer vanishes and comes back. */
    private static void ripple(ServerLevel sl, Vec3 at) {
        if (fx(sl, Fx.fx("illusion_dream_ripple").at(at), "illusion_dream_ripple") < 0) fx(sl, Fx.fx("illusion_poof").at(at), "illusion_poof");
        sl.playSound(null, at.x, at.y + 1, at.z, SoundEvents.AMETHYST_BLOCK_CHIME, SoundSource.PLAYERS, 1.2f, 0.6f);
    }

    /**
     * v «died» in the dream: nothing real happens (no items or XP lost, the real health as it was). The dark screen, under it v is moved to
     * another place of the dream with its illusory health full again; its copies come back around it.
     */
    private static void dreamDeath(Dream d, ServerPlayer v) {
        UUID id = v.getUUID();
        long now = Illusions.now();
        d.grace.put(id, now + DEATH_GRACE);
        d.lost.put(id, 0.0);
        wounds(d, v, 0);
        // it falls apart into butterflies where it stood (no follow), seen by it only; moved on DEATH_MOVE when that is over
        fx(d.sl, Fx.fx("illusion_dream_death").at(v.position()).caster(v).only(v), "illusion_dream_death");
        Net.CH.send(PacketDistributor.PLAYER.with(() -> v), new IlluMsg(IlluMsg.DREAM_DEATH, v.getId(), DEATH_SCREEN, 0, null, "", 0, 0, 0, 0, 0));
        v.playNotifySound(SoundEvents.AMETHYST_BLOCK_BREAK, SoundSource.PLAYERS, 1f, 0.5f);
        Integer cf = d.cocoon.remove(id);   // the cocoon goes while it is moved, and comes back at the new place
        if (cf != null) Fx.stop(d.sl, cf, "");
        Vec3 to = respawnSpot(d, v);
        int[] t = {0};
        ru.pohsmp.core.spell.Tasks.add(() -> {
            if (++t[0] < DEATH_MOVE) return true;
            if (!d.victims.containsKey(id) || !v.isAlive() || v.hasDisconnected() || v.level() != d.sl) return false;
            Vec3 old = v.position();
            v.connection.teleport(to.x, to.y, to.z, v.getYRot(), v.getXRot());
            v.setDeltaMovement(Vec3.ZERO);
            v.fallDistance = 0;
            Cutscene.refreeze(v, to);
            ripple(d.sl, old);
            ripple(d.sl, to);
            fx(d.sl, Fx.fx("illusion_dream_respawn").at(to).caster(v).attach(v).only(v), "illusion_dream_respawn");
            fakeHp(v, 0);
            d.lastStep.put(id, to);
            Long end = d.victims.get(id);
            if (end != null) cocoon(d, v, (int) Math.max(1, end - Illusions.now()));
            return false;
        });
    }

    /** The dream is over for v (waking, Blessing, death, gone): its world, copies and hidden ones go. fade: its music fades in 2 s. */
    private static void release(Dream d, UUID id, boolean fade) {
        Integer f = d.worldFx.remove(id);
        if (f != null) Fx.stop(d.sl, f, "");
        d.lost.remove(id);
        d.grace.remove(id);
        d.nextWhisper.remove(id);
        d.lastStep.remove(id);
        Integer cf = d.cocoon.remove(id);
        if (cf != null) Fx.stop(d.sl, cf, "");
        ServerPlayer w = player(d, id);
        if (w != null) wounds(d, w, 0);
        d.wounds.remove(id);
        ServerPlayer v = player(d, id);
        if (v == null) return;
        Net.CH.send(PacketDistributor.PLAYER.with(() -> v), new IlluMsg(IlluMsg.ZONE_END, d.caster.getId(), 0, IlluMsg.Z_DREAM, null, "", 0, 0, 0, 0, 0));
        fakeHp(v, 0);
        for (LivingEntity h : d.hidden) Net.CH.send(PacketDistributor.PLAYER.with(() -> v), new HideMsg(h.getId(), 0));
        v.removeEffect(Reg.BUTTERFLY_DREAM.get());
        if (fade) music(d.sl, id, 1, 40);
    }

    /** Out of the dream without the waking scene (it resisted longer, Blessing): back through the mirror. */
    private static void exitFx(Dream d, ServerPlayer v) {
        fx(d.sl, Fx.fx("illusion_dream_exit").at(v.position()).caster(v).attach(v).only(v), "illusion_dream_exit");
    }

    /** The waking scene starts (WAKE_SCENE before the break): on every dreamer still in (they all wake at the break now) and the caster. */
    private static void wakeScene(Dream d, long now) {
        fx(d.sl, Fx.fx("illusion_butterfly_wake").at(d.caster.position()).caster(d.caster), "illusion_butterfly_wake");
        fx(d.sl, Fx.fx("illusion_dream_wake").at(d.caster.position()).caster(d.caster).attach(d.caster), "illusion_dream_wake");
        for (var en : d.victims.entrySet()) {
            ServerPlayer v = player(d, en.getKey());
            if (v == null) continue;
            en.setValue(Math.max(en.getValue(), d.wakeAll));
            fx(d.sl, Fx.fx("illusion_dream_wake").at(v.position()).caster(v).attach(v), "illusion_dream_wake");
            Net.CH.send(PacketDistributor.PLAYER.with(() -> v), IlluMsg.of(IlluMsg.DREAM_WAKE, v.getId(), WAKE_SCENE));
        }
    }

    /** The waking (owner 19.11: «это был просто сон»): only the look of it - the shards fly into v and break; nothing is dealt. */
    private static void wakeFx(Dream d, ServerPlayer v) {
        fx(d.sl, Fx.fx("illusion_butterfly_wake_hit").at(v.position()).caster(d.caster).target(v).attach(v), "illusion_butterfly_wake_hit");
        d.sl.playSound(null, v.getX(), v.getY() + 1, v.getZ(), SoundEvents.AMETHYST_BLOCK_CHIME, SoundSource.PLAYERS, 1.2f, 1.3f);
        v.displayClientMessage(net.minecraft.network.chat.Component.translatable("ui.pohsmp_core.butterfly_dream.wake")
                .withStyle(s -> s.withColor(Reg.ILLUSION_COLOR)), true);
    }

    /** Every tick for a dreamer: a «death» when the lost health reaches the real one (real hits from outside count too); whispers, flowers, cocoon. */
    private static void tend(Dream d, ServerPlayer v, long now) {
        UUID id = v.getUUID();
        if (now >= d.grace.getOrDefault(id, 0L) && d.lost.getOrDefault(id, 0.0) >= v.getHealth()) {
            dreamDeath(d, v);
            return;
        }
        if (now >= d.nextWhisper.getOrDefault(id, Long.MAX_VALUE)) {
            whisper(d, v);
            d.nextWhisper.put(id, now + WHISPER_MIN + d.sl.random.nextInt(WHISPER_MAX - WHISPER_MIN));
        }
        Vec3 last = d.lastStep.get(id);
        if (v.onGround() && !v.isInWater() && (last == null || last.distanceToSqr(v.position()) >= STEP * STEP)) {
            d.lastStep.put(id, v.position());
            bloom(d, v);
        }
    }

    /** Hits by the caster, its allies or its copies (the illusion damage type has the caster as its source) are dream hits. */
    private static boolean fromDream(Dream d, DamageSource s) {
        Entity a = s.getEntity();
        return a != null && Illusions.ally(d.caster, a);
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
                    if (t instanceof ServerPlayer v) exitFx(d, v);
                    release(d, t.getUUID(), true);   // Blessing: awake early, the music fades for it
                    any = true;
                }
            return any;
        });
    }

    public static final class Events {
        private Events() {}

        /* driven by Illusions.onTick (TickHub) */
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
                if (now == d.wakeAll - WAKE_SCENE) wakeScene(d, now);
                if (now == d.wakeAll) {   // the dawn over the zone (19.11: a resonance and a quiet bell instead of breaking glass)
                    d.sl.playSound(null, d.caster.getX(), d.caster.getY() + 1, d.caster.getZ(), SoundEvents.AMETHYST_BLOCK_RESONATE, SoundSource.PLAYERS, 6f, 0.8f);
                    d.sl.playSound(null, d.caster.getX(), d.caster.getY() + 1, d.caster.getZ(), SoundEvents.BELL_RESONATE, SoundSource.PLAYERS, 1.5f, 1.2f);
                }
                for (var vi = d.victims.entrySet().iterator(); vi.hasNext(); ) {
                    var en = vi.next();
                    ServerPlayer v = player(d, en.getKey());
                    long end = en.getValue();
                    if (now >= end || v == null || !v.isAlive() || v.level() != d.sl) {
                        vi.remove();
                        boolean woke = v != null && v.isAlive() && now >= end;
                        release(d, en.getKey(), !woke || end < d.wakeAll - WAKE_ANIM_LEAD);   // woke with everyone: the track plays on to its end
                        if (woke && v.level() == d.sl) {
                            if (end < d.wakeAll) exitFx(d, v);   // resisted: out before the others, no scene
                            else wakeFx(d, v);
                        }
                        continue;
                    }
                    tend(d, v, now);
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
         * Owner 19.11: all damage in the dream is not real. A hit on a dreamer by the caster, its allies or its copies does not go through
         * (the flinch and knockback stay, armour is not worn); after armour it is written down as lost dream health and shown on the
         * dreamer's hearts. Hits from outside the dream (mobs, lava, falls, other players) stay real.
         */
        @SubscribeEvent(priority = EventPriority.LOWEST)
        public static void onHurt(LivingHurtEvent e) {
            if (DREAMS.isEmpty() || e.isCanceled() || !(e.getEntity() instanceof ServerPlayer v)) return;
            UUID id = v.getUUID();
            for (Dream d : DREAMS) {
                if (!d.victims.containsKey(id) || !fromDream(d, e.getSource())) continue;
                float amount = e.getAmount();
                e.setCanceled(true);
                if (amount <= 0 || Illusions.now() < d.grace.getOrDefault(id, 0L)) return;
                float dealt = e.getSource().is(DamageTypeTags.BYPASSES_ARMOR) ? amount
                        : CombatRules.getDamageAfterAbsorb(amount, v.getArmorValue(), (float) v.getAttributeValue(Attributes.ARMOR_TOUGHNESS));
                double sum = d.lost.merge(id, (double) dealt, Double::sum);
                fakeHp(v, sum);
                wound(d, v);
                if (sum >= v.getHealth()) dreamDeath(d, v);
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
