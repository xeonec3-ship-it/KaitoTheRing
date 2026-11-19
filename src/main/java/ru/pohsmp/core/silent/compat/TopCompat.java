package ru.pohsmp.core.silent.compat;

import java.util.function.Function;
import mcjty.theoneprobe.api.ITheOneProbe;
import net.minecraft.world.entity.player.Player;
import ru.pohsmp.core.silent.SilentWitch;

/** The One Probe (IMC "getTheOneProbe"): full-set Silent Witches are blacklisted, the probe shows nothing for them. */
public class TopCompat implements Function<ITheOneProbe, Void> {
    @Override
    public Void apply(ITheOneProbe probe) {
        probe.registerEntityBlacklist((viewer, entity) -> entity instanceof Player p && SilentWitch.nameless(p));
        return null;
    }
}
