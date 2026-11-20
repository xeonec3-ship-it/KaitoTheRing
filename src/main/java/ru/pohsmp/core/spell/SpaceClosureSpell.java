package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.events.SpellPreCastEvent;
import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.registry.SchoolRegistry;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.spells.SpellAnimations;
import io.redspace.ironsspellbooks.api.spells.SpellRarity;
import io.redspace.ironsspellbooks.api.util.AnimationHolder;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
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
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.entity.projectile.Projectile;
import net.minecraft.world.item.UseAnim;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.entity.EntityTeleportEvent;
import net.minecraftforge.event.entity.EntityTravelToDimensionEvent;
import net.minecraftforge.event.entity.living.LivingEntityUseItemEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.registries.ForgeRegistries;
import org.joml.Vector3f;
import ru.pohsmp.core.DivineEvents;
import ru.pohsmp.core.Tier;
import ru.pohsmp.core.fx.Fx;
import ru.pohsmp.core.net.Net;
import ru.pohsmp.core.net.Net.HFx;

/**
 * Mythic "Closing of Space" (a Coven seal), levels 1-4. 20 s cast that cannot be interrupted, with a cutscene for everyone within 64.
 * Then a sphere of radius 86 around the cast point: nothing crosses its shell either way (the caster too) — walkers and riders are put back,
 * projectiles (ender pearls too) vanish, teleports through it are cancelled, nobody inside leaves the dimension. Inside, only the caster
 * can cast Iron's spells, MNA is silenced and nobody else can drink potions. Lasts 5/10/20/30 min; casting it again ends the dome early.
 * Not kept across a server restart.
 */
public class SpaceClosureSpell extends PohSpell implements ru.pohsmp.core.spell.FixedCastSpell {
    public static final String PATH = "space_closure";
    public static final String ID = "pohsmp_core:" + PATH;
    public static final double R = 86;
    public static final int CAST = 400, COLOR = 0x8A6CFF, SPENT_TICKS = 200;
    private static final int[] MINUTES = {5, 10, 20, 30};
    private static final double EDGE = 1.2;
    private static final ResourceLocation MNA_SILENCE = new ResourceLocation("mna", "silence");
    private static final DustParticleOptions VIOLET = new DustParticleOptions(new Vector3f(0.6f, 0.45f, 1f), 1.6f);

    private static final class Zone {
        ResourceKey<Level> dim;
        Vec3 c;
        UUID caster;
        long until;
        int key;
        /** Which side of the shell each entity was on (true = inside). Kept for players who leave the level. */
        final Map<UUID, Boolean> side = new HashMap<>();
        final Map<UUID, Long> lastFx = new HashMap<>();
        /** Who was inside when the dome rose: never killed by the shell (BarrierGuard), only held in as before. */
        final java.util.Set<UUID> born = new java.util.HashSet<>();
    }

    private static final List<Zone> ZONES = new ArrayList<>();

    private static final class Casting {
        Vec3 at;
        int fx, cutKey;
        List<UUID> watchers = new ArrayList<>();
    }

    private static final Map<UUID, Casting> CASTING = new HashMap<>();

    public SpaceClosureSpell() {
        super(PATH, SchoolRegistry.ENDER_RESOURCE, SpellRarity.LEGENDARY, 4, 0, CAST, 0, 0);
    }

    @Override public CastType getCastType() { return CastType.LONG; }
    @Override public boolean canBeInterrupted(Player player) { return false; }
    @Override public boolean allowCrafting() { return false; }
    @Override public Optional<SoundEvent> getCastStartSound() { return Optional.of(SoundEvents.END_PORTAL_FRAME_FILL); }
    @Override public Optional<SoundEvent> getCastFinishSound() { return Optional.of(SoundEvents.END_PORTAL_SPAWN); }
    private static final AnimationHolder ANIM_CAST = CastAnims.of("space_closure_cast"), ANIM_FINISH = CastAnims.of("space_closure_finish");
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
        return List.of(ui("cast", CAST / 20), ui("zone", (int) R), ui("time", minutes(level)), ui("wall"), ui("magic"), ui("recast"), ui("spent", SPENT_TICKS / 20));
    }

    // ---- cast ----

    @Override
    public void onServerPreCast(Level level, int spellLevel, LivingEntity caster, MagicData md) {
        super.onServerPreCast(level, spellLevel, caster, md);
        if (level instanceof ServerLevel sl) begin(sl, caster);
    }

    private static void begin(ServerLevel sl, LivingEntity caster) {
        Casting c = new Casting();
        c.at = caster.position();
        c.cutKey = HigherSpell.key();
        Vec3 look = caster.getLookAngle();
        double ang = Math.atan2(look.z, look.x);
        c.watchers = Cutscene.start(sl, caster, c.cutKey, Cutscene.SPACE_CLOSURE, CAST, c.at.add(0, 40, 0), ang);
        c.fx = Fx.play(sl, Fx.fx("space_closure_cast").at(c.at).caster(caster));
        CASTING.put(caster.getUUID(), c);
    }

    @Override
    public void onServerCastTick(Level level, int spellLevel, LivingEntity caster, MagicData md) {
        super.onServerCastTick(level, spellLevel, caster, md);
        if (!(level instanceof ServerLevel sl)) return;
        if (!CASTING.containsKey(caster.getUUID())) begin(sl, caster);
        int t = caster.tickCount;
        if (t % 50 == 0) sl.playSound(null, caster.getX(), caster.getY(), caster.getZ(), SoundEvents.RESPAWN_ANCHOR_CHARGE, SoundSource.PLAYERS, 3f, 0.5f + (t % 200) / 400f);
        if (t % 80 == 0) sl.playSound(null, caster.getX(), caster.getY(), caster.getZ(), SoundEvents.BEACON_AMBIENT, SoundSource.PLAYERS, 4f, 0.5f);
        if (t % 2 == 0) for (int i = 0; i < 7; i++) {   // seven violet motes circling the caster
            double a = t * 0.08 + i * Math.PI * 2 / 7;
            DivineEvents.particle(sl, VIOLET, caster.getX() + Math.cos(a) * 2.2, caster.getY() + 0.2 + (t % 60) / 20.0, caster.getZ() + Math.sin(a) * 2.2, 1, 0, 0);
        }
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

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            Casting cs = CASTING.get(caster.getUUID());
            if (cs != null) Cutscene.flash(sl, cs.watchers, 24, 0xD8C8FF);
            open(sl, caster, cs != null ? cs.at : caster.position(), minutes(spellLevel));
        }
        super.onCast(level, spellLevel, caster, source, md);
    }

    // ---- the dome ----

    /**
     * Owner 19.11 («bring back the old look of the barrier — its wall»): the dome is again the client's HigherFx.closure — the lattice
     * sphere of glowing cells with the running band, the rune belts, seven Coven seals in the shell, the zenith seal, the ground circle
     * and the gyroscope (fx/space_closure_dome.json is no longer played). Sent again every 100 ticks for players who come closer later
     * (the same key only refreshes it).
     */
    private static void sendDome(ServerLevel sl, Zone z) {
        int left = (int) Math.max(1, z.until - sl.getGameTime());
        Net.sendNear(sl, z.c.x, z.c.y, z.c.z, z.c.x, z.c.y + R, z.c.z, new HFx(HFx.CLOSURE, z.key, -1, -1, left, z.c.x, z.c.y, z.c.z, R, COLOR));
    }

    public static void open(ServerLevel sl, LivingEntity caster, Vec3 at, int min) {
        Zone z = new Zone();
        z.dim = sl.dimension();
        z.c = at;
        z.caster = caster.getUUID();
        z.until = sl.getGameTime() + min * 1200L;
        for (Zone o : new ArrayList<>(ZONES)) if (o.caster.equals(z.caster)) close(sl, o);
        for (Entity e : sl.getEntities((Entity) null, box(z, 2), e -> true)) if (e.getVehicle() == null) z.side.put(e.getUUID(), e.position().distanceTo(z.c) < R);
        for (ServerPlayer p : sl.getServer().getPlayerList().getPlayers()) z.side.putIfAbsent(p.getUUID(), p.level() == sl && p.position().distanceTo(z.c) < R);
        for (var s : z.side.entrySet()) if (s.getValue()) z.born.add(s.getKey());
        z.key = HigherSpell.key();
        ZONES.add(z);
        sendDome(sl, z);
        sl.playSound(null, at.x, at.y, at.z, SoundEvents.END_PORTAL_SPAWN, SoundSource.PLAYERS, 8f, 0.6f);
        sl.playSound(null, at.x, at.y, at.z, SoundEvents.BEACON_POWER_SELECT, SoundSource.PLAYERS, 6f, 0.4f);
        sl.playSound(null, at.x, at.y, at.z, SoundEvents.WITHER_SPAWN, SoundSource.PLAYERS, 3f, 0.5f);
        DivineEvents.particle(sl, ParticleTypes.REVERSE_PORTAL, at.x, at.y + 1, at.z, 300, 1.5, 0.8);
        Tasks.add(new Tasks.Task() {
            int age;

            @Override
            public boolean tick() {
                age++;
                if (!ZONES.contains(z)) return false;
                if (sl.getGameTime() > z.until) {
                    close(sl, z);
                    return false;
                }
                if (age > 10) wall(sl, z);   // the shell closes after the dome has grown (client draws it in 40 ticks)
                if (age % 100 == 1) silence(sl, z);
                if (age % 100 == 50) sendDome(sl, z);
                return true;
            }
        });
    }

    private static void close(ServerLevel sl, Zone z) {
        ZONES.remove(z);
        Entity ce = sl.getServer().getPlayerList().getPlayer(z.caster);
        if (ce == null) ce = sl.getEntity(z.caster);
        if (ce instanceof LivingEntity le && le.isAlive()) {   // backlash: the seal drains the caster
            le.addEffect(new MobEffectInstance(ru.pohsmp.core.Reg.SPENT.get(), SPENT_TICKS, 0, false, true, true));
            if (le instanceof ServerPlayer sp) MagicData.getPlayerMagicData(sp).setMana(0);
        }
        Net.sendNear(sl, z.c.x, z.c.y, z.c.z, z.c.x, z.c.y + R, z.c.z, new HFx(HFx.STOP, z.key, -1, -1, 0, 0, 0, 0, 0, 0));
        Fx.play(sl, Fx.fx("space_closure_break").at(z.c));
        sl.playSound(null, z.c.x, z.c.y, z.c.z, SoundEvents.BEACON_DEACTIVATE, SoundSource.PLAYERS, 8f, 0.5f);
        sl.playSound(null, z.c.x, z.c.y, z.c.z, SoundEvents.GLASS_BREAK, SoundSource.PLAYERS, 8f, 0.4f);
    }

    private static AABB box(Zone z, double pad) {
        return new AABB(z.c.x - R - pad, z.c.y - R - pad, z.c.z - R - pad, z.c.x + R + pad, z.c.y + R + pad, z.c.z + R + pad);
    }

    /** Keeps every entity on its own side of the shell; mobs that cross it (or press into it from outside) die (BarrierGuard). */
    private static void wall(ServerLevel sl, Zone z) {
        LivingEntity caster = null;
        boolean looked = false;
        for (Entity e : sl.getEntities((Entity) null, box(z, 16), e -> e.getVehicle() == null && !e.isSpectator())) {
            double d = e.position().distanceTo(z.c);
            boolean in = d < R;
            Boolean was = z.side.get(e.getUUID());
            if (was == null) {
                z.side.put(e.getUUID(), in);
                continue;
            }
            // a mob outside whose body already reaches into the shell and moves in counts as crossing
            boolean pressing = !was && !in && e instanceof net.minecraft.world.entity.Mob && d - e.getBbWidth() / 2 < R
                    && e.getDeltaMovement().dot(z.c.subtract(e.position())) > 0;
            if (was == in && !pressing) continue;
            if (e instanceof Projectile) {   // arrows, spells, ender pearls: dissolve on the shell
                hit(sl, z, e.position(), e.getUUID());
                e.discard();
                continue;
            }
            if (e instanceof LivingEntity le && !z.born.contains(e.getUUID())) {
                if (!looked) {
                    looked = true;
                    Entity ce = sl.getServer().getPlayerList().getPlayer(z.caster);
                    if (ce == null) ce = sl.getEntity(z.caster);
                    caster = ce instanceof LivingEntity cl ? cl : null;
                }
                BarrierGuard.Verdict v = BarrierGuard.judge(caster, le);
                Vec3 dir = e.position().subtract(z.c);
                dir = dir.lengthSqr() < 1e-6 ? new Vec3(1, 0, 0) : dir.normalize();
                Vec3 at = z.c.add(dir.scale(R)).add(0, le.getBbHeight() / 2, 0);
                if (v == BarrierGuard.Verdict.KILL) {
                    hit(sl, z, z.c.add(dir.scale(R)), e.getUUID());
                    BarrierGuard.kill(sl, le, at, COLOR);
                    continue;
                }
                if (v == BarrierGuard.Verdict.BOSS) {
                    if (!pressing) putBack(sl, z, e, was);
                    BarrierGuard.repel(sl, le, was ? dir.scale(-1) : dir, at, COLOR);
                    continue;
                }
            }
            if (!pressing) putBack(sl, z, e, was);
        }
    }

    private static void putBack(ServerLevel sl, Zone z, Entity e, boolean inside) {
        Vec3 dir = e.position().subtract(z.c);
        dir = dir.lengthSqr() < 1e-6 ? new Vec3(1, 0, 0) : dir.normalize();
        Vec3 to = z.c.add(dir.scale(inside ? R - EDGE : R + EDGE));
        if (inside) to = new Vec3(to.x, Math.max(to.y, sl.getMinBuildHeight() + 1), to.z);
        hit(sl, z, z.c.add(dir.scale(R)), e.getUUID());
        if (!e.getPassengers().isEmpty()) e.ejectPassengers();
        Vec3 v = e.getDeltaMovement();
        double out = v.dot(dir);
        if (inside ? out > 0 : out < 0) v = v.subtract(dir.scale(out * 1.6));
        if (e instanceof ServerPlayer sp) {
            if (sp.isFallFlying()) sp.stopFallFlying();
            sp.connection.teleport(to.x, to.y, to.z, sp.getYRot(), sp.getXRot());
        } else e.teleportTo(to.x, to.y, to.z);
        e.setDeltaMovement(v);
        e.hurtMarked = true;
        e.fallDistance = 0;
    }

    private static void hit(ServerLevel sl, Zone z, Vec3 p, UUID who) {
        long now = sl.getGameTime();
        Long last = z.lastFx.get(who);
        if (last != null && now - last < 8) return;
        z.lastFx.put(who, now);
        Vec3 n = p.subtract(z.c).normalize();   // the old lattice ripple on the shell (HigherFx.closureHit), as the old wall
        int yaw = (int) Math.round(Math.atan2(n.z, n.x) * 1000), pitch = (int) Math.round(Math.asin(Math.max(-1, Math.min(1, n.y))) * 1000);
        Net.sendNear(sl, p.x, p.y, p.z, p.x, p.y, p.z, new HFx(HFx.CLOSURE_HIT, HigherSpell.key(), yaw, pitch, 24, p.x, p.y, p.z, 3.5, COLOR));
        sl.playSound(null, p.x, p.y, p.z, SoundEvents.AMETHYST_BLOCK_RESONATE, SoundSource.PLAYERS, 2f, 0.6f);
        sl.playSound(null, p.x, p.y, p.z, SoundEvents.RESPAWN_ANCHOR_SET_SPAWN, SoundSource.PLAYERS, 1.2f, 1.4f);
    }

    private static void silence(ServerLevel sl, Zone z) {
        MobEffect s = ForgeRegistries.MOB_EFFECTS.getValue(MNA_SILENCE);
        if (s == null || !ForgeRegistries.MOB_EFFECTS.containsKey(MNA_SILENCE)) return;
        for (ServerPlayer p : sl.players())
            if (!p.getUUID().equals(z.caster) && p.position().distanceToSqr(z.c) < R * R) p.addEffect(new MobEffectInstance(s, 120, 0, false, false, false));
    }

    /** Inside some dome of another caster: no Iron's casting, no drinking. */
    public static boolean blocked(Entity p) {
        if (ZONES.isEmpty()) return false;
        long now = p.level().getGameTime();
        for (Zone z : ZONES)
            if (z.dim == p.level().dimension() && now <= z.until && !p.getUUID().equals(z.caster) && p.position().distanceToSqr(z.c) < R * R) return true;
        return false;
    }

    /** Is the point inside some dome of this level? For BarrierGuard's teleport rule. */
    public static boolean anyInside(Level lvl, Vec3 p) {
        long now = lvl.getGameTime();
        for (Zone z : ZONES) if (z.dim == lvl.dimension() && now <= z.until && p.distanceToSqr(z.c) < R * R) return true;
        return false;
    }

    /** The live domes of this level as shells, for streams that stop at them (BarrierGuard.stream). */
    public static void shells(Level lvl, List<BarrierGuard.Shell> out) {
        long now = lvl.getGameTime();
        for (Zone z : ZONES) if (z.dim == lvl.dimension() && now <= z.until) out.add(new BarrierGuard.Shell(z, z.c, R, COLOR));
    }

    /** True when the segment from a to b crosses the shell of a dome in this level. */
    private static boolean crosses(Level lvl, Vec3 a, Vec3 b) {
        return crossing(lvl, a, b) != null;
    }

    private static Zone crossing(Level lvl, Vec3 a, Vec3 b) {
        for (Zone z : ZONES)
            if (z.dim == lvl.dimension() && (a.distanceToSqr(z.c) < R * R) != (b.distanceToSqr(z.c) < R * R)) return z;
        return null;
    }

    public static final class SpaceClosureEvents {
        private SpaceClosureEvents() {}

        @SubscribeEvent(priority = EventPriority.HIGH)
        public static void onPreCast(SpellPreCastEvent e) {
            Player p = e.getEntity();
            if (p.level().isClientSide || !(p.level() instanceof ServerLevel sl)) return;
            if (ID.equals(e.getSpellId())) {   // casting it again ends your dome instead
                for (Zone z : new ArrayList<>(ZONES))
                    if (z.caster.equals(p.getUUID())) {
                        ServerLevel zl = sl.getServer().getLevel(z.dim);
                        close(zl != null ? zl : sl, z);
                        e.setCanceled(true);
                    }
                if (e.isCanceled()) return;
            }
            if (blocked(p) && !aboveBarrier(p, e.getSpellId())) e.setCanceled(true);
        }

        /**
         * Owner 19.11: the barrier (this one and the Coven's) does not stop Higher, Mythic, Divine and Creation spells: the scroll's tier
         * (its pohsmp_tier tag or the spell's own), for a book cast the spell's own tier. Ordinary and Unknown (Silent) spells stay forbidden.
         */
        private static boolean aboveBarrier(Player p, String spellId) {
            Tier t = null;
            if (p instanceof net.minecraft.server.level.ServerPlayer sp)
                t = ru.pohsmp.core.DivineEvents.scrollTier(sp, io.redspace.ironsspellbooks.api.magic.MagicData.getPlayerMagicData(sp), spellId);
            if (t == null) t = Tier.builtin(spellId);
            return t == Tier.HIGHER || t == Tier.MYTHIC || t == Tier.DIVINE || t == Tier.CREATION;
        }

        /**
         * No damage crosses the shell: melee over the wall, rays, beams, spells aimed by position, explosions. The attacker is the
         * causing entity (or the direct one, or the source position); MNA's shared fake player is not a real position, so it is skipped.
         */
        @SubscribeEvent(priority = EventPriority.HIGH)
        public static void onAttack(net.minecraftforge.event.entity.living.LivingAttackEvent e) {
            LivingEntity v = e.getEntity();
            if (ZONES.isEmpty() || v.level().isClientSide || !(v.level() instanceof ServerLevel sl)) return;
            Entity src = e.getSource().getEntity();
            if (src == null || src instanceof net.minecraftforge.common.util.FakePlayer) src = e.getSource().getDirectEntity();
            if (src instanceof net.minecraftforge.common.util.FakePlayer) src = null;
            Vec3 from = src != null ? (src.level() == v.level() ? src.position() : null) : e.getSource().getSourcePosition();
            if (from == null) return;
            Zone z = crossing(v.level(), from, v.position());
            if (z == null) return;
            e.setCanceled(true);
            Vec3 d = v.position().subtract(z.c);
            hit(sl, z, z.c.add((d.lengthSqr() < 1e-6 ? new Vec3(1, 0, 0) : d.normalize()).scale(R)), v.getUUID());
        }

        @SubscribeEvent
        public static void onUseStart(LivingEntityUseItemEvent.Start e) {
            if (!e.getEntity().level().isClientSide && e.getItem().getUseAnimation() == UseAnim.DRINK && blocked(e.getEntity())) e.setCanceled(true);
        }

        @SubscribeEvent
        public static void onTeleport(EntityTeleportEvent e) {
            if (ZONES.isEmpty() || e.getEntity().level().isClientSide) return;
            if (!crosses(e.getEntity().level(), e.getPrev(), new Vec3(e.getTargetX(), e.getTargetY(), e.getTargetZ()))) return;
            if (e instanceof EntityTeleportEvent.TeleportCommand || e instanceof EntityTeleportEvent.SpreadPlayersCommand) {
                for (Zone z : ZONES) z.side.remove(e.getEntity().getUUID());   // admin commands pass: the side is read again on the next tick
                return;
            }
            e.setCanceled(true);
        }

        /** Death, respawn and login are not crossings: the side is taken from where the player is now. */
        private static void reread(Player p) {
            for (Zone z : ZONES) z.side.put(p.getUUID(), p.level().dimension() == z.dim && p.position().distanceToSqr(z.c) < R * R);
        }

        @SubscribeEvent
        public static void onRespawn(net.minecraftforge.event.entity.player.PlayerEvent.PlayerRespawnEvent e) {
            if (!e.getEntity().level().isClientSide) reread(e.getEntity());
        }

        @SubscribeEvent
        public static void onLogin(net.minecraftforge.event.entity.player.PlayerEvent.PlayerLoggedInEvent e) {
            if (!e.getEntity().level().isClientSide) reread(e.getEntity());
        }

        @SubscribeEvent
        public static void onTravel(EntityTravelToDimensionEvent e) {
            Entity en = e.getEntity();
            if (ZONES.isEmpty() || en.level().isClientSide) return;
            for (Zone z : ZONES)
                if (z.dim == en.level().dimension() && en.position().distanceToSqr(z.c) < R * R) {
                    e.setCanceled(true);
                    return;
                }
        }

        @SubscribeEvent
        public static void onStopping(ServerStoppingEvent e) {
            ZONES.clear();
            CASTING.clear();
        }
    }
}
