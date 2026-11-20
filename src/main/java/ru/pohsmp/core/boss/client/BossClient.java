package ru.pohsmp.core.boss.client;

import java.util.HashMap;
import java.util.Map;
import net.minecraftforge.client.event.ClientPlayerNetworkEvent;
import net.minecraftforge.client.event.EntityRenderersEvent;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.eventbus.api.IEventBus;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.event.lifecycle.FMLClientSetupEvent;
import ru.pohsmp.core.boss.BossNet;
import ru.pohsmp.core.boss.Bosses;

/** Client half of the bosses: message dispatch, events, renderers, the camera plans of each boss. */
public final class BossClient {
    private BossClient() {}

    /** Render flags of boss entities (BossNet.LOOK_*), by entity id. */
    private static final Map<Integer, Integer> LOOKS = new HashMap<>();

    public static int look(int entityId) {
        return LOOKS.getOrDefault(entityId, 0);
    }

    public static boolean look(int entityId, int flag) {
        return (look(entityId) & flag) != 0;
    }

    public static void init(IEventBus modBus) {
        MinecraftForge.EVENT_BUS.register(BossClient.class);
        MinecraftForge.EVENT_BUS.register(BossBarClient.class);
        MinecraftForge.EVENT_BUS.register(BossCam.class);
        MinecraftForge.EVENT_BUS.register(BossHudClient.class);
        modBus.addListener(BossPoseClient::setup);
        modBus.addListener(BossClient::renderers);
        modBus.addListener(BossClient::setup);
    }

    private static void setup(FMLClientSetupEvent e) {
        e.enqueueWork(ru.pohsmp.core.boss.cult.client.CultLeaderClient::setup);   // T26: camera plans
    }

    private static void renderers(EntityRenderersEvent.RegisterRenderers e) {
        for (var t : Bosses.NPCS.values()) e.registerEntityRenderer(t.get(), BossNpcRenderer::new);
        ru.pohsmp.core.boss.cult.client.CultLeaderClient.renderers(e);
    }

    public static void handle(BossNet.Msg m) {
        switch (m.kind) {
            case BossNet.BAR, BossNet.BAR_STOP -> BossBarClient.onMsg(m);
            case BossNet.SCENE, BossNet.SCENE_STOP -> BossCam.onMsg(m);
            case BossNet.TITLE, BossNet.SUBTITLE -> BossHudClient.onMsg(m);
            case BossNet.MUSIC -> BossMusicClient.onMsg(m);
            case BossNet.POSE -> BossPoseClient.onMsg(m);
            case BossNet.LOOK -> {
                if (m.b == 0) LOOKS.remove(m.a);
                else LOOKS.put(m.a, m.b);
            }
            default -> {}
        }
    }

    @SubscribeEvent
    public static void onLogout(ClientPlayerNetworkEvent.LoggingOut e) {
        LOOKS.clear();
        BossBarClient.clear();
        BossHudClient.clear();
        BossMusicClient.clear();
    }
}
