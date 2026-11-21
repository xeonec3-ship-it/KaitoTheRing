package ru.pohsmp.core.client;

import io.redspace.ironsspellbooks.player.KeyMappings;
import net.minecraft.client.KeyMapping;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.ChatScreen;
import net.minecraft.client.gui.screens.DeathScreen;
import net.minecraft.client.gui.screens.PauseScreen;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.client.player.Input;
import net.minecraft.client.resources.sounds.SimpleSoundInstance;
import net.minecraft.network.chat.Component;
import net.minecraft.sounds.SoundEvents;
import net.minecraftforge.client.event.ClientPlayerNetworkEvent;
import net.minecraftforge.client.event.ComputeFovModifierEvent;
import net.minecraftforge.client.event.InputEvent;
import net.minecraftforge.client.event.MovementInputUpdateEvent;
import net.minecraftforge.client.event.ScreenEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.spell.CastLock;
import ru.pohsmp.core.spell.CastLockMath;
import ru.pohsmp.core.spell.CastLockMath.Act;

/**
 * Owner 21.11 (2), the client half of {@link CastLock}: while the server says the local player is held by the window of an animated
 * spell, his input is dropped here first so nothing jerks (the server cancels the same acts anyway): attack and use (also Epic Fight,
 * whose skills are refused in mixin/EpicFightSkillMixin), the hotbar and the spell wheel / spell bar (Iron's key handling sleeps,
 * mixin/IronsClientInputMixin), Q, F, the inventory and other screens (the pause menu and the chat stay), walking, jumping, sprint,
 * sneaking. The camera stays free. «Безмолвные врата» (GateOrder, HIGHEST) still turns the caster's left click into the command.
 */
public final class CastLockClient {
    private CastLockClient() {}

    private static boolean was;
    private static int slot = -1;
    private static long lastHint = Long.MIN_VALUE;
    private static boolean ironsDown;

    public static boolean locked() {
        Minecraft mc = Minecraft.getInstance();
        return CastLock.clientLocked && mc.player != null && mc.level != null && mc.player.isAlive();
    }

    static void hint() {
        Minecraft mc = Minecraft.getInstance();
        if (mc.level == null) return;
        long now = mc.level.getGameTime();
        if (!CastLockMath.hintDue(lastHint, now)) return;
        lastHint = now;
        mc.gui.setOverlayMessage(Component.translatable("message.pohsmp_core.cast_busy"), false);
        mc.getSoundManager().play(SimpleSoundInstance.forUI(SoundEvents.NOTE_BLOCK_BASS.value(), 0.6f, 0.35f));
    }

    private static boolean eat(KeyMapping k) {
        boolean any = false;
        while (k.consumeClick()) any = true;
        return any;
    }

    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void onTick(TickEvent.ClientTickEvent e) {
        if (e.phase != TickEvent.Phase.START) return;
        Minecraft mc = Minecraft.getInstance();
        boolean on = locked();
        if (on && !was) slot = mc.player.getInventory().selected;
        was = on;
        if (!on) {
            ironsDown = false;
            return;
        }
        var o = mc.options;
        boolean tried = false;
        for (KeyMapping k : o.keyHotbarSlots) tried |= eat(k);
        tried |= eat(o.keySwapOffhand) | eat(o.keyDrop) | eat(o.keyInventory) | eat(o.keyAdvancements) | eat(o.keySocialInteractions);
        // Iron's keys: its handler sleeps (IronsClientInputMixin), here only the hint on a fresh press
        boolean down = KeyMappings.SPELLBOOK_CAST_ACTIVE_KEYMAP.isDown() || KeyMappings.SPELL_WHEEL_KEYMAP.isDown() || KeyMappings.SPELL_WHEEL_TOGGLE_KEYMAP.isDown();
        for (KeyMapping k : KeyMappings.QUICK_CAST_MAPPINGS) down |= k.isDown();
        if (down && !ironsDown) tried = true;
        ironsDown = down;
        if (slot >= 0 && mc.player.getInventory().selected != slot) {
            mc.player.getInventory().selected = slot;
            tried = true;
        }
        if (mc.player.isSprinting()) mc.player.setSprinting(false);
        if (tried) hint();
    }

    /** Attack, use, pick block (vanilla and Epic Fight both come here). GateOrder's command (HIGHEST) is taken before. */
    @SubscribeEvent(priority = EventPriority.HIGH)
    public static void onClick(InputEvent.InteractionKeyMappingTriggered e) {
        if (!locked()) return;
        e.setCanceled(true);
        e.setSwingHand(false);
        if (!e.isPickBlock()) hint();
    }

    @SubscribeEvent(priority = EventPriority.LOWEST)
    public static void onMove(MovementInputUpdateEvent e) {
        if (!locked() || !CastLockMath.blocks(true, Act.MOVE)) return;
        Input in = e.getInput();
        in.forwardImpulse = 0;
        in.leftImpulse = 0;
        in.up = in.down = in.left = in.right = false;
        in.jumping = false;
        in.shiftKeyDown = false;
    }

    /** The hotbar scroll and Iron's spell bar scroll. */
    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void onScroll(InputEvent.MouseScrollingEvent e) {
        if (!locked()) return;
        e.setCanceled(true);
        hint();
    }

    /** The pause menu, the chat, the death screen and screens opened from them stay; the rest is not opened (Iron's would cancel the cast). */
    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void onScreen(ScreenEvent.Opening e) {
        if (!locked() || allowed(e.getCurrentScreen(), e.getNewScreen())) return;
        e.setCanceled(true);
        hint();
    }

    static boolean allowed(Screen current, Screen next) {
        if (current != null) return true;   // options, key binds etc. from the pause menu; closing a screen into another one
        if (next instanceof PauseScreen || next instanceof ChatScreen || next instanceof DeathScreen) return true;
        return next != null && next.getClass().getName().startsWith("ru.pohsmp.core.");
    }

    /** The server takes the walking speed away (falling and knockback stay): no zoom from it. */
    @SubscribeEvent
    public static void onFov(ComputeFovModifierEvent e) {
        if (locked()) e.setNewFovModifier(1.0f);
    }

    @SubscribeEvent
    public static void onLogout(ClientPlayerNetworkEvent.LoggingOut e) {
        CastLock.clientLocked = false;
        was = false;
        slot = -1;
    }
}
