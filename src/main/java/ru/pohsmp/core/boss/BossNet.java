package ru.pohsmp.core.boss;

import java.util.UUID;
import java.util.function.Supplier;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.Entity;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.fml.DistExecutor;
import net.minecraftforge.network.NetworkDirection;
import net.minecraftforge.network.NetworkEvent;
import net.minecraftforge.network.NetworkRegistry;
import net.minecraftforge.network.PacketDistributor;
import net.minecraftforge.network.simple.SimpleChannel;
import ru.pohsmp.core.PohCore;

/**
 * The bosses' own channel (pohsmp_core:boss), so ru.pohsmp.core.net.Net stays untouched. One message type with a kind and generic
 * fields (the way Net.HFx does it); the client side is boss/client/BossClient.handle.
 */
public final class BossNet {
    private BossNet() {}

    private static final String V = "1";
    public static final SimpleChannel CH = NetworkRegistry.newSimpleChannel(new ResourceLocation(PohCore.MODID, "boss"), () -> V, V::equals, V::equals);

    public static void register() {
        CH.messageBuilder(Msg.class, 0, NetworkDirection.PLAY_TO_CLIENT).encoder(Msg::encode).decoder(Msg::new).consumerMainThread(Msg::handle).add();
    }

    // kinds
    /** Bar state: u = boss event id (the entity UUID), s1 = boss id, a = phase, b = flags (BAR_*). */
    public static final int BAR = 0;
    /** Bar gone (the boss died / surrendered / left): u. */
    public static final int BAR_STOP = 1;
    /** Scene start: s1 = scene id, a = boss entity, b = duration, c = flags (SCENE_*), d = extra entity, x,y,z = focus, f = yaw. */
    public static final int SCENE = 2;
    /** Scene stop (camera glides back in 1 s): s1 = scene id, a = boss entity. */
    public static final int SCENE_STOP = 3;
    /** Title: s1 = texture base (textures/gui/title/<s1>_<lang>.png), a = hold ticks, s2 = lang key of a line under it or "". */
    public static final int TITLE = 4;
    /** A line over an entity: a = entity, s1 = lang key, b = ticks, c = rgb, f = height above its feet. */
    public static final int SUBTITLE = 5;
    /**
     * Music (T33, by phases): a = entity, b = MUSIC_* mode, c = loop 1..3 (or 1/0 for MUSIC_FILTER), d = fade ticks, s1 = the base sound
     * id (pohsmp_core:music.<id>: the old one-sound stub; its parts are <s1>_intro, <s1>_p1.._p3).
     */
    public static final int MUSIC = 6;
    /** A PlayerAnimator animation on a player: a = entity, s1 = animation id (irons_spellbooks:...), b = 1 play / 0 stop. */
    public static final int POSE = 7;
    /** Render flags of a boss (LOOK_*): a = entity, b = flags. */
    public static final int LOOK = 8;
    /**
     * A spoken line of a boss on screen (owner 21.11: the subtitle «свиток» over the hotbar instead of the chat): a = entity, b = rgb
     * (the name), d = style (BossSayMath.STYLES index, -1 = default), s1 = lang key of the phrase, s2 = the speaker's name (Component
     * JSON). The client times, wraps and queues it (BossSayClient).
     */
    public static final int SAY = 9;

    /** MUSIC modes. STOP: fade out in d ticks. START: the fight's music (intro → loop c), nothing if it already plays. PHASE: crossfade
     *  in d ticks to loop c (or start loop c fading in, for a late viewer). CUT: loop c at once, the rest stops dead. FILTER: c = 1
     *  muffled («under water»: low-pass), 0 clear. */
    public static final int MUSIC_STOP = 0, MUSIC_START = 1, MUSIC_PHASE = 2, MUSIC_CUT = 3, MUSIC_FILTER = 4;
    public static final int BAR_VISIBLE = 1, BAR_PULSE = 2, BAR_FLASH = 4;
    /** Watchers' movement input is locked (intro, death); without it they can move and fight while the camera plays. */
    public static final int SCENE_LOCK_INPUT = 1;
    /** Letterbox bars. */
    public static final int SCENE_BARS = 2;
    /** The HUD is hidden (as F1). */
    public static final int SCENE_NO_HUD = 4;
    public static final int LOOK_HIDDEN = 1, LOOK_FLAME_OUT = 2, LOOK_NO_WEAPON = 4, LOOK_SOUL = 8;

    public static final class Msg {
        public final int kind;
        public int a, b, c, d;
        public double x, y, z;
        public float f;
        public String s1 = "", s2 = "";
        public UUID u = new UUID(0, 0);

        public Msg(int kind) {
            this.kind = kind;
        }

        public Msg(FriendlyByteBuf buf) {
            kind = buf.readByte();
            a = buf.readVarInt();
            b = buf.readVarInt();
            c = buf.readVarInt();
            d = buf.readVarInt();
            x = buf.readDouble();
            y = buf.readDouble();
            z = buf.readDouble();
            f = buf.readFloat();
            s1 = buf.readUtf(256);
            s2 = buf.readUtf(256);
            u = buf.readUUID();
        }

        public void encode(FriendlyByteBuf buf) {
            buf.writeByte(kind);
            buf.writeVarInt(a);
            buf.writeVarInt(b);
            buf.writeVarInt(c);
            buf.writeVarInt(d);
            buf.writeDouble(x);
            buf.writeDouble(y);
            buf.writeDouble(z);
            buf.writeFloat(f);
            buf.writeUtf(s1, 256);
            buf.writeUtf(s2, 256);
            buf.writeUUID(u);
        }

        public void handle(Supplier<NetworkEvent.Context> ctx) {
            DistExecutor.unsafeRunWhenOn(Dist.CLIENT, () -> () -> ru.pohsmp.core.boss.client.BossClient.handle(this));
            ctx.get().setPacketHandled(true);
        }

        public Msg ints(int a, int b, int c, int d) {
            this.a = a;
            this.b = b;
            this.c = c;
            this.d = d;
            return this;
        }

        public Msg pos(double x, double y, double z) {
            this.x = x;
            this.y = y;
            this.z = z;
            return this;
        }

        public Msg str(String s1, String s2) {
            this.s1 = s1 == null ? "" : s1;
            this.s2 = s2 == null ? "" : s2;
            return this;
        }
    }

    public static void to(ServerPlayer p, Msg m) {
        CH.send(PacketDistributor.PLAYER.with(() -> p), m);
    }

    public static void tracking(Entity e, Msg m) {
        CH.send(PacketDistributor.TRACKING_ENTITY_AND_SELF.with(() -> e), m);
    }
}
