package ru.pohsmp.core.spell.silent;


import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.function.Supplier;
import net.minecraft.core.particles.DustParticleOptions;
import net.minecraft.core.particles.ParticleOptions;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.OwnableEntity;
import net.minecraft.world.entity.decoration.ArmorStand;
import net.minecraft.world.entity.monster.Enemy;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.common.ForgeConfigSpec;
import org.joml.Vector3f;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.fx.Fx;
import ru.pohsmp.core.fx.FxLib;

/**
 * The four finished Silent Witch staff spells (T20) on top of {@link SilentStaffSpell} (school, tier, staff in the main hand,
 * no scrolls, no cast voice - only the staff's short crystal chime; no outfit needed). Cast time, mana and cooldown come from the
 * [silent_staff] section of the server config; damage is multiplied by the caster's Silent spell power. Shared target and effect helpers.
 */
public abstract class SilentSpell extends SilentStaffSpell {
    public static final int COLOR = Reg.SILENT_COLOR;
    public static final DustParticleOptions TURQUOISE = new DustParticleOptions(new Vector3f(0.5f, 1f, 0.82f), 1.0f);
    public static final DustParticleOptions TURQUOISE_SMALL = new DustParticleOptions(new Vector3f(0.5f, 1f, 0.82f), 0.55f);
    public static final DustParticleOptions WHITE_SMALL = new DustParticleOptions(new Vector3f(0.92f, 1f, 0.98f), 0.5f);

    private final ForgeConfigSpec.IntValue castCfg, manaCfg;
    private final ForgeConfigSpec.DoubleValue cooldownCfg;
    private final int castDef, manaDef;
    private final double cooldownDef;

    protected SilentSpell(String path, int castTicks, int mana, double cooldown,
                          ForgeConfigSpec.IntValue castCfg, ForgeConfigSpec.IntValue manaCfg, ForgeConfigSpec.DoubleValue cooldownCfg) {
        super(path, cooldown, castTicks, mana);
        this.castCfg = castCfg;
        this.manaCfg = manaCfg;
        this.cooldownCfg = cooldownCfg;
        this.castDef = castTicks;
        this.manaDef = mana;
        this.cooldownDef = cooldown;
    }

    /** Config value, or the default while the server config is not loaded (main menu, early client). */
    public static <T> T cfg(Supplier<T> v, T def) {
        try {
            T t = v.get();
            return t == null ? def : t;
        } catch (RuntimeException e) {
            return def;
        }
    }

    @Override protected boolean ready() { return true; }
    @Override public int getCastTime(int level) { return getCastType() == io.redspace.ironsspellbooks.api.spells.CastType.INSTANT ? 0 : cfg(castCfg::get, castDef); }
    @Override public int getManaCost(int level) { return cfg(manaCfg::get, manaDef); }
    @Override public int getSpellCooldown() { return (int) Math.round(cfg(cooldownCfg::get, cooldownDef) * 20); }
    @Override public org.joml.Vector3f getTargetingColor() { return new org.joml.Vector3f(0, 0, 0); }

    /** Damage with the caster's Silent spell power. */
    protected double dmg(LivingEntity caster, double base) {
        return base * mult(caster);
    }

    // ---------------------------------------------------------------- targets

    /** Never hit: the caster, its allies (teams, Iron's summons, tamed pets), spectators, creative players, armor stands. */
    public static boolean friendly(LivingEntity caster, Entity e) {
        if (e == caster) return true;
        if (caster == null) return false;
        if (e.isAlliedTo(caster) || caster.isAlliedTo(e)) return true;
        if (e instanceof OwnableEntity o && o.getOwner() == caster) return true;
        return false;
    }

    /** Anything living the caster may hurt. */
    public static boolean hittable(LivingEntity caster, Entity e) {
        if (!(e instanceof LivingEntity le) || !le.isAlive() || le.isSpectator() || le instanceof ArmorStand) return false;
        if (le instanceof Player p && (p.isCreative() || p.isSpectator())) return false;
        return !friendly(caster, le) && le.isPickable();
    }

    /**
     * Silent Witch magic only hurts hostile creatures (owner 19.11): monsters, mobs hunting the caster or its allies, CNPC NPCs
     * of factions hostile to the caster (or attacking it), and a player only for a while after that player hit the caster
     * ({@link Aggro}, [silent_staff] playerAggroSeconds, renewed by every hit). Peaceful animals, villagers, tamed pets - never.
     */
    public static boolean enemy(LivingEntity caster, Entity e) {
        if (!hittable(caster, e)) return false;
        LivingEntity le = (LivingEntity) e;
        if (le instanceof Player p) return Aggro.hostile(caster, p);
        if (le instanceof Mob m && m.getTarget() != null && (m.getTarget() == caster || friendly(caster, m.getTarget()))) return true;
        if (ru.pohsmp.core.spell.CnpcHooks.isNpc(le)) return caster instanceof Player p && npcHostile(le, p);
        if (le instanceof Enemy) return true;
        return caster.getLastHurtByMob() == le || caster.getLastHurtMob() == le;
    }

    /** Players who hit someone lately: they count as hostile to that one for playerAggroSeconds after the last hit. */
    public static final class Aggro {
        private Aggro() {}

        /** victim -> (player -> game time of the last hit) */
        private static final java.util.Map<java.util.UUID, java.util.Map<java.util.UUID, Long>> HITS = new java.util.HashMap<>();

        private static long window() {
            return 20L * cfg(ru.pohsmp.core.ServerConfig.SILENT_PLAYER_AGGRO::get, 60);
        }

        public static boolean hostile(LivingEntity victim, Player p) {
            if (victim == null) return false;
            var m = HITS.get(victim.getUUID());
            Long t = m == null ? null : m.get(p.getUUID());
            return t != null && victim.level().getGameTime() - t <= window();
        }

        @net.minecraftforge.eventbus.api.SubscribeEvent
        public static void onHurt(net.minecraftforge.event.entity.living.LivingHurtEvent e) {
            LivingEntity v = e.getEntity();
            if (v.level().isClientSide || !(e.getSource().getEntity() instanceof Player p) || p == v) return;
            long now = v.level().getGameTime();
            var m = HITS.computeIfAbsent(v.getUUID(), k -> new java.util.HashMap<>());
            m.put(p.getUUID(), now);
            if (HITS.size() > 256) HITS.values().forEach(x -> x.values().removeIf(t -> now - t > window()));
            HITS.values().removeIf(java.util.Map::isEmpty);
        }

        @net.minecraftforge.eventbus.api.SubscribeEvent
        public static void onStopping(net.minecraftforge.event.server.ServerStoppingEvent e) {
            HITS.clear();
        }
    }

    /** CNPC: the NPC's faction is aggressive to this player (read by reflection; false if CNPC changed or is missing). */
    private static boolean npcHostile(LivingEntity npc, Player p) {
        try {
            Object faction = npc.getClass().getField("faction").get(npc);
            if (faction == null) return false;
            for (java.lang.reflect.Method m : faction.getClass().getMethods())
                if (m.getName().equals("isAggressiveToPlayer") && m.getParameterCount() == 1 && m.getParameterTypes()[0].isInstance(p))
                    return Boolean.TRUE.equals(m.invoke(faction, p));
        } catch (ReflectiveOperationException | RuntimeException ignored) {
        }
        return false;
    }

    /** Living in a cone (full angle in degrees) from the eye along the look, sorted by the angle to the aim (nearest to the crosshair first). */
    public static List<LivingEntity> cone(ServerLevel sl, LivingEntity caster, Vec3 eye, Vec3 look, double range, double fullDeg, boolean needSight) {
        double cos = Math.cos(Math.toRadians(fullDeg / 2));
        List<LivingEntity> out = new ArrayList<>();
        List<double[]> ang = new ArrayList<>();
        for (Entity e : sl.getEntities(caster, new AABB(eye, eye).inflate(range), e -> enemy(caster, e))) {
            LivingEntity le = (LivingEntity) e;
            Vec3 to = aimPoint(le).subtract(eye);
            double d = to.length();
            if (d > range + le.getBbWidth() / 2 || d < 1e-4) continue;
            double c = to.scale(1 / d).dot(look);
            if (c < cos && !le.getBoundingBox().inflate(0.3).contains(eye.add(look.scale(d)))) continue;
            if (needSight && !caster.hasLineOfSight(le)) continue;
            out.add(le);
            ang.add(new double[] {c});
        }
        List<Integer> idx = new ArrayList<>();
        for (int i = 0; i < out.size(); i++) idx.add(i);
        idx.sort(Comparator.comparingDouble(i -> -ang.get(i)[0]));
        List<LivingEntity> sorted = new ArrayList<>();
        for (int i : idx) sorted.add(out.get(i));
        return sorted;
    }

    /** Middle of the body. */
    public static Vec3 aimPoint(LivingEntity e) {
        return e.position().add(0, e.getBbHeight() * 0.5, 0);
    }

    /** The head (spears hit it). */
    public static Vec3 head(LivingEntity e) {
        return e.getEyePosition();
    }

    /** A point at the side of the caster: right &gt; 0 = to the right, up from the feet, fwd along the body yaw. */
    public static Vec3 local(LivingEntity e, double right, double up, double fwd) {
        double yaw = Math.toRadians(e.yBodyRot);
        Vec3 f = new Vec3(-Math.sin(yaw), 0, Math.cos(yaw));
        Vec3 r = new Vec3(-f.z, 0, f.x);
        return e.position().add(r.scale(right)).add(f.scale(fwd)).add(0, up, 0);
    }

    // ---------------------------------------------------------------- effects

    /**
     * Data effect fx/&lt;id&gt;.json (made by the ideas chat) if it is already in the mod: starts it and returns the instance;
     * otherwise -1 and the spell draws its stand-in from existing particles.
     */
    public static int fx(ServerLevel sl, String id, Fx.Spec spec) {
        if (FxLib.fx(id) == null) return -1;
        return Fx.play(sl, spec);
    }

    /** Minecraft yaw / pitch (degrees, pitch positive = down) of a direction: data effects turn their models by these. */
    public static float yawOf(Vec3 d) {
        return (float) Math.toDegrees(Math.atan2(-d.x, d.z));
    }

    public static float pitchOf(Vec3 d) {
        return (float) Math.toDegrees(-Math.atan2(d.y, Math.sqrt(d.x * d.x + d.z * d.z)));
    }

    /** Hit flash of a spear or arrow (fx/silent_wind_spears_hit.json); false if the file is missing (stand-in particles then). */
    public static boolean hitFx(ServerLevel sl, Vec3 at, double scale) {
        return fx(sl, "silent_wind_spears_hit", Fx.fx("silent_wind_spears_hit").at(at).scale(scale)) >= 0;
    }

    public static void particles(ServerLevel sl, ParticleOptions p, Vec3 at, int count, double spread, double speed) {
        for (ServerPlayer pl : sl.players())
            if (pl.distanceToSqr(at) < 96 * 96) sl.sendParticles(pl, p, true, at.x, at.y, at.z, count, spread, spread, spread, speed);
    }

    /** Particles along a segment, every step blocks. */
    public static void line(ServerLevel sl, ParticleOptions p, Vec3 a, Vec3 b, double step) {
        Vec3 d = b.subtract(a);
        int n = Math.max(1, (int) (d.length() / step));
        for (int i = 0; i <= n; i++) particles(sl, p, a.add(d.scale(i / (double) n)), 1, 0, 0);
    }
}
