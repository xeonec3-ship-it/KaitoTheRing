package ru.pohsmp.core.spell.silent;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.spells.SpellRarity;
import java.util.List;
import java.util.Optional;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.SilentWitchStaff;
import ru.pohsmp.core.spell.PohSpell;

/**
 * Spell of the Silent Witch staff (T18): "Silent" school, "Unknown" tier, one level, no scrolls (no crafting, no loot),
 * cast only with the staff in the main hand. Silent magic: no cast voice, only a short crystal chime.
 * <p>
 * Subclasses that are not made yet keep {@link #ready()} false: the slot is in the staff wheel, but casting only says
 * "not ready yet" (T03 "Gate", T20 the other four replace the stub bodies with the real spells).
 */
public abstract class SilentStaffSpell extends PohSpell {
    protected SilentStaffSpell(String path, double cooldownSec, int castTicks, int mana) {
        super(path, Reg.SILENT_ID, SpellRarity.LEGENDARY, 1, cooldownSec, castTicks, mana, 0);
    }

    /** False while the spell is a stub. */
    protected boolean ready() {
        return false;
    }

    @Override public CastType getCastType() { return castTime > 0 ? CastType.LONG : CastType.INSTANT; }
    @Override public boolean allowCrafting() { return false; }
    @Override public boolean allowLooting() { return false; }
    @Override public Optional<SoundEvent> getCastStartSound() { return Optional.empty(); }
    @Override public Optional<SoundEvent> getCastFinishSound() { return Optional.of(SoundEvents.AMETHYST_BLOCK_CHIME); }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return ready() ? List.of() : List.of(Component.translatable("ui.pohsmp_core.silent_staff.stub"));
    }

    /** Extra check of a finished spell (e.g. the Gate needs the full outfit); key of "ui.pohsmp_core.&lt;spell&gt;.&lt;key&gt;" or null. */
    protected String whyNot(Level level, LivingEntity entity) {
        return null;
    }

    @Override
    public boolean checkPreCastConditions(Level level, int spellLevel, LivingEntity entity, MagicData md) {
        MutableComponent why = null;
        if (!(entity.getMainHandItem().getItem() instanceof SilentWitchStaff)) why = Component.translatable("ui.pohsmp_core.silent_staff.need_staff");
        else if (!ready()) why = Component.translatable("ui.pohsmp_core.silent_staff.not_ready");
        else {
            String k = whyNot(level, entity);
            if (k != null) why = ui(k);
        }
        if (why != null) {
            if (entity instanceof Player p) p.displayClientMessage(why.withStyle(s -> s.withColor(Reg.SILENT_COLOR)), true);
            return false;
        }
        return super.checkPreCastConditions(level, spellLevel, entity, md);
    }
}
