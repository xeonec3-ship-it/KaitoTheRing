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
from scipy.signal import stft

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


def melspec(mono):
    f, t, Z = stft(mono, SR, nperseg=4096, noverlap=4096 - HOP, boundary=None, padded=False)
    P = np.abs(Z) ** 2
    # 48 мел-полос 40 Гц–16 кГц (треугольные)
    mel = lambda hz: 2595 * np.log10(1 + hz / 700)
    imel = lambda m: 700 * (10 ** (m / 2595) - 1)
    edges = imel(np.linspace(mel(40), mel(16000), 50))
    fb = np.zeros((48, len(f)))
    for i in range(48):
        a, b, c = edges[i:i + 3]
        fb[i] = np.clip(np.minimum((f - a) / (b - a), (c - f) / (c - b)), 0, None)
    M = np.log10(fb @ P + 1e-10)
    return M  # (48, frames); кадр k ~ время k*HOP/SR (начало окна)


def onset_env(M):
    d = np.diff(M, axis=1)
    return np.concatenate([[0], np.clip(d, 0, None).sum(0)])


def tempo(M, lo=60, hi=180):
    o = onset_env(M)
    o = o - np.convolve(o, np.ones(43) / 43, 'same')
    ac = np.correlate(o, o, 'full')[len(o) - 1:]
    fps = SR / HOP
    lags = np.arange(len(ac))
    bpm = np.where(lags > 0, 60 * fps / np.maximum(lags, 1), 0)
    ok = (bpm >= lo) & (bpm <= hi)
    # уточнение параболой по пику
    k = int(np.argmax(np.where(ok, ac, -np.inf)))
    if 0 < k < len(ac) - 1:
        a, b, c = ac[k - 1:k + 2]
        k = k + 0.5 * (a - c) / (a - 2 * b + c + 1e-12)
    strength = float(ac[int(round(k))] / (ac[0] + 1e-12))
    return 60 * fps / k, strength


def find_loop(x, M, t0, t1, lmin=30.0, lmax=60.0, bpm=None, fixed=None):
    fps = SR / HOP
    W = int(CTX * fps)
    if fixed:
        s = int(fixed[0] * fps)
        e = int(fixed[1] * fps)
        best = (s, e - s, None)
    else:
        a, b = int(t0 * fps), int(min(t1 * fps, M.shape[1] - W - 1))
        a = max(a, W + 1)
        F = M[:, a - W:b + W].T
        F = F - F.mean(1, keepdims=True)
        F /= np.linalg.norm(F, axis=1, keepdims=True) + 1e-9
        S = (F @ F.T).astype(np.float32)
        n = S.shape[0]
        best = None
        cands = []
        for L in range(int(lmin * fps), int(lmax * fps) + 1):
            if L + 2 * W >= n:
                break
            d = np.diagonal(S, L)                       # S[i, i+L]
            cs = np.concatenate([[0], np.cumsum(d)])
            # центр i в [W, n-L-W): сумма d[i-W:i+W]
            i = np.arange(W, len(d) - W)
            sc = (cs[i + W] - cs[i - W]) / (2 * W)
            # и начало петли не должно уходить за окно поиска
            j = int(np.argmax(sc))
            score = float(sc[j])
            # предпочтение длинным петлям (меньше заметна повторяемость) и целому числу тактов
            bonus = 0.04 * (L / fps - lmin) / (lmax - lmin)
            if bpm:
                beats = L / fps * bpm / 60
                bars = beats / 4
                bonus += 0.02 * (1 - 2 * abs(bars - round(bars)))
            cands.append((score + bonus, score, a - W + i[j], L))
        cands.sort(reverse=True)
        _, raw, s, L = cands[0]
        best = (s, L, raw)
    s, L, raw = best
    # уточнение по волне: ищем сдвиг конца ±50 мс, максимизирующий корреляцию src[s:s+0.5c] и src[e:e+0.5c]
    mono = x.mean(1)
    s_smp = s * HOP + 2048          # центр окна stft
    e_smp = (s + L) * HOP + 2048
    seg = mono[s_smp:s_smp + SR // 2]
    best_lag, best_c = 0, -2
    R = int(0.05 * SR)
    for lag in range(-R, R + 1, 1):
        o = mono[e_smp + lag:e_smp + lag + SR // 2]
        c = float(np.dot(seg, o) / (np.linalg.norm(seg) * np.linalg.norm(o) + 1e-12))
        if c > best_c:
            best_c, best_lag = c, lag
    e_smp += best_lag
    # начало — на ближайший нулевой переход (по моно), конец сдвигаем так же
    zc = np.where(np.diff(np.signbit(mono[s_smp - 200:s_smp + 200])))[0]
    if len(zc):
        dz = int(zc[np.argmin(np.abs(zc - 200))]) - 200
        s_smp += dz
        e_smp += dz
    return s_smp, e_smp, raw, best_c


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
    bpm, st = tempo(melspec(mono))
    print(f'темп ≈ {bpm:.1f} уд/мин (сила автокорреляции {st:.2f})')


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
    M = melspec(mono)
    rep = dict(id=a.id, source=os.path.basename(a.src), parts={})
    loops = {}
    for k in ('p1', 'p2', 'p3'):
        win = pre.get(k)
        fixed = pre.get(k + '_fixed')
        if fixed:
            win = (fixed[0] - 5, fixed[1] + 5)
        lo, hi = win
        Mw = M[:, int(lo * SR / HOP):int(hi * SR / HOP)]
        bpm, st = tempo(Mw)
        s, e, sim, corr = find_loop(x, M, lo, hi, a.lmin, a.lmax, bpm if st > 0.15 else None, fixed)
        y = make_loop(x, s, e)
        L = (e - s) / SR
        loops[k] = y
        rep['parts'][k] = dict(window=f'{tc(lo)}–{tc(hi)}', start=tc(s / SR), end=tc(e / SR), length=round(L, 3),
                               bpm=round(bpm, 1), bpm_strength=round(st, 2), beats=round(L * bpm / 60, 2),
                               ssm_similarity=None if sim is None else round(sim, 3), wave_corr=round(corr, 3),
                               _s=int(s), _e=int(e))
        print(f'  {k}: {tc(s / SR)}–{tc(e / SR)} ({L:.2f} c, {bpm:.1f} bpm×{L * bpm / 60:.1f} долей, '
              f'сходство {sim if sim is None else round(sim, 3)}, корр. волны {corr:.3f})', file=sys.stderr)
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
