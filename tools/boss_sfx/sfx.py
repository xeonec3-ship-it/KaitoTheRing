"""Boss sound design kit (T36 boss sounds): numpy DSP + ffmpeg I/O.

Every sound is a mix of 2-4 layers: body (low weight), attack (transient / detail), tail and a convolution reverb.
Layers are CC0 recordings (tools/boss_sfx/fetch_cc0.py -> build/boss_sfx_cc0, see docs/licenses/sounds_bosses.md)
or synthesized here. Output: mono 44.1 kHz Vorbis (q3.5), peak-normalized.

Run: python tools/boss_sfx/build_all.py [boss ...]
"""
import os, subprocess, functools
import numpy as np

SR = 44100
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CC0 = os.environ.get("BOSS_SFX_CC0", os.path.join(ROOT, "build", "boss_sfx_cc0"))
OUT = os.path.join(ROOT, "src", "main", "resources", "assets", "pohsmp_core", "sounds", "boss")


# ------------------------------------------------------------------ I/O

USED = set()   # CC0 files used by the current boss (-> docs/licenses/sounds_bosses.md)


@functools.lru_cache(maxsize=None)
def _load(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         check=True, capture_output=True).stdout
    x = np.frombuffer(raw, dtype=np.float32).astype(np.float64)
    return x


def src(rel, start=0.0, dur=None):
    """A CC0 source (path relative to CC0 dir), optionally cut [start, start+dur], peak-normalized."""
    x = _load(os.path.join(CC0, rel))
    USED.add(rel)
    a = int(start * SR)
    b = len(x) if dur is None else min(len(x), a + int(dur * SR))
    y = x[a:b].copy()
    # trim leading silence
    nz = np.nonzero(np.abs(y) > 0.01 * (np.max(np.abs(y)) + 1e-9))[0]
    if len(nz):
        y = y[max(0, nz[0] - 64):]
    return norm(y)


def write(rel, x, peak=0.89, q=3.5, tail_db=-60):
    """Writes OUT/rel(.ogg): trims silent tail, fades, normalizes, encodes Vorbis mono."""
    x = np.asarray(x, dtype=np.float64)
    thr = np.max(np.abs(x)) * 10 ** (tail_db / 20) + 1e-12
    nz = np.nonzero(np.abs(x) > thr)[0]
    if len(nz):
        x = x[: nz[-1] + 1]
    x = fade(x, 0.002, 0.03)
    x = norm(x, peak)
    path = os.path.join(OUT, rel + ".ogg")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    pcm = x.astype(np.float32).tobytes()
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
                    "-c:a", "libvorbis", "-q:a", str(q), "-map_metadata", "-1", path], input=pcm, check=True)
    return path


def write_loop(rel, x, xfade=0.6, peak=0.6, q=3.5):
    """Seamless loop: the last xfade seconds are cross-faded into the head (equal power)."""
    n = int(xfade * SR)
    head, body, tail = x[:n], x[n:-n] if n else x, x[-n:]
    t = np.linspace(0, np.pi / 2, n)
    mixed = tail * np.cos(t) + head * np.sin(t)
    y = np.concatenate([mixed, body[: len(body)]]) if n else x
    y = norm(y, peak)
    path = os.path.join(OUT, rel + ".ogg")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
                    "-c:a", "libvorbis", "-q:a", str(q), "-map_metadata", "-1", path],
                   input=y.astype(np.float32).tobytes(), check=True)
    return path


# ------------------------------------------------------------------ basics

def secs(d):
    return int(round(d * SR))


def norm(x, peak=1.0):
    m = np.max(np.abs(x)) if len(x) else 0
    return x * (peak / m) if m > 0 else x


def db(x, g):
    return x * 10 ** (g / 20)


def pad(x, n):
    return np.concatenate([x, np.zeros(max(0, n - len(x)))]) if len(x) < n else x


def fade(x, fin=0.005, fout=0.05):
    x = x.copy()
    a, b = min(len(x), secs(fin)), min(len(x), secs(fout))
    if a:
        x[:a] *= np.linspace(0, 1, a)
    if b:
        x[-b:] *= np.linspace(1, 0, b) ** 2
    return x


def cut(x, start, dur=None):
    a = secs(start)
    return x[a:] if dur is None else x[a:a + secs(dur)]


def speed(x, r):
    """Resample by ratio r (r>1 = higher and shorter, like Minecraft pitch)."""
    if r == 1:
        return x
    n = int(len(x) / r)
    return np.interp(np.arange(n) * r, np.arange(len(x)), x)


def semis(x, s):
    return speed(x, 2 ** (s / 12))


def rev(x):
    return x[::-1].copy()


def env_exp(n, tau):
    return np.exp(-np.arange(n) / (tau * SR))


def adsr(n, a=0.01, d=0.1, s=0.7, r=0.2):
    a, d, r = secs(a), secs(d), secs(r)
    sus = max(0, n - a - d - r)
    e = np.concatenate([np.linspace(0, 1, a), np.linspace(1, s, d), np.full(sus, s), np.linspace(s, 0, r)])
    return pad(e, n)[:n]


def mix(*layers, length=None):
    """layers: (signal, offset_seconds, gain_db) or signal."""
    ls = []
    for L in layers:
        if isinstance(L, np.ndarray):
            L = (L, 0.0, 0.0)
        elif len(L) == 2:
            L = (L[0], L[1], 0.0)
        ls.append(L)
    n = max(secs(o) + len(s) for s, o, g in ls) if length is None else secs(length)
    out = np.zeros(n)
    for s, o, g in ls:
        a = secs(o)
        if a >= n:
            continue
        seg = s[: n - a]
        out[a:a + len(seg)] += db(seg, g)
    return out


# ------------------------------------------------------------------ filters (zero-phase FFT, fine for one-shots)

def _fft_filter(x, resp):
    n = len(x)
    N = 1 << int(np.ceil(np.log2(max(2, n * 2))))
    X = np.fft.rfft(x, N)
    f = np.fft.rfftfreq(N, 1 / SR)
    return np.fft.irfft(X * resp(f), N)[:n]


def lp(x, fc, order=2):
    return _fft_filter(x, lambda f: 1 / np.sqrt(1 + (f / fc) ** (2 * order)))


def hp(x, fc, order=2):
    return _fft_filter(x, lambda f: 1 / np.sqrt(1 + (fc / np.maximum(f, 1e-3)) ** (2 * order)))


def bp(x, lo, hi, order=2):
    return hp(lp(x, hi, order), lo, order)


def peak_eq(x, fc, gain_db, q=1.0):
    g = 10 ** (gain_db / 20) - 1
    return _fft_filter(x, lambda f: 1 + g * np.exp(-0.5 * (np.log2(np.maximum(f, 1) / fc) * q * 2) ** 2))


def sweep_filter(x, f0, f1, width=1.0, hop=512):
    """Time-varying band-pass (center f0 -> f1, log), overlap-add STFT. width in octaves."""
    win = 2048
    w = np.hanning(win)
    n = len(x)
    out = np.zeros(n + win)
    norm_ = np.zeros(n + win)
    xp = np.concatenate([x, np.zeros(win)])
    f = np.fft.rfftfreq(win, 1 / SR)
    frames = max(1, (n) // hop + 1)
    for i in range(frames):
        a = i * hop
        t = a / max(1, n - 1)
        fc = f0 * (f1 / f0) ** min(1.0, t)
        resp = np.exp(-0.5 * (np.log2(np.maximum(f, 1) / fc) / (width / 2)) ** 2)
        seg = np.fft.irfft(np.fft.rfft(xp[a:a + win] * w) * resp, win)
        out[a:a + win] += seg * w
        norm_[a:a + win] += w * w
    return (out / np.maximum(norm_, 1e-6))[:n]


def drive(x, k=2.0):
    """Soft saturation."""
    return np.tanh(k * x) / np.tanh(k)


def bitcrush_ring(x, f):
    t = np.arange(len(x)) / SR
    return x * np.sin(2 * np.pi * f * t)


# ------------------------------------------------------------------ reverb

_rng = np.random.default_rng(36)


def rng(seed):
    global _rng
    _rng = np.random.default_rng(seed)


def reverb(x, t60=1.6, wet=0.3, pre=0.015, bright=4000, size=1.0):
    """Convolution with an exponentially decaying, darkening noise IR."""
    n = secs(t60 * 1.1)
    noise = _rng.standard_normal(n)
    e = np.exp(-6.9 * np.arange(n) / (t60 * SR))
    ir = lp(noise, bright, 1) * e
    # early reflections
    for d, g in ((0.011, 0.5), (0.019, 0.4), (0.027 * size, 0.3), (0.041 * size, 0.25)):
        k = secs(d)
        if k < n:
            ir[k] += g * (1 if _rng.random() > 0.5 else -1)
    ir = np.concatenate([np.zeros(secs(pre)), ir])
    N = 1 << int(np.ceil(np.log2(len(x) + len(ir))))
    y = np.fft.irfft(np.fft.rfft(x, N) * np.fft.rfft(ir, N), N)[: len(x) + len(ir)]
    y = norm(y, np.max(np.abs(x)) * 0.9)
    return pad(x, len(y)) * (1 - wet * 0.5) + y * wet


# ------------------------------------------------------------------ synthesis

def t_axis(d):
    return np.arange(secs(d)) / SR


def noise(d, color="white"):
    x = _rng.standard_normal(secs(d))
    if color == "pink":
        x = _fft_filter(x, lambda f: 1 / np.sqrt(np.maximum(f, 20) / 20))
    elif color == "brown":
        x = _fft_filter(x, lambda f: 20 / np.maximum(f, 20))
    return norm(x)


def sine(f0, d, f1=None, phase=0.0):
    t = t_axis(d)
    if f1 is None or f1 == f0:
        return np.sin(2 * np.pi * f0 * t + phase)
    k = np.log(f1 / f0) / max(d, 1e-6)
    return np.sin(2 * np.pi * f0 * (np.exp(k * t) - 1) / k + phase)


def saw(f, d, detune=0.0, voices=1):
    t = t_axis(d)
    out = np.zeros(len(t))
    for v in range(voices):
        fv = f * (1 + detune * (v - (voices - 1) / 2))
        out += 2 * ((t * fv + _rng.random()) % 1.0) - 1
    return out / voices


def whoosh(d=0.35, f0=300, f1=1800, width=1.6, curve=2.2, peak_at=0.55, color="pink"):
    """Air swish: band-passed noise sweeping f0->f1 with a swelling envelope."""
    x = noise(d, color)
    x = sweep_filter(x, f0, f1, width)
    t = np.linspace(0, 1, len(x))
    e = np.where(t < peak_at, (t / peak_at) ** curve, ((1 - t) / (1 - peak_at)) ** 1.5)
    return norm(x * e)


def thump(f0=70, f1=38, d=0.5, tau=0.12, click=0.3):
    """Low body hit (sub sine drop + click)."""
    x = sine(f0, d, f1) * env_exp(secs(d), tau)
    c = hp(noise(0.02), 1500) * env_exp(secs(0.02), 0.003) * click
    return norm(mix(x, c))


def rumble(d=2.0, fc=90, tau=None):
    x = lp(noise(d, "brown"), fc, 3)
    if tau:
        x *= env_exp(len(x), tau)
    return norm(x)


def bell(f, d=2.0, partials=((1, 1, 1), (2.76, .5, .6), (5.4, .3, .4), (8.93, .2, .25)), tau=0.8, detune=0.0):
    """Inharmonic struck partials (glass / metal). partials: (ratio, amp, decay factor)."""
    t = t_axis(d)
    out = np.zeros(len(t))
    for r, a, k in partials:
        fr = f * r * (1 + detune * _rng.uniform(-1, 1))
        if fr > SR / 2.2:
            continue
        out += a * np.sin(2 * np.pi * fr * t + _rng.random() * 6.28) * np.exp(-t / (tau * k))
    return norm(out)


def glass_ping(f=2400, d=1.2, tau=0.35):
    return bell(f, d, ((1, 1, 1), (2.32, .6, .7), (4.25, .45, .5), (6.63, .3, .35), (9.38, .2, .25)), tau, detune=0.004)


def metal_ring(f=420, d=1.8, tau=0.6):
    return bell(f, d, ((1, 1, 1), (1.47, .7, .8), (2.09, .6, .7), (2.56, .4, .5), (3.39, .35, .4), (4.17, .25, .3)), tau, detune=0.003)


def shimmer(d=1.5, base=1800, count=14, spread=1.0, tau=0.25):
    """Many tiny glass pings scattered in time (butterflies, shards)."""
    out = np.zeros(secs(d))
    for _ in range(count):
        p = glass_ping(base * 2 ** _rng.uniform(-spread / 2, spread / 2), 0.6, tau * _rng.uniform(0.5, 1.2))
        o = secs(_rng.uniform(0, d * 0.8))
        seg = p[: len(out) - o] * _rng.uniform(0.3, 1.0)
        out[o:o + len(seg)] += seg
    return norm(out)


def crackle(d=1.5, rate=40, tau=0.004, fc=3000):
    """Fire crackle: random clicks."""
    out = np.zeros(secs(d))
    k = int(rate * d)
    for _ in range(k):
        o = _rng.integers(0, len(out) - 400)
        c = _rng.standard_normal(400) * env_exp(400, tau * _rng.uniform(0.5, 2)) * _rng.uniform(0.2, 1)
        out[o:o + 400] += c
    return norm(hp(out, fc * 0.3) + 0.0)


def fire_roar(d=2.0, fc=500):
    """Whooshy flame body: low-passed noise with slow amplitude flutter + crackle."""
    x = lp(noise(d, "pink"), fc, 2)
    t = t_axis(d)
    flutter = 0.6 + 0.4 * lp(_rng.standard_normal(len(t)), 6, 1) * 30
    x = norm(x * np.clip(flutter, 0.1, 2))
    return norm(mix(x, (crackle(d, 30), 0, -10)))


def whisper(d=1.5, syll=6, base=1.0):
    """Unintelligible whisper: noise through moving vowel formants with syllable gating."""
    x = noise(d, "white")
    n = len(x)
    out = np.zeros(n)
    forms = [(700, 1200), (400, 2200), (300, 900), (500, 1700), (350, 2600)]
    bounds = np.sort(_rng.uniform(0, 1, syll * 2)) * n
    for i in range(0, len(bounds) - 1, 2):
        a, b = int(bounds[i]), int(bounds[i + 1])
        if b - a < secs(0.09):   # shorter bursts read as clicks
            continue
        f1, f2 = forms[_rng.integers(len(forms))]
        seg = x[a:b]
        seg = bp(seg, f1 * base * 0.7, f1 * base * 1.3) + 0.7 * bp(seg, f2 * base * 0.8, f2 * base * 1.2)
        seg = seg + 0.12 * bp(x[a:b], 4000, 7000)   # sibilance (soft)
        out[a:b] += seg * np.hanning(b - a)
    return norm(lp(out, 7500))


def drone(f=55, d=4.0, voices=5, detune=0.006, fc=400):
    x = saw(f, d, detune, voices)
    x = lp(x, fc, 2)
    return norm(x)


def heartbeat(d=1.0):
    a = thump(60, 40, 0.35, 0.06, 0.05)
    return norm(mix((a, 0), (a, 0.22, -5), length=d))


def string_creak(d=0.6, f0=180, f1=260, rough=40):
    """Taut thread / rope stretch: a buzzing tone with stick-slip roughness."""
    t = t_axis(d)
    k = np.log(f1 / f0) / d
    ph = 2 * np.pi * f0 * (np.exp(k * t) - 1) / k
    stick = (np.sin(2 * np.pi * rough * t) > 0.3).astype(float)
    stick = lp(stick, 200, 1)
    x = (np.sin(ph) + 0.5 * np.sin(2 * ph) + 0.3 * np.sin(3.01 * ph)) * (0.4 + stick)
    x = bp(x + 0.3 * noise(d) * stick, 150, 4000)
    return norm(x * adsr(len(x), 0.03, 0.1, 0.8, 0.1))


def snap(f=3000):
    """Thread snap: tight click + short ringing."""
    c = hp(noise(0.03), 2000) * env_exp(secs(0.03), 0.002)
    r = sine(f, 0.25, f * 0.7) * env_exp(secs(0.25), 0.04)
    return norm(mix((c, 0), (r, 0, -10)))


def hiss(d=1.5, fc=5000, tau=0.5):
    """Steam / quench hiss."""
    x = hp(noise(d), fc * 0.6) * env_exp(secs(d), tau)
    return norm(x * adsr(len(x), 0.01, 0.05, 1, 0.2))


def variants(fn, k, seed):
    """k variants: fn(i) with deterministic seeds."""
    out = []
    for i in range(k):
        rng(seed * 100 + i)
        out.append(fn(i))
    return out


def uni(a, b, n=None):
    """Seeded uniform random (the generator of the last rng(seed))."""
    return _rng.uniform(a, b, n)
