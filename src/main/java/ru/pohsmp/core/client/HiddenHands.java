package ru.pohsmp.core.client;

import java.util.HashMap;
import java.util.Map;
import net.minecraft.client.Minecraft;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraftforge.client.event.RenderPlayerEvent;
import net.minecraftforge.event.level.LevelEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;

/**
 * Hides whatever a player holds while one of the staff-less cast animations plays (Milky Way, Soul Devour, Taboo,
 * Closing of Space): the hand items are swapped out right before the player is drawn and put back right after,
 * so nothing changes in the inventory itself. Works for every player this client sees.
 */
public final class HiddenHands {
    private HiddenHands() {}

    /** entity id -> game time until which its hands are drawn empty. */
    private static final Map<Integer, Long> UNTIL = new HashMap<>();
    private static final Map<Integer, ItemStack[]> STASH = new HashMap<>();

    /** Called on the client when a staff-less cast starts; ticks covers the cast and its finish animation. */
    public static void hide(LivingEntity e, int ticks, int finish) {
        if (e.level() == null) return;
        clear(e.getId());
        UNTIL.put(e.getId(), e.level().getGameTime() + ticks);
        FINISH.put(e.getId(), finish);
    }

    public static void show(LivingEntity e) {
        clear(e.getId());
    }

    /** entity id -> the spell whose cast hid the hands (seen in the synced cast data), and when the player was last seen casting it. */
    private static final Map<Integer, String> SPELL = new HashMap<>();
    private static final Map<Integer, Long> LAST_CAST = new HashMap<>();
    /** entity id -> how long the hands stay empty after the cast ends (its finish animation / scene tail). */
    private static final Map<Integer, Integer> FINISH = new HashMap<>();

    /**
     * Hidden only for the cast that asked for it and its finish animation: another spell cast meanwhile (e.g. the Worgan breath
     * right after a cancelled Gate) shows the staff again at once (owner, 19.11.2026: a spell without a camera scene keeps the item).
     */
    private static boolean hidden(Player p) {
        int id = p.getId();
        Long until = UNTIL.get(id);
        if (until == null) return false;
        long now = p.level().getGameTime();
        if (!p.isAlive() || now > until) return clear(id);
        io.redspace.ironsspellbooks.capabilities.magic.SyncedSpellData sd = io.redspace.ironsspellbooks.player.ClientMagicData.getSyncedSpellData(p);
        if (sd != null && sd.isCasting()) {
            String spell = sd.getCastingSpellId();
            String own = SPELL.putIfAbsent(id, spell);
            if (own != null && !own.equals(spell)) return clear(id);
            LAST_CAST.put(id, now);
        } else {
            Long last = LAST_CAST.get(id);
            if (last != null && now - last > FINISH.getOrDefault(id, ru.pohsmp.core.spell.CastAnims.FINISH_TICKS)) return clear(id);
        }
        return true;
    }

    private static boolean clear(int id) {
        UNTIL.remove(id);
        SPELL.remove(id);
        LAST_CAST.remove(id);
        FINISH.remove(id);
        return false;
    }

    @SubscribeEvent(priority = EventPriority.LOWEST)
    public static void onPre(RenderPlayerEvent.Pre e) {
        Player p = e.getEntity();
        if (e.isCanceled() || !hidden(p)) return;
        Inventory inv = p.getInventory();
        int sel = inv.selected;
        if (sel < 0 || sel >= inv.items.size()) return;
        STASH.put(p.getId(), new ItemStack[]{inv.items.get(sel), inv.offhand.get(0)});
        inv.items.set(sel, ItemStack.EMPTY);
        inv.offhand.set(0, ItemStack.EMPTY);
    }

    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void onPost(RenderPlayerEvent.Post e) {
        restore(e.getEntity());
    }

    private static void restore(Player p) {
        ItemStack[] s = STASH.remove(p.getId());
        if (s == null) return;
        Inventory inv = p.getInventory();
        int sel = inv.selected;
        if (sel >= 0 && sel < inv.items.size() && inv.items.get(sel).isEmpty()) inv.items.set(sel, s[0]);
        if (inv.offhand.get(0).isEmpty()) inv.offhand.set(0, s[1]);
    }

    @SubscribeEvent
    public static void onUnload(LevelEvent.Unload e) {
        if (!e.getLevel().isClientSide()) return;
        Minecraft mc = Minecraft.getInstance();
        if (mc.level != null) for (Integer id : STASH.keySet().toArray(new Integer[0])) {
            if (mc.level.getEntity(id) instanceof Player p) restore(p);
        }
        STASH.clear();
        UNTIL.clear();
        SPELL.clear();
        LAST_CAST.clear();
        FINISH.clear();
    }
}
