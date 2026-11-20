package ru.pohsmp.core.boss.erebhand;

import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.MobCategory;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.Rarity;
import net.minecraftforge.registries.RegistryObject;
import ru.pohsmp.core.boss.BossDef;
import ru.pohsmp.core.boss.Bosses;

/**
 * T31 «Эреб, Длань Лжи» / «Глава Культа Меллисто» (pohsmp_core:ereb_hand; docs/specs/tasks/T31_ereb_hand_of_lies.md): the later, stronger
 * Ereb who leads the cult after Tyros. T30 (pohsmp_core:ereb) stays as it is; nothing of it is shared but the T22 spells. Three phases
 * («Лживое слово» 100–66, «Длань» 66–33, «Глава Культа» 33–20), the specials «Длань Лжи» (66%), «Падение маски» (45%) and «Сон Бабочки:
 * Полное Раскрытие» (20%: the rest of the fight is fought inside the dream), four spells of his own, the false death when his health
 * is gone (he falls apart into butterflies: LEAVE at a hair over zero), the finisher. Numbers: [ereb_hand] (ErebHandConfig, a draft).
 */
public final class ErebHand {
    private ErebHand() {}

    public static final String ID = "ereb_hand";
    /** His colour: the gold of the title (the crimson of the cult is in the bar). */
    public static final int COLOR = 0xE8B04A;
    /** «Health is gone»: the false death starts here (a LEAVE finale — he never really dies, he flees as butterflies). */
    public static final double FALSE_DEATH_AT = 0.002;

    public static final BossDef DEF = BossDef.builder(ID)
            .phases(0.66, 0.33)
            .standardBar()                     // ereb_hand_bossbar, _p2, _p3 (+ _flash)
            .color(COLOR)
            .leave(FALSE_DEATH_AT)             // the false death: butterflies, the dream breaks, no loot
            .special("hand_of_lies", 0.66)     // «Длань Лжи»
            .special("mask_fall", 0.45)        // «Падение маски» (owner 20.11, instead of «Приговор Предателя»)
            .special("full_reveal", 0.20)      // «Сон Бабочки: Полное Раскрытие»
            .finisher(true)                    // «%1$s раздавлен Дланью Лжи»
            .music("music.ereb_hand")
            .title(ID)
            .fightRadius(40)
            .build();

    public static RegistryObject<EntityType<ErebHandEntity>> TYPE;
    public static RegistryObject<EntityType<ErebHandReflection>> REFLECTION;
    public static RegistryObject<EntityType<ErebHandGiant>> GIANT;
    public static RegistryObject<EntityType<ErebHandShard>> SHARD;
    public static RegistryObject<EntityType<ErebHandTraitor>> TRAITOR;
    public static RegistryObject<Item> RAPIER;

    /** Called from Bosses.init before the registers are attached. */
    public static void register() {
        TYPE = Bosses.boss(ID, ErebHandEntity::new, 0.8f, 2.4f, ErebHandEntity::attributes);
        REFLECTION = Bosses.living("ereb_hand_reflection", ErebHandReflection::new, MobCategory.MISC, 0.8f, 2.4f, ErebHandEntity::attributes);
        GIANT = Bosses.ENTITIES.register("ereb_hand_giant", () -> EntityType.Builder.<ErebHandGiant>of(ErebHandGiant::new, MobCategory.MISC)
                .sized(1.0f, 1.0f).clientTrackingRange(16).updateInterval(1).noSummon().fireImmune().build("ereb_hand_giant"));
        SHARD = Bosses.ENTITIES.register("ereb_hand_mask_shard", () -> EntityType.Builder.<ErebHandShard>of(ErebHandShard::new, MobCategory.MISC)
                .sized(0.8f, 0.8f).clientTrackingRange(10).updateInterval(1).noSummon().fireImmune().build("ereb_hand_mask_shard"));
        TRAITOR = Bosses.living("ereb_hand_traitor", ErebHandTraitor::new, MobCategory.MISC, 0.6f, 1.8f, ErebHandTraitor::attributes);
        // his glass rapier: no recipe, never given to players (not in the creative tab)
        RAPIER = Bosses.ITEMS.register("ereb_hand_rapier", () -> new Item(new Item.Properties().stacksTo(1).rarity(Rarity.EPIC).fireResistant()));
    }
}
