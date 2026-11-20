package ru.pohsmp.core.boss.client;

import java.util.HashMap;
import java.util.Map;
import net.minecraft.client.Minecraft;
import net.minecraft.client.resources.sounds.AbstractTickableSoundInstance;
import net.minecraft.client.resources.sounds.SoundInstance;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.RandomSource;
import ru.pohsmp.core.boss.BossNet;

/**
 * The fight music of a boss (pohsmp_core:music.<boss>, looped, the Music category): starts when the server says, fades out in 1 s
 * when it stops or the boss is gone / far. Replaces Iron's FireBossMusicHandler for the cult leader.
 */
public final class BossMusicClient {
    private BossMusicClient() {}

    private static final Map<Integer, Loop> PLAYING = new HashMap<>();

    static void onMsg(BossNet.Msg m) {
        Loop cur = PLAYING.get(m.a);
        if (m.b == 0) {
            if (cur != null) cur.fadeOut();
            PLAYING.remove(m.a);
            return;
        }
        if (cur != null && !cur.isStopped()) return;
        Loop l = new Loop(m.a, SoundEvent.createVariableRangeEvent(new ResourceLocation(m.s1)));
        PLAYING.put(m.a, l);
        Minecraft.getInstance().getSoundManager().play(l);
    }

    static void clear() {
        for (Loop l : PLAYING.values()) l.fadeOut();
        PLAYING.clear();
    }

    private static final class Loop extends AbstractTickableSoundInstance {
        private final int entity;
        private int fade = -1, in;

        Loop(int entity, SoundEvent ev) {
            super(ev, SoundSource.MUSIC, RandomSource.create());
            this.entity = entity;
            this.looping = true;
            this.delay = 0;
            this.relative = true;
            this.attenuation = SoundInstance.Attenuation.NONE;
            this.volume = 0.01f;
        }

        void fadeOut() {
            if (fade < 0) fade = 20;
        }

        @Override
        public void tick() {
            var mc = Minecraft.getInstance();
            var e = mc.level == null ? null : mc.level.getEntity(entity);
            if ((e == null || mc.player == null || e.distanceToSqr(mc.player) > 128 * 128) && fade < 0) fade = 20;
            if (fade >= 0) {
                volume = Math.max(0, fade / 20f);
                if (--fade <= 0) stop();
            } else if (in < 20) {
                volume = ++in / 20f;
            } else volume = 1;
        }
    }
}
