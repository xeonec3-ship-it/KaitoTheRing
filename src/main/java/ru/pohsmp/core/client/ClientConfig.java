package ru.pohsmp.core.client;

import java.util.List;
import net.minecraftforge.common.ForgeConfigSpec;

public final class ClientConfig {
    public static final ForgeConfigSpec SPEC;
    public static final ForgeConfigSpec.BooleanValue CAM_ENABLED;
    public static final ForgeConfigSpec.ConfigValue<String> CAM_MODE;
    public static final ForgeConfigSpec.DoubleValue CAM_DISTANCE;
    public static final ForgeConfigSpec.DoubleValue FX_DISTANCE;
    public static final ForgeConfigSpec.IntValue FX_MAX;
    public static final ForgeConfigSpec.ConfigValue<String> FX_QUALITY;

    static {
        ForgeConfigSpec.Builder b = new ForgeConfigSpec.Builder();
        b.push("camera");
        CAM_ENABLED = b.comment("Show the player model during camera cutscenes").define("enabled", true);
        CAM_MODE = b.comment("cnpcext - CNPCExtended cutscene flag; distance - camera far from the eyes; both - either")
                .defineInList("mode", "cnpcext", List.of("cnpcext", "distance", "both"));
        CAM_DISTANCE = b.comment("Camera counts as detached when it is farther than this from the player's eyes (blocks)")
                .defineInRange("distanceThreshold", 0.75, 0.1, 64.0);
        b.pop();
        b.push("fx");
        FX_DISTANCE = b.comment("Sigils and effects farther than this from the camera are not drawn (blocks)")
                .defineInRange("maxDistance", 128.0, 16.0, 512.0);
        FX_MAX = b.comment("At most this many effects at once; the oldest is dropped").defineInRange("maxInstances", 96, 8, 1024);
        FX_QUALITY = b.comment("high or low (fewer particles, sparks and curtain beams)").defineInList("quality", "high", List.of("high", "low"));
        b.pop();
        SPEC = b.build();
    }

    private ClientConfig() {}
}
