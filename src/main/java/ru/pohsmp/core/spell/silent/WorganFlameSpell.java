package ru.pohsmp.core.spell.silent;

/** "Black Flame of Worgan" (T20): shadow of a black dragon breathes black fire in a cone. Stub until T20: the slot exists in the staff, the cast only says "not ready yet". */
public class WorganFlameSpell extends SilentStaffSpell {
    public static final String PATH = "worgan_flame";

    public WorganFlameSpell() {
        super(PATH, 30, 40, 150);
    }
}
