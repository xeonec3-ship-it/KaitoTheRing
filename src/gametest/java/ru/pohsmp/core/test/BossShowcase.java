package ru.pohsmp.core.test;

import java.util.ArrayList;
import java.util.List;
import net.minecraft.client.CameraType;
import net.minecraft.client.Minecraft;
import net.minecraft.client.Screenshot;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.client.event.CustomizeGuiOverlayEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.loading.FMLEnvironment;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.boss.PohBoss;

/**
 * T34 visual check (gradlew runClient -PdevRun -PbossShowcase, works under Xvfb): the six bosses one after another, 12 blocks in front
 * of the player, through /pohsmp boss; screenshots of the intro (fx) and of the fight (the bar) go to run/screenshots/boss_*.png; the
 * log says, per boss, whether the client got a boss event row (BossEventProgress fired) for it. Then the game quits.
 */
@Mod.EventBusSubscriber(modid = PohCore.MODID, value = net.minecraftforge.api.distmarker.Dist.CLIENT)
public final class BossShowcase {
    private BossShowcase() {}

    private static final boolean ON = System.getProperty("pohsmp.bossshow") != null;
    private static final String[] BOSSES = System.getProperty("pohsmp.bossshow.only", "ereb,aris,irina,ereb_hand,martin,cult_leader").split(",");
    /** -Dpohsmp.bossshow.dense=from,to: a shot every 4 ticks there too (the finale). */
    private static final int[] DENSE = java.util.Arrays.stream(System.getProperty("pohsmp.bossshow.dense", "0,0").split(",")).mapToInt(Integer::parseInt).toArray();
    private static final int FIRST = 100, EACH = 680;
    private static final int[] SHOTS = {6, 20, 40, 70, 250, 300, 340, 380, 420, 450, 480, 510, 540, 580, 620};

    private static ServerPlayer player;
    private static int serverTick = -1;
    private static volatile String pendingShot;
    private static volatile String current = "";
    private static final java.util.Set<String> ROWS = java.util.concurrent.ConcurrentHashMap.newKeySet();

    @SubscribeEvent
    public static void onLogin(PlayerEvent.PlayerLoggedInEvent e) {
        if (!ON || player != null || !(e.getEntity() instanceof ServerPlayer sp)) return;
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
            lvl.getGameRules().getRule(net.minecraft.world.level.GameRules.RULE_DAYLIGHT).set(false, lvl.getServer());
            BlockPos base = new BlockPos(0, 100, 0);
            for (int x = -24; x <= 24; x++)
                for (int z = -24; z <= 24; z++) {
                    lvl.setBlockAndUpdate(base.offset(x, -1, z), ((x + z & 1) == 0 ? Blocks.SMOOTH_STONE : Blocks.POLISHED_ANDESITE).defaultBlockState());
                    for (int y = 0; y < 10; y++) lvl.setBlockAndUpdate(base.offset(x, y, z), Blocks.AIR.defaultBlockState());
                }
            player.setGameMode(GameType.SURVIVAL);
            player.getAbilities().invulnerable = true;
            player.onUpdateAbilities();
            player.teleportTo(lvl, 0.5, 100, 8.5, 180, 10);   // facing north (-z)
        }
        int k = serverTick - FIRST;
        if (k < 0) return;
        int i = k / EACH, t = k % EACH;
        if (i >= BOSSES.length) {
            if (t == 0) pendingShot = "quit";
            return;
        }
        String id = BOSSES[i];
        if (t == 0) {
            current = id;
            var src = lvl.getServer().createCommandSourceStack().withLevel(lvl).withPermission(4);
            lvl.getServer().getCommands().performPrefixedCommand(src, "pohsmp boss " + id + " 0.5 100 -3.5");
        }
        for (int s : SHOTS) if (t == s) pendingShot = "boss_" + id + "_" + s;
        if (t >= DENSE[0] && t < DENSE[1] && t % 4 == 0) pendingShot = "boss_" + id + "_" + t;
        if (t == 260)
            for (Mob m : lvl.getEntitiesOfClass(Mob.class, new AABB(new Vec3(0, 100, 0), new Vec3(0, 100, 0)).inflate(60), x -> x instanceof PohBoss))
                m.setHealth(m.getMaxHealth() * 0.08f);
        if (t >= 270 && t <= 560 && t % 5 == 0) {   // the finale by ordinary blows (surrender / leave at the floor, death for the rest)
            for (Mob m : lvl.getEntitiesOfClass(Mob.class, new AABB(new Vec3(0, 100, 0), new Vec3(0, 100, 0)).inflate(60), x -> x instanceof PohBoss)) {
                if (((PohBoss) m).bossCore().inFinale()) continue;
                m.invulnerableTime = 0;
                m.hurt(lvl.damageSources().playerAttack(player), m.getMaxHealth() * 0.03f);
            }
        }
        if (t == 560) PohCore.LOG.info("[bossshow] {} finale: {}", id, lvl.getEntitiesOfClass(Mob.class, new AABB(new Vec3(0, 100, 0),
                new Vec3(0, 100, 0)).inflate(60), x -> x instanceof PohBoss).stream().map(m -> m.getHealth() + "/" + m.getMaxHealth() + " finale="
                + ((PohBoss) m).bossCore().inFinale() + " dead=" + ((PohBoss) m).bossCore().dead()).toList());
        if (t == EACH - 20) {
            for (Mob m : lvl.getEntitiesOfClass(Mob.class, new AABB(new Vec3(0, 100, 0), new Vec3(0, 100, 0)).inflate(60), x -> x instanceof PohBoss))
                m.discard();
            lvl.getEntitiesOfClass(Mob.class, new AABB(new Vec3(0, 100, 0), new Vec3(0, 100, 0)).inflate(60)).forEach(Mob::discard);
            player.teleportTo(lvl, 0.5, 100, 8.5, 180, 10);
        }
    }

    // ---- client side ----

    private static final List<String> TAKEN = new ArrayList<>();
    private static boolean created;
    private static int idle;

    @SubscribeEvent(priority = EventPriority.LOWEST, receiveCanceled = true)
    public static void onRow(CustomizeGuiOverlayEvent.BossEventProgress e) {
        if (ON) ROWS.add(current);
    }

    @SubscribeEvent
    public static void onClientTick(TickEvent.ClientTickEvent e) {
        if (!ON || e.phase != TickEvent.Phase.END || FMLEnvironment.dist.isDedicatedServer()) return;
        Minecraft mc = Minecraft.getInstance();
        if (mc.level == null && ++idle % 100 == 0) PohCore.LOG.info("[bossshow] waiting on screen {}", mc.screen);
        if (mc.level == null && mc.screen != null && !(mc.screen instanceof net.minecraft.client.gui.screens.TitleScreen) && !created
                && mc.screen.getClass().getSimpleName().contains("Onboarding")) {
            mc.options.onboardAccessibility = false;
            mc.setScreen(new net.minecraft.client.gui.screens.TitleScreen());
            return;
        }
        if (mc.level == null && mc.screen instanceof net.minecraft.client.gui.screens.TitleScreen && !created) {   // a fresh flat world
            created = true;
            var settings = new net.minecraft.world.level.LevelSettings("bossshow", GameType.CREATIVE, false, net.minecraft.world.Difficulty.NORMAL,
                    true, new net.minecraft.world.level.GameRules(), net.minecraft.world.level.WorldDataConfiguration.DEFAULT);
            mc.createWorldOpenFlows().createFreshLevel("bossshow", settings, new net.minecraft.world.level.levelgen.WorldOptions(1L, false, false),
                    ra -> ra.registryOrThrow(net.minecraft.core.registries.Registries.WORLD_PRESET)
                            .getHolderOrThrow(net.minecraft.world.level.levelgen.presets.WorldPresets.FLAT).value().createWorldDimensions());
            return;
        }
        if (mc.level == null && mc.screen != null) proceed(mc.screen);
        if (mc.player == null || mc.level == null) return;
        mc.options.hideGui = false;
        if (mc.options.getCameraType() != CameraType.FIRST_PERSON) mc.options.setCameraType(CameraType.FIRST_PERSON);
        String s = pendingShot;
        if (s == null) return;
        pendingShot = null;
        if (s.equals("quit")) {
            PohCore.LOG.info("[bossshow] screenshots: {}; boss rows seen for: {}", TAKEN, ROWS);
            mc.stop();
            return;
        }
        Screenshot.grab(mc.gameDirectory, s + ".png", mc.getMainRenderTarget(), msg -> {});
        TAKEN.add(s);
        PohCore.LOG.info("[bossshow] {} (rows so far {})", s, ROWS);
    }

    private static void proceed(Screen screen) {
        for (var w : screen.children())
            if (w instanceof net.minecraft.client.gui.components.Button b && b.getMessage().getContents()
                    instanceof net.minecraft.network.chat.contents.TranslatableContents tc && tc.getKey().equals("gui.proceed")) {
                b.onPress();
                return;
            }
    }
}
