package ru.pohsmp.core.trophy;

import com.google.common.collect.ImmutableMultimap;
import io.redspace.ironsspellbooks.api.registry.AttributeRegistry;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.UUID;
import java.util.function.Supplier;
import net.minecraft.world.entity.ai.attributes.Attribute;
import net.minecraft.world.entity.ai.attributes.AttributeModifier;
import net.minecraft.world.entity.ai.attributes.AttributeModifier.Operation;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.item.ArmorItem;
import ru.pohsmp.core.Reg;

/**
 * T35: the four full sets of the cell heads (owner 21.11) and the two separate wearables of the Cult Heads. Defense, toughness and
 * knockback resistance go to {@link TrophyMaterial}; the Iron's attributes of every piece are here (draft, balance_bosses.md
 * «Броня боссов (T35)»): values per slot {helmet, chestplate, leggings, boots}; ADDITION on Iron's attributes (base 1 = +0%).
 */
public enum TrophySet {
    JEALOUS("jealous", 0x9A1E4A, new int[] {3, 8, 6, 3}, 3.0f, 0.1f, List.of(
            mod(AttributeRegistry.BLOOD_SPELL_POWER, "blood power", Operation.ADDITION, 0.08, 0.08, 0.08, 0.08),
            mod(AttributeRegistry.MAX_MANA, "mana", Operation.ADDITION, 100, 150, 125, 75),
            mod(AttributeRegistry.MANA_REGEN, "mana regen", Operation.ADDITION, 0.05, 0.10, 0.05, 0.05))),
    SMITH("smith", 0x3FE0D0, new int[] {4, 9, 7, 4}, 4.0f, 0.15f, List.of(
            mod(AttributeRegistry.MAX_MANA, "mana", Operation.ADDITION, 50, 50, 50, 50),
            mod(AttributeRegistry.SPELL_RESIST, "spell resist", Operation.ADDITION, 0.02, 0.04, 0.03, 0.01))),
    WARLORD("warlord", 0xD4A017, new int[] {3, 9, 7, 3}, 3.5f, 0.1f, List.of(
            mod(() -> Attributes.MAX_HEALTH, "health", Operation.ADDITION, 2, 4, 3, 1),
            mod(AttributeRegistry.MAX_MANA, "mana", Operation.ADDITION, 50, 50, 50, 50))),
    TRAITOR("traitor", 0x6B4FA0, new int[] {3, 8, 6, 3}, 3.0f, 0.1f, List.of(
            mod(() -> Attributes.MOVEMENT_SPEED, "speed", Operation.MULTIPLY_BASE, 0.03, 0.03, 0.03, 0.03),
            mod(AttributeRegistry.ELDRITCH_SPELL_POWER, "eldritch power", Operation.ADDITION, 0.07, 0.07, 0.07, 0.07),
            mod(Reg.ILLUSION_POWER, "illusion power", Operation.ADDITION, 0.07, 0.07, 0.07, 0.07),
            mod(AttributeRegistry.MAX_MANA, "mana", Operation.ADDITION, 75, 75, 75, 75),
            mod(AttributeRegistry.COOLDOWN_REDUCTION, "cooldown", Operation.ADDITION, 0.025, 0.025, 0.025, 0.025)));

    public final String id;
    public final int color;
    final int[] defense;
    final float toughness, knockback;
    final List<Mod> mods;
    public final TrophyMaterial material;

    TrophySet(String id, int color, int[] defense, float toughness, float knockback, List<Mod> mods) {
        this.id = id;
        this.color = color;
        this.defense = defense;
        this.toughness = toughness;
        this.knockback = knockback;
        this.mods = mods;
        this.material = new TrophyMaterial(this);
    }

    public static TrophySet byId(String id) {
        for (TrophySet s : values()) if (s.id.equals(id)) return s;
        return null;
    }

    /** The piece's item id: jealous_helmet, smith_chestplate... */
    public String item(ArmorItem.Type type) {
        return id + "_" + type.getName();
    }

    /** {helmet, chestplate, leggings, boots} -> 0..3 */
    static int index(ArmorItem.Type t) {
        return switch (t) {
            case HELMET -> 0;
            case CHESTPLATE -> 1;
            case LEGGINGS -> 2;
            case BOOTS -> 3;
        };
    }

    void addModifiers(ImmutableMultimap.Builder<Attribute, AttributeModifier> b, ArmorItem.Type type) {
        int i = index(type);
        for (Mod m : mods) m.put(b, id + ":" + type.getName(), i);
    }

    /** One attribute of a set: its value in each of the four slots. */
    public record Mod(Supplier<Attribute> attr, String name, Operation op, double[] perSlot) {
        void put(ImmutableMultimap.Builder<Attribute, AttributeModifier> b, String where, int slot) {
            Attribute a = attr.get();
            double v = perSlot[Math.min(slot, perSlot.length - 1)];
            if (a == null || v == 0) return;
            b.put(a, new AttributeModifier(uuid(where + ":" + name), "POH trophy " + name, v, op));
        }
    }

    static Mod mod(Supplier<? extends Attribute> a, String name, Operation op, double... perSlot) {
        return new Mod(a::get, name, op, perSlot);
    }

    /** Stable modifier ids (the same on every load, different per set, slot and attribute). */
    static UUID uuid(String key) {
        return UUID.nameUUIDFromBytes(("pohsmp_core:trophy:" + key).getBytes(StandardCharsets.UTF_8));
    }
}
