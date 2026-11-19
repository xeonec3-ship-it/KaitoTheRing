package ru.pohsmp.core;

import com.mojang.brigadier.arguments.IntegerArgumentType;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.EntityArgument;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.Entity;
import net.minecraftforge.event.RegisterCommandsEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;

/** /pohsmp hide &lt;targets&gt; &lt;seconds&gt; (0 = until shown) and /pohsmp show &lt;targets&gt;, op level 2. */
public final class HideCommands {
    private HideCommands() {}

    @SubscribeEvent
    public static void onRegister(RegisterCommandsEvent e) {
        e.getDispatcher().register(Commands.literal("pohsmp").requires(s -> s.hasPermission(2))
                .then(Commands.literal("hide").then(Commands.argument("targets", EntityArgument.entities())
                        .then(Commands.argument("seconds", IntegerArgumentType.integer(0)).executes(c -> {
                            int n = 0, sec = IntegerArgumentType.getInteger(c, "seconds");
                            for (Entity t : EntityArgument.getEntities(c, "targets")) {
                                Hidden.hide(t, sec * 20);
                                n++;
                            }
                            reply(c.getSource(), "Скрыто: " + n);
                            return n;
                        }))))
                .then(Commands.literal("show").then(Commands.argument("targets", EntityArgument.entities()).executes(c -> {
                    int n = 0;
                    for (Entity t : EntityArgument.getEntities(c, "targets")) {
                        if (Hidden.isHidden(t)) n++;
                        Hidden.show(t);
                    }
                    reply(c.getSource(), "Показано: " + n);
                    return n;
                }))));
    }

    private static void reply(CommandSourceStack s, String text) {
        s.sendSuccess(() -> Component.literal(text), false);
    }
}
