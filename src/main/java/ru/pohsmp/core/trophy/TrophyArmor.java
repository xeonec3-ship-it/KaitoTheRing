package ru.pohsmp.core.trophy;

import com.google.common.collect.ImmutableMultimap;
import com.google.common.collect.Multimap;
import java.util.List;
import java.util.function.Consumer;
import net.minecraft.ChatFormatting;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.ai.attributes.Attribute;
import net.minecraft.world.entity.ai.attributes.AttributeModifier;
import net.minecraft.world.item.ArmorItem;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Rarity;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.level.Level;
import net.minecraftforge.client.extensions.common.IClientItemExtensions;
import org.jetbrains.annotations.Nullable;
import ru.pohsmp.core.PohCore;
import software.bernie.geckolib.animatable.GeoItem;
import software.bernie.geckolib.core.animatable.instance.AnimatableInstanceCache;
import software.bernie.geckolib.core.animation.AnimatableManager;
import software.bernie.geckolib.core.animation.AnimationController;
import software.bernie.geckolib.core.animation.RawAnimation;
import software.bernie.geckolib.core.object.PlayState;
import software.bernie.geckolib.util.GeckoLibUtil;

/**
 * T35: one piece of a cell head's set (Irina, Aris, Martin, Ereb). Netherite durability and fire resistance, Mending only, Iron's
 * attributes from {@link TrophySet}; the full-set bonus lives in {@link TrophyEvents}. Drawn by GeckoLib like the Silent Witch outfit
 * (client/TrophyRenderer), netherite look until the visual helpers' files exist ({@link TrophyAssets}). Admin-only (/give).
 */
public class TrophyArmor extends ArmorItem implements GeoItem {
    public static final RawAnimation IDLE = RawAnimation.begin().thenLoop("idle");
    public static final RawAnimation WALK = RawAnimation.begin().thenLoop("walk");
    public static final RawAnimation RUN = RawAnimation.begin().thenLoop("run");
    public static final RawAnimation CAST = RawAnimation.begin().thenLoop("cast");

    public final TrophySet set;
    private final AnimatableInstanceCache cache = GeckoLibUtil.createInstanceCache(this);

    public TrophyArmor(TrophySet set, Type type) {
        super(set.material, type, new Item.Properties().rarity(Rarity.EPIC).fireResistant());
        this.set = set;
    }

    /** The set of the piece in an armor stack, or null. */
    @Nullable
    public static TrophySet setOf(ItemStack s) {
        return s.getItem() instanceof TrophyArmor a ? a.set : null;
    }

    @Override
    public Multimap<Attribute, AttributeModifier> getAttributeModifiers(EquipmentSlot slot, ItemStack stack) {
        Multimap<Attribute, AttributeModifier> base = super.getAttributeModifiers(slot, stack);
        if (slot != getEquipmentSlot()) return base;
        ImmutableMultimap.Builder<Attribute, AttributeModifier> b = ImmutableMultimap.builder();
        b.putAll(base);
        set.addModifiers(b, getType());
        return b.build();
    }

    @Override
    public boolean isValidRepairItem(ItemStack self, ItemStack other) {
        return false;
    }

    @Override
    public void appendHoverText(ItemStack stack, @Nullable Level level, List<Component> tip, TooltipFlag flag) {
        String k = "item." + PohCore.MODID + ".trophy." + set.id;
        tip.add(Component.translatable(k + ".boss").withStyle(s -> s.withColor(set.color)));
        tip.add(Component.translatable("item.pohsmp_core.trophy.set").withStyle(ChatFormatting.GRAY));
        for (int i = 1; i <= 3; i++) {
            String line = k + ".bonus" + i;
            if (!net.minecraft.locale.Language.getInstance().has(line)) break;
            tip.add(Component.translatable(line).withStyle(ChatFormatting.GOLD));
        }
        tip.add(Component.translatable("item.pohsmp_core.trophy.admin").withStyle(ChatFormatting.DARK_GRAY, ChatFormatting.ITALIC));
    }

    // ------------------------------------------------------------------ GeckoLib

    @Override
    public String getArmorTexture(ItemStack stack, Entity entity, EquipmentSlot slot, String type) {
        return TrophyAssets.armorTexture(set.id, slot == EquipmentSlot.LEGS);
    }

    @Override
    public void registerControllers(AnimatableManager.ControllerRegistrar controllers) {
        controllers.add(new AnimationController<>(this, "cloth", 6, s -> {
            if (!TrophyAssets.hasAnim(set.id)) return PlayState.STOP;   // no animation file yet: stand still, no error spam
            return s.setAndContinue(ru.pohsmp.core.client.TrophyRenderer.pick(s.getData(software.bernie.geckolib.constant.DataTickets.ENTITY)));
        }));
    }

    @Override
    public AnimatableInstanceCache getAnimatableInstanceCache() {
        return cache;
    }

    @Override
    public void initializeClient(Consumer<IClientItemExtensions> consumer) {
        consumer.accept(new IClientItemExtensions() {
            private ru.pohsmp.core.client.TrophyRenderer<TrophyArmor> renderer;

            @Override
            public net.minecraft.client.model.HumanoidModel<?> getHumanoidArmorModel(LivingEntity entity, ItemStack stack, EquipmentSlot slot,
                                                                                    net.minecraft.client.model.HumanoidModel<?> original) {
                if (!TrophyAssets.hasGeo(set.id)) return original;   // netherite look until the model exists
                if (renderer == null) renderer = new ru.pohsmp.core.client.TrophyRenderer<>(set.id);
                renderer.prepForRender(entity, stack, slot, original);
                return renderer;
            }
        });
    }
}
