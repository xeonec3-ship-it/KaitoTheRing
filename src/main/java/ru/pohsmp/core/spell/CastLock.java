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
import net.minecraft.network.protocol.game.ClientboundSetCarriedItemPacket;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.ai.attributes.AttributeInstance;
import net.minecraft.world.entity.ai.attributes.AttributeModifier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.item.ItemTossEvent;
import net.minecraftforge.event.entity.living.LivingEntityUseItemEvent;
import net.minecraftforge.event.entity.player.AttackEntityEvent;
import net.minecraftforge.event.entity.player.PlayerContainerEvent;
import net.minecraftforge.event.entity.player.PlayerInteractEvent;
import net.minecraftforge.event.level.BlockEvent;
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
        hint(p);
        return true;
    }

    /** «Заклинание ещё не завершено» over the hotbar and a quiet bass note, at most twice a second (holding a button repeats the act). */
    public static void hint(ServerPlayer p) {
        long now = p.level().getGameTime();
        Long last = LAST_TOLD.get(p.getUUID());
        if (!CastLockMath.hintDue(last == null ? Long.MIN_VALUE : last, now)) return;
        LAST_TOLD.put(p.getUUID(), now);
        SpellBans.tell(p, "cast_busy");
        p.playNotifySound(SoundEvents.NOTE_BLOCK_BASS.value(), SoundSource.PLAYERS, 0.35f, 0.6f);
    }

    /**
     * Called by the mixins on Iron's cancel paths (owner 21.11, 2): false = keep the running cast. The player's own acts (another spell,
     * switching the item, releasing the use button, opening a screen) may not stop the spell that holds the window.
     */
    public static boolean cancelAllowed(ServerPlayer p, CastLockMath.Cancel why) {
        return CastLockMath.cancelAllowed(p.isAlive() && busy(p), why);
    }

    /** The player is held by the window: every act but the camera, the pause menu and the chat is stopped (server events below). */
    private static boolean held(Object e) {
        return e instanceof ServerPlayer p && p.isAlive() && STATE.containsKey(p.getUUID()) && busy(p);
    }

    /** Server: the player is held right now (Epic Fight skills, scripts). Says the hint. */
    public static boolean heldNow(ServerPlayer p) {
        return stop(p, CastLockMath.Act.EF_SKILL);
    }

    /** Server: a spell wheel / spell bar selection is refused now (IronsSelectSpellMixin). */
    public static boolean selectionLocked(ServerPlayer p) {
        return stop(p, CastLockMath.Act.SPELL_SELECT);
    }

    /** Client: the local player is held (set by Net.Lock from the server; the client classes read it in client/CastLockClient). */
    public static volatile boolean clientLocked;

    public static boolean clientHeld(net.minecraft.world.entity.player.Player p) {
        return clientLocked && p.isLocalPlayer();
    }

    private static boolean stop(Object e, CastLockMath.Act a) {
        if (!held(e) || !CastLockMath.blocks(true, a)) return false;
        if (CastLockMath.hints(a)) hint((ServerPlayer) e);
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
        if (e.phase != TickEvent.Phase.END || !(e.player instanceof ServerPlayer p)) return;
        if (STATE.isEmpty() && SENT.isEmpty()) return;
        CastLockMath.State s = STATE.get(p.getUUID());
        if (s != null && (!p.isAlive() || CastLockMath.tick(s, p.level().getGameTime(), castingThis(p, s)) == null)) STATE.remove(p.getUUID());
        hold(p, STATE.containsKey(p.getUUID()) && p.isAlive() && busy(p));
    }

    /** Players whose client was told «held» (CastLockMsg). */
    private static final java.util.Set<UUID> SENT = new java.util.HashSet<>();
    /** The hotbar slot the player had when the window opened. */
    private static final Map<UUID, Integer> SLOT = new HashMap<>();
    private static final UUID STAND_ID = UUID.fromString("6a0b9b0e-3c1e-4c55-9a59-2a1d7c4d2f11");

    /** Keeps the held player still: the client flag, no walking speed (falling and knockback stay), the hotbar slot, no sprint. */
    private static void hold(ServerPlayer p, boolean on) {
        UUID id = p.getUUID();
        if (on != SENT.contains(id)) {
            if (on) {
                SENT.add(id);
                SLOT.put(id, p.getInventory().selected);
            } else {
                SENT.remove(id);
                SLOT.remove(id);
            }
            ru.pohsmp.core.net.Net.CH.send(net.minecraftforge.network.PacketDistributor.PLAYER.with(() -> p), new ru.pohsmp.core.net.Net.Lock(on));
        }
        AttributeInstance speed = p.getAttribute(Attributes.MOVEMENT_SPEED);
        if (speed != null) {
            boolean has = speed.getModifier(STAND_ID) != null;
            if (on && !has) speed.addTransientModifier(new AttributeModifier(STAND_ID, "pohsmp_core cast lock", -1.0, AttributeModifier.Operation.MULTIPLY_TOTAL));
            else if (!on && has) speed.removeModifier(STAND_ID);
        }
        if (!on) return;
        Integer slot = SLOT.get(id);
        if (slot != null && p.getInventory().selected != slot) {
            p.getInventory().selected = slot;
            p.connection.send(new ClientboundSetCarriedItemPacket(slot));
            hint(p);
        }
        if (p.isSprinting()) p.setSprinting(false);
        if (p.isShiftKeyDown()) p.setShiftKeyDown(false);
    }

    /** Ends the hold at once (logout, dimension change): the modifier must not stay. */
    private static void release(ServerPlayer p) {
        STATE.remove(p.getUUID());
        hold(p, false);
    }

    // ---- the server stops every act of a held player (the client does the same first, so nothing jerks) ----

    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void onAttack(AttackEntityEvent e) {
        if (stop(e.getEntity(), CastLockMath.Act.ATTACK)) e.setCanceled(true);
    }

    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void onLeftBlock(PlayerInteractEvent.LeftClickBlock e) {
        if (stop(e.getEntity(), CastLockMath.Act.BREAK)) e.setCanceled(true);
    }

    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void onBreak(BlockEvent.BreakEvent e) {
        if (stop(e.getPlayer(), CastLockMath.Act.BREAK)) e.setCanceled(true);
    }

    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void onPlace(BlockEvent.EntityPlaceEvent e) {
        if (stop(e.getEntity(), CastLockMath.Act.PLACE)) e.setCanceled(true);
    }

    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void onRightBlock(PlayerInteractEvent.RightClickBlock e) {
        if (stop(e.getEntity(), CastLockMath.Act.USE_BLOCK)) {
            e.setCanceled(true);
            e.setCancellationResult(InteractionResult.FAIL);
        }
    }

    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void onRightItem(PlayerInteractEvent.RightClickItem e) {
        if (stop(e.getEntity(), CastLockMath.Act.USE_ITEM)) {
            e.setCanceled(true);
            e.setCancellationResult(InteractionResult.FAIL);
        }
    }

    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void onEntity(PlayerInteractEvent.EntityInteract e) {
        if (stop(e.getEntity(), CastLockMath.Act.USE_ENTITY)) {
            e.setCanceled(true);
            e.setCancellationResult(InteractionResult.FAIL);
        }
    }

    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void onEntityAt(PlayerInteractEvent.EntityInteractSpecific e) {
        if (stop(e.getEntity(), CastLockMath.Act.USE_ENTITY)) {
            e.setCanceled(true);
            e.setCancellationResult(InteractionResult.FAIL);
        }
    }

    /** Started using an item some other way (it was already in use when the window opened: eating, a bow) — stopped. Spell items go on. */
    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void onUseStart(LivingEntityUseItemEvent.Start e) {
        if (!held(e.getEntity()) || e.getItem().getItem() instanceof io.redspace.ironsspellbooks.item.CastingItem
                || io.redspace.ironsspellbooks.api.spells.ISpellContainer.isSpellContainer(e.getItem())
                || e.getItem().getItem() instanceof io.redspace.ironsspellbooks.item.Scroll) return;
        e.setCanceled(true);
    }

    /** Q: the item comes back to the hand (a cancelled toss would lose it: it already left the inventory). */
    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void onToss(ItemTossEvent e) {
        if (!stop(e.getPlayer(), CastLockMath.Act.DROP)) return;
        e.setCanceled(true);
        ServerPlayer p = (ServerPlayer) e.getPlayer();
        net.minecraft.world.item.ItemStack st = e.getEntity().getItem().copy();
        if (!p.getInventory().add(p.getInventory().selected, st) && !p.getInventory().add(st)) p.drop(st, false, false);
        p.containerMenu.broadcastChanges();
    }

    /** F (hands swap). */
    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void onSwap(net.minecraftforge.event.entity.living.LivingSwapItemsEvent.Hands e) {
        if (stop(e.getEntity(), CastLockMath.Act.SWAP_HANDS)) e.setCanceled(true);
    }

    /** A container opened anyway (a command, another mod): closed again; the spell goes on (Iron's cancel there is skipped by the mixin). */
    @SubscribeEvent(priority = EventPriority.LOWEST)
    public static void onContainer(PlayerContainerEvent.Open e) {
        if (e.getEntity() instanceof ServerPlayer p && e.getContainer() != p.inventoryMenu && stop(p, CastLockMath.Act.SCREEN)) p.closeContainer();
    }

    @SubscribeEvent
    public static void onDeath(LivingDeathEvent e) {
        interrupt(e.getEntity());
    }

    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void onLogout(PlayerEvent.PlayerLoggedOutEvent e) {
        if (e.getEntity() instanceof ServerPlayer p) release(p);
        STATE.remove(e.getEntity().getUUID());
        SENT.remove(e.getEntity().getUUID());
        LAST_TOLD.remove(e.getEntity().getUUID());
    }

    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void onDimension(PlayerEvent.PlayerChangedDimensionEvent e) {
        if (e.getEntity() instanceof ServerPlayer p) release(p);
    }

    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void onRespawn(PlayerEvent.PlayerRespawnEvent e) {
        if (e.getEntity() instanceof ServerPlayer p) release(p);
    }

    @SubscribeEvent
    public static void onStopping(ServerStoppingEvent e) {
        STATE.clear();
        SENT.clear();
        SLOT.clear();
        LAST_TOLD.clear();
    }
}
