package ru.pohsmp.core;

import io.redspace.ironsspellbooks.api.spells.AbstractSpell;
import java.lang.reflect.Method;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.spell.NpcCast;

/**
 * Helpers for CustomNPCs scripts: var Core = Java.type("ru.pohsmp.core.Api").
 */
public final class Api {
    private Api() {}

    public static String version() {
        return net.minecraftforge.fml.ModList.get().getModContainerById(PohCore.MODID)
                .map(c -> c.getModInfo().getVersion().toString()).orElse("?");
    }

    /**
     * Starts a sigil (assets/pohsmp_core/sigils/&lt;id&gt;.json, docs/sigils.md) for players nearby; returns its instance id (0 on failure).
     * options: JSON, all optional: {"orientation":"ground|sky|facing|billboard", "scale":1.5, "color":"#B49BFF",
     * "duration":ticks, "attachEntity":"uuid", "offset":[x,y,z], "yaw":deg, "text":"…", "texts":{"slot":"…"}}. Nothing is written to chat.
     * "text" fills the text layers with slot "text", "texts" — any slots (docs/sigils.md «Надписи»).
     */
    public static int sigil(Level level, String id, double x, double y, double z, String options) {
        if (!(level instanceof ServerLevel sl) || ru.pohsmp.core.fx.FxLib.sigil(id) == null) return 0;
        ru.pohsmp.core.fx.Fx.Spec s = ru.pohsmp.core.fx.Fx.sigil(id);
        double ox = 0, oy = 0, oz = 0;
        net.minecraft.world.entity.Entity attach = null;
        if (options != null && !options.isBlank()) {
            com.google.gson.JsonObject o = com.google.gson.JsonParser.parseString(options).getAsJsonObject();
            if (o.has("orientation")) s.orientation(o.get("orientation").getAsString());
            if (o.has("scale")) s.scale(o.get("scale").getAsDouble());
            if (o.has("color")) s.color(Integer.parseInt(o.get("color").getAsString().replace("#", ""), 16));
            if (o.has("duration")) s.duration(o.get("duration").getAsInt());
            if (o.has("yaw")) s.yaw(o.get("yaw").getAsFloat());
            if (o.has("offset")) {
                var a = o.getAsJsonArray("offset");
                ox = a.get(0).getAsDouble();
                oy = a.get(1).getAsDouble();
                oz = a.get(2).getAsDouble();
            }
            if (o.has("text")) s.text("text", o.get("text").getAsString());
            if (o.has("texts")) for (var e : o.getAsJsonObject("texts").entrySet()) s.text(e.getKey(), e.getValue().getAsString());
            if (o.has("attachEntity")) attach = sl.getEntity(java.util.UUID.fromString(o.get("attachEntity").getAsString()));
        }
        if (attach != null) {
            s.attach(attach);
            s.caster(attach);
            s.at(attach.getX() + ox, attach.getY() + oy, attach.getZ() + oz);
        } else s.at(x + ox, y + oy, z + oz);
        return ru.pohsmp.core.fx.Fx.play(sl, s);
    }

    /**
     * Replaces the inscription of a running sigil (text layers with this slot; "text" = the one {@code "text"} option fills), e.g. a
     * counter: <code>Core.sigilText(level, id, "count", "12")</code>. The new text writes itself in with a flare.
     */
    public static void sigilText(Level level, int instanceId, String slot, String text) {
        if (level instanceof ServerLevel sl) ru.pohsmp.core.fx.Fx.text(sl, instanceId, slot, text);
    }

    /** Dissolves a sigil started by {@link #sigil}; mode "" = as defined, or collapse / fade / shatter / reverse. */
    public static void sigilStop(Level level, int instanceId, String mode) {
        if (level instanceof ServerLevel sl) ru.pohsmp.core.fx.Fx.stop(sl, instanceId, mode);
    }

    /** Starts an effect (assets/pohsmp_core/fx/&lt;id&gt;.json) at a point; style "" = the effect's own. Returns the instance id. */
    public static int fx(Level level, String id, double x, double y, double z, float yaw, String style) {
        if (!(level instanceof ServerLevel sl) || ru.pohsmp.core.fx.FxLib.fx(id) == null) return 0;
        ru.pohsmp.core.fx.Fx.Spec s = ru.pohsmp.core.fx.Fx.fx(id).at(x, y, z).yaw(yaw);
        if (style != null && !style.isBlank()) s.style(style);
        return ru.pohsmp.core.fx.Fx.play(sl, s);
    }

    /**
     * Hides an entity from everyone (model, armour, held items, name, shadow; CNPC NPCs too) for ticks (&lt;= 0 = until {@link #show}),
     * with no damage and no collisions; a mob or NPC stays where it was hidden. entity: a CNPC script entity (npc, player, e.npc...)
     * or a Minecraft entity. Example: <code>Core.hide(npc, 100)</code>.
     */
    public static void hide(Object entity, int ticks) {
        Hidden.hide(mc(entity), ticks);
    }

    /** Same, with options: no damage, no pushing/projectiles/clicks; mobs and NPCs (not players) are kept in place. */
    public static void hide(Object entity, int ticks, boolean noDamage, boolean noCollide) {
        Hidden.hide(mc(entity), ticks, noDamage, noCollide);
    }

    /** Same, freeze chosen explicitly (true keeps players in place too, false lets mobs move). */
    public static void hide(Object entity, int ticks, boolean noDamage, boolean noCollide, boolean freeze) {
        Hidden.hide(mc(entity), ticks, noDamage, noCollide, freeze);
    }

    public static void show(Object entity) {
        Hidden.show(mc(entity));
    }

    public static boolean isHidden(Object entity) {
        return Hidden.isHidden(mc(entity));
    }

    /** Cast at a point (same as {@link #cast(Object, String, double, double, double, int)}). */
    public static boolean castAt(Object npc, String id, double x, double y, double z, int level) {
        return cast(npc, id, x, y, z, level);
    }

    public static boolean castAt(Object npc, String id, double x, double y, double z) {
        return cast(npc, id, x, y, z, 0);
    }

    /** Stops any cast, even one that cannot be interrupted (same as cancelCast(npc, true)). */
    public static boolean forceCancelCast(Object npc) {
        return cancelCast(npc, true);
    }

    /** A CNPC script wrapper (IEntity) or a Minecraft entity to the Minecraft entity; null if neither. */
    static net.minecraft.world.entity.Entity mc(Object o) {
        if (o instanceof net.minecraft.world.entity.Entity e) return e;
        if (o == null) return null;
        try {
            Object r = o.getClass().getMethod("getMCEntity").invoke(o);
            return r instanceof net.minecraft.world.entity.Entity e ? e : null;
        } catch (Throwable t) {
            return null;
        }
    }

    /** Runs a command as the server at the level's spawn, with no feedback in chat or log. Returns the command result. */
    public static int cmd(Level level, String command) {
        if (!(level instanceof ServerLevel sl)) return 0;
        MinecraftServer s = sl.getServer();
        return s.getCommands().performPrefixedCommand(s.createCommandSourceStack().withLevel(sl).withSuppressedOutput(), command);
    }

    // ---- NPC casting (spell/NpcCast) ----

    /**
     * The NPC (a CNPC NPC or any non-player creature) casts a spell like a player: turns to the target, the spell's own
     * checks, animation, effects, cutscene, target hold. target: a creature (CNPC IEntity or Minecraft entity), a point
     * (IPos, BlockPos, Vec3, JS array [x, y, z] or {x:, y:, z:}), or null = the NPC's attack target, else straight ahead.
     * Level = the spell's max level. Returns true if the cast started; why not is written to the server log.
     */
    public static boolean cast(Object npc, String spell, Object target) {
        return cast(npc, spell, target, 0);
    }

    /** Same with a spell level (clamped to the spell's levels; 0 = max). */
    public static boolean cast(Object npc, String spell, Object target, int level) {
        LivingEntity caster = living(npc);
        AbstractSpell sp = NpcCast.spell(spell);
        if (caster == null || sp == null) {
            PohCore.LOG.warn("[pohsmp_core] Core.cast: {}", caster == null ? "the first argument is not a living NPC" : "no spell " + spell);
            return false;
        }
        Entity te = entity(target);
        Vec3 point = te == null ? point(target) : null;
        if (target != null && te == null && point == null) {
            PohCore.LOG.warn("[pohsmp_core] Core.cast: target {} is neither an entity nor a point", target);
            return false;
        }
        String why = NpcCast.start(caster, sp, level, te, point);
        if (why != null) PohCore.LOG.info("[pohsmp_core] Core.cast {} by {}: {}", sp.getSpellId(), caster.getName().getString(), why);
        return why == null;
    }

    /** Cast at a point. */
    public static boolean cast(Object npc, String spell, double x, double y, double z) {
        return cast(npc, spell, new Vec3(x, y, z), 0);
    }

    public static boolean cast(Object npc, String spell, double x, double y, double z, int level) {
        return cast(npc, spell, new Vec3(x, y, z), level);
    }

    /** Stops the NPC's cast; false if it was not casting or the spell cannot be cancelled (a long cast that cannot be interrupted). */
    public static boolean cancelCast(Object npc) {
        return cancelCast(npc, false);
    }

    /** force = true stops any cast (for resets of a boss script). */
    public static boolean cancelCast(Object npc, boolean force) {
        return NpcCast.cancel(living(npc), force);
    }

    public static boolean isCasting(Object npc) {
        return NpcCast.isCasting(living(npc));
    }

    /** Id of the spell the NPC is casting through Core.cast, "" if none. */
    public static String castingSpell(Object npc) {
        return NpcCast.castingSpell(living(npc));
    }

    private static LivingEntity living(Object o) {
        return entity(o) instanceof LivingEntity le ? le : null;
    }

    /** A Minecraft entity, or a CNPC wrapper (IEntity.getMCEntity()). */
    private static Entity entity(Object o) {
        if (o instanceof Entity e) return e;
        if (o == null) return null;
        try {
            Method m = o.getClass().getMethod("getMCEntity");
            Object r = m.invoke(o);
            return r instanceof Entity e ? e : null;
        } catch (ReflectiveOperationException | RuntimeException ex) {
            return null;
        }
    }

    /** Vec3, BlockPos/IPos (block center), JS array [x, y, z], JS object or Map {x, y, z}, List, double[]. */
    private static Vec3 point(Object o) {
        if (o instanceof Vec3 v) return v;
        if (o instanceof net.minecraft.core.Vec3i b) return new Vec3(b.getX() + 0.5, b.getY(), b.getZ() + 0.5);
        if (o instanceof double[] a && a.length >= 3) return new Vec3(a[0], a[1], a[2]);
        if (o instanceof java.util.List<?> l && l.size() >= 3) return vec(l.get(0), l.get(1), l.get(2), false);
        if (o instanceof java.util.Map<?, ?> m) {
            if (m.containsKey("x")) return vec(m.get("x"), m.get("y"), m.get("z"), false);
            if (m.containsKey("0")) return vec(m.get("0"), m.get("1"), m.get("2"), false);
        }
        if (o == null) return null;
        try { // CNPC IPos and anything else with getX/getY/getZ
            Class<?> c = o.getClass();
            Method gx = c.getMethod("getX"), gy = c.getMethod("getY"), gz = c.getMethod("getZ");
            gx.setAccessible(true);
            gy.setAccessible(true);
            gz.setAccessible(true);
            Object x = gx.invoke(o), y = gy.invoke(o), z = gz.invoke(o);
            return vec(x, y, z, x instanceof Integer && z instanceof Integer);
        } catch (ReflectiveOperationException | RuntimeException ex) {
            return null;
        }
    }

    private static Vec3 vec(Object x, Object y, Object z, boolean block) {
        if (!(x instanceof Number nx) || !(y instanceof Number ny) || !(z instanceof Number nz)) return null;
        double c = block ? 0.5 : 0;
        return new Vec3(nx.doubleValue() + c, ny.doubleValue(), nz.doubleValue() + c);
    }
}
