package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.events.SpellOnCastEvent;
import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.registry.SpellRegistry;
import io.redspace.ironsspellbooks.api.spells.AbstractSpell;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.util.AnimationHolder;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.LivingEntity;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.living.LivingDeathEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import ru.pohsmp.core.DivineEvents;
import ru.pohsmp.core.PohCore;

/**
 * Owner 21.11: while a player's spell with an animation or a cutscene runs, no other spell may start (before, a new cast cut the old one:
 * Iron's attemptInitiateCast cancels a running cast before any event). Players only, bosses are not touched.
 * <ul>
 *   <li>The refusal: mixin/AbstractSpellMixin at the head of attemptInitiateCast — every way to start a spell goes there (book, scroll,
 *       staff, a curio spell container like the T35 mantle / mask, quick cast keys, /cast). No mana, no cooldown, the running cast goes on.
 *       Hint over the hotbar (message.pohsmp_core.cast_busy) and a quiet bass note.</li>
 *   <li>The window: see {@link CastLockMath}. Begins when an animated cast starts (mixin, attemptInitiateCast returned true),
 *       the tail starts at Iron's onCast (SpellOnCastEvent), cutscenes come from Cutscene.start / end.</li>
 *   <li>Ends at once: death, logout, change of dimension, respawn, Epic Fight stun or «Сломать блок» (BossEpicFight), a cast stopped
 *       before it took effect (Iron's cancel rules: hit by a stun, opening a screen, switching the item, the joint cast's second mage).</li>
 * </ul>
 */
@Mod.EventBusSubscriber(modid = PohCore.MODID)
public final class CastLock {
    private CastLock() {}

    private static final Map<UUID, CastLockMath.State> STATE = new HashMap<>();
    private static final Map<UUID, Long> LAST_TOLD = new HashMap<>();
    private static final Map<String, Boolean> ANIMATED = new HashMap<>();

    /** True if this spell is ours and has its own player animation or a cutscene. */
    public static boolean animated(AbstractSpell sp) {
        if (sp == null || sp == SpellRegistry.none()) return false;
        String id = sp.getSpellId();
        Boolean b = ANIMATED.get(id);
        if (b != null) return b;
        boolean r = id.startsWith(PohCore.MODID + ":") && (sp instanceof FixedCastSpell || ours(sp.getCastStartAnimation()) || ours(sp.getCastFinishAnimation()));
        ANIMATED.put(id, r);
        return r;
    }

    private static boolean ours(AnimationHolder h) {
        if (h == null) return false;
        try {
            return h.getForPlayer().map(ResourceLocation::getPath).map(p -> p.startsWith("pohsmp_")).orElse(false);
        } catch (RuntimeException e) {
            return false;
        }
    }

    /** Finish tail of this cast, or -1 if it takes no window. */
    private static int tail(ServerPlayer p, AbstractSpell sp) {
        boolean ours = sp.getSpellId().startsWith(PohCore.MODID + ":");
        boolean tiered = DivineEvents.scrollTier(p, MagicData.getPlayerMagicData(p), sp.getSpellId()) != null;
        return CastLockMath.tail(ours, animated(sp), tiered, sp.getCastType() == CastType.INSTANT);
    }

    private static boolean castingThis(ServerPlayer p, CastLockMath.State s) {
        if (s == null || s.spell() == null) return false;
        MagicData md = MagicData.getPlayerMagicData(p);
        return md.isCasting() && s.spell().equals(md.getCastingSpellId());
    }

    /** True while the player may not start a spell (also for scripts and tests). */
    public static boolean busy(ServerPlayer p) {
        CastLockMath.State s = STATE.get(p.getUUID());
        return CastLockMath.locked(s, p.level().getGameTime(), castingThis(p, s));
    }

    /** Called by the mixin before Iron's starts a cast: true = refuse it (hint and sound already sent). */
    public static boolean refuse(ServerPlayer p, AbstractSpell sp) {
        CastLockMath.State s = STATE.get(p.getUUID());
        if (s == null) return false;
        long now = p.level().getGameTime();
        boolean recast = sp != null && s.spell() != null && s.spell().equals(sp.getSpellId())
                && MagicData.getPlayerMagicData(p).getPlayerRecasts().hasRecastForSpell(sp.getSpellId());
        if (!CastLockMath.refuses(s, now, castingThis(p, s), recast)) {
            if (!recast) STATE.remove(p.getUUID());   // a finished window: forget it before the new cast
            return false;
        }
        Long last = LAST_TOLD.get(p.getUUID());
        if (last == null || now - last >= 10 || now < last) {   // holding the button repeats the use: say it twice a second at most
            LAST_TOLD.put(p.getUUID(), now);
            SpellBans.tell(p, "cast_busy");
            p.playNotifySound(SoundEvents.NOTE_BLOCK_BASS.value(), SoundSource.PLAYERS, 0.35f, 0.6f);
        }
        return true;
    }

    /** Called by the mixin after Iron's started a cast. */
    public static void begin(ServerPlayer p, AbstractSpell sp) {
        if (sp == null || tail(p, sp) < 0) return;
        STATE.put(p.getUUID(), CastLockMath.begin(STATE.get(p.getUUID()), sp.getSpellId(), p.level().getGameTime()));
    }

    /** The caster opened a cutscene (Cutscene.start). */
    public static void scene(LivingEntity caster, int key, int dur) {
        if (caster instanceof ServerPlayer p)
            STATE.put(p.getUUID(), CastLockMath.scene(STATE.get(p.getUUID()), key, p.level().getGameTime(), dur));
    }

    /** The caster's cutscene is over (Cutscene.end). */
    public static void sceneEnd(LivingEntity caster, int key) {
        if (caster instanceof ServerPlayer p) CastLockMath.sceneEnd(STATE.get(p.getUUID()), key);
    }

    /**
     * Ends the window at once (stun, «Сломать блок»). If Iron's still runs the cast itself (a stun that does not cancel it),
     * the window stays until that cast stops: the spell is still going and must not be cut by a new one.
     */
    public static void interrupt(LivingEntity e) {
        if (!(e instanceof ServerPlayer p)) return;
        if (!castingThis(p, STATE.get(p.getUUID()))) STATE.remove(p.getUUID());
    }

    @SubscribeEvent(priority = EventPriority.LOWEST)
    public static void onCast(SpellOnCastEvent e) {
        if (!(e.getEntity() instanceof ServerPlayer p)) return;
        AbstractSpell sp = SpellRegistry.getSpell(e.getSpellId());
        if (sp == null) return;
        int tail = tail(p, sp);
        if (tail < 0) return;
        long now = p.level().getGameTime();
        CastLockMath.State s = STATE.get(p.getUUID());
        if (s == null || !e.getSpellId().equals(s.spell())) {   // cast some other way (/cast, a script): the tail still holds
            s = CastLockMath.begin(s, e.getSpellId(), now);
            STATE.put(p.getUUID(), s);
        }
        CastLockMath.fired(s, now, tail);
    }

    @SubscribeEvent
    public static void onPlayerTick(TickEvent.PlayerTickEvent e) {
        if (e.phase != TickEvent.Phase.END || STATE.isEmpty() || !(e.player instanceof ServerPlayer p)) return;
        CastLockMath.State s = STATE.get(p.getUUID());
        if (s == null) return;
        if (!p.isAlive() || CastLockMath.tick(s, p.level().getGameTime(), castingThis(p, s)) == null) STATE.remove(p.getUUID());
    }

    @SubscribeEvent
    public static void onDeath(LivingDeathEvent e) {
        interrupt(e.getEntity());
    }

    @SubscribeEvent
    public static void onLogout(PlayerEvent.PlayerLoggedOutEvent e) {
        STATE.remove(e.getEntity().getUUID());
        LAST_TOLD.remove(e.getEntity().getUUID());
    }

    @SubscribeEvent
    public static void onDimension(PlayerEvent.PlayerChangedDimensionEvent e) {
        STATE.remove(e.getEntity().getUUID());
    }

    @SubscribeEvent
    public static void onRespawn(PlayerEvent.PlayerRespawnEvent e) {
        STATE.remove(e.getEntity().getUUID());
    }

    @SubscribeEvent
    public static void onStopping(ServerStoppingEvent e) {
        STATE.clear();
        LAST_TOLD.clear();
    }
}
