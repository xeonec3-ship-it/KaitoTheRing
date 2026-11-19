package ru.pohsmp.core.client;

import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.eventbus.api.IEventBus;
import net.minecraftforge.fml.ModLoadingContext;
import net.minecraftforge.fml.config.ModConfig;

public final class ClientInit {
    private ClientInit() {}

    public static void init(IEventBus modBus) {
        ModLoadingContext.get().registerConfig(ModConfig.Type.CLIENT, ClientConfig.SPEC);
        MinecraftForge.EVENT_BUS.register(CamFixClient.class);
        MinecraftForge.EVENT_BUS.register(TierTooltip.class);
        MinecraftForge.EVENT_BUS.register(DisintegrationFx.class);
        MinecraftForge.EVENT_BUS.register(HigherFx.class);
        MinecraftForge.EVENT_BUS.register(HiddenHands.class);
        MinecraftForge.EVENT_BUS.register(HiddenEntities.class);
        MinecraftForge.EVENT_BUS.register(PohHud.class);
        MinecraftForge.EVENT_BUS.register(DownfallCut.class);
        MinecraftForge.EVENT_BUS.register(SilentWitchClient.class);
        MinecraftForge.EVENT_BUS.register(SilentMusic.class);
        MinecraftForge.EVENT_BUS.register(GateStaff.class);
        MinecraftForge.EVENT_BUS.register(GateOrder.class);
        MinecraftForge.EVENT_BUS.register(IceWallClient.class);
        MinecraftForge.EVENT_BUS.register(NpcCastClient.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.client.fx.FxClient.class);
        modBus.register(ScrollModels.class);
        modBus.addListener(TargetPoseClient::setup);
        MinecraftForge.EVENT_BUS.register(EmberHud.class);
        modBus.addListener(EmberHud::setup);
    }
}
