"""Boss animation sound keyframes (GeckoLib `sound_effects`).

- swing_peaks(anim): times of the fastest arm/weapon motion (the swish) and where it stops (the hit), from the rotation keyframes;
- apply(file, plan): writes `sound_effects` {time: {"effect": "pohsmp_core:<id>[|vol|pitch]"}} into the animations of plan
  (replaces the old sound_effects of those animations only; other animations untouched).
"""
import json, re, sys
import numpy as np

ARM = re.compile(r"(arm|hand|weapon|sword|scythe|staff|hammer|blade|rapier|shield|item|forearm|wrist|elbow|dagger|whip)", re.I)


def _val(v):
    if isinstance(v, dict):
        v = v.get("post", v.get("pre", v.get("vector", [0, 0, 0])))
        if isinstance(v, dict):
            v = v.get("vector", [0, 0, 0])
    if isinstance(v, list):
        out = []
        for c in v[:3]:
            try:
                out.append(float(c))
            except (TypeError, ValueError):
                out.append(0.0)
        return out + [0.0] * (3 - len(out))
    try:
        f = float(v)
        return [f, f, f]
    except (TypeError, ValueError):
        return [0.0, 0.0, 0.0]


def _track(ch, length, fps=60):
    t = np.arange(0, max(length, 1 / fps), 1 / fps)
    if not isinstance(ch, dict) or not ch:
        v = _val(ch)
        return t, np.tile(v, (len(t), 1))
    keys = []
    for k, v in ch.items():
        try:
            keys.append((float(k), _val(v)))
        except ValueError:
            pass
    if not keys:
        return t, np.zeros((len(t), 3))
    keys.sort()
    kt = np.array([k for k, _ in keys])
    kv = np.array([v for _, v in keys])
    return t, np.stack([np.interp(t, kt, kv[:, i]) for i in range(3)], 1)


def motion(anim, bone_filter=ARM, fps=60):
    """Angular speed (deg/s) summed over the matching bones."""
    length = float(anim.get("animation_length", 1.0))
    t = np.arange(0, max(length, 1 / fps), 1 / fps)
    sp = np.zeros(len(t))
    for name, b in anim.get("bones", {}).items():
        if bone_filter is not None and not bone_filter.search(name):
            continue
        if "rotation" not in b:
            continue
        _, v = _track(b["rotation"], length, fps)
        v = v[: len(t)]
        d = np.linalg.norm(np.diff(v, axis=0, prepend=v[:1]), axis=1) * fps
        sp[: len(d)] += d
    return t, sp


def swing_peaks(anim, k=4, min_gap=0.25, rel=0.35, bone_filter=ARM):
    """[(swish_start, peak, hit)] of the fastest motions (peak >= rel * max)."""
    t, sp = motion(anim, bone_filter)
    if sp.max() <= 0:
        return []
    sm = np.convolve(sp, np.ones(5) / 5, mode="same")
    out = []
    order = np.argsort(-sm)
    for i in order:
        if sm[i] < rel * sm.max() or len(out) >= k:
            break
        if any(abs(t[i] - p) < min_gap for _, p, _ in out):
            continue
        a = i
        while a > 0 and sm[a - 1] > 0.3 * sm[i]:
            a -= 1
        b = i
        while b < len(sm) - 1 and sm[b + 1] > 0.3 * sm[i]:
            b += 1
        out.append((round(float(t[a]), 3), round(float(t[i]), 3), round(float(t[b]), 3)))
    return sorted(out, key=lambda x: x[1])


def foot_strikes(anim, bone_re=r"right_(leg|thigh)$|^leg_r|r_leg", axis=0):
    """Two foot strikes per walk cycle: the extremes of the leg swing (right leg forward = left foot back and vice versa)."""
    length = float(anim.get("animation_length", 1.0))
    rx = re.compile(bone_re, re.I)
    for name, b in anim.get("bones", {}).items():
        if rx.search(name) and "rotation" in b:
            t, v = _track(b["rotation"], length)
            x = v[:, axis]
            return sorted([round(float(t[np.argmin(x)]), 3), round(float(t[np.argmax(x)]), 3)])
    return []


def apply(path, plan, ns="pohsmp_core"):
    """plan: {anim_name: [(time, "id[|vol|pitch]"), ...]}; returns count of keyframes written."""
    raw = open(path, encoding="utf-8").read()
    data = json.loads(raw)
    anims = data["animations"]
    n = 0
    for name, events in plan.items():
        if name not in anims:
            print("!! no animation", name, "in", path, file=sys.stderr)
            continue
        se = {}
        for tm, eff in sorted(events, key=lambda e: e[0]):
            tm = max(0.0, round(float(tm), 3))
            while ("%g" % tm) in se:
                tm = round(tm + 0.001, 3)
            se["%g" % tm] = {"effect": eff if ":" in eff.split("|")[0] else ns + ":" + eff}
            n += 1
        anims[name]["sound_effects"] = se
    with open(path, "w", encoding="utf-8") as f:   # keep the files' compact one-line format
        f.write(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ("\n" if raw.endswith("\n") else ""))
    return n


if __name__ == "__main__":
    d = json.load(open(sys.argv[1], encoding="utf-8"))["animations"]
    for name in sys.argv[2:] or d:
        a = d[name]
        print(f"{name:42s} len={a.get('animation_length')} peaks={swing_peaks(a)}")
