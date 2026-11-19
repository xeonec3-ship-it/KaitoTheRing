package ru.pohsmp.core.nightmare;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.util.AnimationHolder;
import io.redspace.ironsspellbooks.api.util.Utils;
import io.redspace.ironsspellbooks.capabilities.magic.TargetEntityCastData;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.network.PacketDistributor;
import ru.pohsmp.core.SchoolSeals;
import ru.pohsmp.core.ServerConfig;
import ru.pohsmp.core.fx.Fx;
import ru.pohsmp.core.fx.FxMath;
import ru.pohsmp.core.illusion.Illusions;
import ru.pohsmp.core.net.IlluMsg;
import ru.pohsmp.core.net.Net;
import ru.pohsmp.core.spell.CastAnims;

/**
 * T25 «Дом, которого нет» (Higher): a 2.5 s cast at the creature looked at. For [house_that_isnt] seconds a player target is in an
 * endless dark corridor with doors: its own client hides the real world (blocks, sky, everyone but the nightmares), the server lays the
 * corridor modules (mesh nightmare_corridor, only for it) round it and moves them as it walks - the corridor goes with it. It is held at
 * stage 2 of «Погружение» and stays there after; every few seconds a door opens and a shadow (nm_lurker) comes out of it. The caster
 * it sees as one more shadow (its client draws it so) - and the caster hits for real. A mob target just loses whom it fights.
 */
public class HouseThatIsntSpell extends NightmareSpells.Base {
    public static final String PATH = NightmareSpells.HOUSE;
    private static final int CAST = 50, MODULES = 7, MODULE_LEN = 4, SHADOW_EVERY = 110;

    public HouseThatIsntSpell() {
        super(PATH, Rank.HIGHER, CAST);
    }

    @Override public CastType getCastType() { return CastType.LONG; }
    @Override public AnimationHolder getCastStartAnimation() { return CastAnims.of("nightmare_house_cast"); }
    @Override public AnimationHolder getCastFinishAnimation() { return CastAnims.of("nightmare_house_finish"); }
    @Override public Optional<SoundEvent> getCastStartSound() { return Optional.of(NmSounds.HEARTBEAT); }
    @Override public Optional<SoundEvent> getCastFinishSound() { return Optional.empty(); }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("time", n(d(ServerConfig.HOUSE_SECONDS))));
    }

    @Override
    public boolean checkPreCastConditions(Level level, int spellLevel, LivingEntity entity, MagicData md) {
        return Utils.preCastTargetHelper(level, entity, md, this, (int) d(ServerConfig.HOUSE_RANGE), 0.35f);
    }

    private static final Map<UUID, int[]> CASTING = new HashMap<>();

    @Override
    public void onServerPreCast(Level level, int spellLevel, LivingEntity caster, MagicData md) {
        super.onServerPreCast(level, spellLevel, caster, md);
        if (!(level instanceof ServerLevel sl)) return;
        LivingEntity t = md != null && md.getAdditionalCastData() instanceof TargetEntityCastData td ? td.getTarget(sl) : null;
        Fx.Spec s = Fx.fx("nightmare_house_that_isnt_cast").at(caster.position()).caster(caster);
        if (t != null) s = s.target(t);
        int a = fx(sl, s, "nightmare_house_that_isnt_cast");
        int b = -1;
        if (!SchoolSeals.shown(caster)) b = fx(sl, Fx.fx("nightmare_house_that_isnt_seal").at(caster.position()).caster(caster), "nightmare_house_that_isnt_seal");
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

    private static final class House {
        final LivingEntity caster, target;
        final ServerLevel sl;
        final long until;
        /** the corridor's frame: origin, yaw; where its modules stand now (along, side, y) */
        final Vec3 origin;
        final float yaw;
        final Vec3 fwd, right;
        final int[] modules = new int[MODULES];
        int atmosphere = -1;
        int base = Integer.MIN_VALUE;
        double side, y;
        long nextShadow;
        Vec3 safe;

        House(LivingEntity caster, LivingEntity target, ServerLevel sl, long until) {
            this.caster = caster;
            this.target = target;
            this.sl = sl;
            this.until = until;
            this.origin = target.position();
            this.yaw = target.getYRot();
            FxMath.Vec f = FxMath.forward(yaw), r = FxMath.right(yaw);
            this.fwd = new Vec3(f.x(), 0, f.z());
            this.right = new Vec3(r.x(), 0, r.z());
            this.side = 0;
            this.y = target.getY();
            this.safe = target.position();
            java.util.Arrays.fill(modules, -1);
        }
    }

    private static final Map<UUID, House> HOUSES = new HashMap<>();

    /** The victim is in a corridor now (the bestiary leaves it to the corridor's own shadows). */
    public static boolean inside(ServerPlayer v) {
        return HOUSES.containsKey(v.getUUID());
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl && md != null && md.getAdditionalCastData() instanceof TargetEntityCastData td) {
            LivingEntity t = td.getTarget(sl);
            if (t != null && t.isAlive() && !Illusions.ally(caster, t)) start(sl, caster, t, ticks(ServerConfig.HOUSE_SECONDS));
        }
        super.onCast(level, spellLevel, caster, source, md);
    }

    private static void start(ServerLevel sl, LivingEntity caster, LivingEntity t, int ticks) {
        House old = HOUSES.remove(t.getUUID());
        if (old != null) end(old, false);
        House h = new House(caster, t, sl, Immersion.now() + ticks);
        h.nextShadow = Immersion.now() + 40;
        HOUSES.put(t.getUUID(), h);
        sl.playSound(null, t.getX(), t.getY() + 1, t.getZ(), SoundEvents.SOUL_ESCAPE, SoundSource.PLAYERS, 1f, 0.6f);
        if (!(t instanceof ServerPlayer p)) return;
        Immersion.hold(p, 2, ticks);   // straight to stage 2, and it stays there after
        fx(sl, Fx.fx("nightmare_house_that_isnt_enter").at(p.position()).caster(p).attach(p).only(p), "nightmare_house_that_isnt_enter");
        h.atmosphere = fx(sl, Fx.fx("nightmare_house_that_isnt_corridor").at(p.position()).caster(p).attach(p).duration(ticks).only(p),
                "nightmare_house_that_isnt_corridor");
        p.connection.send(new net.minecraft.network.protocol.game.ClientboundSoundPacket(net.minecraft.core.Holder.direct(SoundEvents.AMBIENT_CAVE.value()),
                SoundSource.AMBIENT, p.getX(), p.getY(), p.getZ(), 0.8f, 0.7f, p.getRandom().nextLong()));
        Net.CH.send(PacketDistributor.PLAYER.with(() -> p), new IlluMsg(IlluMsg.ZONE, caster.getId(), ticks, IlluMsg.Z_HOUSE, null, "",
                p.getX(), p.getY(), p.getZ(), 0, 0));
        lay(h, p);
    }

    private static void end(House h, boolean exitFx) {
        for (int i = 0; i < MODULES; i++) if (h.modules[i] >= 0) Fx.stop(h.sl, h.modules[i], "");
        if (h.atmosphere >= 0) Fx.stop(h.sl, h.atmosphere, "");
        if (h.target instanceof ServerPlayer p) {
            if (exitFx && p.isAlive()) fx(h.sl, Fx.fx("nightmare_house_that_isnt_exit").at(p.position()).caster(p).attach(p).only(p), "nightmare_house_that_isnt_exit");
            Net.CH.send(PacketDistributor.PLAYER.with(() -> p), new IlluMsg(IlluMsg.ZONE_END, h.caster.getId(), 0, IlluMsg.Z_HOUSE, null, "", 0, 0, 0, 0, 0));
        }
    }

    /**
     * Puts the corridor round the victim: along the corridor the modules stand still in the world and the back one goes to the front
     * every 4 blocks; sideways and up the whole corridor follows the victim when it strays (so it never reaches a wall).
     */
    private static void lay(House h, ServerPlayer p) {
        Vec3 rel = p.position().subtract(h.origin);
        double along = rel.dot(h.fwd), side = rel.dot(h.right);
        int base = (int) Math.floor(along / MODULE_LEN);
        boolean moved = base != h.base || Math.abs(side - h.side) > 0.9 || Math.abs(p.getY() - h.y) > 0.6;
        if (!moved) return;
        if (Math.abs(side - h.side) > 0.9) h.side = side;
        if (Math.abs(p.getY() - h.y) > 0.6) h.y = p.getY();
        h.base = base;
        for (int i = 0; i < MODULES; i++) {
            int k = base + i - MODULES / 2;
            Vec3 at = h.origin.add(h.fwd.scale(k * MODULE_LEN)).add(h.right.scale(h.side));
            at = new Vec3(at.x, h.y, at.z);
            if (h.modules[i] < 0) h.modules[i] = Fx.play(h.sl, Fx.mesh("nightmare_corridor").at(at).yaw(h.yaw).duration((int) (h.until - Immersion.now())).only(p));
            else Fx.move(h.sl, h.modules[i], at, h.yaw);
        }
    }

    /** A door of the corridor opens near the victim (ahead or behind, a random side) and a shadow comes out of it. */
    private static void shadow(House h, ServerPlayer p) {
        int k = h.base + (p.getRandom().nextBoolean() ? 1 : -1) * (1 + p.getRandom().nextInt(2));
        int s = p.getRandom().nextBoolean() ? 1 : -1;
        Vec3 door = h.origin.add(h.fwd.scale(k * MODULE_LEN + 2)).add(h.right.scale(h.side + s * 1.45));
        door = new Vec3(door.x, h.y, door.z);
        float inward = h.yaw + (s > 0 ? 90 : -90);
        fx(h.sl, Fx.fx("nightmare_house_that_isnt_shadow").at(door).yaw(inward).only(p), "nightmare_house_that_isnt_shadow");
        p.connection.send(new net.minecraft.network.protocol.game.ClientboundSoundPacket(net.minecraft.core.Holder.direct(SoundEvents.WOODEN_DOOR_OPEN),
                SoundSource.HOSTILE, door.x, door.y + 1, door.z, 1f, 0.5f, p.getRandom().nextLong()));
        Vec3 g = Bestiary.ground(h.sl, door.x - h.right.x * s * 0.6, door.y, door.z - h.right.z * s * 0.6);
        if (g == null) g = new Vec3(door.x - h.right.x * s * 0.6, h.y, door.z - h.right.z * s * 0.6);
        NightmareMob m = Bestiary.TYPES.get(NightmareMob.Kind.LURKER).get().create(h.sl);
        if (m == null) return;
        m.victim = p.getUUID();
        m.moveTo(g.x, g.y, g.z, inward, 0);
        h.sl.addFreshEntity(m);
    }

    static {
        Illusions.onDispel(t -> {
            House h = HOUSES.remove(t.getUUID());
            if (h == null) return false;
            end(h, true);
            return true;
        });
    }

    public static final class Events {
        private Events() {}

        /* driven by Illusions.onTick (TickHub) */
        public static void onTick(TickEvent.ServerTickEvent e) {
            if (e.phase != TickEvent.Phase.END || HOUSES.isEmpty()) return;
            long now = Immersion.now();
            double fall = d(ServerConfig.HOUSE_FALL);
            for (var it = HOUSES.values().iterator(); it.hasNext(); ) {
                House h = it.next();
                if (now >= h.until || !h.target.isAlive() || h.target.isRemoved()) {
                    end(h, true);
                    it.remove();
                    continue;
                }
                if (h.target instanceof ServerPlayer p) {
                    Immersion.touch(p);
                    lay(h, p);
                    if (p.onGround()) h.safe = p.position();
                    else if (p.fallDistance > fall) {   // blind in the corridor: no falling off a real cliff
                        p.teleportTo(h.safe.x, h.safe.y, h.safe.z);
                        p.fallDistance = 0;
                    }
                    if (now >= h.nextShadow) {
                        shadow(h, p);
                        h.nextShadow = now + SHADOW_EVERY + p.getRandom().nextInt(60);
                    }
                } else if (h.target instanceof Mob mob && now % 20 == 0) {
                    mob.setTarget(null);
                    mob.getNavigation().stop();
                }
            }
        }

        @SubscribeEvent
        public static void onStopping(ServerStoppingEvent e) {
            HOUSES.clear();
            CASTING.clear();
        }
    }
}
