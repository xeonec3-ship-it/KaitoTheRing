package ru.pohsmp.core.boss;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.tags.DamageTypeTags;
import net.minecraftforge.event.entity.living.LivingAttackEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;

/**
 * Watchers of the scenes that take their controls (intro, death: BossNet.SCENE_LOCK_INPUT) are not hurt meanwhile — they cannot
 * move. The special scenes do not lock and do not protect: the fight goes on (owner: «бой в роликах не замораживается»).
 */
public final class BossScenes {
    private BossScenes() {}

    private static final Map<UUID, Long> PROTECTED = new HashMap<>();

    static void protect(ServerPlayer p, int ticks) {
        PROTECTED.put(p.getUUID(), p.level().getGameTime() + ticks);
    }

    static void unprotect(ServerPlayer p) {
        PROTECTED.remove(p.getUUID());
    }

    public static boolean protectedNow(ServerPlayer p) {
        Long until = PROTECTED.get(p.getUUID());
        if (until == null) return false;
        if (p.level().getGameTime() > until) {
            PROTECTED.remove(p.getUUID());
            return false;
        }
        return true;
    }

    public static final class Events {
        private Events() {}

        @SubscribeEvent(priority = EventPriority.HIGHEST)
        public static void onAttack(LivingAttackEvent e) {
            if (PROTECTED.isEmpty() || !(e.getEntity() instanceof ServerPlayer p)) return;
            if (protectedNow(p) && !e.getSource().is(DamageTypeTags.BYPASSES_INVULNERABILITY)) e.setCanceled(true);
        }

        @SubscribeEvent
        public static void onLogout(PlayerEvent.PlayerLoggedOutEvent e) {
            PROTECTED.remove(e.getEntity().getUUID());
        }

        @SubscribeEvent
        public static void onStopping(ServerStoppingEvent e) {
            PROTECTED.clear();
        }
    }
}
