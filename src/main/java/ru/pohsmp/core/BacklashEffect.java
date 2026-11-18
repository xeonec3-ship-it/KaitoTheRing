package ru.pohsmp.core;

import java.util.List;
import java.util.UUID;
import net.minecraft.world.effect.MobEffect;
import net.minecraft.world.effect.MobEffectCategory;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.ai.attributes.Attribute;
import net.minecraft.world.entity.ai.attributes.AttributeInstance;
import net.minecraft.world.entity.ai.attributes.AttributeMap;
import net.minecraft.world.entity.ai.attributes.AttributeModifier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.item.ItemStack;

/**
 * "Divine backlash": one effect for the whole price of a Divine scroll.
 * Slows for the first slowSeconds, weakens for the first weakSeconds (counted from the start of the effect),
 * blocks mana gain for the whole duration (see DivineEvents.onMana). Milk does not remove it.
 */
public class BacklashEffect extends MobEffect {
    private static final UUID SLOW_ID = UUID.fromString("5d2f7c1e-6a43-4f0e-9b1a-7e0c2d4b8a01");
    private static final UUID WEAK_ID = UUID.fromString("5d2f7c1e-6a43-4f0e-9b1a-7e0c2d4b8a02");

    public BacklashEffect() {
        super(MobEffectCategory.HARMFUL, Reg.DIVINE_COLOR);
    }

    @Override
    public boolean isDurationEffectTick(int duration, int amplifier) {
        return duration % 5 == 0;
    }

    @Override
    public void applyEffectTick(LivingEntity e, int amplifier) {
        var inst = e.getEffect(this);
        if (inst == null) return;
        int total = ServerConfig.BACKLASH_SECONDS.get() * 20;
        int elapsed = total - inst.getDuration();
        mod(e, Attributes.MOVEMENT_SPEED, SLOW_ID, "divine backlash slow", -0.30, AttributeModifier.Operation.MULTIPLY_TOTAL,
                elapsed < ServerConfig.SLOW_SECONDS.get() * 20);
        mod(e, Attributes.ATTACK_DAMAGE, WEAK_ID, "divine backlash weak", -8.0, AttributeModifier.Operation.ADDITION,
                elapsed < ServerConfig.WEAK_SECONDS.get() * 20);
    }

    private static void mod(LivingEntity e, Attribute attr, UUID id, String name, double amount, AttributeModifier.Operation op, boolean on) {
        AttributeInstance ai = e.getAttribute(attr);
        if (ai == null) return;
        boolean has = ai.getModifier(id) != null;
        if (on && !has) ai.addTransientModifier(new AttributeModifier(id, name, amount, op));
        else if (!on && has) ai.removeModifier(id);
    }

    @Override
    public void removeAttributeModifiers(LivingEntity e, AttributeMap map, int amplifier) {
        super.removeAttributeModifiers(e, map, amplifier);
        AttributeInstance speed = e.getAttribute(Attributes.MOVEMENT_SPEED);
        if (speed != null) speed.removeModifier(SLOW_ID);
        AttributeInstance dmg = e.getAttribute(Attributes.ATTACK_DAMAGE);
        if (dmg != null) dmg.removeModifier(WEAK_ID);
    }

    @Override
    public List<ItemStack> getCurativeItems() {
        return List.of();
    }
}
