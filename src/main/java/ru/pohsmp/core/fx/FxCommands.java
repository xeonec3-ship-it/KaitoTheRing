package ru.pohsmp.core.fx;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.arguments.DoubleArgumentType;
import com.mojang.brigadier.arguments.StringArgumentType;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.SharedSuggestionProvider;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.RegisterCommandsEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;

/**
 * Preview commands for operators (level 2):
 * /pohsmp sigil play &lt;id&gt; [scale] [orientation] | stop | reload,
 * /pohsmp fx play &lt;id&gt; [style] | stop | reload, /pohsmp mesh play &lt;id&gt; [seconds] | stop.
 */
public final class FxCommands {
    private FxCommands() {}

    @SubscribeEvent
    public static void onRegister(RegisterCommandsEvent e) {
        register(e.getDispatcher());
    }

    private static void register(CommandDispatcher<CommandSourceStack> d) {
        d.register(Commands.literal("pohsmp").requires(s -> s.hasPermission(2))
                .then(Commands.literal("sigil")
                        .then(Commands.literal("play").then(Commands.argument("id", StringArgumentType.word())
                                .suggests((c, b) -> SharedSuggestionProvider.suggest(FxLib.list("sigils"), b))
                                .executes(c -> sigil(c, 1, null))
                                .then(Commands.argument("scale", DoubleArgumentType.doubleArg(0.05, 50))
                                        .executes(c -> sigil(c, DoubleArgumentType.getDouble(c, "scale"), null))
                                        .then(Commands.argument("orientation", StringArgumentType.word())
                                                .suggests((c, b) -> SharedSuggestionProvider.suggest(new String[] {"ground", "sky", "facing", "billboard"}, b))
                                                .executes(c -> sigil(c, DoubleArgumentType.getDouble(c, "scale"), StringArgumentType.getString(c, "orientation")))))))
                        .then(Commands.literal("stop").executes(FxCommands::stop))
                        .then(Commands.literal("reload").executes(FxCommands::reload)))
                .then(Commands.literal("fx")
                        .then(Commands.literal("play").then(Commands.argument("id", StringArgumentType.word())
                                .suggests((c, b) -> SharedSuggestionProvider.suggest(FxLib.list("fx"), b))
                                .executes(c -> fx(c, null))
                                .then(Commands.argument("style", StringArgumentType.word())
                                        .suggests((c, b) -> SharedSuggestionProvider.suggest(FxLib.list("fx/styles"), b))
                                        .executes(c -> fx(c, StringArgumentType.getString(c, "style"))))))
                        .then(Commands.literal("stop").executes(FxCommands::stop))
                        .then(Commands.literal("reload").executes(FxCommands::reload)))
                .then(Commands.literal("mesh")
                        .then(Commands.literal("play").then(Commands.argument("id", StringArgumentType.word())
                                .suggests((c, b) -> SharedSuggestionProvider.suggest(FxLib.list("fx/meshes"), b))
                                .executes(c -> mesh(c, 10))
                                .then(Commands.argument("seconds", DoubleArgumentType.doubleArg(1, 600))
                                        .executes(c -> mesh(c, DoubleArgumentType.getDouble(c, "seconds"))))))
                        .then(Commands.literal("stop").executes(FxCommands::stop))));
    }

    private static Vec3 ahead(ServerPlayer p, double dist) {
        Vec3 f = Vec3.directionFromRotation(0, p.getYRot());
        return p.position().add(f.scale(dist));
    }

    private static int sigil(CommandContext<CommandSourceStack> c, double scale, String orientation) throws CommandSyntaxException {
        ServerPlayer p = c.getSource().getPlayerOrException();
        String id = StringArgumentType.getString(c, "id");
        var def = FxLib.sigil(id);
        if (def == null) {
            c.getSource().sendFailure(Component.literal("No sigil " + id));
            return 0;
        }
        String o = orientation != null ? orientation : def.orientation().name().toLowerCase();
        Vec3 at = switch (o) {
            case "sky" -> ahead(p, 4).add(0, 5, 0);
            case "facing", "billboard" -> ahead(p, 4).add(0, 1.6, 0);
            default -> ahead(p, 4).add(0, 0.05, 0);
        };
        Fx.Spec s = Fx.sigil(id).caster(p).at(at).scale(scale);
        if (orientation != null) s.orientation(orientation);
        int inst = Fx.play((ServerLevel) p.level(), s);
        c.getSource().sendSuccess(() -> Component.literal("Sigil " + id + " #" + inst + ", formed at " + Fx.formedAt(id) + " ticks"), false);
        return inst;
    }

    private static int fx(CommandContext<CommandSourceStack> c, String style) throws CommandSyntaxException {
        ServerPlayer p = c.getSource().getPlayerOrException();
        String id = StringArgumentType.getString(c, "id");
        if (FxLib.fx(id) == null) {
            c.getSource().sendFailure(Component.literal("No effect " + id));
            return 0;
        }
        Fx.Spec s = Fx.fx(id).caster(p).target(ahead(p, 6)).look(ahead(p, 12).add(0, p.getEyeHeight(), 0));
        if (style != null) s.style(style);
        int inst = Fx.play((ServerLevel) p.level(), s);
        c.getSource().sendSuccess(() -> Component.literal("Effect " + id + " #" + inst), false);
        return inst;
    }

    private static int mesh(CommandContext<CommandSourceStack> c, double seconds) throws CommandSyntaxException {
        ServerPlayer p = c.getSource().getPlayerOrException();
        String id = StringArgumentType.getString(c, "id");
        if (FxLib.mesh(id) == null) {
            c.getSource().sendFailure(Component.literal("No mesh " + id));
            return 0;
        }
        ServerLevel sl = (ServerLevel) p.level();
        int inst = Fx.play(sl, Fx.mesh(id).caster(p).at(ahead(p, 6)).yaw(p.getYRot() + 180).duration((int) (seconds * 20)));
        Fx.at(sl, inst, (int) (seconds * 20), () -> Fx.stop(sl, inst, ""));
        c.getSource().sendSuccess(() -> Component.literal("Mesh " + id + " #" + inst), false);
        return inst;
    }

    private static int stop(CommandContext<CommandSourceStack> c) throws CommandSyntaxException {
        ServerPlayer p = c.getSource().getPlayerOrException();
        int n = Fx.stopOwned((ServerLevel) p.level(), p.getUUID());
        c.getSource().sendSuccess(() -> Component.literal("Stopped " + n), false);
        return n;
    }

    private static int reload(CommandContext<CommandSourceStack> c) {
        Fx.reloadClients(c.getSource().getLevel());
        c.getSource().sendSuccess(() -> Component.literal("Fx definitions reloaded"), false);
        return 1;
    }
}
