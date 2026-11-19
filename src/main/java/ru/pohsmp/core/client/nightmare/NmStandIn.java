package ru.pohsmp.core.client.nightmare;

import java.util.EnumMap;
import java.util.Map;
import net.minecraft.client.Minecraft;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.LivingEntity;
import net.minecraftforge.client.event.RenderLivingEvent;
import ru.pohsmp.core.nightmare.Bestiary;
import ru.pohsmp.core.nightmare.NightmareMob;

/**
 * T25: draws a nightmare of the bestiary in place of a real living thing, on this client only (the caster in «Дом, которого нет» and
 * «Пробуждение не наступит», the real monsters of the Mythic). The stand-in is a client-only entity that never enters the level; it takes
 * the real one's place, turn and gait every frame and is drawn by its own renderer inside the real one's RenderLivingEvent.Pre.
 */
public final class NmStandIn {
    private NmStandIn() {}

    private static final Map<NightmareMob.Kind, NightmareMob> DUMMIES = new EnumMap<>(NightmareMob.Kind.class);

    /** Cancels the real one's drawing and draws a kind of nightmare where it is. */
    public static void draw(RenderLivingEvent.Pre<?, ?> e, LivingEntity real, NightmareMob.Kind kind) {
        e.setCanceled(true);
        var mc = Minecraft.getInstance();
        if (mc.level == null) return;
        NightmareMob d = DUMMIES.get(kind);
        if (d == null || d.level() != mc.level) {
            d = Bestiary.TYPES.get(kind).get().create(mc.level);
            if (d == null) return;
            DUMMIES.put(kind, d);
        }
        float pt = e.getPartialTick();
        d.tickCount = 200 + real.tickCount;   // past its «appear», idle loops keep going
        d.setPos(real.getX(), real.getY(), real.getZ());
        d.xo = real.xo;
        d.yo = real.yo;
        d.zo = real.zo;
        d.setYRot(real.getYRot());
        d.yRotO = real.yRotO;
        d.yBodyRot = real.yBodyRot;
        d.yBodyRotO = real.yBodyRotO;
        d.yHeadRot = real.yHeadRot;
        d.yHeadRotO = real.yHeadRotO;
        d.setXRot(real.getXRot());
        d.xRotO = real.xRotO;
        d.walkAnimation.setSpeed(real.walkAnimation.speed());
        d.hurtTime = real.hurtTime;
        float yaw = Mth.lerp(pt, real.yRotO, real.getYRot());
        try {
            mc.getEntityRenderDispatcher().getRenderer(d).render(d, yaw, pt, e.getPoseStack(), e.getMultiBufferSource(), e.getPackedLight());
        } catch (RuntimeException ex) {
            // a renderer that cannot draw it outside the dispatcher: the real one is simply unseen then
        }
    }

    static void clear() {
        DUMMIES.clear();
    }
}
