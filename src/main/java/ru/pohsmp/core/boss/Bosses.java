package ru.pohsmp.core.boss;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.function.Supplier;
import net.minecraft.world.effect.MobEffect;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.MobCategory;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.item.Item;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.event.entity.EntityAttributeCreationEvent;
import net.minecraftforge.eventbus.api.IEventBus;
import net.minecraftforge.fml.ModLoadingContext;
import net.minecraftforge.fml.config.ModConfig;
import net.minecraftforge.fml.event.lifecycle.FMLCommonSetupEvent;
import net.minecraftforge.fml.loading.FMLEnvironment;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.ForgeRegistries;
import net.minecraftforge.registries.RegistryObject;
import ru.pohsmp.core.PohCore;

/**
 * Entry point of the cult bosses (T26-T30): its own registers, config file, channel, events and command, so the rest of the mod is
 * touched in one line only (PohCore: {@code ru.pohsmp.core.boss.Bosses.init(modBus);}). Each boss adds itself in its own class
 * (static init) through {@link #boss}, {@link #npc}, {@link #attributes}.
 */
public final class Bosses {
    private Bosses() {}

    public static final DeferredRegister<EntityType<?>> ENTITIES = DeferredRegister.create(ForgeRegistries.ENTITY_TYPES, PohCore.MODID);
    public static final DeferredRegister<Item> ITEMS = DeferredRegister.create(ForgeRegistries.ITEMS, PohCore.MODID);
    public static final DeferredRegister<MobEffect> EFFECTS = DeferredRegister.create(ForgeRegistries.MOB_EFFECTS, PohCore.MODID);

    /** Boss id → its entity type (what /pohsmp boss <id> spawns). Only bosses that exist in code are here. */
    static final Map<String, Supplier<? extends EntityType<? extends Mob>>> SPAWNABLE = new LinkedHashMap<>();
    private static final Map<Supplier<? extends EntityType<? extends LivingEntity>>, Supplier<AttributeSupplier.Builder>> ATTRS = new LinkedHashMap<>();

    /** Registers a boss entity type and makes it spawnable with /pohsmp boss <id>. */
    public static <T extends Mob> RegistryObject<EntityType<T>> boss(String id, EntityType.EntityFactory<T> f, float w, float h,
                                                                     Supplier<AttributeSupplier.Builder> attrs) {
        RegistryObject<EntityType<T>> t = ENTITIES.register(id, () -> EntityType.Builder.of(f, MobCategory.MONSTER).sized(w, h)
                .clientTrackingRange(10).fireImmune().build(id));
        SPAWNABLE.put(id, t);
        ATTRS.put(t, attrs);
        return t;
    }

    /** Any other entity of a boss (summons, thrown weapons): registered, attributes if it is living. */
    public static <T extends LivingEntity> RegistryObject<EntityType<T>> living(String id, EntityType.EntityFactory<T> f, MobCategory cat, float w, float h,
                                                                                Supplier<AttributeSupplier.Builder> attrs) {
        RegistryObject<EntityType<T>> t = ENTITIES.register(id, () -> EntityType.Builder.of(f, cat).sized(w, h).clientTrackingRange(10).build(id));
        ATTRS.put(t, attrs);
        return t;
    }

    /** The peaceful NPC a SURRENDER boss turns into: pohsmp_core:<bossId>_npc (BossDef.surrender(at, bossId + "_npc")). */
    public static RegistryObject<EntityType<BossNpc>> npc(String bossId, float w, float h) {
        String id = bossId + "_npc";
        RegistryObject<EntityType<BossNpc>> t = ENTITIES.register(id, () -> EntityType.Builder.<BossNpc>of((type, l) -> new BossNpc(type, l, bossId),
                MobCategory.MISC).sized(w, h).clientTrackingRange(10).build(id));
        ATTRS.put(t, BossNpc::attributes);
        NPCS.put(bossId, t);
        return t;
    }

    public static final Map<String, RegistryObject<EntityType<BossNpc>>> NPCS = new LinkedHashMap<>();

    public static void init(IEventBus modBus) {
        ru.pohsmp.core.boss.cult.CultLeader.register();   // T26 (static registrations)
        ru.pohsmp.core.boss.aris.Aris.register();   // T28
        ru.pohsmp.core.boss.martin.Martin.register();     // T29
        ENTITIES.register(modBus);
        ITEMS.register(modBus);
        EFFECTS.register(modBus);
        ModLoadingContext.get().registerConfig(ModConfig.Type.SERVER, BossConfig.SPEC, PohCore.MODID + "-bosses-server.toml");
        modBus.addListener(Bosses::attributes);
        modBus.addListener((FMLCommonSetupEvent e) -> e.enqueueWork(BossNet::register));
        MinecraftForge.EVENT_BUS.register(BossScenes.Events.class);
        MinecraftForge.EVENT_BUS.register(BossFinisher.Events.class);
        MinecraftForge.EVENT_BUS.register(BossCommands.class);
        ru.pohsmp.core.boss.cult.CultLeader.events();
        ru.pohsmp.core.boss.aris.Aris.events();   // T28
        ru.pohsmp.core.boss.martin.Martin.events();       // T29
        if (FMLEnvironment.dist.isClient()) ru.pohsmp.core.boss.client.BossClient.init(modBus);
    }

    @SuppressWarnings({"unchecked", "rawtypes"})
    private static void attributes(EntityAttributeCreationEvent e) {
        for (var en : ATTRS.entrySet()) e.put((EntityType) en.getKey().get(), en.getValue().get().build());
    }
}
