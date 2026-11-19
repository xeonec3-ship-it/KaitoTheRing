package ru.pohsmp.core.net;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.function.Supplier;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.fml.DistExecutor;
import net.minecraftforge.network.NetworkEvent;

/**
 * Data-driven effects (ru.pohsmp.core.fx): start, stop, move, reload or replace a sigil inscription (TEXT, T07). One instance = one sigil, mesh or whole effect.
 * Everything the client needs to draw the same thing as every other client: definition id, style, anchor, view yaw,
 * entities to follow, named points, scale, colour override, seed.
 */
public final class FxMsg {
    public static final int START = 0, STOP = 1, MOVE = 2, RELOAD = 3, TEXT = 4;
    public static final int FX = 0, SIGIL = 1, MESH = 2;

    public int op, inst, kind;
    public String id = "", style = "", mode = "";
    public double x, y, z, tx, ty, tz, lx, ly, lz;
    public float yaw, pitch, scale = 1;
    /** Entity ids: caster (anchor "caster", follow), target, attach (whole instance follows it); -1 none. */
    public int caster = -1, target = -1, attach = -1;
    public boolean hasTarget, hasLook;
    /** -1 = no override. */
    public int color = -1, orientation = -1, duration = -1;
    public long seed;
    /** Ticks already elapsed when sent (late joiners see the effect at its current moment). */
    public int age;
    public final Map<String, double[]> points = new LinkedHashMap<>();
    /** Sigil inscriptions by slot (layers of type text with "slot", docs/sigils.md «Надписи»); START carries the current ones. */
    public final Map<String, String> texts = new LinkedHashMap<>();
    /** TEXT: which slot gets which text. */
    public String slot = "", text = "";
    public static final int MAX_TEXT = 256;

    public FxMsg() {}

    public FxMsg(FriendlyByteBuf b) {
        op = b.readByte();
        inst = b.readVarInt();
        if (op == START) {
            kind = b.readByte();
            id = b.readUtf(128);
            style = b.readUtf(64);
            x = b.readDouble();
            y = b.readDouble();
            z = b.readDouble();
            yaw = b.readFloat();
            pitch = b.readFloat();
            scale = b.readFloat();
            caster = b.readVarInt();
            target = b.readVarInt();
            attach = b.readVarInt();
            hasTarget = b.readBoolean();
            if (hasTarget) {
                tx = b.readDouble();
                ty = b.readDouble();
                tz = b.readDouble();
            }
            hasLook = b.readBoolean();
            if (hasLook) {
                lx = b.readDouble();
                ly = b.readDouble();
                lz = b.readDouble();
            }
            color = b.readInt();
            orientation = b.readByte();
            duration = b.readVarInt();
            seed = b.readLong();
            age = b.readVarInt();
            int n = b.readVarInt();
            for (int i = 0; i < n; i++) points.put(b.readUtf(64), new double[] {b.readDouble(), b.readDouble(), b.readDouble()});
            int nt = b.readVarInt();
            for (int i = 0; i < nt; i++) texts.put(b.readUtf(64), b.readUtf(MAX_TEXT));
        } else if (op == TEXT) {
            slot = b.readUtf(64);
            text = b.readUtf(MAX_TEXT);
        } else if (op == STOP) {
            mode = b.readUtf(64);
        } else if (op == MOVE) {
            x = b.readDouble();
            y = b.readDouble();
            z = b.readDouble();
            yaw = b.readFloat();
            pitch = b.readFloat();
        }
    }

    public void encode(FriendlyByteBuf b) {
        b.writeByte(op);
        b.writeVarInt(inst);
        if (op == START) {
            b.writeByte(kind);
            b.writeUtf(id, 128);
            b.writeUtf(style == null ? "" : style, 64);
            b.writeDouble(x);
            b.writeDouble(y);
            b.writeDouble(z);
            b.writeFloat(yaw);
            b.writeFloat(pitch);
            b.writeFloat(scale);
            b.writeVarInt(caster);
            b.writeVarInt(target);
            b.writeVarInt(attach);
            b.writeBoolean(hasTarget);
            if (hasTarget) {
                b.writeDouble(tx);
                b.writeDouble(ty);
                b.writeDouble(tz);
            }
            b.writeBoolean(hasLook);
            if (hasLook) {
                b.writeDouble(lx);
                b.writeDouble(ly);
                b.writeDouble(lz);
            }
            b.writeInt(color);
            b.writeByte(orientation);
            b.writeVarInt(duration);
            b.writeLong(seed);
            b.writeVarInt(Math.max(0, age));
            b.writeVarInt(points.size());
            for (var e : points.entrySet()) {
                b.writeUtf(e.getKey(), 64);
                b.writeDouble(e.getValue()[0]);
                b.writeDouble(e.getValue()[1]);
                b.writeDouble(e.getValue()[2]);
            }
            b.writeVarInt(texts.size());
            for (var e : texts.entrySet()) {
                b.writeUtf(e.getKey(), 64);
                b.writeUtf(e.getValue(), MAX_TEXT);
            }
        } else if (op == TEXT) {
            b.writeUtf(slot == null ? "" : slot, 64);
            b.writeUtf(text == null ? "" : text, MAX_TEXT);
        } else if (op == STOP) {
            b.writeUtf(mode == null ? "" : mode, 64);
        } else if (op == MOVE) {
            b.writeDouble(x);
            b.writeDouble(y);
            b.writeDouble(z);
            b.writeFloat(yaw);
            b.writeFloat(pitch);
        }
    }

    /** A copy for re-sending (late joiners), with the age at that moment. */
    public FxMsg copyAged(int age) {
        FxMsg m = new FxMsg();
        m.op = op;
        m.inst = inst;
        m.kind = kind;
        m.id = id;
        m.style = style;
        m.mode = mode;
        m.x = x;
        m.y = y;
        m.z = z;
        m.tx = tx;
        m.ty = ty;
        m.tz = tz;
        m.lx = lx;
        m.ly = ly;
        m.lz = lz;
        m.yaw = yaw;
        m.pitch = pitch;
        m.scale = scale;
        m.caster = caster;
        m.target = target;
        m.attach = attach;
        m.hasTarget = hasTarget;
        m.hasLook = hasLook;
        m.color = color;
        m.orientation = orientation;
        m.duration = duration;
        m.seed = seed;
        m.age = age;
        m.points.putAll(points);
        m.texts.putAll(texts);
        m.slot = slot;
        m.text = text;
        return m;
    }

    public void handle(Supplier<NetworkEvent.Context> ctx) {
        DistExecutor.unsafeRunWhenOn(Dist.CLIENT, () -> () -> ru.pohsmp.core.client.fx.FxClient.handle(this));
    }
}
