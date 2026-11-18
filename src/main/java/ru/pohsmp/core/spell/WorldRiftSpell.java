package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import net.minecraft.core.BlockPos;
import net.minecraft.core.particles.BlockParticleOption;
import net.minecraft.core.particles.DustParticleOptions;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.Vec3;
import org.joml.Vector3f;
import ru.pohsmp.core.DivineEvents;
import ru.pohsmp.core.net.Net;

/** Higher: the ground splits along the caster's gaze for 20 blocks; whoever stands on the crack is thrown up, a second later pillars of darkness rise from it. */
public class WorldRiftSpell extends HigherSpell {
    public static final String PATH = "world_rift";
    private static final int LEN = 20;
    private static final double W = 1.6, TOSS_DMG = 8, PILLAR_DMG = 12;
    public static final int COLOR = 0x5A1A8A;
    private static final DustParticleOptions DARK = new DustParticleOptions(new Vector3f(0.18f, 0.02f, 0.28f), 1.6f);

    public WorldRiftSpell() {
        super(PATH, 10);
    }

    @Override public CastType getCastType() { return CastType.LONG; }
    @Override public Optional<SoundEvent> getCastStartSound() { return Optional.of(SoundEvents.WARDEN_DIG); }
    @Override public Optional<SoundEvent> getCastFinishSound() { return Optional.empty(); }

    @Override
    public List<MutableComponent> getUniqueInfo(int spellLevel, LivingEntity caster) {
        return List.of(ui("length", LEN), ui("toss", num(TOSS_DMG)), ui("pillars", num(PILLAR_DMG)));
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            Vec3 f = caster.getLookAngle().multiply(1, 0, 1);
            if (f.lengthSqr() < 1e-4) f = new Vec3(0, 0, 1);
            f = f.normalize();
            List<Vec3> pts = new ArrayList<>();
            Vec3 o = caster.position();
            for (int i = 1; i <= LEN; i++) pts.add(PohSpell.ground(sl, caster, o.add(f.scale(i)).add(0, 1.5, 0)));
            Set<UUID> tossed = new HashSet<>();
            final Vec3 dir = f;
            sl.playSound(null, o.x, o.y, o.z, SoundEvents.GENERIC_EXPLODE, SoundSource.PLAYERS, 2f, 0.4f);
            Tasks.add(new Tasks.Task() {
                int age;

                @Override
                public boolean tick() {
                    age++;
                    int shown = Math.min(LEN, age * 2);
                    for (int i = Math.max(0, shown - 2); i < shown; i++) {   // the crack runs forward 2 blocks per tick
                        Vec3 p = pts.get(i);
                        BlockState bs = sl.getBlockState(BlockPos.containing(p.x, p.y - 0.5, p.z));
                        if (!bs.isAir()) DivineEvents.particle(sl, new BlockParticleOption(ParticleTypes.BLOCK, bs), p.x, p.y + 0.2, p.z, 25, 0.5, 0.3);
                        DivineEvents.particle(sl, ParticleTypes.LARGE_SMOKE, p.x, p.y + 0.3, p.z, 4, 0.3, 0.05);
                        if (i % 3 == 0) sl.playSound(null, p.x, p.y, p.z, SoundEvents.DRIPSTONE_BLOCK_BREAK, SoundSource.PLAYERS, 2f, 0.5f);
                        for (LivingEntity e : around(sl, p, W + 1, e -> !friendly(caster, e))) {
                            if (tossed.contains(e.getUUID()) || hdist(e, p) > W) continue;
                            tossed.add(e.getUUID());
                            hurt(sl, caster, e, dmg(TOSS_DMG));
                            push(e, new Vec3(0, 1.05, 0));
                        }
                    }
                    if (age % 2 == 0)
                        for (int i = 0; i < shown; i += 2) {
                            Vec3 p = pts.get(i);
                            Vec3 side = new Vec3(-dir.z, 0, dir.x).scale((sl.random.nextDouble() - 0.5) * 0.8);
                            DivineEvents.particle(sl, DARK, p.x + side.x, p.y + 0.1, p.z + side.z, 1, 0.05, 0);
                        }
                    if (age == LEN / 2 + 20) {
                        sl.playSound(null, o.x, o.y, o.z, SoundEvents.WITHER_SHOOT, SoundSource.PLAYERS, 3f, 0.4f);
                        for (int i = 0; i < LEN; i += 3) {
                            Vec3 p = pts.get(i);
                            fx(sl, p.x, p.y, p.z, new Net.HFx(Net.HFx.PILLAR, key(), -1, -1, 30, p.x, p.y, p.z, 1.1f, COLOR));
                            DivineEvents.particle(sl, ParticleTypes.SQUID_INK, p.x, p.y + 1, p.z, 20, 0.4, 0.2);
                        }
                        Set<UUID> hit = new HashSet<>();
                        for (Vec3 p : pts)
                            for (LivingEntity e : around(sl, p.add(0, 2, 0), W + 3, e -> !friendly(caster, e))) {
                                if (hit.contains(e.getUUID()) || hdist(e, p) > W || e.getY() > p.y + 12) continue;
                                hit.add(e.getUUID());
                                hurt(sl, caster, e, dmg(PILLAR_DMG));
                            }
                        return false;
                    }
                    return true;
                }
            });
        }
        super.onCast(level, spellLevel, caster, source, md);
    }

    private static double hdist(LivingEntity e, Vec3 c) {
        double dx = e.getX() - c.x, dz = e.getZ() - c.z;
        return Math.sqrt(dx * dx + dz * dz);
    }
}
