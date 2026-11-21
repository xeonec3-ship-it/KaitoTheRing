"""Animation start times inside the T29–T31 preview videos (they have no marks.json entries): the clip frame functions of
tools/boss_video_b.py / tools/boss_video_t31.py are run without rendering, and every (model, animation) restart is a mark.
Loops restart on each wrap (like in game: the walk's step keyframes play every cycle).
Output: build/boss_sfx_marks.json  {video: {"dur": s, "marks": [[t, "`anim`"], ...]}} — read by build_all.video().
"""
import importlib, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "build", "boss_sfx_marks.json")
sys.path.insert(0, os.path.join(ROOT, "tools"))


MAIN = {"martin", "ereb", "ereb_hand", "ereb_hand_mended", "ereb_hand_cracked"}   # the boss models (other models: "model:anim")


def marks_of(clip, fps):
    last = {}
    marks = []
    for i, fr in enumerate(clip.frames):
        t = i / fps
        seen = set()
        for k, o in enumerate(fr.get("objs", [])):
            if not o.get("anim") or not o.get("model"):
                continue
            key = (o["model"], o["anim"], round(o.get("pos", (0, 0, 0))[0], 1) if isinstance(o.get("pos"), (list, tuple)) else k)
            if key in seen:
                continue
            seen.add(key)
            lt = float(o.get("t", 0))
            prev = last.get(key)
            if prev is None or lt < prev[1] - 0.05 or t - prev[0] > 2.0 / fps + 1e-6:
                start = round(t - lt, 3)
                label = "`%s`" % (o["anim"] if o["model"] in MAIN else o["model"] + ":" + o["anim"])
                if not any(m[1] == label and abs(m[0] - start) < 0.15 for m in marks):
                    marks.append([start, label])
            last[key] = (t, lt)
    marks.sort()
    return {"dur": round(len(clip.frames) / fps, 3), "marks": marks}


def main():
    out = json.load(open(OUT)) if os.path.exists(OUT) else {}
    for modname in ("boss_video_b", "boss_video_t31"):
        m = importlib.import_module(modname)
        if hasattr(m, "load_anims"):
            m.load_anims()
        for name, spec in m.CLIPS.items():
            if "turntable" in name:
                continue
            fn = spec[1] if isinstance(spec, tuple) else spec
            try:
                clip = fn()
            except Exception as e:  # noqa: BLE001
                print("skip", name, e, file=sys.stderr)
                continue
            out[name] = marks_of(clip, getattr(m, "FPS", None) or m.VB.FPS)
            print(name, out[name]["dur"], len(out[name]["marks"]), file=sys.stderr)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
