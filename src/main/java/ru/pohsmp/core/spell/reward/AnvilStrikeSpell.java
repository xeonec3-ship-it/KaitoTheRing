package ru.pohsmp.core.spell.reward;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import java.util.List;
import java.util.Optional;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.spell.PohSpell;
import ru.pohsmp.core.spell.Tasks;

/**
 * «Удар Наковальни» (reward of Aris): a ghostly turquoise hammer falls from the sky onto the looked-at point (up to 20 blocks): area
 * damage r3 and a throw back (none on bosses: HigherSpell.push asks BossGuard); the caster's weapon is «tempered» for 15 s:
 * +20% weapon damage (RewardMarks). Fx: anvil_strike_warn (the mark on the ground), anvil_strike (the hammer), anvil_strike_temper
 * (on the caster) — fallback: Aris's aris_slam.
 */
public class AnvilStrikeSpell extends RewardSpell {
    public AnvilStrikeSpell() {
        super(RewardMath.ANVIL_STRIKE, RewardMath.ANV_CAST, RewardMath.ANV_CD, RewardMath.ANV_MANA, RewardMath.ANV_MANA_LVL);
    }

    @Override public Optional<SoundEvent> getCastStartSound() { return Optional.of(SoundEvents.ANVIL_PLACE); }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("damage", num(lv(RewardMath.ANV_DAMAGE, level))), ui("radius", (int) RewardMath.ANV_RADIUS),
                ui("temper", (int) lv(RewardMath.ANV_TEMPER, level), (int) Math.round(RewardMath.ANV_TEMPER_BONUS * 100) + "%"));
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            Vec3 at = PohSpell.ground(sl, caster, PohSpell.lookPoint(sl, caster, RewardMath.ANV_RANGE));
            int warn = play(sl, "anvil_strike_warn", null, s -> s.at(at).caster(caster));
            Tasks.add(new Tasks.Task() {
                int age;

                @Override
                public boolean tick() {
                    if (++age < RewardMath.ANV_FALL) return true;
                    stopFx(sl, warn);
                    land(sl, caster, at, spellLevel);
                    return false;
                }
            });
        }
        super.onCast(level, spellLevel, caster, source, md);
    }

    private static void land(ServerLevel sl, LivingEntity caster, Vec3 at, int lvl) {
        play(sl, "anvil_strike", "aris_slam", s -> s.at(at).caster(caster).yaw(caster.getYRot()));
        sl.playSound(null, at.x, at.y, at.z, SoundEvents.ANVIL_LAND, SoundSource.PLAYERS, 1.6f, 0.6f);
        sl.playSound(null, at.x, at.y, at.z, SoundEvents.GENERIC_EXPLODE, SoundSource.PLAYERS, 0.8f, 1.2f);
        float dmg = dmg(lv(RewardMath.ANV_DAMAGE, lvl));
        for (LivingEntity e : around(sl, at, RewardMath.ANV_RADIUS + 0.5, e -> hittable(caster, e) && Math.abs(e.getY() - at.y) < 3)) {
            if (!hurt(sl, caster, e, dmg)) continue;
            Vec3 d = e.position().subtract(at).multiply(1, 0, 1);
            d = d.lengthSqr() < 1e-4 ? new Vec3(0, 0, 0) : d.normalize().scale(RewardMath.ANV_KNOCK);
            if (!bossLike(e)) push(e, d.add(0, 0.45, 0));
        }
        if (caster.isAlive()) {
            int ticks = RewardMath.ticks(lv(RewardMath.ANV_TEMPER, lvl));
            RewardMarks.temper(caster, ticks);
            play(sl, "anvil_strike_temper", null, s -> s.at(caster.position()).caster(caster).attach(caster).duration(ticks));
        }
    }
}
