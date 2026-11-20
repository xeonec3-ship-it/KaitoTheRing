package ru.pohsmp.core.boss.aris;

import net.minecraft.world.effect.MobEffect;
import net.minecraft.world.effect.MobEffectCategory;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.MobCategory;
import net.minecraft.world.entity.ai.attributes.AttributeModifier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.Rarity;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.registries.RegistryObject;
import ru.pohsmp.core.PohEffect;
import ru.pohsmp.core.boss.BossDef;
import ru.pohsmp.core.boss.BossNpc;
import ru.pohsmp.core.boss.Bosses;

/**
 * T28 «Арис, Мифический Кузнец» (pohsmp_core:aris; docs/specs/tasks/T28_aris_boss.md): definition and registrations. A GeckoLib body
 * of her own (geo/entity/aris.geo.json, animation.aris.*), three phases («Ковка» / «Оружейная» 66% / «Мифический сплав» 33%), the
 * specials «Горн» (75%) and «Последний удар молота» (10%), four spells of her own, surrender at 5% → the peaceful NPC aris_npc,
 * the answer to «Дезинтеграция: Реплика». No finisher (owner).
 */
public final class Aris {
    private Aris() {}

    public static final String ID = "aris";
    /** Turquoise of her horns: chat lines, subtitles, the epithet. */
    public static final int COLOR = 0x4FE0D0;

    public static final BossDef DEF = BossDef.builder(ID)
            .phases(0.66, 0.33)
            .standardBar()
            .overlay(2, BossDef.Overlay.FRAMES, "heat")   // phase 3: heat over the frame (aris_bossbar_p3_heat, 8 frames)
            .color(COLOR)
            .surrender(0.05, "aris_npc")
            .special("forge", 0.75)
            .special("last_blow", 0.10)
            .finisher(false)
            .music("music.aris")
            .title("aris")
            .fightRadius(40)
            .build();

    public static RegistryObject<EntityType<ArisEntity>> TYPE;
    public static RegistryObject<EntityType<ArisNpc>> NPC;
    public static RegistryObject<EntityType<ArisAnvilEntity>> ANVIL;
    public static RegistryObject<EntityType<ArisBladeEntity>> BLADE;
    public static RegistryObject<EntityType<ArisBilletEntity>> BILLET;
    public static RegistryObject<Item> HAMMER;
    public static RegistryObject<MobEffect> REFORGED, SCORCHED, CHAINED, STEAMED;

    /** Called from Bosses.init before the registers are attached. */
    public static void register() {
        TYPE = Bosses.boss(ID, ArisEntity::new, 0.9f, 2.4f, ArisEntity::attributes);
        NPC = Bosses.living("aris_npc", (EntityType<ArisNpc> t, net.minecraft.world.level.Level l) -> new ArisNpc(t, l), MobCategory.MISC, 0.9f, 2.4f,
                BossNpc::attributes);
        BLADE = Bosses.living("aris_blade", ArisBladeEntity::new, MobCategory.MISC, 0.7f, 0.7f, () -> Mob.createMobAttributes()
                .add(Attributes.MAX_HEALTH, 24).add(Attributes.FLYING_SPEED, 0.6).add(Attributes.ARMOR, 4));
        ANVIL = Bosses.ENTITIES.register("aris_anvil", () -> EntityType.Builder.<ArisAnvilEntity>of(ArisAnvilEntity::new, MobCategory.MISC)
                .sized((float) ArisMath.ANVIL_LONG, (float) ArisMath.ANVIL_HEIGHT).clientTrackingRange(10).updateInterval(20).noSummon().fireImmune()
                .build("aris_anvil"));
        BILLET = Bosses.ENTITIES.register("aris_billet", () -> EntityType.Builder.<ArisBilletEntity>of(ArisBilletEntity::new, MobCategory.MISC)
                .sized(0.6f, 0.4f).clientTrackingRange(10).updateInterval(1).noSummon().fireImmune().build("aris_billet"));
        // her hammer as an item (models/item/aris_hammer.json): never given to players, not in a creative tab; the boss draws its own
        HAMMER = Bosses.ITEMS.register("aris_hammer", () -> new Item(new Item.Properties().stacksTo(1).rarity(Rarity.EPIC).fireResistant()));
        REFORGED = Bosses.EFFECTS.register("aris_reforged", () -> new PohEffect(MobEffectCategory.HARMFUL, 0x4FE0D0));
        SCORCHED = Bosses.EFFECTS.register("aris_scorched", () -> new PohEffect(MobEffectCategory.HARMFUL, 0xFF6A1A));
        CHAINED = Bosses.EFFECTS.register("aris_chained", () -> new PohEffect(MobEffectCategory.HARMFUL, 0x8A8A8A)
                .addAttributeModifier(Attributes.MOVEMENT_SPEED, "6b1f6f0e-3c2a-4e7b-9d14-2a7c5e0b8f31", -1.0, AttributeModifier.Operation.MULTIPLY_TOTAL));
        STEAMED = Bosses.EFFECTS.register("aris_steamed", () -> new PohEffect(MobEffectCategory.HARMFUL, 0xD0D8DC));
    }

    public static void events() {
        MinecraftForge.EVENT_BUS.register(ArisEvents.class);
    }
}
