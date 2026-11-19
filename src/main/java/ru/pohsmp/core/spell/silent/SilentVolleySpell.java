package ru.pohsmp.core.spell.silent;

/** "Silent Volley" (T20): 24 small sigils behind the caster, arrows of light into every enemy around. Stub until T20: the slot exists in the staff, the cast only says "not ready yet". */
public class SilentVolleySpell extends SilentStaffSpell {
    public static final String PATH = "silent_volley";

    public SilentVolleySpell() {
        super(PATH, 20, 60, 100);
    }
}
