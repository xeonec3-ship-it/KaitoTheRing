package ru.pohsmp.core.test;

import com.mojang.authlib.GameProfile;
import io.netty.channel.embedded.EmbeddedChannel;
import io.redspace.ironsspellbooks.api.magic.MagicData;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import net.minecraft.client.CameraType;
import net.minecraft.client.Minecraft;
import net.minecraft.client.Screenshot;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.core.BlockPos;
import net.minecraft.network.Connection;
import net.minecraft.network.protocol.PacketFlow;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Blocks;
import net.minecraftforge.client.event.RenderGuiEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.loading.FMLEnvironment;
import ru.pohsmp.core.Charges;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.Scrolls;
import ru.pohsmp.core.client.JointFx;

/**
 * Visual check in the real client (gradlew runClient -PdevRun -Pshowcase, works under Xvfb): a second mage appears in front
 * of the player, both cast Frozen Hour from scrolls (the player's has 3 charges), the casts merge. Screenshots go to
 * run/screenshots: joint_*.png (double outline of the sigils, shortened cast bar) and tooltip.png ("Заряды: 2/3"); then the game quits.
 */
@Mod.EventBusSubscriber(modid = PohCore.MODID, value = net.minecraftforge.api.distmarker.Dist.CLIENT)
public final class Showcase {
    private Showcase() {}

    private static final boolean ON = System.getProperty("pohsmp.showcase") != null;
    private static final ResourceLocation SPELL = new ResourceLocation(PohCore.MODID, "frozen_hour");

    // ---- server side (integrated server) ----

    private static ServerPlayer player, mage;
    private static int serverTick = -1;

    @SubscribeEvent
    public static void onLogin(PlayerEvent.PlayerLoggedInEvent e) {
        if (!ON || player != null || !(e.getEntity() instanceof ServerPlayer sp) || sp.getGameProfile().getName().startsWith("mage")) return;
        player = sp;
        serverTick = 0;
    }

    @SubscribeEvent
    public static void onServerTick(TickEvent.ServerTickEvent e) {
        if (!ON || serverTick < 0 || e.phase != TickEvent.Phase.END) return;
        serverTick++;
        ServerLevel lvl = player.serverLevel();
        if (serverTick == 20) {
            lvl.setDayTime(6000);
            lvl.setWeatherParameters(6000, 0, false, false);
            BlockPos base = new BlockPos(0, 100, 0);
            for (int x = -10; x <= 10; x++)
                for (int z = -10; z <= 10; z++) {
                    lvl.setBlockAndUpdate(base.offset(x, -1, z), ((x + z & 1) == 0 ? Blocks.SMOOTH_STONE : Blocks.POLISHED_ANDESITE).defaultBlockState());
                    for (int y = 0; y < 8; y++) lvl.setBlockAndUpdate(base.offset(x, y, z), Blocks.AIR.defaultBlockState());
                }
            player.setGameMode(GameType.SURVIVAL);
            player.teleportTo(lvl, 0.5, 100, 2.5, 180, 25);   // facing north (-z), toward the mage
            ItemStack own = Scrolls.make(SPELL, 1, null);
            own.getOrCreateTag().putInt(Charges.NBT, 3);
            player.setItemInHand(InteractionHand.MAIN_HAND, own);
            mage = new ServerPlayer(lvl.getServer(), lvl, new GameProfile(UUID.randomUUID(), "mage"));
            Connection c = new Connection(PacketFlow.SERVERBOUND);
            new EmbeddedChannel(c);
            lvl.getServer().getPlayerList().placeNewPlayer(c, mage);
            mage.setGameMode(GameType.SURVIVAL);
            mage.teleportTo(lvl, 0.5, 100, -1.5, 0, 0);   // 4 blocks in front, facing the player
            mage.setItemInHand(InteractionHand.MAIN_HAND, Scrolls.make(SPELL, 1, null));
        }
        if (serverTick == 80) mage.getMainHandItem().use(lvl, mage, InteractionHand.MAIN_HAND);
        if (serverTick == 88) player.getMainHandItem().use(lvl, player, InteractionHand.MAIN_HAND);
        if (serverTick == 90) PohCore.LOG.info("[showcase] player casting {}, remaining {}", MagicData.getPlayerMagicData(player).isCasting(),
                MagicData.getPlayerMagicData(player).getCastDurationRemaining());
    }

    // ---- client side ----

    private static int clientTick = -1, jointSeen = -1;
    private static boolean tooltip;
    private static final List<String> SHOTS = new ArrayList<>();

    @SubscribeEvent
    public static void onClientTick(TickEvent.ClientTickEvent e) {
        if (!ON || e.phase != TickEvent.Phase.END || FMLEnvironment.dist.isDedicatedServer()) return;
        Minecraft mc = Minecraft.getInstance();
        if (mc.level == null && mc.screen != null) proceed(mc.screen);   // the world made by the test server is "experimental"
        if (mc.player == null || mc.level == null) return;
        clientTick++;
        if (clientTick == 30) {
            mc.options.setCameraType(CameraType.THIRD_PERSON_BACK);
            mc.options.hideGui = false;
        }
        if (jointSeen < 0 && JointFx.isJoint(mc.player)) jointSeen = clientTick;
        if (jointSeen >= 0) {
            int t = clientTick - jointSeen;
            if (t == 6) shot(mc, "joint_start");
            if (t == 14) shot(mc, "joint_mid");
            if (t == 30) {   // past the end of the merged cast: one charge spent
                tooltip = true;
                mc.options.setCameraType(CameraType.FIRST_PERSON);
            }
            if (t == 34) shot(mc, "tooltip");
            if (t == 40) {
                PohCore.LOG.info("[showcase] screenshots: {}, hand: {} charges {}/{}", SHOTS, mc.player.getMainHandItem(),
                        Charges.get(mc.player.getMainHandItem()), Charges.max(mc.player.getMainHandItem()));
                mc.stop();
            }
        }
        if (clientTick > 2400) mc.stop();   // never hang
    }

    private static void proceed(Screen screen) {
        for (var w : screen.children())
            if (w instanceof net.minecraft.client.gui.components.Button b && b.getMessage().getContents()
                    instanceof net.minecraft.network.chat.contents.TranslatableContents tc && tc.getKey().equals("gui.proceed")) {
                b.onPress();
                return;
            }
    }

    private static void shot(Minecraft mc, String name) {
        Screenshot.grab(mc.gameDirectory, name + ".png", mc.getMainRenderTarget(), msg -> {});
        SHOTS.add(name);
    }

    @SubscribeEvent
    public static void onGui(RenderGuiEvent.Post e) {
        if (!ON || !tooltip) return;
        Minecraft mc = Minecraft.getInstance();
        ItemStack st = mc.player.getMainHandItem();
        if (st.isEmpty()) return;
        e.getGuiGraphics().renderTooltip(mc.font, Screen.getTooltipFromItem(mc, st), Optional.empty(), 16, 24);
    }
}
