package ru.pohsmp.core.client;

import com.mojang.blaze3d.vertex.PoseStack;
import net.minecraft.client.model.EntityModel;
import net.minecraft.client.model.HumanoidModel;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.entity.RenderLayerParent;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.item.ItemStack;
import net.minecraftforge.eventbus.api.IEventBus;
import net.minecraftforge.fml.event.lifecycle.FMLClientSetupEvent;
import ru.pohsmp.core.trophy.Trophies;
import ru.pohsmp.core.trophy.TrophyAssets;
import ru.pohsmp.core.trophy.TrophyCurios;
import ru.pohsmp.core.trophy.TrophyWear;
import top.theillusivec4.curios.api.SlotContext;
import top.theillusivec4.curios.api.client.CuriosRendererRegistry;
import top.theillusivec4.curios.api.client.ICurioRenderer;

/** T35 client: the mantle and the mask drawn from their Curios slots over the armor (Curios classes only in {@link CurioImpl}). */
public final class TrophyClient {
    private TrophyClient() {}

    public static void init(IEventBus modBus) {
        modBus.addListener((FMLClientSetupEvent e) -> {
            if (TrophyCurios.ON) e.enqueueWork(CurioImpl::register);
        });
    }

    private static final class CurioImpl {
        static void register() {
            for (TrophyWear w : Trophies.wearables()) CuriosRendererRegistry.register(w, () -> new WearRenderer(w));
        }
    }

    /** Draws the wearable as the chest (mantle) / head (mask) part of a GeckoLib armor model on the wearer's pose. */
    private static final class WearRenderer implements ICurioRenderer {
        private final TrophyWear item;
        private TrophyRenderer<TrophyWear> renderer;

        WearRenderer(TrophyWear item) {
            this.item = item;
        }

        @Override
        public <T extends LivingEntity, M extends EntityModel<T>> void render(ItemStack stack, SlotContext ctx, PoseStack pose,
                RenderLayerParent<T, M> parent, MultiBufferSource buffers, int light, float limbSwing, float limbSwingAmount, float partialTicks,
                float ageInTicks, float netHeadYaw, float headPitch) {
            if (!TrophyAssets.hasGeo(item.kind.id) || !(parent.getModel() instanceof HumanoidModel<?> base) || !ctx.visible()) return;
            if (renderer == null) renderer = new TrophyRenderer<>(item.kind.id);
            renderer.prepForRender(ctx.entity(), stack, item.kind.fallbackSlot, base);
            renderer.renderToBuffer(pose, buffers.getBuffer(RenderType.armorCutoutNoCull(TrophyAssets.texture(item.kind.id))), light,
                    OverlayTexture.NO_OVERLAY, 1f, 1f, 1f, 1f);
        }
    }
}
