package ru.pohsmp.core.client;

import io.redspace.ironsspellbooks.api.spells.ISpellContainer;
import io.redspace.ironsspellbooks.api.spells.SpellData;
import java.util.List;
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
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.spell.DisintegrationSpell;
import ru.pohsmp.core.spell.silent.SageBarrierSpell;
import ru.pohsmp.core.spell.silent.SilentVolleySpell;
import ru.pohsmp.core.spell.silent.WindSpearsSpell;
import ru.pohsmp.core.spell.silent.WorganFlameSpell;

/**
 * Own 32x32 scroll pictures for single spells (Explosion, Heaven's Fall, Frozen Hour): the Iron's scroll model is wrapped,
 * and for these spells its overrides return our model; every other scroll keeps Iron's choice by school.
 */
public final class ScrollModels {
    private ScrollModels() {}

    /** spell id -> item/scroll_&lt;path&gt;: the mythic four, every Divine and Higher spell, Disintegration, the four silent scrolls. */
    private static final Map<String, ResourceLocation> OWN = new java.util.HashMap<>();

    private static void own(ResourceLocation spell) {
        OWN.put(spell.toString(), new ResourceLocation(spell.getNamespace(), "item/scroll_" + spell.getPath()));
    }

    static {
        for (String p : List.of("explosion", "heaven_fall", "frozen_hour", "space_closure")) own(new ResourceLocation(PohCore.MODID, p));
        for (String p : Reg.DIVINE_SPELLS) own(new ResourceLocation(PohCore.MODID, p));
        for (String p : Reg.HIGHER_SPELLS) own(new ResourceLocation(PohCore.MODID, p));
        own(DisintegrationSpell.ID);
        for (String p : List.of(SageBarrierSpell.PATH, WindSpearsSpell.PATH, SilentVolleySpell.PATH, WorganFlameSpell.PATH))
            own(new ResourceLocation(PohCore.MODID, p));
    }

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
