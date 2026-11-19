package ru.pohsmp.core.spell.silent;

/** "Barrier" (T20): a dome around the caster that stops projectiles for 8 s. Stub until T20: the slot exists in the staff, the cast only says "not ready yet". */
public class SageBarrierSpell extends SilentStaffSpell {
    public static final String PATH = "sage_barrier";

    public SageBarrierSpell() {
        super(PATH, 40, 30, 120);
    }
}
