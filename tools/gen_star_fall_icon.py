"""Spell icon for Star Fall (T05): 16x16, a star falling diagonally with a trail onto a glowing ground.
Writes src/main/resources/assets/pohsmp_core/textures/gui/spell_icons/star_fall.png. Needs Pillow."""
from pathlib import Path
from PIL import Image

OUT = Path(__file__).resolve().parent.parent / "src/main/resources/assets/pohsmp_core/textures/gui/spell_icons/star_fall.png"
im = Image.new("RGBA", (16, 16))
px = im.load()
for y in range(16):                                   # night sky, lighter towards the bottom
    for x in range(16):
        px[x, y] = (30 + y * 3, 6 + y, 14 + y, 255)
for x, y in [(2, 2), (6, 1), (12, 4), (3, 7), (14, 9)]:
    px[x, y] = (220, 150, 160, 255)
for x in range(16):                                   # glowing crater line at the bottom
    d = abs(x - 6) / 8
    px[x, 15] = (int(255 - 120 * d), int(60 - 40 * d), int(70 - 40 * d), 255)
    if d < 0.5:
        px[x, 14] = (200, 40, 55, 255)
for i in range(9):                                    # trail from the top right to the head
    x, y = 14 - i, 1 + i
    k = i / 8
    px[x, y] = (int(150 + 105 * k), int(20 + 80 * k), int(40 + 70 * k), 255)
    if i > 3:
        px[x + 1, y] = (110 + 15 * i, 10 + 6 * i, 30 + 6 * i, 255)
hx, hy = 6, 10                                        # the head
for dx, dy in [(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)]:
    px[hx + dx, hy + dy] = (255, 255, 255, 255)
for dx, dy in [(1, 1), (-1, 1), (1, -1), (-1, -1)]:
    px[hx + dx, hy + dy] = (255, 140, 150, 255)
im.save(OUT)
print(OUT)
