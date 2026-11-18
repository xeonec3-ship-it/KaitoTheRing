package ru.pohsmp.core.spell;

import java.util.Collections;
import java.util.HashSet;
import java.util.Set;
import java.util.UUID;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.FloatTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraftforge.event.entity.EntityJoinLevelEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;

/**
 * Temporary display entities for spell visuals. Each one is tagged "poh_fx" and kept in memory; a tagged display that joins
 * the level without being known (left over after a restart or a crash) is removed at once.
 */
public final class Disp {
    private Disp() {}

    public static final String TAG = "poh_fx";
    private static final Set<UUID> LIVE = Collections.synchronizedSet(new HashSet<>());

    /** Block display: block id, scale (sx sy sz) centered on the position in x/z, bottom at the position; rotation around y (degrees). */
    public static Entity block(ServerLevel sl, String block, double x, double y, double z, float sx, float sy, float sz, float yaw) {
        CompoundTag t = new CompoundTag();
        CompoundTag st = new CompoundTag();
        st.putString("Name", block);
        t.put("block_state", st);
        t.put("transformation", transform(-sx / 2, 0, -sz / 2, sx, sy, sz));
        return spawn(sl, EntityType.BLOCK_DISPLAY, t, x, y, z, yaw);
    }

    /** Item display: item id, uniform scale, rotation around y. */
    public static Entity item(ServerLevel sl, String item, double x, double y, double z, float scale, float yaw) {
        CompoundTag t = new CompoundTag();
        CompoundTag it = new CompoundTag();
        it.putString("id", item);
        it.putByte("Count", (byte) 1);
        t.put("item", it);
        t.put("transformation", transform(0, 0, 0, scale, scale, scale));
        return spawn(sl, EntityType.ITEM_DISPLAY, t, x, y, z, yaw);
    }

    private static ListTag transform(float tx, float ty, float tz, float sx, float sy, float sz) {
        // 4x4 row-major matrix: scale + translation
        float[] m = {sx, 0, 0, tx, 0, sy, 0, ty, 0, 0, sz, tz, 0, 0, 0, 1};
        ListTag l = new ListTag();
        for (float f : m) l.add(FloatTag.valueOf(f));
        return l;
    }

    private static Entity spawn(ServerLevel sl, EntityType<?> type, CompoundTag extra, double x, double y, double z, float yaw) {
        Entity e = type.create(sl);
        if (e == null) return null;
        CompoundTag full = e.saveWithoutId(new CompoundTag());
        full.merge(extra);
        e.load(full);
        e.moveTo(x, y, z, yaw, 0);
        e.addTag(TAG);
        e.setSilent(true);
        LIVE.add(e.getUUID());
        sl.addFreshEntity(e);
        return e;
    }

    /** Marks any temporary entity (a summoned creeper, a decoy): removed if it is ever loaded after a restart. Call before adding it. */
    public static void track(Entity e) {
        e.addTag(TAG);
        LIVE.add(e.getUUID());
    }

    public static void move(Entity e, double x, double y, double z, float yaw) {
        if (e != null && !e.isRemoved()) e.moveTo(x, y, z, yaw, 0);
    }

    public static void kill(Entity e) {
        if (e == null) return;
        LIVE.remove(e.getUUID());
        e.discard();
    }

    @SubscribeEvent
    public static void onJoin(EntityJoinLevelEvent e) {
        if (e.getLevel().isClientSide) return;
        Entity en = e.getEntity();
        if (en.getTags().contains(TAG) && !LIVE.contains(en.getUUID())) e.setCanceled(true);
    }

    @SubscribeEvent
    public static void onStopping(ServerStoppingEvent e) {
        LIVE.clear();
    }
}
