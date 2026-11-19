package ru.pohsmp.core.nightmare;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.AbstractSpell;
import io.redspace.ironsspellbooks.api.spells.CastType;
import java.util.List;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraftforge.common.MinecraftForge;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.spell.illusion.IllusionBase;

/** T25: the three spells of the Nightmares school by id (Reg registers them by these ids) and their event classes. */
public final class NightmareSpells {
    private NightmareSpells() {}

    public static final String HOUSE = "house_that_isnt", NIGHT = "endless_night", NO_AWAKENING = "no_awakening";
    public static final List<String> HIGHER = List.of(HOUSE, NIGHT);

    public static AbstractSpell make(String path) {
        return switch (path) {
            case NIGHT -> new EndlessNightSpell();
            case HOUSE -> new HouseThatIsntSpell();
            default -> new Pending(path, path.equals(NO_AWAKENING) ? IllusionBase.Rank.MYTHIC : IllusionBase.Rank.HIGHER);
        };
    }

    public static void registerEvents() {
        MinecraftForge.EVENT_BUS.register(EndlessNightSpell.Events.class);
        MinecraftForge.EVENT_BUS.register(HouseThatIsntSpell.Events.class);
    }

    /** Base of the school's spells: Higher / Mythic on the rules of T22 (level 1, no mana, no cooldown, not crafted). */
    public abstract static class Base extends IllusionBase {
        protected Base(String path, Rank rank, int castTicks) {
            super(path, rank, castTicks, Reg.NIGHTMARE_ID);
        }
    }

    /** A spell of the school not written yet: registered (scrolls, tiers), never cast. */
    static final class Pending extends Base {
        Pending(String path, Rank rank) {
            super(path, rank, 0);
        }

        @Override public CastType getCastType() { return CastType.INSTANT; }

        @Override
        public boolean checkPreCastConditions(Level level, int spellLevel, LivingEntity entity, MagicData md) {
            if (entity instanceof Player p && !level.isClientSide) p.displayClientMessage(Component.literal("…"), true);
            return false;
        }
    }
}
