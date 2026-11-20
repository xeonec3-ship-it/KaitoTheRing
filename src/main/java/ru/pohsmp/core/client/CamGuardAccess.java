package ru.pohsmp.core.client;

import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.world.phys.Vec3;

/**
 * Public door to {@link CamGuard} (package-private) for the boss scenes in ru.pohsmp.core.boss.client — a new file instead of
 * changing CamGuard's visibility. Note: CamGuard keeps one state, the boss camera and DownfallCut never run at once.
 */
public final class CamGuardAccess {
    private CamGuardAccess() {}

    public static void reset() {
        CamGuard.reset();
    }

    public static Vec3 guard(ClientLevel lvl, Vec3 wanted, Vec3 focus) {
        return CamGuard.guard(lvl, wanted, focus);
    }
}
