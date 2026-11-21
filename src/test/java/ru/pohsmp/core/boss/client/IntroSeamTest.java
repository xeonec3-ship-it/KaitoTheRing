package ru.pohsmp.core.boss.client;

import static org.junit.jupiter.api.Assertions.*;

import com.mojang.blaze3d.audio.OggAudioStream;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.file.Files;
import java.nio.file.Path;
import net.minecraft.client.sounds.LoopingAudioStream;
import org.junit.jupiter.api.Test;

/** T33: intro + loop through Minecraft's own Ogg decoder and our IntroThenLoop — byte-exact, no gap at the seams (real files). */
class IntroSeamTest {
    static final Path DIR = Path.of("src/main/resources/assets/pohsmp_core/sounds/music");

    static byte[] all(byte[] ogg) throws Exception {
        try (OggAudioStream s = new OggAudioStream(new ByteArrayInputStream(ogg))) {
            ByteBuffer b = s.readAll();
            byte[] out = new byte[b.remaining()];
            b.get(out);
            return out;
        }
    }

    static short sample(byte[] a, int frame, int ch) {
        return ByteBuffer.wrap(a, frame * 4 + ch * 2, 2).order(ByteOrder.LITTLE_ENDIAN).getShort();
    }

    static int jump(byte[] a, byte[] b) { // last frame of a → first of b
        int fa = a.length / 4 - 1, m = 0;
        for (int c = 0; c < 2; c++) m = Math.max(m, Math.abs(sample(a, fa, c) - sample(b, 0, c)));
        return m;
    }

    static int typical(byte[] a) { // 99th percentile of |Δ| between neighbour frames
        int n = a.length / 4 - 1;
        int[] d = new int[n];
        for (int i = 0; i < n; i++) d[i] = Math.abs(sample(a, i + 1, 0) - sample(a, i, 0));
        java.util.Arrays.sort(d);
        return d[(int) (n * 0.99)];
    }

    @Test
    void seams() throws Exception {
        for (String id : new String[] {"cult_leader", "irina", "aris", "martin", "ereb", "ereb_hand"}) {
            if (!Files.exists(DIR.resolve(id + "_intro.ogg")) || !Files.exists(DIR.resolve(id + "_p1.ogg"))) continue;   // not cut yet
            byte[] introOgg = Files.readAllBytes(DIR.resolve(id + "_intro.ogg")), p1Ogg = Files.readAllBytes(DIR.resolve(id + "_p1.ogg"));
            byte[] intro = all(introOgg), p1 = all(p1Ogg);
            BossMusicClient.IntroThenLoop s = new BossMusicClient.IntroThenLoop(new OggAudioStream(new ByteArrayInputStream(introOgg)),
                    new LoopingAudioStream(OggAudioStream::new, new ByteArrayInputStream(p1Ogg)));
            ByteArrayOutputStream got = new ByteArrayOutputStream();
            int want = intro.length + p1.length * 2 + p1.length / 2;
            while (got.size() < want) {
                ByteBuffer b = s.read(44100 * 4);   // ~ the channel's streaming chunk
                assertTrue(b.hasRemaining(), "never empty");
                byte[] x = new byte[b.remaining()];
                b.get(x);
                got.write(x);
            }
            byte[] g = got.toByteArray();
            ByteArrayOutputStream exp = new ByteArrayOutputStream();
            exp.write(intro);
            exp.write(p1);
            exp.write(p1);
            exp.write(p1);
            byte[] e = exp.toByteArray();
            for (int i = 0; i < want; i++) if (g[i] != e[i]) fail(id + ": differs at byte " + i + " (intro " + intro.length + ", p1 " + p1.length + ")");
            System.out.printf("%s: intro %.3f s, p1 %.3f s, byte-exact intro+p1+p1+.. ; jump intro->p1 %d, p1 end->start %d, typical(99%%) %d%n",
                    id, intro.length / 4 / 44100.0, p1.length / 4 / 44100.0, jump(intro, p1), jump(p1, p1), typical(p1));
            assertTrue(jump(intro, p1) <= 2 * typical(p1) && jump(p1, p1) <= 2 * typical(p1), id + ": a click at a seam");
            s.close();
        }
    }
}
