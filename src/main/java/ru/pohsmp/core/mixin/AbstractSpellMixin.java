package ru.pohsmp.core.mixin;

import io.redspace.ironsspellbooks.api.spells.AbstractSpell;
import net.minecraft.world.entity.LivingEntity;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
import ru.pohsmp.core.spell.FixedCastSpell;
import ru.pohsmp.core.spell.SpellBans;

/**
 * Owner 20.11.
 * <ul>
 *   <li>Spells marked {@link FixedCastSpell} (all with a camera cutscene): the cast time is fixed, cast time reduction does not shorten it.
 *       Covers every subclass that does not override getEffectiveCastTime or calls super (PohSpell checks the marker itself for Silent spells).</li>
 *   <li>allowCrafting: our spells of Higher and above and all Silent ones are never crafted, whatever the Iron's spell config says
 *       (overrides that return true in subclasses are fixed in those classes: SilentStaffSpell).</li>
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
}
