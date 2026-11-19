"""T14: temporary 16x16 icons of the fire sword-whip ("Раскалённые угли") until the manager's model.

ember_blade.png      — sword form: dark steel curved blade, ring guard, leather grip, ember glints in the edge;
ember_blade_hot.png  — whip form: the blade glows orange and a flaming lash curls off its tip.
Run: python -I tools/gen_ember_blade.py
"""
import math
import os
import struct
import zlib

OUT = os.path.join(os.path.dirname(__file__), "..", "src", "main", "resources", "assets", "pohsmp_core", "textures", "item")


def png(path, px):
    raw = b"".join(b"\x00" + bytes(c for p in row for c in p) for row in px)

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 16, 16, 8, 6, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def hexc(h, a=255):
    return (int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16), a)


def blank():
    return [[(0, 0, 0, 0)] * 16 for _ in range(16)]


def put(px, x, y, c):
    if 0 <= x < 16 and 0 <= y < 16:
        px[y][x] = c


# blade spine: from the guard (6,9) to the tip (14,1), bowed outward (curved blade)
def spine():
    pts = []
    for i in range(10):
        t = i / 9
        x = 6 + 8 * t + math.sin(t * math.pi) * 1.1
        y = 9 - 8 * t + math.sin(t * math.pi) * 1.1
        pts.append((round(x), round(y)))
    return pts


def draw(hot):
    px = blank()
    steel, edge, dark = hexc("#4A4E58"), hexc("#9AA0AC"), hexc("#23252B")
    if hot:
        steel, edge, dark = hexc("#E0521A"), hexc("#FFE7A0"), hexc("#8A2A0C")
    pts = spine()
    for i, (x, y) in enumerate(pts):
        put(px, x, y, steel)
        if i < len(pts) - 1:
            put(px, x + 1, y + 1, dark)   # back of the blade
            put(px, x - 1, y, edge if i % 3 else (hexc("#FF8A3A") if not hot else edge))   # edge with ember glints
    # ring guard around (5,10)
    ring = hexc("#B8742A") if not hot else hexc("#FFB040")
    for (x, y) in [(4, 9), (5, 9), (6, 10), (6, 11), (5, 12), (4, 12), (3, 11), (3, 10)]:
        put(px, x, y, ring)
    put(px, 4, 10, hexc("#FF6A1A") if hot else hexc("#5A0E08"))
    # grip down-left
    grip = hexc("#3A2418")
    for (x, y) in [(3, 12), (2, 13), (1, 14)]:
        put(px, x, y, grip)
    put(px, 0, 15, hexc("#B8742A"))
    if hot:   # the lash curling from the tip
        lash = [(15, 2), (15, 3), (14, 4), (13, 5), (13, 6), (14, 7)]
        for i, (x, y) in enumerate(lash):
            put(px, x, y, hexc("#FFB040") if i % 2 else hexc("#FF6A1A"))
        for (x, y) in [(12, 0), (15, 0), (10, 2)]:
            put(px, x, y, hexc("#FFE7A0", 200))
    return px


if __name__ == "__main__":
    png(os.path.join(OUT, "ember_blade.png"), draw(False))
    png(os.path.join(OUT, "ember_blade_hot.png"), draw(True))
    print("ember_blade icons written")
