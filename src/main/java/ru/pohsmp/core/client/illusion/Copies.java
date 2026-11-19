package ru.pohsmp.core.client.illusion;

import com.mojang.authlib.GameProfile;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.player.AbstractClientPlayer;
import net.minecraft.client.player.RemotePlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Pose;
import net.minecraft.world.phys.EntityHitResult;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.client.event.InputEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.net.IlluMsg;
import ru.pohsmp.core.net.Net;

/**
 * T22: false players on this client (ru.pohsmp.core.illusion.Copies on the server). Each is a real RemotePlayer added to the client level
 * under a negative id: the player renderer draws it (Epic Fight too) with the caster's skin (AbstractClientPlayerMixin), armour and hand
 * items copied from the caster every tick, its name and team colours, shadow, walk animation from its moves; the minimap and Jade see a
 * player. A strike at it - a click on it or, with Epic Fight's swings, a swing at one in reach in front - is reported to the server.
 */
public final class Copies {
    private Copies() {}

    private static final class Copy {
        final int id, clientId, ownerId;
        final UUID owner;
        final RemotePlayer body;
        long until;
        boolean casting;
        String spell = "";

        Copy(int id, int clientId, int ownerId, UUID owner, RemotePlayer body, long until) {
            this.id = id;
            this.clientId = clientId;
            this.ownerId = ownerId;
            this.owner = owner;
            this.body = body;
            this.until = until;
        }
    }

    private static final Map<Integer, Copy> BY_ID = new HashMap<>();
    private static final Map<Integer, Copy> BY_CLIENT_ID = new HashMap<>();

    private static int clientId(int id) {
        return -1_000_000 - id;
    }

    static void handle(IlluMsg m) {
        ClientLevel lvl = Minecraft.getInstance().level;
        if (lvl == null) return;
        switch (m.kind) {
            case IlluMsg.COPY_SPAWN -> spawn(lvl, m);
            case IlluMsg.COPY_MOVE -> {
                Copy c = BY_ID.get(m.i);
                if (c == null) return;
                RemotePlayer b = c.body;
                b.lerpTo(m.x, m.y, m.z, m.yaw, m.pitch, 3, true);
                b.lerpHeadTo(m.yaw, 3);
                int f = m.ticks;
                if ((f & ru.pohsmp.core.illusion.Copies.SWING) != 0) b.swing(InteractionHand.MAIN_HAND);
                b.setSprinting((f & ru.pohsmp.core.illusion.Copies.SPRINT) != 0);
                boolean sneak = (f & ru.pohsmp.core.illusion.Copies.SNEAK) != 0;
                b.setShiftKeyDown(sneak);
                b.setPose(sneak ? Pose.CROUCHING : Pose.STANDING);
                boolean cast = (f & ru.pohsmp.core.illusion.Copies.CAST) != 0;
                if (cast && !m.text.isEmpty()) c.spell = m.text;
                if (!cast && c.casting) bolt(c);   // the copy's cast is over: its harmless spell flies off
                c.casting = cast;
            }
            case IlluMsg.COPY_HURT -> {
                Copy c = BY_ID.get(m.i);
                if (c == null) return;
                c.body.animateHurt(m.yaw);
                c.body.hurtTime = c.body.hurtDuration = 10;
                lvl.playLocalSound(c.body.getX(), c.body.getY(), c.body.getZ(), SoundEvents.PLAYER_HURT, SoundSource.PLAYERS, 1f,
                        (lvl.random.nextFloat() - lvl.random.nextFloat()) * 0.2f + 1f, false);
            }
            case IlluMsg.COPY_GONE -> remove(lvl, m.i);
            default -> {}
        }
    }

    private static void spawn(ClientLevel lvl, IlluMsg m) {
        remove(lvl, m.i);
        RemotePlayer b = new RemotePlayer(lvl, new GameProfile(UUID.randomUUID(), m.text));
        int cid = clientId(m.i);
        b.setId(cid);
        b.moveTo(m.x, m.y, m.z, m.yaw, m.pitch);
        b.setOldPosAndRot();
        b.yHeadRot = b.yHeadRotO = b.yBodyRot = b.yBodyRotO = m.yaw;
        Copy c = new Copy(m.i, cid, m.entity, m.other, b, IllusionClient.now() + m.ticks + 20);
        dress(lvl, c);
        BY_ID.put(m.i, c);
        BY_CLIENT_ID.put(cid, c);
        lvl.addPlayer(cid, b);
    }

    private static void remove(ClientLevel lvl, int id) {
        Copy c = BY_ID.remove(id);
        if (c == null) return;
        BY_CLIENT_ID.remove(c.clientId);
        lvl.removeEntity(c.clientId, Entity.RemovalReason.DISCARDED);
    }

    /**
     * The armour and hand items of the one whose look the copy wears (the caster, or the player the server gave it: «Сон бабочки»), when
     * this client knows that player; else the caster's. The copy changes when they do.
     */
    private static void dress(ClientLevel lvl, Copy c) {
        LivingEntity o = c.owner == null ? null : lvl.getPlayerByUUID(c.owner);
        if (o == null && lvl.getEntity(c.ownerId) instanceof LivingEntity le) o = le;
        if (o == null) return;
        for (EquipmentSlot s : EquipmentSlot.values()) {
            var want = o.getItemBySlot(s);
            if (!net.minecraft.world.item.ItemStack.matches(want, c.body.getItemBySlot(s))) c.body.setItemSlot(s, want.copy());
        }
        c.body.setGlowingTag(o.hasGlowingTag());
        c.body.setInvisible(o.isInvisible());
    }

    /** The owner whose skin copy p wears, or null if p is no copy. */
    static UUID faceOf(AbstractClientPlayer p) {
        if (BY_CLIENT_ID.isEmpty()) return null;
        Copy c = BY_CLIENT_ID.get(p.getId());
        return c == null ? null : c.owner;
    }

    public static boolean isCopy(Entity e) {
        return e != null && BY_CLIENT_ID.containsKey(e.getId());
    }

    // ---------------------------------------------------------------- the copies' false spells

    private static final class Bolt {
        Vec3 pos;
        final Vec3 dir;
        final org.joml.Vector3f color;
        int age;

        Bolt(Vec3 pos, Vec3 dir, org.joml.Vector3f color) {
            this.pos = pos;
            this.dir = dir;
            this.color = color;
        }
    }

    private static final java.util.List<Bolt> BOLTS = new java.util.ArrayList<>();
    private static final int BOLT_LIFE = 30;

    /** A bolt of the spell's school colour from the copy's hand along its look: it flies 1.5 s, fades and hurts no one. */
    private static void bolt(Copy c) {
        org.joml.Vector3f col = new org.joml.Vector3f(0.85f, 0.75f, 1f);
        try {
            var s = io.redspace.ironsspellbooks.api.registry.SpellRegistry.getSpell(c.spell);
            if (s != null && s.getSchoolType() != null) {
                var tc = s.getSchoolType().getDisplayName().getStyle().getColor();
                if (tc != null) {
                    int rgb = tc.getValue();
                    col = new org.joml.Vector3f(((rgb >> 16) & 255) / 255f, ((rgb >> 8) & 255) / 255f, (rgb & 255) / 255f);
                }
            }
        } catch (RuntimeException ignored) {
        }
        RemotePlayer b = c.body;
        Vec3 look = Vec3.directionFromRotation(b.getXRot(), b.getYHeadRot());
        BOLTS.add(new Bolt(b.getEyePosition().add(look.scale(0.6)).add(0, -0.25, 0), look, col));
        if (BOLTS.size() > 24) BOLTS.remove(0);
        c.spell = "";
    }

    private static void bolts(ClientLevel lvl) {
        if (BOLTS.isEmpty()) return;
        for (var it = BOLTS.iterator(); it.hasNext(); ) {
            Bolt bo = it.next();
            if (++bo.age > BOLT_LIFE) {
                it.remove();
                continue;
            }
            float k = 1 - bo.age / (float) BOLT_LIFE;
            var dust = new net.minecraft.core.particles.DustParticleOptions(bo.color, 0.4f + 1.3f * k);
            for (int i = 0; i < 3; i++) {
                Vec3 p = bo.pos.add(bo.dir.scale(i * 0.3));
                lvl.addParticle(dust, p.x, p.y, p.z, 0, 0, 0);
            }
            if (bo.age % 3 == 0 && k > 0.4) lvl.addParticle(net.minecraft.core.particles.ParticleTypes.END_ROD, bo.pos.x, bo.pos.y, bo.pos.z, 0, 0, 0);
            bo.pos = bo.pos.add(bo.dir.scale(0.9));
        }
    }

    static void tick(ClientLevel lvl) {
        bolts(lvl);
        if (BY_ID.isEmpty()) return;
        long now = IllusionClient.now();
        for (Copy c : BY_ID.values().toArray(new Copy[0])) {
            if (now > c.until) {   // the "gone" packet was lost
                remove(lvl, c.id);
                continue;
            }
            dress(lvl, c);
        }
    }

    static void clear() {
        BOLTS.clear();
        BY_ID.clear();
        BY_CLIENT_ID.clear();
    }

    /** A strike: the copy under the crosshair, or (Epic Fight swings past the crosshair) the nearest one in reach in front. */
    @SubscribeEvent
    public static void onAttack(InputEvent.InteractionKeyMappingTriggered e) {
        if (!e.isAttack() || BY_ID.isEmpty()) return;
        Minecraft mc = Minecraft.getInstance();
        if (mc.player == null) return;
        Copy hit = null;
        if (mc.hitResult instanceof EntityHitResult eh) hit = BY_CLIENT_ID.get(eh.getEntity().getId());
        if (hit == null) {
            Vec3 eye = mc.player.getEyePosition(), look = mc.player.getLookAngle();
            double best = 3.6;
            for (Copy c : BY_ID.values()) {
                Vec3 to = c.body.getBoundingBox().getCenter().subtract(eye);
                double d = to.length();
                if (d < best && to.normalize().dot(look) > 0.6) {
                    best = d;
                    hit = c;
                }
            }
        }
        if (hit != null) Net.CH.sendToServer(new Net.CopyHit(hit.id));
    }
}
