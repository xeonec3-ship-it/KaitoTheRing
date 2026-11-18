package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.spells.SpellAnimations;
import io.redspace.ironsspellbooks.api.spells.SpellRarity;
import io.redspace.ironsspellbooks.api.util.AnimationHolder;
import io.redspace.ironsspellbooks.api.util.CameraShakeData;
import io.redspace.ironsspellbooks.api.util.CameraShakeManager;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.function.Function;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.particles.DustParticleOptions;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.tags.BlockTags;
import net.minecraft.tags.DamageTypeTags;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LightningBolt;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.portal.PortalInfo;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.common.util.ITeleporter;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.living.LivingAttackEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.network.PacketDistributor;
import org.joml.Vector3f;
import ru.pohsmp.core.DivineEvents;
import ru.pohsmp.core.DownfallStaff;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.net.Net;

/**
 * "Creation" tier, Forbidden school, only from its staff. "Downfall": a 25 s cast; every player within 64 blocks is frozen,
 * cannot be hurt and watches a camera cutscene (client: DownfallCut). Then a rift opens where the caster was looking
 * (up to 48 blocks) and for a minute sends everything that touches it to the Nether (x/8, z/8, a safe spot). No way back.
 * Price: mana 0, for 3 minutes no mana and no spells, max health -50%, slow and weak, darkness 10 s.
 */
public class DownfallSpell extends PohSpell {
    public static final String PATH = "downfall";
    public static final int CAST = 500, RIFT_TICKS = 1200, BACKLASH_TICKS = 3600;
    public static final double RANGE = 48, CUT_R = 64, RIFT_W = 1.8, RIFT_H = 5.2;
    private static final int COLOR = Reg.FORBIDDEN_COLOR;
    private static final DustParticleOptions GOLD = new DustParticleOptions(new Vector3f(1f, 0.78f, 0.2f), 1.6f);
    private static final DustParticleOptions BLACK = new DustParticleOptions(new Vector3f(0.05f, 0.03f, 0.03f), 2.2f);

    private static final class Cast {
        Vec3 at, rift, normal;
        int age, cutKey, downKey;
        List<UUID> watchers = new ArrayList<>();
    }

    private static final Map<UUID, Cast> CASTS = new HashMap<>();

    public DownfallSpell() {
        super(PATH, Reg.FORBIDDEN_ID, SpellRarity.LEGENDARY, 1, 600, CAST, 0, 0);
    }

    @Override public CastType getCastType() { return CastType.LONG; }
    @Override public boolean canBeInterrupted(Player player) { return false; }
    @Override public boolean allowCrafting() { return false; }
    @Override public boolean allowLooting() { return false; }
    @Override public Optional<SoundEvent> getCastStartSound() { return Optional.of(SoundEvents.BEACON_ACTIVATE); }
    @Override public Optional<SoundEvent> getCastFinishSound() { return Optional.empty(); }
    @Override public AnimationHolder getCastStartAnimation() { return SpellAnimations.ANIMATION_LONG_CAST; }
    @Override public AnimationHolder getCastFinishAnimation() { return SpellAnimations.ANIMATION_LONG_CAST_FINISH; }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("cast", CAST / 20), ui("rift", RIFT_TICKS / 20, (int) RANGE), ui("watch", (int) CUT_R), ui("price", BACKLASH_TICKS / 1200));
    }

    @Override
    public boolean checkPreCastConditions(Level level, int spellLevel, LivingEntity entity, MagicData md) {
        String why = null;
        if (!(entity.getMainHandItem().getItem() instanceof DownfallStaff)) why = "need_staff";
        else if (level.dimension() == Level.NETHER) why = "nether";
        if (why != null) {
            if (entity instanceof Player p) p.displayClientMessage(Component.translatable("ui.pohsmp_core.downfall." + why).withStyle(s -> s.withColor(COLOR)), true);
            return false;
        }
        return super.checkPreCastConditions(level, spellLevel, entity, md);
    }

    @Override
    public void onServerPreCast(Level level, int spellLevel, LivingEntity caster, MagicData md) {
        super.onServerPreCast(level, spellLevel, caster, md);
        if (level instanceof ServerLevel sl) start(sl, caster);
    }

    private void start(ServerLevel sl, LivingEntity caster) {
        Cast c = new Cast();
        c.at = caster.position();
        Vec3 look = caster.getLookAngle().multiply(1, 0, 1);
        if (look.lengthSqr() < 1e-4) look = new Vec3(0, 0, 1);
        look = look.normalize();
        Vec3 p = lookPoint(sl, caster, RANGE);
        if (hdist(caster, p) < 6) p = c.at.add(look.scale(7)).add(0, 1, 0);
        c.rift = ground(sl, caster, p);
        Vec3 n = c.at.subtract(c.rift).multiply(1, 0, 1);
        c.normal = n.lengthSqr() < 1e-4 ? look.scale(-1) : n.normalize();
        c.cutKey = HigherSpell.key();
        c.downKey = HigherSpell.key();
        float ang = (float) Math.atan2(c.normal.z, c.normal.x);
        c.watchers = Cutscene.start(sl, caster, c.cutKey, Cutscene.DOWNFALL, CAST, c.rift, ang);
        HigherSpell.fx(sl, c.at.x, c.at.y, c.at.z, new Net.HFx(Net.HFx.DOWN, c.downKey, caster.getId(), -1, CAST, c.rift.x, c.rift.y, c.rift.z, ang, COLOR));
        CASTS.put(caster.getUUID(), c);
        DownfallStaff.anim(caster, "cast");
        sl.playSound(null, c.at.x, c.at.y, c.at.z, SoundEvents.BEACON_ACTIVATE, SoundSource.PLAYERS, 4f, 0.5f);
    }

    @Override
    public void onServerCastTick(Level level, int spellLevel, LivingEntity caster, MagicData md) {
        super.onServerCastTick(level, spellLevel, caster, md);
        if (!(level instanceof ServerLevel sl)) return;
        Cast c = CASTS.get(caster.getUUID());
        if (c == null) {
            start(sl, caster);
            c = CASTS.get(caster.getUUID());
        }
        c.age++;
        tickFx(sl, caster, c);
    }

    private static void tickFx(ServerLevel sl, LivingEntity caster, Cast c) {
        int t = c.age;
        Vec3 a = c.at, r = c.rift, rc = r.add(0, RIFT_H / 2, 0);
        if (t % 2 == 0) {   // two golden arms spiral into the caster
            double k = (t % 40) / 40.0, rad = 4.5 * (1 - k);
            for (int arm = 0; arm < 2; arm++) {
                double ang = t * 0.25 + arm * Math.PI;
                DivineEvents.particle(sl, GOLD, a.x + Math.cos(ang) * rad, a.y + 0.2 + k * 2.2, a.z + Math.sin(ang) * rad, 1, 0, 0);
                DivineEvents.particle(sl, ParticleTypes.SOUL_FIRE_FLAME, a.x + Math.cos(ang + 0.3) * rad, a.y + 0.1, a.z + Math.sin(ang + 0.3) * rad, 1, 0, 0);
            }
            DivineEvents.particle(sl, ParticleTypes.ENCHANT, a.x, a.y + 2.2, a.z, 6, 1.6, 0.6);
        }
        if (t % 40 == 0) sl.playSound(null, a.x, a.y, a.z, SoundEvents.AMBIENT_CAVE.value(), SoundSource.PLAYERS, 3f, 0.4f);
        switch (t) {
            case 100 -> sl.playSound(null, a.x, a.y, a.z, SoundEvents.WITHER_SPAWN, SoundSource.PLAYERS, 2.5f, 0.6f);
            case 200 -> {
                sl.playSound(null, r.x, r.y, r.z, SoundEvents.END_PORTAL_SPAWN, SoundSource.PLAYERS, 4f, 0.5f);
                CameraShakeManager.addCameraShake(new CameraShakeData(sl, 20, r, 40));
            }
            case 300 -> {
                sl.playSound(null, a.x, a.y, a.z, SoundEvents.ELDER_GUARDIAN_CURSE, SoundSource.PLAYERS, 2f, 0.5f);
                CameraShakeManager.addCameraShake(new CameraShakeData(sl, 20, a, 40));
            }
            case 400 -> {
                sl.playSound(null, a.x, a.y, a.z, SoundEvents.WARDEN_SONIC_CHARGE, SoundSource.PLAYERS, 4f, 0.5f);
                sl.playSound(null, r.x, r.y, r.z, SoundEvents.WARDEN_SONIC_CHARGE, SoundSource.PLAYERS, 4f, 0.4f);
            }
            case 480 -> sl.playSound(null, r.x, r.y, r.z, SoundEvents.END_GATEWAY_SPAWN, SoundSource.PLAYERS, 4f, 0.5f);
            default -> {}
        }
        if (t >= 100 && t % 25 == 0) {   // dry lightning around the caster, nothing burns
            double ang = sl.random.nextDouble() * Math.PI * 2, d = 7 + sl.random.nextDouble() * 9;
            bolt(sl, ground(sl, caster, a.add(Math.cos(ang) * d, 4, Math.sin(ang) * d)));
        }
        if (t >= 200 && t % 2 == 0) {
            double grow = Math.min(1, (t - 200) / 200.0);
            DivineEvents.particle(sl, ParticleTypes.REVERSE_PORTAL, rc.x, rc.y, rc.z, 6, 0.6 + grow, 0.05);
            DivineEvents.particle(sl, BLACK, rc.x, rc.y, rc.z, 3, 0.4 + grow, 0);
            for (int i = 0; i < 4; i++) {
                double ang = sl.random.nextDouble() * Math.PI * 2, d = 1 + grow * 6;
                DivineEvents.particle(sl, ParticleTypes.LARGE_SMOKE, r.x + Math.cos(ang) * d, r.y + 0.1, r.z + Math.sin(ang) * d, 1, 0, 0.01);
            }
        }
        if (t >= 300 && t % 3 == 0) {   // golden thread from the staff to the rift
            Vec3 from = caster.getEyePosition().add(0, 0.8, 0);
            for (int i = 0; i < 14; i++) {
                double k = ((i / 14.0) + t * 0.02) % 1.0;
                Vec3 q = from.lerp(rc, k);
                DivineEvents.particle(sl, GOLD, q.x, q.y + Math.sin(k * Math.PI) * 1.5, q.z, 1, 0, 0);
            }
        }
        if (t >= 400 && t % 20 == 0) CameraShakeManager.addCameraShake(new CameraShakeData(sl, 14, rc, 60));
        if (t >= 440 && t % 10 == 0) bolt(sl, r.add((sl.random.nextDouble() - 0.5) * 6, 0, (sl.random.nextDouble() - 0.5) * 6));
    }

    private static void bolt(ServerLevel sl, Vec3 p) {
        LightningBolt b = EntityType.LIGHTNING_BOLT.create(sl);
        if (b == null) return;
        b.moveTo(p.x, p.y, p.z);
        b.setVisualOnly(true);
        sl.addFreshEntity(b);
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            Cast c = CASTS.get(caster.getUUID());
            if (c != null) {
                c.age = CAST + 1;
                openRift(sl, c);
                backlash(caster, md);
                DownfallStaff.anim(caster, "flash");
                Cutscene.flash(sl, c.watchers, 24, 0xFFE6A0);
            }
        }
        super.onCast(level, spellLevel, caster, source, md);
    }

    @Override
    public void onServerCastComplete(Level level, int spellLevel, LivingEntity caster, MagicData md, boolean cancelled) {
        Cast c = CASTS.remove(caster.getUUID());
        if (c != null && level instanceof ServerLevel sl) {
            HigherSpell.stop(sl, c.at.x, c.at.y, c.at.z, c.cutKey);
            HigherSpell.stop(sl, c.at.x, c.at.y, c.at.z, c.downKey);
            Cutscene.end(sl, caster, c.watchers, c.cutKey);
            if (c.age <= CAST) DownfallStaff.anim(caster, null);
        }
        super.onServerCastComplete(level, spellLevel, caster, md, cancelled);
    }

    private static void backlash(LivingEntity c, MagicData md) {
        if (md != null) md.setMana(0);
        if (c instanceof ServerPlayer sp) MagicData.getPlayerMagicData(sp).setMana(0);
        c.removeEffect(Reg.CREATION_BACKLASH.get());
        c.addEffect(new MobEffectInstance(Reg.CREATION_BACKLASH.get(), BACKLASH_TICKS, 0, false, true, true));
        c.addEffect(new MobEffectInstance(MobEffects.DARKNESS, 200, 0, false, false, false));
        MobEffectInstance n = new MobEffectInstance(MobEffects.CONFUSION, 160, 0, false, false, false);
        n.setCurativeItems(new ArrayList<>());
        c.addEffect(n);
        if (c.getHealth() > c.getMaxHealth()) c.setHealth(c.getMaxHealth());
    }

    // ---- the rift ----

    private static void openRift(ServerLevel sl, Cast c) {
        Vec3 g = c.rift, n = c.normal, side = new Vec3(-n.z, 0, n.x), center = g.add(0, RIFT_H / 2, 0);
        int key = HigherSpell.key();
        HigherSpell.fx(sl, g.x, g.y, g.z, new Net.HFx(Net.HFx.RIFT, key, -1, -1, RIFT_TICKS, g.x, g.y, g.z, Math.atan2(n.z, n.x), COLOR));
        HigherSpell.burst(sl, g.x, g.y + 0.1, g.z, 8, COLOR);
        DivineEvents.particle(sl, ParticleTypes.EXPLOSION_EMITTER, center.x, center.y, center.z, 1, 0, 0);
        sl.playSound(null, g.x, g.y, g.z, SoundEvents.END_PORTAL_SPAWN, SoundSource.PLAYERS, 5f, 0.4f);
        sl.playSound(null, g.x, g.y, g.z, SoundEvents.GENERIC_EXPLODE, SoundSource.PLAYERS, 3f, 0.5f);
        for (int i = 0; i < 3; i++) bolt(sl, g.add(side.scale((i - 1) * 2.5)));
        CameraShakeManager.addCameraShake(new CameraShakeData(sl, 30, center, 64));
        ServerLevel nether = sl.getServer().getLevel(Level.NETHER);
        if (nether == null) return;
        Vec3 dest = safe(nether, g.x / 8.0, g.z / 8.0);
        Tasks.add(new Tasks.Task() {
            int age;

            @Override
            public boolean tick() {
                age++;
                if (age % 2 == 0) {
                    DivineEvents.particle(sl, ParticleTypes.REVERSE_PORTAL, center.x, center.y, center.z, 8, 1.2, 0.1);
                    DivineEvents.particle(sl, ParticleTypes.FLAME, center.x, center.y - 1.5, center.z, 2, 0.8, 0.02);
                    DivineEvents.particle(sl, GOLD, center.x + side.x * RIFT_W, center.y + (sl.random.nextDouble() - 0.5) * RIFT_H, center.z + side.z * RIFT_W, 1, 0.1, 0);
                    DivineEvents.particle(sl, GOLD, center.x - side.x * RIFT_W, center.y + (sl.random.nextDouble() - 0.5) * RIFT_H, center.z - side.z * RIFT_W, 1, 0.1, 0);
                }
                if (age % 40 == 0) sl.playSound(null, center.x, center.y, center.z, SoundEvents.PORTAL_AMBIENT, SoundSource.PLAYERS, 3f, 0.5f);
                if (age >= 15) swallow(sl, nether, center, n, side, dest);
                if (age >= RIFT_TICKS) {
                    HigherSpell.stop(sl, g.x, g.y, g.z, key);
                    HigherSpell.burst(sl, g.x, g.y + 0.1, g.z, 5, COLOR);
                    sl.playSound(null, center.x, center.y, center.z, SoundEvents.END_PORTAL_FRAME_FILL, SoundSource.PLAYERS, 4f, 0.4f);
                    return false;
                }
                return true;
            }
        });
    }

    /** Everything whose body touches the rift's oval goes through. */
    private static void swallow(ServerLevel sl, ServerLevel nether, Vec3 center, Vec3 n, Vec3 side, Vec3 dest) {
        AABB box = new AABB(center, center).inflate(RIFT_W + 1.5, RIFT_H / 2 + 1, RIFT_W + 1.5);
        for (Entity e : sl.getEntities((Entity) null, box, e -> e.isAlive() && !e.isSpectator() && !e.getTags().contains(Disp.TAG))) {
            Vec3 d = e.position().add(0, e.getBbHeight() / 2, 0).subtract(center);
            double across = Math.abs(d.dot(n)), along = d.dot(side), up = d.y;
            if (across > 0.45 + e.getBbWidth() / 2) continue;
            double ex = along / (RIFT_W + e.getBbWidth() / 2), ey = up / (RIFT_H / 2 + e.getBbHeight() / 4);
            if (ex * ex + ey * ey > 1) continue;
            if (e.isPassenger()) e.stopRiding();
            if (e.isVehicle()) e.ejectPassengers();
            sl.playSound(null, e.getX(), e.getY(), e.getZ(), SoundEvents.PORTAL_TRAVEL, SoundSource.PLAYERS, 0.6f, 0.6f);
            DivineEvents.particle(sl, ParticleTypes.REVERSE_PORTAL, e.getX(), e.getY() + 1, e.getZ(), 30, 0.5, 0.2);
            send(e, nether, dest);
        }
    }

    private static void send(Entity e, ServerLevel nether, Vec3 dest) {
        e.fallDistance = 0;
        if (e instanceof ServerPlayer sp) {
            sp.teleportTo(nether, dest.x, dest.y, dest.z, sp.getYRot(), sp.getXRot());
            sp.setDeltaMovement(Vec3.ZERO);
            nether.playSound(null, dest.x, dest.y, dest.z, SoundEvents.PORTAL_TRAVEL, SoundSource.PLAYERS, 0.8f, 0.6f);
            return;
        }
        e.changeDimension(nether, new ITeleporter() {
            @Override
            public PortalInfo getPortalInfo(Entity entity, ServerLevel destWorld, Function<ServerLevel, PortalInfo> defaultPortalInfo) {
                return new PortalInfo(dest, Vec3.ZERO, entity.getYRot(), entity.getXRot());
            }

            @Override
            public boolean playTeleportSound(ServerPlayer player, ServerLevel sourceWorld, ServerLevel destWorld) {
                return false;
            }
        });
    }

    /** A spot with solid ground and two free blocks above, near x z in the Nether; otherwise a small obsidian ledge at y 70. */
    private static Vec3 safe(ServerLevel nl, double x, double z) {
        BlockPos c = nl.getWorldBorder().clampToBounds(x, 64, z);
        for (int r = 0; r <= 24; r += 4) {
            int steps = r == 0 ? 1 : 8;
            for (int k = 0; k < steps; k++) {
                int cx = c.getX() + (int) Math.round(r * Math.cos(k * Math.PI / 4)), cz = c.getZ() + (int) Math.round(r * Math.sin(k * Math.PI / 4));
                for (int y = 100; y >= 32; y--) {
                    BlockPos p = new BlockPos(cx, y, cz);
                    if (standable(nl, p)) return Vec3.atBottomCenterOf(p);
                }
            }
        }
        BlockPos base = new BlockPos(c.getX(), 70, c.getZ());
        for (int dx = -2; dx <= 2; dx++)
            for (int dz = -2; dz <= 2; dz++) {
                nl.setBlockAndUpdate(base.offset(dx, -1, dz), Blocks.OBSIDIAN.defaultBlockState());
                for (int dy = 0; dy < 3; dy++) nl.setBlockAndUpdate(base.offset(dx, dy, dz), Blocks.AIR.defaultBlockState());
            }
        return Vec3.atBottomCenterOf(base);
    }

    private static boolean standable(ServerLevel nl, BlockPos p) {
        BlockState below = nl.getBlockState(p.below());
        if (!below.isFaceSturdy(nl, p.below(), Direction.UP) || below.is(Blocks.MAGMA_BLOCK) || !below.getFluidState().isEmpty()) return false;
        for (int i = 0; i < 2; i++) {
            BlockPos q = p.above(i);
            BlockState s = nl.getBlockState(q);
            if (!s.getCollisionShape(nl, q).isEmpty() || !s.getFluidState().isEmpty() || s.is(BlockTags.FIRE)) return false;
        }
        return true;
    }

    public static final class DownfallEvents {
        private DownfallEvents() {}

        @SubscribeEvent
        public static void onStopping(ServerStoppingEvent e) {
            CASTS.clear();
        }
    }

    /** Ids of frozen players (for tests). */
    public static List<UUID> frozen() {
        return Cutscene.frozen();
    }
}
