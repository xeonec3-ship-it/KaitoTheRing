"""Builds the boss sounds: python tools/boss_sfx/build_all.py [--no-video] [boss ...]

For each boss module (tools/boss_sfx/<boss>.py):
  build()  -> {event: [file rel to sounds/boss, ...]}     (writes the .ogg)
  EVENTS   =  {event: (subtitle ru, subtitle en, attenuation distance, volume)}
  ANIMS    =  {animation file: {animation: [(time, "event[|vol|pitch]"), ...]}}   -> GeckoLib sound_effects
  VIDEOS   =  {out name: (source video, {anim: [(t, event)]} code-timed sounds by animation, extra [(t, event)])}
Then: sounds.json (events replaced / added), lang subtitles, the animations, docs/licenses/sounds_bosses.md (used CC0 files),
docs/media/video/<boss>_sound.mp4.
"""
import importlib, json, os, sys, subprocess, collections
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sfx  # noqa: E402

ROOT = sfx.ROOT
ASSETS = os.path.join(ROOT, "src", "main", "resources", "assets", "pohsmp_core")
SOUNDS_JSON = os.path.join(ASSETS, "sounds.json")
ANIM_DIR = os.path.join(ASSETS, "animations", "entity")
VIDEO_DIR = os.path.join(ROOT, "docs", "media", "video")
USED_LOG = os.path.join(ROOT, "tools", "boss_sfx", "used_sources.json")
BOSSES = ["common", "cult_leader", "irina", "aris", "martin", "ereb", "ereb_hand"]


def update_sounds_json(boss, files, events):
    raw = open(SOUNDS_JSON, encoding="utf-8").read()
    d = json.loads(raw)
    for ev, rels in files.items():
        ru, en, dist, vol = events[ev]
        entries = []
        for r in rels:
            e = {"name": "pohsmp_core:boss/" + r, "attenuation_distance": int(dist)}
            if vol != 1:
                e["volume"] = vol
            entries.append(e)
        d[ev] = {"subtitle": "subtitles.pohsmp_core." + ev, "sounds": entries}
    with open(SOUNDS_JSON, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
        f.write("\n")


def update_lang(events):
    for code, idx in (("ru_ru", 0), ("en_us", 1)):
        p = os.path.join(ASSETS, "lang", code + ".json")
        raw = open(p, encoding="utf-8").read()
        d = json.loads(raw)
        for ev, spec in events.items():
            d["subtitles.pohsmp_core." + ev] = spec[idx]
        with open(p, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
            f.write("\n")


def log_used(boss):
    log = json.load(open(USED_LOG)) if os.path.exists(USED_LOG) else {}
    log[boss] = sorted(sfx.USED)
    with open(USED_LOG, "w") as f:
        json.dump(log, f, indent=1, ensure_ascii=False)
        f.write("\n")
    sfx.USED.clear()


# ------------------------------------------------------------------ demo video

def _ogg(path):
    return sfx._load(path)


def _from_sounds_json(ev):
    d = json.load(open(SOUNDS_JSON, encoding="utf-8")).get(ev, {})
    return [s["name"].split("pohsmp_core:boss/")[1] for s in d.get("sounds", []) if s["name"].startswith("pohsmp_core:boss/")]


def video(boss, name, spec, files):
    """spec: (source mp4 name, code events by anim {anim: [(t, ev)]}, extra [(t, ev)])."""
    src_name, code, extra = spec
    marks = json.load(open(os.path.join(VIDEO_DIR, "marks.json"), encoding="utf-8"))[src_name]
    mod = importlib.import_module(boss)
    plan = {}
    for fl in mod.ANIMS.values():
        plan.update(fl)
    import re
    events = list(extra)
    ms = marks["marks"]
    for i, (t0, label) in enumerate(ms):
        t_end = ms[i + 1][0] if i + 1 < len(ms) else marks["dur"]
        m = re.findall(r"`([^`]+)`", label)
        for anim in m:
            a = anim if anim in plan or anim in code else "animation.%s.%s" % (boss, anim)
            for t, ev in plan.get(a, []) + code.get(a, []) + code.get(anim, []):
                if t0 + t < t_end + 0.05:
                    events.append((t0 + t, ev))
    dur = marks["dur"]
    out = np.zeros(sfx.secs(dur + 3))
    counters = collections.Counter()
    for t, ev in sorted(events):
        parts = ev.split("|")
        e = parts[0].split(":")[-1]
        vol = float(parts[1]) if len(parts) > 1 else 1.0
        rels = files.get(e) or _from_sounds_json(e)
        if not rels:
            print("  (video) no file for", e, file=sys.stderr)
            continue
        r = rels[counters[e] % len(rels)]
        counters[e] += 1
        x = _ogg(os.path.join(sfx.OUT, r + ".ogg"))
        level = min(1.0, 0.55 + 0.25 * vol) * (mod.EVENTS[e][3] if e in mod.EVENTS else 1.0)
        a = sfx.secs(t)
        seg = x[: len(out) - a] * level
        out[a:a + len(seg)] += seg
    aura = files.get(boss + ".aura")
    if aura:
        bed = _ogg(os.path.join(sfx.OUT, aura[0] + ".ogg"))
        reps = int(np.ceil(len(out) / len(bed))) + 1
        out += np.tile(bed, reps)[: len(out)] * 0.35
    out = out[: sfx.secs(dur)]
    out = np.tanh(out / max(1e-9, np.percentile(np.abs(out), 99.9)) * 0.9) * 0.89
    wav = os.path.join(sfx.CC0, "_video_%s.f32" % name)
    out.astype(np.float32).tofile(wav)
    dst = os.path.join(VIDEO_DIR, name + ".mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(VIDEO_DIR, src_name + ".mp4"),
                    "-f", "f32le", "-ar", str(sfx.SR), "-ac", "1", "-i", wav, "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-ac", "2", "-shortest", dst], check=True)
    return dst, sorted(events)


def concat_videos(boss, parts):
    """<boss>_sound.mp4 = the boss's demo parts one after another."""
    lst = os.path.join(sfx.CC0, "_concat_%s.txt" % boss)
    with open(lst, "w") as f:
        for p in parts:
            f.write("file '%s'\n" % p)
    dst = os.path.join(VIDEO_DIR, boss + "_sound.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst,
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "26", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "128k", dst], check=True)
    for p in parts:
        os.remove(p)
    return dst


def main(args):
    no_video = "--no-video" in args
    bosses = [a for a in args if not a.startswith("--")] or BOSSES
    for boss in bosses:
        mod = importlib.import_module(boss)
        print("==", boss, file=sys.stderr)
        files = mod.build()
        missing = set(files) - set(mod.EVENTS)
        assert not missing, missing
        update_sounds_json(boss, files, mod.EVENTS)
        update_lang({e: mod.EVENTS[e] for e in files})
        log_used(boss)
        from anim_sfx import apply
        for fn, plan in mod.ANIMS.items():
            n = apply(os.path.join(ANIM_DIR, fn), plan)
            print("  keyframes", fn, n, file=sys.stderr)
        if not no_video and getattr(mod, "VIDEOS", None):
            parts = []
            for name, spec in mod.VIDEOS.items():
                dst, evs = video(boss, name, spec, files)
                parts.append(dst)
                print("  video part", dst, len(evs), "sounds", file=sys.stderr)
            print("  video", concat_videos(boss, parts), file=sys.stderr)
        n = sum(len(v) for v in files.values())
        print("  %d events, %d files" % (len(files), n), file=sys.stderr)
    import licenses
    licenses.main()


if __name__ == "__main__":
    main(sys.argv[1:])
