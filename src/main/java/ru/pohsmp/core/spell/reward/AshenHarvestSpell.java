package ru.pohsmp.core.spell.reward;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import java.util.HashSet;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.spell.Tasks;

/**
 * «Пепельная Жатва» (reward of the Cult Leader): the ghostly fire scythe sweeps a wide arc in front of the caster (r4, 150°): damage and
 * fire; the ash trail left in that arc burns whoever walks in for 3 s. Fx: ashen_harvest (swing), ashen_harvest_trail (fallback: the
 * Cult Leader's cult_ash_slash / cult_ash_trail).
 */
public class AshenHarvestSpell extends RewardSpell {
    public AshenHarvestSpell() {
        super(RewardMath.ASHEN_HARVEST, RewardMath.ASH_CAST, RewardMath.ASH_CD, RewardMath.ASH_MANA, RewardMath.ASH_MANA_LVL);
    }

    @Override public Optional<SoundEvent> getCastStartSound() { return Optional.of(SoundEvents.BLAZE_SHOOT); }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("damage", num(lv(RewardMath.ASH_DAMAGE, level))), ui("fire", (int) lv(RewardMath.ASH_FIRE, level)),
                ui("trail", (int) RewardMath.ASH_TRAIL_SECONDS, num(lv(RewardMath.ASH_TRAIL_DPS, level))));
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            Vec3 at = caster.position();
            float yaw = caster.getYRot();
            Tasks.add(new Tasks.Task() {
                int age;

                @Override
                public boolean tick() {
                    if (age++ < RewardMath.ASH_SWING_AT) return true;
                    swing(sl, caster, at, yaw, spellLevel);
                    return false;
                }
            });
        }
        super.onCast(level, spellLevel, caster, source, md);
    }

    private static List<LivingEntity> inArc(ServerLevel sl, LivingEntity caster, Vec3 at, float yaw) {
        return around(sl, at, RewardMath.ASH_RADIUS + 1, e -> hittable(caster, e)
                && RewardMath.inSector(e.getX() - at.x, e.getZ() - at.z, yaw, RewardMath.ASH_RADIUS + e.getBbWidth() / 2, RewardMath.ASH_ARC)
                && Math.abs(e.getY() - at.y) < 3);
    }

    private static void swing(ServerLevel sl, LivingEntity caster, Vec3 at, float yaw, int lvl) {
        play(sl, "ashen_harvest", "cult_ash_slash", s -> s.at(at).yaw(yaw).caster(caster));
        sl.playSound(null, at.x, at.y, at.z, SoundEvents.PLAYER_ATTACK_SWEEP, SoundSource.PLAYERS, 1.2f, 0.6f);
        sl.playSound(null, at.x, at.y, at.z, SoundEvents.FIRECHARGE_USE, SoundSource.PLAYERS, 1f, 0.8f);
        float dmg = dmg(lv(RewardMath.ASH_DAMAGE, lvl));
        int fire = (int) lv(RewardMath.ASH_FIRE, lvl);
        for (LivingEntity e : inArc(sl, caster, at, yaw)) {
            if (hurt(sl, caster, e, dmg)) e.setSecondsOnFire(fire);
        }
        int trailFx = play(sl, "ashen_harvest_trail", "cult_ash_trail", s -> s.at(at).yaw(yaw).caster(caster));
        int life = RewardMath.ticks(RewardMath.ASH_TRAIL_SECONDS);
        float tick = dmg(lv(RewardMath.ASH_TRAIL_DPS, lvl) / 2);   // every 10 ticks
        Tasks.add(new Tasks.Task() {
            int age;
            final Set<UUID> seen = new HashSet<>();

            @Override
            public boolean tick() {
                age++;
                if (age >= life) {
                    stopFx(sl, trailFx);
                    return false;
                }
                if (age % 10 != 0) return true;
                for (LivingEntity e : inArc(sl, caster, at, yaw)) {
                    if (Math.abs(e.getY() - at.y) > 1.5) continue;
                    hurt(sl, caster, e, tick);
                    if (seen.add(e.getUUID()) || e.getRemainingFireTicks() < 20) e.setSecondsOnFire(2);
                }
                return true;
            }
        });
    }
}
