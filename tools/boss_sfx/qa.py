"""QA of the boss sounds: duration, peak / RMS, spectral centroid, a spectrogram sheet (build/boss_sfx_qa/<boss>.png)."""
import glob, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sfx

def stats(x):
    rms = 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9)
    pk = 20 * np.log10(np.max(np.abs(x)) + 1e-9)
    X = np.abs(np.fft.rfft(x)); f = np.fft.rfftfreq(len(x), 1 / sfx.SR)
    return len(x) / sfx.SR, pk, rms, (X * f).sum() / (X.sum() + 1e-9)

def main(boss):
    files = sorted(glob.glob(os.path.join(sfx.OUT, boss, "*.ogg")))
    rows = []
    for p in files:
        x = sfx._load(p)
        d, pk, rms, c = stats(x)
        rows.append((os.path.basename(p)[:-4], x))
        print(f"{os.path.basename(p):28s} {d:5.2f}s peak {pk:6.1f} dB rms {rms:6.1f} dB centroid {c:6.0f} Hz {os.path.getsize(p)//1024:4d} KB")
    try:
        import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    except ImportError:
        return
    n = len(rows); cols = 4; r = (n + cols - 1) // cols
    fig, axs = plt.subplots(r, cols, figsize=(16, 2.0 * r))
    for ax, (name, x) in zip(axs.flat, rows):
        ax.specgram(x + 1e-7, NFFT=1024, Fs=sfx.SR, noverlap=768, cmap="magma", vmin=-120)
        ax.set_ylim(0, 12000); ax.set_title(name, fontsize=8); ax.tick_params(labelsize=6)
    for ax in list(axs.flat)[n:]:
        ax.axis("off")
    out = os.path.join(sfx.ROOT, "build", "boss_sfx_qa"); os.makedirs(out, exist_ok=True)
    fig.tight_layout(); fig.savefig(os.path.join(out, boss + ".png"), dpi=60)

if __name__ == "__main__":
    for b in sys.argv[1:]:
        main(b)
