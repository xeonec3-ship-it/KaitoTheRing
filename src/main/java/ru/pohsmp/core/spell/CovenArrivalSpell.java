package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.magic.SpellSelectionManager;
import io.redspace.ironsspellbooks.api.registry.SchoolRegistry;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.spells.ISpellContainer;
import io.redspace.ironsspellbooks.api.spells.SpellData;
import io.redspace.ironsspellbooks.api.spells.SpellRarity;
import io.redspace.ironsspellbooks.api.util.AnimationHolder;
import com.mojang.logging.LogUtils;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import net.minecraft.core.registries.Registries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.level.TicketType;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.common.util.ITeleporter;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.event.entity.player.PlayerInteractEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.Hidden;
import ru.pohsmp.core.fx.Fx;
import ru.pohsmp.core.net.Net;
import ru.pohsmp.core.net.Net.HFx;
import org.slf4j.Logger;

/**
 * Mythic "Coven Arrival" (a Coven seal), level 1. First use marks the arena where the caster stands (no cast, the scroll stays);
 * using it within 8 blocks of the mark moves the mark. Shift+right click on a creature with the scroll (or the spell selected
 * in a spellbook) adds it to the retinue or removes it (up to 3). Using it farther away starts a 90 s cast that cannot be
 * interrupted, with a cutscene for everyone within 98 blocks of the arena and of the caster: a portal opens on the arena,
 * the retinue and the caster step out of it (from another dimension too), a line, a ritual, and at 83 s Closing of Space
 * (15 min) unfolds over the arena. CNPC NPCs of the retinue get script events coven_exit and coven_ritual.
 */
public class CovenArrivalSpell extends PohSpell {
    public static final String PATH = "coven_arrival";
    public static final String ID = "pohsmp_core:" + PATH;
    public static final int CAST = 1800, COLOR = 0xB49BFF, MAX_RETINUE = 3, DOME_MIN = 15;
    public static final double REMARK = 8;
    private static final String TAG = "pohsmp_core:coven_arena";
    /** Timeline, ticks from the start of the cast. The retinue steps out one by one in T_EXITS..T_CASTER (owner 19.11: up to 3). */
    private static final int T_PORTAL = 380, T_EXITS = 600, T_CASTER = 760, T_RITUAL = 1380, T_DOME = 1660, T_CLOSE = 1720;
    /** HFx.ANIM b: tells the cutscene clients how many of the retinue step out (dur = the count), for the camera of 30-38 s. */
    public static final int ANIM_RETINUE = 3;

    /** Pause between two exits; the last of the retinue steps out this long after the caster (4 s, as between three). */
    private static final int EXIT_GAP = 80;

    /**
     * Tick of the i-th retinue exit of n. Owner 19.11 («the caster walks through the last chosen one»): all but the last step out
     * in 30-38 s (the window shared equally), then the caster at 38 s, then the last one EXIT_GAP later, when the caster has
     * walked on past his spot (the slot behind the caster for three).
     */
    public static int exitTick(int i, int n) {
        if (i >= n - 1) return T_CASTER + EXIT_GAP;
        return T_EXITS + i * (T_CASTER - T_EXITS) / (n - 1);
    }

    /** Where the caster ends up in front of the portal. */
    private static Vec3 casterSpot(Arrival a) {
        return a.at.add(a.fw.scale(3.2));
    }

    /**
     * Where retinue i stands after its exit: №1 left (-2.6 to the side, 1.0 behind the caster), №2 right (+2.6, 1.0), №3 in the
     * middle 2.4 behind the caster — a diamond with the caster in front (docs/specs/coven_arrival_spec.md, end).
     */
    private static Vec3 slot(Arrival a, int i) {
        Vec3 c = casterSpot(a);
        return switch (i) {
            case 0 -> c.subtract(a.fw.scale(1.0)).subtract(a.rt.scale(2.6));
            case 1 -> c.subtract(a.fw.scale(1.0)).add(a.rt.scale(2.6));
            default -> c.subtract(a.fw.scale(2.4));
        };
    }
    /** The caster's own portal: opens in front of him (the arms open at 14 s), he and the retinue walk into it at 16.2-18.6 s. Retinue NPCs bow at the nod. */
    private static final int T_BOW = 188, T_BOW_END = 222, T_CPORTAL = 220, T_STEP = 324, STEP = 48, WALK = 32;
    /** How far in front of the caster his portal stands (the animation steps him 1.4 forward). */
    private static final double C_FRONT = 1.9;
    /** Height of the portal's centre over the ground (fx/meshes/coven_portal.json "center"): the cosmos disc stands on the ground. */
    public static final double PORTAL_Y = 1.86;
    /** Where the retinue stands at the start: to the sides of the caster, a little behind. */
    private static final double R_SIDE = 1.8, R_BACK = 0.5, R_BEHIND = 2.0;
    /** The retinue within this of its place beside the caster walks there; farther ones are moved at once. */
    private static final double APPROACH_MAX = 24;
    /** CNPC model animations: bow, arms forward. */
    private static final int NPC_BOW = 11, NPC_RITUAL = 3;

    public CovenArrivalSpell() {
        super(PATH, SchoolRegistry.ENDER_RESOURCE, SpellRarity.LEGENDARY, 1, 0, CAST, 0, 0);
    }

    @Override public CastType getCastType() { return CastType.LONG; }
    /**
     * The 90 s scene has a fixed timeline: cast time reduction (e.g. the Silent Witch robe) must not end the cast before it —
     * owner 19.11: the cast "completed" right as the dome began to form.
     */
    @Override public int getEffectiveCastTime(int spellLevel, @javax.annotation.Nullable LivingEntity entity) { return CAST; }
    @Override public boolean canBeInterrupted(Player player) { return false; }
    @Override public boolean allowCrafting() { return false; }
    @Override public Optional<SoundEvent> getCastStartSound() { return Optional.of(SoundEvents.BEACON_ACTIVATE); }
    @Override public Optional<SoundEvent> getCastFinishSound() { return Optional.of(SoundEvents.END_PORTAL_SPAWN); }
    private static final AnimationHolder ANIM_CAST = CastAnims.of("coven_arrival_cast"), ANIM_FINISH = CastAnims.of("coven_arrival_finish");
    @Override public AnimationHolder getCastStartAnimation() { return ANIM_CAST; }
    @Override public AnimationHolder getCastFinishAnimation() { return ANIM_FINISH; }

    @Override
    public void onClientPreCast(Level level, int spellLevel, LivingEntity entity, net.minecraft.world.InteractionHand hand, @javax.annotation.Nullable MagicData md) {
        super.onClientPreCast(level, spellLevel, entity, hand, md);
        CastAnims.hideHands(level, entity, getEffectiveCastTime(spellLevel, entity));
    }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("mark", (int) REMARK), ui("retinue", MAX_RETINUE), ui("cast", CAST / 20, (int) Cutscene.R_COVEN), ui("dome", DOME_MIN));
    }

    // ---------------------------------------------------------------- arena mark

    private record Mark(ResourceKey<Level> dim, Vec3 pos, float yaw) {}

    private static CompoundTag persisted(Player p) {
        CompoundTag root = p.getPersistentData();
        if (!root.contains(Player.PERSISTED_NBT_TAG)) root.put(Player.PERSISTED_NBT_TAG, new CompoundTag());
        return root.getCompound(Player.PERSISTED_NBT_TAG);
    }

    private static Mark mark(Player p) {
        CompoundTag t = persisted(p);
        if (!t.contains(TAG)) return null;
        CompoundTag m = t.getCompound(TAG);
        ResourceKey<Level> dim = ResourceKey.create(Registries.DIMENSION, new ResourceLocation(m.getString("dim")));
        return new Mark(dim, new Vec3(m.getDouble("x"), m.getDouble("y"), m.getDouble("z")), m.getFloat("yaw"));
    }

    private static void setMark(Player p, Mark k) {
        CompoundTag t = persisted(p);
        if (k == null) {
            t.remove(TAG);
            return;
        }
        CompoundTag m = new CompoundTag();
        m.putString("dim", k.dim().location().toString());
        m.putDouble("x", k.pos().x);
        m.putDouble("y", k.pos().y);
        m.putDouble("z", k.pos().z);
        m.putFloat("yaw", k.yaw());
        t.put(TAG, m);
    }

    private static void say(Player p, String key) {
        p.displayClientMessage(Component.translatable("ui.pohsmp_core.coven_arrival." + key).withStyle(s -> s.withColor(COLOR)), true);
    }

    /** Fx instance of the small seal over the mark, seen by its owner only. */
    private static final Map<UUID, Integer> MARK_FX = new HashMap<>();

    private static void showMark(ServerPlayer sp) {
        Integer old = MARK_FX.remove(sp.getUUID());
        if (old != null && sp.level() instanceof ServerLevel sl0) Fx.stop(sl0, old, "");
        Mark k = mark(sp);
        if (k == null) return;
        ServerLevel sl = sp.server.getLevel(k.dim());
        if (sl == null) return;
        int id = Fx.play(sl, Fx.sigil("coven_seal").at(k.pos().add(0, 2.2, 0)).yaw(k.yaw()).scale(0.09).orientation("billboard").duration(72000).only(sp));
        MARK_FX.put(sp.getUUID(), id);
    }

    @Override
    public boolean checkPreCastConditions(Level level, int spellLevel, LivingEntity entity, MagicData md) {
        if (!(level instanceof ServerLevel sl) || !(entity instanceof ServerPlayer sp)) return super.checkPreCastConditions(level, spellLevel, entity, md);
        if (CAST_BY.containsKey(sp.getUUID())) return false;
        Mark k = mark(sp);
        boolean near = k != null && k.dim() == sl.dimension() && k.pos().distanceTo(sp.position()) < REMARK;
        if (k == null || near || sp.server.getLevel(k.dim()) == null) {
            Mark nk = new Mark(sl.dimension(), sp.position(), sp.getYRot());
            setMark(sp, nk);
            say(sp, k == null ? "marked" : "moved");
            Fx.play(sl, Fx.sigil("coven_seal").at(nk.pos().add(0, 0.05, 0)).yaw(nk.yaw()).scale(0.35).orientation("ground").duration(30));
            sl.playSound(null, sp.getX(), sp.getY(), sp.getZ(), SoundEvents.AMETHYST_BLOCK_RESONATE, SoundSource.PLAYERS, 1.2f, 0.7f);
            showMark(sp);
            return false;
        }
        return super.checkPreCastConditions(level, spellLevel, entity, md);
    }

    // ---------------------------------------------------------------- retinue (Shift + right click)

    /** Caster -> chosen creatures (in order), and the marker over each (seen by the caster). */
    private static final Map<UUID, LinkedHashMap<UUID, Integer>> RETINUE = new HashMap<>();

    private boolean holdsThis(Player p) {
        for (ItemStack st : new ItemStack[] {p.getMainHandItem(), p.getOffhandItem()}) {
            if (st.isEmpty() || !(st.getItem() instanceof io.redspace.ironsspellbooks.item.Scroll) || !ISpellContainer.isSpellContainer(st)) continue;
            if (ISpellContainer.get(st).getSpellAtIndex(0).getSpell() == this) return true;
        }
        SpellData sel = new SpellSelectionManager(p).getSelectedSpellData();
        return sel != null && sel.getSpell() == this;
    }

    private static void dropRetinue(ServerPlayer caster) {
        LinkedHashMap<UUID, Integer> r = RETINUE.remove(caster.getUUID());
        if (r != null && caster.level() instanceof ServerLevel sl) for (int id : r.values()) Fx.stop(sl, id, "");
    }

    void toggle(ServerPlayer sp, LivingEntity t) {
        LinkedHashMap<UUID, Integer> r = RETINUE.computeIfAbsent(sp.getUUID(), u -> new LinkedHashMap<>());
        ServerLevel sl = sp.serverLevel();
        Integer had = r.remove(t.getUUID());
        if (had != null) {
            Fx.stop(sl, had, "");
            sp.displayClientMessage(Component.translatable("ui.pohsmp_core.coven_arrival.retinue_out", t.getDisplayName()).withStyle(s -> s.withColor(COLOR)), true);
            return;
        }
        if (r.size() >= MAX_RETINUE) {
            say(sp, "retinue_full");
            return;
        }
        int id = Fx.play(sl, Fx.sigil("coven_seal").at(t.position().add(0, t.getBbHeight() + 0.6, 0)).attach(t).scale(0.06)
                .orientation("billboard").duration(72000).only(sp));
        r.put(t.getUUID(), id);
        sp.displayClientMessage(Component.translatable("ui.pohsmp_core.coven_arrival.retinue_in", t.getDisplayName(), r.size(), MAX_RETINUE)
                .withStyle(s -> s.withColor(COLOR)), true);
        sl.playSound(null, t.getX(), t.getY(), t.getZ(), SoundEvents.AMETHYST_BLOCK_CHIME, SoundSource.PLAYERS, 1f, 1.2f);
    }

    private static LivingEntity find(net.minecraft.server.MinecraftServer srv, UUID u) {
        ServerPlayer p = srv.getPlayerList().getPlayer(u);
        if (p != null) return p;
        for (ServerLevel l : srv.getAllLevels()) if (l.getEntity(u) instanceof LivingEntity le) return le;
        return null;
    }

    // ---------------------------------------------------------------- the arrival

    private static final class Arrival {
        ServerLevel castLevel, arena;
        Vec3 at, fw, rt;
        float yaw;
        int cutKey, age;
        List<UUID> watchers = new ArrayList<>();
        final List<LivingEntity> retinue = new ArrayList<>();
        /** Who is hidden inside the portal (damage to them is cancelled), and where each one stands. */
        final Map<UUID, Vec3> hold = new HashMap<>();
        final List<Integer> fx = new ArrayList<>();
        int seed = -1, portal = -1, seal = -1, cPortal = -1, cSeal = -1;
        boolean domeOpened;
        /** Where the caster stood at the start (cast level) and his facing; the ground spot inside the arena portal. */
        Vec3 cAt, cFw, inside;
        float cYaw;
        /** Who walks now (out of the arena portal, or into the caster's): from, to, start tick, length. */
        final Map<UUID, Walk> walks = new HashMap<>();
        /** Retinue players told to walk the current walk by themselves (Cutscene.walk). */
        final java.util.Set<UUID> walkSent = new java.util.HashSet<>();
        /** The retinue beside the caster on the cast level until they enter his portal. */
        final Map<UUID, Vec3> pre = new HashMap<>();
        /** CNPC NPCs: the model animation they had before the arrival changed it. */
        final Map<UUID, Integer> poses = new HashMap<>();
        /** CNPC NPCs whose «return home» flag the scene turned off (it stays off; their home is moved to where they end up). */
        final Map<UUID, Boolean> homes = new HashMap<>();
        /** Retinue members whose exit came while they could not be found (chunk not loaded yet): retried every tick. */
        final Map<UUID, Vec3> pendingExit = new HashMap<>();
    }

    private static final Logger LOG = LogUtils.getLogger();
    /** Keeps the arena and the cast spot loaded through the whole arrival (renewed every second, lives 3 s). */
    private static final TicketType<ChunkPos> TICKET = TicketType.create("pohsmp_coven", Comparator.comparingLong(ChunkPos::toLong), 60);

    private static void keep(ServerLevel l, Vec3 p) {
        ChunkPos cp = new ChunkPos(BlockPos.containing(p));
        l.getChunkSource().addRegionTicket(TICKET, cp, 2, cp);
    }

    private static String where(LivingEntity e) {
        return e == null ? "null" : String.format("%s %s %.1f %.1f %.1f", e.getName().getString(), e.level().dimension().location(), e.getX(), e.getY(), e.getZ());
    }

    private record Walk(Vec3 from, Vec3 to, int start, int len) {}

    private static final Map<UUID, Arrival> CAST_BY = new HashMap<>();
    /** Entity -> caster: inside the portal (ru.pohsmp.core.Hidden: not drawn, no damage, no collisions). */
    private static final Map<UUID, UUID> HIDDEN = new HashMap<>();

    @Override
    public void onServerPreCast(Level level, int spellLevel, LivingEntity caster, MagicData md) {
        super.onServerPreCast(level, spellLevel, caster, md);
        if (level instanceof ServerLevel sl && !CAST_BY.containsKey(caster.getUUID())) begin(sl, caster);
    }

    private static void begin(ServerLevel sl, LivingEntity caster) {
        Arrival a = new Arrival();
        a.castLevel = sl;
        Mark k = caster instanceof Player p ? mark(p) : null;
        a.arena = k != null ? sl.getServer().getLevel(k.dim()) : null;
        if (a.arena == null) {
            a.arena = sl;
            a.at = caster.position();
            a.yaw = caster.getYRot();
        } else {
            a.at = k.pos();
            a.yaw = k.yaw();
        }
        // the portals stand on the ground even if the mark or the cast was made in a jump, on a ladder or in flight
        a.at = ground(a.arena, caster, a.at);
        double r = Math.toRadians(a.yaw);
        a.fw = new Vec3(-Math.sin(r), 0, Math.cos(r));
        a.rt = new Vec3(-a.fw.z, 0, a.fw.x);
        a.inside = a.at.subtract(a.fw.scale(0.3));
        a.cAt = ground(sl, caster, caster.position());
        a.cYaw = caster.getYRot();
        double cr = Math.toRadians(a.cYaw);
        a.cFw = new Vec3(-Math.sin(cr), 0, Math.cos(cr));
        LinkedHashMap<UUID, Integer> ret = RETINUE.get(caster.getUUID());
        if (ret != null) for (UUID u : ret.keySet()) {
            LivingEntity e = find(sl.getServer(), u);
            if (e != null && e.isAlive() && e != caster) a.retinue.add(e);
        }
        a.cutKey = HigherSpell.key();
        // owner 19.11 («a player in the retinue does not move»): the retinue players watch and are held wherever they stand,
        // the walks below move them through the cutscene freeze
        java.util.Set<UUID> retPlayers = new java.util.HashSet<>();
        for (LivingEntity e : a.retinue) if (e instanceof ServerPlayer) retPlayers.add(e.getUUID());
        a.watchers = Cutscene.start(sl, caster, a.cutKey, Cutscene.COVEN_ARRIVAL, CAST, a.at, a.yaw, Cutscene.R_COVEN, a.arena, a.at, retPlayers);
        HFx count = new HFx(HFx.ANIM, a.cutKey, caster.getId(), ANIM_RETINUE, a.retinue.size(), 0, 0, 0, 0, 0);
        for (UUID u : a.watchers) {
            ServerPlayer w = sl.getServer().getPlayerList().getPlayer(u);
            if (w != null) Net.CH.send(net.minecraftforge.network.PacketDistributor.PLAYER.with(() -> w), count);
        }
        // the retinue comes to the caster's sides (№3 right behind him), facing the way he faces, ready for the nod and the walk into his portal
        Vec3 cRt = new Vec3(-a.cFw.z, 0, a.cFw.x);
        for (int i = 0; i < a.retinue.size(); i++) {
            LivingEntity e = a.retinue.get(i);
            Vec3 spot = i == 2 ? a.cAt.subtract(a.cFw.scale(R_BEHIND))
                    : a.cAt.add(cRt.scale(i == 0 ? -R_SIDE : R_SIDE)).subtract(a.cFw.scale(R_BACK));
            // owner 19.11 («only teleported to the cast spot»): who stands near walks up to the caster, the far ones are brought
            double far = e.level() == sl ? e.position().distanceTo(spot) : Double.MAX_VALUE;
            if (far <= APPROACH_MAX) {
                if (far > 0.3) a.walks.put(e.getUUID(), new Walk(e.position(), spot, 0, (int) Math.max(20, Math.min(T_BOW - 20, far / 0.16))));
                a.pre.put(e.getUUID(), e.position());
                continue;
            }
            LivingEntity moved = move(e, sl, spot, a.cYaw);
            a.retinue.set(i, moved);
            a.pre.put(moved.getUUID(), spot);
        }
        a.fx.add(Fx.play(a.arena, Fx.fx("coven_tint").at(a.at).yaw(a.yaw)));
        a.seed = Fx.play(a.arena, Fx.mesh("coven_seed").at(a.at).yaw(a.yaw));
        a.arena.playSound(null, a.at.x, a.at.y, a.at.z, SoundEvents.BEACON_AMBIENT, SoundSource.PLAYERS, 6f, 0.5f);
        CAST_BY.put(caster.getUUID(), a);
        keep(a.arena, a.at);
        keep(sl, a.cAt);
        LOG.info("[pohsmp] coven arrival: caster {}, arena {} {}, retinue {}", where(caster), a.arena.dimension().location(), a.at,
                a.retinue.stream().map(CovenArrivalSpell::where).toList());
        // manager 19.11 («the NPC animations are gone again»): what each NPC of the retinue is at the start, for the server log
        for (LivingEntity e : a.retinue) if (!(e instanceof Player)) LOG.info("[pohsmp] coven arrival: retinue {} — {}", e.getUUID(), CnpcHooks.describe(e));
        Tasks.add(() -> step(caster, a));
    }

    /** One server tick of the arrival; false ends the task. */
    private static boolean step(LivingEntity caster, Arrival a) {
        if (CAST_BY.get(caster.getUUID()) != a) return false;
        int t = ++a.age;
        ServerLevel ar = a.arena;
        if (t % 20 == 0) {   // the arena (often far from the caster) must tick its entities before anyone arrives
            keep(ar, a.at);
            if (t < T_PORTAL + 20) keep(a.castLevel, a.cAt);
        }
        if (t % 200 == 0) LOG.info("[pohsmp] coven arrival t={}: {}", t, a.retinue.stream().map(e -> where(find(ar.getServer(), e.getUUID()))).toList());
        if (!a.pendingExit.isEmpty()) for (var e : new ArrayList<>(a.pendingExit.entrySet())) {
            LivingEntity le = find(ar.getServer(), e.getKey());
            if (le != null && exit(caster, a, le, e.getValue(), 0.6f)) a.pendingExit.remove(e.getKey());
        }
        if (t % 100 == 0 && t < T_PORTAL) ar.playSound(null, a.at.x, a.at.y + 3, a.at.z, SoundEvents.BEACON_AMBIENT, SoundSource.PLAYERS, 5f, 0.45f);
        if (t == 200) ar.playSound(null, a.at.x, a.at.y, a.at.z, SoundEvents.AMETHYST_BLOCK_RESONATE, SoundSource.PLAYERS, 4f, 0.5f);
        if (t == T_BOW || t == T_BOW_END) for (LivingEntity e : a.retinue) {
            if (e instanceof ServerPlayer sp && t == T_BOW && sp.isAlive())   // owner 19.11: the retinue players bow too
                Net.CH.send(net.minecraftforge.network.PacketDistributor.TRACKING_ENTITY_AND_SELF.with(() -> sp),
                        new ru.pohsmp.core.net.IlluMsg(ru.pohsmp.core.net.IlluMsg.ANIM, sp.getId(), 0, 0, null, "pohsmp_coven_bow", 0, 0, 0, 0, 0));
            if (e instanceof Player || !e.isAlive()) continue;
            if (t == T_BOW) {
                int old = CnpcHooks.anim(e, NPC_BOW);
                if (old >= 0) a.poses.putIfAbsent(e.getUUID(), old);
            } else if (a.poses.containsKey(e.getUUID())) CnpcHooks.anim(e, a.poses.get(e.getUUID()));
        }
        if (t == T_CPORTAL) openCasterPortal(a);
        if (t == T_PORTAL) openPortal(caster, a);
        for (int i = 0; i < a.retinue.size(); i++)
            if (t == exitTick(i, a.retinue.size())) exitOrWait(caster, a, a.retinue.get(i), slot(a, i));
        if (t == T_CASTER) exit(caster, a, caster, casterSpot(a), 0.45f);
        if (t == T_RITUAL) ritual(caster, a);
        if (t == T_DOME) {
            a.domeOpened = true;
            Cutscene.flash(ar, a.watchers, 20, 0xD8C8FF);
            SpaceClosureSpell.open(ar, caster, a.at, DOME_MIN);
        }
        if (t == T_CLOSE) {
            if (a.portal >= 0) Fx.stop(ar, a.portal, "");
            if (a.seal >= 0) Fx.stop(ar, a.seal, "");
            HigherSpell.burst(ar, a.at.x, a.at.y + PORTAL_Y, a.at.z, 4, COLOR);
            ar.playSound(null, a.at.x, a.at.y, a.at.z, SoundEvents.ENDER_EYE_DEATH, SoundSource.PLAYERS, 4f, 0.5f);
        }
        // before the portal: the retinue stands beside the caster, then walks with him into his portal
        if (t == T_STEP) {
            Vec3 shift = a.cFw.scale(C_FRONT + 0.2);
            for (var e : a.pre.entrySet()) a.walks.put(e.getKey(), new Walk(e.getValue(), e.getValue().add(shift), T_STEP, STEP));
        }
        if (t < T_PORTAL) holdAll(a, a.pre, a.castLevel, a.cYaw, t);
        // hold everyone hidden or already out in place: the retinue NPCs stand still, the hidden are not seen
        holdAll(a, a.hold, ar, a.yaw, t);
        return t < CAST + 40;
    }

    private static void holdAll(Arrival a, Map<UUID, Vec3> where, ServerLevel ar, float baseYaw, int t) {
        for (var e : where.entrySet()) {
            LivingEntity le = find(ar.getServer(), e.getKey());
            if (le == null || !le.isAlive() || le.level() != ar) continue;
            float yaw = baseYaw;
            Walk w = a.walks.get(le.getUUID());
            if (w != null && le instanceof ServerPlayer sp) {   // owner 19.11 «пусть ходит по-настоящему»: its own client walks it
                if (a.walkSent.add(sp.getUUID())) Cutscene.walk(sp, w.to(), Math.max(1, w.start() + w.len() - t), baseYaw);
                e.setValue(w.to());
                if (t >= w.start() + w.len()) {
                    a.walks.remove(sp.getUUID());
                    a.walkSent.remove(sp.getUUID());
                }
                Cutscene.refreeze(sp, w.to(), baseYaw);   // ignored while it walks; after it, holds it at the goal
                continue;
            }
            if (w != null) {   // walking: the server leads it in small steps, the client animates the legs
                double k = Math.min(1, (t - w.start()) / (double) w.len());
                double s = k * k * (3 - 2 * k);
                Vec3 d = w.to().subtract(w.from());
                e.setValue(w.from().add(d.scale(s)));
                if (k < 1 && d.horizontalDistanceSqr() > 1e-4) yaw = (float) Math.toDegrees(Math.atan2(-d.x, d.z));
                if (k >= 1) a.walks.remove(le.getUUID());
            }
            Vec3 p = e.getValue();
            if (le instanceof ServerPlayer sp) {   // players are held by the cutscene freeze
                Cutscene.refreeze(sp, p, yaw);   // walking: step and face the way; standing: face the line's way
                continue;
            }
            if (le.position().distanceToSqr(p) > 0.0004) le.teleportTo(p.x, p.y, p.z);
            // CNPC drops the model animation (bow) of an NPC away from its home: no «return home» while the scene holds it
            Boolean old = CnpcHooks.returnHome(le, false);
            if (old != null) a.homes.putIfAbsent(le.getUUID(), old);
            if (le instanceof net.minecraft.world.entity.Mob mob) mob.getNavigation().stop();   // a path also drops the pose
            le.fallDistance = 0;
            le.setDeltaMovement(Vec3.ZERO);
            le.setYRot(yaw);
            le.setYHeadRot(yaw);
            le.setYBodyRot(yaw);
        }
    }

    /** The caster's own portal in front of him, on the cast level: he opens it with his arms and walks into it. */
    private static void openCasterPortal(Arrival a) {
        ServerLevel cl = a.castLevel;
        Vec3 p = a.cAt.add(a.cFw.scale(C_FRONT));
        a.cPortal = Fx.play(cl, Fx.mesh("coven_portal").at(p).yaw(a.cYaw).duration(T_PORTAL + 8 - T_CPORTAL));
        a.cSeal = Fx.play(cl, Fx.sigil("coven_seal").at(p.add(0, 0.05, 0)).yaw(a.cYaw).scale(0.5).orientation("ground")
                .duration(T_PORTAL + 8 - T_CPORTAL));
        cl.playSound(null, p.x, p.y, p.z, SoundEvents.END_PORTAL_SPAWN, SoundSource.PLAYERS, 3f, 0.8f);
    }

    private static void openPortal(LivingEntity caster, Arrival a) {
        ServerLevel ar = a.arena;
        if (a.seed >= 0) Fx.stop(ar, a.seed, "");
        a.portal = Fx.play(ar, Fx.mesh("coven_portal").at(a.at).yaw(a.yaw).duration(T_CLOSE - T_PORTAL));
        a.seal = Fx.play(ar, Fx.sigil("coven_seal").at(a.at.add(0, 0.05, 0)).yaw(a.yaw).scale(0.8).orientation("ground").duration(T_CLOSE - T_PORTAL));
        a.fx.add(Fx.play(ar, Fx.fx("coven_wave").at(a.at).yaw(a.yaw)));
        ar.playSound(null, a.at.x, a.at.y, a.at.z, SoundEvents.END_PORTAL_SPAWN, SoundSource.PLAYERS, 6f, 0.6f);
        // the caster's own portal closes behind those who stepped into it
        ServerLevel cl = a.castLevel;
        Vec3 cp = a.cAt.add(a.cFw.scale(C_FRONT));
        if (a.cPortal >= 0) Fx.stop(cl, a.cPortal, "");
        if (a.cSeal >= 0) Fx.stop(cl, a.cSeal, "");
        HigherSpell.burst(cl, cp.x, cp.y + PORTAL_Y, cp.z, 2.5, COLOR);
        cl.playSound(null, cp.x, cp.y, cp.z, SoundEvents.ENDERMAN_TELEPORT, SoundSource.PLAYERS, 3f, 0.5f);
        // everyone steps into the portal: moved to the arena (other dimension too) right behind the portal, hidden from every viewer
        // (CNPC NPCs ignore invisibility when drawn, so Hidden cancels their rendering), unhurt and not pushed until their exit
        a.pre.clear();
        a.walks.clear();
        a.walkSent.clear();
        Vec3 p = a.inside;
        List<LivingEntity> all = new ArrayList<>(a.retinue);
        all.add(caster);
        for (LivingEntity e : all) {
            HIDDEN.put(e.getUUID(), caster.getUUID());
            Hidden.hide(e, CAST, true, true);   // gone on the cast level at once; the time limit is a safety net, exit/finish show them
            if (!(e instanceof Player)) HigherSpell.burst(e.level() instanceof ServerLevel el ? el : cl, e.getX(), e.getY() + 1, e.getZ(), 1.4, COLOR);
            LivingEntity moved = move(e, ar, p, a.yaw);
            Hidden.hide(moved, CAST, true, true);   // again: held at the new spot (and the new entity if it changed dimension)
            a.hold.put(moved.getUUID(), p);
            if (moved != caster) LOG.info("[pohsmp] coven arrival: {} into the portal -> {}", where(moved), p);
            if (moved != e) {
                a.retinue.replaceAll(x -> x == e ? moved : x);
                Integer pose = a.poses.remove(e.getUUID());
                if (pose != null) a.poses.put(moved.getUUID(), pose);
            }
        }
        // watchers left in another dimension (around the caster) have nothing to watch any more
        List<UUID> gone = new ArrayList<>();
        for (UUID u : a.watchers) {
            ServerPlayer sp = ar.getServer().getPlayerList().getPlayer(u);
            if (sp != null && sp.level() != ar) gone.add(u);
        }
        if (!gone.isEmpty()) {
            Cutscene.release(ar, gone, a.cutKey);
            a.watchers.removeAll(gone);
        }
    }

    /** Moves an entity to p in level `to`, facing yaw; returns the entity (a new one if a non-player changed dimension). */
    private static LivingEntity move(LivingEntity e, ServerLevel to, Vec3 p, float yaw) {
        e.fallDistance = 0;
        e.stopRiding();
        if (e instanceof ServerPlayer sp) {
            if (sp.level() == to) sp.connection.teleport(p.x, p.y, p.z, yaw, 0);
            else sp.teleportTo(to, p.x, p.y, p.z, yaw, 0);
            sp.setDeltaMovement(Vec3.ZERO);
            Cutscene.refreeze(sp, p);
            return sp;
        }
        keep(to, p);
        if (e.level() == to) {
            e.teleportTo(p.x, p.y, p.z);
            e.setYRot(yaw);
            return e;
        }
        Entity moved = e.changeDimension(to, new ITeleporter() {
            @Override
            public net.minecraft.world.level.portal.PortalInfo getPortalInfo(Entity entity, ServerLevel dest,
                    java.util.function.Function<ServerLevel, net.minecraft.world.level.portal.PortalInfo> def) {
                return new net.minecraft.world.level.portal.PortalInfo(p, Vec3.ZERO, yaw, 0);
            }

            @Override
            public boolean playTeleportSound(ServerPlayer player, ServerLevel src, ServerLevel dest) {
                return false;
            }
        });
        return moved instanceof LivingEntity le ? le : e;
    }

    private static void exitOrWait(LivingEntity caster, Arrival a, LivingEntity e, Vec3 to) {
        if (!exit(caster, a, e, to, 0.6f)) {
            LOG.warn("[pohsmp] coven arrival: {} not found at its exit, waiting for it", e.getUUID());
            a.pendingExit.put(e.getUUID(), to);
        }
    }

    /** False if the entity cannot be found right now (its chunk is not loaded): the caller retries. */
    private static boolean exit(LivingEntity caster, Arrival a, LivingEntity e, Vec3 to, float pitch) {
        ServerLevel ar = a.arena;
        LivingEntity le = find(ar.getServer(), e.getUUID());
        if (le == null) return false;
        if (!le.isAlive()) return true;
        keep(ar, to);
        HIDDEN.remove(le.getUUID());
        Hidden.show(le);
        unhideEverywhere(ar, le.getUUID());
        LivingEntity m;
        if (le == caster) {   // the caster's animation walks him out by itself: he is set at the end point at once
            m = move(le, ar, to, a.yaw);
            a.hold.put(m.getUUID(), to);
        } else {   // the retinue really walks out: from inside the portal to its place
            m = move(le, ar, a.inside, a.yaw);
            a.hold.put(m.getUUID(), a.inside);
            a.walks.put(m.getUUID(), new Walk(a.inside, to, a.age, WALK));
        }
        a.fx.add(Fx.play(ar, Fx.sigil("coven_seal").at(to.add(0, 0.04, 0)).yaw(a.yaw).scale(0.16).orientation("ground").duration(50)));
        HigherSpell.burst(ar, to.x, to.y + 1, to.z, 1.6, COLOR);
        ar.playSound(null, to.x, to.y, to.z, SoundEvents.ENDERMAN_TELEPORT, SoundSource.PLAYERS, 2f, pitch);
        ar.playSound(null, to.x, to.y, to.z, SoundEvents.AMETHYST_BLOCK_CHIME, SoundSource.PLAYERS, 2f, 0.8f);
        if (m != caster) {
            if (!(m instanceof Player) && !CnpcHooks.call(m, "coven_exit", caster.getName().getString()))
                LOG.info("[pohsmp] coven arrival: no coven_exit script call for {} ({})", m.getUUID(), CnpcHooks.describe(m));
            LOG.info("[pohsmp] coven arrival: {} steps out to {}", where(m), to);
        }
        return true;
    }

    /**
     * Owner 19.11 («на дальние расстояния НПС просто не появляются»): Hidden.show reaches only the players tracking the entity at that
     * moment; a client that got the hide near the cast spot and re-tracks it at the far arena later keeps it hidden. So the «shown» goes
     * to everyone in the arena's dimension, now and again at 1, 3 and 6 s.
     */
    private static void unhideEverywhere(ServerLevel ar, UUID id) {
        int[] t = {0};
        Tasks.add(() -> {
            if (t[0] == 0 || t[0] == 20 || t[0] == 60 || t[0] == 120) {
                Entity e = ar.getEntity(id);
                if (e != null && !Hidden.isHidden(e))
                    Net.CH.send(net.minecraftforge.network.PacketDistributor.DIMENSION.with(ar::dimension), new ru.pohsmp.core.net.HideMsg(e.getId(), 0));
            }
            return ++t[0] <= 120;
        });
    }

    private static void ritual(LivingEntity caster, Arrival a) {
        ServerLevel ar = a.arena;
        // fx/coven_ritual.json: a ring of lines a-b-c-d-a. Around the diamond: caster, №1 (left), №3 (behind), №2 (right);
        // missing ones repeat the last point, so two give the triangle and none a single point
        List<Vec3> ring = new ArrayList<>();
        ring.add(casterSpot(a));
        for (int i : new int[] {0, 2, 1}) if (i < a.retinue.size()) ring.add(slot(a, i));
        Vec3 sum = Vec3.ZERO;
        for (Vec3 p : ring) sum = sum.add(p);
        Vec3 sky = sum.scale(1.0 / ring.size()).add(0, 22, 0);
        while (ring.size() < 4) ring.add(ring.get(ring.size() - 1));
        a.fx.add(Fx.play(ar, Fx.fx("coven_ritual").at(a.at).yaw(a.yaw).point("a", ring.get(0)).point("b", ring.get(1))
                .point("c", ring.get(2)).point("d", ring.get(3)).point("sky", sky)));
        ar.playSound(null, a.at.x, a.at.y, a.at.z, SoundEvents.BEACON_POWER_SELECT, SoundSource.PLAYERS, 5f, 0.5f);
        for (LivingEntity e : a.retinue) {
            LivingEntity le = find(ar.getServer(), e.getUUID());
            if (le == null || !le.isAlive()) continue;
            if (le instanceof ServerPlayer) Net.sendNear(ar, le.getX(), le.getY(), le.getZ(), a.at.x, a.at.y, a.at.z,
                    new HFx(HFx.ANIM, 0, le.getId(), 0, 0, 0, 0, 0, 0, 0));
            else {
                int old = CnpcHooks.anim(le, NPC_RITUAL);   // arms forward; the NPC script may change it in coven_ritual
                if (old >= 0) a.poses.putIfAbsent(le.getUUID(), old);
                CnpcHooks.call(le, "coven_ritual", caster.getName().getString());
            }
        }
    }

    private static void finish(LivingEntity caster, Arrival a, boolean cancelled) {
        CAST_BY.remove(caster.getUUID());
        ServerLevel ar = a.arena;
        Cutscene.end(ar, caster, a.watchers, a.cutKey);
        for (UUID u : new ArrayList<>(a.hold.keySet())) {
            LivingEntity le = find(ar.getServer(), u);
            Walk w = a.walks.get(u);
            if (le != null && w != null && !(le instanceof Player) && le.level() == ar) le.teleportTo(w.to().x, w.to().y, w.to().z);
            if (le != null && !(le instanceof Player) && le.level() == ar) unhideEverywhere(ar, u);
            if (HIDDEN.remove(u) == null || le == null) continue;
            Hidden.show(le);   // cut short while still inside the portal: they appear where they waited, behind the portal
        }
        for (var p : a.poses.entrySet()) {
            LivingEntity le = find(ar.getServer(), p.getKey());
            if (le != null) CnpcHooks.anim(le, p.getValue());
        }
        // owner 19.11: no going back to where it stood before the teleport — the «return home» flag stays off and the home is
        // where the NPC ends the scene
        for (UUID u : a.homes.keySet()) {
            LivingEntity le = find(ar.getServer(), u);
            if (le != null) CnpcHooks.setHome(le, le.blockPosition());
        }
        HIDDEN.values().removeIf(c -> c.equals(caster.getUUID()));
        if (cancelled) {
            for (int id : a.fx) Fx.stop(ar, id, "");
            for (int id : new int[] {a.seed, a.portal, a.seal}) if (id >= 0) Fx.stop(ar, id, "");
            if (a.cPortal >= 0) Fx.stop(a.castLevel, a.cPortal, "");
            if (a.cSeal >= 0) Fx.stop(a.castLevel, a.cSeal, "");
        }
        if (caster instanceof ServerPlayer sp) {
            dropRetinue(sp);
            if (!cancelled || a.domeOpened) {
                setMark(sp, null);
                showMark(sp);
            }
        }
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        Arrival a = CAST_BY.get(caster.getUUID());
        if (a != null) {
            if (!a.domeOpened) {   // the cast ended early on the clock: still raise the dome
                a.domeOpened = true;
                SpaceClosureSpell.open(a.arena, caster, a.at, DOME_MIN);
            }
            finish(caster, a, false);
        }
        super.onCast(level, spellLevel, caster, source, md);
    }

    @Override
    public void onServerCastComplete(Level level, int spellLevel, LivingEntity caster, MagicData md, boolean cancelled) {
        Arrival a = CAST_BY.get(caster.getUUID());
        if (a != null) finish(caster, a, cancelled);
        super.onServerCastComplete(level, spellLevel, caster, md, cancelled);
    }

    // ---------------------------------------------------------------- events

    public static final class CovenArrivalEvents {
        private CovenArrivalEvents() {}

        @SubscribeEvent
        public static void onInteract(PlayerInteractEvent.EntityInteract e) {
            Player p = e.getEntity();
            if (!p.isShiftKeyDown() || !(e.getTarget() instanceof LivingEntity t)) return;
            if (!(ru.pohsmp.core.Reg.COVEN_ARRIVAL.get() instanceof CovenArrivalSpell spell) || !spell.holdsThis(p)) return;
            e.setCanceled(true);
            e.setCancellationResult(InteractionResult.SUCCESS);
            if (p instanceof ServerPlayer sp && e.getHand() == net.minecraft.world.InteractionHand.MAIN_HAND) spell.toggle(sp, t);
        }

        /**
         * Manager 19.11: Shift + right click into the air (no block, no creature in reach) with this spell clears the arena choice —
         * the mark and the chosen retinue. A plain right click works as before. Cancelled on both sides, so the scroll is not used.
         */
        @SubscribeEvent
        public static void onUseItem(PlayerInteractEvent.RightClickItem e) {
            Player p = e.getEntity();
            if (!p.isShiftKeyDown() || e.getHand() != net.minecraft.world.InteractionHand.MAIN_HAND) return;
            if (!(ru.pohsmp.core.Reg.COVEN_ARRIVAL.get() instanceof CovenArrivalSpell spell) || !spell.holdsThis(p)) return;
            double reach = p.getBlockReach();
            Vec3 eye = p.getEyePosition(), end = eye.add(p.getViewVector(1).scale(reach));
            if (p.pick(reach, 1, false).getType() != net.minecraft.world.phys.HitResult.Type.MISS) return;
            if (net.minecraft.world.entity.projectile.ProjectileUtil.getEntityHitResult(p, eye, end,
                    p.getBoundingBox().expandTowards(end.subtract(eye)).inflate(1), x -> !x.isSpectator() && x.isPickable(), reach * reach) != null) return;
            e.setCanceled(true);
            e.setCancellationResult(InteractionResult.SUCCESS);
            if (!(p instanceof ServerPlayer sp) || CAST_BY.containsKey(sp.getUUID())) return;
            setMark(sp, null);
            showMark(sp);   // no mark: only stops the seal over the old one
            dropRetinue(sp);
            say(sp, "cleared");
            sp.playNotifySound(SoundEvents.UI_BUTTON_CLICK.value(), SoundSource.PLAYERS, 0.35f, 1.3f);
        }

        @SubscribeEvent
        public static void onPlayerTick(TickEvent.PlayerTickEvent e) {
            if (e.phase != TickEvent.Phase.END || !(e.player instanceof ServerPlayer sp) || sp.tickCount % 200 != 37) return;
            Integer id = MARK_FX.get(sp.getUUID());
            if ((id == null || !Fx.running(id)) && mark(sp) != null) showMark(sp);
        }

        @SubscribeEvent
        public static void onLogin(PlayerEvent.PlayerLoggedInEvent e) {
            if (e.getEntity() instanceof ServerPlayer sp && mark(sp) != null) showMark(sp);
        }

        @SubscribeEvent
        public static void onLogout(PlayerEvent.PlayerLoggedOutEvent e) {
            if (!(e.getEntity() instanceof ServerPlayer sp)) return;
            dropRetinue(sp);
            Integer id = MARK_FX.remove(sp.getUUID());
            if (id != null) Fx.stop(sp.serverLevel(), id, "");
        }

        @SubscribeEvent
        public static void onStopping(ServerStoppingEvent e) {
            RETINUE.clear();
            MARK_FX.clear();
            CAST_BY.clear();
            HIDDEN.clear();
        }
    }
}
