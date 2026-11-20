package ru.pohsmp.core.spell;

import java.util.Set;

/**
 * Pure rules (no Minecraft, tested in MagicRulesTest) of what our magic may go through. Tier keys are Tier.key
 * ("higher", "mythic", "divine", "creation", "unknown"); null = an ordinary spell.
 * <ul>
 *   <li>Owner 20.11: Higher, Mythic, Divine, Creation, Unknown and the whole Silent school are never crafted (Scroll Forge etc.).</li>
 *   <li>Owner 20.11: magic above Higher is not written into spell books and not imbued into items (Arcane Anvil);
 *       Higher still can. Our staffs that come with their spells built in are not affected (nothing is written into them by a player).</li>
 * </ul>
 */
public final class MagicRules {
    private MagicRules() {}

    /** Tiers whose spells are never crafted. */
    public static final Set<String> NO_CRAFT_TIERS = Set.of("higher", "mythic", "divine", "creation", "unknown");
    /** Tiers whose spells are never written into a book or imbued into an item by a player. */
    public static final Set<String> NO_BIND_TIERS = Set.of("mythic", "divine", "creation", "unknown");

    /** May a spell with this built-in tier (null = none) and school be crafted? */
    public static boolean craftBanned(String tierKey, boolean silentSchool) {
        return silentSchool || (tierKey != null && NO_CRAFT_TIERS.contains(tierKey));
    }

    /** May a scroll of this tier (null = ordinary) be written into a spell book / imbued into an item? */
    public static boolean bindBanned(String tierKey) {
        return tierKey != null && NO_BIND_TIERS.contains(tierKey);
    }
}
