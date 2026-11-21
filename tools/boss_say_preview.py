"""Preview of the bosses' on-screen lines (BossSayClient) over a game-like frame, for mock-ups and the animation.

Repeats the client's layout and timing exactly (the constants and formulas of BossSayMath, the 9-slice and the marks of
BossSayClient) and draws the text with the vanilla bitmap font (ascii / accented / nonlatin_european from the Minecraft client jar,
advance = glyph width + 1, shadow +1 px at 25% colour, italic = the glyph sheared 1 px at the top as in BakedGlyph). The background is
a simple perspective arena of vanilla block textures and the vanilla HUD (hotbar, hearts, food, xp) at GUI scale 3.

  python3 tools/boss_say_preview.py mockups   -> docs/media/boss_say_mockups.png
  python3 tools/boss_say_preview.py video     -> docs/media/video/boss_say.mp4 (ffmpeg)
  python3 tools/boss_say_preview.py sysline <title_ru_before.png> -> docs/media/t26_name_ru_and_sysline.png
        (the Cult Leader's ru title before/after, the system lines of a fight beside a spoken line; owner 21.11)
Needs Pillow + numpy and the client jar of ForgeGradle (~/.gradle/caches/forge_gradle/minecraft_repo/versions/1.20.1/client.jar).
"""
import io
import json
import math
import os
import subprocess
import sys
import tempfile
import zipfile

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
JAR = os.path.expanduser("~/.gradle/caches/forge_gradle/minecraft_repo/versions/1.20.1/client.jar")
TEX = os.path.join(ROOT, "src/main/resources/assets/pohsmp_core/textures/gui/boss_say")
LANG = os.path.join(ROOT, "src/main/resources/assets/pohsmp_core/lang/ru_ru.json")

SW, SH, S = 1280, 720, 3                 # window, GUI scale
GW, GH = SW // S, SH // S                # GUI size (426 x 240)

# ---- BossSayMath (keep in step with the Java) ----
CPS, IN, TYPE_DELAY, OUT = 40, 7, 3, 10
HOLD_BASE, HOLD_PER_CHAR, QUEUE_HOLD, RISE = 50, 1.2, 30, 6
PAD_X, PAD_TOP, PAD_BOTTOM, NAME_H, NAME_GAP, LINE_H = 14, 6, 6, 9, 5, 10
MAX_TEXT, MIN_TEXT, SCREEN_MARGIN, ACTIONBAR_CLEAR = 300, 100, 10, 74


def type_ticks(n): return n * 20.0 / CPS
def hold(n): return HOLD_BASE + HOLD_PER_CHAR * n
def typed_at(n): return TYPE_DELAY + type_ticks(n)
def out_at(n): return typed_at(n) + hold(n)
def smooth(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)


def visible(age, n):
    return 0 if age <= TYPE_DELAY else int(min(n, math.floor((age - TYPE_DELAY) * CPS / 20.0)))


def alpha(age, oat):
    if age < 0: return 0.0
    o = 1 if age <= oat else max(0.0, 1 - (age - oat) / OUT)
    return smooth(min(1, age / IN)) * smooth(o)


def rise(age, oat):
    r = RISE * (1 - smooth(min(1, max(0, age / IN))))
    return r + (2 * smooth(min(1, (age - oat) / OUT)) if age > oat else 0)


def max_text(gw): return max(MIN_TEXT, min(MAX_TEXT, gw - 2 * (SCREEN_MARGIN + PAD_X)))
def box_h(lines): return PAD_TOP + NAME_H + NAME_GAP + max(1, lines) * LINE_H - 1 + PAD_BOTTOM
def box_w(nw, tw, gw): return min(max(nw + 26, tw) + 2 * PAD_X, gw - 2 * SCREEN_MARGIN)


def bottom(gh, hud, bar):
    if hud <= 0: return gh - max(bar + 8, int(gh * 0.1))
    return gh - max(ACTIONBAR_CLEAR, hud + 8)


def mix(a, b, t):
    return tuple(int(round(a[i] * (1 - t) + b[i] * t)) for i in range(3))


def rgb(c): return ((c >> 16) & 255, (c >> 8) & 255, c & 255)


def wrap(text, maxw, width):
    out, line = [], ""
    for word in " ".join(text.split()).split(" "):
        probe = word if not line else line + " " + word
        if width(probe) <= maxw:
            line = probe
            continue
        if line: out.append(line); line = ""
        w = word
        while width(w) > maxw and len(w) > 1:
            cut = len(w) - 1
            while cut > 1 and width(w[:cut]) > maxw: cut -= 1
            out.append(w[:cut]); w = w[cut:]
        line = w
    if line: out.append(line)
    return out


def typed(lines, v):
    out = []
    for l in lines:
        k = min(len(l), max(0, v)); out.append(l[:k]); v -= k
    return out


# ---- vanilla assets ----
class Jar:
    def __init__(self, path):
        self.z = zipfile.ZipFile(path)

    def img(self, p):
        return Image.open(io.BytesIO(self.z.read("assets/minecraft/" + p))).convert("RGBA")

    def json(self, p):
        return json.loads(self.z.read("assets/minecraft/" + p).decode("utf-8"))


class Font:
    """The vanilla default font's bitmap providers."""

    def __init__(self, jar):
        self.g = {}
        for prov in jar.json("font/include/default.json")["providers"]:
            if prov["type"] != "bitmap": continue
            im = np.array(jar.img("textures/" + prov["file"].split(":")[1]))
            rows = prov["chars"]
            ch = im.shape[0] // len(rows); cw = im.shape[1] // len(rows[0])
            asc = prov.get("ascent", 7)
            for r, row in enumerate(rows):
                for c, chx in enumerate(row):
                    if chx in self.g or chx == "\u0000": continue
                    cell = im[r * ch:(r + 1) * ch, c * cw:(c + 1) * cw, 3] > 0
                    cols = np.where(cell.any(axis=0))[0]
                    w = int(cols[-1]) + 1 if len(cols) else 0
                    self.g[chx] = (cell, w, asc)
        self.g[" "] = (None, 3, 7)

    def adv(self, ch):
        g = self.g.get(ch)
        return 6 if g is None else g[1] + 1

    def width(self, s):
        return sum(self.adv(c) for c in s)

    def draw(self, img, s, gx, gy, color, a=1.0, italic=False, shadow=True):
        """Text at GUI (gx, gy) onto the screen image (numpy HxWx4 float), as the game draws it at scale S."""
        if shadow: self._draw(img, s, gx + 1, gy + 1, tuple(c // 4 for c in color), a, italic)
        self._draw(img, s, gx, gy, color, a, italic)

    def _draw(self, img, s, gx, gy, color, a, italic):
        x = gx
        col = np.array(color, dtype=np.float32) / 255.0
        for ch in s:
            g = self.g.get(ch)
            if g is not None and g[0] is not None:
                cell, w, asc = g
                top = gy + 7 - asc
                for r in range(cell.shape[0]):
                    shift = (1.0 - 0.25 * (r + 0.5 - 1)) if italic else 0.0   # BakedGlyph: 1 − 0.25·up
                    for c in np.where(cell[r])[0]:
                        sx = int(round((x + c + shift) * S)); sy = int((top + r) * S)
                        blend(img, sx, sy, S, S, col, a)
            x += self.adv(ch)


def blend(img, x, y, w, h, col, a):
    x0, y0, x1, y1 = max(0, x), max(0, y), min(img.shape[1], x + w), min(img.shape[0], y + h)
    if x1 <= x0 or y1 <= y0 or a <= 0: return
    img[y0:y1, x0:x1, :3] = img[y0:y1, x0:x1, :3] * (1 - a) + col[:3] * a


def blit(img, tex, gx, gy, gw, gh, u, v, uw, vh, a=1.0):
    """GuiGraphics.blit: the texture region (u, v, uw, vh) stretched to GUI (gx, gy, gw, gh), nearest, alpha × a."""
    if gw <= 0 or gh <= 0: return
    reg = tex.crop((u, v, u + uw, v + vh)).resize((gw * S, gh * S), Image.NEAREST)
    arr = np.asarray(reg, dtype=np.float32) / 255.0
    x, y = gx * S, gy * S
    x0, y0, x1, y1 = max(0, x), max(0, y), min(img.shape[1], x + gw * S), min(img.shape[0], y + gh * S)
    if x1 <= x0 or y1 <= y0: return
    sub = arr[y0 - y:y1 - y, x0 - x:x1 - x]
    al = sub[..., 3:4] * a
    img[y0:y1, x0:x1, :3] = img[y0:y1, x0:x1, :3] * (1 - al) + sub[..., :3] * al


def fill(img, gx0, gy0, gx1, gy1, color, a):
    blend(img, gx0 * S, gy0 * S, (gx1 - gx0) * S, (gy1 - gy0) * S, np.array(color, np.float32) / 255.0, a)


# ---- BossSayClient.render ----
def nine_slice(img, tex, x, y, w, h, a):
    TW, TH, SD, ED = 48, 32, 12, 8
    cw, ch, mw, mh = TW - 2 * SD, TH - 2 * ED, w - 2 * SD, h - 2 * ED
    blit(img, tex, x, y, SD, ED, 0, 0, SD, ED, a)
    blit(img, tex, x + w - SD, y, SD, ED, TW - SD, 0, SD, ED, a)
    blit(img, tex, x, y + h - ED, SD, ED, 0, TH - ED, SD, ED, a)
    blit(img, tex, x + w - SD, y + h - ED, SD, ED, TW - SD, TH - ED, SD, ED, a)
    if mw > 0:
        blit(img, tex, x + SD, y, mw, ED, SD, 0, cw, ED, a)
        blit(img, tex, x + SD, y + h - ED, mw, ED, SD, TH - ED, cw, ED, a)
    if mh > 0:
        blit(img, tex, x, y + ED, SD, mh, 0, ED, SD, ch, a)
        blit(img, tex, x + w - SD, y + ED, SD, mh, TW - SD, ED, SD, ch, a)
    if mw > 0 and mh > 0: blit(img, tex, x + SD, y + ED, mw, mh, SD, ED, cw, ch, a)


def draw_say(img, font, style, name, color, text, age, oat, gw, gh, hud, bar):
    a = alpha(age, oat)
    if a < 0.03: return
    n = len(text.strip())
    lines = wrap(text, max_text(gw), font.width)
    tw = max(font.width(l) for l in lines)
    nw = font.width(name)
    bw, bh = box_w(nw, tw, gw), box_h(len(lines))
    x, y = (gw - bw) // 2, bottom(gh, hud, bar) - bh + int(round(rise(age, oat)))
    tex = Image.open(os.path.join(TEX, style + ".png")).convert("RGBA")
    mark = Image.open(os.path.join(TEX, style + "_mark.png")).convert("RGBA")
    nine_slice(img, tex, x, y, bw, bh, a)
    ny, nx = y + PAD_TOP, gw // 2 - nw // 2
    blit(img, mark, nx - 13, ny - 1, 9, 9, 0, 0, 9, 9, a)
    blit(img, mark, nx + nw + 3, ny - 1, 9, 9, 9, 0, 9, 9, a)
    c = rgb(color)
    font.draw(img, name, nx, ny, c, a)
    # thread under the name
    width = min(bw - 2 * PAD_X, max(nw + 48, tw * 3 // 4)); half = max(8, width // 2); cx = gw // 2; ty0 = ny + NAME_H + 1
    for i in range(0, half, 2):
        k = 1 - i / half; al = a * 150 * k * k / 255
        if al * 255 < 4: continue
        fill(img, cx + i, ty0, cx + i + 2, ty0 + 1, c, al); fill(img, cx - i - 2, ty0, cx - i, ty0 + 1, c, al)
    tc = mix((0xF2, 0xEC, 0xDF), c, 0.18)
    ty = ny + NAME_H + NAME_GAP
    for i, part in enumerate(typed(lines, visible(age, n))):
        if part: font.draw(img, part, gw // 2 - font.width(lines[i]) // 2, ty + i * LINE_H, tc, a, italic=True)


SYSTEM_TEXT, SYSTEM_MARK_ALPHA = (0xD6, 0xD3, 0xCC), 0.55


def draw_sys(img, font, style, text, age, oat, gw, gh, hud, bar):
    """BossSayClient.renderSystem: the «default» scroll, no name, upright SYSTEM_TEXT, the boss marks dimmed by the first line."""
    a = alpha(age, oat)
    if a < 0.03: return
    n = len(text.strip())
    lines = wrap(text, max_text(gw) - 26, font.width)
    tw = max(font.width(l) for l in lines)
    bw = min(tw + 26 + 2 * PAD_X, gw - 2 * SCREEN_MARGIN)
    bh = PAD_TOP + max(1, len(lines)) * LINE_H - 1 + PAD_BOTTOM
    x, y = (gw - bw) // 2, bottom(gh, hud, bar) - bh + int(round(rise(age, oat)))
    tex = Image.open(os.path.join(TEX, "default.png")).convert("RGBA")
    mark = Image.open(os.path.join(TEX, style + "_mark.png")).convert("RGBA")
    nine_slice(img, tex, x, y, bw, bh, a)
    ty = y + PAD_TOP
    fw = font.width(lines[0])
    blit(img, mark, gw // 2 - fw // 2 - 13, ty - 1, 9, 9, 0, 0, 9, 9, a * SYSTEM_MARK_ALPHA)
    blit(img, mark, gw // 2 + fw // 2 + 3, ty - 1, 9, 9, 9, 0, 9, 9, a * SYSTEM_MARK_ALPHA)
    for i, part in enumerate(typed(lines, visible(age, n))):
        if part: font.draw(img, part, gw // 2 - font.width(lines[i]) // 2, ty + i * LINE_H, SYSTEM_TEXT, a)


# ---- the frame: arena + HUD ----
ARENAS = {
    "cult_leader": ("blackstone", "polished_blackstone_bricks", (70, 26, 18), (150, 70, 40)),
    "irina": ("amethyst_block", "deepslate_tiles", (40, 22, 60), (110, 70, 140)),
    "aris": ("smooth_stone", "oxidized_cut_copper", (40, 66, 70), (130, 170, 170)),
    "martin": ("stone_bricks", "polished_andesite", (110, 150, 200), (190, 210, 230)),
    "ereb": ("quartz_bricks", "crying_obsidian", (14, 16, 34), (60, 60, 100)),
    "ereb_hand": ("purpur_block", "crying_obsidian", (30, 14, 44), (90, 60, 120)),
}


def arena(jar, style, w=SW, h=SH):
    floor_t, wall_t, sky_top, sky_bot = ARENAS[style]
    ft = np.asarray(jar.img("textures/block/%s.png" % floor_t), np.float32)[..., :3] / 255
    wt = np.asarray(jar.img("textures/block/%s.png" % wall_t), np.float32)[..., :3] / 255
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    f = h * 0.9
    dx, dy = (xx - w / 2) / f, (h * 0.42 - yy) / f   # camera looks level-ish, horizon at 42%
    cam_h, wall_z, wall_top = 1.62, 14.0, 7.0
    out = np.zeros((h, w, 3), np.float32)
    t = np.clip(yy / (h * 0.42), 0, 1)[..., None]
    out[:] = np.array(sky_top, np.float32) / 255 * (1 - t) + np.array(sky_bot, np.float32) / 255 * t
    # wall plane at z = wall_z (in front), from the floor to wall_top
    wy = cam_h + dy * wall_z
    wx = dx * wall_z + 0.37
    m = (wy >= 0) & (wy <= wall_top)
    u = ((wx % 1) * 16).astype(int) % 16; v = ((1 - (wy % 1)) * 16).astype(int) % 16
    shade = 0.55 + 0.1 * (wy / wall_top)
    out[m] = wt[v[m], u[m]] * shade[m][..., None]
    # floor
    fm = (dy < 0)
    z = np.where(fm, cam_h / np.maximum(-dy, 1e-4), 0)
    fm &= z < wall_z
    fx = dx * z + 0.37
    u = ((fx % 1) * 16).astype(int) % 16; v = ((z % 1) * 16).astype(int) % 16
    fog = np.clip(z / wall_z, 0, 1)[..., None] * 0.55
    col = ft[v, u] * 0.8
    out[fm] = (col * (1 - fog) + np.array(sky_bot, np.float32) / 255 * 0.5 * fog)[fm]
    # vignette
    r = np.sqrt(((xx - w / 2) / w) ** 2 + ((yy - h / 2) / h) ** 2)
    out *= np.clip(1.1 - r * 0.6, 0, 1)[..., None]
    return out


def hud(img, jar, gw, gh):
    """Vanilla hotbar, hearts, armour, food and the xp bar (their rows: Forge leftHeight 49, rightHeight 49)."""
    wid, icons = jar.img("textures/gui/widgets.png"), jar.img("textures/gui/icons.png")
    hx = gw // 2 - 91
    blit(img, wid, hx, gh - 22, 182, 22, 0, 0, 182, 22)
    blit(img, wid, hx - 1 + 2 * 20, gh - 23, 24, 22, 0, 22, 24, 22)
    items = ["netherite_sword", "bow", "book", "golden_apple", "cooked_beef", "ender_pearl", "totem_of_undying"]
    for i, it in enumerate(items):
        blit(img, jar.img("textures/item/%s.png" % it), hx + 3 + i * 20, gh - 19, 16, 16, 0, 0, 16, 16)
    blit(img, icons, hx, gh - 29, 182, 5, 0, 64, 182, 5)
    blit(img, icons, hx, gh - 29, 140, 5, 0, 69, 140, 5)
    font_lvl = "27"
    return icons, hx, font_lvl


def hud_rows(img, font, icons, hx, gh, lvl):
    tx = hx + 91 - font.width(lvl) // 2
    for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1)): font.draw(img, lvl, tx + ox, gh - 35 + oy, (0, 0, 0), shadow=False)
    font.draw(img, lvl, tx, gh - 35, (0x80, 0xFF, 0x20), shadow=False)
    y = gh - 39
    for i in range(10):
        blit(img, icons, hx + i * 8, y, 9, 9, 16, 0, 9, 9)
        blit(img, icons, hx + i * 8, y, 9, 9, 52 if i < 8 else (61 if i == 8 else 16), 0, 9, 9)
        blit(img, icons, hx + 182 - 9 - i * 8, y, 9, 9, 16, 27, 9, 9)
        blit(img, icons, hx + 182 - 9 - i * 8, y, 9, 9, 52, 27, 9, 9)


NAMES = {}


def load_names():
    lang = json.load(open(LANG, encoding="utf-8"))
    return lang


BOSSES = [  # style, colour, lang key of the phrase
    ("cult_leader", 0xFFB040, "ui.pohsmp_core.cult_leader.replica_taunt"),
    ("irina", 0xC9A8FF, "ui.pohsmp_core.irina.replica"),
    ("aris", 0x4FE0D0, "ui.pohsmp_core.aris.surrender"),
    ("martin", 0xE8C060, "ui.pohsmp_core.martin.yield"),
    ("ereb", 0xE8C766, "ui.pohsmp_core.ereb.farewell"),
    ("ereb_hand", 0xE8B04A, "ui.pohsmp_core.ereb_hand.replica"),
]


def frame(jar, font, lang, style, says, now, scene=False, size=(SW, SH)):
    """says: [(style, colour, text, start, outAt)] of the current line (one at a time, as the queue draws)."""
    w, h = size
    gw, gh = w // S, h // S
    img = np.concatenate([arena(jar, style, w, h), np.ones((h, w, 1), np.float32)], axis=2)
    bar = 0
    if scene:
        bar = int(gh * 0.09)
    else:
        icons, hx, lvl = hud(img, jar, gw, gh)
        hud_rows(img, font, icons, hx, gh, lvl)
    for st, col, text, start, oat in says:
        if col is None:                                  # a system line
            draw_sys(img, font, st, text, now - start, oat, gw, gh, 0 if scene else 49, bar)
            continue
        name = lang["entity.pohsmp_core." + st]
        draw_say(img, font, st, name, col, text, now - start, oat, gw, gh, 0 if scene else 49, bar)
    if scene:
        fill(img, 0, 0, gw + 1, bar, (0, 0, 0), 1.0)
        fill(img, 0, gh - bar, gw + 1, gh + 1, (0, 0, 0), 1.0)
    return Image.fromarray((np.clip(img[..., :3], 0, 1) * 255).astype(np.uint8))


def label(im, text):
    d = ImageDraw.Draw(im)
    f = ImageFont.load_default(size=22)
    d.rectangle((0, 0, 20 + int(d.textlength(text, font=f)), 34), fill=(0, 0, 0))
    d.text((10, 5), text, fill=(235, 225, 200), font=f)
    return im


def mockups(jar, font, lang):
    tiles = []
    for st, col, key in BOSSES:
        text = lang[key]
        n = len(text)
        tiles.append(label(frame(jar, font, lang, st, [(st, col, text, 0, out_at(n))], typed_at(n) + 20), "%s - %s" % (st, key)))
    # in a scene (HUD hidden, letterbox) and on a narrow window (wrapping)
    st, col, key = BOSSES[3]
    text = lang[key]
    tiles.append(label(frame(jar, font, lang, st, [(st, col, text, 0, out_at(len(text)))], typed_at(len(text)) + 20, scene=True), "martin - in a scene (BossCam, letterbox)"))
    st, col, key = BOSSES[2]
    text = lang[key]
    nar = frame(jar, font, lang, st, [(st, col, text, 0, out_at(len(text)))], typed_at(len(text)) + 20, size=(720, 720))
    canvas = Image.new("RGB", (SW, SH), (24, 24, 28)); canvas.paste(nar, ((SW - 720) // 2, 0))
    tiles.append(label(canvas, "aris - narrow window 720x720 (wrapped)"))
    cols, pad = 2, 8
    sheet = Image.new("RGB", (cols * SW + (cols + 1) * pad, 4 * SH + 5 * pad), (12, 12, 14))
    for i, t in enumerate(tiles):
        sheet.paste(t, (pad + (i % cols) * (SW + pad), pad + (i // cols) * (SH + pad)))
    out = os.path.join(ROOT, "docs/media/boss_say_mockups.png")
    sheet.save(out, optimize=True)
    print("written", out, sheet.size)


def video(jar, font, lang):
    """Ereb, Hand of Lies: his arrival line, and while it holds the Replica taunt comes (queued: the first holds 1.5 s, then the next)."""
    st, col = "ereb_hand", 0xE8B04A
    a, b = lang["ui.pohsmp_core.ereb_hand.spawn"], lang["ui.pohsmp_core.ereb_hand.replica"]
    # queue as BossSayMath.Queue: b is pushed at t = 40 while a holds
    a_start, b_push = 10, 40
    a_out = min(out_at(len(a)), max(typed_at(len(a)), b_push - a_start) + QUEUE_HOLD)
    b_start = a_start + a_out + OUT
    end = b_start + out_at(len(b)) + OUT + 10
    fps = 30
    tmp = tempfile.mkdtemp()
    bg_cache = {}
    n = int(end / 20 * fps)
    for i in range(n):
        t = i * 20 / fps
        says = [(st, col, a, a_start, a_out)] if t < b_start else [(st, col, b, b_start, out_at(len(b)))]
        frame(jar, font, lang, st, says, t).save(os.path.join(tmp, "f%04d.png" % i))
    out = os.path.join(ROOT, "docs/media/video/boss_say.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", os.path.join(tmp, "f%04d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", out], check=True)
    print("written", out, n, "frames")


def sysline(jar, font, lang, before):
    """The ru title of the Cult Leader before/after and the system lines of a fight on screen beside a spoken line."""
    tiles = []
    for path, cap in ((before, "title ru - before (Tyros, First Flamebearer)"),
                      (os.path.join(ROOT, "src/main/resources/assets/pohsmp_core/textures/gui/title/cult_leader_ru.png"),
                       "title ru - after (owner 21.11: the Russian name)")):
        t = Image.open(path).convert("RGBA")
        bg = Image.fromarray((np.clip(arena(jar, "cult_leader"), 0, 1) * 255).astype(np.uint8)).convert("RGBA")
        k = SW * 0.8 / t.width
        t = t.resize((int(t.width * k), int(t.height * k)), Image.LANCZOS)
        bg.alpha_composite(t, ((SW - t.width) // 2, int(SH * 0.22)))
        tiles.append(label(bg.convert("RGB"), cap))
    def one(st, col, text, cap, scene=False):
        n = len(text)
        tiles.append(label(frame(jar, font, lang, st, [(st, col, text, 0, out_at(n))], typed_at(n) + 20, scene=scene), cap))
    one("cult_leader", 0xFFB040, lang["ui.pohsmp_core.cult_leader.replica_taunt"], "speech (as before): the name is now Russian")
    one("irina", None, lang["ui.pohsmp_core.irina.mark"].replace("%s", "Steve"), "system line: irina.mark (was the chat)")
    one("ereb", None, lang["ui.pohsmp_core.ereb.vanish"], "system line: ereb.vanish, in the finale scene", scene=True)
    one("irina", None, lang["ui.pohsmp_core.irina.bond"].replace("%s", "Alex"), "system line: irina.bond (long, wrapped)")
    cols, pad = 2, 8
    rows = (len(tiles) + 1) // 2
    sheet = Image.new("RGB", (cols * SW + (cols + 1) * pad, rows * SH + (rows + 1) * pad), (12, 12, 14))
    for i, t in enumerate(tiles):
        sheet.paste(t, (pad + (i % cols) * (SW + pad), pad + (i // cols) * (SH + pad)))
    out = os.path.join(ROOT, "docs/media/t26_name_ru_and_sysline.png")
    sheet.save(out, optimize=True)
    print("written", out, sheet.size)


def main():
    jar = Jar(os.environ.get("MC_CLIENT_JAR", JAR))
    font, lang = Font(jar), load_names()
    if sys.argv[1] == "mockups": mockups(jar, font, lang)
    elif sys.argv[1] == "video": video(jar, font, lang)
    elif sys.argv[1] == "sysline": sysline(jar, font, lang, sys.argv[2])
    elif sys.argv[1] == "one":
        st, col, key = BOSSES[int(sys.argv[3]) if len(sys.argv) > 3 else 0]
        text = lang[key]
        frame(jar, font, lang, st, [(st, col, text, 0, out_at(len(text)))], typed_at(len(text)) + 20).save(sys.argv[4] if len(sys.argv) > 4 else "one.png")


if __name__ == "__main__":
    main()
