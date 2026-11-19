package ru.pohsmp.core.silent;

import net.minecraft.world.entity.LivingEntity;

/** Server API of the Silent Witch outfit for other spells (agreed with T20). */
public final class SilentOutfit {
    private SilentOutfit() {}

    /** Longest the cat stays a dragon if "return" never comes (ticks). */
    public static final int DRAGON_MAX = 20 * 60;

    /**
     * Nero's transformation: "dragon" - the cat jumps off and dissolves (nero_dragon), "return" - it comes back (nero_return).
     * Checks the full set and sends the animation to players near the wearer; true when the cat exists and the animation started
     * (false: no full set or unknown anim - keep the plain dragon shadow).
     */
    public static boolean nero(LivingEntity wearer, String anim) {
        return switch (anim) {
            case "dragon" -> SilentWitch.neroDragon(wearer, DRAGON_MAX);
            case "return" -> SilentWitch.neroDragon(wearer, 0);
            default -> false;
        };
    }
}
