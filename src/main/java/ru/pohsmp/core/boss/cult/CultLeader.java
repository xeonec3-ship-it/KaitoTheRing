package ru.pohsmp.core.boss.cult;

import io.redspace.ironsspellbooks.entity.mobs.wizards.fire_boss.FireBossEntity;
import io.redspace.ironsspellbooks.entity.mobs.wizards.pyromancer.PyromancerEntity;
import net.minecraft.world.effect.MobEffect;
import net.minecraft.world.effect.MobEffectCategory;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.MobCategory;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.Rarity;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.registries.RegistryObject;
import ru.pohsmp.core.PohEffect;
import ru.pohsmp.core.boss.BossDef;
import ru.pohsmp.core.boss.Bosses;

/**
 * T26 «Глава Культа Меллисто» (pohsmp_core:cult_leader; docs/specs/tasks/T26_cult_leader_boss.md): its definition and
 * registrations. Tyros's body and moves (Iron's FireBossEntity, size as the original: render ×1.75, soul ×2.0125, hitbox
 * 1.4875×3.675), three phases (66% «Приговор Меллисто», 33% «Истинное пламя»), the specials «Первое Пламя» (66%) and «Пепел Меллисто»
 * (15%), four attacks of its own, the finisher, the answer to «Дезинтеграция: Реплика».
 */
public final class CultLeader {
    private CultLeader() {}

    public static final String ID = "cult_leader";
    /** Colour of its lines (the gold of the bar title). */
    public static final int COLOR = 0xFFB040;

    public static final BossDef DEF = BossDef.builder(ID)
            .phases(0.66, 0.33)
            .standardBar()
            .overlay(1, BossDef.Overlay.PULSE, "pulse")     // phase 2: the frame pulses while magic is forbidden
            .overlay(2, BossDef.Overlay.FRAMES, "flames")   // phase 3: tongues of fire over the frame
            .color(COLOR)
            .death()
            .special("first_flame", 0.66)
            .special("ash", 0.15)
            .finisher(true)
            .music("music.cult_leader")
            .title("cult_leader")
            .fightRadius(40)
            .build();

    public static RegistryObject<EntityType<CultLeaderEntity>> TYPE;
    public static RegistryObject<EntityType<FireCultistEntity>> CULTIST;
    public static RegistryObject<EntityType<CultSickleEntity>> SICKLE;
    public static RegistryObject<Item> SCYTHE;
    public static RegistryObject<MobEffect> VERDICT, BRAND;

    /** Called from Bosses.init before the registers are attached. */
    public static void register() {
        TYPE = Bosses.boss(ID, CultLeaderEntity::new, 1.4875f, 3.675f,
                () -> FireBossEntity.prepareAttributes().add(Attributes.MAX_HEALTH, 3000).add(Attributes.ATTACK_DAMAGE, 13));
        CULTIST = Bosses.living("fire_cultist", FireCultistEntity::new, MobCategory.MONSTER, 0.6f, 1.8f, PyromancerEntity::prepareAttributes);
        SICKLE = Bosses.ENTITIES.register("cult_sickle", () -> EntityType.Builder.<CultSickleEntity>of(CultSickleEntity::new, MobCategory.MISC)
                .sized(1.5f, 0.5f).clientTrackingRange(8).updateInterval(1).noSummon().fireImmune().build("cult_sickle"));
        // the boss's own scythe: no recipe, never given to players (not in the creative tab)
        SCYTHE = Bosses.ITEMS.register("cult_scythe", () -> new Item(new Item.Properties().stacksTo(1).rarity(Rarity.EPIC).fireResistant()));
        VERDICT = Bosses.EFFECTS.register("mellisto_verdict", () -> new PohEffect(MobEffectCategory.HARMFUL, 0xC8401A));
        BRAND = Bosses.EFFECTS.register("cult_brand", () -> new PohEffect(MobEffectCategory.HARMFUL, 0xFF6A1A));
    }

    public static void events() {
        MinecraftForge.EVENT_BUS.register(CultFight.Events.class);
    }
}
