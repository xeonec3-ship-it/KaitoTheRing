package ru.pohsmp.core.spell.silent;

import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.Level;
import ru.pohsmp.core.silent.SilentWitch;

/** "Gate" (T03): ultimate, 50 s cast under music, only in the full Silent Witch outfit. Stub until T03: the slot exists in the staff, the cast only says "not ready yet". */
public class SilentGateSpell extends SilentStaffSpell {
    public static final String PATH = "silent_gate";

    public SilentGateSpell() {
        super(PATH, 180, 1000, 0);
    }

    /** T19 effect 10: castable only in the full Silent Witch outfit. */
    @Override
    protected String whyNot(Level level, LivingEntity entity) {
        return SilentWitch.fullSet(entity) ? null : "need_outfit";
    }

    /** The cast is tied to the music (build-up 0-49 s, strike from 50 s): the robe's Silent cast time reduction does not apply. */
    @Override
    public int getEffectiveCastTime(int spellLevel, LivingEntity entity) {
        return getCastTime(spellLevel);
    }
}
