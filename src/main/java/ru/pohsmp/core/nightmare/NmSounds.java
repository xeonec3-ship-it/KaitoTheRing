package ru.pohsmp.core.nightmare;

import net.minecraft.resources.ResourceLocation;
import net.minecraft.sounds.SoundEvent;
import ru.pohsmp.core.PohCore;

/**
 * T25: the Nightmares' own sounds (sounds.json nightmare.*, volume 0.5 there; approved by the owner 19.11 - «всё устраивает, просто тише»).
 * Not registered: the packets carry them by location (Holder.direct), the clients find them in sounds.json. Volumes in code stay <= 1.
 */
public final class NmSounds {
    private NmSounds() {}

    private static SoundEvent s(String name) {
        return SoundEvent.createVariableRangeEvent(new ResourceLocation(PohCore.MODID, "nightmare." + name));
    }

    public static final SoundEvent HEARTBEAT = s("heartbeat"), CHILD_LAUGH = s("child_laugh"), WHISPER = s("whisper"), SCRAPE = s("scrape"),
            CRAWLER_STEP = s("crawler_step"), CRAWLER_HISS = s("crawler_hiss"), MAW_ROAR = s("maw_roar"), MAW_BITE = s("maw_bite"),
            WEEPER_CRY = s("weeper_cry"), WEEPER_WAIL = s("weeper_wail"), MOTHS = s("moths"), HANDS_GRAB = s("hands_grab"),
            INK_RISE = s("ink_rise"), INK_FALL = s("ink_fall"), CAST_HOUSE = s("cast_house"), CAST_NIGHT = s("cast_night"),
            CAST_NO_AWAKENING = s("cast_no_awakening"), THICKEN = s("thicken");
}
