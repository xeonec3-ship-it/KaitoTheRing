package ru.pohsmp.core.spell.silent;

/** "Wind Spears" (T20): up to 5 wind spears into the heads of enemies in a cone. Stub until T20: the slot exists in the staff, the cast only says "not ready yet". */
public class WindSpearsSpell extends SilentStaffSpell {
    public static final String PATH = "wind_spears";

    public WindSpearsSpell() {
        super(PATH, 6, 20, 40);
    }
}
