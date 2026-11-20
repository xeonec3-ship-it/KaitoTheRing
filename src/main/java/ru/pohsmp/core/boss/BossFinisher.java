package ru.pohsmp.core.boss;

import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;
import java.util.UUID;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.RelativeMovement;
import net.minecraft.world.item.Items;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.living.LivingAttackEvent;
import net.minecraftforge.event.entity.living.LivingDamageEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.spell.TargetPose;

/**
 * The finisher (T26, T27; owner 20.11): a blow of the boss that would kill a player is cancelled; instead the victim is held (its
 * pose, the boss's animation, the victim's own camera) and dies at the boss's kill tick with the boss's death message
 * (death.attack.pohsmp_core.<boss>_finisher). A totem in hand: no finisher, the totem works as usual. Not more often than
 * [bosses_common] finisherCooldown per boss (a second player dying meanwhile dies the usual way). Meanwhile the victim cannot act and
 * cannot be hurt by anyone else, the boss attacks no one (AI off) but can be hit.
 */
public final class BossFinisher {
    private BossFinisher() {}

    private static final class Hold {
        final PohBoss boss;
        final ServerPlayer victim;
        final Vec3 from;
        final boolean noGravity;
        int t;
        boolean killing;

        Hold(PohBoss boss, ServerPlayer victim) {
            this.boss = boss;
            this.victim = victim;
            this.from = victim.position();
            this.noGravity = victim.isNoGravity();
        }
    }

    private static final Map<UUID, Hold> HOLDS = new HashMap<>();

    public static boolean held(LivingEntity e) {
        return HOLDS.containsKey(e.getUUID());
    }

    private static boolean hasTotem(ServerPlayer p) {
        return p.getMainHandItem().is(Items.TOTEM_OF_UNDYING) || p.getOffhandItem().is(Items.TOTEM_OF_UNDYING);
    }

    /** The boss behind a damage source (direct, or the owner of its projectile / summon), or null. */
    private static PohBoss bossOf(DamageSource src) {
        if (src.getEntity() instanceof PohBoss b) return b;
        if (src.getDirectEntity() instanceof PohBoss b) return b;
        return null;
    }

    private static void start(PohBoss boss, ServerPlayer victim) {
        BossCore core = boss.bossCore();
        long now = victim.level().getGameTime();
        core.finisherUsed(now);
        Hold h = new Hold(boss, victim);
        HOLDS.put(victim.getUUID(), h);
        victim.setNoGravity(true);
        victim.stopUsingItem();
        String anim = boss.finisherVictimAnim();
        if (anim != null) BossNet.tracking(victim, new BossNet.Msg(BossNet.POSE).ints(victim.getId(), 1, 0, 0).str(anim, ""));
        else TargetPose.hold(victim);
        Mob m = boss.bossMob();
        m.setTarget(null);
        core.lock(boss.finisherTicks(), true, false);
        boss.onFinisherStart(victim);
    }

    private static void release(Hold h) {
        h.victim.setNoGravity(h.noGravity);
        h.victim.fallDistance = 0;
        String anim = h.boss.finisherVictimAnim();
        if (anim != null) BossNet.tracking(h.victim, new BossNet.Msg(BossNet.POSE).ints(h.victim.getId(), 0, 0, 0).str(anim, ""));
        else TargetPose.release(h.victim);
    }

    private static void kill(Hold h) {
        ServerPlayer v = h.victim;
        if (!(v.level() instanceof ServerLevel sl) || !v.isAlive()) return;
        DamageSource src = h.boss.bossCore().finisherDamage(sl);
        h.killing = true;
        v.invulnerableTime = 0;
        v.setAbsorptionAmount(0);
        v.hurt(src, Float.MAX_VALUE / 4);
        if (v.isAlive() && !v.isCreative() && !v.isSpectator()) {   // a resistance or another mod kept it alive: the finisher still ends it
            v.setHealth(0);
            v.die(src);
        }
        h.killing = false;
    }

    public static final class Events {
        private Events() {}

        /** Last word on the damage (after armour, absorption and other mods): lethal from a boss with a finisher → the finisher. */
        @SubscribeEvent(priority = EventPriority.LOWEST)
        public static void onDamage(LivingDamageEvent e) {
            if (!(e.getEntity() instanceof ServerPlayer victim) || e.isCanceled()) return;
            Hold held = HOLDS.get(victim.getUUID());
            if (held != null) {
                if (!held.killing) e.setCanceled(true);
                return;
            }
            PohBoss boss = bossOf(e.getSource());
            if (boss == null || victim.isCreative() || victim.isSpectator()) return;
            if (e.getAmount() < victim.getHealth()) return;
            if (hasTotem(victim) || !boss.bossCore().finisherReady(victim.level().getGameTime())) return;
            e.setCanceled(true);
            start(boss, victim);
        }

        /** The held victim: nobody else hurts it, it hurts no one. */
        @SubscribeEvent(priority = EventPriority.HIGHEST)
        public static void onAttack(LivingAttackEvent e) {
            if (HOLDS.isEmpty()) return;
            Hold h = HOLDS.get(e.getEntity().getUUID());
            if (h != null && !h.killing) {
                e.setCanceled(true);
                return;
            }
            if (e.getSource().getEntity() instanceof ServerPlayer p && HOLDS.containsKey(p.getUUID())) e.setCanceled(true);
        }

        @SubscribeEvent
        public static void onCast(io.redspace.ironsspellbooks.api.events.SpellPreCastEvent e) {
            if (!HOLDS.isEmpty() && HOLDS.containsKey(e.getEntity().getUUID())) e.setCanceled(true);
        }

        @SubscribeEvent
        public static void onServerTick(TickEvent.ServerTickEvent e) {
            if (e.phase != TickEvent.Phase.END || HOLDS.isEmpty()) return;
            java.util.List<Hold> due = new java.util.ArrayList<>();
            Iterator<Hold> it = HOLDS.values().iterator();
            while (it.hasNext()) {
                Hold h = it.next();
                Mob m = h.boss.bossMob();
                boolean gone = !h.victim.isAlive() || h.victim.isRemoved() || !m.isAlive() || m.isRemoved() || h.victim.level() != m.level();
                if (gone) {   // the boss died / left meanwhile: the victim is free (with the health it had)
                    release(h);
                    it.remove();
                    continue;
                }
                h.t++;
                Vec3 p = h.boss.finisherVictimPos(h.victim, h.t, h.from);
                h.victim.connection.teleport(p.x, p.y, p.z, 0, 0, java.util.EnumSet.of(RelativeMovement.X_ROT, RelativeMovement.Y_ROT));
                h.victim.setDeltaMovement(Vec3.ZERO);
                h.victim.fallDistance = 0;
                h.boss.onFinisherTick(h.victim, h.t);
                if (h.t >= h.boss.finisherKillTick()) due.add(h);
            }
            for (Hold h : due) {   // still in HOLDS during its own death blow (nobody else's damage gets in)
                release(h);
                kill(h);
                HOLDS.remove(h.victim.getUUID());
            }
        }

        @SubscribeEvent
        public static void onLogout(PlayerEvent.PlayerLoggedOutEvent e) {
            Hold h = HOLDS.remove(e.getEntity().getUUID());
            if (h != null) release(h);
        }

        @SubscribeEvent
        public static void onStopping(ServerStoppingEvent e) {
            HOLDS.clear();
        }
    }
}
