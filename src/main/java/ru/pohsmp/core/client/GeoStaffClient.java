package ru.pohsmp.core.client;

import io.redspace.ironsspellbooks.render.ClientStaffItemExtensions;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.BlockEntityWithoutLevelRenderer;
import net.minecraft.resources.ResourceLocation;
import ru.pohsmp.core.AnimatedStaff;
import ru.pohsmp.core.PohCore;
import software.bernie.geckolib.model.DefaultedItemGeoModel;
import software.bernie.geckolib.renderer.GeoItemRenderer;
import software.bernie.geckolib.renderer.layer.AutoGlowingGeoLayer;

/** Iron's staff arm pose plus the GeckoLib renderer (geo/item/&lt;model&gt;.geo.json, glow from &lt;model&gt;_glowmask.png). */
public class GeoStaffClient extends ClientStaffItemExtensions {
    /**
     * The item, not its model name: Forge calls initializeClient from the Item constructor, before AnimatedStaff has set
     * its fields, so the name is read only when the renderer is first needed (1.10.0 crashed here with a null name).
     */
    private final AnimatedStaff staff;
    private GeoItemRenderer<AnimatedStaff> renderer;

    public GeoStaffClient(AnimatedStaff staff) {
        this.staff = staff;
    }

    @Override
    public BlockEntityWithoutLevelRenderer getCustomRenderer() {
        if (renderer == null) {
            renderer = new GeoItemRenderer<>(new DefaultedItemGeoModel<>(new ResourceLocation(PohCore.MODID, modelName())));
            renderer.addRenderLayer(new AutoGlowingGeoLayer<>(renderer));
        }
        return renderer;
    }

    /** Model that exists: a staff whose GeckoLib files are not made yet (e.g. the Silent Witch staff) borrows another staff's model. */
    private String modelName() {
        String m = staff.model;
        if (staff.fallbackModel == null) return m;
        ResourceLocation geo = new ResourceLocation(PohCore.MODID, "geo/item/" + m + ".geo.json");
        return Minecraft.getInstance().getResourceManager().getResource(geo).isPresent() ? m : staff.fallbackModel;
    }
}
