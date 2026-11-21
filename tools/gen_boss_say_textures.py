"""Textures of the bosses' on-screen lines (BossSayClient): textures/gui/boss_say/<boss>.png and <boss>_mark.png.

<boss>.png: 48x32 9-slice (corners 12x8; the top/bottom edges are plain along x, the sides along y, the middle along x - they are
stretched). A pixel scroll in the vanilla / Iron's GUI manner: a soft two-step shadow outside, a 1 px border, a dark gap, a thin inner
line, a translucent body with a vertical shade, small corner ornaments. <boss>_mark.png: 18x9, the mark left of the name and its mirror.
Run from the repository root: python3 tools/gen_boss_say_textures.py
"""
import math
import os

from PIL import Image

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "main", "resources", "assets", "pohsmp_core",
                   "textures", "gui", "boss_say")
W, H, SIDE, EDGE, R = 48, 32, 12, 8, 6

# per boss: body top / bottom (rgb), body alpha, border, inner line (rgba), shadow, extras
STYLES = {
    # «пепел и огонь»: ash body, ember border, a warm glow along the bottom, tiny flames at the corners
    "cult_leader": dict(top=(34, 26, 24), bot=(20, 15, 14), a=218, border=(226, 122, 44), border2=(150, 66, 22),
                        inner=(104, 90, 82, 170), shadow=(12, 6, 4), glow=(255, 120, 30), corner="flame"),
    # «лиловое с красной нитью»: violet body, lilac border, a red thread inside, red knots at the corners
    "irina": dict(top=(40, 22, 54), bot=(24, 12, 34), a=218, border=(196, 158, 240), border2=(120, 86, 170),
                  inner=(206, 40, 64, 230), shadow=(10, 4, 16), corner="knot"),
    # «бирюза и металл»: dark teal body, steel border, a turquoise inner line, rivets
    "aris": dict(top=(18, 36, 38), bot=(10, 22, 24), a=220, border=(162, 176, 182), border2=(88, 100, 106),
                 inner=(70, 214, 198, 200), shadow=(2, 10, 10), corner="rivet"),
    # «золото / серебро»: dark warm body, gold border, a silver inner line, gold studs
    "martin": dict(top=(32, 29, 22), bot=(18, 16, 12), a=220, border=(222, 182, 76), border2=(140, 106, 34),
                   inner=(200, 206, 216, 190), shadow=(8, 6, 2), corner="stud"),
    # «стекло / золото»: a clearer glass body with a sheen, a thin gold border, a pale glass inner line
    "ereb": dict(top=(26, 36, 52), bot=(14, 20, 30), a=176, border=(234, 202, 108), border2=(150, 120, 50),
                 inner=(186, 214, 238, 120), shadow=(4, 6, 12), sheen=(255, 255, 255), corner="glass"),
    # «фиолетово-золотое стекло»: violet glass with a lavender sheen, gold border, violet inner line, violet gems
    "ereb_hand": dict(top=(40, 24, 62), bot=(22, 12, 38), a=182, border=(236, 180, 78), border2=(150, 100, 36),
                      inner=(160, 112, 230, 190), shadow=(8, 2, 14), sheen=(222, 204, 255), corner="gem"),
    "default": dict(top=(30, 30, 36), bot=(18, 18, 22), a=210, border=(170, 170, 180), border2=(90, 90, 100),
                    inner=(120, 120, 130, 150), shadow=(4, 4, 6), corner=None),
}

# 9x9 marks by the name: . empty, the letters are colours of MARK_PAL[boss]
MARKS = {
    "cult_leader": ["....y....", "...yo....", "...oo.y..", "..oor.o..", "..orroo..", ".orrdro..", ".ordddro.", "..rdddr..", "...rrr..."],
    "irina": [".........", ".ll...ll.", "lrrl.lrrl", "lrrrlrrrl", ".lrrrrrl.", "..lrrrl..", "...lrl...", "....l....", "....t...."],
    "aris": [".........", ".ssssss..", ".sllllss.", ".ssssss..", "...dt....", "...dt....", "...dt....", "...dt....", "...dd...."],
    "martin": ["...ggg...", "..gwwwg..", ".gwssswg.", ".gwssswg.", ".gwssswg.", "..gwswg..", "...gwg...", "....g....", "........."],
    "ereb": ["gg.....gg", "gpg...gpg", "gppg.gppg", ".gppgppg.", "..ggggg..", ".gpg.gpg.", "gppg.gppg", ".gg...gg.", "........."],
    "ereb_hand": ["...g.g...", "..gvgvg..", ".gvvvvvg.", ".gvlvlvg.", ".gvvvvvg.", "..gvvvg..", "...gvg...", "....g....",
                  "........."],
    "default": [".........", ".........", "....w....", "...www...", "..wwwww..", "...www...", "....w....", ".........", "........."],
}
MARK_PAL = {
    "cult_leader": {"y": (255, 222, 120), "o": (255, 150, 40), "r": (214, 70, 24), "d": (110, 30, 12)},
    "irina": {"l": (196, 158, 240), "r": (214, 44, 70), "t": (206, 40, 64)},
    "aris": {"s": (170, 184, 190), "l": (90, 230, 214), "d": (96, 60, 36), "t": (140, 92, 52)},
    "martin": {"g": (226, 186, 80), "w": (236, 238, 244), "s": (176, 182, 196)},
    "ereb": {"g": (236, 204, 110), "p": (200, 226, 250)},
    "ereb_hand": {"g": (238, 184, 80), "v": (150, 100, 226), "l": (240, 228, 255)},
    "default": {"w": (200, 200, 210)},
}


def inset(x, y):
    """How many pixels (x, y) lies inside the rounded rectangle's outline (0 = the outermost ring, <0 = outside)."""
    cx = min(x, W - 1 - x)
    cy = min(y, H - 1 - y)
    if cx < R and cy < R:
        d = R - math.hypot(R - cx - 0.5, R - cy - 0.5)
        return int(math.floor(d + 0.35))
    return min(cx, cy)


def lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(len(a)))


def frame(s):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    px = img.load()
    for y in range(H):
        # the shade by rows: kept the same along x, so every slice stretches cleanly
        t = (y - 3) / (H - 7)
        body = lerp(s["top"], s["bot"], max(0.0, min(1.0, t)))
        for x in range(W):
            d = inset(x, y)
            if d < 0:
                continue
            if d == 0:
                c = s["shadow"] + (46,)
            elif d == 1:
                c = s["shadow"] + (110,)
            elif d == 2:
                c = (s["border"] if y < H / 2 else lerp(s["border"], s["border2"], 0.45)) + (255,)
            elif d == 3:
                c = lerp(body, (0, 0, 0), 0.35) + (min(255, s["a"] + 20),)
            elif d == 4:
                c = s["inner"]
            else:
                c = body + (s["a"],)
                if "glow" in s and y >= H - 9:   # embers under the ash: a warm glow along the bottom
                    k = (y - (H - 9)) / 4.0
                    c = lerp(body, s["glow"], 0.10 * min(1.0, k)) + (s["a"],)
                if "sheen" in s and y in (6, 7):   # glass: a bright streak under the top edge
                    c = lerp(body, s["sheen"], 0.22 if y == 6 else 0.09) + (s["a"] + 10,)
            px[x, y] = c
    corner(px, s)
    return img


def put(px, x, y, c):
    if 0 <= x < W and 0 <= y < H:
        px[x, y] = c if len(c) == 4 else c + (255,)


def corner(px, s):
    kind = s.get("corner")
    for fx, fy in ((False, False), (True, False), (False, True), (True, True)):
        def P(x, y, c):   # draw in the top-left corner's coordinates, mirrored to the others
            put(px, W - 1 - x if fx else x, H - 1 - y if fy else y, c)
        if kind == "flame":   # a tiny flame licking out of the border
            P(3, 2, (255, 150, 40)); P(2, 3, (255, 150, 40)); P(3, 3, (255, 214, 110)); P(4, 2, (214, 70, 24))
            P(2, 4, (214, 70, 24)); P(1, 1, (255, 120, 30, 120))
        elif kind == "knot":   # a red knot of the thread
            P(4, 4, (230, 60, 84)); P(5, 4, (170, 30, 50)); P(4, 5, (170, 30, 50)); P(3, 3, (196, 158, 240))
            P(5, 5, (206, 40, 64))
        elif kind == "rivet":   # a steel rivet with a highlight
            P(4, 4, (226, 234, 236)); P(5, 4, (150, 162, 168)); P(4, 5, (150, 162, 168)); P(5, 5, (70, 80, 86))
        elif kind == "stud":   # a gold diamond stud
            P(4, 3, (250, 220, 120)); P(3, 4, (226, 186, 80)); P(4, 4, (255, 240, 180)); P(5, 4, (180, 140, 50))
            P(4, 5, (150, 112, 36))
        elif kind == "glass":   # gold corner with a glint
            P(3, 3, (255, 236, 160)); P(4, 3, (234, 202, 108)); P(3, 4, (234, 202, 108)); P(2, 2, (255, 255, 255, 140))
        elif kind == "gem":   # a violet gem in gold
            P(3, 3, (238, 184, 80)); P(4, 4, (176, 128, 246)); P(5, 4, (110, 70, 190)); P(4, 5, (110, 70, 190))
            P(5, 5, (236, 180, 78)); P(2, 2, (255, 255, 255, 120))


def mark(name):
    rows, pal = MARKS[name], MARK_PAL[name]
    img = Image.new("RGBA", (18, 9), (0, 0, 0, 0))
    for y, row in enumerate(rows):
        for x, ch in enumerate(row[:9]):
            if ch in pal:
                img.putpixel((x, y), pal[ch] + (255,))
                img.putpixel((17 - x, y), pal[ch] + (255,))
    return img


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, s in STYLES.items():
        frame(s).save(os.path.join(OUT, name + ".png"))
        mark(name).save(os.path.join(OUT, name + "_mark.png"))
    print("written", len(STYLES) * 2, "textures to", os.path.normpath(OUT))


if __name__ == "__main__":
    main()
