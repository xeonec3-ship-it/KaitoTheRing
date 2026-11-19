package ru.pohsmp.core;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.item.Scroll;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.item.ItemStack;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;

/**
 * Scrolls with charges (T16): NBT {@code pohsmp_charges} 1..3 on an Iron's scroll. A cast spends one charge, the scroll disappears
 * with the last one. Iron's itself always removes the scroll after a scroll cast ({@code Scroll.removeScrollAfterCast}, also on a
 * cancelled continuous cast); we watch the casting stack of every player who casts from a charged scroll and, when Iron's takes it,
 * give it back with one charge less. Creative players spend nothing (Iron's does not take scrolls from them either).
 * {@code pohsmp_charges_max} keeps the starting count for the tooltip ("Charges: 2/3"); it is written on the first spent charge.
 */
public final class Charges {
    private Charges() {}

    public static final String NBT = "pohsmp_charges", NBT_MAX = "pohsmp_charges_max";
    public static final int MAX = 3;

    /** Charges left on a scroll, 0 = an ordinary scroll (no tag). */
    public static int get(ItemStack st) {
        if (st == null || st.isEmpty() || !(st.getItem() instanceof Scroll)) return 0;
        CompoundTag tag = st.getTag();
        if (tag == null || !tag.contains(NBT)) return 0;
        return Math.max(1, Math.min(MAX, tag.getInt(NBT)));
    }

    /** Charges the scroll started with (for "2/3"). */
    public static int max(ItemStack st) {
        int c = get(st);
        if (c == 0) return 0;
        CompoundTag tag = st.getTag();
        int m = tag != null && tag.contains(NBT_MAX) ? tag.getInt(NBT_MAX) : c;
        return Math.max(c, Math.min(MAX, m));
    }

    public static void set(ItemStack st, int charges, int max) {
        st.getOrCreateTag().putInt(NBT, charges);
        st.getOrCreateTag().putInt(NBT_MAX, max);
    }

    /** Tooltip line "Charges: 2/3", or null for a scroll without charges. */
    public static MutableComponent tooltip(ItemStack st) {
        int c = get(st);
        if (c == 0) return null;
        return Component.translatable("tooltip.pohsmp_core.charges", c, max(st)).withStyle(s -> s.withColor(0xE8C26A));
    }

    // ---- spending ----

    private static final class Track {
        ItemStack stack;
        int count, charges, max;
    }

    private static final Map<UUID, Track> TRACK = new HashMap<>();

    @SubscribeEvent
    public static void onServerTick(TickEvent.ServerTickEvent e) {
        check(e.getServer());
    }

    @SubscribeEvent
    public static void onLogout(PlayerEvent.PlayerLoggedOutEvent e) {
        TRACK.remove(e.getEntity().getUUID());
    }

    @SubscribeEvent
    public static void onStopping(ServerStoppingEvent e) {
        TRACK.clear();
    }

    /**
     * Runs at the start and the end of every server tick: Iron's takes the scroll inside the level tick (cast finished) or between
     * ticks (a cancel packet), so a scroll is always seen before and after.
     */
    public static void check(MinecraftServer server) {
        for (ServerPlayer p : server.getPlayerList().getPlayers()) {
            UUID id = p.getUUID();
            Track t = TRACK.get(id);
            MagicData md = MagicData.getPlayerMagicData(p);
            if (t != null) {
                if (t.stack.getCount() < t.count) {
                    TRACK.remove(id);
                    giveBack(p, t);
                    t = null;
                } else if (!md.isCasting() || md.getPlayerCastingItem() != t.stack) {
                    TRACK.remove(id);
                    t = null;
                }
            }
            if (t == null && md.isCasting() && md.getCastSource() == CastSource.SCROLL && !p.isCreative()) {
                ItemStack st = md.getPlayerCastingItem();
                int c = get(st);
                if (c > 1) {
                    Track n = new Track();
                    n.stack = st;
                    n.count = st.getCount();
                    n.charges = c;
                    n.max = max(st);
                    TRACK.put(id, n);
                }
            }
        }
    }

    /** Iron's took the scroll: return it with one charge less (a stack of several gives back one scroll with the rest). */
    private static void giveBack(ServerPlayer p, Track t) {
        int left = t.charges - 1;
        if (left <= 0) return;
        if (t.stack.isEmpty() && holds(p.getInventory(), t.stack)) {
            t.stack.setCount(1);
            set(t.stack, left, t.max);
        } else {
            ItemStack one = t.stack.copyWithCount(1);
            set(one, left, t.max);
            if (!p.getInventory().add(one)) p.drop(one, false);
        }
        p.inventoryMenu.broadcastChanges();
    }

    private static boolean holds(Inventory inv, ItemStack st) {
        for (int i = 0; i < inv.getContainerSize(); i++) if (inv.getItem(i) == st) return true;
        return false;
    }
}
