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
        --pN A=B (через «=») — задать петлю жёстко: начало A, конец B (конец уточняется по корреляции ±50 мс).
  Арис, когда будет файл:  python3 tools/music_cut.py cut aris путь/к/Old_Iron_King.mp4

Как ищется петля: лог-мел-спектр (hop 46 мс) → матрица самоподобия (косинус) в окне → для каждой пары (начало s, длина L)
сумма сходства по диагонали в ±3 с вокруг s и s+L (то, что звучит после конца петли, похоже на то, что звучит после её начала,
и то же до них) → лучшая пара с предпочтением длинных петель и целого числа тактов при найденном темпе → уточнение конца по
корреляции волны ±50 мс → петля = src[s:e], последние 40 мс — кроссфейд src[e-40мс:e] → src[s-40мс:s] (равная мощность), так что
при переходе конец→начало слышно ровно то, что было в исходнике перед s. Вступление = src[s1-N : s1] (s1 — начало p1), т.е.
оно перетекает в p1 без шва; если начало не совпадает с началом трека — 0.4 с fade-in.
Громкость: интегральная громкость p1+p2+p3 (ffmpeg loudnorm, проход 1) → одно линейное усиление на всё (проход 2 = linear),
так что у всех боссов −16 LUFS, а p1 остаётся тише p3, и стыки не портятся динамической обработкой.
Выход: src/main/resources/assets/pohsmp_core/sounds/music/<id>_{intro,p1,p2,p3}.ogg (Vorbis 44.1 кГц стерео),
демо docs/media/audio/<id>_phases.mp3 (64 кбит/с), отчёт по стыкам — в stdout и <tmp>/<id>_report.json.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

import numpy as np
import soundfile as sf

SR = 44100
HOP = 2048                      # 46.4 мс
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_OGG = os.path.join(ROOT, 'src/main/resources/assets/pohsmp_core/sounds/music')
OUT_DEMO = os.path.join(ROOT, 'docs/media/audio')
TARGET_LUFS = -16.0
XFADE = 0.040                   # кроссфейд внутри петли, с
CTX = 3.0                       # контекст сравнения вокруг точек резки, с

# Окна поиска петель (секунды исходника), длина вступления. Подобраны по огибающей/структуре трека (см. отчёт в docs/inbox).
PRESETS = {
    'cult_leader': dict(p1=(8, 78), p2=(78, 170), p3=(256, 420), intro=10),
    'irina':       dict(p1=(8, 75), p2=(74, 145), p3=(144, 238), intro=10),
    'martin':      dict(p1=(8, 80), p2=(78, 170), p3=(183, 345), intro=10),
    'ereb':        dict(p1=(4, 105), p2=(54, 120), p3=(115, 190), intro=8),
    'ereb_hand':   dict(p1=(8, 100), p2=(55, 104), p3=(110, 255), intro=10),
    'aris':        dict(intro=10),   # окна — автоматически (трети трека), пока файла нет
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


class Feat:
    """Признаки трека на 22.05 кГц, hop 512 (23 мс): лог-мел 64 полосы и хрома, обе z-нормированы по полосам по всему треку;
    сетка долей (librosa.beat); огибающая онсетов hop 128 на 44.1 кГц для точной подгонки конца петли."""

    def __init__(self, x):
        import librosa
        self.lr = librosa
        y = librosa.resample(x.mean(1).astype(np.float32), orig_sr=SR, target_sr=FSR)
        self.y = y
        mel = librosa.power_to_db(librosa.feature.melspectrogram(y=y, sr=FSR, hop_length=FHOP, n_mels=64, fmax=11000))
        chroma = librosa.feature.chroma_stft(y=y, sr=FSR, hop_length=FHOP)
        z = lambda A: (A - A.mean(1, keepdims=True)) / (A.std(1, keepdims=True) + 1e-9)
        self.mel, self.chroma = z(mel), z(chroma)
        self.onset = librosa.onset.onset_strength(y=y, sr=FSR, hop_length=FHOP)
        self.fine = librosa.onset.onset_strength(y=x.mean(1).astype(np.float32), sr=SR, hop_length=128)

    def beats(self, t0, t1):
        a, b = int(t0 * FSR / FHOP), int(t1 * FSR / FHOP)
        o = self.onset[a:b]
        bpm = float(self.lr.feature.tempo(onset_envelope=o, sr=FSR, hop_length=FHOP)[0])
        _, bt = self.lr.beat.beat_track(onset_envelope=o, sr=FSR, hop_length=FHOP, start_bpm=bpm, tightness=200)
        bt = np.asarray(bt) + a
        # сила пульса: автокорреляция онсетов на лаге доли
        oc = o - o.mean()
        lag = int(round(60 / bpm * FSR / FHOP))
        st = float(np.dot(oc[:-lag], oc[lag:]) / (np.dot(oc, oc) + 1e-9))
        return bpm, st, bt

    def beat_sync(self, bt):
        F = np.vstack([self.mel, self.chroma * np.sqrt(64 / 12)])
        out = np.stack([F[:, bt[i]:bt[i + 1]].mean(1) for i in range(len(bt) - 1)], 1)
        out /= np.linalg.norm(out, axis=0, keepdims=True) + 1e-9
        return out


FSR, FHOP = 22050, 512


def tempo_of(feat, t0, t1):
    bpm, st, _ = feat.beats(t0, t1)
    return bpm, st


def find_loop(x, feat, t0, t1, lmin=30.0, lmax=60.0, fixed=None):
    """Начало и конец петли — на долях; длина — кратна 4 долям (такт); оценка — сходство ±K долей вокруг начала и конца."""
    bpm, st, bt = feat.beats(t0, t1)
    T = bt * FHOP / FSR
    B = feat.beat_sync(bt)
    S = B.T @ B
    K = max(4, int(round(3.0 * bpm / 60)))     # ±~3 с контекста
    nb = len(bt) - 1
    cands = []
    if fixed:
        i = int(np.argmin(np.abs(T - fixed[0])))
        j = int(np.argmin(np.abs(T - fixed[1])))
        js = [(i, j)]
    else:
        js = []
        for i in range(K, nb):
            for j in range(i + 4, nb - K, 4):
                L = T[j] - T[i]
                if L < lmin:
                    continue
                if L > lmax:
                    break
                js.append((i, j))
    for i, j in js:
        lo, hi = max(-K, -i), min(K, nb - j)
        sc = float(np.mean([S[i + k, j + k] for k in range(lo, hi)]))
        L = T[j] - T[i]
        cands.append((sc + 0.03 * (L - lmin) / (lmax - lmin), sc, i, j))
    cands.sort(reverse=True)
    _, sim, i, j = cands[0]
    # точная подгонка конца по онсетам (hop 128 @ 44.1 кГц ≈ 2.9 мс): окно −1…+4 с, сдвиг ±80 мс
    f = feat.fine
    r = SR / 128
    si, ei = int(T[i] * r), int(T[j] * r)
    w0, w1, R = int(1 * r), int(4 * r), int(0.08 * r)
    ref = f[si - w0:si + w1] - f[si - w0:si + w1].mean()
    best = (-2, 0)
    for lag in range(-R, R + 1):
        o = f[ei + lag - w0:ei + lag + w1]
        o = o - o.mean()
        c = float(np.dot(ref, o) / (np.linalg.norm(ref) * np.linalg.norm(o) + 1e-9))
        best = max(best, (c, lag))
    corr, lag = best
    s_smp = int(T[i] * SR)
    e_smp = int(T[j] * SR) + lag * 128
    # сдвиг обеих точек на 30 мс раньше доли: кроссфейд ложится перед атакой, а не на неё
    s_smp -= int(0.03 * SR)
    e_smp -= int(0.03 * SR)
    mono = x.mean(1)
    zc = np.where(np.diff(np.signbit(mono[s_smp - 200:s_smp + 200])))[0]
    if len(zc):
        dz = int(zc[np.argmin(np.abs(zc - 200))]) - 200
        s_smp += dz
        e_smp += dz
    return dict(s=s_smp, e=e_smp, sim=sim, onset_corr=corr, bpm=bpm, pulse=st, beats=j - i,
                top=[(round(c[1], 3), round(T[c[2]], 2), round(T[c[3]] - T[c[2]], 2)) for c in cands[:5]])


def make_loop(x, s, e):
    n = int(XFADE * SR)
    y = x[s:e].copy()
    t = np.linspace(0, np.pi / 2, n)[:, None]
    y[-n:] = x[e - n:e] * np.cos(t) + x[s - n:s] * np.sin(t)   # равная мощность
    return y


def seam_check(y):
    """Стык петли: конец→начало. RMS и спектр последних/первых 100 мс, щелчок = скачок 1-й разности на стыке."""
    w = int(0.1 * SR)
    a, b = y[-w:], y[:w]
    rms = lambda z: 20 * np.log10(np.sqrt(np.mean(z ** 2)) + 1e-9)
    spec = lambda z: 20 * np.log10(np.abs(np.fft.rfft(z.mean(1) * np.hanning(len(z))))[:2000] + 1e-6)
    sa, sb = spec(a), spec(b)
    bands = np.array_split(np.arange(2000), 20)
    sd = float(np.sqrt(np.mean([(sa[i].mean() - sb[i].mean()) ** 2 for i in bands])))
    d = np.diff(np.concatenate([y[-2000:], y[:2000]]), axis=0)
    jump = float(np.abs(d[1999]).max())                         # разность ровно через стык
    typ = float(np.percentile(np.abs(d).max(1), 99))            # 99-й перцентиль вокруг
    return dict(rms_end=round(rms(a), 2), rms_start=round(rms(b), 2), d_rms=round(rms(a) - rms(b), 2),
                spec_dist_db=round(sd, 2), seam_step=round(jump, 4), p99_step=round(typ, 4),
                click=bool(jump > 1.5 * typ + 0.01))


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
    feat = Feat(seg)
    bpm, st = tempo_of(feat, 0, len(mono) / SR)
    print(f'темп ≈ {bpm:.1f} уд/мин (сила пульса {st:.2f})')


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
    mono = x.mean(1)
    print(f'[{a.id}] {a.src}: {dur:.1f} c', file=sys.stderr)
    feat = Feat(x)
    rep = dict(id=a.id, source=os.path.basename(a.src), parts={})
    loops = {}
    for k in ('p1', 'p2', 'p3'):
        win = pre.get(k)
        fixed = pre.get(k + '_fixed')
        if fixed:
            win = (fixed[0] - 8, fixed[1] + 8)
        lo, hi = win
        r = find_loop(x, feat, lo, hi, a.lmin, a.lmax, fixed)
        s, e = r['s'], r['e']
        y = make_loop(x, s, e)
        L = (e - s) / SR
        loops[k] = y
        rep['parts'][k] = dict(window=f'{tc(lo)}–{tc(hi)}', start=tc(s / SR), end=tc(e / SR), length=round(L, 3),
                               bpm=round(r['bpm'], 1), pulse=round(r['pulse'], 2), beats=r['beats'],
                               beat_similarity=round(r['sim'], 3), onset_corr=round(r['onset_corr'], 3),
                               alternatives=r['top'][1:], _s=int(s), _e=int(e))
        print(f"  {k}: {tc(s / SR)}–{tc(e / SR)} ({L:.2f} c, {r['bpm']:.1f} bpm, {r['beats']} долей, "
              f"сходство {r['sim']:.3f}, онсеты {r['onset_corr']:.3f}); топ {r['top']}", file=sys.stderr)
    s1 = rep['parts']['p1']['_s']
    i0 = max(0, s1 - int(intro_len * SR))
    intro = x[i0:s1].copy()
    if i0 > 0:
        nf = int(0.4 * SR)
        intro[:nf] *= np.linspace(0, 1, nf)[:, None]
    rep['parts']['intro'] = dict(start=tc(i0 / SR), end=tc(s1 / SR), length=round((s1 - i0) / SR, 3))
    with tempfile.TemporaryDirectory() as tmp:
        allw = os.path.join(tmp, 'all.wav')
        sf.write(allw, np.concatenate([loops['p1'], loops['p2'], loops['p3']]).astype(np.float32), SR, subtype='FLOAT')
        I, tp = ff_loudness(allw)
        g = 10 ** ((TARGET_LUFS - I) / 20)
        rep['loudness_in'] = I
        rep['gain_db'] = round(TARGET_LUFS - I, 2)
        parts = dict(intro=intro * g, **{k: v * g for k, v in loops.items()})
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
                rep['parts'][k]['seam_src'] = seam_check(y)        # до кодека
                rep['parts'][k]['seam_ogg'] = seam_check(dec)      # после кодека (что услышит игра)
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
    p.add_argument('--intro', type=float)
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
