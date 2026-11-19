package ru.pohsmp.core.spell.illusion;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.AbstractSpell;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.spells.SpellRarity;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraftforge.common.MinecraftForge;
import ru.pohsmp.core.ServerConfig;

/** T22: the eight spells of the Illusions school by id (Reg registers them by these ids) and their event classes. */
public final class IllusionSpells {
    private IllusionSpells() {}

    public static AbstractSpell make(String path) {
        return switch (path) {
            case MirrorImagesSpell.PATH -> new MirrorImagesSpell();
            case FalseStepSpell.PATH -> new FalseStepSpell();
            case PhantomPainSpell.PATH -> new PhantomPainSpell();
            case BorrowedFaceSpell.PATH -> new BorrowedFaceSpell();
            case VeilSpell.PATH -> new VeilSpell();
            case MirrorLabyrinthSpell.PATH -> new MirrorLabyrinthSpell();
            case WakingNightmareSpell.PATH -> new WakingNightmareSpell();
            case ButterflyDreamSpell.PATH -> new ButterflyDreamSpell();
            default -> new Pending(path);
        };
    }

    public static void registerEvents() {
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.illusion.Illusions.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.illusion.Copies.class);
        MinecraftForge.EVENT_BUS.register(ru.pohsmp.core.illusion.Voices.class);
        MinecraftForge.EVENT_BUS.register(PhantomPainSpell.Events.class);
        MinecraftForge.EVENT_BUS.register(BorrowedFaceSpell.Events.class);
        MinecraftForge.EVENT_BUS.register(MirrorImagesSpell.Events.class);
        MinecraftForge.EVENT_BUS.register(VeilSpell.Events.class);
        MinecraftForge.EVENT_BUS.register(MirrorLabyrinthSpell.Events.class);
        MinecraftForge.EVENT_BUS.register(WakingNightmareSpell.Events.class);
        MinecraftForge.EVENT_BUS.register(ButterflyDreamSpell.Events.class);
    }

    /** A spell of the school not written yet: registered (scrolls, tiers), never cast. */
    static final class Pending extends IllusionBase {
        Pending(String path) {
            super(path, SpellRarity.UNCOMMON, 1, 0, ServerConfig.VEIL_MANA, ServerConfig.VEIL_COOLDOWN);
        }

        @Override public CastType getCastType() { return CastType.INSTANT; }

        @Override
        public boolean checkPreCastConditions(Level level, int spellLevel, LivingEntity entity, MagicData md) {
            if (entity instanceof Player p && !level.isClientSide) p.displayClientMessage(Component.literal("…"), true);
            return false;
        }
    }
}
