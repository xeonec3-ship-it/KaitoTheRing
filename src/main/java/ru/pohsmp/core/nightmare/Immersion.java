package ru.pohsmp.core.nightmare;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.living.LivingDeathEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.network.PacketDistributor;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.ServerConfig;
import ru.pohsmp.core.net.IlluMsg;
import ru.pohsmp.core.net.Net;

/**
 * T25 «Погружение» (owner 19.11): the spells of the Nightmares school turn the world around the victim into a nightmare, only for it.
 * Stage 1 shadows, 2 hallucinations, 3 the nightmare itself. A stage falls by one when the victim was not hit by a school spell for
 * [nightmare] stageDecaySeconds; «Стойкость рассудка» (nightmare_magic_resist) makes the stages come slower and go faster; Blessing
 * takes it all. A spell may hold a stage for a while (the floor it cannot fall below). The stage goes to the victim's client
 * (IlluMsg IMMERSION) and shows as the effect icon.
 */
public final class Immersion {
    private Immersion() {}

    public static final int MAX = 3;

    private static final class State {
        /** progress towards the stages: stage = floor(progress) */
        double progress;
        long lastHit, floorUntil;
        int floor, sent = -1;
    }

    private static final Map<UUID, State> STATES = new HashMap<>();
    private static long now;

    public static long now() {
        return now;
    }

    /** The stage of this player now (0 = not immersed). */
    public static int stage(LivingEntity p) {
        State s = p == null ? null : STATES.get(p.getUUID());
        return s == null ? 0 : stage(s);
    }

    private static int stage(State s) {
        int st = Math.min(MAX, (int) Math.floor(s.progress + 1e-6));
        return now < s.floorUntil ? Math.max(st, s.floor) : st;
    }

    private static double resist(LivingEntity p) {
        var a = p.getAttribute(Reg.NIGHTMARE_RESIST.get());
        return a == null ? 1 : p.getAttributeValue(Reg.NIGHTMARE_RESIST.get());
    }

    /** A school spell hits v: `stages` deeper (resistance 1 = as is, 2 = half, 0 = double), and the fall timer starts again. */
    public static void deepen(ServerPlayer v, double stages) {
        if (v.isCreative() || v.isSpectator()) return;
        State s = STATES.computeIfAbsent(v.getUUID(), k -> new State());
        double k = Math.max(0.25, Math.min(2, 2 - resist(v)));
        s.progress = Math.min(MAX + 0.999, s.progress + stages * k);
        s.lastHit = now;
        sync(v, s);
    }

    /** v is at least at `stage` for `ticks` (the spell holds it), and the fall timer starts again. */
    public static void hold(ServerPlayer v, int stage, int ticks) {
        if (v.isCreative() || v.isSpectator()) return;
        State s = STATES.computeIfAbsent(v.getUUID(), k -> new State());
        s.floor = Math.max(now < s.floorUntil ? s.floor : 0, Math.min(MAX, stage));
        s.floorUntil = Math.max(s.floorUntil, now + ticks);
        s.progress = Math.max(s.progress, s.floor);
        s.lastHit = now;
        sync(v, s);
    }

    /** Keeps v's stage from falling now (a spell still holds it: the zone of «Ночь без рассвета»). */
    public static void touch(ServerPlayer v) {
        State s = STATES.get(v.getUUID());
        if (s != null) s.lastHit = now;
    }

    /** All of it gone (Blessing, death, the caster of the Mythic died). */
    public static boolean clear(LivingEntity v) {
        State s = STATES.remove(v.getUUID());
        if (s == null) return false;
        if (v instanceof ServerPlayer sp) send(sp, 0, 0);
        v.removeEffect(Reg.IMMERSION.get());
        return true;
    }

    private static void sync(ServerPlayer v, State s) {
        int st = stage(s);
        if (st == s.sent) return;
        s.sent = st;
        send(v, st, (int) Math.max(0, s.floorUntil - now));
        if (st <= 0) v.removeEffect(Reg.IMMERSION.get());
        else v.addEffect(new MobEffectInstance(Reg.IMMERSION.get(), -1, st - 1, false, false, true));
    }

    private static void send(ServerPlayer v, int stage, int ticks) {
        Net.CH.send(PacketDistributor.PLAYER.with(() -> v), new IlluMsg(IlluMsg.IMMERSION, v.getId(), ticks, stage, null, "", 0, 0, 0, 0, 0));
    }

    static {
        ru.pohsmp.core.illusion.Illusions.onDispel(t -> t instanceof Player && clear(t));   // Blessing takes it all
    }

    @SubscribeEvent
    public static void onTick(TickEvent.ServerTickEvent e) {
        if (e.phase != TickEvent.Phase.END) return;
        now++;
        if (STATES.isEmpty() || now % 10 != 0) return;
        var server = e.getServer();
        for (var it = STATES.entrySet().iterator(); it.hasNext(); ) {
            var en = it.next();
            State s = en.getValue();
            ServerPlayer v = server.getPlayerList().getPlayer(en.getKey());
            if (v == null) {
                it.remove();
                continue;
            }
            double r = Math.max(0.5, Math.min(2, resist(v)));
            long decay = Math.round(ServerConfig.get(ServerConfig.IM_DECAY) * 20 / r);
            if (now >= s.floorUntil && now - s.lastHit >= decay) {
                s.progress = Math.floor(s.progress + 1e-6) - 1;
                s.lastHit = now;
            }
            if (s.progress < 1 && now >= s.floorUntil) {
                it.remove();
                send(v, 0, 0);
                v.removeEffect(Reg.IMMERSION.get());
                continue;
            }
            sync(v, s);
        }
    }

    @SubscribeEvent
    public static void onDeath(LivingDeathEvent e) {
        if (e.getEntity() instanceof ServerPlayer sp) clear(sp);
    }

    @SubscribeEvent
    public static void onLogout(PlayerEvent.PlayerLoggedOutEvent e) {
        STATES.remove(e.getEntity().getUUID());
    }

    @SubscribeEvent
    public static void onRespawn(PlayerEvent.PlayerRespawnEvent e) {
        if (e.getEntity() instanceof ServerPlayer sp) send(sp, 0, 0);
    }

    @SubscribeEvent
    public static void onStopping(ServerStoppingEvent e) {
        STATES.clear();
    }
}
