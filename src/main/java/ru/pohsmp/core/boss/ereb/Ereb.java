package ru.pohsmp.core.boss.ereb;

import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.MobCategory;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.Rarity;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.registries.RegistryObject;
import ru.pohsmp.core.boss.BossDef;
import ru.pohsmp.core.boss.Bosses;

/**
 * T30 «Эреб, Первый Предатель» / «Глава 1 Ячейки Культа» (pohsmp_core:ereb; docs/specs/tasks/T30_ereb_boss.md): a mage with a rapier
 * on the illusion mechanics of T22. Three phases («Две правды» 100–66, «Чужое лицо» 66–33, «Предательство» 33–5), the specials
 * «Ложный союзник» (50%) and «Зеркальный лабиринт» (20%), four spells of his own, the finale at 5%: «Сон бабочки» from his point and
 * he is gone (LEAVE). Immune to illusions. Numbers: [ereb] (balance_bosses.md, section 6).
 */
public final class Ereb {
    private Ereb() {}

    public static final String ID = "ereb";
    /** His colour (the gold of the title and the bar). */
    public static final int COLOR = 0xE8C766;

    public static final BossDef DEF = BossDef.builder(ID)
            .phases(0.66, 0.33)
            .standardBar()                 // ereb_bossbar, _p2, _p3 (+ _flash)
            .color(COLOR)
            .leave(0.05)                   // «Сон бабочки» and gone
            .special("false_ally", 0.50)   // balance: false_ally_at
            .special("labyrinth", 0.20)    // balance: labyrinth_at
            .finisher(true)                // owner 20.11: «всем боссам добивание» (ТЗ «Добивание»)
            .music("music.ereb")
            .title("ereb")
            .fightRadius(40)
            .build();

    public static RegistryObject<EntityType<ErebEntity>> TYPE;
    public static RegistryObject<EntityType<ErebReflection>> REFLECTION;
    public static RegistryObject<EntityType<ErebShard>> SHARD;
    public static RegistryObject<EntityType<ErebDreamPoint>> DREAM_POINT;
    public static RegistryObject<Item> RAPIER;

    /** Called from Bosses.init before the registers are attached. */
    public static void register() {
        TYPE = Bosses.boss(ID, ErebEntity::new, 0.6f, 1.95f, ErebEntity::attributes);
        REFLECTION = Bosses.living("ereb_reflection", ErebReflection::new, MobCategory.MISC, 0.6f, 1.95f, ErebEntity::attributes);
        DREAM_POINT = Bosses.living("ereb_dream_point", ErebDreamPoint::new, MobCategory.MISC, 0.2f, 0.2f, ErebDreamPoint::attributes);
        SHARD = Bosses.ENTITIES.register("ereb_shard", () -> EntityType.Builder.<ErebShard>of(ErebShard::new, MobCategory.MISC)
                .sized(0.3f, 0.3f).clientTrackingRange(8).updateInterval(1).noSummon().fireImmune().build("ereb_shard"));
        // his own rapier: no recipe, never given to players (not in the creative tab)
        RAPIER = Bosses.ITEMS.register("ereb_rapier", () -> new Item(new Item.Properties().stacksTo(1).rarity(Rarity.EPIC).fireResistant()));
    }

    public static void events() {
        MinecraftForge.EVENT_BUS.register(ErebFight.Events.class);
    }
}
