package ru.pohsmp.core.boss.client;

import io.redspace.ironsspellbooks.entity.mobs.abstract_spell_casting_mob.AbstractSpellCastingMob;
import net.minecraft.world.phys.Vec3;
import org.joml.Vector2f;
import ru.pohsmp.core.boss.ClothSway;
import software.bernie.geckolib.core.animatable.model.CoreGeoBone;

/**
 * Client side of {@link ClothSway} for Iron's casting mobs: the leg as it will be rendered this frame. Iron's procedural walk is only
 * pushed to its transform stack inside {@code setCustomAnimations} and lands on the bones after it, so the bone still holds the animation
 * (or rest) pose — the walk part (rotation and offset) is added here by Iron's own rules.
 */
public final class ClothClient {
    private ClothClient() {}

    public static ClothSway.Leg leg(AbstractSpellCastingMob e, CoreGeoBone leg, Vector2f limb, boolean right) {
        float rot = leg == null ? 0 : leg.getRotX(), py = leg == null ? 0 : leg.getPosY(), pz = leg == null ? 0 : leg.getPosZ();
        if (!e.shouldBeExtraAnimated()) return new ClothSway.Leg(rot, py, pz);
        if (e.isPassenger() && e.getVehicle() != null && e.getVehicle().shouldRiderSit()) return new ClothSway.Leg(rot + ClothSway.LEG_SIT, py, pz);
        if (e.isAnimating() && !e.shouldAlwaysAnimateLegs()) return new ClothSway.Leg(rot, py, pz);
        Vec3 facing = e.getLookAngle().multiply(1, 0, 1).normalize(), motion = e.getDeltaMovement().multiply(1, 0, 1).normalize();
        ClothSway.Leg w = ClothSway.ironWalk(limb.x(), limb.y(), right, (float) facing.dot(motion));
        return new ClothSway.Leg(rot + w.rotX(), py + w.posY(), pz + w.posZ());
    }

    /** Pushes the solved cloth (ClothSway.solve: seven rotX, then the tails' z offsets) onto Iron's transform stack; missing bones skipped. */
    public static void push(io.redspace.ironsspellbooks.entity.mobs.abstract_spell_casting_mob.TransformStack stack,
                            java.util.function.Function<String, CoreGeoBone> bones, float[] d) {
        String[] names = {"coat_front_r", "coat_front_l", "coat_back_r", "coat_back_l", "cape", "cape_mid", "cape_low"};
        for (int i = 0; i < names.length; i++) {
            CoreGeoBone b = bones.apply(names[i]);
            if (b != null && d[i] != 0) stack.pushRotation(b, d[i], 0, 0);
            if (b != null && i < 4 && d[7 + i] != 0) stack.pushPosition(b, 0, 0, d[7 + i]);
        }
    }
}
