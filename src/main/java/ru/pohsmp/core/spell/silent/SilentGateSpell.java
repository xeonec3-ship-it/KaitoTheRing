package ru.pohsmp.core.spell.silent;

/** "Gate" (T03): ultimate, 50 s cast under music, only in the full Silent Witch outfit. Stub until T03: the slot exists in the staff, the cast only says "not ready yet". */
public class SilentGateSpell extends SilentStaffSpell {
    public static final String PATH = "silent_gate";

    public SilentGateSpell() {
        super(PATH, 180, 1000, 0);
    }
}
