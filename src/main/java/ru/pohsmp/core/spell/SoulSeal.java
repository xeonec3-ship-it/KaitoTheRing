package ru.pohsmp.core.spell;

import com.mojang.brigadier.arguments.StringArgumentType;
import io.redspace.ironsspellbooks.api.events.SpellPreCastEvent;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.effect.MobEffect;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.saveddata.SavedData;
import net.minecraftforge.event.RegisterCommandsEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.registries.ForgeRegistries;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.fx.Fx;

/**
 * T21, "Soul Seal": the player may not cast at all, for good — through death, logout and server restarts. The flag lives in the player's
 * persisted data ({@link Player#PERSISTED_NBT_TAG}), the list of the sealed in the overworld's saved data (for /pohsmp soulseal list and
 * for clearing someone offline: the flag is dropped when he logs in). The visible side: the endless effect pohsmp_core:soul_seal (milk and
 * totems do not take it: put back each second), the small seal on the chest (fx soul_seal_mark), MNA silenced. Every Iron's cast — books,
 * scrolls, staffs, our spells, the joint cast — is cancelled with «Душа запечатана» and a flash of the seal (fx soul_seal_deny).
 * Only "Blessing" ({@link #clear}) or an operator takes it off.
 */
public final class SoulSeal {
    private SoulSeal() {}

    private static final String KEY = "pohsmp_soul_seal";
    private static final ResourceLocation MNA_SILENCE = new ResourceLocation("mna", "silence");
    private static final int MARK_TICKS = 72000;

    public static boolean sealed(Player p) {
        return p.getPersistentData().getCompound(Player.PERSISTED_NBT_TAG).getBoolean(KEY);
    }

    private static void flag(Player p, boolean on) {
        CompoundTag root = p.getPersistentData();
        CompoundTag kept = root.getCompound(Player.PERSISTED_NBT_TAG);
        if (on) kept.putBoolean(KEY, true);
        else kept.remove(KEY);
        root.put(Player.PERSISTED_NBT_TAG, kept);
    }

    /** Seals the player's soul (the rite took effect). */
    public static void seal(ServerPlayer p) {
        flag(p, true);
        data(p.server).put(p.getUUID(), p.getGameProfile().getName());
        show(p);
    }

    /** Takes the seal off (Blessing, operator). Returns false if there was none. */
    public static boolean clear(ServerPlayer p) {
        boolean was = sealed(p) || data(p.server).sealed.containsKey(p.getUUID());
        flag(p, false);
        data(p.server).remove(p.getUUID());
        p.removeEffect(Reg.SOUL_SEAL.get());
        Integer m = MARKS.remove(p.getUUID());
        if (m != null) Fx.stop(p.serverLevel(), m, "");
        return was;
    }

    // ---- what the others see ----

    /** player -> the running chest mark */
    private static final Map<UUID, Integer> MARKS = new HashMap<>();
    private static final Map<UUID, Long> LAST_DENY = new HashMap<>();

    /** The effect and the chest mark (again after respawn, login, a change of dimension). */
    private static void show(ServerPlayer p) {
        p.addEffect(new MobEffectInstance(Reg.SOUL_SEAL.get(), MobEffectInstance.INFINITE_DURATION, 0, false, false, true));
        Integer old = MARKS.remove(p.getUUID());
        if (old != null) Fx.stop(p.serverLevel(), old, "");
        MARKS.put(p.getUUID(), Fx.play(p.serverLevel(), Fx.fx("soul_seal_mark").at(p.position()).caster(p).attach(p).duration(MARK_TICKS).not(p)));   // owner 19.11: the mark in its own face got in the way
    }

    private static void deny(ServerPlayer p) {
        long now = p.level().getGameTime();
        Long last = LAST_DENY.get(p.getUUID());
        if (last != null && now - last < 10) return;
        LAST_DENY.put(p.getUUID(), now);
        p.displayClientMessage(Component.translatable("ui.pohsmp_core.soul_seal.denied").withStyle(s -> s.withColor(0x9A7BFF)), true);
        ServerLevel sl = p.serverLevel();
        Fx.play(sl, Fx.fx("soul_seal_deny").at(p.position()).caster(p).attach(p));
        sl.playSound(null, p.getX(), p.getY(), p.getZ(), SoundEvents.CHAIN_PLACE, SoundSource.PLAYERS, 1f, 0.6f);
        sl.playSound(null, p.getX(), p.getY(), p.getZ(), SoundEvents.AMETHYST_BLOCK_RESONATE, SoundSource.PLAYERS, 0.8f, 0.5f);
    }

    // ---- saved list ----

    private static final class Data extends SavedData {
        final Map<UUID, String> sealed = new HashMap<>();

        void put(UUID u, String name) {
            sealed.put(u, name);
            setDirty();
        }

        void remove(UUID u) {
            if (sealed.remove(u) != null) setDirty();
        }

        static Data load(CompoundTag t) {
            Data d = new Data();
            CompoundTag s = t.getCompound("sealed");
            for (String k : s.getAllKeys()) {
                try {
                    d.sealed.put(UUID.fromString(k), s.getString(k));
                } catch (IllegalArgumentException ignored) {
                }
            }
            return d;
        }

        @Override
        public CompoundTag save(CompoundTag t) {
            CompoundTag s = new CompoundTag();
            sealed.forEach((u, n) -> s.putString(u.toString(), n));
            t.put("sealed", s);
            return t;
        }
    }

    private static Data data(MinecraftServer server) {
        return server.overworld().getDataStorage().computeIfAbsent(Data::load, Data::new, "pohsmp_soul_seal");
    }

    // ---- events ----

    public static final class Events {
        private Events() {}

        /** Before the joint cast and everyone else: a sealed soul casts nothing. */
        @SubscribeEvent(priority = EventPriority.HIGHEST)
        public static void onPreCast(SpellPreCastEvent e) {
            if (e.getEntity() instanceof ServerPlayer sp && sealed(sp)) {
                e.setCanceled(true);
                deny(sp);
            }
        }

        @SubscribeEvent
        public static void onLogin(PlayerEvent.PlayerLoggedInEvent e) {
            if (!(e.getEntity() instanceof ServerPlayer sp)) return;
            boolean listed = data(sp.server).sealed.containsKey(sp.getUUID());
            if (sealed(sp) && !listed) SoulSeal.clear(sp);   // an operator cleared it while he was away
            else if (sealed(sp)) show(sp);
        }

        @SubscribeEvent
        public static void onRespawn(PlayerEvent.PlayerRespawnEvent e) {
            if (e.getEntity() instanceof ServerPlayer sp && sealed(sp)) show(sp);
        }

        @SubscribeEvent
        public static void onDimension(PlayerEvent.PlayerChangedDimensionEvent e) {
            if (e.getEntity() instanceof ServerPlayer sp && sealed(sp)) show(sp);
        }

        @SubscribeEvent
        public static void onLogout(PlayerEvent.PlayerLoggedOutEvent e) {
            Integer m = MARKS.remove(e.getEntity().getUUID());
            if (m != null && e.getEntity().level() instanceof ServerLevel sl) Fx.stop(sl, m, "");
            LAST_DENY.remove(e.getEntity().getUUID());
        }

        /** Each second: the effect back if milk or a totem took it; MNA silenced (as in the Closing of Space). */
        @SubscribeEvent
        public static void onPlayerTick(TickEvent.PlayerTickEvent e) {
            if (e.phase != TickEvent.Phase.END || !(e.player instanceof ServerPlayer sp) || sp.tickCount % 20 != 0 || !sealed(sp)) return;
            if (!sp.hasEffect(Reg.SOUL_SEAL.get())) show(sp);
            if (sp.tickCount % 100 == 0 && ForgeRegistries.MOB_EFFECTS.containsKey(MNA_SILENCE)) {
                MobEffect s = ForgeRegistries.MOB_EFFECTS.getValue(MNA_SILENCE);
                if (s != null) sp.addEffect(new MobEffectInstance(s, 120, 0, false, false, false));
            }
        }

        @SubscribeEvent
        public static void onCommands(RegisterCommandsEvent e) {
            e.getDispatcher().register(Commands.literal("pohsmp").requires(s -> s.hasPermission(2))
                    .then(Commands.literal("soulseal")
                            .then(Commands.literal("list").executes(c -> list(c.getSource())))
                            .then(Commands.literal("clear").then(Commands.argument("player", StringArgumentType.word())
                                    .suggests((c, b) -> net.minecraft.commands.SharedSuggestionProvider.suggest(data(c.getSource().getServer()).sealed.values(), b))
                                    .executes(c -> clear(c.getSource(), StringArgumentType.getString(c, "player")))))));
        }

        private static int list(CommandSourceStack src) {
            Map<UUID, String> s = data(src.getServer()).sealed;
            if (s.isEmpty()) {
                src.sendSuccess(() -> Component.translatable("ui.pohsmp_core.soul_seal.list_empty"), false);
                return 0;
            }
            String names = String.join(", ", new java.util.TreeSet<>(s.values()));
            src.sendSuccess(() -> Component.translatable("ui.pohsmp_core.soul_seal.list", s.size(), names), false);
            return s.size();
        }

        private static int clear(CommandSourceStack src, String name) {
            MinecraftServer server = src.getServer();
            ServerPlayer p = server.getPlayerList().getPlayerByName(name);
            if (p != null) {
                if (!SoulSeal.clear(p)) {
                    src.sendFailure(Component.translatable("ui.pohsmp_core.soul_seal.not_sealed", name));
                    return 0;
                }
                p.displayClientMessage(Component.translatable("ui.pohsmp_core.soul_seal.freed").withStyle(s -> s.withColor(Reg.DIVINE_COLOR)), true);
                src.sendSuccess(() -> Component.translatable("ui.pohsmp_core.soul_seal.cleared", name), true);
                return 1;
            }
            Data d = data(server);   // offline: off the list now, the flag goes at his next login
            UUID u = d.sealed.entrySet().stream().filter(en -> en.getValue().equalsIgnoreCase(name)).map(Map.Entry::getKey).findFirst().orElse(null);
            if (u == null) {
                src.sendFailure(Component.translatable("ui.pohsmp_core.soul_seal.not_sealed", name));
                return 0;
            }
            d.remove(u);
            src.sendSuccess(() -> Component.translatable("ui.pohsmp_core.soul_seal.cleared", name), true);
            return 1;
        }
    }
}
