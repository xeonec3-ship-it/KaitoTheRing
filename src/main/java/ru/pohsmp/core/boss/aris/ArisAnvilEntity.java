package ru.pohsmp.core.boss.aris;

import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.protocol.Packet;
import net.minecraft.network.protocol.game.ClientGamePacketListener;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.AABB;
import net.minecraftforge.network.NetworkHooks;

/**
 * An anvil grown from the ground («Ковка»): no blocks are placed (owner) — the anvil is the mesh of fx aris_anvil_rise, this entity
 * is only its collision (like a shulker or a boat: players and mobs bump into it, arrows and the cone of «Мехи» are stopped by it).
 * Box 2.6 × 1.6 × 1.2, the long side along x (yaw 0) or z (yaw 90); it grows from the ground with the mesh over 12 ticks. The fight
 * (ArisFight) owns its fx and its life; this only keeps the box and removes itself if left behind.
 */
public class ArisAnvilEntity extends Entity {
    public ArisAnvilEntity(EntityType<?> type, Level level) {
        super(type, level);
        noPhysics = true;
        setNoGravity(true);
    }

    /** Long side along z (the anvil turned 90°)? */
    private boolean alongZ() {
        float y = ((getYRot() % 180) + 180) % 180;
        return y > 45 && y < 135;
    }

    @Override
    protected AABB makeBoundingBox() {
        double hx = (alongZ() ? ArisMath.ANVIL_SHORT : ArisMath.ANVIL_LONG) / 2, hz = (alongZ() ? ArisMath.ANVIL_LONG : ArisMath.ANVIL_SHORT) / 2;
        double h = Math.max(0.05, ArisMath.anvilHeight(tickCount));
        return new AABB(getX() - hx, getY(), getZ() - hz, getX() + hx, getY() + h, getZ() + hz);
    }

    /** Half sizes on the ground plane (x, z). */
    public double halfX() {
        return (alongZ() ? ArisMath.ANVIL_SHORT : ArisMath.ANVIL_LONG) / 2;
    }

    public double halfZ() {
        return (alongZ() ? ArisMath.ANVIL_LONG : ArisMath.ANVIL_SHORT) / 2;
    }

    @Override
    public void tick() {
        super.tick();
        if (tickCount <= ArisMath.ANVIL_GROW + 1) setBoundingBox(makeBoundingBox());
        if (!level().isClientSide && tickCount > 20 * 130) discard();   // safety: never left behind
    }

    @Override
    public boolean canBeCollidedWith() {
        return isAlive();
    }

    @Override
    public boolean isPickable() {
        return false;
    }

    @Override
    public boolean isPushable() {
        return false;
    }

    @Override
    public boolean shouldRender(double x, double y, double z) {
        return false;   // the fx draws it
    }

    @Override
    protected void defineSynchedData() {}

    @Override
    protected void readAdditionalSaveData(CompoundTag tag) {}

    @Override
    protected void addAdditionalSaveData(CompoundTag tag) {}

    @Override
    public boolean shouldBeSaved() {
        return false;
    }

    @Override
    public Packet<ClientGamePacketListener> getAddEntityPacket() {
        return NetworkHooks.getEntitySpawningPacket(this);
    }
}
