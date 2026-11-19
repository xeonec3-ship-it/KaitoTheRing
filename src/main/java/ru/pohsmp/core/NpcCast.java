package ru.pohsmp.core;

import io.redspace.ironsspellbooks.api.entity.IMagicEntity;
import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.registry.SpellRegistry;
import io.redspace.ironsspellbooks.api.spells.AbstractSpell;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.spells.SpellData;
import io.redspace.ironsspellbooks.capabilities.magic.TargetEntityCastData;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.living.LivingDeathEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.spell.CnpcHooks;

/**
 * T17: any non-player mob (CustomNPCs NPCs too) casts a spell of this mod or of Iron's the way Iron's casting mobs do:
 * pre-cast check (target hold), onServerPreCast, a tick per server tick, onCast at the end (every 10 ticks for continuous),
 * onServerCastComplete. The spell's own effects and cutscene play as for a player. CNPC NPCs raise their arms while casting
 * and get script events {@code cast_start(e)} / {@code cast_end(e)} (e.caster holds the spell id). No mana, no cooldowns:
 * the boss script decides when.
 */
public final class NpcCast {
    private NpcCast() {}

    private static final class Cast {
        final LivingEntity e;
        final AbstractSpell spell;
        final int level;
        LivingEntity target;
        Vec3 point;
        int pose = -1;

        Cast(LivingEntity e, AbstractSpell spell, int level) {
            this.e = e;
            this.spell = spell;
            this.level = level;
        }
    }

    private static final Map<UUID, Cast> ACTIVE = new HashMap<>();
    private static final int NPC_ARMS = 3;

    /** The spell by id ("pohsmp_core:disintegration", "irons_spellbooks:fireball"); null if unknown. */
    public static AbstractSpell spell(String id) {
        if (id == null) return null;
        AbstractSpell s = SpellRegistry.getSpell(id.contains(":") ? id : "irons_spellbooks:" + id);
        return s == null || s == SpellRegistry.none() ? null : s;
    }

    /**
     * Starts the cast; target: a LivingEntity, a Vec3 point, or null (straight ahead). level ≤ 0 = the spell's minimum.
     * Returns false if the caster is a player, is already casting, the spell is unknown, or the spell refuses (no target in range...).
     */
    public static boolean cast(LivingEntity e, String id, int level, LivingEntity target, Vec3 point) {
        if (e == null || e instanceof Player || !(e.level() instanceof ServerLevel sl) || !e.isAlive()) return false;
        AbstractSpell spell = spell(id);
        if (spell == null || isCasting(e)) return false;
        int lvl = Math.max(spell.getMinLevel(), Math.min(spell.getMaxLevel(), level <= 0 ? spell.getMinLevel() : level));
        if (target != null) point = target.getEyePosition();
        if (point != null) face(e, point);
        if (target != null && e instanceof Mob m) m.setTarget(target);
        if (e instanceof IMagicEntity me) {   // Iron's own casting mobs drive themselves
            me.initiateCastSpell(spell, lvl);
            return me.isCasting();
        }
        MagicData md = MagicData.getPlayerMagicData(e);
        md.resetAdditionalCastData();
        if (!spell.checkPreCastConditions(sl, lvl, e, md)) {
            if (target == null) return false;
            md.setAdditionalCastData(new TargetEntityCastData(target));   // the script named the target: hold it even out of sight
        }
        md.initiateCast(spell, lvl, spell.getEffectiveCastTime(lvl, e), CastSource.MOB, "mainhand");
        Cast c = new Cast(e, spell, lvl);
        c.target = target;
        c.point = point;
        ACTIVE.put(e.getUUID(), c);
        c.pose = CnpcHooks.anim(e, NPC_ARMS);
        CnpcHooks.call(e, "cast_start", spell.getSpellId());
        spell.onServerPreCast(sl, lvl, e, md);
        if (spell.getCastType() == CastType.INSTANT) step(c);
        return true;
    }

    public static boolean isCasting(LivingEntity e) {
        if (e == null) return false;
        if (e instanceof IMagicEntity me) return me.isCasting();
        return ACTIVE.containsKey(e.getUUID());
    }

    /** Stops the cast; a spell that cannot be interrupted keeps going unless force. Returns true if it stopped. */
    public static boolean cancel(LivingEntity e, boolean force) {
        if (e == null) return false;
        if (e instanceof IMagicEntity me) {
            if (!me.isCasting()) return false;
            me.cancelCast();
            return true;
        }
        Cast c = ACTIVE.get(e.getUUID());
        if (c == null) return false;
        if (!force && !interruptible(c.spell)) return false;
        end(c, true);
        return true;
    }

    private static boolean interruptible(AbstractSpell s) {
        try {
            return s.canBeInterrupted(null);
        } catch (Throwable t) {
            return true;
        }
    }

    private static void face(LivingEntity e, Vec3 p) {
        Vec3 d = p.subtract(e.getEyePosition());
        float yaw = (float) Math.toDegrees(Math.atan2(-d.x, d.z));
        float pitch = (float) -Math.toDegrees(Math.atan2(d.y, Math.sqrt(d.x * d.x + d.z * d.z)));
        e.setYRot(yaw);
        e.setYHeadRot(yaw);
        e.setYBodyRot(yaw);
        e.setXRot(pitch);
    }

    /** One tick; false once the cast is over. */
    private static boolean step(Cast c) {
        LivingEntity e = c.e;
        MagicData md = MagicData.getPlayerMagicData(e);
        if (!e.isAlive() || e.isRemoved() || !md.isCasting()) {
            end(c, true);
            return false;
        }
        ServerLevel sl = (ServerLevel) e.level();
        if (c.target != null && c.target.isAlive()) c.point = c.target.getEyePosition();
        if (c.point != null) face(e, c.point);
        md.handleCastDuration();
        c.spell.onServerCastTick(sl, c.level, e, md);
        CastType type = c.spell.getCastType();
        if (md.getCastDurationRemaining() <= 0 && (type == CastType.LONG || type == CastType.INSTANT)) {
            c.spell.onCast(sl, c.level, e, CastSource.MOB, md);
            end(c, false);
            return false;
        }
        if (type == CastType.CONTINUOUS) {
            if ((md.getCastDurationRemaining() + 1) % 10 == 0) c.spell.onCast(sl, c.level, e, CastSource.MOB, md);
            if (md.getCastDurationRemaining() <= 0) {
                end(c, false);
                return false;
            }
        }
        return true;
    }

    private static void end(Cast c, boolean cancelled) {
        ACTIVE.remove(c.e.getUUID());
        MagicData md = MagicData.getPlayerMagicData(c.e);
        SpellData sd = md.getCastingSpell();
        if (md.isCasting() && sd != null && sd.getSpell() == c.spell) {
            c.spell.onServerCastComplete(c.e.level(), c.level, c.e, md, cancelled);
            md.resetCastingState();
        }
        if (c.pose >= 0) CnpcHooks.anim(c.e, c.pose);
        CnpcHooks.call(c.e, "cast_end", c.spell.getSpellId());
    }

    public static final class NpcCastEvents {
        private NpcCastEvents() {}

        @SubscribeEvent
        public static void onTick(TickEvent.ServerTickEvent ev) {
            if (ev.phase != TickEvent.Phase.END || ACTIVE.isEmpty()) return;
            for (Cast c : new ArrayList<>(ACTIVE.values())) if (ACTIVE.get(c.e.getUUID()) == c) step(c);
        }

        @SubscribeEvent
        public static void onDeath(LivingDeathEvent ev) {
            Cast c = ACTIVE.get(ev.getEntity().getUUID());
            if (c != null) end(c, true);
        }

        @SubscribeEvent
        public static void onStopping(ServerStoppingEvent ev) {
            for (Cast c : new ArrayList<>(ACTIVE.values())) end(c, true);
        }
    }
}
