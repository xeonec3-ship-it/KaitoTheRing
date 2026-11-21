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
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.spell.Tasks;

/**
 * «Длань Лжи» (reward of the Hand of Lies): a ghostly glass hand grabs the looked-at target (up to 16 blocks) and holds it 2.5 s
 * (paralysis: no walking, no attacks); meanwhile the caster and its allies hit it for +25% (RewardMarks). Players (PvP): 1.5 s.
 * Bosses (BossGuard, forge:bosses) are never held — only slowed for 2.5 s. Fx: hand_of_lies (grab), hand_of_lies_hold,
 * hand_of_lies_release — fallback: the Hand's ereb_hand_grab / ereb_hand_hold / ereb_hand_release.
 */
public class HandOfLiesSpell extends RewardSpell {
    public HandOfLiesSpell() {
        super(RewardMath.HAND_OF_LIES, RewardMath.HAND_CAST, RewardMath.HAND_CD, RewardMath.HAND_MANA, RewardMath.HAND_MANA_LVL);
    }

    @Override public Optional<SoundEvent> getCastStartSound() { return Optional.of(SoundEvents.AMETHYST_CLUSTER_PLACE); }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("hold", num(lv(RewardMath.HAND_HOLD, level)), num(lv(RewardMath.HAND_HOLD_PVP, level))),
                ui("bonus", (int) Math.round(RewardMath.HAND_BONUS * 100) + "%"), ui("boss", num(RewardMath.HAND_BOSS_SLOW)));
    }

    @Override
    public boolean checkPreCastConditions(Level level, int spellLevel, LivingEntity entity, MagicData md) {
        return Utils.preCastTargetHelper(level, entity, md, this, (int) RewardMath.HAND_RANGE, 0.35f);
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            LivingEntity t = target(sl, md);
            if (t != null && t.isAlive() && t.distanceTo(caster) <= RewardMath.HAND_RANGE + 2) {
                play(sl, "hand_of_lies", "ereb_hand_grab", s -> s.at(t.position()).caster(caster).target(t));
                sl.playSound(null, t.getX(), t.getY(), t.getZ(), SoundEvents.AMETHYST_BLOCK_RESONATE, SoundSource.PLAYERS, 1.5f, 0.6f);
                Tasks.add(new Tasks.Task() {
                    int age;

                    @Override
                    public boolean tick() {
                        if (++age < RewardMath.HAND_GRAB_AT) return true;
                        if (t.isAlive() && t.level() == sl) grab(sl, caster, t, spellLevel);
                        return false;
                    }
                });
            }
        }
        super.onCast(level, spellLevel, caster, source, md);
    }

    /** How long the hand holds this target (ticks); 0 = a boss, slowed only. */
    static int holdTicks(LivingEntity t, int lvl) {
        if (bossLike(t)) return 0;
        return RewardMath.ticks(lv(t instanceof Player ? RewardMath.HAND_HOLD_PVP : RewardMath.HAND_HOLD, lvl));
    }

    private static void grab(ServerLevel sl, LivingEntity caster, LivingEntity t, int lvl) {
        sl.playSound(null, t.getX(), t.getY(), t.getZ(), SoundEvents.GLASS_HIT, SoundSource.PLAYERS, 1.5f, 0.5f);
        int hold = holdTicks(t, lvl);
        if (hold <= 0) {   // a boss: only slowed, never held or moved
            int slow = RewardMath.ticks(RewardMath.HAND_BOSS_SLOW);
            t.addEffect(new MobEffectInstance(MobEffects.MOVEMENT_SLOWDOWN, slow, 2, false, true, true), caster);
            play(sl, "hand_of_lies_release", "ereb_hand_release", s -> s.at(t.position()).caster(caster).target(t));
            return;
        }
        t.addEffect(new MobEffectInstance(Reg.PARALYSIS.get(), hold, 0, false, true, true), caster);
        RewardMarks.held(t, caster, hold);
        int k = play(sl, "hand_of_lies_hold", "ereb_hand_hold", s -> s.at(t.position()).caster(caster).target(t).attach(t).duration(hold));
        Tasks.add(new Tasks.Task() {
            int age;

            @Override
            public boolean tick() {
                age++;
                if (!t.isAlive() || t.level() != sl || age >= hold) {
                    stopFx(sl, k);
                    if (t.isAlive()) {
                        play(sl, "hand_of_lies_release", "ereb_hand_release", s -> s.at(t.position()).caster(caster).target(t));
                        sl.playSound(null, t.getX(), t.getY(), t.getZ(), SoundEvents.GLASS_BREAK, SoundSource.PLAYERS, 1f, 0.9f);
                    }
                    return false;
                }
                if (!(t instanceof Player)) {   // players are held by the paralysis (their movement is client-side)
                    t.setDeltaMovement(0, Math.min(0, t.getDeltaMovement().y), 0);
                    t.hurtMarked = true;
                }
                return true;
            }
        });
    }
}
