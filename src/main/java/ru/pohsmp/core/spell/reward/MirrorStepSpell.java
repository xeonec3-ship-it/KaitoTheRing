package ru.pohsmp.core.spell.reward;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.util.Utils;
import java.util.EnumSet;
import java.util.List;
import java.util.Optional;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.spell.Tasks;

/**
 * «Шаг сквозь отражение» (reward of Ereb): the caster vanishes in a glass ripple, reappears behind the looked-at target (up to 16 blocks)
 * and stabs; 2 s of invisibility. Only the caster moves (bosses stay where they are). No free spot behind, at the corners or the
 * sides — no step, only the stab if the target is already within reach. Fx: mirror_step_vanish, mirror_step_appear, mirror_step
 * (the stab) — fallback: Ereb's ereb_vanish / ereb_appear / ereb_thrust.
 */
public class MirrorStepSpell extends RewardSpell {
    public MirrorStepSpell() {
        super(RewardMath.MIRROR_STEP, RewardMath.MIR_CAST, RewardMath.MIR_CD, RewardMath.MIR_MANA, RewardMath.MIR_MANA_LVL);
    }

    @Override public Optional<SoundEvent> getCastStartSound() { return Optional.of(SoundEvents.AMETHYST_BLOCK_CHIME); }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("damage", num(lv(RewardMath.MIR_DAMAGE, level))), ui("range", (int) RewardMath.MIR_RANGE),
                ui("invis", num(lv(RewardMath.MIR_INVIS, level))));
    }

    @Override
    public boolean checkPreCastConditions(Level level, int spellLevel, LivingEntity entity, MagicData md) {
        return Utils.preCastTargetHelper(level, entity, md, this, (int) RewardMath.MIR_RANGE, 0.35f);
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            LivingEntity t = target(sl, md);
            if (t != null && t.isAlive() && t.distanceTo(caster) <= RewardMath.MIR_RANGE + 2) step(sl, caster, t, spellLevel);
        }
        super.onCast(level, spellLevel, caster, source, md);
    }

    /** A free spot behind t (feet position), or null. */
    private static Vec3 spot(ServerLevel sl, LivingEntity caster, LivingEntity t) {
        double d = t.getBbWidth() / 2 + caster.getBbWidth() / 2 + RewardMath.MIR_BEHIND - 0.5;
        for (boolean ground : new boolean[] {true, false})   // first a spot with floor under it, then any free one (flying targets)
        for (double extra : RewardMath.MIR_TRIES) {
            double[] p = RewardMath.behind(t.getX(), t.getZ(), t.getYRot(), d, extra);
            for (double dy : new double[] {0, 1, -1}) {
                Vec3 at = new Vec3(p[0], t.getY() + dy, p[1]);
                AABB box = caster.getBoundingBox().move(at.subtract(caster.position()));
                if (sl.noCollision(caster, box) && (!ground || !sl.noCollision(caster, box.move(0, -0.6, 0).setMaxY(box.minY)))) return at;
            }
        }
        return null;
    }

    private static void step(ServerLevel sl, LivingEntity caster, LivingEntity t, int lvl) {
        Vec3 to = spot(sl, caster, t);
        if (to != null) {
            Vec3 from = caster.position();
            play(sl, "mirror_step_vanish", "ereb_vanish", s -> s.at(from).caster(caster).yaw(caster.getYRot()));
            sl.playSound(null, from.x, from.y, from.z, SoundEvents.GLASS_BREAK, SoundSource.PLAYERS, 1f, 1.4f);
            float yaw = RewardMath.yawTo(to.x, to.z, t.getX(), t.getZ());
            if (caster instanceof ServerPlayer p) {
                p.connection.teleport(to.x, to.y, to.z, yaw, p.getXRot(), EnumSet.noneOf(net.minecraft.world.entity.RelativeMovement.class));
            } else {
                caster.teleportTo(to.x, to.y, to.z);
                caster.setYRot(yaw);
                caster.setYHeadRot(yaw);
            }
            caster.resetFallDistance();
            play(sl, "mirror_step_appear", "ereb_appear", s -> s.at(to).caster(caster).yaw(yaw));
            sl.playSound(null, to.x, to.y, to.z, SoundEvents.AMETHYST_BLOCK_BREAK, SoundSource.PLAYERS, 1f, 0.8f);
        } else if (caster.distanceTo(t) > 3.5) {
            return;   // nowhere to step and out of reach: the mana is spent, nothing happens (as a missed Iron's spell)
        }
        caster.addEffect(new MobEffectInstance(MobEffects.INVISIBILITY, RewardMath.ticks(lv(RewardMath.MIR_INVIS, lvl)), 0, false, false, true));
        Tasks.add(new Tasks.Task() {
            int age;

            @Override
            public boolean tick() {
                if (++age < RewardMath.MIR_STAB_AT) return true;
                if (!t.isAlive() || !caster.isAlive() || t.level() != sl || caster.distanceTo(t) > 4.5) return false;
                play(sl, "mirror_step", "ereb_thrust", s -> s.at(caster.position()).caster(caster).target(t).yaw(caster.getYRot()));
                sl.playSound(null, t.getX(), t.getY(), t.getZ(), SoundEvents.PLAYER_ATTACK_CRIT, SoundSource.PLAYERS, 1f, 1.2f);
                caster.swing(net.minecraft.world.InteractionHand.MAIN_HAND, true);
                hurt(sl, caster, t, dmg(lv(RewardMath.MIR_DAMAGE, lvl)));
                return false;
            }
        });
    }
}
