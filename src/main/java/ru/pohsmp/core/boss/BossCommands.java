package ru.pohsmp.core.boss;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.arguments.StringArgumentType;
import com.mojang.brigadier.context.CommandContext;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.SharedSuggestionProvider;
import net.minecraft.commands.arguments.coordinates.Vec3Argument;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.MobSpawnType;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.RegisterCommandsEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;

/**
 * /pohsmp boss <cult_leader|irina|aris|martin|ereb> [x y z] — op level 2 only; the only way a cult boss appears (no natural spawn).
 * Without a position: 8 blocks before the admin, facing the admin. The «pohsmp» node merges with FxCommands' one.
 */
public final class BossCommands {
    private BossCommands() {}

    /** All five ids (the ones without code yet answer «not implemented»). */
    private static final String[] IDS = {"cult_leader", "irina", "aris", "martin", "ereb", "ereb_hand"};

    @SubscribeEvent
    public static void onRegister(RegisterCommandsEvent e) {
        register(e.getDispatcher());
    }

    private static void register(CommandDispatcher<CommandSourceStack> d) {
        d.register(Commands.literal("pohsmp").requires(s -> s.hasPermission(2))
                .then(Commands.literal("boss").requires(s -> s.hasPermission(2))
                        .then(Commands.argument("id", StringArgumentType.word())
                                .suggests((c, b) -> SharedSuggestionProvider.suggest(IDS, b))
                                .executes(c -> spawn(c, null))
                                .then(Commands.argument("pos", Vec3Argument.vec3()).executes(c -> spawn(c, Vec3Argument.getVec3(c, "pos")))))));
    }

    private static int spawn(CommandContext<CommandSourceStack> c, Vec3 at) {
        String id = StringArgumentType.getString(c, "id");
        var sup = Bosses.SPAWNABLE.get(id);
        if (sup == null) {
            c.getSource().sendFailure(Component.translatableWithFallback("ui.pohsmp_core.boss.unknown", "Босс %s ещё не сделан (или неизвестен)", id));
            return 0;
        }
        ServerLevel sl = c.getSource().getLevel();
        Vec3 src = c.getSource().getPosition();
        float yaw;
        Vec3 pos;
        if (at == null) {
            float look = c.getSource().getRotation().y;
            Vec3 fwd = Vec3.directionFromRotation(0, look);
            pos = src.add(fwd.scale(8));
            yaw = look + 180;
        } else {
            pos = at;
            ServerPlayer near = sl.getNearestPlayer(at.x, at.y, at.z, 64, false) instanceof ServerPlayer sp ? sp : null;
            Vec3 to = near != null ? near.position() : src;
            yaw = (float) (Mth.atan2(to.z - at.z, to.x - at.x) * Mth.RAD_TO_DEG) - 90;
        }
        EntityType<? extends Mob> type = sup.get();
        Mob m = type.create(sl);
        if (!(m instanceof PohBoss boss)) {
            c.getSource().sendFailure(Component.literal("Not a boss: " + id));
            return 0;
        }
        m.moveTo(pos.x, pos.y, pos.z, yaw, 0);
        m.setYHeadRot(yaw);
        m.setYBodyRot(yaw);
        m.finalizeSpawn(sl, sl.getCurrentDifficultyAt(m.blockPosition()), MobSpawnType.COMMAND, null, null);
        m.setPersistenceRequired();
        boss.onBossPreSpawn();
        sl.addFreshEntity(m);
        boss.bossCore().begin(sl, pos);
        c.getSource().sendSuccess(() -> Component.translatableWithFallback("ui.pohsmp_core.boss.spawned", "Вызван: %s", m.getDisplayName()), true);
        return 1;
    }
}
