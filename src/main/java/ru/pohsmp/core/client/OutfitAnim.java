package ru.pohsmp.core.client;

import io.redspace.ironsspellbooks.player.ClientMagicData;
import java.util.HashMap;
import java.util.Map;
import net.minecraft.client.Minecraft;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import ru.pohsmp.core.silent.SilentWitchArmor;
import software.bernie.geckolib.constant.DataTickets;
import software.bernie.geckolib.core.animation.AnimationState;
import software.bernie.geckolib.core.animation.RawAnimation;

/**
 * Silent Witch outfit, effect 7 (living cloak) and 9 (Nero): which cloak animation plays for the wearer, and whether the cat sits on the shoulder.
 * cast &gt; run (sprinting) &gt; walk (moving) &gt; idle. Nero jumps off while running and comes back {@link #NERO_BACK} ticks after the run stops.
 */
public final class OutfitAnim {
    private OutfitAnim() {}

    public static final int NERO_BACK = 40;
    private static final Map<Integer, Long> LAST_RUN = new HashMap<>();

    public static boolean casting(LivingEntity e) {
        if (e == Minecraft.getInstance().player) return ClientMagicData.isCasting();
        var d = ClientMagicData.getSyncedSpellData(e);
        return d != null && d.isCasting();
    }

    public static boolean running(Entity e) {
        return e.isSprinting() && moving(e);
    }

    public static boolean moving(Entity e) {
        double dx = e.getX() - e.xo, dz = e.getZ() - e.zo;
        return dx * dx + dz * dz > 0.0004;
    }

    public static RawAnimation pick(AnimationState<SilentWitchArmor> s) {
        Entity e = s.getData(DataTickets.ENTITY);
        if (!(e instanceof LivingEntity le)) return SilentWitchArmor.IDLE;
        if (casting(le)) return SilentWitchArmor.CAST;
        if (running(le)) return SilentWitchArmor.RUN;
        if (moving(le)) return SilentWitchArmor.WALK;
        return SilentWitchArmor.IDLE;
    }

    /** Whether Nero is drawn on this wearer's shoulder now (the full set is checked by the caller). */
    public static boolean neroHere(Entity e) {
        long now = e.level().getGameTime();
        if (running(e)) {
            LAST_RUN.put(e.getId(), now);
            return false;
        }
        Long last = LAST_RUN.get(e.getId());
        if (last == null) return true;
        if (now - last >= NERO_BACK || now < last) {
            LAST_RUN.remove(e.getId());
            return true;
        }
        return false;
    }
}
