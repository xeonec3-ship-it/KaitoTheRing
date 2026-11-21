package ru.pohsmp.core.client.fx;

import java.lang.reflect.Field;
import java.util.Map;
import java.util.WeakHashMap;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.client.event.RenderLevelStageEvent;
import ru.pohsmp.core.client.ClientClock;
import ru.pohsmp.core.fx.MoveSmooth;
import ru.pohsmp.core.net.FxMsg;

/**
 * Client-only patch of the released jar (tools/client_anim_patch): the FxMsg.MOVE glide of the repo's FxClient (MoveSmooth),
 * put into the old FxClient by two injected calls - handle() starts with {@code if (FxGlide.move(m)) return;},
 * onRender() starts with {@code FxGlide.frame(e);}. FxClient's LIVE map and Inst fields are reached by reflection (same mod).
 * Uses no obfuscated Minecraft names (Vec3's constructor and Forge's event API only).
 */
public final class FxGlide {
    private FxGlide() {}

    private static final Map<Object, MoveSmooth> GLIDES = new WeakHashMap<>();
    private static float lastPt;
    private static Map<Integer, Object> live;
    private static Field fFx, fSigil, fMesh;
    private static boolean broken;

    @SuppressWarnings("unchecked")
    private static boolean init() {
        if (live != null) return true;
        if (broken) return false;
        try {
            Field l = FxClient.class.getDeclaredField("LIVE");
            l.setAccessible(true);
            Class<?> inst = Class.forName("ru.pohsmp.core.client.fx.FxClient$Inst");
            fFx = inst.getDeclaredField("fx");
            fSigil = inst.getDeclaredField("sigil");
            fMesh = inst.getDeclaredField("mesh");
            fFx.setAccessible(true);
            fSigil.setAccessible(true);
            fMesh.setAccessible(true);
            live = (Map<Integer, Object>) l.get(null);
            return true;
        } catch (ReflectiveOperationException | RuntimeException ex) {
            broken = true;   // the old behaviour (jump to the new place) stays
            return false;
        }
    }

    /** True when the message was a MOVE and is handled here (FxClient.handle returns at once). */
    public static boolean move(FxMsg m) {
        if (m.op != FxMsg.MOVE || !init()) return false;
        try {
            Object i = live.get(m.inst);
            if (i == null) return true;
            FxRun fx = (FxRun) fFx.get(i);
            SigilRun sigil = (SigilRun) fSigil.get(i);
            MeshDraw.Run mesh = (MeshDraw.Run) fMesh.get(i);
            if (fx == null && sigil == null && mesh == null) return true;
            MoveSmooth g = GLIDES.get(i);
            if (g == null) {
                Vec3 b = fx != null ? fx.base : sigil != null ? sigil.base : mesh.base;
                float yaw = fx != null ? fx.yaw : sigil != null ? sigil.yaw : mesh.yaw;
                float pitch = fx != null ? fx.pitch : mesh != null ? mesh.pitch : 0;
                g = new MoveSmooth(b.x, b.y, b.z, yaw, pitch);
                GLIDES.put(i, g);
            }
            g.move(ClientClock.now(lastPt), m.x, m.y, m.z, m.yaw, m.pitch);
            return true;
        } catch (ReflectiveOperationException | RuntimeException ex) {
            broken = true;
            return false;
        }
    }

    /** Before FxClient draws: every gliding instance is put where its glide is at this frame. */
    public static void frame(RenderLevelStageEvent e) {
        if (e.getStage() != RenderLevelStageEvent.Stage.AFTER_PARTICLES) return;
        lastPt = e.getPartialTick();
        if (GLIDES.isEmpty() || live == null) return;
        double time = ClientClock.now(lastPt);
        try {
            var it = GLIDES.entrySet().iterator();
            while (it.hasNext()) {
                var en = it.next();
                Object i = en.getKey();
                if (!live.containsValue(i)) {
                    it.remove();
                    continue;
                }
                double[] g = en.getValue().sample(time);
                Vec3 p = new Vec3(g[0], g[1], g[2]);
                FxRun fx = (FxRun) fFx.get(i);
                SigilRun sigil = (SigilRun) fSigil.get(i);
                MeshDraw.Run mesh = (MeshDraw.Run) fMesh.get(i);
                if (fx != null) {
                    fx.base = p;
                    fx.yaw = (float) g[3];
                    fx.pitch = (float) g[4];
                }
                if (sigil != null) {
                    sigil.base = p;
                    sigil.yaw = (float) g[3];
                }
                if (mesh != null) {
                    mesh.base = p;
                    mesh.yaw = (float) g[3];
                    mesh.pitch = (float) g[4];
                }
            }
        } catch (ReflectiveOperationException | RuntimeException ex) {
            GLIDES.clear();
        }
    }
}
