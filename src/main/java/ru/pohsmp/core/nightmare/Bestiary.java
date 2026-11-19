package ru.pohsmp.core.nightmare;

import java.util.ArrayList;
import java.util.EnumMap;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.MobCategory;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.EntityAttributeCreationEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.ForgeRegistries;
import net.minecraftforge.registries.RegistryObject;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.ServerConfig;

/**
 * T25 bestiary: the entity types of the nightmares, who may see them, and who brings them. Every immersed player gets nightmares around
 * it up to [nightmare] limitStageN (by its stage), out of its sight, of the kinds its stage allows; the whole server no more than
 * limitServer. A spell may ask for more at once (spawnFor).
 */
public final class Bestiary {
    private Bestiary() {}

    public static final DeferredRegister<EntityType<?>> ENTITIES = DeferredRegister.create(ForgeRegistries.ENTITY_TYPES, PohCore.MODID);
    public static final Map<NightmareMob.Kind, RegistryObject<EntityType<NightmareMob>>> TYPES = new EnumMap<>(NightmareMob.Kind.class);

    static {
        for (NightmareMob.Kind k : NightmareMob.Kind.values()) {
            float w = 0.6f * k.scale, h = 1.95f * k.scale;
            TYPES.put(k, ENTITIES.register(k.id, () -> EntityType.Builder.<NightmareMob>of((t, l) -> new NightmareMob(t, l, k), MobCategory.MISC)
                    .sized(w, k == NightmareMob.Kind.HANDS ? 0.6f : h).clientTrackingRange(6).updateInterval(2).noSummon().build(k.id)));
        }
    }

    public static void attributes(EntityAttributeCreationEvent e) {
        for (var t : TYPES.values()) e.put(t.get(), NightmareMob.attributes().build());
    }

    /** TrackedEntityMixin: a nightmare is not sent to a player who is not immersed deep enough for it. */
    public static boolean hiddenFrom(Entity e, ServerPlayer viewer) {
        return e instanceof NightmareMob m && Immersion.stage(viewer) < m.kind.stage;
    }

    /** The weeping of a Weeper near it hastens the others (x1.3). */
    static double speedFor(NightmareMob m) {
        if (m.kind == NightmareMob.Kind.WEEPER) return 1;
        for (NightmareMob o : m.level().getEntitiesOfClass(NightmareMob.class, m.getBoundingBox().inflate(16)))
            if (o.kind == NightmareMob.Kind.WEEPER) return 1.3;
        return 1;
    }

    /** Where a body may stand near (x, y, z): solid under the feet, two free blocks, no liquid; null if none in ±6. */
    static Vec3 ground(ServerLevel sl, double x, double y, double z) {
        BlockPos.MutableBlockPos p = new BlockPos.MutableBlockPos();
        int bx = Mth.floor(x), bz = Mth.floor(z), by = Mth.floor(y);
        for (int dy = 0; dy <= 6; dy++)
            for (int s = -1; s <= 1; s += 2) {
                int yy = by + dy * s;
                p.set(bx, yy - 1, bz);
                BlockState under = sl.getBlockState(p);
                if (!under.isFaceSturdy(sl, p, net.minecraft.core.Direction.UP)) continue;
                p.set(bx, yy, bz);
                BlockState a = sl.getBlockState(p);
                BlockState b = sl.getBlockState(p.above());
                if (a.getCollisionShape(sl, p).isEmpty() && b.getCollisionShape(sl, p.above()).isEmpty()
                        && a.getFluidState().isEmpty() && b.getFluidState().isEmpty())
                    return new Vec3(bx + 0.5, yy, bz + 0.5);
                if (dy == 0) break;
            }
        return null;
    }

    /** Kinds a stage may bring. */
    private static List<NightmareMob.Kind> kinds(int stage) {
        List<NightmareMob.Kind> out = new ArrayList<>();
        for (NightmareMob.Kind k : NightmareMob.Kind.values()) if (k != NightmareMob.Kind.DREAD && k.stage <= stage) out.add(k);
        return out;
    }

    private static int limit(int stage) {
        return switch (stage) {
            case 1 -> ServerConfig.get(ServerConfig.IM_LIMIT_1);
            case 2 -> ServerConfig.get(ServerConfig.IM_LIMIT_2);
            case 3 -> ServerConfig.get(ServerConfig.IM_LIMIT_3);
            default -> 0;
        };
    }

    /** Extra room for a victim (the Mythic raises it to limitMythic); expires by itself. */
    private static final Map<UUID, long[]> EXTRA = new HashMap<>();

    public static void allow(ServerPlayer v, int limit, int ticks) {
        EXTRA.put(v.getUUID(), new long[] {limit, Immersion.now() + ticks});
    }

    /** One nightmare of kind for v somewhere out of its sight (dist blocks away); null if no place was found. */
    public static NightmareMob spawnFor(ServerPlayer v, NightmareMob.Kind k, double dist) {
        ServerLevel sl = v.serverLevel();
        Vec3 at = null;
        if (k == NightmareMob.Kind.HANDS) at = v.position();
        else {
            Vec3 look = v.getViewVector(1).multiply(1, 0, 1);
            for (int i = 0; i < 12 && at == null; i++) {
                double a = v.getRandom().nextDouble() * Math.PI * 2;
                Vec3 dir = new Vec3(Math.cos(a), 0, Math.sin(a));
                if (look.lengthSqr() > 1e-4 && dir.dot(look.normalize()) > 0.1) continue;   // not in front of the eyes
                Vec3 g = ground(sl, v.getX() + dir.x * dist, v.getY(), v.getZ() + dir.z * dist);
                if (g != null) at = g;
            }
        }
        if (at == null) return null;
        NightmareMob m = TYPES.get(k).get().create(sl);
        if (m == null) return null;
        m.victim = v.getUUID();
        m.moveTo(at.x, at.y, at.z, v.getRandom().nextFloat() * 360, 0);
        sl.addFreshEntity(m);
        return m;
    }

    public static final class Events {
        private Events() {}

        @SubscribeEvent
        public static void onTick(TickEvent.ServerTickEvent e) {
            if (e.phase != TickEvent.Phase.END || Immersion.now() % 40 != 7) return;
            var server = e.getServer();
            EXTRA.values().removeIf(x -> Immersion.now() >= x[1]);
            Map<UUID, Integer> per = new HashMap<>();
            int total = 0;
            for (ServerLevel sl : server.getAllLevels())
                for (Entity en : sl.getAllEntities())
                    if (en instanceof NightmareMob m) {
                        total++;
                        if (m.victim() != null) per.merge(m.victim(), 1, Integer::sum);
                    }
            int cap = ServerConfig.get(ServerConfig.IM_LIMIT_SERVER);
            for (ServerPlayer v : server.getPlayerList().getPlayers()) {
                if (total >= cap) return;
                int st = Immersion.stage(v);
                if (st <= 0 || v.isSpectator() || v.isCreative()) continue;
                long[] x = EXTRA.get(v.getUUID());
                int lim = Math.max(limit(st), x == null ? 0 : (int) x[0]);
                if (per.getOrDefault(v.getUUID(), 0) >= lim) continue;
                List<NightmareMob.Kind> ks = kinds(st);
                if (ks.isEmpty()) continue;
                NightmareMob.Kind k = ks.get(v.getRandom().nextInt(ks.size()));
                if (k == NightmareMob.Kind.HANDS && v.getRandom().nextInt(3) != 0) k = ks.get(0);   // the hands are rare
                if (spawnFor(v, k, 12 + v.getRandom().nextInt(8)) != null) total++;
            }
        }

        @SubscribeEvent
        public static void onStopping(ServerStoppingEvent e) {
            EXTRA.clear();
        }
    }
}
