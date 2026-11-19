package ru.pohsmp.core.illusion;

import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.StringTag;
import net.minecraft.nbt.Tag;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.level.saveddata.SavedData;
import net.minecraftforge.event.entity.player.PlayerInteractEvent;
import net.minecraftforge.event.server.ServerStartedEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.Reg;

/**
 * T22, owner 19.11: allies of an Illusions caster are only the players it chose itself - Shift + right click on a player with the
 * Prism of Illusions in hand adds them, the same again takes them off. Kept in the world (survives restarts and relogs).
 * One way: the caster's choice says whom ITS illusions spare and who sees through them.
 */
public final class IllusionAllies {
    private IllusionAllies() {}

    private static final class Data extends SavedData {
        final Map<UUID, Set<UUID>> allies = new HashMap<>();

        static Data load(CompoundTag t) {
            Data d = new Data();
            CompoundTag a = t.getCompound("allies");
            for (String k : a.getAllKeys()) {
                Set<UUID> s = new HashSet<>();
                for (Tag x : a.getList(k, Tag.TAG_STRING)) {
                    try {
                        s.add(UUID.fromString(x.getAsString()));
                    } catch (IllegalArgumentException ignored) {}
                }
                try {
                    if (!s.isEmpty()) d.allies.put(UUID.fromString(k), s);
                } catch (IllegalArgumentException ignored) {}
            }
            return d;
        }

        @Override
        public CompoundTag save(CompoundTag t) {
            CompoundTag a = new CompoundTag();
            allies.forEach((k, s) -> {
                ListTag l = new ListTag();
                for (UUID u : s) l.add(StringTag.valueOf(u.toString()));
                a.put(k.toString(), l);
            });
            t.put("allies", a);
            return t;
        }
    }

    private static Data data;

    private static Data data(MinecraftServer server) {
        if (data == null && server != null) data = server.overworld().getDataStorage().computeIfAbsent(Data::load, Data::new, "pohsmp_illusion_allies");
        return data;
    }

    /** Did caster choose ally? (Server side; false before the world is up.) */
    public static boolean chose(UUID caster, UUID ally) {
        Data d = data;
        if (d == null) return false;
        Set<UUID> s = d.allies.get(caster);
        return s != null && s.contains(ally);
    }

    @SubscribeEvent
    public static void onStarted(ServerStartedEvent e) {
        data = null;
        data(e.getServer());
    }

    @SubscribeEvent
    public static void onStopping(ServerStoppingEvent e) {
        data = null;
    }

    /** Shift + right click on a player with the Prism: ally on / off. */
    @SubscribeEvent(priority = EventPriority.HIGH)
    public static void onInteract(PlayerInteractEvent.EntityInteract e) {
        if (!(e.getEntity() instanceof ServerPlayer p) || !(e.getTarget() instanceof ServerPlayer t)) return;
        if (!p.isShiftKeyDown() || !e.getItemStack().is(Reg.ILLUSION_PRISM.get())) return;
        e.setCanceled(true);
        e.setCancellationResult(InteractionResult.SUCCESS);
        Data d = data(p.getServer());
        if (d == null) return;
        Set<UUID> s = d.allies.computeIfAbsent(p.getUUID(), k -> new HashSet<>());
        boolean added = s.add(t.getUUID());
        if (!added) s.remove(t.getUUID());
        if (s.isEmpty()) d.allies.remove(p.getUUID());
        d.setDirty();
        p.displayClientMessage(Component.translatable("ui.pohsmp_core.illusion.ally_" + (added ? "added" : "removed"), t.getDisplayName())
                .withStyle(st -> st.withColor(Reg.ILLUSION_COLOR)), true);
        t.displayClientMessage(Component.translatable("ui.pohsmp_core.illusion.ally_you_" + (added ? "added" : "removed"), p.getDisplayName())
                .withStyle(st -> st.withColor(Reg.ILLUSION_COLOR)), true);
        p.level().playSound(null, p.getX(), p.getY() + 1, p.getZ(), SoundEvents.AMETHYST_BLOCK_CHIME, SoundSource.PLAYERS, 1f, added ? 1.5f : 0.8f);
    }
}
