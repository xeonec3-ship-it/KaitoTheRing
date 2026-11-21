package ru.pohsmp.core.spell.reward;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.util.Utils;
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
import ru.pohsmp.core.spell.Tasks;

/**
 * «Объятия Ревности» (reward of Irina): threads bind the looked-at target (up to 16 blocks) and yank it to the caster, the staff hook
 * strikes; for 5 s the «метка ревности» — the target takes +20% damage from this caster (RewardMarks). Bosses (BossGuard, forge:bosses)
 * are never pulled: only hit and marked. Fx: jealous_embrace (threads), jealous_embrace_hit (hook), jealous_embrace_mark (fallback:
 * Irina's irina_yank / irina_whip / irina_mark).
 */
public class JealousEmbraceSpell extends RewardSpell {
    public JealousEmbraceSpell() {
        super(RewardMath.JEALOUS_EMBRACE, RewardMath.EMB_CAST, RewardMath.EMB_CD, RewardMath.EMB_MANA, RewardMath.EMB_MANA_LVL);
    }

    @Override public Optional<SoundEvent> getCastStartSound() { return Optional.of(SoundEvents.SPIDER_AMBIENT); }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("damage", num(lv(RewardMath.EMB_DAMAGE, level))), ui("range", (int) RewardMath.EMB_RANGE),
                ui("mark", (int) lv(RewardMath.EMB_MARK, level), (int) Math.round(RewardMath.EMB_MARK_BONUS * 100) + "%"));
    }

    @Override
    public boolean checkPreCastConditions(Level level, int spellLevel, LivingEntity entity, MagicData md) {
        return Utils.preCastTargetHelper(level, entity, md, this, (int) RewardMath.EMB_RANGE, 0.35f);
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            LivingEntity t = target(sl, md);
            if (t != null && t.isAlive() && t.distanceTo(caster) <= RewardMath.EMB_RANGE + 2) embrace(sl, caster, t, spellLevel);
        }
        super.onCast(level, spellLevel, caster, source, md);
    }

    private static void embrace(ServerLevel sl, LivingEntity caster, LivingEntity t, int lvl) {
        play(sl, "jealous_embrace", "irina_yank", s -> s.at(caster.position()).caster(caster).target(t));
        sl.playSound(null, t.getX(), t.getY(), t.getZ(), SoundEvents.CHAIN_PLACE, SoundSource.PLAYERS, 1.2f, 0.7f);
        boolean boss = bossLike(t);
        if (!boss) {
            Vec3 d = caster.position().subtract(t.position()).multiply(1, 0, 1);
            double dist = d.length();
            if (dist > 1e-3) push(t, d.normalize().scale(RewardMath.pullSpeed(dist)).add(0, 0.25 + Math.min(0.3, dist * 0.02), 0));
        }
        int markTicks = RewardMath.ticks(lv(RewardMath.EMB_MARK, lvl));
        Tasks.add(new Tasks.Task() {
            int age;

            @Override
            public boolean tick() {
                if (++age < RewardMath.EMB_HOOK_AT) return true;
                if (!t.isAlive() || !caster.isAlive() || t.level() != sl) return false;
                play(sl, "jealous_embrace_hit", "irina_whip", s -> s.at(t.position()).caster(caster).target(t));
                sl.playSound(null, t.getX(), t.getY(), t.getZ(), SoundEvents.PLAYER_ATTACK_STRONG, SoundSource.PLAYERS, 1f, 0.8f);
                hurt(sl, caster, t, dmg(lv(RewardMath.EMB_DAMAGE, lvl)));
                RewardMarks.jealous(t, caster, markTicks);
                play(sl, "jealous_embrace_mark", "irina_mark", s -> s.at(t.position()).caster(t).attach(t).duration(markTicks));
                return false;
            }
        });
    }
}
