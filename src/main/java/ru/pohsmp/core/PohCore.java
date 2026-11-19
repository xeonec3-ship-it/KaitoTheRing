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
        MinecraftForge.EVENT_BUS.register(SchoolSeals.class);
        MinecraftForge.EVENT_BUS.register(DisintegrationSpell.DisintegrationEvents.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.spell.TargetPose.Events.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.spell.DisintegrationReplicaSpell.ReplicaEvents.class);
        MinecraftForge.EVENT_BUS.register(HigherEvents.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.spell.Tasks.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.spell.PohEvents.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.spell.Disp.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.spell.TabooSpell.TabooEvents.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.spell.SoulDevourSpell.SoulDevourEvents.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.spell.MadnessSpell.MadnessEvents.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.spell.Marks.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.spell.IllusionSpell.IllusionEvents.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.spell.MirrorPrisonSpell.MirrorPrisonEvents.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.spell.FrozenHourSpell.FrozenHourEvents.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.spell.CountdownSpell.CountdownEvents.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.spell.ArkSpell.ArkEvents.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.spell.DownfallSpell.DownfallEvents.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.spell.Cutscene.CutsceneEvents.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.spell.silent.SilentGateSpell.SilentGateEvents.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.spell.MilkyWaySpell.MilkyWayEvents.class);
        MinecraftForge.EVENT_BUS.register(AnimatedStaff.StaffAnimEvents.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.spell.silent.SageBarrierSpell.BarrierEvents.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.spell.silent.SilentSpell.Aggro.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.spell.SpaceClosureSpell.SpaceClosureEvents.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.spell.CovenArrivalSpell.CovenArrivalEvents.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.fx.Fx.FxServerEvents.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.fx.FxCommands.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.silent.SilentWitchEvents.class);
        ru.pohsmp.core.silent.compat.Compat.common(modBus);
        MinecraftForge.EVENT_BUS.register(Hidden.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.spell.NpcCast.Events.class);
        MinecraftForge.EVENT_BUS.register(Charges.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.spell.JointCast.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.ember.EmberBlade.Events.class);
        if (ru.pohsmp.core.ember.EmberEpicFight.ON) ru.pohsmp.core.ember.EmberEpicFight.init(modBus);   // T14 animations, weapon type
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
            if (!e.has(type, Reg.SILENT_POWER.get())) e.add(type, Reg.SILENT_POWER.get());
            if (!e.has(type, Reg.SILENT_RESIST.get())) e.add(type, Reg.SILENT_RESIST.get());
            if (!e.has(type, Reg.SILENT_CAST.get())) e.add(type, Reg.SILENT_CAST.get());
        }
    }
}
