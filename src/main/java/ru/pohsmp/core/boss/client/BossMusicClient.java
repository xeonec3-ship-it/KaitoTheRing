package ru.pohsmp.core.boss.client;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import net.minecraft.client.Minecraft;
import net.minecraft.client.resources.sounds.AbstractTickableSoundInstance;
import net.minecraft.client.resources.sounds.SoundInstance;
import net.minecraft.client.sounds.SoundManager;
import net.minecraft.client.sounds.WeighedSoundEvents;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.RandomSource;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.boss.BossMusicMath;
import ru.pohsmp.core.boss.BossNet;

/**
 * T33 the fight music of a boss, by phases: <base>_intro once, then the loop of the phase (<base>_p1.._p3, looping), crossfading to the
 * next phase's loop when the server says (BossNet.MUSIC_*). Each part is our own tickable sound (the Music slider, paused with the game,
 * starts even with the slider at 0 so moving it later is heard), the volume driven here by the client tick with an equal-power curve.
 * A part with no file (the sound event missing or empty — the sound manager drops missing .ogg on load) is never played: the previous
 * phase's loop plays instead, and with no loop at all the old one-sound stub <base> (Iron's) as before T33. The music of a boss fades
 * out when the server stops it, when the boss is gone or farther than 128 blocks, and when the player dies (a respawn brings it back
 * through the server's late-viewer resume).
 */
public final class BossMusicClient {
    private BossMusicClient() {}

    private static final double RANGE = 128;
    /** Fading in when a part starts with nothing to crossfade from (intro, late viewer, stub). */
    private static final int FADE_IN = 20;
    /** Fading out when the client itself ends it (boss gone / far, the player died): the default music_fade_out_seconds. */
    private static final int FADE_AWAY = 40;

    private static final Map<Integer, Fight> PLAYING = new HashMap<>();
    /** Parts fading out after their fight was stopped / forgotten. */
    private static final List<Part> FADING = new ArrayList<>();

    /**
     * The phase parts are in sounds.json before the files exist (the sound designer cuts them when the owner sends the tracks): the
     * sound manager says «File pohsmp_core:sounds/music/<boss>_<part>.ogg does not exist» for each on every resource load. Those lines
     * (only those) are dropped; a missing part is simply not played (exists()).
     */
    static void quietMissingParts() {
        try {
            if (!(org.apache.logging.log4j.LogManager.getLogger(SoundManager.class.getName()) instanceof org.apache.logging.log4j.core.Logger l)) return;
            l.addFilter(new org.apache.logging.log4j.core.filter.AbstractFilter() {
                @Override
                public Result filter(org.apache.logging.log4j.core.LogEvent e) {
                    String s = e.getMessage() == null ? "" : e.getMessage().getFormattedMessage();
                    return MISSING_PART.matcher(s).find() ? Result.DENY : Result.NEUTRAL;
                }
            });
        } catch (Throwable t) {
            ru.pohsmp.core.PohCore.LOG.debug("[boss music] could not quiet the missing-part warnings: {}", t.toString());
        }
    }

    private static final java.util.regex.Pattern MISSING_PART =
            java.util.regex.Pattern.compile("pohsmp_core:sounds/music/(cult_leader|irina|aris|martin|ereb|ereb_hand)_(intro|p[123])\\.ogg does not exist");

    static void onMsg(BossNet.Msg m) {
        Fight f = PLAYING.get(m.a);
        switch (m.b) {
            case BossNet.MUSIC_STOP -> {
                if (f != null) f.fadeAll(m.d);
                PLAYING.remove(m.a);
            }
            case BossNet.MUSIC_START -> {
                if (f != null && f.alive()) return;
                f = fight(m);
                f.start(m.c);
            }
            case BossNet.MUSIC_PHASE -> {
                if (f == null || !f.alive()) fight(m).loop(m.c, Math.max(m.d, 1), true);
                else f.loop(m.c, m.d, false);
            }
            case BossNet.MUSIC_CUT -> fight(m).cut(m.c);
            case BossNet.MUSIC_FILTER -> {
                if (f != null) f.filter(m.c != 0);
            }
            default -> {}
        }
    }

    private static Fight fight(BossNet.Msg m) {
        Fight old = PLAYING.get(m.a);
        if (old != null && old.base.equals(m.s1)) return old;
        if (old != null) old.fadeAll(FADE_IN);
        Fight f = new Fight(m.a, m.s1);
        PLAYING.put(m.a, f);
        return f;
    }

    static void clear() {
        for (Fight f : PLAYING.values()) f.fadeAll(FADE_IN);
        PLAYING.clear();
    }

    @SubscribeEvent
    public static void onTick(TickEvent.ClientTickEvent e) {
        if (e.phase != TickEvent.Phase.END) return;
        Minecraft mc = Minecraft.getInstance();
        if (mc.isPaused()) return;   // the sound engine is paused too: the fades wait
        for (Iterator<Map.Entry<Integer, Fight>> it = PLAYING.entrySet().iterator(); it.hasNext(); ) {
            Fight f = it.next().getValue();
            var boss = mc.level == null ? null : mc.level.getEntity(f.entity);
            boolean away = boss == null || mc.player == null || !mc.player.isAlive() || boss.distanceToSqr(mc.player) > RANGE * RANGE;
            if (away) {
                f.fadeAll(FADE_AWAY);
                it.remove();
                continue;
            }
            f.tick();
        }
        for (Iterator<Part> it = FADING.iterator(); it.hasNext(); ) {
            Part p = it.next();
            p.step();
            if (p.isStopped()) it.remove();
        }
    }

    /** Is there a playable sound behind this event (registered, at least one file loaded)? */
    static boolean exists(ResourceLocation id) {
        SoundManager sm = Minecraft.getInstance().getSoundManager();
        WeighedSoundEvents ev = sm.getSoundEvent(id);
        return ev != null && ev.getSound(RandomSource.create()) != SoundManager.EMPTY_SOUND;
    }

    /** The music of one boss. */
    private static final class Fight {
        final int entity;
        final String base;
        /** has[0] intro, has[1..3] the phase loops; stub = the old one-sound <base>. */
        final boolean[] has = new boolean[BossMusicMath.PARTS.length];
        final boolean stubExists;
        Part current;
        /** The loop to go to when the intro ends. */
        int afterIntro;
        boolean filtered;

        Fight(int entity, String base) {
            this.entity = entity;
            this.base = base;
            ResourceLocation b = ResourceLocation.tryParse(base);
            for (int i = 0; i < has.length; i++) has[i] = b != null && exists(new ResourceLocation(b.getNamespace(), b.getPath() + BossMusicMath.PARTS[i]));
            stubExists = b != null && exists(b);
        }

        boolean alive() {
            return current != null && !current.isStopped();
        }

        boolean stub() {
            return BossMusicMath.useStub(has);
        }

        void start(int loop) {
            if (stub()) {
                play(-1, FADE_IN);
                return;
            }
            if (BossMusicMath.playIntro(loop, has)) {
                afterIntro = BossMusicMath.pickLoop(loop, has);
                play(BossMusicMath.INTRO, FADE_IN);
            } else play(BossMusicMath.pickLoop(loop, has), FADE_IN);
        }

        /** Crossfade to `loop` in `ticks` (or start it, fading in). */
        void loop(int loop, int ticks, boolean fresh) {
            if (stub()) {
                if (!alive()) play(-1, Math.max(ticks, 1));
                return;
            }
            int want = BossMusicMath.pickLoop(loop, has);
            if (current != null && current.part == BossMusicMath.INTRO && !current.isStopped()) {
                afterIntro = want;   // still in the intro: it hands over to this loop
                if (want == 1) return;
            }
            if (!fresh && current != null && !current.isStopped() && current.part == want) return;   // same loop (a fallback): goes on
            play(want, Math.max(ticks, 1));
        }

        void cut(int loop) {
            if (current != null) current.kill();
            current = null;
            for (Part p : FADING) if (p.entity == entity) p.kill();
            if (stub()) play(-1, 1);
            else play(BossMusicMath.pickLoop(loop, has), 1);
            if (current != null) current.set(1);
        }

        /** Start a part (-1 = the stub), fading the current one out in the same `ticks`. */
        private void play(int part, int ticks) {
            ResourceLocation id;
            if (part < 0) {
                if (!stubExists) return;   // no track, no stub (music.ereb): silence, no log
                id = ResourceLocation.tryParse(base);
            } else {
                ResourceLocation b = ResourceLocation.tryParse(base);
                id = new ResourceLocation(b.getNamespace(), b.getPath() + BossMusicMath.PARTS[part]);
            }
            if (current != null && !current.isStopped()) {
                current.ramp(0, ticks);
                FADING.add(current);
            }
            Part p = new Part(entity, part, SoundEvent.createVariableRangeEvent(id), part != BossMusicMath.INTRO);
            p.filtered = filtered;
            p.ramp(1, ticks);
            current = p;
            Minecraft.getInstance().getSoundManager().play(p);
        }

        void tick() {
            if (current == null) return;
            current.step();
            if (current.part == BossMusicMath.INTRO && current.started && !Minecraft.getInstance().getSoundManager().isActive(current)) {
                current.kill();
                current = null;
                play(afterIntro, 1);   // the intro ran out: straight into the loop (it was mixed to follow on)
                if (current != null) current.set(1);
            }
        }

        void filter(boolean on) {
            filtered = on;
            if (current != null) current.filter(on);
            for (Part p : FADING) if (p.entity == entity) p.filter(on);
        }

        void fadeAll(int ticks) {
            if (current != null && !current.isStopped()) {
                current.ramp(0, Math.max(ticks, 1));
                FADING.add(current);
            }
            current = null;
        }
    }

    /** One part of the track playing: its gain ramps from → to over len ticks (BossMusicMath.fadeGain). */
    static final class Part extends AbstractTickableSoundInstance {
        final int entity, part;
        float gain, from, to;
        int t, len;
        boolean started, filtered, filterApplied;

        Part(int entity, int part, SoundEvent ev, boolean loop) {
            super(ev, SoundSource.MUSIC, RandomSource.create());
            this.entity = entity;
            this.part = part;
            this.looping = loop;
            this.delay = 0;
            this.relative = true;
            this.attenuation = SoundInstance.Attenuation.NONE;
            this.volume = 0;
        }

        void ramp(float target, int ticks) {
            from = gain;
            to = target;
            t = 0;
            len = Math.max(1, ticks);
        }

        void set(float g) {
            gain = from = to = g;
            t = len = 1;
            applyVolume();
        }

        void filter(boolean on) {
            filtered = on;
            filterApplied = false;
        }

        void kill() {
            stop();
        }

        /** Advanced by BossMusicClient's client tick (not paused). */
        void step() {
            if (isStopped()) return;
            started = true;
            if (t < len) gain = BossMusicMath.fadeGain(from, to, ++t / (float) len);
            if (!filterApplied) filterApplied = BossMusicFilter.apply(this, filtered);
            applyVolume();
            if (to <= 0 && t >= len) stop();
        }

        private void applyVolume() {
            volume = gain * (filtered && !BossMusicFilter.works() ? 0.55f : 1f);   // no low-pass available: just quieter
        }

        @Override
        public void tick() {}   // the volume is set in step(); the engine reads it every tick

        @Override
        public boolean canStartSilent() {
            return true;   // starts at 0 (fade in), and with the Music slider at 0
        }
    }
}
