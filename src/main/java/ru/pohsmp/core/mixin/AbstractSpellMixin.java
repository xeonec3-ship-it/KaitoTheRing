package ru.pohsmp.core.mixin;

import io.redspace.ironsspellbooks.api.spells.AbstractSpell;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
import ru.pohsmp.core.spell.CastLock;
import ru.pohsmp.core.spell.FixedCastSpell;
import ru.pohsmp.core.spell.SpellBans;

/**
 * Owner 20.11.
 * <ul>
 *   <li>Spells marked {@link FixedCastSpell} (all with a camera cutscene): the cast time is fixed, cast time reduction does not shorten it.
 *       Covers every subclass that does not override getEffectiveCastTime or calls super (PohSpell checks the marker itself for Silent spells).</li>
 *   <li>allowCrafting: our spells of Higher and above and all Silent ones are never crafted, whatever the Iron's spell config says
 *       (overrides that return true in subclasses are fixed in those classes: SilentStaffSpell).</li>
 *   <li>Owner 21.11, {@link CastLock}: attemptInitiateCast is refused while the player's animated spell runs (before Iron's would cancel
 *       the running cast), and an animated cast that did start opens the window.</li>
 * </ul>
 * Iron's own method names (not obfuscated): remap = false works both in dev and in the production jar.
 */
@Mixin(value = AbstractSpell.class, remap = false)
public abstract class AbstractSpellMixin {
    @Inject(method = "getEffectiveCastTime", at = @At("HEAD"), cancellable = true, remap = false)
    private void pohsmp$fixedCast(int spellLevel, LivingEntity entity, CallbackInfoReturnable<Integer> cir) {
        if ((Object) this instanceof FixedCastSpell) cir.setReturnValue(((AbstractSpell) (Object) this).getCastTime(spellLevel));
    }

    @Inject(method = "allowCrafting", at = @At("HEAD"), cancellable = true, remap = false)
    private void pohsmp$noCraft(CallbackInfoReturnable<Boolean> cir) {
        if (SpellBans.craftBanned((AbstractSpell) (Object) this)) cir.setReturnValue(false);
    }

    @Inject(method = "attemptInitiateCast", at = @At("HEAD"), cancellable = true, remap = false)
    private void pohsmp$castLock(ItemStack stack, int spellLevel, Level level, Player player, CastSource source, boolean triggerCooldown,
                                 String castingEquipmentSlot, CallbackInfoReturnable<Boolean> cir) {
        if (!level.isClientSide && player instanceof ServerPlayer sp && CastLock.refuse(sp, (AbstractSpell) (Object) this)) cir.setReturnValue(false);
    }

    @Inject(method = "attemptInitiateCast", at = @At("RETURN"), remap = false)
    private void pohsmp$castLockBegin(ItemStack stack, int spellLevel, Level level, Player player, CastSource source, boolean triggerCooldown,
                                      String castingEquipmentSlot, CallbackInfoReturnable<Boolean> cir) {
        if (cir.getReturnValueZ() && !level.isClientSide && player instanceof ServerPlayer sp) CastLock.begin(sp, (AbstractSpell) (Object) this);
    }
}
