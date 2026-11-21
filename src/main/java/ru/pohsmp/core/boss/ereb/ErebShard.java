package ru.pohsmp.core.boss.ereb;

import java.util.Map;
import java.util.UUID;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.entity.projectile.ThrowableItemProjectile;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.EntityHitResult;
import net.minecraft.world.phys.HitResult;

/**
 * A glass shard of Ereb's magic by hand (ereb_shard_cast: a fan from the left palm). A plain projectile: no line to the target, no
 * homing, flies straight without gravity for 2 s, breaks on a block. Hurts with his own damage type (boss_attack); one fan hits the
 * same target at most shards_per_target times (the fan's tally is shared by its shards).
 */
public class ErebShard extends ThrowableItemProjectile {
    private float damage = 9;
    /** The fan's tally: target → hits (server only, shared by the fan's shards). */
    private Map<UUID, Integer> tally;
    private int cap = 3;

    public ErebShard(EntityType<? extends ErebShard> type, Level level) {
        super(type, level);
        setNoGravity(true);
    }

    public void setup(float damage, Map<UUID, Integer> tally, int cap) {
        this.damage = damage;
        this.tally = tally;
        this.cap = cap;
    }

    @Override
    protected Item getDefaultItem() {
        return Items.GLASS_PANE;
    }

    @Override
    public void tick() {
        super.tick();
        if (level().isClientSide) {
            if (tickCount % 2 == 0) level().addParticle(ParticleTypes.END_ROD, getX(), getY(), getZ(), 0, 0, 0);
        } else if (tickCount > 40) discard();
    }

    @Override
    protected boolean canHitEntity(Entity e) {
        if (e instanceof ErebBody || e instanceof ErebShard || e instanceof ErebDreamPoint) return false;
        if (e instanceof Player p && (p.isCreative() || p.isSpectator())) return false;
        return super.canHitEntity(e);
    }

    @Override
    protected void onHitEntity(EntityHitResult r) {
        if (!(level() instanceof ServerLevel) || !(r.getEntity() instanceof LivingEntity t)) return;
        int had = tally == null ? 0 : tally.getOrDefault(t.getUUID(), 0);
        if (!ErebMath.shardMayHit(had, cap)) return;
        if (tally != null) tally.put(t.getUUID(), had + 1);
        t.invulnerableTime = 0;
        if (getOwner() instanceof ErebEntity e) t.hurt(e.bossCore().attackDamage(), damage);
        else t.hurt(damageSources().thrown(this, getOwner()), damage);
    }

    @Override
    protected void onHit(HitResult r) {
        super.onHit(r);
        if (level() instanceof ServerLevel sl) {
            sl.sendParticles(new net.minecraft.core.particles.ItemParticleOption(ParticleTypes.ITEM, getItem()), getX(), getY(), getZ(), 6, 0.1, 0.1, 0.1, 0.05);
            sl.playSound(null, getX(), getY(), getZ(), ru.pohsmp.core.boss.BossCore.sound("ereb.shard_break"), SoundSource.HOSTILE, 0.8f, 0.95f + random.nextFloat() * 0.1f);
            discard();
        }
    }

    @Override
    public boolean shouldBeSaved() {
        return false;
    }
}
