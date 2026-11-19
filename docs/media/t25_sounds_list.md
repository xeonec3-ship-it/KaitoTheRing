# T25 «Кошмары» — звуки на согласование (демо `t25_sounds_demo.mp3`)

Все звуки подряд, перед каждым — 0.5 с тишины. Генератор — `tools/gen_nightmare_sounds.py`; файлы — `assets/pohsmp_core/sounds/nightmare/`. События `nightmare.*` в `sounds.json` **ждут согласования** — код их не подключает.

| № | время в демо | длина | событие (вариант) | что это | где звучит |
|---|---|---|---|---|---|
| 1 | 0:00.5 | 1.9 с | `nightmare.heartbeat` (1) | Сердцебиение: глухое, медленное, с инфранизким ударом | стадии Погружения, касты, сгущение мифического |
| 2 | 0:02.9 | 2.1 с | `nightmare.heartbeat` (2) | Сердцебиение: глухое, медленное, с инфранизким ударом | стадии Погружения, касты, сгущение мифического |
| 3 | 0:05.5 | 2.6 с | `nightmare.heartbeat` (3) | Сердцебиение: глухое, медленное, с инфранизким ударом | стадии Погружения, касты, сгущение мифического |
| 4 | 0:08.5 | 5.5 с | `nightmare.child_laugh` (1) | Далёкий детский смех: хихиканье выше тоном, глухо, с эхом и «наплывом» перед ним | Пустой ребёнок (idle/laugh), галлюцинации стадии 2+ |
| 5 | 0:14.5 | 5.5 с | `nightmare.child_laugh` (2) | Далёкий детский смех: хихиканье выше тоном, глухо, с эхом и «наплывом» перед ним | Пустой ребёнок (idle/laugh), галлюцинации стадии 2+ |
| 6 | 0:20.5 | 5.5 с | `nightmare.child_laugh` (3) | Далёкий детский смех: хихиканье выше тоном, глухо, с эхом и «наплывом» перед ним | Пустой ребёнок (idle/laugh), галлюцинации стадии 2+ |
| 7 | 0:26.5 | 4.5 с | `nightmare.whisper` (1) | Шёпот: бормотание на непонятном языке, слоем задом наперёд, в пустом зале | стадии 1–3 (вокруг жертвы), «Дом, которого нет» |
| 8 | 0:31.5 | 4.5 с | `nightmare.whisper` (2) | Шёпот: бормотание на непонятном языке, слоем задом наперёд, в пустом зале | стадии 1–3 (вокруг жертвы), «Дом, которого нет» |
| 9 | 0:36.5 | 3.9 с | `nightmare.whisper` (3) | Шёпот: бормотание на непонятном языке, слоем задом наперёд, в пустом зале | стадии 1–3 (вокруг жертвы), «Дом, которого нет» |
| 10 | 0:40.9 | 3.3 с | `nightmare.scrape` (1) | Скрежет: когти по камню, ниже на октаву, со скрипом старого дерева | стадии 2–3, Ползун рядом |
| 11 | 0:44.7 | 3.6 с | `nightmare.scrape` (2) | Скрежет: когти по камню, ниже на октаву, со скрипом старого дерева | стадии 2–3, Ползун рядом |
| 12 | 0:48.8 | 3.6 с | `nightmare.scrape` (3) | Скрежет: когти по камню, ниже на октаву, со скрипом старого дерева | стадии 2–3, Ползун рядом |
| 13 | 0:52.9 | 0.7 с | `nightmare.crawler_step` (1) | Ползун: быстрые влажные шаги с хрустом суставов | Ползун — ходьба по земле/стенам |
| 14 | 0:54.2 | 0.7 с | `nightmare.crawler_step` (2) | Ползун: быстрые влажные шаги с хрустом суставов | Ползун — ходьба по земле/стенам |
| 15 | 0:55.3 | 0.7 с | `nightmare.crawler_step` (3) | Ползун: быстрые влажные шаги с хрустом суставов | Ползун — ходьба по земле/стенам |
| 16 | 0:56.5 | 1.3 с | `nightmare.crawler_hiss` (1) | Ползун: щёлкающий хрип, голова раскрывается | Ползун — idle/attack/pounce |
| 17 | 0:58.3 | 1.6 с | `nightmare.crawler_hiss` (2) | Ползун: щёлкающий хрип, голова раскрывается | Ползун — idle/attack/pounce |
| 18 | 1:00.4 | 1.6 с | `nightmare.crawler_hiss` (3) | Ползун: щёлкающий хрип, голова раскрывается | Ползун — idle/attack/pounce |
| 19 | 1:02.5 | 5.0 с | `nightmare.maw_roar` (1) | Пасть: рёв — глубокий, с рыком и обратным «вдохом» перед ним, гул в груди | Пасть — roar |
| 20 | 1:08.0 | 5.0 с | `nightmare.maw_roar` (2) | Пасть: рёв — глубокий, с рыком и обратным «вдохом» перед ним, гул в груди | Пасть — roar |
| 21 | 1:13.5 | 5.0 с | `nightmare.maw_roar` (3) | Пасть: рёв — глубокий, с рыком и обратным «вдохом» перед ним, гул в груди | Пасть — roar |
| 22 | 1:19.0 | 1.6 с | `nightmare.maw_bite` (1) | Пасть: укус-таран — тяжёлый влажный удар челюстей | Пасть — attack |
| 23 | 1:21.1 | 1.2 с | `nightmare.maw_bite` (2) | Пасть: укус-таран — тяжёлый влажный удар челюстей | Пасть — attack |
| 24 | 1:22.8 | 1.4 с | `nightmare.maw_bite` (3) | Пасть: укус-таран — тяжёлый влажный удар челюстей | Пасть — attack |
| 25 | 1:24.7 | 4.5 с | `nightmare.weeper_cry` (1) | Плакальщица: тихий плач — всхлипывающий напев с прерывистым дыханием, эхо | Плакальщица — idle (плачет) |
| 26 | 1:29.7 | 4.3 с | `nightmare.weeper_cry` (2) | Плакальщица: тихий плач — всхлипывающий напев с прерывистым дыханием, эхо | Плакальщица — idle (плачет) |
| 27 | 1:34.5 | 4.8 с | `nightmare.weeper_cry` (3) | Плакальщица: тихий плач — всхлипывающий напев с прерывистым дыханием, эхо | Плакальщица — idle (плачет) |
| 28 | 1:39.8 | 5.0 с | `nightmare.weeper_wail` (1) | Плакальщица: вопль — высокий призрачный вой со стоном | Плакальщица — wail |
| 29 | 1:45.3 | 5.0 с | `nightmare.weeper_wail` (2) | Плакальщица: вопль — высокий призрачный вой со стоном | Плакальщица — wail |
| 30 | 1:50.8 | 5.0 с | `nightmare.weeper_wail` (3) | Плакальщица: вопль — высокий призрачный вой со стоном | Плакальщица — wail |
| 31 | 1:56.3 | 1.4 с | `nightmare.moths` (1) | Мотыльки: сухой шорох множества крыльев | Мотыльки-глаза — рой, атака |
| 32 | 1:58.2 | 1.5 с | `nightmare.moths` (2) | Мотыльки: сухой шорох множества крыльев | Мотыльки-глаза — рой, атака |
| 33 | 2:00.2 | 1.4 с | `nightmare.moths` (3) | Мотыльки: сухой шорох множества крыльев | Мотыльки-глаза — рой, атака |
| 34 | 2:02.1 | 2.0 с | `nightmare.hands_grab` (1) | Руки из земли: хватают — чавкающая грязь, шлепок | Руки из земли — grab |
| 35 | 2:04.6 | 1.5 с | `nightmare.hands_grab` (2) | Руки из земли: хватают — чавкающая грязь, шлепок | Руки из земли — grab |
| 36 | 2:06.5 | 1.0 с | `nightmare.hands_grab` (3) | Руки из земли: хватают — чавкающая грязь, шлепок | Руки из земли — grab |
| 37 | 2:08.0 | 2.1 с | `nightmare.ink_rise` (1) | Кошмар появляется: чернила вздуваются и булькают (всплеск задом наперёд) | любой кошмар — appear (nm_spawn) |
| 38 | 2:10.6 | 2.0 с | `nightmare.ink_rise` (2) | Кошмар появляется: чернила вздуваются и булькают (всплеск задом наперёд) | любой кошмар — appear (nm_spawn) |
| 39 | 2:13.1 | 2.1 с | `nightmare.ink_rise` (3) | Кошмар появляется: чернила вздуваются и булькают (всплеск задом наперёд) | любой кошмар — appear (nm_spawn) |
| 40 | 2:15.7 | 1.9 с | `nightmare.ink_fall` (1) | Кошмар исчезает: рассыпается чернилами — всплеск и бульканье | любой кошмар — vanish/смерть (nm_despawn) |
| 41 | 2:18.1 | 1.9 с | `nightmare.ink_fall` (2) | Кошмар исчезает: рассыпается чернилами — всплеск и бульканье | любой кошмар — vanish/смерть (nm_despawn) |
| 42 | 2:20.4 | 1.5 с | `nightmare.ink_fall` (3) | Кошмар исчезает: рассыпается чернилами — всплеск и бульканье | любой кошмар — vanish/смерть (nm_despawn) |
| 43 | 2:22.4 | 4.0 с | `nightmare.cast_house` (1) | «Дом, которого нет» (2.5 с): гул, шёпот, медленно скрипит дверь, на 2.3 с — глухой удар (цель провалилась) | каст «Дома, которого нет» |
| 44 | 2:26.9 | 4.0 с | `nightmare.cast_house` (2) | «Дом, которого нет» (2.5 с): гул, шёпот, медленно скрипит дверь, на 2.3 с — глухой удар (цель провалилась) | каст «Дома, которого нет» |
| 45 | 2:31.4 | 4.6 с | `nightmare.cast_night` (1) | «Ночь без рассвета» (3 с): нарастающий гул, низкий колокол восходящей луны, стон, на 2.8 с — удар «заката» | каст «Ночи без рассвета» |
| 46 | 2:36.5 | 4.6 с | `nightmare.cast_night` (2) | «Ночь без рассвета» (3 с): нарастающий гул, низкий колокол восходящей луны, стон, на 2.8 с — удар «заката» | каст «Ночи без рассвета» |
| 47 | 2:41.6 | 15.0 с | `nightmare.cast_no_awakening` (1) | «Пробуждение не наступит» (12 с, под ролик): сломанная колыбельная шкатулки (замедляется, фальшивит) → чернила булькают, шёпот → нарастающий гул и вой → 9 с удар сердца → тишина, 11 с сердце тише → 11.8 с рёв-вспышка | каст мифического — ролик (stream) |
| 48 | 2:57.1 | 4.4 с | `nightmare.thicken` (1) | Сгущение: мир глохнет, два удара сердца, хор шёпота | мифическое — каждую минуту (nightmare_no_awakening_thicken) |
| 49 | 3:02.0 | 4.4 с | `nightmare.thicken` (2) | Сгущение: мир глохнет, два удара сердца, хор шёпота | мифическое — каждую минуту (nightmare_no_awakening_thicken) |

## Источники (все CC0, opengameart.org) — обработаны: высота, скорость, реверс, эхо, реверберация, фильтры, слои

- `heartbeat_slow_0.wav` — bart, https://opengameart.org/content/heartbeat-sounds
- `heartbeat.mp3_.flac` — qubodup, https://opengameart.org/content/heartbeat-single-sound
- `group_giggling.ogg` — Nocturnal_Vanguard (AuraVoice), https://opengameart.org/content/group-giggling
- `ghostbreath.flac` — qubodup, https://opengameart.org/content/ghost-breath
- `Creepychanting.zip` — OwlishMedia, https://opengameart.org/content/creepy-incoherent-chanting
- `ghostly_humming.ogg` — Nocturnal_Vanguard (AuraVoice), https://opengameart.org/content/ghostly-humming
- `monster_roar.wav` — trazzz123, https://opengameart.org/content/cc0-deep-monster-roar
- `monster_-_starninjas.zip` — StarNinjas, https://opengameart.org/content/16-monster-growls
- `independent_nu_ljudbank-wet_squish_slurp_impacts.7z` — qubodup / Independent.nu, https://opengameart.org/content/8-wet-squish-slurp-impacts
- `25-CC0-mud-sfx.zip` — rubberduck, https://opengameart.org/content/25-cc0-mud-sfx
- `water-splash-slime-sfx.zip` — rubberduck, https://opengameart.org/content/40-cc0-water-splash-slime-sfx
- `wings_flap_large.zip` — AntumDeluge, https://opengameart.org/content/large-wings-flap
- `scrapes.zip` — AntumDeluge, https://opengameart.org/content/scrapes
- `tree_creak.flac` — AntumDeluge, https://opengameart.org/content/tree-creaking
- `qubodup-GhostMoans.zip` — qubodup, https://opengameart.org/content/ghost-monster-voice-moaning-growling
- `independent_nu_ljudbank-atmosphere_moody.7z` — qubodup / Independent.nu, https://opengameart.org/content/4-atmospheric-ghostly-loops
- `scaryhighpitchedghost.wav` — Fupi, https://opengameart.org/content/scary-high-pitched-ghost
- `80-CC0-creature-SFX_0.zip` — rubberduck, https://opengameart.org/content/80-cc0-creature-sfx

Музыкальная шкатулка (колыбельная, «колокол» луны) и инфранизкие удары — синтез.
