package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.util.AnimationHolder;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.Level;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.fml.DistExecutor;

/**
 * Own player animations of the cutscene spells. The files live in assets/irons_spellbooks/player_animation/
 * (made by tools/gen_player_anims.py), so a plain name works with any Iron's version.
 * The staff-less ones also hide the caster's hand items for the cast and the finish (client/HiddenHands).
 */
public final class CastAnims {
    private CastAnims() {}

    /** Length of every finish animation plus a small margin, in ticks. */
    public static final int FINISH_TICKS = 30;

    public static AnimationHolder of(String name) {
        return new AnimationHolder("pohsmp_" + name, true);
    }

    /** Client side only: draw the caster's hands empty for the cast (castTicks) and the finish animation. */
    public static void hideHands(Level level, LivingEntity caster, int castTicks) {
        hideHands(level, caster, castTicks, FINISH_TICKS);
    }

    /** Same, with a longer tail after the cast (finish ticks), e.g. the Gate scene. Another spell cast meanwhile shows the hands at once. */
    public static void hideHands(Level level, LivingEntity caster, int castTicks, int finishTicks) {
        hideHands(level, caster, castTicks, finishTicks, false);
    }

    /** A staff stays in the hand unless staffsToo (only the Gate scene, where the staff floats on its own). */
    public static void hideHands(Level level, LivingEntity caster, int castTicks, int finishTicks, boolean staffsToo) {
        if (!level.isClientSide) return;
        int ticks = castTicks + finishTicks;
        DistExecutor.unsafeRunWhenOn(Dist.CLIENT, () -> () -> ru.pohsmp.core.client.HiddenHands.hide(caster, ticks, finishTicks, staffsToo));
    }
}
