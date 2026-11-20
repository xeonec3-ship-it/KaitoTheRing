package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.util.Utils;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.entity.living.LivingAttackEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.DivineEvents;

/**
 * Higher: the target is shut in a mirror cube for 6 s. Whatever it strikes or casts at others hits itself instead,
 * nothing from outside can reach it, and it cannot leave the cube.
 */
public class MirrorPrisonSpell extends HigherSpell {
    public static final String PATH = "mirror_prison";
    private static final int LIFE = 120;
    private static final double HALF = 1.5, H = 3;

    private static final class Cell {
        LivingEntity caster, t;
        Vec3 c;
        long until;
        int fx = -1;
    }

    private static final Map<UUID, Cell> CELLS = new HashMap<>();
    private static final ThreadLocal<Boolean> REFLECT = ThreadLocal.withInitial(() -> false);

    public MirrorPrisonSpell() {
        super(PATH, 0);
    }

    @Override public CastType getCastType() { return CastType.INSTANT; }
    @Override public Optional<SoundEvent> getCastStartSound() { return Optional.empty(); }
    @Override public Optional<SoundEvent> getCastFinishSound() { return Optional.of(SoundEvents.ILLUSIONER_MIRROR_MOVE); }

    @Override
    public List<MutableComponent> getUniqueInfo(int spellLevel, LivingEntity caster) {
        return List.of(ui("time", LIFE / 20), ui("reflect"), ui("sealed"));
    }

    @Override
    public boolean checkPreCastConditions(Level level, int spellLevel, LivingEntity entity, MagicData md) {
        return Utils.preCastTargetHelper(level, entity, md, this, 24, 0.35f);
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            LivingEntity t = target(sl, md);
            int life = t == null ? 0 : ru.pohsmp.core.boss.BossGuard.mirrorPrisonTicks(t, LIFE);   // cult bosses: 1 s
            if (t != null && t.isAlive() && !CELLS.containsKey(t.getUUID()) && life > 0) {
                if (t.isPassenger()) t.stopRiding();
                Cell cell = new Cell();
                cell.caster = caster;
                cell.t = t;
                cell.c = t.position();
                cell.until = sl.getGameTime() + life;
                Vec3 c = cell.c;
                // the mirror cage (owner, 19.11.2026: new look instead of blue glass blocks): seal, mirror panes, glints — fx/mirror_prison.json
                cell.fx = ru.pohsmp.core.fx.Fx.play(sl, ru.pohsmp.core.fx.Fx.fx("mirror_prison").at(c).yaw(0));
                CELLS.put(t.getUUID(), cell);
                sl.playSound(null, c.x, c.y, c.z, SoundEvents.GLASS_PLACE, SoundSource.PLAYERS, 2f, 0.6f);
                sl.playSound(null, c.x, c.y, c.z, SoundEvents.AMETHYST_BLOCK_RESONATE, SoundSource.PLAYERS, 2f, 0.8f);
                sl.playSound(null, c.x, c.y, c.z, SoundEvents.ILLUSIONER_MIRROR_MOVE, SoundSource.PLAYERS, 1.5f, 0.7f);
            }
        }
        super.onCast(level, spellLevel, caster, source, md);
    }

    private static void release(Cell cell) {
        if (cell.t.level() instanceof ServerLevel sl) {
            Vec3 c = cell.c;
            if (cell.fx >= 0) ru.pohsmp.core.fx.Fx.stop(sl, cell.fx, "");
            sl.playSound(null, c.x, c.y, c.z, SoundEvents.GLASS_BREAK, SoundSource.PLAYERS, 2f, 0.7f);
            DivineEvents.particle(sl, ParticleTypes.END_ROD, c.x, c.y + 1.5, c.z, 30, 1.2, 0.1);
        }
    }

    public static final class MirrorPrisonEvents {
        private MirrorPrisonEvents() {}

        @SubscribeEvent
        public static void onServerTick(net.minecraftforge.event.TickEvent.ServerTickEvent e) {
            if (e.phase != net.minecraftforge.event.TickEvent.Phase.END || CELLS.isEmpty()) return;
            CELLS.values().removeIf(cell -> {
                LivingEntity t = cell.t;
                if (!t.isAlive() || t.isRemoved() || t.level().getGameTime() > cell.until) {
                    release(cell);
                    return true;
                }
                double dx = t.getX() - cell.c.x, dz = t.getZ() - cell.c.z;
                if (Math.abs(dx) > HALF - 0.4 || Math.abs(dz) > HALF - 0.4 || t.getY() > cell.c.y + H - t.getBbHeight() || t.getY() < cell.c.y - 1) {
                    place(t, cell.c.x, cell.c.y, cell.c.z);
                    t.setDeltaMovement(Vec3.ZERO);
                }
                if (t instanceof Mob m && m.getTarget() != null) m.getNavigation().stop();
                return false;
            });
        }

        @SubscribeEvent(priority = EventPriority.HIGH)
        public static void onAttack(LivingAttackEvent e) {
            if (CELLS.isEmpty() || REFLECT.get() || e.getEntity().level().isClientSide) return;
            LivingEntity victim = e.getEntity();
            Entity src = e.getSource().getEntity();
            Cell inside = CELLS.get(victim.getUUID());
            if (inside != null && src != null && src != victim) {   // nothing from outside reaches the prisoner
                e.setCanceled(true);
                return;
            }
            if (src instanceof LivingEntity a && a != victim) {
                Cell own = CELLS.get(a.getUUID());
                if (own == null) return;
                e.setCanceled(true);   // the prisoner's attack turns back on itself
                REFLECT.set(true);
                try {
                    a.invulnerableTime = 0;
                    a.hurt(e.getSource(), e.getAmount());
                } finally {
                    REFLECT.set(false);
                }
                if (a.level() instanceof ServerLevel sl) DivineEvents.particle(sl, ParticleTypes.END_ROD, a.getX(), a.getY() + 1, a.getZ(), 8, 0.4, 0.05);
            }
        }

        @SubscribeEvent
        public static void onStopping(ServerStoppingEvent e) {
            CELLS.clear();
        }
    }
}
