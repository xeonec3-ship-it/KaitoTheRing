package ru.pohsmp.core.silent;

import io.redspace.ironsspellbooks.api.spells.AbstractSpell;
import io.redspace.ironsspellbooks.api.util.Utils;
import io.redspace.ironsspellbooks.api.registry.AttributeRegistry;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.ServerConfig;

/**
 * Silent Witch outfit (T19): which pieces an entity wears, and who is "nameless".
 * <p>
 * Name hiding has two levels, kept by the server per player and synced to every client ({@link ru.pohsmp.core.net.Net.SilentSync}),
 * so that clients know it even for players whose entity they do not have (tracked minimap markers):
 * {@link #NAME_TAG} - the hood is on, the name above the head is hidden (effect 6);
 * {@link #NAMELESS} - the full set is on, the player is also hidden on minimaps, world maps and look-at HUDs (effect 11).
 */
public final class SilentWitch {
    private SilentWitch() {}

    public static final int NAME_TAG = 1, NAMELESS = 2;
    /** Server: flags of online players. */
    static final Map<UUID, Integer> SERVER = new HashMap<>();
    /** Client: the last map the server sent. */
    private static volatile Map<UUID, Integer> client = Map.of();

    public static boolean piece(LivingEntity e, EquipmentSlot slot) {
        return e != null && e.getItemBySlot(slot).getItem() instanceof SilentWitchArmor a && a.getEquipmentSlot() == slot;
    }

    public static boolean hood(LivingEntity e) {
        return piece(e, EquipmentSlot.HEAD);
    }

    public static boolean robe(LivingEntity e) {
        return piece(e, EquipmentSlot.CHEST);
    }

    public static boolean skirt(LivingEntity e) {
        return piece(e, EquipmentSlot.LEGS);
    }

    public static boolean fullSet(LivingEntity e) {
        return hood(e) && robe(e) && skirt(e);
    }

    /** Flags for an entity from what it wears now (server side source of truth; the client uses it for loaded players too). */
    public static int flagsOf(LivingEntity e) {
        if (!(e instanceof Player)) return 0;
        int f = 0;
        if (hood(e)) f |= NAME_TAG;
        if (fullSet(e)) f |= NAMELESS;
        return f;
    }

    public static void setClientFlags(Map<UUID, Integer> m) {
        client = Map.copyOf(m);
    }

    public static void clearClient() {
        client = Map.of();
    }

    /** Flags of a player by id on the given side (synced map; for loaded players also their own equipment). */
    public static int flags(UUID id, boolean clientSide) {
        Integer f = clientSide ? client.get(id) : SERVER.get(id);
        return f == null ? 0 : f;
    }

    public static int flags(Entity e) {
        if (!(e instanceof Player p)) return 0;
        return flags(p.getUUID(), p.level().isClientSide) | flagsOf(p);
    }

    /** The name above this entity's head must not be drawn (hood or full set). */
    public static boolean nameTagHidden(Entity e) {
        return (flags(e) & (NAME_TAG | NAMELESS)) != 0;
    }

    /** Hidden on minimaps, world maps and look-at HUDs (full set). */
    public static boolean nameless(Entity e) {
        return (flags(e) & NAMELESS) != 0;
    }

    public static boolean namelessClient(UUID id) {
        return (flags(id, true) & NAMELESS) != 0;
    }

    public static boolean namelessServer(UUID id) {
        return (flags(id, false) & NAMELESS) != 0;
    }

    /** Effect 1: chants (Replica, Explosion) are not written to chat while the robe is on. */
    public static boolean muted(LivingEntity caster) {
        return robe(caster) && ServerConfig.get(ServerConfig.SW_MUTE_CHANT);
    }

    /**
     * Cast time of a Silent-school spell: Iron's formula with the Silent bonus added to cast_time_reduction
     * (the robe: 15% for all spells + 10% more for Silent ones = 25%). Silent spells override getEffectiveCastTime with this.
     */
    public static int castTime(AbstractSpell spell, int spellLevel, LivingEntity e) {
        int base = spell.getCastTime(spellLevel);
        if (e == null) return base;
        double ctr = e.getAttributeValue(AttributeRegistry.CAST_TIME_REDUCTION.get());
        double extra = e.getAttributes().hasAttribute(Reg.SILENT_CAST.get()) ? e.getAttributeValue(Reg.SILENT_CAST.get()) - 1.0 : 0;
        double mult = spell.getCastType() == io.redspace.ironsspellbooks.api.spells.CastType.CONTINUOUS
                ? ctr + extra : 2.0 - Utils.softCapFormula(ctr + extra);
        return Math.round((float) (base * mult));
    }

    /**
     * Effect 9 + T20 "Black Flame of Worgan": in the full set the dragon shadow is Nero himself - the cat jumps off and dissolves
     * (armor animation nero_dragon; the shadow should rise 0.55 s after this call) and comes back after {@code ticks} (nero_return).
     * Returns false (nothing sent) outside the full set. ticks 0 brings the cat back at once (cancelled cast).
     */
    public static boolean neroDragon(LivingEntity wearer, int ticks) {
        if (!fullSet(wearer) || wearer.level().isClientSide) return false;
        ru.pohsmp.core.net.Net.CH.send(net.minecraftforge.network.PacketDistributor.TRACKING_ENTITY_AND_SELF.with(() -> wearer),
                new ru.pohsmp.core.net.Net.NeroMsg(wearer.getId(), Math.max(0, ticks)));
        return true;
    }
}
