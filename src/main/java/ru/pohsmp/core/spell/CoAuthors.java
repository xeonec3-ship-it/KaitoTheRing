package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.damage.SpellDamageSource;
import io.redspace.ironsspellbooks.entity.mobs.IMagicSummon;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.StringTag;
import net.minecraft.nbt.Tag;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.OwnableEntity;
import net.minecraft.world.entity.TraceableEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.entity.projectile.Projectile;
import net.minecraftforge.event.entity.EntityJoinLevelEvent;
import net.minecraftforge.event.entity.living.LivingAttackEvent;
import net.minecraftforge.event.entity.living.LivingDamageEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.ServerConfig;

/**
 * Owner 21.11, joint cast (T15), server side of {@link CoAuthorMath}.
 * <ul>
 *   <li>Point 4: JointCast links the two mages at the merge ({@link #link}); while linked, our spells count the partner as the caster
 *       himself (HigherSpell.friendly, Explosion, Frozen Hour, Disintegration), Iron's counts them as friends
 *       (mixin/IronsFriendlyFireMixin on DamageSources.isFriendlyFireBetween), and any spell damage between them is cancelled here.
 *       Entities a co-author spawns while the spell takes effect carry both names (NBT {@value #TAG}) and never hurt either of them.</li>
 *   <li>Point 5: every damage between two players (attributed through projectiles, pets, summons, zones) is remembered;
 *       JointCast does not merge such a pair for [joint_cast] hostility_memory_seconds.</li>
 * </ul>
 */
@Mod.EventBusSubscriber(modid = PohCore.MODID)
public final class CoAuthors {
    private CoAuthors() {}

    public static final String TAG = "pohsmp_coauthors";
    /** Entities spawned this long after the spell took effect still belong to it (its zones, rains, fields). */
    private static final long SPAWN_GRACE = 40;

    private static final List<CoAuthorMath.Link> LINKS = new ArrayList<>();
    private static final Map<CoAuthorMath.Link, Long> FIRED = new java.util.HashMap<>();
    private static final Map<String, Long> HOSTILE = CoAuthorMath.memory();

    private static long now(Entity e) {
        return e.level().getGameTime();
    }

    // ---- point 4 ----

    /** The two mages merged their casts of spell. */
    public static CoAuthorMath.Link link(ServerPlayer a, ServerPlayer b, String spell) {
        CoAuthorMath.Link l = new CoAuthorMath.Link(a.getUUID(), b.getUUID(), spell);
        LINKS.add(l);
        return l;
    }

    /** The joint spell took effect: the link stays for its fields. */
    public static void fired(CoAuthorMath.Link l, ServerPlayer by) {
        if (l == null) return;
        l.fired(now(by));
        FIRED.put(l, now(by));
    }

    /** The pair broke up before the spell took effect: nothing of it is shared. */
    public static void unlink(CoAuthorMath.Link l) {
        if (l == null) return;
        LINKS.remove(l);
        FIRED.remove(l);
    }

    /** True if x and y are co-authors of a live joint cast. */
    public static boolean linked(Entity x, Entity y) {
        if (x == null || y == null || LINKS.isEmpty() || !(x instanceof Player) || !(y instanceof Player)) return false;
        return CoAuthorMath.linked(LINKS, x.getUUID(), y.getUUID(), now(x));
    }

    /** The next owner of an entity: shooter, summoner, tamer, the caster of a zone. */
    static Entity ownerOf(Entity e) {
        if (e instanceof IMagicSummon s) return s.getSummoner();
        if (e instanceof Projectile p) return p.getOwner();
        if (e instanceof TraceableEntity t) return t.getOwner();
        if (e instanceof OwnableEntity o) return o.getOwner();
        return null;
    }

    /** The player a hit by this entity is attributed to, or null. */
    public static ServerPlayer playerOf(Entity e) {
        Entity r = CoAuthorMath.attribute(e, CoAuthors::ownerOf, x -> x instanceof ServerPlayer);
        return r instanceof ServerPlayer p ? p : null;
    }

    private static ServerPlayer attacker(DamageSource s) {
        ServerPlayer p = playerOf(s.getEntity());
        return p != null ? p : playerOf(s.getDirectEntity());
    }

    private static List<UUID> tagged(Entity e) {
        List<UUID> out = new ArrayList<>();
        if (e == null || !e.getPersistentData().contains(TAG, Tag.TAG_LIST)) return out;
        for (Tag t : e.getPersistentData().getList(TAG, Tag.TAG_STRING)) {
            try {
                out.add(UUID.fromString(t.getAsString()));
            } catch (IllegalArgumentException ignored) {
            }
        }
        return out;
    }

    /** An entity a co-author spawned while the joint spell takes effect carries both co-authors. */
    @SubscribeEvent(priority = EventPriority.LOWEST)
    public static void onJoin(EntityJoinLevelEvent e) {
        if (LINKS.isEmpty() || e.getLevel().isClientSide() || e.getEntity() instanceof Player) return;
        Entity ent = e.getEntity();
        Entity owner = ownerOf(ent);
        if (!(owner instanceof ServerPlayer p)) return;
        long now = now(p);
        for (CoAuthorMath.Link l : LINKS) {
            if (!l.alive(now) || !l.has(p.getUUID())) continue;
            Long at = FIRED.get(l);
            if (at != null && now - at > SPAWN_GRACE) continue;
            ListTag list = new ListTag();
            list.add(StringTag.valueOf(l.a.toString()));
            list.add(StringTag.valueOf(l.b.toString()));
            ent.getPersistentData().put(TAG, list);
            return;
        }
    }

    /** Spell harm between co-authors is cancelled (any spell damage while linked; everything from an entity of the joint spell). */
    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void onAttack(LivingAttackEvent e) {
        if (!(e.getEntity() instanceof ServerPlayer victim)) return;
        DamageSource s = e.getSource();
        List<UUID> tags = tagged(s.getDirectEntity());
        if (LINKS.isEmpty() && tags.isEmpty()) return;
        ServerPlayer att = attacker(s);
        if (att == null) return;
        String spell = s instanceof SpellDamageSource sds && sds.spell() != null ? sds.spell().getSpellId() : null;
        boolean magic = spell != null || s.typeHolder().unwrapKey().map(k -> k.location().getNamespace().equals(PohCore.MODID)).orElse(false);
        if (CoAuthorMath.shields(LINKS, att.getUUID(), victim.getUUID(), now(victim), spell, magic, tags)) e.setCanceled(true);
    }

    // ---- point 5 ----

    /** Damage that really landed between two players (after armor, not cancelled). */
    @SubscribeEvent(priority = EventPriority.LOWEST)
    public static void onDamage(LivingDamageEvent e) {
        if (e.getAmount() <= 0 || !(e.getEntity() instanceof ServerPlayer victim)) return;
        ServerPlayer att = attacker(e.getSource());
        if (att != null && att != victim) CoAuthorMath.hurt(HOSTILE, att.getUUID(), victim.getUUID(), now(victim));
    }

    /** True if the two players hurt each other recently: no joint cast. */
    public static boolean hostile(ServerPlayer a, ServerPlayer b) {
        return CoAuthorMath.hostile(HOSTILE, a.getUUID(), b.getUUID(), now(a), 20L * ServerConfig.JOINT_HOSTILITY.get());
    }

    public static void tellHostile(ServerPlayer p) {
        p.displayClientMessage(Component.translatable("ui.pohsmp_core.joint_cast.hostile"), true);
    }

    @SubscribeEvent
    public static void onTick(net.minecraftforge.event.TickEvent.ServerTickEvent e) {
        if (e.phase != net.minecraftforge.event.TickEvent.Phase.END || LINKS.isEmpty()) return;
        long now = e.getServer().overworld().getGameTime();
        LINKS.removeIf(l -> {
            boolean dead = !l.alive(now);
            if (dead) FIRED.remove(l);
            return dead;
        });
    }

    @SubscribeEvent
    public static void onLogout(PlayerEvent.PlayerLoggedOutEvent e) {
        CoAuthorMath.forget(HOSTILE, e.getEntity().getUUID());
    }

    @SubscribeEvent
    public static void onStopping(ServerStoppingEvent e) {
        LINKS.clear();
        FIRED.clear();
        HOSTILE.clear();
    }
}
