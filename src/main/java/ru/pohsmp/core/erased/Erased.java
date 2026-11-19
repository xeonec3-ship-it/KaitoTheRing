package ru.pohsmp.core.erased;

import com.mojang.brigadier.arguments.IntegerArgumentType;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.EntityArgument;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.ClickEvent;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.HoverEvent;
import net.minecraft.network.chat.Style;
import net.minecraft.network.chat.contents.TranslatableContents;
import net.minecraft.network.protocol.game.ClientboundPlayerInfoRemovePacket;
import net.minecraft.network.protocol.game.ClientboundPlayerInfoUpdatePacket;
import net.minecraft.ChatFormatting;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ChunkMap;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.saveddata.SavedData;
import net.minecraft.world.phys.AABB;
import net.minecraftforge.event.CommandEvent;
import net.minecraftforge.event.RegisterCommandsEvent;
import net.minecraftforge.event.ServerChatEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.living.LivingChangeTargetEvent;
import net.minecraftforge.event.entity.living.LivingEntityUseItemEvent;
import net.minecraftforge.event.entity.living.LivingHealEvent;
import net.minecraftforge.event.entity.living.LivingHurtEvent;
import net.minecraftforge.event.entity.living.LivingUseTotemEvent;
import net.minecraftforge.event.entity.player.EntityItemPickupEvent;
import net.minecraftforge.event.entity.player.FillBucketEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.event.entity.player.PlayerInteractEvent;
import net.minecraftforge.event.level.BlockEvent;
import net.minecraftforge.event.server.ServerStartedEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.Event;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.network.PacketDistributor;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.fx.Fx;
import ru.pohsmp.core.net.IlluMsg;
import ru.pohsmp.core.net.Net;

/**
 * T24 «Стёртое имя»: the world forgot a player for 10 minutes. Kept in the world's data by the real time it ends (a relog or a restart
 * does not end it). While erased:
 * <ul>
 * <li>nobody else is sent its entity (mixin/TrackedEntityMixin) - no model, name, shadow, entity sounds, minimap dot, Jade line;</li>
 * <li>it is off everybody else's Tab list; vanilla join / leave / death / advancement lines about it are not sent (mixin/PlayerListMixin);</li>
 * <li>its chat and /msg /tell /w /me /teammsg go nowhere (it gets «Тебя никто не слышит»); its voice is not heard (compat/VoiceIllusions);</li>
 * <li>mobs drop it as a target; its damage x0.25; no healing of any kind, no totem; it picks nothing up;</li>
 * <li>owner 19.11: «Мир его не признаёт» - it cannot use any block (containers, doors, levers...), place or break blocks, even its own.</li>
 * </ul>
 * Lifted by time («вернулся в мир»), Blessing or /pohsmp erase clear; then 10 s it cannot be erased again.
 */
public final class Erased {
    private Erased() {}

    public static final long DURATION_MS = 10 * 60 * 1000L, IMMUNE_MS = 10_000L;
    public static final int COLOR = 0xFFFF55;   // the yellow of the vanilla join/leave lines

    // ---------------------------------------------------------------- data

    private static final class Data extends SavedData {
        /** player -> end, ms of the real clock */
        final Map<UUID, Long> until = new HashMap<>();
        final Map<UUID, String> names = new HashMap<>();

        static Data load(CompoundTag t) {
            Data d = new Data();
            CompoundTag a = t.getCompound("erased");
            for (String k : a.getAllKeys()) {
                try {
                    UUID u = UUID.fromString(k);
                    CompoundTag e = a.getCompound(k);
                    d.until.put(u, e.getLong("until"));
                    d.names.put(u, e.getString("name"));
                } catch (IllegalArgumentException ignored) {}
            }
            return d;
        }

        @Override
        public CompoundTag save(CompoundTag t) {
            CompoundTag a = new CompoundTag();
            until.forEach((u, end) -> {
                CompoundTag e = new CompoundTag();
                e.putLong("until", end);
                e.putString("name", names.getOrDefault(u, ""));
                a.put(u.toString(), e);
            });
            t.put("erased", a);
            return t;
        }
    }

    private static Data data;
    private static MinecraftServer server;
    private static final Map<UUID, Long> IMMUNE = new HashMap<>();
    private static final Map<UUID, Integer> SELF_FX = new HashMap<>();
    private static final Map<UUID, Long> LAST_DENY = new HashMap<>();
    /** erased ones waiting for their vanish (the spell hides the target on tick 300, after erased_vanish began on 290) */
    private static volatile Set<UUID> SNAPSHOT = Set.of();

    private static Data data() {
        if (data == null && server != null) data = server.overworld().getDataStorage().computeIfAbsent(Data::load, Data::new, "pohsmp_erased");
        return data;
    }

    private static void snapshot() {
        Data d = data();
        SNAPSHOT = d == null ? Set.of() : Set.copyOf(d.until.keySet());
    }

    /** Any thread (the voice chat asks from its own). */
    public static boolean isErased(UUID id) {
        return id != null && SNAPSHOT.contains(id);
    }

    public static boolean isErased(Entity e) {
        return e instanceof Player && isErased(e.getUUID());
    }

    /** viewer does not get e's entity (everyone but e itself). */
    public static boolean hiddenFrom(Entity e, ServerPlayer viewer) {
        return e != viewer && isErased(e);
    }

    public static long msLeft(UUID id) {
        Data d = data();
        Long end = d == null ? null : d.until.get(id);
        return end == null ? 0 : Math.max(0, end - System.currentTimeMillis());
    }

    public static boolean immune(UUID id) {
        Long t = IMMUNE.get(id);
        return t != null && System.currentTimeMillis() < t;
    }

    // ---------------------------------------------------------------- erase / lift

    /** Erases p for ms (the spell: DURATION_MS). The messages and the hiding go out now. */
    public static void erase(ServerPlayer p, long ms) {
        Data d = data();
        if (d == null) return;
        boolean was = d.until.containsKey(p.getUUID());
        d.until.put(p.getUUID(), System.currentTimeMillis() + ms);
        d.names.put(p.getUUID(), p.getGameProfile().getName());
        d.setDirty();
        snapshot();
        if (!was) {
            broadcast(Component.translatable("ui.pohsmp_core.erased_name.erased", p.getGameProfile().getName()));
            hideAll(p);
        }
        selfOn(p);
    }

    /** Back to the world (time, Blessing, command): «вернулся в мир» to all, Tab and the model back, erased_return, 10 s immune. */
    public static boolean lift(UUID id) {
        Data d = data();
        if (d == null || d.until.remove(id) == null) return false;
        String name = d.names.remove(id);
        d.setDirty();
        snapshot();
        IMMUNE.put(id, System.currentTimeMillis() + IMMUNE_MS);
        ServerPlayer p = server.getPlayerList().getPlayer(id);
        if (p == null) return true;   // offline: comes back quietly at the next login (vanilla join line)
        broadcast(Component.translatable("ui.pohsmp_core.erased_name.returned", name != null && !name.isEmpty() ? name : p.getGameProfile().getName()));
        showAll(p);
        selfOff(p);
        if (p.level() instanceof ServerLevel sl)
            Fx.play(sl, Fx.fx("erased_return").at(p.position()).caster(p).attach(p).text("name", p.getGameProfile().getName()));
        return true;
    }

    private static void broadcast(Component c) {
        Component line = c.copy().withStyle(ChatFormatting.YELLOW);
        for (ServerPlayer p : server.getPlayerList().getPlayers()) p.sendSystemMessage(line);
        server.sendSystemMessage(line);
    }

    // ---------------------------------------------------------------- hiding

    private static void hideAll(ServerPlayer p) {
        var pkt = new ClientboundPlayerInfoRemovePacket(List.of(p.getUUID()));
        for (ServerPlayer o : server.getPlayerList().getPlayers()) if (o != p) o.connection.send(pkt);
        retrack(p);
    }

    private static void showAll(ServerPlayer p) {
        var pkt = ClientboundPlayerInfoUpdatePacket.createPlayerInitializing(List.of(p));
        for (ServerPlayer o : server.getPlayerList().getPlayers()) if (o != p) o.connection.send(pkt);
        retrack(p);
    }

    private static Field entityMap;
    private static Method updatePlayer;

    /** Runs the vanilla tracker for p against every player of its level: with p erased the mixin takes them off, else adds them back. */
    private static void retrack(ServerPlayer p) {
        if (!(p.level() instanceof ServerLevel sl)) return;
        try {
            ChunkMap cm = sl.getChunkSource().chunkMap;
            if (entityMap == null) {
                for (Field f : ChunkMap.class.getDeclaredFields())
                    if (f.getName().equals("f_140150_") || f.getName().equals("entityMap")) entityMap = f;
                entityMap.setAccessible(true);
            }
            Object te = ((it.unimi.dsi.fastutil.ints.Int2ObjectMap<?>) entityMap.get(cm)).get(p.getId());
            if (te == null) return;
            if (updatePlayer == null) {
                for (Method m : te.getClass().getDeclaredMethods())
                    if ((m.getName().equals("m_140497_") || m.getName().equals("updatePlayer")) && m.getParameterCount() == 1) updatePlayer = m;
                updatePlayer.setAccessible(true);
            }
            for (ServerPlayer o : sl.players()) if (o != p) updatePlayer.invoke(te, o);
        } catch (ReflectiveOperationException | RuntimeException ex) {
            PohCore.LOG.error("[pohsmp_core] erased: cannot re-track {}", p.getGameProfile().getName(), ex);
        }
    }

    /** The erased one's own client: the screen, the quiet fx, the icon. */
    private static void selfOn(ServerPlayer p) {
        int ticks = (int) Math.min(Integer.MAX_VALUE, msLeft(p.getUUID()) / 50);
        Net.CH.send(PacketDistributor.PLAYER.with(() -> p), new IlluMsg(IlluMsg.ERASED, p.getId(), Math.max(1, ticks), 0, null, "", 0, 0, 0, 0, 0));
        Integer old = SELF_FX.remove(p.getUUID());
        if (old != null && p.level() instanceof ServerLevel sl) Fx.stop(sl, old, "");
        if (p.level() instanceof ServerLevel sl) SELF_FX.put(p.getUUID(), Fx.play(sl, Fx.fx("erased_self").at(p.position()).caster(p).attach(p).only(p)));
        icon(p, ticks);
    }

    private static void selfOff(ServerPlayer p) {
        Net.CH.send(PacketDistributor.PLAYER.with(() -> p), new IlluMsg(IlluMsg.ERASED, p.getId(), 0, 0, null, "", 0, 0, 0, 0, 0));
        Integer f = SELF_FX.remove(p.getUUID());
        if (f != null && p.level() instanceof ServerLevel sl) Fx.stop(sl, f, "");
        p.removeEffect(Reg.ERASED.get());
    }

    private static void icon(ServerPlayer p, int ticks) {
        MobEffectInstance mi = new MobEffectInstance(Reg.ERASED.get(), Math.max(20, ticks), 0, false, false, true);
        mi.setCurativeItems(new ArrayList<>());
        p.removeEffect(Reg.ERASED.get());
        p.addEffect(mi);
    }

    // ---------------------------------------------------------------- messages about it

    /** True for a vanilla line (join / leave / death / advancement) that names an erased player. */
    public static boolean mute(Component msg) {
        if (SNAPSHOT.isEmpty() || !(msg.getContents() instanceof TranslatableContents tc)) return false;
        String k = tc.getKey();
        if (!(k.startsWith("multiplayer.player.") || k.startsWith("death.") || k.startsWith("chat.type.advancement."))) return false;
        for (Object a : tc.getArgs()) if (a instanceof Component c && names(c)) return true;
        return false;
    }

    /** Does this component (or a part of it) stand for an erased player: its entity hover, its insertion name or its plain name. */
    private static boolean names(Component c) {
        Style s = c.getStyle();
        HoverEvent h = s.getHoverEvent();
        if (h != null) {
            HoverEvent.EntityTooltipInfo info = h.getValue(HoverEvent.Action.SHOW_ENTITY);
            if (info != null && isErased(info.id)) return true;
        }
        Data d = data;
        if (d != null) {
            String ins = s.getInsertion();
            String plain = c.getString();
            for (String n : d.names.values()) if (n.equals(ins) || n.equals(plain)) return true;
        }
        for (Component x : c.getSiblings()) if (names(x)) return true;
        if (c.getContents() instanceof TranslatableContents tc)
            for (Object a : tc.getArgs()) if (a instanceof Component ac && names(ac)) return true;
        return false;
    }

    private static void deny(Player p) {
        long now = System.currentTimeMillis();
        Long last = LAST_DENY.get(p.getUUID());
        if (last != null && now - last < 800) return;
        LAST_DENY.put(p.getUUID(), now);
        p.displayClientMessage(Component.translatable("ui.pohsmp_core.erased_name.not_recognized").withStyle(st -> st.withColor(0xE9E4D8)), true);
    }

    // ---------------------------------------------------------------- events

    static {
        ru.pohsmp.core.illusion.Illusions.onDispel(t -> t instanceof Player && lift(t.getUUID()));   // Blessing
    }

    @SubscribeEvent
    public static void onStarted(ServerStartedEvent e) {
        server = e.getServer();
        data = null;
        data();
        snapshot();
    }

    @SubscribeEvent
    public static void onStopping(ServerStoppingEvent e) {
        data = null;
        server = null;
        SNAPSHOT = Set.of();
        SELF_FX.clear();
        IMMUNE.clear();
    }

    @SubscribeEvent
    public static void onTick(TickEvent.ServerTickEvent e) {
        if (e.phase != TickEvent.Phase.END || SNAPSHOT.isEmpty() || server == null) return;
        long now = System.currentTimeMillis();
        Data d = data();
        if (d == null) return;
        for (UUID id : new ArrayList<>(d.until.keySet())) {
            if (d.until.get(id) <= now) {
                lift(id);
                continue;
            }
            ServerPlayer p = server.getPlayerList().getPlayer(id);
            if (p == null || server.getTickCount() % 20 != 0) continue;
            if (!p.hasEffect(Reg.ERASED.get())) icon(p, (int) (msLeft(id) / 50));   // milk took the icon: back
            // mobs that still hold it as a target let go
            for (Mob m : p.level().getEntitiesOfClass(Mob.class, new AABB(p.blockPosition()).inflate(48), m -> m.getTarget() == p)) {
                m.setTarget(null);
                m.getNavigation().stop();
            }
        }
    }

    /** Somebody joins: the erased are not on its Tab list. An erased one joins: hidden at once, no line (the mixin), its screen back. */
    @SubscribeEvent
    public static void onLogin(PlayerEvent.PlayerLoggedInEvent e) {
        if (!(e.getEntity() instanceof ServerPlayer p) || SNAPSHOT.isEmpty()) return;
        List<UUID> gone = new ArrayList<>();
        for (UUID id : SNAPSHOT) if (!id.equals(p.getUUID())) gone.add(id);
        if (!gone.isEmpty()) p.connection.send(new ClientboundPlayerInfoRemovePacket(gone));
        if (isErased(p)) {
            if (msLeft(p.getUUID()) <= 0) {
                lift(p.getUUID());
                return;
            }
            hideAll(p);
            selfOn(p);
            p.displayClientMessage(Component.translatable("ui.pohsmp_core.erased_name.self_erased", clock(msLeft(p.getUUID())))
                    .withStyle(st -> st.withColor(0xE9E4D8)), false);
        }
    }

    @SubscribeEvent
    public static void onRespawn(PlayerEvent.PlayerRespawnEvent e) {
        if (e.getEntity() instanceof ServerPlayer p && isErased(p)) selfOn(p);
    }

    @SubscribeEvent
    public static void onDimension(PlayerEvent.PlayerChangedDimensionEvent e) {
        if (e.getEntity() instanceof ServerPlayer p && isErased(p)) selfOn(p);
    }

    @SubscribeEvent
    public static void onLogout(PlayerEvent.PlayerLoggedOutEvent e) {
        SELF_FX.remove(e.getEntity().getUUID());
    }

    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void onChat(ServerChatEvent e) {
        if (!isErased(e.getPlayer())) return;
        e.setCanceled(true);
        e.getPlayer().displayClientMessage(Component.translatable("ui.pohsmp_core.erased_name.unheard").withStyle(st -> st.withColor(0xE9E4D8)), true);
    }

    private static final Set<String> TALK = Set.of("msg", "tell", "w", "me", "teammsg", "tm", "say");

    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void onCommand(CommandEvent e) {
        if (SNAPSHOT.isEmpty()) return;
        CommandSourceStack src = e.getParseResults().getContext().getSource();
        if (!(src.getEntity() instanceof ServerPlayer p) || !isErased(p)) return;
        String s = e.getParseResults().getReader().getString().trim();
        if (s.startsWith("/")) s = s.substring(1);
        String root = s.split(" ", 2)[0].toLowerCase(java.util.Locale.ROOT);
        if (root.contains(":")) root = root.substring(root.indexOf(':') + 1);
        if (!TALK.contains(root)) return;
        e.setCanceled(true);
        p.displayClientMessage(Component.translatable("ui.pohsmp_core.erased_name.unheard").withStyle(st -> st.withColor(0xE9E4D8)), true);
    }

    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void onTarget(LivingChangeTargetEvent e) {
        if (!SNAPSHOT.isEmpty() && isErased(e.getNewTarget())) e.setCanceled(true);
    }

    /** Its blows are a quarter. */
    @SubscribeEvent(priority = EventPriority.LOW)
    public static void onHurt(LivingHurtEvent e) {
        if (!SNAPSHOT.isEmpty() && isErased(e.getSource().getEntity())) e.setAmount(e.getAmount() * 0.25f);
    }

    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void onHeal(LivingHealEvent e) {
        if (!SNAPSHOT.isEmpty() && isErased(e.getEntity())) e.setCanceled(true);
    }

    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void onTotem(LivingUseTotemEvent e) {
        if (!SNAPSHOT.isEmpty() && isErased(e.getEntity())) e.setCanceled(true);
    }

    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void onPickup(EntityItemPickupEvent e) {
        if (!SNAPSHOT.isEmpty() && isErased(e.getEntity())) e.setCanceled(true);
    }

    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void onXp(net.minecraftforge.event.entity.player.PlayerXpEvent.PickupXp e) {
        if (!SNAPSHOT.isEmpty() && isErased(e.getEntity())) e.setCanceled(true);
    }

    // «Мир его не признаёт» (owner 19.11): no block use at all, no placing, no breaking - not even its own

    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void onUseBlock(PlayerInteractEvent.RightClickBlock e) {
        if (SNAPSHOT.isEmpty() || !isErased(e.getEntity())) return;
        e.setUseBlock(Event.Result.DENY);   // the item in hand still works (a scroll, a staff), but not on the block
        if (!e.getLevel().isClientSide) deny(e.getEntity());
    }

    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void onHitBlock(PlayerInteractEvent.LeftClickBlock e) {
        if (SNAPSHOT.isEmpty() || !isErased(e.getEntity())) return;
        e.setCanceled(true);
        if (!e.getLevel().isClientSide) deny(e.getEntity());
    }

    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void onBreak(BlockEvent.BreakEvent e) {
        if (SNAPSHOT.isEmpty() || !isErased(e.getPlayer())) return;
        e.setCanceled(true);
        deny(e.getPlayer());
    }

    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void onPlace(BlockEvent.EntityPlaceEvent e) {
        if (SNAPSHOT.isEmpty() || !isErased(e.getEntity())) return;
        e.setCanceled(true);
        if (e.getEntity() instanceof Player p) deny(p);
    }

    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void onBucket(FillBucketEvent e) {
        if (SNAPSHOT.isEmpty() || !isErased(e.getEntity())) return;
        e.setCanceled(true);
        deny(e.getEntity());
    }

    // ---------------------------------------------------------------- commands

    @SubscribeEvent
    public static void onCommands(RegisterCommandsEvent e) {
        e.getDispatcher().register(Commands.literal("pohsmp").requires(s -> s.hasPermission(2))
                .then(Commands.literal("erase")
                        .then(Commands.literal("list").executes(c -> list(c.getSource())))
                        .then(Commands.literal("clear").then(Commands.argument("player", EntityArgument.player())
                                .executes(c -> clear(c.getSource(), EntityArgument.getPlayer(c, "player")))))
                        .then(Commands.literal("set").then(Commands.argument("player", EntityArgument.player())
                                .then(Commands.argument("seconds", IntegerArgumentType.integer(1, 86400))
                                        .executes(c -> set(c.getSource(), EntityArgument.getPlayer(c, "player"),
                                                IntegerArgumentType.getInteger(c, "seconds"))))))));
    }

    private static int list(CommandSourceStack src) {
        Data d = data();
        if (d == null || d.until.isEmpty()) {
            src.sendSuccess(() -> Component.translatable("ui.pohsmp_core.erased_name.list_empty"), false);
            return 0;
        }
        List<String> parts = new ArrayList<>();
        d.until.forEach((u, end) -> parts.add(d.names.getOrDefault(u, u.toString()) + " (" + clock(Math.max(0, end - System.currentTimeMillis())) + ")"));
        src.sendSuccess(() -> Component.translatable("ui.pohsmp_core.erased_name.list", parts.size(), String.join(", ", parts)), false);
        return parts.size();
    }

    private static int clear(CommandSourceStack src, ServerPlayer p) {
        if (!lift(p.getUUID())) {
            src.sendFailure(Component.translatable("ui.pohsmp_core.erased_name.not_erased", p.getGameProfile().getName()));
            return 0;
        }
        src.sendSuccess(() -> Component.translatable("ui.pohsmp_core.erased_name.cleared", p.getGameProfile().getName()), true);
        return 1;
    }

    private static int set(CommandSourceStack src, ServerPlayer p, int seconds) {
        erase(p, seconds * 1000L);
        src.sendSuccess(() -> Component.literal("Erased: " + p.getGameProfile().getName() + " for " + seconds + " s"), true);
        return 1;
    }

    public static String clock(long ms) {
        long s = (ms + 999) / 1000;
        return String.format(java.util.Locale.ROOT, "%d:%02d", s / 60, s % 60);
    }
}
