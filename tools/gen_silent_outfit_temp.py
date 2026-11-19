"""
TEMPORARY Silent Witch outfit (T19) until the ideas chat ships tools/gen_silent_outfit.py with the real model.

Writes, under src/main/resources/assets/pohsmp_core/:
  geo/armor/silent_witch_outfit.geo.json            one GeckoLib armor model for the three pieces
  animations/armor/silent_witch_outfit.animation.json   idle / walk / run / cast (cloak) + nero_idle (cat)
  textures/armor/silent_witch_outfit.png (+ _glowmask.png: only the gold trim, glows at night)
  textures/item/silent_witch_{hood,robe,skirt}.png + models/item/*.json   inventory icons
  textures/mob_effect/silent_barrier_cooldown.png

Contract the code relies on (keep it in the real model):
  bones armorHead, armorBody, armorRightArm, armorLeftArm, armorRightLeg, armorLeftLeg (GeckoLib armor, Bedrock player coordinates);
  "nero" - the cat, child of armorBody, on the left shoulder (hidden by code outside the full set and while running);
  animations "idle", "walk", "run", "cast" (controller "cloak") and "nero_idle" (controller "nero"); do not animate the armor* bones themselves.
Run: python tools/gen_silent_outfit_temp.py   (needs Pillow)
"""
import json, os
from PIL import Image, ImageDraw

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "main", "resources", "assets", "pohsmp_core")
NAVY, NAVY_D, GOLD, LILAC, BLACK, EYE = (24, 32, 74, 255), (14, 19, 46, 255), (226, 182, 74, 255), (150, 112, 196, 255), (16, 14, 20, 255), (250, 214, 60, 255)
NONE = (0, 0, 0, 0)

# ---------------------------------------------------------------- texture atlas (64x64): name -> (u, v, w, h)
SW = {
    "navy": (0, 0, 8, 8), "trim": (8, 0, 8, 8), "lilac": (16, 0, 8, 8), "frame": (24, 0, 8, 8), "black": (32, 0, 4, 4),
    "eye": (36, 0, 2, 2), "gold": (40, 0, 4, 4), "navy_d": (44, 0, 4, 4), "hem": (0, 8, 16, 8),
}


def atlas():
    img, glow = Image.new("RGBA", (64, 64), NONE), Image.new("RGBA", (64, 64), NONE)
    d, g = ImageDraw.Draw(img), ImageDraw.Draw(glow)

    def fill(name, col):
        u, v, w, h = SW[name]
        d.rectangle([u, v, u + w - 1, v + h - 1], fill=col)

    fill("navy", NAVY); fill("lilac", LILAC); fill("black", BLACK); fill("eye", EYE); fill("navy_d", NAVY_D)
    fill("gold", GOLD); u, v, w, h = SW["gold"]; g.rectangle([u, v, u + w - 1, v + h - 1], fill=GOLD)
    for name in ("trim", "hem"):   # navy with a gold zigzag along the bottom edge
        u, v, w, h = SW[name]
        d.rectangle([u, v, u + w - 1, v + h - 1], fill=NAVY)
        for x in range(w):
            y = v + h - 2 - (x % 4 if x % 4 < 2 else 4 - x % 4)
            for yy in (y, y + 1):
                d.point((u + x, yy), GOLD); g.point((u + x, yy), GOLD)
        d.line([u, v + h - 1, u + w - 1, v + h - 1], fill=GOLD); g.line([u, v + h - 1, u + w - 1, v + h - 1], fill=GOLD)
    u, v, w, h = SW["frame"]   # hood opening: navy rim with gold edge, see-through middle
    d.rectangle([u, v, u + w - 1, v + h - 1], fill=NAVY)
    d.rectangle([u + 1, v + 1, u + w - 2, v + h - 1], fill=GOLD); g.rectangle([u + 1, v + 1, u + w - 2, v + h - 1], fill=GOLD)
    d.rectangle([u + 2, v + 2, u + w - 3, v + h - 1], fill=NONE); g.rectangle([u + 2, v + 2, u + w - 3, v + h - 1], fill=NONE)
    return img, glow


def faces(sw, front=None, sides=None):
    u, v, w, h = SW[sw]
    f = {k: {"uv": [u, v], "uv_size": [w, h]} for k in ("north", "south", "east", "west", "up", "down")}
    for k, s in ((("north",), front), (("east", "west", "south"), sides)):
        if s:
            uu, vv, ww, hh = SW[s]
            for kk in k:
                f[kk] = {"uv": [uu, vv], "uv_size": [ww, hh]}
    return f


def cube(origin, size, sw, inflate=0.0, rot=None, pivot=None, front=None, sides=None):
    c = {"origin": origin, "size": size, "uv": faces(sw, front, sides)}
    if inflate:
        c["inflate"] = inflate
    if rot:
        c["rotation"] = rot
        c["pivot"] = pivot
    return c


def bone(name, pivot, cubes=(), parent=None, rot=None):
    b = {"name": name, "pivot": pivot}
    if parent:
        b["parent"] = parent
    if rot:
        b["rotation"] = rot
    if cubes:
        b["cubes"] = list(cubes)
    return b


def model():
    bones = [
        # hood: shell over the head, pointed tail at the back, gold rim around the face opening
        bone("armorHead", [0, 24, 0], [cube([-4, 24, -4], [8, 8, 8], "navy", 0.9, front="frame")]),
        bone("hood_tip", [0, 30, 4], [cube([-2, 27, 4.5], [4, 4, 3], "navy", 0.2), cube([-1, 26, 7], [2, 2, 2], "trim")], "armorHead", [-25, 0, 0]),
        # robe: torso, collar, lilac lining, cloak at the back (cape -> cape_hem), Nero on the left shoulder
        bone("armorBody", [0, 24, 0], [cube([-4, 12, -2], [8, 12, 4], "navy", 0.6, front="navy_d"),
                                        cube([-4.5, 22.5, -2.6], [9, 2, 5.2], "trim", 0.2)]),
        bone("cape", [0, 24, 2.6], [cube([-5, 9, 2.6], [10, 15, 0.6], "navy", 0, sides="lilac")], "armorBody"),
        bone("cape_hem", [0, 9, 2.6], [cube([-5.5, -1, 2.6], [11, 10, 0.6], "hem", 0, sides="lilac")], "cape"),
        bone("nero", [5.5, 24.6, 0], [cube([4.2, 24.6, -1.5], [2.6, 2.2, 3.6], "black")], "armorBody"),
        bone("nero_head", [5.5, 26.3, -1.2], [cube([4.1, 25.8, -3.4], [2.8, 2.6, 2.4], "black"),
                                               cube([4.2, 28.4, -2.6], [0.8, 0.9, 0.8], "black"), cube([6.0, 28.4, -2.6], [0.8, 0.9, 0.8], "black")], "nero"),
        bone("nero_eyes", [5.5, 27.2, -3.45], [cube([4.5, 26.9, -3.5], [0.6, 0.6, 0.1], "eye"), cube([5.9, 26.9, -3.5], [0.6, 0.6, 0.1], "eye")], "nero_head"),
        bone("nero_tail", [5.5, 25.2, 2.1], [cube([5.2, 21.6, 1.9], [0.6, 3.8, 0.6], "black")], "nero", [10, 0, 0]),
        # sleeves with wide gold-trimmed cuffs
        bone("armorRightArm", [-5, 22, 0], [cube([-8, 12, -2], [4, 12, 4], "navy", 0.55)]),
        bone("cuff_r", [-6, 14, 0], [cube([-8.6, 11, -2.6], [5.2, 3.5, 5.2], "trim", 0.15)], "armorRightArm"),
        bone("armorLeftArm", [5, 22, 0], [cube([4, 12, -2], [4, 12, 4], "navy", 0.55)]),
        bone("cuff_l", [6, 14, 0], [cube([3.4, 11, -2.6], [5.2, 3.5, 5.2], "trim", 0.15)], "armorLeftArm"),
        # robe skirt: a panel around each leg that flares and sways
        bone("armorRightLeg", [-1.9, 12, 0], [cube([-3.9, 4, -2], [4, 8, 4], "navy", 0.5)]),
        bone("skirt_r", [-1.9, 12, 0], [cube([-4.6, -0.5, -2.7], [5.4, 12.5, 5.4], "lilac", 0.05, front="hem", sides="hem")], "armorRightLeg"),
        bone("armorLeftLeg", [1.9, 12, 0], [cube([-0.1, 4, -2], [4, 8, 4], "navy", 0.5)]),
        bone("skirt_l", [1.9, 12, 0], [cube([-0.8, -0.5, -2.7], [5.4, 12.5, 5.4], "lilac", 0.05, front="hem", sides="hem")], "armorLeftLeg"),
    ]
    return {"format_version": "1.12.0", "minecraft:geometry": [{
        "description": {"identifier": "geometry.silent_witch_outfit", "texture_width": 64, "texture_height": 64,
                        "visible_bounds_width": 3, "visible_bounds_height": 3.5, "visible_bounds_offset": [0, 1.25, 0]},
        "bones": bones}]}


def kf(points):
    return {("%.2f" % t): v for t, v in points}


def sway(period, amp_x, base_x=0.0, amp_z=0.0, steps=8):
    import math
    pts = []
    for i in range(steps + 1):
        t = period * i / steps
        a = 2 * math.pi * i / steps
        pts.append((t, [round(base_x + amp_x * math.sin(a), 2), 0, round(amp_z * math.sin(a + 1.3), 2)]))
    return kf(pts)


def anim():
    # cape: negative X lifts the cloak away from the back
    a = {
        "idle": {"loop": True, "animation_length": 4.0, "bones": {
            "cape": {"rotation": sway(4.0, 2.0, -4, 1.5)}, "cape_hem": {"rotation": sway(4.0, 3.0, -2)},
            "skirt_r": {"rotation": sway(4.0, 1.2)}, "skirt_l": {"rotation": sway(4.0, -1.2)}}},
        "walk": {"loop": True, "animation_length": 1.0, "bones": {
            "cape": {"rotation": sway(1.0, 4.0, -14, 3)}, "cape_hem": {"rotation": sway(1.0, 7.0, -10)},
            "skirt_r": {"rotation": sway(1.0, 4.0, 0, 2)}, "skirt_l": {"rotation": sway(1.0, -4.0, 0, -2)}}},
        "run": {"loop": True, "animation_length": 0.6, "bones": {
            "cape": {"rotation": sway(0.6, 6.0, -38, 4)}, "cape_hem": {"rotation": sway(0.6, 10.0, -22)},
            "skirt_r": {"rotation": sway(0.6, 7.0, -6, 3)}, "skirt_l": {"rotation": sway(0.6, -7.0, -6, -3)}}},
        "cast": {"loop": True, "animation_length": 2.0, "bones": {
            "cape": {"rotation": sway(2.0, 6.0, -55, 6)}, "cape_hem": {"rotation": sway(2.0, 12.0, -30)},
            "skirt_r": {"rotation": sway(2.0, 5.0, -10, 4)}, "skirt_l": {"rotation": sway(2.0, -5.0, -10, -4)},
            "hood_tip": {"rotation": sway(2.0, 6.0, -10)}}},
        "nero_idle": {"loop": True, "animation_length": 6.0, "bones": {
            "nero_eyes": {"scale": kf([(0, [1, 1, 1]), (2.3, [1, 1, 1]), (2.4, [1, 0.1, 1]), (2.5, [1, 1, 1]), (4.9, [1, 1, 1]),
                                       (5.0, [1, 0.1, 1]), (5.1, [1, 1, 1]), (6.0, [1, 1, 1])])},
            "nero_head": {"rotation": kf([(0, [0, 0, 0]), (1.0, [0, 0, 0]), (1.6, [0, 35, 0]), (2.8, [0, 35, 0]), (3.4, [-8, -25, 0]),
                                          (4.6, [-8, -25, 0]), (5.2, [0, 0, 0]), (6.0, [0, 0, 0])])},
            "nero_tail": {"rotation": {("%.2f" % t): [10, (25 if i % 2 else -25), 0]
                                       for i, t in enumerate([0.0, 0.75, 1.5, 2.25, 3.0, 3.75, 4.5, 5.25, 6.0])}}}},
    }
    return {"format_version": "1.8.0", "animations": a, "geckolib_format_version": 2}


def icon(kind):
    img = Image.new("RGBA", (16, 16), NONE)
    d = ImageDraw.Draw(img)
    if kind == "hood":
        d.polygon([(3, 14), (3, 7), (6, 3), (10, 2), (13, 6), (13, 14)], fill=NAVY)
        d.polygon([(5, 14), (5, 8), (8, 5), (11, 8), (11, 14)], fill=NAVY_D)
        d.line([(3, 14), (3, 7), (6, 3), (10, 2), (13, 6), (13, 14)], fill=GOLD)
        d.line([(5, 14), (5, 8), (8, 5), (11, 8), (11, 14)], fill=LILAC)
    elif kind == "robe":
        d.polygon([(4, 2), (12, 2), (15, 7), (13, 8), (12, 6), (12, 15), (4, 15), (4, 6), (3, 8), (1, 7)], fill=NAVY)
        d.line([(7, 2), (8, 6), (9, 2)], fill=GOLD)
        for x in range(4, 13):
            d.point((x, 14 - (x % 2)), GOLD)
        d.line([(8, 6), (8, 13)], fill=LILAC)
    else:
        d.polygon([(4, 2), (12, 2), (14, 15), (2, 15)], fill=NAVY)
        d.line([(8, 3), (8, 14)], fill=LILAC)
        for x in range(2, 15):
            d.point((x, 14 - (x % 2)), GOLD)
        d.line([(4, 2), (12, 2)], fill=GOLD)
    return img


def effect_icon():
    img = Image.new("RGBA", (18, 18), NONE)
    d = ImageDraw.Draw(img)
    d.ellipse([1, 1, 16, 16], outline=(127, 255, 208, 255), width=2)
    d.ellipse([5, 5, 12, 12], outline=(127, 255, 208, 160), width=1)
    d.line([(9, 3), (9, 6)], fill=(226, 182, 74, 255))
    d.line([(9, 9), (12, 9)], fill=(226, 182, 74, 255))
    return img


def write(rel, data):
    p = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    if isinstance(data, Image.Image):
        data.save(p)
    else:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
            f.write("\n")
    print("wrote", rel)


if __name__ == "__main__":
    img, glow = atlas()
    write("textures/armor/silent_witch_outfit.png", img)
    write("textures/armor/silent_witch_outfit_glowmask.png", glow)
    write("geo/armor/silent_witch_outfit.geo.json", model())
    write("animations/armor/silent_witch_outfit.animation.json", anim())
    for k in ("hood", "robe", "skirt"):
        write("textures/item/silent_witch_%s.png" % k, icon(k))
        write("models/item/silent_witch_%s.json" % k, {"parent": "item/generated", "textures": {"layer0": "pohsmp_core:item/silent_witch_%s" % k}})
    write("textures/mob_effect/silent_barrier_cooldown.png", effect_icon())
