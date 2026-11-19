package ru.pohsmp.core;

import io.redspace.ironsspellbooks.api.events.SpellOnCastEvent;
import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.registry.SpellRegistry;
import io.redspace.ironsspellbooks.api.spells.AbstractSpell;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.LivingEntity;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.fx.Fx;
import ru.pohsmp.core.spell.PohSpell;

/**
 * T06: the seal of the scroll tier under the caster for ANY spell cast from a tiered scroll (Iron's own ones too).
 * Higher -> fx/school_&lt;school&gt;_cast, Mythic/Divine -> fx/school_&lt;school&gt;_cast_crown (the manager's look). The seal holds
 * while the cast lasts and falls apart its own way on Fx.stop (done, cancelled, interrupted, logout). Instant spells: 2 s.
 * Mod spells cast this way skip their ordinary school sign (PohSpell.onCast asks {@link #shown}).
 */
public final class SchoolSeals {
    private SchoolSeals() {}

    private static final int INSTANT_TICKS = 40;

    private record Run(String spellId, int inst) {}

    private static final Map<UUID, Run> RUNS = new HashMap<>();
    /** player -> game time a tier seal was last shown (running or just played): the ordinary sign stays off then. */
    private static final Map<UUID, Long> SHOWN = new HashMap<>();

    /** Effect id for this spell and tier, or null (no tier seal: ordinary tier, unknown school). */
    private static String fxFor(AbstractSpell spell, Tier tier) {
        if (spell == null || tier == null || spell.getSchoolType() == null) return null;
        String school = spell.getSchoolType().getId().getPath();
        if (PohSpell.sigilIndex(school) < 0) return null;
        return switch (tier) {
            case HIGHER -> "school_" + school + "_cast";
            case MYTHIC -> "school_" + school + "_cast_crown";
            case DIVINE -> "school_" + school + "_cast_divine";   // owner 19.11: + an arc of 7 golden circles behind

            default -> null;
        };
    }

    /** True if a tier seal is up for this caster now (or was put up this tick or the one before). */
    public static boolean shown(LivingEntity caster) {
        Long t = SHOWN.get(caster.getUUID());
        return t != null && caster.level().getGameTime() - t <= 2;
    }

    @SubscribeEvent
    public static void onPlayerTick(TickEvent.PlayerTickEvent e) {
        if (e.phase != TickEvent.Phase.END || !(e.player instanceof ServerPlayer sp)) return;
        ServerLevel sl = sp.serverLevel();
        MagicData md = MagicData.getPlayerMagicData(sp);
        Run run = RUNS.get(sp.getUUID());
        String id = md.isCasting() ? md.getCastingSpellId() : null;
        if (run != null && (id == null || !id.equals(run.spellId()))) {
            if (run.inst() >= 0) Fx.stop(sl, run.inst(), "");
            RUNS.remove(sp.getUUID());
            run = null;
        }
        if (id == null) return;
        if (run != null) {
            if (run.inst() >= 0) SHOWN.put(sp.getUUID(), sl.getGameTime());
            return;
        }
        if (md.getCastSource() != CastSource.SCROLL || RUNS.containsKey(sp.getUUID())) return;
        String fx = fxFor(SpellRegistry.getSpell(id), DivineEvents.scrollTier(sp, md, id));
        if (fx == null) {
            RUNS.put(sp.getUUID(), new Run(id, -1));   // checked: no seal for this cast
            return;
        }
        RUNS.put(sp.getUUID(), new Run(id, Fx.play(sl, Fx.fx(fx).caster(sp).at(sp.position()))));
        SHOWN.put(sp.getUUID(), sl.getGameTime());
    }

    /** Instant spells never show as "casting": their seal stands 2 s and falls apart by itself. */
    @SubscribeEvent
    public static void onCast(SpellOnCastEvent e) {
        if (!(e.getEntity() instanceof ServerPlayer sp) || e.getCastSource() != CastSource.SCROLL) return;
        AbstractSpell spell = SpellRegistry.getSpell(e.getSpellId());
        if (spell == null || spell.getCastType() != CastType.INSTANT) return;
        String fx = fxFor(spell, DivineEvents.scrollTier(sp, MagicData.getPlayerMagicData(sp), e.getSpellId()));
        if (fx == null) return;
        ServerLevel sl = sp.serverLevel();
        Fx.play(sl, Fx.fx(fx).caster(sp).at(sp.position()).duration(INSTANT_TICKS));
        SHOWN.put(sp.getUUID(), sl.getGameTime());
    }

    @SubscribeEvent
    public static void onLogout(PlayerEvent.PlayerLoggedOutEvent e) {
        Run run = RUNS.remove(e.getEntity().getUUID());
        SHOWN.remove(e.getEntity().getUUID());
        if (run != null && run.inst() >= 0 && e.getEntity().level() instanceof ServerLevel sl) Fx.stop(sl, run.inst(), "");
    }
}
