package ru.pohsmp.core.silent.compat;

import net.minecraft.world.entity.player.Player;
import ru.pohsmp.core.silent.SilentWitch;
import snownee.jade.api.EntityAccessor;
import snownee.jade.api.IWailaClientRegistration;
import snownee.jade.api.IWailaPlugin;
import snownee.jade.api.WailaPlugin;

/** Jade: looking at a full-set Silent Witch shows no tooltip at all. */
@WailaPlugin
public class JadeCompat implements IWailaPlugin {
    @Override
    public void registerClient(IWailaClientRegistration reg) {
        reg.addRayTraceCallback((hit, accessor, original) ->
                accessor instanceof EntityAccessor ea && ea.getEntity() instanceof Player p && SilentWitch.nameless(p) ? null : accessor);
    }
}
