package ru.pohsmp.core.client.nightmare;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.UUID;
import net.minecraft.client.Minecraft;
import net.minecraft.client.player.AbstractClientPlayer;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.scores.PlayerTeam;
import net.minecraftforge.client.event.RenderLivingEvent;
import net.minecraftforge.client.event.RenderNameTagEvent;
import net.minecraftforge.client.event.RenderPlayerEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.Event;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.nightmare.NightmareMob;

/**
 * T25 «Люди в кошмаре по стадиям» (owner 19.11), on the immersed player's own client only; mobs are left alone, all damage is real.
 * Stage 1: the players swap places - each wears another one's look (skin, name, armour, held items; the victim's own look is in the pool,
 * the caster takes part), fixed for the stage. Stage 2: about a third of them (fixed for the stage) and always the caster are nm_dread
 * with no name, the rest shuffled. Stage 3: every player is nm_dread with no name.
 */
public final class NightmarePeople {
    private NightmarePeople() {}

    private static UUID caster;
    private static int stage, seed;
    /** player -> whose look it wears (stage 1-2) */
    private static final Map<UUID, UUID> FACES = new HashMap<>();
    private static final Map<UUID, Boolean> DREAD = new HashMap<>();

    public static void caster(UUID c) {
        if (c != null) caster = c;
        else if (NightmareClient.stage() <= 0) caster = null;
    }

    @SubscribeEvent
    public static void onTick(TickEvent.ClientTickEvent e) {
        if (e.phase != TickEvent.Phase.END) return;
        var mc = Minecraft.getInstance();
        int st = mc.level == null ? 0 : NightmareClient.stage();
        if (st != stage) {   // a new stage: a new shuffle
            stage = st;
            seed = mc.level == null ? 0 : mc.level.random.nextInt();
            FACES.clear();
            DREAD.clear();
        }
        if (stage <= 0 || stage >= 3 || mc.player == null || mc.level == null) return;
        // the pool: everyone near (the victim's own look too) - a newcomer takes a look nobody wears yet, if any
        List<AbstractClientPlayer> near = new ArrayList<>();
        for (Player p : mc.level.players()) if (p instanceof AbstractClientPlayer a && p.distanceToSqr(mc.player) < 96 * 96) near.add(a);
        if (near.size() < 2) return;
        Random r = new Random(seed);
        for (AbstractClientPlayer p : near) {
            if (p == mc.player || FACES.containsKey(p.getUUID())) continue;
            List<UUID> free = new ArrayList<>();
            for (AbstractClientPlayer q : near) if (q != p && !FACES.containsValue(q.getUUID())) free.add(q.getUUID());
            if (free.isEmpty()) for (AbstractClientPlayer q : near) if (q != p) free.add(q.getUUID());
            r.setSeed(seed ^ p.getUUID().hashCode());
            FACES.put(p.getUUID(), free.get(r.nextInt(free.size())));
        }
    }

    /** nm_dread for this player now (no name). */
    private static boolean dread(Player p) {
        if (stage >= 3) return true;
        if (stage < 2) return false;
        if (p.getUUID().equals(caster)) return true;
        return DREAD.computeIfAbsent(p.getUUID(), k -> Math.floorMod(k.hashCode() ^ seed, 3) == 0);
    }

    private static boolean ours(Player p) {
        return stage > 0 && p != Minecraft.getInstance().player && !HouseClient.on();
    }

    /** IllusionClient.faceOf: the tab entry this player's skin comes from now, or null. */
    public static UUID faceOf(AbstractClientPlayer p) {
        if (!ours(p) || dread(p)) return null;
        return FACES.get(p.getUUID());
    }

    @SubscribeEvent(priority = EventPriority.HIGH)
    public static void onLiving(RenderLivingEvent.Pre<?, ?> e) {
        if (e.getEntity() instanceof Player p && ours(p) && dread(p)) NmStandIn.draw(e, p, NightmareMob.Kind.DREAD);
    }

    @SubscribeEvent(priority = EventPriority.HIGH)
    public static void onName(RenderNameTagEvent e) {
        if (!(e.getEntity() instanceof Player p) || !ours(p)) return;
        if (dread(p)) {
            e.setResult(Event.Result.DENY);
            return;
        }
        UUID f = FACES.get(p.getUUID());
        Player src = f == null || Minecraft.getInstance().level == null ? null : Minecraft.getInstance().level.getPlayerByUUID(f);
        if (src == null) return;
        String n = src.getGameProfile().getName();
        Component name = Component.literal(n);
        PlayerTeam team = Minecraft.getInstance().level.getScoreboard().getPlayersTeam(n);
        if (team != null) name = PlayerTeam.formatNameForTeam(team, name);
        e.setContent(name);
    }

    // ---- the armour and the held items of the borrowed look: put on for this one draw, taken off after ----

    private static final EquipmentSlot[] SLOTS = EquipmentSlot.values();
    private static Player worn;
    private static ItemStack[] own;

    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void onPlayerPre(RenderPlayerEvent.Pre e) {
        restore();
        Player p = e.getEntity();
        if (!ours(p) || dread(p)) return;
        UUID f = FACES.get(p.getUUID());
        Player src = f == null || Minecraft.getInstance().level == null ? null : Minecraft.getInstance().level.getPlayerByUUID(f);
        if (src == null) return;
        own = new ItemStack[SLOTS.length];
        for (int i = 0; i < SLOTS.length; i++) {
            own[i] = p.getItemBySlot(SLOTS[i]);
            p.setItemSlot(SLOTS[i], src.getItemBySlot(SLOTS[i]).copy());
        }
        worn = p;
    }

    @SubscribeEvent(priority = EventPriority.LOWEST)
    public static void onPlayerPost(RenderPlayerEvent.Post e) {
        restore();
    }

    /** Also at the start of every frame: a draw another handler cancelled sends no Post. */
    @SubscribeEvent
    public static void onFrame(TickEvent.RenderTickEvent e) {
        if (e.phase == TickEvent.Phase.START) restore();
    }

    private static void restore() {
        if (worn == null) return;
        for (int i = 0; i < SLOTS.length; i++) worn.setItemSlot(SLOTS[i], own[i]);
        worn = null;
        own = null;
    }
}
