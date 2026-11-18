package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.registry.SchoolRegistry;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.spells.SpellRarity;
import java.util.List;
import net.minecraft.core.BlockPos;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.DivineEvents;

/** Ender: everyone around the caster (except the caster) is thrown away through space to a safe spot N blocks further. */
public class BanishmentSpell extends PohSpell {
    public static final String PATH = "banishment";

    public BanishmentSpell() {
        super(PATH, SchoolRegistry.ENDER_RESOURCE, SpellRarity.UNCOMMON, 6, 30, 0, 50, 10);
    }

    @Override public CastType getCastType() { return CastType.INSTANT; }

    private double radius(int l) { return lv(l, 4, 8); }
    private double dist(int l) { return lv(l, 8, 32); }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("radius", n(radius(level))), ui("distance", n(dist(level))));
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            double d = dist(spellLevel);
            Vec3 c = caster.position();
            for (LivingEntity e : HigherSpell.around(sl, c, radius(spellLevel), e -> e != caster && !e.isSpectator() && !e.isPassenger())) {
                Vec3 dir = e.position().subtract(c).multiply(1, 0, 1);
                if (dir.lengthSqr() < 1e-4) dir = caster.getLookAngle().multiply(1, 0, 1);
                if (dir.lengthSqr() < 1e-4) dir = new Vec3(1, 0, 0);
                dir = dir.normalize();
                Vec3 to = safeSpot(sl, e, dir, d);
                if (to == null) continue;
                DivineEvents.particle(sl, ParticleTypes.PORTAL, e.getX(), e.getY() + 1, e.getZ(), 40, 0.4, 0.4);
                DivineEvents.particle(sl, ParticleTypes.REVERSE_PORTAL, e.getX(), e.getY() + 1, e.getZ(), 20, 0.3, 0.05);
                HigherSpell.place(e, to.x, to.y, to.z);
                e.fallDistance = 0;
                e.setDeltaMovement(Vec3.ZERO);
                DivineEvents.particle(sl, ParticleTypes.PORTAL, to.x, to.y + 1, to.z, 40, 0.4, 0.4);
                sl.playSound(null, to.x, to.y, to.z, SoundEvents.ENDERMAN_TELEPORT, SoundSource.PLAYERS, 1f, 0.8f);
            }
            sl.playSound(null, c.x, c.y, c.z, SoundEvents.END_PORTAL_SPAWN, SoundSource.PLAYERS, 0.6f, 1.6f);
            DivineEvents.particle(sl, ParticleTypes.REVERSE_PORTAL, c.x, c.y + 1, c.z, 80, radius(spellLevel) * 0.4, 0.05);
        }
        super.onCast(level, spellLevel, caster, source, md);
    }

    /** Free spot with ground under it, searched from the full distance back toward the start. */
    private static Vec3 safeSpot(ServerLevel sl, LivingEntity e, Vec3 dir, double d) {
        for (double k = d; k >= 3; k -= 1.5) {
            Vec3 p = e.position().add(dir.scale(k));
            for (int dy = 6; dy >= -8; dy--) {
                double y = Math.floor(p.y) + dy;
                BlockPos below = BlockPos.containing(p.x, y - 0.5, p.z);
                if (!sl.getBlockState(below).isFaceSturdy(sl, below, net.minecraft.core.Direction.UP)) continue;
                AABB box = e.getBoundingBox().move(p.x - e.getX(), y - e.getY(), p.z - e.getZ());
                if (sl.noCollision(e, box) && !sl.containsAnyLiquid(box)) return new Vec3(p.x, y, p.z);
            }
        }
        return null;
    }
}
