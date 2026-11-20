package ru.pohsmp.core.boss.erebhand;

import java.util.Optional;
import java.util.UUID;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.network.protocol.Packet;
import net.minecraft.network.protocol.game.ClientGamePacketListener;
import net.minecraft.network.syncher.EntityDataAccessor;
import net.minecraft.network.syncher.EntityDataSerializers;
import net.minecraft.network.syncher.SynchedEntityData;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraftforge.network.NetworkHooks;

/**
 * «Падение маски»: a shard of his mask that belongs to one player — in it that player's reflection (the client draws its skin's face
 * in the shard's player_face slot and its name over it). It circles the arena (the fight moves it). One hit or projectile hit by its
 * own player breaks it; anyone else's only makes it ring. Not saved.
 */
public class ErebHandShard extends Entity {
    private static final EntityDataAccessor<Optional<UUID>> OWNER = SynchedEntityData.defineId(ErebHandShard.class, EntityDataSerializers.OPTIONAL_UUID);
    /** Server: the fight that made it (it is told of every hit). */
    ErebHandFight fight;
    private long lastRing;

    public ErebHandShard(EntityType<? extends ErebHandShard> type, Level level) {
        super(type, level);
        noPhysics = true;
        setNoGravity(true);
    }

    @Override
    protected void defineSynchedData() {
        entityData.define(OWNER, Optional.empty());
    }

    public void setOwner(Player p) {
        entityData.set(OWNER, Optional.of(p.getUUID()));
        setCustomName(Component.literal(p.getGameProfile().getName()));
        setCustomNameVisible(true);
    }

    /** The player this shard reflects. */
    public UUID owner() {
        return entityData.get(OWNER).orElse(null);
    }

    @Override
    public void tick() {
        super.tick();
        if (!level().isClientSide && (fight == null || tickCount > 20 * 40)) discard();
    }

    @Override
    public boolean hurt(DamageSource src, float amount) {
        if (!(level() instanceof ServerLevel sl) || isRemoved() || fight == null) return false;
        if (!(src.getEntity() instanceof Player p)) return false;
        if (p.getUUID().equals(owner())) fight.shardBroken(sl, this);
        else if (sl.getGameTime() - lastRing >= 6) {
            lastRing = sl.getGameTime();
            fight.shardRing(sl, this);
        }
        return true;
    }

    @Override
    public boolean isPickable() {
        return !isRemoved();
    }

    @Override
    public boolean isAttackable() {
        return true;
    }

    @Override
    public boolean isPushable() {
        return false;
    }

    @Override
    public boolean shouldBeSaved() {
        return false;
    }

    @Override
    protected void readAdditionalSaveData(CompoundTag tag) {}

    @Override
    protected void addAdditionalSaveData(CompoundTag tag) {}

    @Override
    public Packet<ClientGamePacketListener> getAddEntityPacket() {
        return NetworkHooks.getEntitySpawningPacket(this);
    }
}
