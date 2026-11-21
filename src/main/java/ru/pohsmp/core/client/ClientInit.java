package ru.pohsmp.core.client;

import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.eventbus.api.IEventBus;
import net.minecraftforge.fml.ModLoadingContext;
import net.minecraftforge.fml.config.ModConfig;

public final class ClientInit {
    private ClientInit() {}

    public static void init(IEventBus modBus) {
        ModLoadingContext.get().registerConfig(ModConfig.Type.CLIENT, ClientConfig.SPEC);
        MinecraftForge.EVENT_BUS.register(ClientClock.class);   // monotonic animation time (fx, cameras) - before everything that reads it
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
        MinecraftForge.EVENT_BUS.register(CastLockClient.class);   // owner 21.11: nothing but the camera while an animated spell runs
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.client.fx.gate.GateManaRender.class);
        MinecraftForge.EVENT_BUS.register(IceWallClient.class);
        MinecraftForge.EVENT_BUS.register(NpcCastClient.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.client.fx.FxClient.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.client.illusion.IllusionClient.class);   // T22
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.client.illusion.Copies.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.client.illusion.ZoneDraw.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.client.illusion.MirrorReflections.class);   // T22 reflections in the labyrinth
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.client.illusion.DreamScreen.class);   // T22 dream: mirror, sky, death, waking
        MinecraftForge.EVENT_BUS.register(ScriptedWalk.class);   // Coven Arrival: the retinue players walk
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.client.illusion.ErasedClient.class);   // T24
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.client.mythic.SkyClient.class);   // T23
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.client.illusion.Ghosts.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.client.illusion.DreamMusic.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.client.nightmare.NightmareClient.class);   // T25
        modBus.addListener(ru.pohsmp.core.client.nightmare.NightmareRender::register);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.client.nightmare.NightmareWorld.class);   // T25 stage 3: the world rots
        modBus.addListener(ru.pohsmp.core.client.nightmare.NightmareWorld::colors);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.client.nightmare.HouseClient.class);   // T25 «Дом, которого нет»
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.client.nightmare.NoAwakeningClient.class);   // T25 «Пробуждение не наступит»
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.client.nightmare.NightmarePeople.class);   // T25 people by stage
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.client.nightmare.WakingClient.class);   // T22 «Кошмар наяву»: people as the caster's monster
        modBus.register(ScrollModels.class);
        modBus.addListener(TargetPoseClient::setup);
        MinecraftForge.EVENT_BUS.register(EmberHud.class);
        MinecraftForge.EVENT_BUS.register(EmberWhipClient.class);   // T14: the physics whip of the whip form
        modBus.addListener(EmberHud::setup);
    }
}
