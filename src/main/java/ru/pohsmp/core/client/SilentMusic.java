package ru.pohsmp.core.client;

import net.minecraft.client.Minecraft;
import net.minecraft.client.resources.sounds.AbstractTickableSoundInstance;
import net.minecraft.client.resources.sounds.SoundInstance;
import net.minecraft.client.sounds.SoundManager;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.RandomSource;
import net.minecraftforge.client.event.sound.PlaySoundEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.level.LevelEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.Reg;

/**
 * "Gate" (T03) on the client of every watcher: the music track plays the same everywhere (not positional, no distance falloff)
 * from the start of the cast, and every other game sound and the game's music are muted for the whole scene: sounds already
 * playing stop, new ones are dropped (PlaySoundEvent), so the game music cannot start either. After the scene everything plays
 * again. Cancelled cast: the track fades out in 1 s and the other sounds come back at once.
 */
public final class SilentMusic {
    private SilentMusic() {}

    private static final int FADE_TICKS = 20;
    private static Track track;
    private static int key;
    /** Client ticks left until the silence lifts by itself (lost STOP packet). */
    private static int left;
    private static boolean silent;

    /** The track: relative to the listener at 0,0,0 with no attenuation = the same loudness for everyone. */
    private static final class Track extends AbstractTickableSoundInstance {
        private int fade = -1;

        Track() {
            super(Reg.MUSIC_SILENT_GATE.get(), SoundSource.RECORDS, RandomSource.create());
            this.relative = true;
            this.attenuation = SoundInstance.Attenuation.NONE;
            this.looping = false;
            this.delay = 0;
            this.volume = 1f;
            this.x = this.y = this.z = 0;
        }

        void fadeOut() {
            if (fade < 0) fade = FADE_TICKS;
        }

        @Override
        public boolean canStartSilent() {
            return true;
        }

        @Override
        public void tick() {
            if (fade < 0) return;
            fade--;
            volume = Math.max(0f, fade / (float) FADE_TICKS);
            if (fade <= 0) stop();
        }
    }

    /** Scene start (Cutscene SILENT_GATE packet): silence the game, play the track. dur: scene length in ticks. */
    public static void start(int k, int dur) {
        Minecraft mc = Minecraft.getInstance();
        SoundManager sm = mc.getSoundManager();
        if (track != null) sm.stop(track);
        key = k;
        left = dur + 60;
        silent = true;
        mc.getMusicManager().stopPlaying();
        sm.stop();
        track = new Track();
        sm.play(track);
    }

    /** Scene end or cancel (STOP with the scene key): the track fades in 1 s (at the natural end it is already over), sound returns. */
    public static void stop(int k) {
        if (!silent && track == null || k != key) return;
        silent = false;
        if (track != null) track.fadeOut();
    }

    private static void reset() {
        silent = false;
        if (track != null) Minecraft.getInstance().getSoundManager().stop(track);
        track = null;
    }

    @SubscribeEvent(priority = EventPriority.LOWEST)
    public static void onSound(PlaySoundEvent e) {
        if (!silent) return;
        SoundInstance s = e.getSound();
        if (s != null && s != track) e.setSound(null);
    }

    @SubscribeEvent
    public static void onTick(TickEvent.ClientTickEvent e) {
        if (e.phase != TickEvent.Phase.END) return;
        if (silent && --left <= 0) stop(key);
        if (track != null && (track.isStopped() || !silent && !Minecraft.getInstance().getSoundManager().isActive(track))) track = null;
    }

    @SubscribeEvent
    public static void onUnload(LevelEvent.Unload e) {
        if (e.getLevel().isClientSide()) reset();
    }
}
