#!/usr/bin/env python3
"""
Свитки Запретной школы (ступень «Мироздание», владелец 19.11). Рамка «Мироздание»: тёмное золото и чёрный, бумага пепельно-серая.
erased_name — «Стёртое имя»: вычеркнутая строка-имя, буквы рассыпаются. Каркас — tools/gen_tier_scrolls.py.
Запуск: python3 tools/gen_forbidden_scrolls.py
"""
import importlib.util, os

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('gts', os.path.join(HERE, 'gen_tier_scrolls.py'))
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

g.TIERS['creation'] = dict(
    rod={'A': '#0A0806', 'B': '#FFE9A8', 'C': '#3A3020', 'D': '#1A1610', 'E': '#D4A017', 'F': '#2A2418', 'G': '#D4A017',
         'H': '#120E0A', 'I': '#6A4A08'},
    edge='#0A0806', sh1='#7A7468', sh2='#A8A298', base='#CFCAC0', light='#E4E0D8',
    ink={'1': '#0A0806', '2': '#8A6A10', '3': '#FFFFFF'})

E = {
    'erased_name': ('creation', ('#2A2420', '#D4A017'), [
        "................", ".444.4.4.444.44.", ".4...44..4.4.4..", ".44..4.4.44..44.", "5555555555555555",
        ".4...4.4.4.4.4..", ".444.4.4.4.4.44.", "............4..4", "..........4...4.", "............4..."]),
}

if __name__ == '__main__':
    for sid, (tier, acc, em) in E.items():
        assert len(em) == 10 and all(len(r) == 16 for r in em), sid
        g.make(sid, tier, acc, em)
        print('wrote scroll_%s' % sid)
