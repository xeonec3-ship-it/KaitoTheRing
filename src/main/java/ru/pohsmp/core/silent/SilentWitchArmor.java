package ru.pohsmp.core.silent;

import com.google.common.collect.ImmutableMultimap;
import com.google.common.collect.Multimap;
import io.redspace.ironsspellbooks.api.registry.AttributeRegistry;
import java.util.List;
import java.util.UUID;
import java.util.function.Consumer;
import net.minecraft.ChatFormatting;
import net.minecraft.network.chat.Component;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.ai.attributes.Attribute;
import net.minecraft.world.entity.ai.attributes.AttributeModifier;
import net.minecraft.world.item.ArmorItem;
import net.minecraft.world.item.ArmorMaterial;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.Rarity;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.item.crafting.Ingredient;
import net.minecraft.world.level.Level;
import net.minecraftforge.client.extensions.common.IClientItemExtensions;
import org.jetbrains.annotations.Nullable;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.ServerConfig;
import software.bernie.geckolib.animatable.GeoItem;
import software.bernie.geckolib.core.animatable.instance.AnimatableInstanceCache;
import software.bernie.geckolib.core.animation.AnimatableManager;
import software.bernie.geckolib.core.animation.AnimationController;
import software.bernie.geckolib.core.animation.RawAnimation;
import software.bernie.geckolib.util.GeckoLibUtil;

/**
 * Hood, robe and robe skirt of the Silent Witch (T19). Leather-level protection (1/3/2), high durability, enchantable,
 * repaired with lapis. Drawn by GeckoLib (geo/armor/silent_witch_armor.geo.json from tools/gen_silent_outfit.py - one model, each slot shows its bones).
 * Bonuses are attribute modifiers read from the [silent_witch] server config; the rest of the effects live in {@link SilentWitchEvents}.
 */
public class SilentWitchArmor extends ArmorItem implements GeoItem {
    public static final RawAnimation IDLE = RawAnimation.begin().thenLoop("idle");
    public static final RawAnimation WALK = RawAnimation.begin().thenLoop("walk");
    public static final RawAnimation RUN = RawAnimation.begin().thenLoop("run");
    public static final RawAnimation CAST = RawAnimation.begin().thenLoop("cast");

    private final AnimatableInstanceCache cache = GeckoLibUtil.createInstanceCache(this);

    public SilentWitchArmor(Type type) {
        super(MATERIAL, type, new Item.Properties().rarity(Rarity.EPIC));
    }

    // ------------------------------------------------------------------ bonuses

    private static final UUID CAST_ID = UUID.fromString("5e1a7c10-19a0-4b6e-9f3a-71c0d0a9e101");
    private static final UUID CAST_SILENT_ID = UUID.fromString("5e1a7c10-19a0-4b6e-9f3a-71c0d0a9e102");
    private static final UUID MANA_ROBE_ID = UUID.fromString("5e1a7c10-19a0-4b6e-9f3a-71c0d0a9e103");
    private static final UUID MANA_HOOD_ID = UUID.fromString("5e1a7c10-19a0-4b6e-9f3a-71c0d0a9e104");
    private static final UUID REGEN_ROBE_ID = UUID.fromString("5e1a7c10-19a0-4b6e-9f3a-71c0d0a9e105");
    private static final UUID REGEN_HOOD_ID = UUID.fromString("5e1a7c10-19a0-4b6e-9f3a-71c0d0a9e106");
    private static final UUID RESIST_SKIRT_ID = UUID.fromString("5e1a7c10-19a0-4b6e-9f3a-71c0d0a9e107");
    private static final UUID RESIST_HOOD_ID = UUID.fromString("5e1a7c10-19a0-4b6e-9f3a-71c0d0a9e108");
    private static final UUID SRESIST_SKIRT_ID = UUID.fromString("5e1a7c10-19a0-4b6e-9f3a-71c0d0a9e109");
    private static final UUID SRESIST_HOOD_ID = UUID.fromString("5e1a7c10-19a0-4b6e-9f3a-71c0d0a9e10a");

    private static void add(ImmutableMultimap.Builder<Attribute, AttributeModifier> b, Attribute a, UUID id, String name, double v) {
        if (a != null && v != 0) b.put(a, new AttributeModifier(id, "Silent Witch " + name, v, AttributeModifier.Operation.ADDITION));
    }

    @Override
    public Multimap<Attribute, AttributeModifier> getAttributeModifiers(EquipmentSlot slot, ItemStack stack) {
        Multimap<Attribute, AttributeModifier> base = super.getAttributeModifiers(slot, stack);
        if (slot != getEquipmentSlot()) return base;
        ImmutableMultimap.Builder<Attribute, AttributeModifier> b = ImmutableMultimap.builder();
        b.putAll(base);
        double regen = ServerConfig.get(ServerConfig.SW_REGEN) / 2, resist = ServerConfig.get(ServerConfig.SW_RESIST) / 2,
                sresist = ServerConfig.get(ServerConfig.SW_RESIST_SILENT) / 2;
        switch (getType()) {
            case CHESTPLATE -> {
                double cast = ServerConfig.get(ServerConfig.SW_CAST);
                add(b, AttributeRegistry.CAST_TIME_REDUCTION.get(), CAST_ID, "cast", cast);
                add(b, Reg.SILENT_CAST.get(), CAST_SILENT_ID, "silent cast", Math.max(0, ServerConfig.get(ServerConfig.SW_CAST_SILENT) - cast));
                add(b, AttributeRegistry.MAX_MANA.get(), MANA_ROBE_ID, "mana", ServerConfig.get(ServerConfig.SW_MANA_ROBE));
                add(b, AttributeRegistry.MANA_REGEN.get(), REGEN_ROBE_ID, "regen", regen);
            }
            case HELMET -> {
                add(b, AttributeRegistry.MAX_MANA.get(), MANA_HOOD_ID, "mana", ServerConfig.get(ServerConfig.SW_MANA_HOOD));
                add(b, AttributeRegistry.MANA_REGEN.get(), REGEN_HOOD_ID, "regen", regen);
                add(b, AttributeRegistry.SPELL_RESIST.get(), RESIST_HOOD_ID, "resist", resist);
                add(b, Reg.SILENT_RESIST.get(), SRESIST_HOOD_ID, "silent resist", sresist);
            }
            case LEGGINGS -> {
                add(b, AttributeRegistry.SPELL_RESIST.get(), RESIST_SKIRT_ID, "resist", resist);
                add(b, Reg.SILENT_RESIST.get(), SRESIST_SKIRT_ID, "silent resist", sresist);
            }
            default -> {}
        }
        return b.build();
    }

    @Override
    public void appendHoverText(ItemStack stack, @Nullable Level level, List<Component> tip, TooltipFlag flag) {
        String key = "item." + PohCore.MODID + "." + switch (getType()) {
            case HELMET -> "silent_witch_hood";
            case CHESTPLATE -> "silent_witch_robe";
            default -> "silent_witch_skirt";
        } + ".desc";
        for (int i = 1; i <= 4; i++) {
            String k = key + i;
            if (!net.minecraft.locale.Language.getInstance().has(k)) break;
            tip.add(Component.translatable(k).withStyle(ChatFormatting.GRAY));
        }
        tip.add(Component.translatable("item.pohsmp_core.silent_witch.set").withStyle(s -> s.withColor(Reg.SILENT_COLOR)));
        tip.add(Component.translatable("item.pohsmp_core.silent_witch.set_barrier").withStyle(ChatFormatting.DARK_AQUA));
        tip.add(Component.translatable("item.pohsmp_core.silent_witch.set_nameless").withStyle(ChatFormatting.DARK_AQUA));
        tip.add(Component.translatable("item.pohsmp_core.silent_witch.set_gate").withStyle(ChatFormatting.GOLD));
    }

    // ------------------------------------------------------------------ GeckoLib

    /** The vanilla armor layer asks for a texture even though GeckoLib draws the model; give it ours (no missing-texture spam). */
    @Override
    public String getArmorTexture(ItemStack stack, net.minecraft.world.entity.Entity entity, EquipmentSlot slot, String type) {
        return PohCore.MODID + ":textures/armor/silent_witch_armor.png";
    }

    @Override
    public void registerControllers(AnimatableManager.ControllerRegistrar controllers) {
        controllers.add(new AnimationController<>(this, "cloak", 6, s -> s.setAndContinue(ru.pohsmp.core.client.OutfitAnim.pick(s))));
        controllers.add(new AnimationController<>(this, "nero", 2, s -> s.setAndContinue(ru.pohsmp.core.client.OutfitAnim.cat(s))));
    }

    @Override
    public AnimatableInstanceCache getAnimatableInstanceCache() {
        return cache;
    }

    @Override
    public void initializeClient(Consumer<IClientItemExtensions> consumer) {
        consumer.accept(new IClientItemExtensions() {
            private net.minecraft.client.model.HumanoidModel<?> renderer;

            @Override
            public net.minecraft.client.model.HumanoidModel<?> getHumanoidArmorModel(net.minecraft.world.entity.LivingEntity entity, ItemStack stack,
                                                                                    EquipmentSlot slot, net.minecraft.client.model.HumanoidModel<?> original) {
                if (renderer == null) renderer = new ru.pohsmp.core.client.SilentWitchRenderer();
                ((ru.pohsmp.core.client.SilentWitchRenderer) renderer).prepForRender(entity, stack, slot, original);
                return renderer;
            }
        });
    }

    // ------------------------------------------------------------------ material

    public static final ArmorMaterial MATERIAL = new ArmorMaterial() {
        @Override
        public int getDurabilityForType(Type type) {
            return new int[] {13, 15, 16, 11}[type.getSlot().getIndex()] * 33;   // netherite-level durability
        }

        @Override
        public int getDefenseForType(Type type) {
            return switch (type) {
                case HELMET -> 1;
                case CHESTPLATE -> 3;
                case LEGGINGS -> 2;
                case BOOTS -> 1;
            };
        }

        @Override
        public int getEnchantmentValue() {
            return 25;
        }

        @Override
        public SoundEvent getEquipSound() {
            return SoundEvents.ARMOR_EQUIP_LEATHER;
        }

        @Override
        public Ingredient getRepairIngredient() {
            return Ingredient.of(Items.LAPIS_LAZULI);
        }

        @Override
        public String getName() {
            return PohCore.MODID + ":silent_witch";
        }

        @Override
        public float getToughness() {
            return 0;
        }

        @Override
        public float getKnockbackResistance() {
            return 0;
        }
    };
}
