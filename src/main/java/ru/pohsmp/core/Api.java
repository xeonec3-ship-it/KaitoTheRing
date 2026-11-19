package ru.pohsmp.core;

import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.Level;

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
     * "duration":ticks, "attachEntity":"uuid", "offset":[x,y,z], "yaw":deg}. Nothing is written to chat.
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
            if (o.has("attachEntity")) attach = sl.getEntity(java.util.UUID.fromString(o.get("attachEntity").getAsString()));
        }
        if (attach != null) {
            s.attach(attach);
            s.caster(attach);
            s.at(attach.getX() + ox, attach.getY() + oy, attach.getZ() + oz);
        } else s.at(x + ox, y + oy, z + oz);
        return ru.pohsmp.core.fx.Fx.play(sl, s);
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

    /**
     * An NPC (or any non-player mob) casts a spell like a player: animation, effects, cutscene. id: "pohsmp_core:disintegration",
     * "irons_spellbooks:fireball" (or just "fireball"). target: an entity (CNPC or Minecraft) or null (straight ahead).
     * Spell level = its minimum. Returns false if it could not start (already casting, unknown spell, the spell refused).
     */
    public static boolean cast(Object npc, String id, Object target) {
        return cast(npc, id, target, 0);
    }

    public static boolean cast(Object npc, String id, Object target, int level) {
        net.minecraft.world.entity.Entity t = mc(target);
        return mc(npc) instanceof net.minecraft.world.entity.LivingEntity le
                && NpcCast.cast(le, id, level, t instanceof net.minecraft.world.entity.LivingEntity lt ? lt : null,
                        t != null ? t.position() : null);
    }

    /** Same, aimed at a point. */
    public static boolean castAt(Object npc, String id, double x, double y, double z, int level) {
        return mc(npc) instanceof net.minecraft.world.entity.LivingEntity le && NpcCast.cast(le, id, level, null, new net.minecraft.world.phys.Vec3(x, y, z));
    }

    /** Stops the NPC's cast; a spell that cannot be interrupted is not stopped. Returns true if stopped. */
    public static boolean cancelCast(Object npc) {
        return mc(npc) instanceof net.minecraft.world.entity.LivingEntity le && NpcCast.cancel(le, false);
    }

    /** Stops it even if the spell cannot be interrupted (the boss dies, the phase changes). */
    public static boolean forceCancelCast(Object npc) {
        return mc(npc) instanceof net.minecraft.world.entity.LivingEntity le && NpcCast.cancel(le, true);
    }

    public static boolean isCasting(Object npc) {
        return mc(npc) instanceof net.minecraft.world.entity.LivingEntity le && NpcCast.isCasting(le);
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
}
