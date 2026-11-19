package ru.pohsmp.core.net;

import java.util.function.Supplier;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.fml.DistExecutor;
import net.minecraftforge.network.NetworkDirection;
import net.minecraftforge.network.NetworkEvent;
import net.minecraftforge.network.NetworkRegistry;
import net.minecraftforge.network.PacketDistributor;
import net.minecraftforge.network.simple.SimpleChannel;
import ru.pohsmp.core.PohCore;

public final class Net {
    private Net() {}

    private static final String V = "5";
    public static final SimpleChannel CH = NetworkRegistry.newSimpleChannel(new ResourceLocation(PohCore.MODID, "main"), () -> V, V::equals, V::equals);

    public static void register() {
        CH.messageBuilder(Fx.class, 0, NetworkDirection.PLAY_TO_CLIENT).encoder(Fx::encode).decoder(Fx::new).consumerMainThread(Fx::handle).add();
        CH.messageBuilder(HFx.class, 1, NetworkDirection.PLAY_TO_CLIENT).encoder(HFx::encode).decoder(HFx::new).consumerMainThread(HFx::handle).add();
        CH.messageBuilder(FxMsg.class, 2, NetworkDirection.PLAY_TO_CLIENT).encoder(FxMsg::encode).decoder(FxMsg::new).consumerMainThread(FxMsg::handle).add();
        CH.messageBuilder(HideMsg.class, 3, NetworkDirection.PLAY_TO_CLIENT).encoder(HideMsg::encode).decoder(HideMsg::new).consumerMainThread(HideMsg::handle).add();
        CH.messageBuilder(NpcCastMsg.class, 4, NetworkDirection.PLAY_TO_CLIENT).encoder(NpcCastMsg::encode).decoder(NpcCastMsg::new).consumerMainThread(NpcCastMsg::handle).add();
        CH.messageBuilder(CastTime.class, 5, NetworkDirection.PLAY_TO_CLIENT).encoder(CastTime::encode).decoder(CastTime::new).consumerMainThread(CastTime::handle).add();
    }

    /**
     * Visuals of the Higher school. kind: see constants. key identifies one effect instance (STOP removes it, the same key replaces it).
     * a, b: entity ids (-1 none); x y z: position; dur: ticks; f: radius/size; i: color or mask.
     */
    public static final class HFx {
        public static final int STOP = 0, TELE = 1, SLEEP = 2, STAR = 3, SING = 4, SEAL = 5, ASC = 6, RING = 7, BURST = 8, PILLAR = 9, SKY = 10, FLASH = 11, MOON = 12,
                CUT = 13, DOWN = 14, RIFT = 15, TABOO = 16, SIGIL = 17, WARD = 18, MILKY = 19, GALAXY = 20, SOUL = 21, TABOO_CAST = 22, BLIZZARD = 23,
                CLOSURE_CAST = 24, CLOSURE = 25, CLOSURE_HIT = 26, ANIM = 27,
                JOINT = 28;   // joint cast: a = caster, b = partner, dur, f = sigil radius, i = (school sigil << 24) | color
        public final byte kind;
        public final int key, a, b, dur, i;
        public final float x, y, z, f;

        public HFx(int kind, int key, int a, int b, int dur, double x, double y, double z, double f, int i) {
            this.kind = (byte) kind;
            this.key = key;
            this.a = a;
            this.b = b;
            this.dur = dur;
            this.x = (float) x;
            this.y = (float) y;
            this.z = (float) z;
            this.f = (float) f;
            this.i = i;
        }

        public HFx(FriendlyByteBuf buf) {
            kind = buf.readByte();
            key = buf.readVarInt();
            a = buf.readVarInt();
            b = buf.readVarInt();
            dur = buf.readVarInt();
            x = buf.readFloat();
            y = buf.readFloat();
            z = buf.readFloat();
            f = buf.readFloat();
            i = buf.readInt();
        }

        public void encode(FriendlyByteBuf buf) {
            buf.writeByte(kind);
            buf.writeVarInt(key);
            buf.writeVarInt(a);
            buf.writeVarInt(b);
            buf.writeVarInt(dur);
            buf.writeFloat(x);
            buf.writeFloat(y);
            buf.writeFloat(z);
            buf.writeFloat(f);
            buf.writeInt(i);
        }

        public void handle(Supplier<NetworkEvent.Context> ctx) {
            DistExecutor.unsafeRunWhenOn(Dist.CLIENT, () -> () -> ru.pohsmp.core.client.HigherFx.handle(this));
        }
    }

    /** Sends to every player in the level within 160 blocks of either point. */
    public static void sendNear(ServerLevel sl, double x1, double y1, double z1, double x2, double y2, double z2, Object msg) {
        for (ServerPlayer p : sl.players())
            if (p.distanceToSqr(x1, y1, z1) < 160 * 160 || p.distanceToSqr(x2, y2, z2) < 160 * 160)
                CH.send(PacketDistributor.PLAYER.with(() -> p), msg);
    }

    /** Disintegration visuals. type: 0 start, 1 finished (x y z = target center), 2 cancelled. */
    public static final class Fx {
        public final byte type;
        public final int caster, target, duration;
        public final float x, y, z;

        public Fx(int type, int caster, int target, int duration, double x, double y, double z) {
            this.type = (byte) type;
            this.caster = caster;
            this.target = target;
            this.duration = duration;
            this.x = (float) x;
            this.y = (float) y;
            this.z = (float) z;
        }

        public Fx(FriendlyByteBuf b) {
            type = b.readByte();
            caster = b.readVarInt();
            target = b.readVarInt();
            duration = b.readVarInt();
            x = b.readFloat();
            y = b.readFloat();
            z = b.readFloat();
        }

        public void encode(FriendlyByteBuf b) {
            b.writeByte(type);
            b.writeVarInt(caster);
            b.writeVarInt(target);
            b.writeVarInt(duration);
            b.writeFloat(x);
            b.writeFloat(y);
            b.writeFloat(z);
        }

        public void handle(Supplier<NetworkEvent.Context> ctx) {
            DistExecutor.unsafeRunWhenOn(Dist.CLIENT, () -> () -> ru.pohsmp.core.client.DisintegrationFx.handle(this));
        }
    }

    /** A non-player caster (spell/NpcCast) started, finished or cancelled a cast: sound and animation on clients. */
    public static final class NpcCastMsg {
        public static final int START = 0, FINISH = 1, CANCEL = 2;
        public final byte phase;
        public final int entity, level, ticks;
        public final String spell;

        public NpcCastMsg(int phase, int entity, String spell, int level, int ticks) {
            this.phase = (byte) phase;
            this.entity = entity;
            this.spell = spell;
            this.level = level;
            this.ticks = ticks;
        }

        public NpcCastMsg(FriendlyByteBuf b) {
            phase = b.readByte();
            entity = b.readVarInt();
            spell = b.readUtf(256);
            level = b.readVarInt();
            ticks = b.readVarInt();
        }

        public void encode(FriendlyByteBuf b) {
            b.writeByte(phase);
            b.writeVarInt(entity);
            b.writeUtf(spell, 256);
            b.writeVarInt(level);
            b.writeVarInt(ticks);
        }

        public void handle(Supplier<NetworkEvent.Context> ctx) {
            DistExecutor.unsafeRunWhenOn(Dist.CLIENT, () -> () -> ru.pohsmp.core.client.NpcCastClient.handle(this));
        }
    }

    /** Joint cast: the caster's own cast bar gets the new total and remaining time (ticks). */
    public static final class CastTime {
        public final int duration, remaining;

        public CastTime(int duration, int remaining) {
            this.duration = duration;
            this.remaining = remaining;
        }

        public CastTime(FriendlyByteBuf b) {
            duration = b.readVarInt();
            remaining = b.readVarInt();
        }

        public void encode(FriendlyByteBuf b) {
            b.writeVarInt(duration);
            b.writeVarInt(remaining);
        }

        public void handle(Supplier<NetworkEvent.Context> ctx) {
            DistExecutor.unsafeRunWhenOn(Dist.CLIENT, () -> () -> ru.pohsmp.core.client.JointFx.castTime(this));
        }
    }
}
