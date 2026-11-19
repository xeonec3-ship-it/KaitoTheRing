package ru.pohsmp.core.client.illusion;

import net.minecraft.client.Minecraft;
import net.minecraft.client.resources.sounds.AbstractTickableSoundInstance;
import net.minecraft.client.resources.sounds.SoundInstance;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.RandomSource;
import net.minecraftforge.client.event.sound.PlaySoundEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.level.LevelEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.Reg;

/**
 * T22 «Сон бабочки» music (owner 19.11): one track for the caster, its allies and the victims, from the start of the cast, the same loudness
 * everywhere. The game's own music and records stay off while it plays; every other sound plays. Fades: cast cancelled - 1 s, a victim's
 * dream ended early - 2 s (the server says how long).
 */
public final class DreamMusic {
    private DreamMusic() {}

    private static Track track;
    private static int left;

    private static final class Track extends AbstractTickableSoundInstance {
        int fade = -1, fadeLen = 20;

        Track() {
            super(Reg.MUSIC_BUTTERFLY_DREAM.get(), SoundSource.RECORDS, RandomSource.create());
            this.relative = true;
            this.attenuation = SoundInstance.Attenuation.NONE;
            this.looping = false;
            this.delay = 0;
            this.volume = 1f;
            this.x = this.y = this.z = 0;
        }

        @Override
        public boolean canStartSilent() {
            return true;
        }

        @Override
        public void tick() {
            if (fade < 0) return;
            fade--;
            volume = Math.max(0f, fade / (float) fadeLen);
            if (fade <= 0) stop();
        }
    }

    static void handle(int i, int ticks) {
        Minecraft mc = Minecraft.getInstance();
        var sm = mc.getSoundManager();
        if (i == 0) {
            if (track != null) sm.stop(track);
            mc.getMusicManager().stopPlaying();
            sm.stop(null, SoundSource.MUSIC);
            sm.stop(null, SoundSource.RECORDS);
            track = new Track();
            left = Math.max(20, ticks);
            sm.play(track);
        } else if (track != null && track.fade < 0) {
            track.fadeLen = Math.max(1, ticks);
            track.fade = track.fadeLen;
        }
    }

    @SubscribeEvent(priority = EventPriority.LOWEST)
    public static void onSound(PlaySoundEvent e) {
        if (track == null) return;
        SoundInstance s = e.getSound();
        if (s != null && s != track && (s.getSource() == SoundSource.MUSIC || s.getSource() == SoundSource.RECORDS)) e.setSound(null);
    }

    @SubscribeEvent
    public static void onTick(TickEvent.ClientTickEvent e) {
        if (e.phase != TickEvent.Phase.END || track == null) return;
        if (--left <= 0 && track.fade < 0) track.fade = track.fadeLen = 20;
        if (track.isStopped() || left < -40 && !Minecraft.getInstance().getSoundManager().isActive(track)) track = null;
    }

    @SubscribeEvent
    public static void onUnload(LevelEvent.Unload e) {
        if (!e.getLevel().isClientSide() || track == null) return;
        Minecraft.getInstance().getSoundManager().stop(track);
        track = null;
    }
}
