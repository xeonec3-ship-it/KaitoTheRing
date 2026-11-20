package ru.pohsmp.core.spell.illusion;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.util.AnimationHolder;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.network.PacketDistributor;
import ru.pohsmp.core.SchoolSeals;
import ru.pohsmp.core.ServerConfig;
import ru.pohsmp.core.fx.Fx;
import ru.pohsmp.core.illusion.Illusions;
import ru.pohsmp.core.illusion.Maze;
import ru.pohsmp.core.net.IlluMsg;
import ru.pohsmp.core.net.Net;
import ru.pohsmp.core.spell.CastAnims;
import ru.pohsmp.core.spell.HigherSpell;

/**
 * T22 «Зеркальный лабиринт» (Higher): a 4 s cast, then a dome of [mirror_labyrinth] radius for its time where the caster stood.
 * Enemies inside (and who walk in) see mirror walls of a maze - opaque, but nothing stops them: walking into one is illusory damage
 * from the shards and a push back out (fx/illusion_labyrinth_wall_hit, only to them); left and right are swapped for them while inside.
 * The caster and its allies see no walls. The maze is built the same on the server and on the clients (illusion/Maze, one seed).
 */
public class MirrorLabyrinthSpell extends IllusionBase {
    public static final String PATH = "mirror_labyrinth";
    private static final int CAST = 80, STRIKE = 76;

    public MirrorLabyrinthSpell() {
        super(PATH, Rank.HIGHER, CAST);
    }

    @Override public CastType getCastType() { return CastType.LONG; }
    @Override public AnimationHolder getCastStartAnimation() { return CastAnims.of("illusion_labyrinth_cast"); }
    @Override public AnimationHolder getCastFinishAnimation() { return CastAnims.of("illusion_labyrinth_finish"); }
    @Override public Optional<SoundEvent> getCastStartSound() { return Optional.of(SoundEvents.AMETHYST_BLOCK_RESONATE); }
    @Override public Optional<SoundEvent> getCastFinishSound() { return Optional.empty(); }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("zone", n(d(ServerConfig.LAB_RADIUS)), n(d(ServerConfig.LAB_SECONDS))), ui("shards", n(d(ServerConfig.LAB_WALL_DAMAGE))));
    }

    /** caster -> its cast effects (the cast and, without a tier seal, the seal under the feet) */
    private static final Map<UUID, int[]> CASTING = new HashMap<>();

    @Override
    public void onServerPreCast(Level level, int spellLevel, LivingEntity caster, MagicData md) {
        super.onServerPreCast(level, spellLevel, caster, md);
        if (!(level instanceof ServerLevel sl)) return;
        int a = fx(sl, Fx.fx("illusion_labyrinth_cast").at(caster.position()).caster(caster), "illusion_labyrinth_cast");
        int b = -1;
        if (!SchoolSeals.shown(caster)) b = fx(sl, Fx.fx("illusion_labyrinth_seal").at(caster.position()).caster(caster), "illusion_labyrinth_seal");
        CASTING.put(caster.getUUID(), new int[] {a, b});
    }

    @Override
    public void onServerCastComplete(Level level, int spellLevel, LivingEntity caster, MagicData md, boolean cancelled) {
        int[] f = CASTING.remove(caster.getUUID());
        if (f != null && level instanceof ServerLevel sl) {
            if (cancelled && f[0] >= 0) Fx.stop(sl, f[0], "");
            if (f[1] >= 0) Fx.stop(sl, f[1], "");
        }
        super.onServerCastComplete(level, spellLevel, caster, md, cancelled);
    }

    private static final class Lab {
        final LivingEntity caster;
        final ServerLevel sl;
        final Maze maze;
        final long seed, until;
        final Set<UUID> inside = new HashSet<>();
        final Map<UUID, Long> lastHit = new HashMap<>();
        final float damage;
        int fx = -1, debug = 61;

        Lab(LivingEntity caster, ServerLevel sl, Maze maze, long seed, long until, float damage) {
            this.caster = caster;
            this.sl = sl;
            this.maze = maze;
            this.seed = seed;
            this.until = until;
            this.damage = damage;
        }
    }

    private static final List<Lab> LABS = new ArrayList<>();
    private static int TAG = 3_000_000;

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            double r = d(ServerConfig.LAB_RADIUS);
            int ticks = ticks(ServerConfig.LAB_SECONDS);
            Vec3 c = caster.position();
            long seed = sl.getRandom().nextLong();
            Lab lab = new Lab(caster, sl, new Maze(c.x, c.y, c.z, r, seed), seed, Illusions.now() + ticks, (float) power(caster, d(ServerConfig.LAB_WALL_DAMAGE)));
            lab.fx = fx(sl, Fx.fx("illusion_labyrinth").at(c).caster(caster).scale(r / 14.0).duration(ticks), "illusion_labyrinth");
            sl.playSound(null, c.x, c.y + 1, c.z, SoundEvents.GLASS_BREAK, SoundSource.PLAYERS, 2f, 0.7f);
            sl.playSound(null, c.x, c.y + 1, c.z, SoundEvents.AMETHYST_BLOCK_RESONATE, SoundSource.PLAYERS, 2f, 0.6f);
            LABS.add(lab);
            Illusions.logZone("mirror_labyrinth", sl, caster, c, r);
            ru.pohsmp.core.PohCore.LOG.info("[pohsmp] mirror_labyrinth: lab added, until={} now={} labs={}", lab.until, Illusions.now(), LABS.size());
        }
        super.onCast(level, spellLevel, caster, source, md);
    }

    /**
     * T30 «Эреб, Первый Предатель», special «Зеркальный лабиринт»: the same dome raised by a caster without an Iron's cast, with its own
     * centre, radius (the arena), time and wall damage (balance [ereb] labyrinth_*). The caster's allies see no walls, as always.
     */
    public static void raise(ServerLevel sl, LivingEntity caster, Vec3 c, double r, int ticks, float damage) {
        long seed = sl.getRandom().nextLong();
        Lab lab = new Lab(caster, sl, new Maze(c.x, c.y, c.z, r, seed), seed, Illusions.now() + ticks, damage);
        lab.fx = fx(sl, Fx.fx("illusion_labyrinth").at(c).caster(caster).scale(r / 14.0).duration(ticks), "illusion_labyrinth");
        sl.playSound(null, c.x, c.y + 1, c.z, SoundEvents.GLASS_BREAK, SoundSource.HOSTILE, 3f, 0.7f);
        sl.playSound(null, c.x, c.y + 1, c.z, SoundEvents.AMETHYST_BLOCK_RESONATE, SoundSource.HOSTILE, 3f, 0.6f);
        LABS.add(lab);
        Illusions.logZone("mirror_labyrinth (boss)", sl, caster, c, r);
    }

    private static void enter(Lab lab, ServerPlayer p) {
        if (!lab.inside.add(p.getUUID())) return;
        int left = (int) Math.max(1, Math.min(lab.until - Illusions.now(), Illusions.duration(p, (int) (lab.until - Illusions.now()))));
        // owner 19.11 («the labyrinth does not work on the player»): the client of Helm_Mertimer never got a zone; who gets it, for the log
        ru.pohsmp.core.PohCore.LOG.info("[pohsmp] mirror_labyrinth: zone -> {} for {} ticks", p.getGameProfile().getName(), left);
        Net.CH.send(PacketDistributor.PLAYER.with(() -> p), new IlluMsg(IlluMsg.ZONE, lab.caster.getId(), left, IlluMsg.Z_LABYRINTH, null,
                Long.toString(lab.seed), lab.maze.cx, lab.maze.cy, lab.maze.cz, (float) lab.maze.r, 0));
    }

    private static void leave(Lab lab, ServerPlayer p) {
        Net.CH.send(PacketDistributor.PLAYER.with(() -> p), new IlluMsg(IlluMsg.ZONE_END, lab.caster.getId(), 0, IlluMsg.Z_LABYRINTH, null, "", 0, 0, 0, 0, 0));
    }

    static {
        Illusions.onDispel(t -> {
            boolean any = false;
            for (Lab lab : LABS)
                if (t instanceof ServerPlayer p && lab.inside.contains(p.getUUID())) {
                    leave(lab, p);
                    lab.lastHit.put(p.getUUID(), Long.MAX_VALUE);   // blessed: walls gone for good in this labyrinth
                    any = true;
                }
            return any;
        });
    }

    public static final class Events {
        private Events() {}

        private static long alive;

        /* driven by Illusions.onTick (TickHub) */
        public static void onTick(TickEvent.ServerTickEvent e) {
            if (e.phase == TickEvent.Phase.END && alive++ == 0)
                ru.pohsmp.core.PohCore.LOG.info("[pohsmp] mirror_labyrinth ticker started: {} labs, now={}", LABS.size(), Illusions.now());
            if (e.phase != TickEvent.Phase.END || LABS.isEmpty()) return;
            try {
                tick();
            } catch (Throwable ex) {
                ru.pohsmp.core.PohCore.LOG.error("[pohsmp] mirror_labyrinth tick failed", ex);
            }
        }

        private static void tick() {
            long now = Illusions.now();
            int back = (int) Math.round(d(ServerConfig.LAB_WALL_RETURN) * 20);
            double push = d(ServerConfig.LAB_PUSH);
            for (var it = LABS.iterator(); it.hasNext(); ) {
                Lab lab = it.next();
                if (now >= lab.until) {
                    for (UUID id : lab.inside) {
                        ServerPlayer p = lab.sl.getServer().getPlayerList().getPlayer(id);
                        if (p != null) leave(lab, p);
                    }
                    it.remove();
                    continue;
                }
                double r = lab.maze.r;
                Vec3 c = new Vec3(lab.maze.cx, lab.maze.cy, lab.maze.cz);
                if (lab.debug-- > 0 && lab.debug % 20 == 0) {   // owner 19.11: the zone never reaches the victim - why, every second for 3 s
                    StringBuilder sb = new StringBuilder();
                    for (ServerPlayer p : lab.sl.players())
                        sb.append(p.getGameProfile().getName()).append(" d=").append(Math.round(Math.sqrt(p.position().distanceToSqr(c)) * 10) / 10.0)
                                .append(" ally=").append(Illusions.ally(lab.caster, p)).append(" in=").append(lab.inside.contains(p.getUUID()))
                                .append(" last=").append(lab.lastHit.get(p.getUUID())).append("; ");
                    ru.pohsmp.core.PohCore.LOG.info("[pohsmp] mirror_labyrinth tick now={} until={} level={} : {}", now, lab.until,
                            lab.sl.dimension().location(), sb);
                }
                for (ServerPlayer p : lab.sl.players()) {
                    if (p.isSpectator() || Illusions.ally(lab.caster, p) || p.position().distanceToSqr(c) > r * r) continue;
                    Long last = lab.lastHit.get(p.getUUID());
                    if (last != null && last == Long.MAX_VALUE) continue;   // blessed
                    enter(lab, p);
                    if (last != null && now - last < 15) continue;
                    double[] w = lab.maze.wallAt(p.getX(), p.getY(), p.getZ(), 0.3);
                    if (w == null) continue;
                    lab.lastHit.put(p.getUUID(), now);
                    Illusions.illusory(lab.caster, p, lab.damage, back, ++TAG);
                    // push back out across the wall's normal, away from the side the body is on
                    boolean alongX = Math.abs(w[0] - w[2]) > Math.abs(w[1] - w[3]);
                    Vec3 n = alongX ? new Vec3(0, 0, Math.signum(p.getZ() - w[1])) : new Vec3(Math.signum(p.getX() - w[0]), 0, 0);
                    if (n.lengthSqr() < 1e-6) n = p.getLookAngle().multiply(-1, 0, -1).normalize();
                    HigherSpell.push(p, n.scale(push).add(0, 0.15, 0));
                    Vec3 hit = alongX ? new Vec3(p.getX(), p.getY() + 1.2, w[1]) : new Vec3(w[0], p.getY() + 1.2, p.getZ());
                    fx(lab.sl, Fx.fx("illusion_labyrinth_wall_hit").at(hit).caster(p).point("hit", hit).only(p), "illusion_labyrinth_wall_hit");
                    p.connection.send(new net.minecraft.network.protocol.game.ClientboundSoundPacket(net.minecraft.core.Holder.direct(SoundEvents.GLASS_BREAK),
                            SoundSource.PLAYERS, hit.x, hit.y, hit.z, 0.9f, 1.4f + p.getRandom().nextFloat() * 0.4f, p.getRandom().nextLong()));
                }
                for (UUID id : new ArrayList<>(lab.inside)) {   // walked out: the walls go for it
                    ServerPlayer p = lab.sl.getServer().getPlayerList().getPlayer(id);
                    if (p == null || p.level() != lab.sl || p.position().distanceToSqr(c) > r * r) {
                        lab.inside.remove(id);
                        if (p != null) leave(lab, p);
                    }
                }
            }
        }

        @SubscribeEvent
        public static void onStopping(ServerStoppingEvent e) {
            LABS.clear();
            CASTING.clear();
        }
    }

    /** The cast strike (fx tick 76) falls at the end of the 80-tick cast: nothing else to time here. */
    @SuppressWarnings("unused")
    private static final int STRIKE_TICK = STRIKE;
}
