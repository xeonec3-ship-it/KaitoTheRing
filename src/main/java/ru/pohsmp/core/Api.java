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

    /** Runs a command as the server at the level's spawn, with no feedback in chat or log. Returns the command result. */
    public static int cmd(Level level, String command) {
        if (!(level instanceof ServerLevel sl)) return 0;
        MinecraftServer s = sl.getServer();
        return s.getCommands().performPrefixedCommand(s.createCommandSourceStack().withLevel(sl).withSuppressedOutput(), command);
    }
}
