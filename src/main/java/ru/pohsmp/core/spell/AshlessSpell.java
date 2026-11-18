package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.util.Utils;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.ClipContext;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.HitResult;
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.DivineEvents;
import ru.pohsmp.core.net.Net;

/**
 * Ashley: 1.5 s cast with a blue circle under the target, then a pillar of blue fire (14 in r1.5, burning 5 s)
 * and three fire rings running outward to 9 blocks (4 and burning 3 s each). Rings run along the ground: jump over them.
 */
public class AshlessSpell extends HigherSpell {
    public static final String PATH = "ashless_flame";
    private static final int CAST = 30, RING_LIFE = 30;
    private static final int[] RING_AT = {6, 14, 22};
    private static final double PILLAR_R = 1.5, PILLAR_DMG = 14, RING_R = 9, RING_DMG = 4;
    public static final int COLOR = 0x4DA6FF;
    private static final Map<UUID, Integer> TELE = new HashMap<>();

    public AshlessSpell() {
        super(PATH, CAST);
    }

    @Override public CastType getCastType() { return CastType.LONG; }
    @Override public Optional<SoundEvent> getCastStartSound() { return Optional.of(SoundEvents.FIRECHARGE_USE); }
    @Override public Optional<SoundEvent> getCastFinishSound() { return Optional.empty(); }

    @Override
    public List<MutableComponent> getUniqueInfo(int spellLevel, LivingEntity caster) {
        return List.of(ui("pillar", num(PILLAR_DMG)), ui("rings", num(RING_DMG), (int) RING_R));
    }

    @Override
    public boolean checkPreCastConditions(Level level, int spellLevel, LivingEntity entity, MagicData md) {
        return Utils.preCastTargetHelper(level, entity, md, this, 24, 0.35f);
    }

    @Override
    public void onServerPreCast(Level level, int spellLevel, LivingEntity entity, MagicData md) {
        super.onServerPreCast(level, spellLevel, entity, md);
        if (!(level instanceof ServerLevel sl)) return;
        LivingEntity t = target(sl, md);
        if (t == null) return;
        int k = key();
        TELE.put(entity.getUUID(), k);
        fx(sl, t.getX(), t.getY(), t.getZ(), new Net.HFx(Net.HFx.TELE, k, -1, t.getId(), CAST, t.getX(), t.getY(), t.getZ(), 1.8, COLOR));
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity entity, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            LivingEntity t = target(sl, md);
            if (t != null && t.isAlive()) erupt(sl, entity, ground(sl, entity, t.position()));
        }
        super.onCast(level, spellLevel, entity, source, md);
    }

    @Override
    public void onServerCastComplete(Level level, int spellLevel, LivingEntity entity, MagicData md, boolean cancelled) {
        Integer k = TELE.remove(entity.getUUID());
        if (k != null && level instanceof ServerLevel sl) stop(sl, entity.getX(), entity.getY(), entity.getZ(), k);
        super.onServerCastComplete(level, spellLevel, entity, md, cancelled);
    }

    private static Vec3 ground(ServerLevel sl, LivingEntity caster, Vec3 p) {
        BlockHitResult hr = sl.clip(new ClipContext(p.add(0, 0.2, 0), p.add(0, -8, 0), ClipContext.Block.COLLIDER, ClipContext.Fluid.NONE, caster));
        return hr.getType() == HitResult.Type.MISS ? p : hr.getLocation();
    }

    private static double hdist(LivingEntity e, Vec3 c) {
        double dx = e.getX() - c.x, dz = e.getZ() - c.z;
        return Math.sqrt(dx * dx + dz * dz);
    }

    private static void erupt(ServerLevel sl, LivingEntity caster, Vec3 c) {
        fx(sl, c.x, c.y, c.z, new Net.HFx(Net.HFx.PILLAR, key(), -1, -1, 25, c.x, c.y, c.z, PILLAR_R, COLOR));
        burst(sl, c.x, c.y + 0.1, c.z, 3, COLOR);
        sl.playSound(null, c.x, c.y, c.z, SoundEvents.BLAZE_SHOOT, SoundSource.PLAYERS, 2.5f, 0.5f);
        sl.playSound(null, c.x, c.y, c.z, SoundEvents.SOUL_ESCAPE, SoundSource.PLAYERS, 3f, 0.8f);
        sl.playSound(null, c.x, c.y, c.z, SoundEvents.GENERIC_EXPLODE, SoundSource.PLAYERS, 1.2f, 1.6f);
        DivineEvents.particle(sl, ParticleTypes.SOUL_FIRE_FLAME, c.x, c.y + 2, c.z, 120, 0.5, 0.15);
        for (LivingEntity e : around(sl, c, PILLAR_R + 3, e -> !friendly(caster, e))) {
            if (hdist(e, c) > PILLAR_R + e.getBbWidth() / 2 || e.getY() > c.y + 4 || e.getY() < c.y - 2) continue;
            hurt(sl, caster, e, dmg(PILLAR_DMG));
            e.setSecondsOnFire(5);
        }
        Tasks.add(new Tasks.Task() {
            int age;
            final List<Set<UUID>> hit = List.of(new HashSet<>(), new HashSet<>(), new HashSet<>());

            @Override
            public boolean tick() {
                age++;
                boolean any = false;
                for (int k = 0; k < RING_AT.length; k++) {
                    int a = age - RING_AT[k];
                    if (a == 0) {
                        fx(sl, c.x, c.y, c.z, new Net.HFx(Net.HFx.RING, key(), -1, -1, RING_LIFE, c.x, c.y, c.z, RING_R, COLOR));
                        sl.playSound(null, c.x, c.y, c.z, SoundEvents.FIRECHARGE_USE, SoundSource.PLAYERS, 2f, 0.6f + 0.2f * k);
                    }
                    if (a < 0 || a > RING_LIFE) {
                        if (a < 0) any = true;
                        continue;
                    }
                    any = true;
                    double r = 1 + (RING_R - 1) * a / (double) RING_LIFE;
                    if (a % 2 == 0) {
                        int n = (int) (r * 5) + 6;
                        for (int i = 0; i < n; i++) {
                            double an = i * Math.PI * 2 / n + a * 0.05;
                            DivineEvents.particle(sl, ParticleTypes.SOUL_FIRE_FLAME, c.x + Math.cos(an) * r, c.y + 0.15, c.z + Math.sin(an) * r, 1, 0.02, 0.01);
                        }
                    }
                    Set<UUID> done = hit.get(k);
                    for (LivingEntity e : around(sl, c, RING_R + 2, e -> !friendly(caster, e))) {
                        if (done.contains(e.getUUID())) continue;
                        if (Math.abs(hdist(e, c) - r) > 0.6 + e.getBbWidth() / 2) continue;
                        if (e.getY() > c.y + 0.9 || e.getY() < c.y - 1.5) continue;
                        done.add(e.getUUID());
                        hurt(sl, caster, e, dmg(RING_DMG));
                        e.setSecondsOnFire(3);
                    }
                }
                return any;
            }
        });
    }
}
