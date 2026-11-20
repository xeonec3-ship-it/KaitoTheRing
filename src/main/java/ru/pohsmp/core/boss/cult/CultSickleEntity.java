package ru.pohsmp.core.boss.cult;

import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.protocol.Packet;
import net.minecraft.network.protocol.game.ClientGamePacketListener;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.level.Level;
import net.minecraftforge.network.NetworkHooks;

/**
 * «Огненный серп»: the thrown scythe. No physics of its own — the boss moves it along the arc each tick (CultFight.sickle) and removes
 * it on the catch; the client draws the cult_scythe item spinning (CultSickleRenderer) with the fx cult_sickle_spin on it.
 */
public class CultSickleEntity extends Entity {
    public CultSickleEntity(EntityType<?> type, Level level) {
        super(type, level);
        noPhysics = true;
        setNoGravity(true);
    }

    @Override
    protected void defineSynchedData() {}

    @Override
    public void tick() {
        super.tick();
        if (!level().isClientSide && tickCount > 100) discard();   // safety: never left behind
    }

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
