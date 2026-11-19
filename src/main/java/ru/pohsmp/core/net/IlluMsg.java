package ru.pohsmp.core.net;

import java.util.UUID;
import java.util.function.Supplier;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.fml.DistExecutor;
import net.minecraftforge.network.NetworkEvent;

/**
 * T22 "Illusions": what one client must draw falsely. kind - see constants; entity - the real entity it is about; other - a player uuid
 * (whose face) or the copy's owner; text - a name or an entity type id; x y z yaw pitch - a place; ticks - how long; i - a small number
 * (copy id, flags).
 */
public final class IlluMsg {
    /** entity looks like player other (name = text) for ticks. */
    public static final int DISGUISE_PLAYER = 0;
    /** entity looks like a mob of type text for ticks. */
    public static final int DISGUISE_MOB = 1;
    /** entity's disguise is over. */
    public static final int DISGUISE_END = 2;
    /** copy i of player entity appears at x y z (yaw), lives ticks. */
    public static final int COPY_SPAWN = 3;
    /** copy i moves to x y z, yaw, pitch; ticks bit 0 = swing, bit 1 = jumping, bit 2 = sprint, bit 3 = sneak, bit 4 = cast. */
    public static final int COPY_MOVE = 4;
    /** copy i is hurt (red flash, sound). */
    public static final int COPY_HURT = 5;
    /** copy i is gone (poof). */
    public static final int COPY_GONE = 6;
    /** generic zone on for this client: i = zone kind, x y z = centre, yaw = radius, ticks = life, entity = caster. */
    public static final int ZONE = 8;
    /** zone i of caster entity is over. */
    public static final int ZONE_END = 9;
    /** player entity plays the Iron's / PlayerAnimator animation text (e.g. pohsmp_illusion_butterfly_wake). */
    public static final int ANIM = 10;
    /** «Сон бабочки»: this client's hearts show x less health than it has (the held back damage); x = 0 ends it. */
    public static final int FAKE_HP = 11;
    /** T24: this client's player is erased for ticks more (its screen, its quiet); 0 = back in the world. */
    public static final int ERASED = 12;
    /** T23: the sky of this client - i = SKY_DREAD (the Abyss Eye looks at you: dark edges, swaying view) or SKY_DAWN (day light, warm), for ticks; 0 = off. */
    public static final int SKY = 13;
    public static final int SKY_DREAD = 1, SKY_DAWN = 2;
    /** «Сон бабочки»: entity is drawn see-through for ticks (it showed itself by a strike or a cast). */
    public static final int GHOST = 14;
    /** «Сон бабочки»: the victim «died» in the dream - the short dark screen for ticks (it is moved meanwhile). */
    public static final int DREAM_DEATH = 15;
    /** «Сон бабочки» music: i = 0 start (ticks = how long it may play at most), i = 1 fade out over ticks. */
    public static final int DREAM_MUSIC = 16;
    /** T25 «Погружение»: i = this client's stage now (0 = none), ticks = how long it is held at least. */
    public static final int IMMERSION = 17;
    /** T25 «Ночь без рассвета»: this client's night (midnight, the red moon) for ticks more; 0 = it ends. */
    public static final int NIGHT = 18;
    /** A walk led by a spell (Coven Arrival, the retinue players): this client's own player walks to x y z within ticks and faces yaw at the end. */
    public static final int WALK = 19;
    /** zone kinds (i of ZONE / ZONE_END) */
    public static final int Z_VEIL = 1, Z_LABYRINTH = 2, Z_NIGHTMARE = 3, Z_DREAM = 4;

    public final byte kind;
    public final int entity, ticks, i;
    public final UUID other;
    public final String text;
    public final float x, y, z, yaw, pitch;

    public IlluMsg(int kind, int entity, int ticks, int i, UUID other, String text, double x, double y, double z, float yaw, float pitch) {
        this.kind = (byte) kind;
        this.entity = entity;
        this.ticks = ticks;
        this.i = i;
        this.other = other;
        this.text = text == null ? "" : text;
        this.x = (float) x;
        this.y = (float) y;
        this.z = (float) z;
        this.yaw = yaw;
        this.pitch = pitch;
    }

    public static IlluMsg of(int kind, int entity, int ticks) {
        return new IlluMsg(kind, entity, ticks, 0, null, "", 0, 0, 0, 0, 0);
    }

    public IlluMsg(FriendlyByteBuf b) {
        kind = b.readByte();
        entity = b.readVarInt();
        ticks = b.readVarInt();
        i = b.readVarInt();
        other = b.readBoolean() ? b.readUUID() : null;
        text = b.readUtf(256);
        x = b.readFloat();
        y = b.readFloat();
        z = b.readFloat();
        yaw = b.readFloat();
        pitch = b.readFloat();
    }

    public void encode(FriendlyByteBuf b) {
        b.writeByte(kind);
        b.writeVarInt(entity);
        b.writeVarInt(ticks);
        b.writeVarInt(i);
        b.writeBoolean(other != null);
        if (other != null) b.writeUUID(other);
        b.writeUtf(text, 256);
        b.writeFloat(x);
        b.writeFloat(y);
        b.writeFloat(z);
        b.writeFloat(yaw);
        b.writeFloat(pitch);
    }

    public void handle(Supplier<NetworkEvent.Context> ctx) {
        DistExecutor.unsafeRunWhenOn(Dist.CLIENT, () -> () -> ru.pohsmp.core.client.illusion.IllusionClient.handle(this));
    }
}
