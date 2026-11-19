package ru.pohsmp.core.test;

import java.util.ArrayList;
import java.util.List;
import net.minecraft.client.Minecraft;
import net.minecraft.client.Screenshot;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Blocks;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.loading.FMLEnvironment;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.client.DownfallCut;
import ru.pohsmp.core.client.SilentMusic;
import io.redspace.ironsspellbooks.api.spells.CastSource;

/**
 * Visual check of "Gate" (T03) in the real client: gradlew runClient -PdevRun -PgateShowcase (works under Xvfb; needs the world
 * run/saves/showcase, e.g. a copy of the game test world). The player stands on a platform with the Silent Witch staff, husks 16-24
 * blocks ahead; Gate is cast through Iron's. Screenshots of the camera scene go to run/screenshots/gate_*.png at the storyboard moments,
 * the client log gets the music/silence state ([gate-showcase]); then the game quits.
 */
@Mod.EventBusSubscriber(modid = PohCore.MODID, value = net.minecraftforge.api.distmarker.Dist.CLIENT)
public final class GateShowcase {
    private GateShowcase() {}

    private static final boolean ON = System.getProperty("pohsmp.gateshow") != null;
    /** Seconds of the scene to photograph: intro, hand, gate appears, gate + halo, "shh", circles, finger up, seals, main beam, wide, crystal. */
    private static final double[] AT = {6, 18, 24.5, 30, 39, 45, 49.5, 51, 53.5, 58, 63.5};

    private static ServerPlayer player;
    private static int serverTick = -1;

    @SubscribeEvent
    public static void onLogin(PlayerEvent.PlayerLoggedInEvent e) {
        if (!ON || player != null || !(e.getEntity() instanceof ServerPlayer sp)) return;
        player = sp;
        serverTick = 0;
    }

    private static void husk(ServerLevel lvl, double x, double z) {
        Mob m = EntityType.HUSK.create(lvl);
        m.moveTo(x, 100, z, 0, 0);
        m.setNoAi(true);
        m.setPersistenceRequired();
        m.getAttribute(Attributes.MAX_HEALTH).setBaseValue(2000);
        m.setHealth(2000);
        lvl.addFreshEntity(m);
    }

    @SubscribeEvent
    public static void onServerTick(TickEvent.ServerTickEvent e) {
        if (!ON || serverTick < 0 || e.phase != TickEvent.Phase.END) return;
        serverTick++;
        ServerLevel lvl = player.serverLevel();
        if (serverTick == 20) {
            lvl.setDayTime(12000);   // sunset, before monsters spawn
            lvl.setWeatherParameters(6000, 0, false, false);
            BlockPos base = new BlockPos(0, 100, 0);
            for (int x = -30; x <= 30; x++)
                for (int z = -12; z <= 40; z++) {
                    lvl.setBlockAndUpdate(base.offset(x, -1, z), ((x + z & 1) == 0 ? Blocks.SMOOTH_STONE : Blocks.POLISHED_ANDESITE).defaultBlockState());
                    for (int y = 0; y < 40; y++) lvl.setBlockAndUpdate(base.offset(x, y, z), Blocks.AIR.defaultBlockState());
                }
            player.setGameMode(GameType.SURVIVAL);
            player.teleportTo(lvl, 0.5, 100, 0.5, 0, 0);   // facing south (+z)
            player.setItemInHand(InteractionHand.MAIN_HAND, new ItemStack(Reg.SILENT_WITCH_STAFF.get()));
            husk(lvl, 0.5, 18.5);
            husk(lvl, 6.5, 22.5);
            husk(lvl, -7.5, 26.5);
        }
        if (serverTick > 80 && serverTick % 20 == 0 && serverTick < 400)
            PohCore.LOG.info("[gate-showcase] server t={} casting {} remaining {}", serverTick - 80,
                    io.redspace.ironsspellbooks.api.magic.MagicData.getPlayerMagicData(player).isCasting(),
                    io.redspace.ironsspellbooks.api.magic.MagicData.getPlayerMagicData(player).getCastDurationRemaining());
        if (serverTick == 80) {
            boolean ok = Reg.SILENT_GATE.get().attemptInitiateCast(player.getMainHandItem(), 1, lvl, player, CastSource.SPELLBOOK, true, "mainhand");
            PohCore.LOG.info("[gate-showcase] cast started: {}", ok);
        }
    }

    // ---- client side ----

    private static int clientTick = -1, sceneStart = -1, next;
    private static final List<String> SHOTS = new ArrayList<>();

    @SubscribeEvent
    public static void onClientTick(TickEvent.ClientTickEvent e) {
        if (!ON || e.phase != TickEvent.Phase.END || FMLEnvironment.dist.isDedicatedServer()) return;
        Minecraft mc = Minecraft.getInstance();
        if (mc.level == null && mc.screen != null) proceed(mc.screen);   // the world made by the test server is "experimental"
        if (mc.player == null || mc.level == null) return;
        clientTick++;
        if (sceneStart < 0 && DownfallCut.active()) {
            sceneStart = clientTick;
            PohCore.LOG.info("[gate-showcase] scene started, silence {}", SilentMusic.silent());
        }
        if (sceneStart >= 0 && next < AT.length && clientTick - sceneStart >= AT[next] * 20) {
            String name = String.format("gate_%02d_%04.1fs", next, AT[next]);
            Screenshot.grab(mc.gameDirectory, name + ".png", mc.getMainRenderTarget(), msg -> {});
            SHOTS.add(name);
            PohCore.LOG.info("[gate-showcase] {} camera {} silence {}", name, DownfallCut.active(), SilentMusic.silent());
            next++;
        }
        if (sceneStart >= 0 && clientTick - sceneStart == 70 * 20) {
            PohCore.LOG.info("[gate-showcase] after the scene: camera {} silence {}; screenshots {}", DownfallCut.active(), SilentMusic.silent(), SHOTS);
            mc.stop();
        }
        if (clientTick > 4000) mc.stop();   // never hang
    }

    private static void proceed(net.minecraft.client.gui.screens.Screen screen) {
        for (var w : screen.children())
            if (w instanceof net.minecraft.client.gui.components.Button b && b.getMessage().getContents()
                    instanceof net.minecraft.network.chat.contents.TranslatableContents tc && tc.getKey().equals("gui.proceed")) {
                b.onPress();
                return;
            }
    }
}
