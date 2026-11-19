package ru.pohsmp.core.silent.compat;

import mcp.mobius.waila.api.IEntityAccessor;
import mcp.mobius.waila.api.IEntityComponentProvider;
import mcp.mobius.waila.api.IPluginConfig;
import mcp.mobius.waila.api.IRegistrar;
import mcp.mobius.waila.api.IWailaPlugin;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.player.Player;
import ru.pohsmp.core.silent.SilentWitch;

/** WTHIT (declared in waila_plugins.json): a full-set Silent Witch is replaced by "no entity", so no tooltip shows. */
public class WthitCompat implements IWailaPlugin {
    @Override
    public void register(IRegistrar reg) {
        reg.addOverride(new IEntityComponentProvider() {
            @Override
            public Entity getOverride(IEntityAccessor accessor, IPluginConfig config) {
                return accessor.getEntity() instanceof Player p && SilentWitch.nameless(p) ? EMPTY_ENTITY : null;
            }
        }, Player.class, 0);
    }
}
