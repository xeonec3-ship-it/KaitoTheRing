package ru.pohsmp.core.client;

import io.redspace.ironsspellbooks.render.ClientStaffItemExtensions;
import net.minecraft.client.renderer.BlockEntityWithoutLevelRenderer;
import net.minecraft.resources.ResourceLocation;
import ru.pohsmp.core.DownfallStaff;
import ru.pohsmp.core.PohCore;
import software.bernie.geckolib.model.DefaultedItemGeoModel;
import software.bernie.geckolib.renderer.GeoItemRenderer;
import software.bernie.geckolib.renderer.layer.AutoGlowingGeoLayer;

/** Iron's staff arm pose plus the GeckoLib renderer (geo/item/downfall_staff.geo.json, glow from downfall_staff_glowmask.png). */
public class DownfallStaffClient extends ClientStaffItemExtensions {
    private GeoItemRenderer<DownfallStaff> renderer;

    @Override
    public BlockEntityWithoutLevelRenderer getCustomRenderer() {
        if (renderer == null) {
            renderer = new GeoItemRenderer<>(new DefaultedItemGeoModel<>(new ResourceLocation(PohCore.MODID, "downfall_staff")));
            renderer.addRenderLayer(new AutoGlowingGeoLayer<>(renderer));
        }
        return renderer;
    }
}
