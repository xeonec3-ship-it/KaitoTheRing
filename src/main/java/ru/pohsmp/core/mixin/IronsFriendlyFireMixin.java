package ru.pohsmp.core.mixin;

import io.redspace.ironsspellbooks.damage.DamageSources;
import net.minecraft.world.entity.Entity;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
import ru.pohsmp.core.spell.CoAuthors;

/**
 * Owner 21.11 (4): the two mages of a joint cast are friends for Iron's — its spells, zones and projectiles (an Iron's spell in the
 * [joint_cast] list) skip the partner as they skip the caster's team, and its ally effects reach him. Works on attributed owners
 * (a projectile or zone of the caster counts as the caster).
 */
@Mixin(value = DamageSources.class, remap = false)
public abstract class IronsFriendlyFireMixin {
    @Inject(method = "isFriendlyFireBetween", at = @At("HEAD"), cancellable = true, remap = false, require = 0)
    private static void pohsmp$coAuthors(Entity a, Entity b, CallbackInfoReturnable<Boolean> cir) {
        if (a == null || b == null) return;
        if (CoAuthors.linked(CoAuthors.playerOf(a), CoAuthors.playerOf(b))) cir.setReturnValue(true);
    }
}
