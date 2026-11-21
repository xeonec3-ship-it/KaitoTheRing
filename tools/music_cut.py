#!/usr/bin/env python3
"""
Нарезка музыки боссов по фазам (T33): вступление + 3 бесшовные петли (p1 спокойная, p2 основная, p3 кульминация).

Исходник (mp4/mp3/wav, что угодно, что читает ffmpeg) передаётся ТОЛЬКО аргументом — скрипт его не копирует.

  python3 tools/music_cut.py analyze SRC [--from 0:30 --to 2:00]
        огибающая громкости по 4 с и темп (автокорреляция онсетов) — чтобы выбрать окна фаз.
  python3 tools/music_cut.py cut ID SRC [--p1 A-B] [--p2 A-B] [--p3 A-B] [--intro N] [--q 1.5] [--no-demo]
        нарезка. Для известных ID (cult_leader, irina, martin, ereb, ereb_hand, aris) окна поиска петель заданы в PRESETS;
        для нового босса без пресета окна берутся автоматически (трек делится на трети: p1 — первая, p2 — вторая, p3 — третья).
        --pN A-B — окно ПОИСКА петли (м:сс-м:сс), петля 30–60 с выбирается внутри него;
        --pN A=B (через «=») — задать петлю жёстко: начало A, конец B (оба уточняются в ±70 мс).
        --intro-from T — вступление с T с исходника до начала p1 (начало p1 тогда ищется в T+5…T+15 с).
  Арис, когда будет файл:  python3 tools/music_cut.py cut aris путь/к/Old_Iron_King.mp4

Зависимости: ffmpeg (libvorbis, libmp3lame), pip install numpy scipy soundfile librosa.

Как ищется петля (find_loop): признаки — лог-мел 64 полосы + хрома (z-нормированы, кадр 23 мс). Для всех пар (начало s,
длина L = 30–60 с) — сходство кадров в ±3 с вокруг s и вокруг s+L (что звучит до и после конца петли ≈ что звучит до и
после её начала); 80 лучших → конец подгоняется по огибающей онсетов (2.9 мс) в пределах ±½ доли, чтобы ритм после конца
совпал с ритмом после начала (доля — из автокорреляции онсетов, tempo_grid); итог = ½·сходство(±3 с) + ½·сходство(±0.5 с)
+ 0.3·корреляция онсетов − штраф за разницу громкости у стыка + чуть за длину. Точки резки — на 30 мс раньше места
(кроссфейд ложится перед атакой) и на нулевой переход. Петля = src[s:e], последние 40 мс — кроссфейд равной мощности
src[e−40мс:e] → src[s−40мс:s], так что на переходе конец→начало звучит ровно то, что было в исходнике перед s.
Для сравнения в отчёте — «естественное» сходство того же трека с самим собой через 1 и 2 с (natural_similarity_1s_2s):
сходство на стыке не ниже него = стык не резче обычного хода музыки.
Вступление = src[intro_from : s1] (s1 — начало p1), т.е. переходит в p1 без шва; без intro_from — src[s1−N : s1] с fade-in 0.4 с.
Громкость: интегральная громкость p1+p2+p3 (ffmpeg loudnorm, проход 1) → одно линейное усиление на все 4 файла (проход 2
как linear), так что у всех боссов −16 LUFS, p1 остаётся тише p3, а стыки не портятся динамической обработкой.
Проверка стыков (seam_check) — по декодированному .ogg (как услышит игра) и до кодека: RMS/спектр последних и первых
100 мс, спектр начала петли против настоящего продолжения в исходнике, скачок огибающей 10 мс, ВЧ-всплеск (щелчок).
Выход: src/main/resources/assets/pohsmp_core/sounds/music/<id>_{intro,p1,p2,p3}.ogg (Vorbis 44.1 кГц стерео, q1.5 ≈ 80 кбит/с),
демо docs/media/audio/<id>_phases.mp3 (64 кбит/с: вступление → p1×2 → кроссфейд 1.5 с → p2×2 → кроссфейд → p3×2 → 2 с
затухание), отчёт JSON — в stdout и --report.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

import numpy as np
import soundfile as sf

SR = 44100
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_OGG = os.path.join(ROOT, 'src/main/resources/assets/pohsmp_core/sounds/music')
OUT_DEMO = os.path.join(ROOT, 'docs/media/audio')
TARGET_LUFS = -16.0
XFADE = 0.040                   # кроссфейд внутри петли, с

# Окна поиска петель (секунды исходника); intro — длина вступления, если нет intro_from. Подобраны по огибающей/структуре трека (см. отчёт в docs/inbox).
# intro_from — откуда в исходнике начинается вступление (начало музыки); тогда начало p1 ищется в intro_from + 5…15 с,
# и вступление — это ровно исходник от intro_from до начала p1 (переход вступление→p1 = естественное продолжение).
PRESETS = {
    'cult_leader': dict(intro_from=0.0, p1=(0, 80), p2=(78, 170), p3=(256, 420)),
    'irina':       dict(intro_from=0.0, p1=(0, 76), p2=(74, 145), p3_fixed=(165.5, 231.91)),   # p3 = игровая петля 66.41 с
    'martin':      dict(intro_from=5.4, p1=(5, 82), p2=(78, 176), p3=(288, 345)),
    'ereb':        dict(intro_from=0.0, p1=(0, 54), p2=(54, 120), p3=(115, 190)),
    'ereb_hand':   dict(intro=15, p1=(10, 104), p2=(110, 172), p3=(185, 255)),
    'aris':        dict(intro_from=0.0),   # окна — автоматически (трети трека), пока файла нет
}


def tsec(s):
    s = str(s).strip()
    if ':' in s:
        m, x = s.split(':')
        return int(m) * 60 + float(x)
    return float(s)


def tc(t):
    return f'{int(t // 60)}:{t % 60:06.3f}'


def load(src):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', src, '-vn', '-ac', '2', '-ar', str(SR), '-f', 'f32le', '-'],
                         check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).astype(np.float64)


FSR, FHOP = 22050, 512           # признаки для самоподобия: 23 мс
OHOP = 128                       # онсеты для темпа/подгонки: 2.9 мс на 44.1 кГц


class Feat:
    """Признаки трека: лог-мел 64 полосы + хрома (z-нормированы по полосам, кадр нормирован) на 22.05 кГц hop 512;
    огибающая онсетов (spectral flux) на 44.1 кГц hop 128 — для темпа и точной подгонки конца петли."""

    def __init__(self, x):
        import librosa
        y = librosa.resample(x.mean(1).astype(np.float32), orig_sr=SR, target_sr=FSR)
        mel = librosa.power_to_db(librosa.feature.melspectrogram(y=y, sr=FSR, hop_length=FHOP, n_mels=64, fmax=11000))
        chroma = librosa.feature.chroma_stft(y=y, sr=FSR, hop_length=FHOP)
        z = lambda A: (A - A.mean(1, keepdims=True)) / (A.std(1, keepdims=True) + 1e-9)
        F = np.vstack([z(mel), z(chroma) * np.sqrt(64 / 12)]).T       # хрома весит столько же, сколько мел
        F /= np.linalg.norm(F, axis=1, keepdims=True) + 1e-9
        self.F = F.astype(np.float32)
        self.db = 10 * np.log10(np.mean(librosa.db_to_power(mel), 0) + 1e-12)       # громкость кадра, дБ
        fine = librosa.onset.onset_strength(y=x.mean(1).astype(np.float32), sr=SR, hop_length=OHOP)
        self.fine = np.convolve(fine, np.hanning(7) / np.hanning(7).sum(), 'same')     # сглаживание ~15 мс
        self.fps = FSR / FHOP
        self.ofps = SR / OHOP


def tempo_grid(feat, t0, t1):
    """Доля и такт по автокорреляции онсетов в окне: доля — сильнейший пик 0.4–1.2 с, такт — сильнейший из 2,3,4,6,8 долей
    (1.2–6.5 с); период такта уточняется по пику автокорреляции на лаге ~24 с (параболой) и делится на число тактов."""
    from scipy.signal import find_peaks
    r = feat.ofps
    o = feat.fine[int(t0 * r):int(t1 * r)].astype(np.float64)
    o = o - np.convolve(o, np.ones(201) / 201, 'same')
    n = len(o)
    ac = np.correlate(o, o, 'full')[n - 1:] / (np.arange(n, 0, -1)) if n < 60000 else None
    if ac is None:   # длинное окно — через FFT
        f = np.fft.rfft(o, 2 * n)
        ac = np.fft.irfft(f * np.conj(f))[:n] / np.arange(n, 0, -1)
    ac = ac / ac[0]

    def peak_near(lag, tol):
        lo, hi = int(lag - tol), int(lag + tol) + 1
        k = lo + int(np.argmax(ac[lo:hi]))
        a_, b_, c_ = ac[k - 1:k + 2]
        return k + 0.5 * (a_ - c_) / (a_ - 2 * b_ + c_ + 1e-12), float(ac[k])

    pk, _ = find_peaks(ac[:int(7 * r)])
    beat_c = [p for p in pk if 0.4 * r <= p <= 1.2 * r]   # 50–150 уд/мин
    # «гребёнка»: доля, у которой пики и на 2, 3, 4 долях — сильнее (иначе ловится восьмая/триоль)
    comb = lambda p: sum(peak_near(m * p, 0.02 * m * p)[1] for m in (1, 2, 3, 4) if m * p < len(ac) - 2)
    beat = max(beat_c, key=comb)
    beat, beat_v = peak_near(beat, 3)
    best = None
    for m in (2, 3, 4, 6, 8):
        if 1.2 * r <= m * beat <= 6.5 * r:
            lag, v = peak_near(m * beat, 0.03 * m * beat)
            if best is None or v > best[2] * 1.05:
                best = (m, lag, v)
    m, bar, bar_v = best
    nb = max(1, int(round(24 * r / bar)))
    if nb * bar < n * 0.6:
        lag, _ = peak_near(nb * bar, 0.02 * bar)
        bar = lag / nb
    return dict(bpm=60 * r / (bar / m), beats_per_bar=m, bar=bar / r, pulse=round(beat_v, 3), bar_pulse=round(bar_v, 3))


def onset_align(feat, s, e, R=0.06):
    """Сдвиг конца (с) ±R, при котором ритм после конца лучше всего совпадает с ритмом после начала (окно −1…+4 с)."""
    f, r = feat.fine, feat.ofps
    si, ei = int(s * r), int(e * r)
    w0, w1, Rk = int(1 * r), int(4 * r), int(R * r)
    ref = f[si - w0:si + w1] - f[si - w0:si + w1].mean()
    best = (-2.0, 0)
    for lag in range(-Rk, Rk + 1):
        o = f[ei + lag - w0:ei + lag + w1]
        if len(o) != len(ref):          # у самого края трека
            continue
        o = o - o.mean()
        c = float(np.dot(ref, o) / (np.linalg.norm(ref) * np.linalg.norm(o) + 1e-9))
        best = max(best, (c, lag))
    return best[1] / r, best[0]


def short_check(feat, s, L):
    """Ближний стык: сходство мел+хрома в ±0.5 с и разница громкости за 0.25 с до/после (конец против начала), дБ."""
    fps = feat.fps
    i, j, w, q = int(s * fps), int((s + L) * fps), int(0.5 * fps), int(0.25 * fps)
    sim = float(np.mean(np.einsum('ij,ij->i', feat.F[i - w:i + w], feat.F[j - w:j + w])))
    db = feat.db
    dl = max(abs(db[i - q:i].mean() - db[j - q:j].mean()), abs(db[i:i + q].mean() - db[j:j + q].mean()))
    return sim, float(dl)


def ctx_sim(feat, L, a, b):
    """Для начал s ∈ [a, b−L) (кадры): среднее косинусное сходство кадров s+k и s+L+k, k ∈ [−3 с, +3 с) —
    насколько звучание вокруг конца петли совпадает со звучанием вокруг её начала."""
    F, W = feat.F, int(3.0 * feat.fps)
    rng = np.arange(a, b - L)
    if len(rng) == 0:
        return rng, np.zeros(0)
    d = np.einsum('ij,ij->i', F[rng[0] - W:rng[-1] + W], F[rng[0] - W + L:rng[-1] + W + L])
    cs = np.concatenate([[0], np.cumsum(d)])
    return rng, (cs[2 * W:2 * W + len(rng)] - cs[:len(rng)]) / (2 * W)


def find_loop(x, feat, t0, t1, lmin=30.0, lmax=60.0, fixed=None, srange=None):
    """1) все пары (начало, длина 30–60 с) с шагом 23 мс → сходство мел+хрома в ±3 с вокруг начала и конца;
    2) 80 лучших (без дублей) → подгонка конца по онсетам в пределах ±½ доли (ритм после конца = ритм после начала);
    3) итог = сходство + 0.3·корреляция онсетов + 0.03·(длиннее лучше); точки — на 30 мс раньше и на нулевой переход."""
    g = tempo_grid(feat, t0, t1)
    fps, W = feat.fps, int(3.0 * feat.fps)
    a, b = max(int(t0 * fps), W + 1), min(int(t1 * fps), len(feat.F) - W - 1)
    base = {k: round(float(np.median(ctx_sim(feat, int(k * fps), a, b)[1])), 3) for k in (1, 2)}
    raw = []
    if fixed:
        i0, L0 = int(fixed[0] * fps), int((fixed[1] - fixed[0]) * fps)
        for L in range(L0 - 3, L0 + 4):
            rng, sc = ctx_sim(feat, L, i0 - 3, i0 + 4 + L)
            j = int(np.argmax(sc))
            raw.append((float(sc[j]), rng[j], L))
    else:
        for L in range(int(lmin * fps), int(lmax * fps) + 1):
            rng, sc = ctx_sim(feat, L, a, b)
            if srange:
                keep = (rng >= srange[0] * fps) & (rng <= srange[1] * fps)
                rng, sc = rng[keep], sc[keep]
            if len(sc) == 0:
                continue
            for j in np.argsort(sc)[-3:]:
                raw.append((float(sc[j]), int(rng[j]), L))
    raw.sort(reverse=True)
    pool = []
    for c in raw:
        if all(abs(c[1] - q[1]) > fps or abs(c[2] - q[2]) > fps for q in pool):
            pool.append(c)
        if len(pool) >= 80:
            break
    beat = g['bar'] / g['beats_per_bar']
    cands = []
    for sim, i, L in pool:
        s, L_ = i / fps, L / fps
        lag, corr = onset_align(feat, s, s + L_, min(0.15, beat / 2))
        Lt = L_ + lag
        near, dl = short_check(feat, s, Lt)
        score = 0.5 * sim + 0.5 * near + 0.3 * corr - 0.03 * max(0.0, dl - 1.0) + 0.03 * (Lt - lmin) / (lmax - lmin)
        cands.append((score, sim, corr, s, Lt, near, dl))
    cands.sort(reverse=True)
    _, sim, corr, s, L, near, dl = cands[0]
    s_smp = int((s - 0.03) * SR)
    e_smp = int((s + L - 0.03) * SR)
    mono = x.mean(1)
    zc = np.where(np.diff(np.signbit(mono[s_smp - 200:s_smp + 200])))[0]
    if len(zc):
        dz = int(zc[np.argmin(np.abs(zc - 200))]) - 200
        s_smp += dz
        e_smp += dz
    top = [f'{tc(c[3])} +{c[4]:.2f}с сх {c[1]:.3f}/{c[5]:.3f} онс {c[2]:.2f} ΔдБ {c[6]:.1f}' for c in cands[:4]]
    return dict(s=s_smp, e=e_smp, sim=sim, near=near, dl=dl, onset_corr=corr, grid=g, beats=round(L / beat, 2), base=base, top=top)


def make_loop(x, s, e):
    n = int(XFADE * SR)
    y = x[s:e].copy()
    t = np.linspace(0, np.pi / 2, n)[:, None]
    y[-n:] = x[e - n:e] * np.cos(t) + x[s - n:s] * np.sin(t)   # равная мощность
    return y


def seam_check(y, ref_after=None):
    """Стык петли: конец→начало. RMS и спектр (18 полос 100 Гц–11 кГц) последних/первых 100 мс; 2-я разность (ошибка
    линейного предсказания) на стыке и 99.9-й перцентиль в ±45 мс; щелчок = ВЧ-всплеск (>6 кГц, 2.5 мс) на стыке выше
    99-го перцентиля ВЧ-энергии в ±0.5 с (после Vorbis 2-я разность на стыке всегда больше — это шум кодека двух концов
    файла, он на уровне обычного шума кодека и не слышен; поэтому критерий — ВЧ-энергия); скачок огибающей 10 мс через стык; ref_after — что в исходнике звучало после конца петли (с тем же
    усилением): спектральное расстояние начала петли до него (насколько «продолжение» похоже на настоящее)."""
    w = int(0.1 * SR)
    a, b = y[-w:], y[:w]
    env = np.sqrt(np.mean(np.concatenate([y[-w:], y[:w]]).reshape(-1, 441, 2) ** 2, axis=(1, 2)))
    envj = np.abs(np.diff(20 * np.log10(env + 1e-9)))
    rms = lambda z: 20 * np.log10(np.sqrt(np.mean(z ** 2)) + 1e-9)
    edges = np.geomspace(100, 11000, 19)            # 18 полос, 100 Гц–11 кГц (выше режет Vorbis — не сравниваем)
    fr = np.fft.rfftfreq(w, 1 / SR)
    bands = [(fr >= lo) & (fr < hi) for lo, hi in zip(edges[:-1], edges[1:])]
    spec = lambda z: 10 * np.log10(np.abs(np.fft.rfft(z.mean(1) * np.hanning(len(z)))) ** 2 + 1e-12)
    bandpow = lambda S: np.array([10 * np.log10(np.mean(10 ** (S[m] / 10))) for m in bands])
    sa, sb = bandpow(spec(a)), bandpow(spec(b))
    sd = float(np.sqrt(np.mean((sa - sb) ** 2)))
    # щелчок: остаток линейного предсказания (2-я разность) ровно на стыке против 99.9-го перцентиля в ±45 мс вокруг
    d2 = np.abs(np.diff(np.concatenate([y[-2000:], y[:2000]]), n=2, axis=0)).max(1)
    jump = float(d2[1998:2000].max())
    typ = float(np.percentile(np.delete(d2, [1998, 1999]), 99.9))
    out = dict(rms_end=round(rms(a), 2), rms_start=round(rms(b), 2), d_rms=round(rms(a) - rms(b), 2),
               spec_dist_db=round(sd, 2), env10ms_jump_db=round(float(envj[9]), 2),
               env10ms_jump_max_elsewhere_db=round(float(np.delete(envj, 9).max()), 2),
               seam_d2=round(jump, 4), p999_d2_around=round(typ, 4))
    # слышимый щелчок = всплеск ВЧ (>6 кГц) на стыке: энергия в окне 2.5 мс у стыка против 99-го перцентиля в ±0.5 с
    from scipy.signal import butter, sosfiltfilt
    m = np.concatenate([y[-SR // 2:], y[:SR // 2]]).mean(1)
    h = sosfiltfilt(butter(4, 6000, 'hp', fs=SR, output='sos'), m)
    e = np.convolve(h ** 2, np.ones(110) / 110, 'same')
    c = SR // 2
    out['hf_seam_db'] = round(float(10 * np.log10(e[c - 110:c + 110].max() + 1e-12)), 1)
    out['hf_median_db'] = round(float(10 * np.log10(np.median(e) + 1e-12)), 1)
    out['hf_p99_db'] = round(float(10 * np.log10(np.percentile(e, 99) + 1e-12)), 1)
    out['click'] = bool(out['hf_seam_db'] > out['hf_p99_db'])
    if ref_after is not None:
        sr_ = bandpow(spec(ref_after[:w]))
        out['spec_vs_source_continuation_db'] = round(float(np.sqrt(np.mean((sb - sr_) ** 2))), 2)
        out['rms_source_continuation'] = round(rms(ref_after[:w]), 2)
    return out


def ff_loudness(wav):
    r = subprocess.run(['ffmpeg', '-hide_banner', '-i', wav, '-af', f'loudnorm=I={TARGET_LUFS}:TP=-1.5:LRA=11:print_format=json',
                        '-f', 'null', '-'], capture_output=True, text=True).stderr
    js = json.loads(r[r.rindex('{'):r.rindex('}') + 1])
    return float(js['input_i']), float(js['input_tp'])


def enc_ogg(y, path, q, tmp):
    w = os.path.join(tmp, os.path.basename(path) + '.wav')
    sf.write(w, np.clip(y, -1, 1).astype(np.float32), SR, subtype='FLOAT')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', w, '-c:a', 'libvorbis', '-q:a', str(q), '-ar', str(SR), '-ac', '2',
                    '-map_metadata', '-1', path], check=True)


def cmd_analyze(a):
    x = load(a.src)
    t0 = tsec(a.frm) if a.frm else 0
    t1 = tsec(a.to) if a.to else len(x) / SR
    seg = x[int(t0 * SR):int(t1 * SR)]
    mono = seg.mean(1)
    print(f'{a.src}: {len(x) / SR:.1f} c; окно {tc(t0)}–{tc(t1)}')
    line = ''
    for i, k in enumerate(range(0, len(mono) - 4 * SR + 1, 4 * SR)):
        r = 20 * np.log10(np.sqrt(np.mean(mono[k:k + 4 * SR] ** 2)) + 1e-9)
        line += f'{tc(t0 + k / SR)[:-4]} {r:5.1f} | '
        if i % 8 == 7:
            print(line)
            line = ''
    print(line)
    g = tempo_grid(Feat(seg), 0, len(mono) / SR)
    print(f"темп ≈ {g['bpm']:.2f} уд/мин, такт {g['beats_per_bar']} доли = {g['bar']:.3f} с "
          f"(автокорреляция онсетов: доля {g['pulse']}, такт {g['bar_pulse']})")


def cmd_cut(a):
    pre = dict(PRESETS.get(a.id, {}))
    x = load(a.src)
    dur = len(x) / SR
    for k in ('p1', 'p2', 'p3'):
        v = getattr(a, k)
        if v:
            if '=' in v:
                p, q_ = v.split('=')
                pre[k + '_fixed'] = (tsec(p), tsec(q_))
            else:
                p, q_ = v.split('-')
                pre[k] = (tsec(p), tsec(q_))
        if k not in pre and k + '_fixed' not in pre:
            third = (dur * 0.9) / 3
            i = int(k[1]) - 1
            pre[k] = (dur * 0.05 + third * i, dur * 0.05 + third * (i + 1) + 20)
    intro_len = a.intro if a.intro else pre.get('intro', 10)
    if a.intro_from is not None:
        pre['intro_from'] = a.intro_from
    print(f'[{a.id}] {a.src}: {dur:.1f} c', file=sys.stderr)
    feat = Feat(x)
    rep = dict(id=a.id, source=os.path.basename(a.src), parts={})
    loops = {}
    for k in ('p1', 'p2', 'p3'):
        win = pre.get(k)
        fixed = pre.get(k + '_fixed')
        if fixed:
            win = (fixed[0] - 8, fixed[1] + 8)
        lo, hi = max(0.0, win[0]), min(win[1], dur - 5.0)     # после конца петли нужно ещё ~4 с исходника
        sr_ = None
        if k == 'p1' and pre.get('intro_from') is not None and not fixed:
            f0 = pre['intro_from']
            sr_ = (f0 + 5, f0 + 15)          # вступление = исходник [intro_from, начало p1], 5–15 с
        r = find_loop(x, feat, lo, hi, a.lmin, a.lmax, fixed, sr_)
        s, e = r['s'], r['e']
        y = make_loop(x, s, e)
        L = (e - s) / SR
        loops[k] = y
        g = r['grid']
        rep['parts'][k] = dict(window=f'{tc(lo)}–{tc(hi)}', start=tc(s / SR), end=tc(e / SR), length=round(L, 3),
                               bpm=round(g['bpm'], 2), grid_beats=g['beats_per_bar'], beats=r['beats'],
                               pulse=g['pulse'], bar_pulse=g['bar_pulse'],
                               context_similarity=round(r['sim'], 3), near_similarity=round(r['near'], 3),
                               near_level_diff_db=round(r['dl'], 2), natural_similarity_1s_2s=r['base'],
                               onset_corr=round(r['onset_corr'], 3),
                               alternatives=r['top'], _s=int(s), _e=int(e))
        print(f"  {k}: {tc(s / SR)}–{tc(e / SR)} ({L:.2f} c = {r['beats']} долей при {g['bpm']:.1f} bpm, "
              f"сходство {r['sim']:.3f}/{r['near']:.3f} ΔдБ {r['dl']:.1f} [естеств. через 1/2 с: {r['base']}], онсеты {r['onset_corr']:.3f}); {r['top']}",
              file=sys.stderr)
    s1 = rep['parts']['p1']['_s']
    if pre.get('intro_from') is not None and not pre.get('p1_fixed'):
        i0 = int(pre['intro_from'] * SR)
    else:
        i0 = max(0, s1 - int(intro_len * SR))
    intro = x[i0:s1].copy()
    if i0 > 0 and pre.get('intro_from') is None:
        nf = int(0.4 * SR)
        intro[:nf] *= np.linspace(0, 1, nf)[:, None]
    rep['parts']['intro'] = dict(start=tc(i0 / SR), end=tc(s1 / SR), length=round((s1 - i0) / SR, 3))
    with tempfile.TemporaryDirectory() as tmp:
        allw = os.path.join(tmp, 'all.wav')
        sf.write(allw, np.concatenate([loops['p1'], loops['p2'], loops['p3']]).astype(np.float32), SR, subtype='FLOAT')
        I, tp = ff_loudness(allw)
        gain = 10 ** ((TARGET_LUFS - I) / 20)
        rep['loudness_in'] = I
        rep['gain_db'] = round(TARGET_LUFS - I, 2)
        parts = dict(intro=intro * gain, **{k: v * gain for k, v in loops.items()})
        peak = max(np.abs(v).max() for v in parts.values())
        rep['peak_after_gain_dbfs'] = round(20 * np.log10(peak), 2)
        if peak > 0.995:
            print(f'  ВНИМАНИЕ: пик {20 * np.log10(peak):.2f} dBFS — будет срез', file=sys.stderr)
        os.makedirs(a.out, exist_ok=True)
        total = 0
        for k, y in parts.items():
            p = os.path.join(a.out, f'{a.id}_{k}.ogg')
            enc_ogg(y, p, a.q, tmp)
            sz = os.path.getsize(p)
            total += sz
            dec = load(p)
            rep['parts'][k]['size_kb'] = round(sz / 1024, 1)
            rep['parts'][k]['ogg_len'] = round(len(dec) / SR, 3)
            if k != 'intro':
                e_ = rep['parts'][k]['_e']
                rep['parts'][k]['seam_src'] = seam_check(y, x[e_:e_ + SR // 10] * gain)     # до кодека
                rep['parts'][k]['seam_ogg'] = seam_check(dec, x[e_:e_ + SR // 10] * gain)   # после кодека (что услышит игра)
        rep['total_kb'] = round(total / 1024, 1)
        # громкость готового
        cat = np.concatenate([load(os.path.join(a.out, f'{a.id}_{k}.ogg')) for k in ('p1', 'p2', 'p3')])
        sf.write(allw, cat.astype(np.float32), SR, subtype='FLOAT')
        rep['lufs_out'], rep['tp_out'] = ff_loudness(allw)
        for k in ('intro', 'p1', 'p2', 'p3'):
            sf.write(allw, load(os.path.join(a.out, f'{a.id}_{k}.ogg')).astype(np.float32), SR, subtype='FLOAT')
            rep['parts'][k]['lufs'] = ff_loudness(allw)[0]
        if not a.no_demo:
            demo(a.id, a.out, tmp)
    for v in rep['parts'].values():
        v.pop('_s', None)
        v.pop('_e', None)
    js = json.dumps(rep, ensure_ascii=False, indent=1)
    print(js)
    if a.report:
        with open(a.report, 'w') as f:
            f.write(js)


def demo(id_, out, tmp):
    """вступление → p1×2 → кроссфейд 1.5 с → p2×2 → кроссфейд → p3×2 → затухание 2 с; mp3 64 кбит/с."""
    P = {k: load(os.path.join(out, f'{id_}_{k}.ogg')) for k in ('intro', 'p1', 'p2', 'p3')}
    xf = int(1.5 * SR)
    seq = np.concatenate([P['intro'], P['p1'], P['p1']])
    for k in ('p2', 'p3'):
        nxt = np.concatenate([P[k], P[k]])
        # кроссфейд как в игре: старая петля продолжает звучать (её начало, т.к. петля бы пошла по кругу), новая — с начала
        prev = P['p2' if k == 'p3' else 'p1']
        tail = prev[:xf]
        t = np.linspace(0, np.pi / 2, xf)[:, None]
        head = tail * np.cos(t) + nxt[:xf] * np.sin(t)
        seq = np.concatenate([seq, head, nxt[xf:]])
    nf = 2 * SR
    seq[-nf:] *= np.linspace(1, 0, nf)[:, None]
    os.makedirs(OUT_DEMO, exist_ok=True)
    w = os.path.join(tmp, 'demo.wav')
    sf.write(w, np.clip(seq, -1, 1).astype(np.float32), SR, subtype='FLOAT')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', w, '-c:a', 'libmp3lame', '-b:a', '64k', '-map_metadata', '-1',
                    os.path.join(OUT_DEMO, f'{id_}_phases.mp3')], check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    p = sp.add_parser('analyze')
    p.add_argument('src')
    p.add_argument('--from', dest='frm')
    p.add_argument('--to')
    p = sp.add_parser('cut')
    p.add_argument('id')
    p.add_argument('src')
    for k in ('p1', 'p2', 'p3'):
        p.add_argument('--' + k)
    p.add_argument('--intro', type=float, help='длина вступления, если начало p1 не привязано к intro_from')
    p.add_argument('--intro-from', type=float, help='где в исходнике начинается вступление, с')
    p.add_argument('--lmin', type=float, default=30)
    p.add_argument('--lmax', type=float, default=60)
    p.add_argument('--q', type=float, default=1.5)
    p.add_argument('--out', default=OUT_OGG)
    p.add_argument('--report')
    p.add_argument('--no-demo', action='store_true')
    a = ap.parse_args()
    (cmd_analyze if a.cmd == 'analyze' else cmd_cut)(a)


if __name__ == '__main__':
    main()
