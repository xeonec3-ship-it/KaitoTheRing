package ru.pohsmp.core.trophy;

import java.util.ArrayList;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;
import net.minecraft.world.item.ArmorItem;
import net.minecraft.world.item.Item;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.eventbus.api.IEventBus;
import net.minecraftforge.fml.ModLoadingContext;
import net.minecraftforge.fml.config.ModConfig;
import net.minecraftforge.fml.loading.FMLEnvironment;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.ForgeRegistries;
import net.minecraftforge.registries.RegistryObject;
import ru.pohsmp.core.PohCore;

/**
 * T35 «Броня за победу над боссами культа» (docs/specs/tasks/T35_boss_armor_sets.md): 4 sets × 4 pieces + the mantle and the mask =
 * 18 items. Admin-only: no recipe, not in the creative tab, out of every loot table by {@link ru.pohsmp.core.NoLoot} (all our items),
 * not sold by anyone (no trade lists them).
 */
public final class Trophies {
    private Trophies() {}

    public static final DeferredRegister<Item> ITEMS = DeferredRegister.create(ForgeRegistries.ITEMS, PohCore.MODID);
    public static final Map<TrophySet, List<RegistryObject<Item>>> SETS = new EnumMap<>(TrophySet.class);
    public static final RegistryObject<Item> CULT_MANTLE = ITEMS.register(TrophyWear.Kind.MANTLE.id, () -> new TrophyWear(TrophyWear.Kind.MANTLE));
    public static final RegistryObject<Item> MASK_OF_LIES = ITEMS.register(TrophyWear.Kind.MASK.id, () -> new TrophyWear(TrophyWear.Kind.MASK));

    static {
        for (TrophySet s : TrophySet.values()) {
            List<RegistryObject<Item>> l = new ArrayList<>();
            for (ArmorItem.Type t : ArmorItem.Type.values()) l.add(ITEMS.register(s.item(t), () -> new TrophyArmor(s, t)));
            SETS.put(s, l);
        }
    }

    public static List<TrophyWear> wearables() {
        return List.of((TrophyWear) CULT_MANTLE.get(), (TrophyWear) MASK_OF_LIES.get());
    }

    public static TrophyWear mantle() {
        return (TrophyWear) CULT_MANTLE.get();
    }

    public static TrophyWear mask() {
        return (TrophyWear) MASK_OF_LIES.get();
    }

    /** All 18 ids (for the /give list in the letter and the tests). */
    public static List<String> ids() {
        List<String> out = new ArrayList<>();
        for (TrophySet s : TrophySet.values()) for (ArmorItem.Type t : ArmorItem.Type.values()) out.add(s.item(t));
        out.add(TrophyWear.Kind.MANTLE.id);
        out.add(TrophyWear.Kind.MASK.id);
        return out;
    }

    public static void init(IEventBus modBus) {
        ITEMS.register(modBus);
        ModLoadingContext.get().registerConfig(ModConfig.Type.SERVER, TrophyConfig.SPEC, PohCore.MODID + "-boss_armor-server.toml");
        modBus.addListener((net.minecraftforge.fml.event.lifecycle.FMLCommonSetupEvent e) -> e.enqueueWork(TrophyCurios::setup));
        MinecraftForge.EVENT_BUS.register(TrophyEvents.class);
        if (FMLEnvironment.dist.isClient()) ru.pohsmp.core.client.TrophyClient.init(modBus);
    }
}
