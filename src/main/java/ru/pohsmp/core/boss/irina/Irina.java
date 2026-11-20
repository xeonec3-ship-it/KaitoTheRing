package ru.pohsmp.core.boss.irina;

import net.minecraft.world.effect.MobEffect;
import net.minecraft.world.effect.MobEffectCategory;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.ai.attributes.AttributeModifier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.Rarity;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.registries.RegistryObject;
import ru.pohsmp.core.PohEffect;
import ru.pohsmp.core.boss.BossDef;
import ru.pohsmp.core.boss.Bosses;

/**
 * T27 «Ирина, Ведьма Ревности» (pohsmp_core:irina; docs/specs/tasks/T27_irina_boss.md): definition and registrations. Her own
 * GeckoLib body on Iron's casting mob (bones of Iron's mage), three phases (66% «Красные нити», 33% «Ярость ревности»), the specials
 * «Чужое счастье» (66%) and «Только мой» (15%), four spells of her own, the finisher, the answer to «Дезинтеграция: Реплика».
 */
public final class Irina {
    private Irina() {}

    public static final String ID = "irina";
    /** Colour of her lines (the lilac of the bar). */
    public static final int COLOR = 0xC9A8FF;

    public static final BossDef DEF = BossDef.builder(ID)
            .phases(IrinaMath.PHASES)
            .standardBar()
            .overlay(1, BossDef.Overlay.PULSE, "pulse")       // phase 2: pulses while pairs are bound
            .overlay(2, BossDef.Overlay.FRAMES, "threads")    // phase 3: lashing threads over the frame
            .color(COLOR)
            .death()
            .special("happiness", 0.66)
            .special("only_mine", 0.15)
            .finisher(true)
            .music("music.irina")
            .title("irina")
            .fightRadius(40)
            .build();

    public static RegistryObject<EntityType<IrinaEntity>> TYPE;
    public static RegistryObject<Item> STAFF;
    public static RegistryObject<MobEffect> JEALOUSY_MARK, THREAD_BOND, STOLEN_HAPPINESS, JEALOUS_GAZE, THREAD_SNARE, MARIONETTE;

    /**
     * An effect of hers: registered as pohsmp_core:irina_<icon> (so its icon is textures/mob_effect/irina_<icon>.png, as the visual
     * assistant drew them) but named by the lang key effect.pohsmp_core.<name> the lang files already have.
     */
    static final class IrinaEffect extends PohEffect {
        private final String key;

        IrinaEffect(MobEffectCategory cat, int color, String name) {
            super(cat, color);
            this.key = "effect.pohsmp_core." + name;
        }

        @Override
        public String getDescriptionId() {
            return key;
        }
    }

    private static RegistryObject<MobEffect> effect(String icon, String name, MobEffectCategory cat, int color, String speedUuid, double speed) {
        return Bosses.EFFECTS.register("irina_" + icon, () -> {
            IrinaEffect e = new IrinaEffect(cat, color, name);
            if (speedUuid != null) e.addAttributeModifier(Attributes.MOVEMENT_SPEED, speedUuid, speed, AttributeModifier.Operation.MULTIPLY_TOTAL);
            return e;
        });
    }

    /** Called from Bosses.init before the registers are attached. */
    public static void register() {
        TYPE = Bosses.boss(ID, IrinaEntity::new, 0.7f, 2.4f, IrinaEntity::attributes);
        // her staff: no recipe, never given to players (not in the creative tab)
        STAFF = Bosses.ITEMS.register("irina_staff", () -> new Item(new Item.Properties().stacksTo(1).rarity(Rarity.EPIC).fireResistant()));
        JEALOUSY_MARK = effect("jealousy_mark", "jealousy_mark", MobEffectCategory.HARMFUL, 0xC0201C, null, 0);
        THREAD_BOND = effect("thread_bond", "thread_bond", MobEffectCategory.HARMFUL, 0xA0181A, null, 0);
        STOLEN_HAPPINESS = effect("stolen_happiness", "stolen_happiness", MobEffectCategory.HARMFUL, 0xE0C060, null, 0);
        // slowness-like: −15% speed per level (gaze_slow_amplifier 1 = level II = −30%)
        JEALOUS_GAZE = effect("jealous_gaze", "jealous_gaze", MobEffectCategory.HARMFUL, 0xC9A8FF, "3f0c8a51-2b7e-4d6a-9c14-8e1f6a2b7d01", -0.15);
        // held in place / not one's own legs: −100% speed (the puppet is walked by the server)
        THREAD_SNARE = effect("snared", "thread_snare", MobEffectCategory.HARMFUL, 0x7A0E10, "3f0c8a51-2b7e-4d6a-9c14-8e1f6a2b7d02", -1.0);
        MARIONETTE = effect("puppet", "marionette", MobEffectCategory.HARMFUL, 0xC0201C, "3f0c8a51-2b7e-4d6a-9c14-8e1f6a2b7d03", -1.0);
    }

    public static void events() {
        MinecraftForge.EVENT_BUS.register(IrinaFight.Events.class);
    }
}
