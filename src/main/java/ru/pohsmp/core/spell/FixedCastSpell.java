package ru.pohsmp.core.spell;

/**
 * Marker: the spell's cast time is fixed (owner 20.11: "all magic with a camera cutscene has a fixed duration").
 * Iron's cast time reduction (attribute, enchantments, robes, the Silent Witch robe) does not change it:
 * {@code getEffectiveCastTime} returns {@code getCastTime(level)} (see mixin/AbstractSpellMixin and PohSpell).
 * Every spell that calls {@code Cutscene.start} must implement it (checked by FixedCastGuardTest).
 * New spell with a cutscene: add {@code implements FixedCastSpell} to its class - that is all.
 */
public interface FixedCastSpell {
}
