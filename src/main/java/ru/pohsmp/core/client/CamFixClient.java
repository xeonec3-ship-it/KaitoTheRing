package ru.pohsmp.core.client;

import com.mojang.logging.LogUtils;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import net.minecraft.client.Camera;
import net.minecraft.client.Minecraft;
import net.minecraftforge.client.event.RenderHandEvent;
import net.minecraftforge.client.event.ViewportEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.ModList;
import net.minecraftforge.fml.util.ObfuscationReflectionHelper;
import org.slf4j.Logger;

/**
 * Minecraft draws the local player's model only when Camera.isDetached() is true, which depends on the F5 view.
 * ComputeCameraAngles fires after Camera.setup() and before the level is rendered, so the flag set here is what
 * LevelRenderer sees for this frame; Camera.setup() resets it on the next frame.
 * The first-person hand is drawn by camera type, not by isDetached(), so RenderHandEvent is cancelled separately.
 */
public final class CamFixClient {
    private static final Logger LOG = LogUtils.getLogger();
    private static final String CNPC_CLASS = "com.cnpcextended.client.CutsceneCamera";

    private static Field detached;
    private static boolean detachedFailed;
    private static Method cnpcActive;
    private static boolean cnpcTried, cnpcFailed;
    private static boolean activeFrame;

    private CamFixClient() {}

    @SubscribeEvent(priority = EventPriority.LOWEST)
    public static void onCamera(ViewportEvent.ComputeCameraAngles e) {
        activeFrame = false;
        if (!ClientConfig.CAM_ENABLED.get()) return;
        Camera cam = e.getCamera();
        Minecraft mc = Minecraft.getInstance();
        if (cam.isDetached() || mc.player == null || cam.getEntity() != mc.player) return;
        String mode = ClientConfig.CAM_MODE.get();
        boolean on = false;
        if (!"distance".equals(mode)) on = cutsceneActive();
        if (!on && ("distance".equals(mode) || "both".equals(mode) || cnpcFailed)) {
            double max = ClientConfig.CAM_DISTANCE.get();
            on = cam.getPosition().distanceToSqr(mc.player.getEyePosition((float) e.getPartialTick())) > max * max;
        }
        if (on && setDetached(cam)) activeFrame = true;
    }

    @SubscribeEvent
    public static void onHand(RenderHandEvent e) {
        if (activeFrame) e.setCanceled(true);
    }

    private static boolean cutsceneActive() {
        if (!cnpcTried) {
            cnpcTried = true;
            if (!ModList.get().isLoaded("cnpcextended")) {
                cnpcFailed = true;
                LOG.info("[camfix] CNPCExtended not found, using distance check");
            } else {
                try {
                    cnpcActive = Class.forName(CNPC_CLASS).getMethod("isActive");
                    LOG.info("[camfix] using {}.isActive()", CNPC_CLASS);
                } catch (Throwable t) {
                    cnpcFailed = true;
                    LOG.warn("[camfix] {}.isActive() not available, using distance check: {}", CNPC_CLASS, t.toString());
                }
            }
        }
        if (cnpcFailed) return false;
        try {
            return (Boolean) cnpcActive.invoke(null);
        } catch (Throwable t) {
            cnpcFailed = true;
            LOG.warn("[camfix] {}.isActive() failed, using distance check: {}", CNPC_CLASS, t.toString());
            return false;
        }
    }

    private static boolean setDetached(Camera cam) {
        if (detachedFailed) return false;
        try {
            if (detached == null) detached = ObfuscationReflectionHelper.findField(Camera.class, "f_90560_");
            detached.setBoolean(cam, true);
            return true;
        } catch (Throwable t) {
            detachedFailed = true;
            LOG.error("[camfix] cannot set Camera.detached, mod disabled: {}", t.toString());
            return false;
        }
    }
}
