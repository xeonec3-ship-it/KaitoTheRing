#!/usr/bin/env python3
"""
Свитки четырёх Мифических T23 (владелец 19.11): «Древо мира», «Око бездны», «Чёрное солнце», «Последний рассвет».
Рамка мифической ступени (как у «Сна бабочки»), эмблема 16×10 — см. tools/gen_tier_scrolls.py.
Запуск: python3 tools/gen_mythic_t23_scrolls.py
"""
import importlib.util, os

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('gis', os.path.join(HERE, 'gen_illusion_scrolls.py'))
gi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gi)
g = gi.g

E = {
    'world_tree': ('mythic', ('#2E7A2E', '#6A4220'), [
        "....44444444....", "..444444444444..", ".44444444444444.", "..4444455444444.", "....44.55.444...",
        ".......55.......", ".......55.......", "......5555......", "....55.55.55....", "...5..5..5..5..."]),
    'abyss_eye': ('mythic', ('#1A0A2A', '#C02A6A'), [
        "................", ".....444444.....", "...44......44...", ".44...5555...44.", "4....555555....4",
        "4....553355....4", ".44...5555...44.", "...44......44...", ".....444444.....", "................"]),
    'last_dawn': ('mythic', ('#E0A020', '#FFFFFF'), [
        "....4...4...4...", ".....4..4..4....", "..4...4.4.4...4.", "...4..44444..4..", "......45554.....",
        "....445555544...", "1111111111111111", "..1....1....1...", "................", "................"]),
}

if __name__ == '__main__':
    for sid, (tier, acc, em) in E.items():
        assert len(em) == 10 and all(len(r) == 16 for r in em), sid
        g.make(sid, tier, acc, em)
        print('wrote scroll_%s' % sid)
