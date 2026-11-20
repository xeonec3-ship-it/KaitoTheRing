package ru.pohsmp.core.boss.ereb;

import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.level.Level;

/**
 * The POINT the finale's «Сон бабочки» is cast from (owner: caster = the point where Ereb stood, not him — he vanishes at 5.0 s while the
 * spell's scene and dream go on). ButterflyDreamSpell and Cutscene need a living caster known to the clients (the camera orbits it), so
 * the point is an invisible, silent, unhittable entity without AI that is drawn as nothing and removes itself when the dream is over.
 * Never saved: after a restart the dream (kept in memory only) is gone too.
 */
public class ErebDreamPoint extends Mob {
    private int life = 20 * 60 * 3;

    public ErebDreamPoint(EntityType<? extends Mob> type, Level level) {
        super(type, level);
        setNoAi(true);
        setNoGravity(true);
        setInvisible(true);
        setInvulnerable(true);
        setSilent(true);
        noPhysics = true;
    }

    public static AttributeSupplier.Builder attributes() {
        return Mob.createMobAttributes().add(Attributes.MAX_HEALTH, 1);
    }

    /** It lives this many ticks more, then is removed. */
    public void lifeTicks(int ticks) {
        life = ticks;
    }

    @Override
    public void tick() {
        super.tick();
        if (!level().isClientSide && --life <= 0) discard();
    }

    @Override
    public boolean hurt(DamageSource src, float amount) {
        return false;
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
    public boolean canBeCollidedWith() {
        return false;
    }

    @Override
    public boolean shouldBeSaved() {
        return false;
    }

    @Override
    public boolean removeWhenFarAway(double d) {
        return false;
    }

    @Override
    public net.minecraft.network.chat.Component getTypeName() {
        return net.minecraft.network.chat.Component.translatable("entity.pohsmp_core.ereb");
    }
}
