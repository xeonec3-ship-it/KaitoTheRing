#!/usr/bin/env python3
"""
Свитки школы «Кошмары» (T25, владелец 19.11): 2 Высших (алая рамка ступени) и 1 Мифическое (фиолетовая рамка).
Каркас — tools/gen_tier_scrolls.py, рамка mythic — tools/gen_illusion_scrolls.py. Запуск: python3 tools/gen_nightmare_scrolls.py
"""
import importlib.util, os

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('gis', os.path.join(HERE, 'gen_illusion_scrolls.py'))
gi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gi)
g = gi.g

E = {
    'house_that_isnt': ('higher', ('#0A0610', '#E8E0D8'), [
        "4444444444444444", "4..4..4..4..4..4", "4.44.44.44.44.44", "4..............4", "44.4444444444.44",
        "4..4.444444.4..4", "4..4.4.55.4.4..4", "4..4.4.55.4.4..4", "4..4.4....4.4..4", "4444444444444444"]),
    'endless_night': ('higher', ('#0A0610', '#7A1040'), [
        "......5555......", ".....555555.....", ".....55555......", "......555.......", "................",
        "4..4.....4...4..", "44.44...444.44.4", "4444444444444444", "4444444444444444", "................"]),
    'no_awakening': ('mythic', ('#0A0610', '#B01A4A'), [
        "....44444444....", "..444444444444..", ".444...44...444.", ".44.55.44.55.44.", ".444...44...444.",
        "..444444444444..", "...4.4.4.4.4.4..", "...4.4.4.4.4.4..", "....4...4...4...", "......4...4....."]),
}

if __name__ == '__main__':
    for sid, (tier, acc, em) in E.items():
        assert len(em) == 10 and all(len(r) == 16 for r in em), sid
        g.make(sid, tier, acc, em)
        print('wrote scroll_%s' % sid)
