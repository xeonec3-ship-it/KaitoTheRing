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
        MinecraftForge.EVENT_BUS.register(BossMusicClient.class);   // T33: fades / crossfades by the client tick
        MinecraftForge.EVENT_BUS.register(BossSoundClient.class);   // boss sounds 21.11: animation sound keyframes, aura loops
        BossMusicClient.quietMissingParts();
        modBus.addListener(BossSayClient::overlays);   // 21.11: the bosses' lines as an on-screen subtitle
        modBus.addListener(BossPoseClient::setup);
        modBus.addListener(BossClient::renderers);
        modBus.addListener(BossClient::setup);
    }

    private static void setup(FMLClientSetupEvent e) {
        e.enqueueWork(ru.pohsmp.core.boss.cult.client.CultLeaderClient::setup);   // T26: camera plans
        e.enqueueWork(ru.pohsmp.core.boss.irina.client.IrinaClient::setup);       // T27: camera plans
        e.enqueueWork(ru.pohsmp.core.boss.aris.client.ArisClient::setup);   // T28: camera plans, NPC look, steam fog
        e.enqueueWork(ru.pohsmp.core.boss.martin.client.MartinClient::setup);     // T29: camera plans, NPC look, status icons
        e.enqueueWork(ru.pohsmp.core.boss.ereb.client.ErebClient::setup);         // T30: camera plans, «Предательство»
        e.enqueueWork(ru.pohsmp.core.boss.erebhand.client.ErebHandClient::setup); // T31: camera plans, the false arena
    }

    private static void renderers(EntityRenderersEvent.RegisterRenderers e) {
        for (var t : Bosses.NPCS.values()) e.registerEntityRenderer(t.get(), BossNpcRenderer::new);
        ru.pohsmp.core.boss.cult.client.CultLeaderClient.renderers(e);
        ru.pohsmp.core.boss.irina.client.IrinaClient.renderers(e);   // T27
        ru.pohsmp.core.boss.aris.client.ArisClient.renderers(e);   // T28
        ru.pohsmp.core.boss.martin.client.MartinClient.renderers(e);   // T29
        e.registerEntityRenderer(ru.pohsmp.core.spell.reward.Rewards.SOLDIER.get(), ru.pohsmp.core.boss.martin.client.MartinRenderers.BannerSoldier::new);   // T34
        ru.pohsmp.core.boss.ereb.client.ErebClient.renderers(e);
        ru.pohsmp.core.boss.erebhand.client.ErebHandClient.renderers(e);   // T31
    }

    public static void handle(BossNet.Msg m) {
        switch (m.kind) {
            case BossNet.BAR, BossNet.BAR_STOP -> BossBarClient.onMsg(m);
            case BossNet.SCENE, BossNet.SCENE_STOP -> BossCam.onMsg(m);
            case BossNet.TITLE, BossNet.SUBTITLE -> BossHudClient.onMsg(m);
            case BossNet.SAY -> BossSayClient.onMsg(m);
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
        BossSayClient.clear();
        BossMusicClient.clear();
        BossSoundClient.clear();
    }
}
