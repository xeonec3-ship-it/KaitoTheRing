package ru.pohsmp.core;

import com.mojang.logging.LogUtils;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.event.entity.EntityAttributeModificationEvent;
import net.minecraftforge.eventbus.api.IEventBus;
import net.minecraftforge.fml.ModLoadingContext;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.config.ModConfig;
import net.minecraftforge.fml.event.lifecycle.FMLCommonSetupEvent;
import net.minecraftforge.fml.javafmlmod.FMLJavaModLoadingContext;
import net.minecraftforge.fml.loading.FMLEnvironment;
import org.slf4j.Logger;
import ru.pohsmp.core.client.ClientInit;
import ru.pohsmp.core.net.Net;
import ru.pohsmp.core.spell.DisintegrationSpell;

@Mod(PohCore.MODID)
public class PohCore {
    public static final String MODID = "pohsmp_core";
    public static final Logger LOG = LogUtils.getLogger();

    public PohCore() {
        LOG.info("[pohsmp_core] loaded, dist={}", FMLEnvironment.dist);
        IEventBus modBus = FMLJavaModLoadingContext.get().getModEventBus();
        Reg.register(modBus);
        modBus.addListener(PohCore::commonSetup);
        modBus.addListener(PohCore::attributes);
        ModLoadingContext.get().registerConfig(ModConfig.Type.SERVER, ServerConfig.SPEC);
        MinecraftForge.EVENT_BUS.register(DivineEvents.class);
        MinecraftForge.EVENT_BUS.register(DisintegrationSpell.Events.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.spell.DisintegrationReplicaSpell.Events.class);
        MinecraftForge.EVENT_BUS.register(HigherEvents.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.spell.Tasks.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.spell.PohEvents.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.spell.Disp.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.spell.TabooSpell.Events.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.spell.SoulDevourSpell.Events.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.spell.MadnessSpell.Events.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.spell.Marks.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.spell.IllusionSpell.Events.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.spell.MirrorPrisonSpell.Events.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.spell.FrozenHourSpell.Events.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.spell.ArkSpell.Events.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.spell.DownfallSpell.Events.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.spell.EightShieldsSpell.EightShieldsEvents.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.spell.Cutscene.CutsceneEvents.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.spell.MilkyWaySpell.MilkyWayEvents.class);
        MinecraftForge.EVENT_BUS.register(AnimatedStaff.StaffAnimEvents.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.spell.SpaceClosureSpell.SpaceClosureEvents.class);
        if (FMLEnvironment.dist == Dist.CLIENT) ClientInit.init(modBus);
    }

    private static void commonSetup(FMLCommonSetupEvent e) {
        e.enqueueWork(Net::register);
    }

    @SuppressWarnings("unchecked")
    private static void attributes(EntityAttributeModificationEvent e) {
        for (EntityType<? extends LivingEntity> type : e.getTypes()) {
            if (!e.has(type, Reg.DIVINE_POWER.get())) e.add(type, Reg.DIVINE_POWER.get());
            if (!e.has(type, Reg.DIVINE_RESIST.get())) e.add(type, Reg.DIVINE_RESIST.get());
            if (!e.has(type, Reg.HIGHER_POWER.get())) e.add(type, Reg.HIGHER_POWER.get());
            if (!e.has(type, Reg.HIGHER_RESIST.get())) e.add(type, Reg.HIGHER_RESIST.get());
            if (!e.has(type, Reg.FORBIDDEN_POWER.get())) e.add(type, Reg.FORBIDDEN_POWER.get());
            if (!e.has(type, Reg.FORBIDDEN_RESIST.get())) e.add(type, Reg.FORBIDDEN_RESIST.get());
        }
    }
}
