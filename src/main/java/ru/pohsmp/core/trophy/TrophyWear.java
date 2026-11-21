package ru.pohsmp.core.trophy;

import com.google.common.collect.ImmutableMultimap;
import com.google.common.collect.Multimap;
import io.redspace.ironsspellbooks.api.registry.AttributeRegistry;
import java.util.List;
import java.util.function.Consumer;
import net.minecraft.ChatFormatting;
import net.minecraft.network.chat.Component;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResultHolder;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.ai.attributes.Attribute;
import net.minecraft.world.entity.ai.attributes.AttributeModifier;
import net.minecraft.world.entity.ai.attributes.AttributeModifier.Operation;
import net.minecraft.world.entity.player.Player;
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
import software.bernie.geckolib.core.object.PlayState;
import software.bernie.geckolib.util.GeckoLibUtil;

/**
 * T35: the separate wearables of the two Cult Heads, worn over any armor: «Накидка Главы Культа» (Curios slot "back") and «Маска Лжи»
 * (Curios slot "head"). Curios is in the pack (Iron's 3.16.1 requires it) and soft for us ({@link TrophyCurios}); without it the
 * thing takes the chest / head armor slot instead. Effects: {@link TrophyEvents}.
 */
public class TrophyWear extends Item implements GeoItem {
    public enum Kind {
        MANTLE("cult_mantle", "back", EquipmentSlot.CHEST, 0xFF6A1A),
        MASK("mask_of_lies", "head", EquipmentSlot.HEAD, 0xE8C15A);

        public final String id, curioSlot;
        public final EquipmentSlot fallbackSlot;
        public final int color;

        Kind(String id, String curioSlot, EquipmentSlot fallbackSlot, int color) {
            this.id = id;
            this.curioSlot = curioSlot;
            this.fallbackSlot = fallbackSlot;
            this.color = color;
        }
    }

    public final Kind kind;
    private final AnimatableInstanceCache cache = GeckoLibUtil.createInstanceCache(this);

    public TrophyWear(Kind kind) {
        super(new Item.Properties().stacksTo(1).rarity(Rarity.EPIC).fireResistant());   // nothing wears it down: no durability
        this.kind = kind;
    }

    /** The draft attributes (balance_bosses.md «Броня боссов (T35)»). */
    public Multimap<Attribute, AttributeModifier> modifiers() {
        ImmutableMultimap.Builder<Attribute, AttributeModifier> b = ImmutableMultimap.builder();
        String w = kind.id;
        if (kind == Kind.MANTLE) {
            put(b, AttributeRegistry.FIRE_SPELL_POWER.get(), w, "fire power", 0.15);
            put(b, AttributeRegistry.FIRE_MAGIC_RESIST.get(), w, "fire resist", 0.20);
            put(b, AttributeRegistry.MAX_MANA.get(), w, "mana", 50);
        } else {
            put(b, AttributeRegistry.SPELL_POWER.get(), w, "spell power", 0.10);
            put(b, AttributeRegistry.MAX_MANA.get(), w, "mana", 100);
        }
        return b.build();
    }

    private static void put(ImmutableMultimap.Builder<Attribute, AttributeModifier> b, Attribute a, String where, String name, double v) {
        if (a != null) b.put(a, new AttributeModifier(TrophySet.uuid(where + ":" + name), "POH trophy " + name, v, Operation.ADDITION));
    }

    // ------------------------------------------------------------------ the armor-slot fallback (no Curios)

    @Nullable
    @Override
    public EquipmentSlot getEquipmentSlot(ItemStack stack) {
        return TrophyCurios.ON ? null : kind.fallbackSlot;
    }

    @Override
    public Multimap<Attribute, AttributeModifier> getAttributeModifiers(EquipmentSlot slot, ItemStack stack) {
        if (!TrophyCurios.ON && slot == kind.fallbackSlot) return modifiers();
        return super.getAttributeModifiers(slot, stack);
    }

    @Override
    public InteractionResultHolder<ItemStack> use(Level level, Player player, InteractionHand hand) {
        ItemStack held = player.getItemInHand(hand);
        if (TrophyCurios.ON) return InteractionResultHolder.pass(held);   // Curios puts it on by right click itself
        ItemStack worn = player.getItemBySlot(kind.fallbackSlot);
        player.setItemSlot(kind.fallbackSlot, held.copy());
        player.setItemInHand(hand, worn);
        level.playSound(null, player.blockPosition(), SoundEvents.ARMOR_EQUIP_LEATHER, player.getSoundSource(), 1f, 1f);
        return InteractionResultHolder.sidedSuccess(player.getItemInHand(hand), level.isClientSide);
    }

    @Override
    public boolean isValidRepairItem(ItemStack self, ItemStack other) {
        return false;
    }

    @Override
    public void appendHoverText(ItemStack stack, @Nullable Level level, List<Component> tip, TooltipFlag flag) {
        String k = "item." + PohCore.MODID + "." + kind.id;
        tip.add(Component.translatable(k + ".boss").withStyle(s -> s.withColor(kind.color)));
        tip.add(Component.translatable("item.pohsmp_core.trophy.slot_" + kind.curioSlot).withStyle(ChatFormatting.GRAY));
        for (int i = 1; i <= 3; i++) {
            String line = k + ".desc" + i;
            if (!net.minecraft.locale.Language.getInstance().has(line)) break;
            tip.add(Component.translatable(line).withStyle(ChatFormatting.GOLD));
        }
        tip.add(Component.translatable("item.pohsmp_core.trophy.admin").withStyle(ChatFormatting.DARK_GRAY, ChatFormatting.ITALIC));
    }

    // ------------------------------------------------------------------ GeckoLib

    @Override
    public String getArmorTexture(ItemStack stack, Entity entity, EquipmentSlot slot, String type) {
        return TrophyAssets.armorTexture(kind.id, false);
    }

    @Override
    public void registerControllers(AnimatableManager.ControllerRegistrar controllers) {
        controllers.add(new AnimationController<>(this, "cloth", 6, s -> {
            if (!TrophyAssets.hasAnim(kind.id)) return PlayState.STOP;
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
            private ru.pohsmp.core.client.TrophyRenderer<TrophyWear> renderer;

            @Override
            public net.minecraft.client.model.HumanoidModel<?> getHumanoidArmorModel(LivingEntity entity, ItemStack stack, EquipmentSlot slot,
                                                                                    net.minecraft.client.model.HumanoidModel<?> original) {
                if (!TrophyAssets.hasGeo(kind.id)) return original;
                if (renderer == null) renderer = new ru.pohsmp.core.client.TrophyRenderer<>(kind.id);
                renderer.prepForRender(entity, stack, slot, original);
                return renderer;
            }
        });
    }
}
