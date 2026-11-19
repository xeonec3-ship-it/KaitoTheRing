#!/usr/bin/env python3
"""
«Безмолвные врата» — звук попадания наведённого луча по врагу (владелец 19.11: «сделай звуки ударов у врат по врагам»).
Синтез, моно 44.1 кГц (позиционный звук Minecraft), три вариации -> sounds/spell/gate_hit1..3.ogg:
  * «свист» луча сверху: короткий нисходящий тон с тонким шумом (0–60 мс до удара);
  * удар: глухой низкий толчок (синус 70→38 Гц) + щелчок-трескотня;
  * хрустальный отзвук: несколько неровных гармоник (колокольчик/аметист), длинный спад;
  * мягкий «шипящий» хвост света (полосовой шум), ~0.9 с.
Запуск: python3 tools/gen_gate_hit_sound.py   (нужен ffmpeg)
"""
import os, subprocess, tempfile, wave
import numpy as np

SR = 44100
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src', 'main', 'resources', 'assets', 'pohsmp_core', 'sounds', 'spell')


def env(t, a, d):
    return np.where(t < a, t / max(a, 1e-6), np.exp(-(t - a) / d))


def bandnoise(n, lo, hi, rnd):
    x = rnd.standard_normal(n)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    X[(f < lo) | (f > hi)] = 0
    y = np.fft.irfft(X, n)
    return y / (np.abs(y).max() + 1e-9)


def make(seed, pitch):
    rnd = np.random.default_rng(seed)
    L = 1.15
    n = int(SR * L)
    t = np.arange(n) / SR
    hit = 0.06
    out = np.zeros(n)
    # свист луча: 2400→900 Гц до удара
    w = t < hit
    tw = t[w]
    f = (2400 - 1500 * tw / hit) * pitch
    out[w] += 0.18 * np.sin(2 * np.pi * np.cumsum(f) / SR) * (tw / hit) ** 2
    out[w] += 0.10 * bandnoise(n, 3000, 9000, rnd)[w] * (tw / hit) ** 2
    th = np.clip(t - hit, 0, None)
    on = t >= hit
    # удар: низкий толчок
    f0 = 38 + 32 * np.exp(-th / 0.04)
    out += on * 0.85 * np.sin(2 * np.pi * np.cumsum(f0 * on) / SR) * env(th, 0.003, 0.11)
    # щелчок/треск
    out += on * 0.55 * bandnoise(n, 800, 7000, rnd) * env(th, 0.001, 0.018)
    out += on * 0.20 * bandnoise(n, 2000, 12000, rnd) * env(th, 0.002, 0.06) * (rnd.random(n) < 0.25)
    # хрустальный отзвук: неровные гармоники
    base = 880 * pitch
    for k, (mult, amp, dec) in enumerate([(1.0, 0.22, 0.45), (2.76, 0.14, 0.30), (5.4, 0.08, 0.18), (8.93, 0.05, 0.12), (1.5, 0.08, 0.6)]):
        det = 1 + rnd.uniform(-0.004, 0.004)
        out += on * amp * np.sin(2 * np.pi * base * mult * det * th + rnd.uniform(0, 6.28)) * env(th, 0.004, dec)
    # шипящий хвост света
    out += on * 0.12 * bandnoise(n, 4000, 11000, rnd) * env(th, 0.02, 0.28)
    # конец без щелчка
    fade = np.clip((L - t) / 0.08, 0, 1)
    out *= fade
    out /= np.abs(out).max() + 1e-9
    return (out * 0.92 * 32767).astype(np.int16)


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    for i, (seed, pitch) in enumerate([(31, 1.0), (32, 0.89), (33, 1.12)], 1):
        data = make(seed, pitch)
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tf:
            path = tf.name
        with wave.open(path, 'wb') as wv:
            wv.setnchannels(1); wv.setsampwidth(2); wv.setframerate(SR); wv.writeframes(data.tobytes())
        dst = os.path.join(OUT, f'gate_hit{i}.ogg')
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', path, '-c:a', 'libvorbis', '-q:a', '5', '-ac', '1', dst], check=True)
        os.remove(path)
        print('wrote sounds/spell/gate_hit%d.ogg' % i)
