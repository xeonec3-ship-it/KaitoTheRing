package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.events.SpellOnCastEvent;
import io.redspace.ironsspellbooks.api.events.SpellPreCastEvent;
import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.registry.SpellRegistry;
import io.redspace.ironsspellbooks.api.spells.AbstractSpell;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.util.Utils;
import io.redspace.ironsspellbooks.item.Scroll;
import java.lang.reflect.Field;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.network.PacketDistributor;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.ServerConfig;
import ru.pohsmp.core.net.Net;

/**
 * Joint cast (T15). Two mages near each other (radius) cast the same spell from scrolls, the second one starts within the window
 * after the first: the casts merge. Both end together after castTimeMult of the first mage's cast time; the spell takes effect once
 * (whoever finishes first, normally the first mage), the other cast is cancelled and its scroll is spent as well (a charged scroll
 * loses one charge, see Charges). Sigils of both mages get a double outline (HFx.JOINT on the client).
 * Only spells listed in the server config [joint_cast] spells and only long casts (a cast bar) take part.
 */
public final class JointCast {
    private JointCast() {}

    private static final class Caster {
        ServerPlayer p;
        String spell;
        long start;
        int duration;
        Caster partner;
        int fxKey;
        /** Owner 21.11 (4): both mages own the spell (CoAuthors), shared by the pair. */
        CoAuthorMath.Link link;
        boolean toldHostile;
    }

    private static final Map<UUID, Long> PENDING = new HashMap<>();
    private static final Map<UUID, Caster> CASTERS = new HashMap<>();
    /** Set while the joint cast finishes, so the cancel of the second mage is not taken for a break-up. */
    private static boolean finishing;

    public static boolean isJointSpell(String spellId) {
        return spellId != null && ServerConfig.JOINT_SPELLS.get().contains(spellId);
    }

    /** True while the player is in a merged cast (for scripts and tests). */
    public static boolean isJoint(ServerPlayer p) {
        Caster c = CASTERS.get(p.getUUID());
        return c != null && c.partner != null;
    }

    @SubscribeEvent(priority = EventPriority.LOWEST)
    public static void onPreCast(SpellPreCastEvent e) {
        if (e.isCanceled() || e.getCastSource() != CastSource.SCROLL || !(e.getEntity() instanceof ServerPlayer sp)) return;
        if (!isJointSpell(e.getSpellId())) return;
        PENDING.put(sp.getUUID(), sp.level().getGameTime());
    }

    @SubscribeEvent
    public static void onServerTick(TickEvent.ServerTickEvent e) {
        tick(e.getServer());
    }

    @SubscribeEvent
    public static void onStopping(ServerStoppingEvent e) {
        PENDING.clear();
        CASTERS.clear();
    }

    static void tick(MinecraftServer server) {
        if (!CASTERS.isEmpty()) {
            for (Caster c : new ArrayList<>(CASTERS.values())) {
                if (stillCasting(c)) continue;
                CASTERS.remove(c.p.getUUID());
                if (c.partner != null) breakUp(c);
            }
        }
        if (PENDING.isEmpty()) return;
        for (Map.Entry<UUID, Long> en : PENDING.entrySet()) {
            ServerPlayer p = server.getPlayerList().getPlayer(en.getKey());
            if (p == null) continue;
            MagicData md = MagicData.getPlayerMagicData(p);
            if (!md.isCasting() || md.getCastSource() != CastSource.SCROLL || md.getCastType() != CastType.LONG) continue;
            String spell = md.getCastingSpellId();
            if (!isJointSpell(spell)) continue;
            Caster c = new Caster();
            c.p = p;
            c.spell = spell;
            c.start = en.getValue();
            c.duration = md.getCastDuration();
            Caster old = CASTERS.put(p.getUUID(), c);
            if (old != null && old.partner != null) breakUp(old);
            Caster lead = findLead(c);
            if (lead != null) merge(lead, c);
        }
        PENDING.clear();
    }

    private static boolean stillCasting(Caster c) {
        if (c.p.isRemoved() || !c.p.isAlive()) return false;
        MagicData md = MagicData.getPlayerMagicData(c.p);
        return md.isCasting() && c.spell.equals(md.getCastingSpellId());
    }

    /** The earliest single mage of the same spell nearby who started no more than the window before. */
    private static Caster findLead(Caster c) {
        double r = ServerConfig.JOINT_RADIUS.get();
        long window = Math.round(ServerConfig.JOINT_WINDOW.get() * 20);
        Caster best = null;
        for (Caster o : CASTERS.values()) {
            if (o == c || o.partner != null || !o.spell.equals(c.spell) || o.p.level() != c.p.level()) continue;
            if (c.start < o.start || c.start - o.start > window) continue;
            if (o.p.distanceToSqr(c.p) > r * r || !stillCasting(o)) continue;
            if (CoAuthors.hostile(o.p, c.p)) {   // owner 21.11 (5): they hurt each other recently - each casts alone
                if (!c.toldHostile) {
                    CoAuthors.tellHostile(o.p);
                    CoAuthors.tellHostile(c.p);
                    c.toldHostile = true;
                }
                continue;
            }
            if (best == null || o.start < best.start) best = o;
        }
        return best;
    }

    private static void merge(Caster lead, Caster follow) {
        long now = lead.p.level().getGameTime();
        int total = Math.max(1, (int) Math.round(lead.duration * ServerConfig.JOINT_MULT.get()));
        int leadLeft = (int) Math.max(1, lead.start + total - now);
        // the second mage ends one tick later: the first one's cast takes effect, then the second is folded into it
        int followLeft = leadLeft + 1;
        setCastTime(lead.p, (int) (now - lead.start) + leadLeft, leadLeft);
        setCastTime(follow.p, (int) (now - follow.start) + followLeft, followLeft);
        lead.partner = follow;
        follow.partner = lead;
        lead.link = follow.link = CoAuthors.link(lead.p, follow.p, lead.spell);
        AbstractSpell sp = SpellRegistry.getSpell(lead.spell);
        Component name = sp.getDisplayName(lead.p);
        for (Caster c : List.of(lead, follow)) {
            c.p.displayClientMessage(Component.translatable("ui.pohsmp_core.joint_cast", name).withStyle(s -> s.withColor(0xE8C26A)), true);
            c.fxKey = HigherSpell.key();
        }
        ServerLevel sl = (ServerLevel) lead.p.level();
        int school = schoolIndex(sp), color = schoolColor(sp);
        for (Caster c : List.of(lead, follow)) {
            int left = c == lead ? leadLeft : followLeft;
            Net.sendNear(sl, c.p.getX(), c.p.getY(), c.p.getZ(), c.partner.p.getX(), c.partner.p.getY(), c.partner.p.getZ(),
                    new Net.HFx(Net.HFx.JOINT, c.fxKey, c.p.getId(), c.partner.p.getId(), left, c.p.getX(), c.p.getY(), c.p.getZ(), 2.2,
                            (school << 24) | (color & 0xFFFFFF)));
        }
        sl.playSound(null, follow.p.getX(), follow.p.getY(), follow.p.getZ(), SoundEvents.AMETHYST_BLOCK_RESONATE, SoundSource.PLAYERS, 1.5f, 0.7f);
        PohCore.LOG.info("[pohsmp_core] joint cast {}: {} + {}, {} -> {} ticks", lead.spell, lead.p.getGameProfile().getName(),
                follow.p.getGameProfile().getName(), lead.duration, total);
    }

    /** The first of the pair whose cast takes effect: the other cast is cancelled, its scroll spent. */
    @SubscribeEvent
    public static void onCast(SpellOnCastEvent e) {
        if (finishing || e.getCastSource() != CastSource.SCROLL || !(e.getEntity() instanceof ServerPlayer sp)) return;
        Caster c = CASTERS.get(sp.getUUID());
        if (c == null || c.partner == null || !c.spell.equals(e.getSpellId())) return;
        Caster o = c.partner;
        CASTERS.remove(c.p.getUUID());
        CASTERS.remove(o.p.getUUID());
        c.partner = null;
        o.partner = null;
        CoAuthors.fired(c.link, c.p);   // the spell took effect: both stay its owners while its fields live
        c.link = o.link = null;
        stopFx(c);
        stopFx(o);
        if (!stillCasting(o)) return;
        finishing = true;
        try {
            Scroll.attemptRemoveScrollAfterCast(o.p);
            Utils.serverSideCancelCast(o.p, false);
        } finally {
            finishing = false;
        }
        o.p.displayClientMessage(Component.translatable("ui.pohsmp_core.joint_cast.done").withStyle(s -> s.withColor(0xE8C26A)), true);
    }

    /** One of the pair stopped (cancelled, died, left): the other goes on alone with the time it already has. */
    private static void breakUp(Caster c) {
        Caster o = c.partner;
        c.partner = null;
        CoAuthors.unlink(c.link);   // broke up before the spell took effect: each casts his own again
        c.link = null;
        stopFx(c);
        if (o == null) return;
        o.partner = null;
        o.link = null;
        stopFx(o);
    }

    private static void stopFx(Caster c) {
        if (c.fxKey == 0 || !(c.p.level() instanceof ServerLevel sl)) return;
        HigherSpell.stop(sl, c.p.getX(), c.p.getY(), c.p.getZ(), c.fxKey);
        c.fxKey = 0;
    }

    // ---- cast time ----

    private static Field DURATION, REMAINING;

    /** Iron's has no setter for the cast time: set both fields and tell the caster's client (cast bar). */
    static void setCastTime(ServerPlayer p, int duration, int remaining) {
        setCastTime(MagicData.getPlayerMagicData(p), duration, remaining);
        Net.CH.send(PacketDistributor.PLAYER.with(() -> p), new Net.CastTime(duration, remaining));
    }

    public static void setCastTime(MagicData md, int duration, int remaining) {
        try {
            if (DURATION == null) {
                DURATION = MagicData.class.getDeclaredField("castDuration");
                REMAINING = MagicData.class.getDeclaredField("castDurationRemaining");
                DURATION.setAccessible(true);
                REMAINING.setAccessible(true);
            }
            DURATION.setInt(md, Math.max(1, duration));
            REMAINING.setInt(md, Math.max(1, remaining));
        } catch (ReflectiveOperationException ex) {
            PohCore.LOG.error("[pohsmp_core] joint cast: cannot change Iron's cast time", ex);
        }
    }

    // ---- look ----

    /** Index into the drawn school sigils (see PohSpell), Higher/Divine/Forbidden and unknown schools fall back to evocation. */
    private static int schoolIndex(AbstractSpell sp) {
        String s = sp.getSchoolType() == null ? "" : sp.getSchoolType().getId().getPath();
        int i = PohSpell.sigilIndex(s);
        return i < 0 ? PohSpell.sigilIndex("evocation") : i;
    }

    private static int schoolColor(AbstractSpell sp) {
        String s = sp.getSchoolType() == null ? "" : sp.getSchoolType().getId().getPath();
        return switch (s) {
            case "higher" -> ru.pohsmp.core.Reg.HIGHER_COLOR;
            case "divine" -> ru.pohsmp.core.Reg.DIVINE_COLOR;
            case "forbidden" -> ru.pohsmp.core.Reg.FORBIDDEN_COLOR;
            default -> {
                int i = PohSpell.sigilIndex(s);
                yield i < 0 ? 0xE8C26A : PohSpell.sigilColor(i);
            }
        };
    }
}
