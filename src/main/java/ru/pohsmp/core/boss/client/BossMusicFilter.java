package ru.pohsmp.core.boss.client;

import com.mojang.blaze3d.audio.Channel;
import java.lang.reflect.Field;
import java.lang.reflect.Modifier;
import java.util.Map;
import net.minecraft.client.Minecraft;
import net.minecraft.client.resources.sounds.SoundInstance;
import net.minecraft.client.sounds.ChannelAccess;
import net.minecraft.client.sounds.SoundEngine;
import net.minecraft.client.sounds.SoundManager;
import org.lwjgl.openal.AL10;
import org.lwjgl.openal.ALC10;
import org.lwjgl.openal.EXTEfx;
import ru.pohsmp.core.PohCore;

/**
 * T33 «Полное Раскрытие»: the boss music muffled inside the dream — an OpenAL EFX low-pass on the part's own source (the high
 * frequencies cut, as under water). The source is found by reflection by type, not by name (SoundManager → its SoundEngine → the map
 * instance → channel handle → the Channel's int field that is an AL source), so no SRG names are needed. Anything missing (no EFX on
 * the device, the fields not found) → works() = false and the music is only made quieter (BossMusicClient.Part). Logged once.
 */
final class BossMusicFilter {
    private BossMusicFilter() {}

    private static boolean broken;
    private static Field engineField, mapField, sourceField;
    /** The low-pass filter, made on the sound thread on first use (0 = not yet, -1 = unavailable). */
    private static volatile int filter;

    static boolean works() {
        return !broken && filter >= 0;
    }

    /** Puts the filter on / off the part's source. True = done (or never possible), false = its channel is not there yet: try again. */
    static boolean apply(SoundInstance inst, boolean on) {
        if (!works()) return true;
        if (!on && filter == 0) return true;   // never filtered
        try {
            SoundManager sm = Minecraft.getInstance().getSoundManager();
            if (engineField == null) engineField = fieldOfType(SoundManager.class, SoundEngine.class);
            SoundEngine engine = (SoundEngine) engineField.get(sm);
            ChannelAccess.ChannelHandle h = handle(engine, inst);
            if (h == null) return false;
            h.execute(ch -> onSoundThread(ch, on));
            return true;
        } catch (Throwable t) {
            fail(t.toString());
            return true;
        }
    }

    private static ChannelAccess.ChannelHandle handle(SoundEngine engine, SoundInstance inst) throws IllegalAccessException {
        if (mapField != null) return (ChannelAccess.ChannelHandle) ((Map<?, ?>) mapField.get(engine)).get(inst);
        for (Field f : SoundEngine.class.getDeclaredFields()) {
            if (Modifier.isStatic(f.getModifiers()) || !Map.class.isAssignableFrom(f.getType())) continue;
            f.setAccessible(true);
            if (((Map<?, ?>) f.get(engine)).get(inst) instanceof ChannelAccess.ChannelHandle h) {
                mapField = f;
                return h;
            }
        }
        return null;   // not playing (yet)
    }

    private static void onSoundThread(Channel ch, boolean on) {
        try {
            int src = source(ch);
            if (src == 0) return;
            if (filter == 0) filter = makeFilter();
            if (filter < 0) return;
            AL10.alSourcei(src, EXTEfx.AL_DIRECT_FILTER, on ? filter : EXTEfx.AL_FILTER_NULL);
        } catch (Throwable t) {
            fail(t.toString());
        }
    }

    private static int source(Channel ch) throws IllegalAccessException {
        if (sourceField != null) return sourceField.getInt(ch);
        for (Field f : Channel.class.getDeclaredFields()) {
            if (Modifier.isStatic(f.getModifiers()) || f.getType() != int.class) continue;
            f.setAccessible(true);
            int v = f.getInt(ch);
            if (v != 0 && AL10.alIsSource(v)) {
                sourceField = f;
                return v;
            }
        }
        fail("no AL source in Channel");
        return 0;
    }

    private static int makeFilter() {
        long device = ALC10.alcGetContextsDevice(ALC10.alcGetCurrentContext());
        if (!ALC10.alcIsExtensionPresent(device, "ALC_EXT_EFX")) {
            PohCore.LOG.info("[boss music] no OpenAL EFX: the dream music is only made quieter");
            return -1;
        }
        int f = EXTEfx.alGenFilters();
        EXTEfx.alFilteri(f, EXTEfx.AL_FILTER_TYPE, EXTEfx.AL_FILTER_LOWPASS);
        EXTEfx.alFilterf(f, EXTEfx.AL_LOWPASS_GAIN, 0.85f);
        EXTEfx.alFilterf(f, EXTEfx.AL_LOWPASS_GAINHF, 0.08f);
        if (AL10.alGetError() != AL10.AL_NO_ERROR) {
            PohCore.LOG.info("[boss music] the EFX low-pass failed: the dream music is only made quieter");
            return -1;
        }
        return f;
    }

    private static Field fieldOfType(Class<?> owner, Class<?> type) throws NoSuchFieldException {
        for (Field f : owner.getDeclaredFields())
            if (!Modifier.isStatic(f.getModifiers()) && f.getType() == type) {
                f.setAccessible(true);
                return f;
            }
        throw new NoSuchFieldException(type.getSimpleName() + " in " + owner.getSimpleName());
    }

    private static void fail(String why) {
        if (broken) return;
        broken = true;
        PohCore.LOG.info("[boss music] no low-pass ({}): the dream music is only made quieter", why);
    }
}
