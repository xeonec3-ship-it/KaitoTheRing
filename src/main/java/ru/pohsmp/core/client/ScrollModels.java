package ru.pohsmp.core.client;

import io.redspace.ironsspellbooks.api.spells.ISpellContainer;
import io.redspace.ironsspellbooks.api.spells.SpellData;
import java.util.Map;
import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.renderer.block.model.ItemOverrides;
import net.minecraft.client.resources.model.BakedModel;
import net.minecraft.client.resources.model.ModelResourceLocation;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.item.ItemStack;
import net.minecraftforge.client.event.ModelEvent;
import net.minecraftforge.client.model.BakedModelWrapper;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.PohCore;

/**
 * Own 32x32 scroll pictures for single spells (Explosion, Heaven's Fall, Frozen Hour): the Iron's scroll model is wrapped,
 * and for these spells its overrides return our model; every other scroll keeps Iron's choice by school.
 */
public final class ScrollModels {
    private ScrollModels() {}

    private static final Map<String, ResourceLocation> OWN = Map.of(
            PohCore.MODID + ":explosion", new ResourceLocation(PohCore.MODID, "item/scroll_explosion"),
            PohCore.MODID + ":heaven_fall", new ResourceLocation(PohCore.MODID, "item/scroll_heaven_fall"),
            PohCore.MODID + ":frozen_hour", new ResourceLocation(PohCore.MODID, "item/scroll_frozen_hour"),
            PohCore.MODID + ":space_closure", new ResourceLocation(PohCore.MODID, "item/scroll_space_closure"));

    @SubscribeEvent
    public static void onRegister(ModelEvent.RegisterAdditional e) {
        for (ResourceLocation r : OWN.values()) e.register(r);
    }

    @SubscribeEvent
    public static void onModify(ModelEvent.ModifyBakingResult e) {
        ModelResourceLocation key = new ModelResourceLocation(new ResourceLocation("irons_spellbooks", "scroll"), "inventory");
        BakedModel base = e.getModels().get(key);
        if (base == null) return;
        e.getModels().put(key, new Wrapped(base));
    }

    private static final class Wrapped extends BakedModelWrapper<BakedModel> {
        private final ItemOverrides overrides;

        Wrapped(BakedModel base) {
            super(base);
            ItemOverrides inner = base.getOverrides();
            overrides = new ItemOverrides() {
                @Override
                public BakedModel resolve(BakedModel model, ItemStack stack, ClientLevel level, LivingEntity entity, int seed) {
                    ResourceLocation own = pick(stack);
                    if (own != null) {
                        BakedModel m = Minecraft.getInstance().getModelManager().getModel(own);
                        if (m != null && m != Minecraft.getInstance().getModelManager().getMissingModel()) return m;
                    }
                    return inner.resolve(model, stack, level, entity, seed);
                }
            };
        }

        @Override
        public ItemOverrides getOverrides() {
            return overrides;
        }
    }

    private static ResourceLocation pick(ItemStack stack) {
        try {
            if (!ISpellContainer.isSpellContainer(stack)) return null;
            SpellData d = ISpellContainer.get(stack).getSpellAtIndex(0);
            return d == null ? null : OWN.get(d.getSpell().getSpellId());
        } catch (RuntimeException ex) {
            return null;
        }
    }
}
