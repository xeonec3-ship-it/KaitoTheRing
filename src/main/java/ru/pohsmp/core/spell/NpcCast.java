package ru.pohsmp.core.spell;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.arguments.BoolArgumentType;
import com.mojang.brigadier.arguments.IntegerArgumentType;
import com.mojang.brigadier.arguments.StringArgumentType;
import com.mojang.brigadier.context.CommandContext;
import io.redspace.ironsspellbooks.api.entity.IMagicEntity;
import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.registry.SpellRegistry;
import io.redspace.ironsspellbooks.api.spells.AbstractSpell;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.util.Utils;
import io.redspace.ironsspellbooks.capabilities.magic.TargetEntityCastData;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.SharedSuggestionProvider;
import net.minecraft.commands.arguments.EntityArgument;
import net.minecraft.commands.arguments.coordinates.Vec3Argument;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.RegisterCommandsEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.living.LivingAttackEvent;
import net.minecraftforge.event.entity.living.LivingEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.network.PacketDistributor;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.net.Net;

/**
 * Spell casting for creatures that are not players (CustomNPCs NPCs, any mob): the same course as a player's cast.
 * The caster turns to the target, the spell's own pre-cast check runs (range, line of sight, its conditions), then the
 * server pre-cast, a cast tick every tick, the cast itself and the cast-complete with the usual Iron's hooks, so the spell's
 * visuals, cutscene and target hold work as for a player. Clients get {@link Net.NpcCastMsg} for the cast sound and the
 * player-style animation on the NPC model (client/NpcCastClient). No mana and no cooldowns, like Iron's own mobs.
 * Rules kept: a long cast that the spell lets be interrupted is broken by damage; a long cast that cannot be interrupted
 * (Disintegration and the like) cannot be cancelled either, except by force (script reset, death, unload).
 */
public final class NpcCast {
    private NpcCast() {}

    private static final class Cast {
        LivingEntity caster;
        AbstractSpell spell;
        int level;
        MagicData md;
        /** Aim: a creature (followed while it lives) or a fixed point; both null = keep the caster's own facing. */
        Entity target;
        Vec3 point;
        boolean done;
    }

    private static final Map<UUID, Cast> CASTS = new HashMap<>();

    /** Spell by id: "pohsmp_core:disintegration", "irons_spellbooks:fireball"; without a namespace this mod, then Iron's. */
    public static AbstractSpell spell(String id) {
        if (id == null || id.isBlank()) return null;
        id = id.trim().toLowerCase(java.util.Locale.ROOT);
        List<String> tries = id.contains(":") ? List.of(id) : List.of(PohCore.MODID + ":" + id, "irons_spellbooks:" + id);
        for (String s : tries) {
            AbstractSpell sp = SpellRegistry.getSpell(s);
            if (sp != null && sp != SpellRegistry.none()) return sp;
        }
        return null;
    }

    public static boolean isCasting(LivingEntity e) {
        if (e == null) return false;
        if (CASTS.containsKey(e.getUUID())) return true;
        return e instanceof IMagicEntity m && m.isCasting();
    }

    /** Id of the spell being cast by this creature, "" if none. */
    public static String castingSpell(LivingEntity e) {
        Cast c = e == null ? null : CASTS.get(e.getUUID());
        return c == null ? "" : c.spell.getSpellId();
    }

    /**
     * Starts a cast. level &lt;= 0 = the spell's max level. target: a creature, or null with point set, or both null
     * (the caster's own attack target if it has one, otherwise straight ahead). Returns null on success, else why not.
     */
    public static String start(LivingEntity caster, AbstractSpell spell, int level, Entity target, Vec3 point) {
        if (caster == null || spell == null) return "no caster or no such spell";
        if (!(caster.level() instanceof ServerLevel sl)) return "not on the server";
        if (caster instanceof ServerPlayer) return "players cast by themselves";
        if (!caster.isAlive() || caster.isRemoved()) return "the caster is dead";
        if (isCasting(caster)) return "already casting";
        if (target == null && point == null && caster instanceof Mob m && m.getTarget() != null && m.getTarget().isAlive()) target = m.getTarget();
        if (target != null && target.level() != sl) return "the target is in another dimension";
        int lv = level <= 0 ? spell.getMaxLevel() : Mth.clamp(level, spell.getMinLevel(), spell.getMaxLevel());

        Cast c = new Cast();
        c.caster = caster;
        c.spell = spell;
        c.level = lv;
        c.target = target;
        c.point = point;
        aim(c);
        MagicData md = MagicData.getPlayerMagicData(caster);
        c.md = md;
        md.resetAdditionalCastData();
        if (!spell.checkPreCastConditions(sl, lv, caster, md)) {
            md.resetAdditionalCastData();
            return "the spell's conditions failed (range, line of sight or its own rule)";
        }
        // the caster was told whom to hit: if the aim ray caught someone in between, the named target still counts
        if (target instanceof LivingEntity lt && md.getAdditionalCastData() instanceof TargetEntityCastData td && td.getTarget(sl) != lt)
            md.setAdditionalCastData(new TargetEntityCastData(lt));
        int ticks = spell.getCastType() == CastType.INSTANT ? 0 : spell.getEffectiveCastTime(lv, caster);
        md.initiateCast(spell, lv, ticks, CastSource.MOB, "mainhand");
        CASTS.put(caster.getUUID(), c);
        send(caster, new Net.NpcCastMsg(Net.NpcCastMsg.START, caster.getId(), spell.getSpellId(), lv, ticks));
        spell.onServerPreCast(sl, lv, caster, md);
        if (c.done) return null; // the spell itself stopped the cast in its pre-cast
        if (ticks == 0) tick(c);
        return null;
    }

    /** true if a cast was stopped. Without force a long cast that its spell does not let be interrupted goes on. */
    public static boolean cancel(LivingEntity caster, boolean force) {
        if (caster == null) return false;
        Cast c = CASTS.get(caster.getUUID());
        if (c == null) {
            if (caster instanceof IMagicEntity m && m.isCasting()) {
                m.cancelCast();
                return true;
            }
            return false;
        }
        if (!force && !cancellable(c.spell)) return false;
        end(c, true);
        return true;
    }

    /** For spells: stop the caster's cast whoever it is (a player, an NPC through this API, an Iron's mob). */
    public static void cancelAny(LivingEntity caster) {
        if (caster instanceof ServerPlayer sp) Utils.serverSideCancelCast(sp);
        else cancel(caster, true);
    }

    /** A long cast whose spell says it cannot be interrupted cannot be cancelled; everything else can. */
    public static boolean cancellable(AbstractSpell spell) {
        return spell.getCastType() != CastType.LONG || interruptible(spell);
    }

    /** Would damage break this cast (Iron's rule for players: long casts the spell allows to be interrupted). */
    private static boolean interruptible(AbstractSpell spell) {
        if (spell.getCastType() != CastType.LONG) return false;
        try {
            return spell.canBeInterrupted(null);
        } catch (RuntimeException e) {
            return true; // Iron's default looks at the player's curios; with no player the base rule (long = interruptible) stays
        }
    }

    private static void tick(Cast c) {
        if (c.done) return;
        LivingEntity e = c.caster;
        if (!(e.level() instanceof ServerLevel sl)) return;
        if (!c.md.isCasting()) { // something else reset the cast (another mod, a command)
            finish(c, true, false);
            return;
        }
        aim(c);
        if (c.spell.getCastType() != CastType.INSTANT) {
            if (e instanceof Mob m) m.getNavigation().stop();
            Vec3 v = e.getDeltaMovement();
            e.setDeltaMovement(0, v.y, 0);
        }
        c.md.handleCastDuration();
        c.spell.onServerCastTick(sl, c.level, e, c.md);
        if (c.done) return;
        int left = c.md.getCastDurationRemaining();
        CastType type = c.spell.getCastType();
        if (left <= 0) {
            if (type == CastType.INSTANT || type == CastType.LONG) c.spell.onCast(sl, c.level, e, CastSource.MOB, c.md);
            end(c, false);
        } else if (type == CastType.CONTINUOUS && (left + 1) % 10 == 0) {
            c.spell.onCast(sl, c.level, e, CastSource.MOB, c.md);
        }
    }

    private static void end(Cast c, boolean cancelled) {
        finish(c, cancelled, true);
    }

    private static void finish(Cast c, boolean cancelled, boolean complete) {
        if (c.done) return;
        c.done = true;
        CASTS.remove(c.caster.getUUID(), c);
        if (complete && c.caster.level() instanceof ServerLevel sl) c.spell.onServerCastComplete(sl, c.level, c.caster, c.md, cancelled);
        else c.md.resetCastingState();
        send(c.caster, new Net.NpcCastMsg(cancelled ? Net.NpcCastMsg.CANCEL : Net.NpcCastMsg.FINISH, c.caster.getId(), c.spell.getSpellId(), c.level, 0));
        CnpcHooks.callWith(c.caster, "pohsmp_cast_end", new EndEvent(c.caster, c.spell.getSpellId(), cancelled));
    }

    /** What the NPC script function pohsmp_cast_end(e) gets. */
    public static final class EndEvent {
        public Object npc;
        public final String spell;
        public final boolean cancelled;
        public final double x, y, z;

        EndEvent(LivingEntity caster, String spell, boolean cancelled) {
            this.spell = spell;
            this.cancelled = cancelled;
            this.x = caster.getX();
            this.y = caster.getY();
            this.z = caster.getZ();
        }
    }

    /** Turns the caster's head, body and view to the target (creatures: the middle of the body). */
    private static void aim(Cast c) {
        Vec3 p = c.point;
        if (c.target != null) {
            if (!c.target.isAlive() || c.target.isRemoved() || c.target.level() != c.caster.level()) return;
            p = c.target.position().add(0, c.target.getBbHeight() * 0.5, 0);
        }
        if (p != null) face(c.caster, p);
    }

    public static void face(LivingEntity e, Vec3 p) {
        Vec3 eye = e.getEyePosition();
        double dx = p.x - eye.x, dy = p.y - eye.y, dz = p.z - eye.z;
        double h = Math.sqrt(dx * dx + dz * dz);
        if (h < 1e-4 && Math.abs(dy) < 1e-4) return;
        float yaw = (float) (Mth.atan2(dz, dx) * Mth.RAD_TO_DEG) - 90f;
        float pitch = (float) -(Mth.atan2(dy, h) * Mth.RAD_TO_DEG);
        e.setYRot(yaw);
        e.setXRot(pitch);
        e.setYHeadRot(yaw);
        e.setYBodyRot(yaw);
        e.yRotO = yaw;
        e.xRotO = pitch;
        e.yHeadRotO = yaw;
        e.yBodyRotO = yaw;
        if (e instanceof Mob m) m.getLookControl().setLookAt(p.x, p.y, p.z, 360f, 360f);
    }

    private static void send(LivingEntity e, Net.NpcCastMsg msg) {
        Net.CH.send(PacketDistributor.TRACKING_ENTITY.with(() -> e), msg);
    }

    // ---- events ----

    public static final class Events {
        private Events() {}

        @SubscribeEvent
        public static void onLivingTick(LivingEvent.LivingTickEvent e) {
            if (CASTS.isEmpty() || e.getEntity().level().isClientSide) return;
            Cast c = CASTS.get(e.getEntity().getUUID());
            if (c != null && c.caster == e.getEntity()) tick(c);
        }

        /** Dead, removed or moved casters lose their cast (forced: no rule keeps a cast without its caster). */
        @SubscribeEvent
        public static void onServerTick(TickEvent.ServerTickEvent e) {
            if (e.phase != TickEvent.Phase.END || CASTS.isEmpty()) return;
            for (Cast c : new ArrayList<>(CASTS.values()))
                if (!c.caster.isAlive() || c.caster.isRemoved()) end(c, true);
        }

        /** Iron's rule for players: damage breaks a long cast when the spell allows it. */
        @SubscribeEvent(priority = EventPriority.LOWEST)
        public static void onAttack(LivingAttackEvent e) {
            if (e.isCanceled() || CASTS.isEmpty() || e.getEntity().level().isClientSide) return;
            Cast c = CASTS.get(e.getEntity().getUUID());
            if (c != null && interruptible(c.spell)) end(c, true);
        }

        @SubscribeEvent
        public static void onStopping(ServerStoppingEvent e) {
            for (Cast c : new ArrayList<>(CASTS.values())) end(c, true);
            CASTS.clear();
        }

        @SubscribeEvent
        public static void onRegister(RegisterCommandsEvent e) {
            register(e.getDispatcher());
        }
    }

    /**
     * Operator commands (level 2), the same as Core.cast from a script:
     * /pohsmp npccast &lt;caster&gt; &lt;spell&gt; [level] [entity &lt;target&gt; | at &lt;pos&gt;], /pohsmp npccancel &lt;caster&gt; [force].
     */
    private static void register(CommandDispatcher<CommandSourceStack> d) {
        d.register(Commands.literal("pohsmp").requires(s -> s.hasPermission(2))
                .then(Commands.literal("npccast").then(Commands.argument("caster", EntityArgument.entity())
                        .then(target(Commands.argument("spell", StringArgumentType.string())
                                .suggests((c, b) -> SharedSuggestionProvider.suggest(SpellRegistry.REGISTRY.get().getValues().stream()
                                        .filter(s -> s != SpellRegistry.none()).map(s -> "\"" + s.getSpellId() + "\""), b))
                                .executes(c -> cmdCast(c, 0, null, null))
                                .then(target(Commands.argument("level", IntegerArgumentType.integer(1, 100))
                                        .executes(c -> cmdCast(c, IntegerArgumentType.getInteger(c, "level"), null, null)), true)), false))))
                .then(Commands.literal("npccancel").then(Commands.argument("caster", EntityArgument.entity())
                        .executes(c -> cmdCancel(c, false))
                        .then(Commands.argument("force", BoolArgumentType.bool()).executes(c -> cmdCancel(c, BoolArgumentType.getBool(c, "force")))))));
    }

    private static <T extends com.mojang.brigadier.builder.ArgumentBuilder<CommandSourceStack, T>> T target(T node, boolean withLevel) {
        return node
                .then(Commands.literal("entity").then(Commands.argument("target", EntityArgument.entity())
                        .executes(c -> cmdCast(c, withLevel ? IntegerArgumentType.getInteger(c, "level") : 0, EntityArgument.getEntity(c, "target"), null))))
                .then(Commands.literal("at").then(Commands.argument("pos", Vec3Argument.vec3())
                        .executes(c -> cmdCast(c, withLevel ? IntegerArgumentType.getInteger(c, "level") : 0, null, Vec3Argument.getVec3(c, "pos")))));
    }

    private static int cmdCast(CommandContext<CommandSourceStack> c, int level, Entity target, Vec3 point) throws com.mojang.brigadier.exceptions.CommandSyntaxException {
        Entity caster = EntityArgument.getEntity(c, "caster");
        String id = StringArgumentType.getString(c, "spell");
        AbstractSpell sp = spell(id);
        if (sp == null) {
            c.getSource().sendFailure(Component.literal("No spell " + id));
            return 0;
        }
        if (!(caster instanceof LivingEntity le)) {
            c.getSource().sendFailure(Component.literal("The caster is not a living creature"));
            return 0;
        }
        String why;
        try {
            why = start(le, sp, level, target, point);
        } catch (RuntimeException ex) {
            PohCore.LOG.error("[pohsmp_core] npccast {} failed", sp.getSpellId(), ex);
            c.getSource().sendFailure(Component.literal("Error: " + ex));
            return 0;
        }
        if (why != null) {
            c.getSource().sendFailure(Component.literal("Not cast: " + why));
            return 0;
        }
        c.getSource().sendSuccess(() -> Component.literal(caster.getName().getString() + " casts " + sp.getSpellId()), true);
        return 1;
    }

    private static int cmdCancel(CommandContext<CommandSourceStack> c, boolean force) throws com.mojang.brigadier.exceptions.CommandSyntaxException {
        Entity caster = EntityArgument.getEntity(c, "caster");
        boolean ok = caster instanceof LivingEntity le && cancel(le, force);
        if (ok) c.getSource().sendSuccess(() -> Component.literal("Cast cancelled"), true);
        else c.getSource().sendFailure(Component.literal("Nothing cancelled (not casting, or the spell cannot be cancelled without force)"));
        return ok ? 1 : 0;
    }
}
