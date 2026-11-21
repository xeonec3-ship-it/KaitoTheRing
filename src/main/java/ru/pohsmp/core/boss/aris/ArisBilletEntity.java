package ru.pohsmp.core.boss.aris;

import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.protocol.Packet;
import net.minecraft.network.protocol.game.ClientGamePacketListener;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.level.Level;
import net.minecraftforge.network.NetworkHooks;

/**
 * «Раскалённая заготовка»: the glowing billet she throws. No physics — the fight moves it along its arc and explodes it 3 s after it
 * lands; drawn by fx (mesh aris_billet in flight, fx aris_billet with the visible zone r3 while it lies).
 */
public class ArisBilletEntity extends Entity {
    /** The fx drawing it now (mesh in flight, then the lying zone): stopped with it, whatever removes it (FX audit 21.11). */
    int fx = -1;

    public ArisBilletEntity(EntityType<?> type, Level level) {
        super(type, level);
        noPhysics = true;
        setNoGravity(true);
    }

    @Override
    public void tick() {
        super.tick();
        if (!level().isClientSide && tickCount > 200) discard();   // safety
    }

    /**
     * Surrender / death in the 10 ticks of flight (cleanup discards it, the timeline is cancelled before landAt) left the endless mesh
     * hanging glowing in the air at the throw point for everyone, latecomers too.
     */
    @Override
    public void remove(RemovalReason reason) {
        if (fx > 0 && level() instanceof net.minecraft.server.level.ServerLevel sl) ru.pohsmp.core.fx.Fx.stop(sl, fx, "");
        fx = -1;
        super.remove(reason);
    }

    @Override
    public boolean shouldRender(double x, double y, double z) {
        return false;
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
