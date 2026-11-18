package ru.pohsmp.core.client;

import java.util.List;
import net.minecraftforge.common.ForgeConfigSpec;

public final class ClientConfig {
    public static final ForgeConfigSpec SPEC;
    public static final ForgeConfigSpec.BooleanValue CAM_ENABLED;
    public static final ForgeConfigSpec.ConfigValue<String> CAM_MODE;
    public static final ForgeConfigSpec.DoubleValue CAM_DISTANCE;

    static {
        ForgeConfigSpec.Builder b = new ForgeConfigSpec.Builder();
        b.push("camera");
        CAM_ENABLED = b.comment("Show the player model during camera cutscenes").define("enabled", true);
        CAM_MODE = b.comment("cnpcext - CNPCExtended cutscene flag; distance - camera far from the eyes; both - either")
                .defineInList("mode", "cnpcext", List.of("cnpcext", "distance", "both"));
        CAM_DISTANCE = b.comment("Camera counts as detached when it is farther than this from the player's eyes (blocks)")
                .defineInRange("distanceThreshold", 0.75, 0.1, 64.0);
        b.pop();
        SPEC = b.build();
    }

    private ClientConfig() {}
}
