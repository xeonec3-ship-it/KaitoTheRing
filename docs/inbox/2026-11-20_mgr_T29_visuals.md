# T29 «Мартин, Последний Полководец» — визуал готов (помощник по визуалу → управляющему; для чата Кодинга)

Ветка `claude/cnpc-chats-repo-0hcody`. Java не трогал, чужие файлы (T27/T28) не трогал.

**Генератор:** `tools/gen_martin.py` (модель, меч, щит, анимации, 3D-предмет меча). Он вызывает:
- `gen_martin_extra.py` — солдаты, знамя, конница;
- `gen_martin_fx.py` — fx, полоса, титры, иконки, lang, звуки, кадры;
- превью — `martin_render.py` + `martin_preview.template.html`.

Перед запуском нужен jar Iron's: `python3 tools/fetch_libs.py`.
- Запуск: `python3 tools/gen_martin.py [--shots] [--html]`. Для `--shots` нужна переменная `MARTIN_THREE=<путь к three.min.js r128>` (`npm i three@0.128.0`).
- Интерактивное превью — `tools/martin_preview.html`: модели, все анимации, свечение.

Планы роликов по секундам дописаны в ТЗ: `docs/specs/tasks/T29_martin_boss.md`, раздел «Визуал и ролики».

## Стандарт качества (эталон — Глава Культа)
- **Плотность текстуры.** Модель Мартина строится на каркасе мага Iron's в его масштабе. Текстура ×4, как у эталона: UV-атлас 128 ед. → `martin.png` 512×512, 4 пикселя на единицу.
- **Фактура.** Ручная светотень:
  - светлая кромка сверху, тёмная снизу;
  - пятна-мазки в 2–3 тона;
  - гравировка, золотая кайма, заклёпки, складки ткани и плаща;
  - узоры и гербы — крупным пикселем.
- **Объёмные детали брусками:** ламы наплечников и шипы, наколенники, сабатоны, нащёчники, корона и рога, пряжка, полы табарда, подбой плаща.
- **Кадры для сравнения:**
  - `docs/media/t29_vs_cult_leader.jpg` — рядом с Главой Культа в одном масштабе мира и свете;
  - `docs/media/t29_vs_reference.jpg` — сверка с референсом.

## 1. Мартин (GeckoLib)
**Файлы:**
- `geo/entity/martin.geo.json` (identifier `geometry.martin`);
- `textures/entity/martin/martin.png` (512×512) и `martin_glowmask.png` (только холодный блик в щели забрала);
- `animations/entity/martin.animation.json`.

**Масштаб.** Модель — в единицах мага Iron's (голова до +33 ед., рога до +39). **Код рисует ×2:** `withScale(2)` / `poseStack.scale(2, 2, 2)`.
- Рост в мире: шлем ≈ 4.1 бл., рога ≈ 4.9 бл.
- Хитбокс предлагаю **1.4 × 4.0**, глаза на 3.5.
- Анимации Iron's играют без правок: кости и шарниры те же. Позиции в анимациях Iron's тоже в единицах модели, поэтому масштаб ×2 их не ломает.

**Кости** (имена Iron's + свои):

| кость | родитель | что |
|---|---|---|
| `body` | — | корень (шарнир y 12) |
| `torso` | body | кираса, золотой ворот, пояс, фалды |
| `tabard_front`, `tabard_back` | torso | полы табарда: красные с золотой каймой, по центру серебряная пластина; сзади — герб |
| `cape` → `cape_low` | torso | чёрно-белый плащ до земли (две кости для взмаха); анимации их качают |
| `head` | body | шлем-корона, рога, золотое забрало |
| `right_arm` → `right_forearm` → `bipedHandRight` → `rightItem` | body | рука; предплечье — своя кость для хвата двуручником. Анимации Iron's его не трогают, рука остаётся прямой |
| `left_arm` → `left_forearm` → `bipedHandLeft` → `leftItem` | body | то же |
| `right_leg`, `left_leg` | body | латные ноги |
| `sword` | right_forearm | **двуручник — кость модели** (той же формы, что предмет), шарнир в хвате правой руки |
| `shield_back` | torso | башенный щит на спине |
| `shield_hand` | left_forearm | тот же щит в руке |
| `banner_held` | left_forearm | знамя в руке, только в `martin_banner_plant` до `plant` |

**Видимость.** Щит на спине и в руке, знамя в руке переключаются **ключами scale в самих анимациях** (0/1). Код ничего не прячет.
- Во все анимации Iron's в нашем файле добавлено `shield_hand` и `banner_held` = 0.
- **Меч держит кость `sword`, поэтому слой предметов не нужен.** Если в главной руке у сущности есть предмет, его рисовать не надо: иначе меч задвоится. Меч и щит игрокам не выдаются.

## 2. Анимации Мартина (`martin.animation.json`; плюс все анимации заклинаний Iron's под их именами)
События — ключи `timeline` (GeckoLib `CustomInstructionKeyframeEvent`); их можно заменить таймерами по таблице.

| имя | длина, с | цикл | события (с) | для чего |
|---|---|---|---|---|
| `martin_idle` | 3.0 | да | — | стойка: двуручник остриём на противника, тяжёлое дыхание |
| `martin_walk` | 1.6 | да | `step` 0.4, 1.2 | тяжёлый шаг, меч на плече (звук `martin.step`, по желанию лёгкая дрожь камеры рядом) |
| `martin_swing` | 1.6 | нет | `swing` 0.62, **`hit` 0.75** | горизонтальный размах справа налево (дуга ~4.6 бл. перед ним) |
| `martin_overhead` | 2.0 | нет | `swing` 0.82, **`hit` 0.95** | рубящий сверху, клинок в землю ≈ 4.5 бл. впереди → fx `martin_slam` |
| `martin_thrust` | 1.4 | нет | **`hit` 0.6** | выпад, корпус уходит на 6 ед. (×2 = 0.75 бл.) вперёд |
| `martin_shield_bash` | 1.5 | нет | `shield_draw` 0.12, `dash` 0.45, **`hit` 0.75** | рывок щитом; рывок сущности — код (0.45–0.75), fx `martin_dash` |
| `martin_command` | 2.2 | нет | `command` 0.85 | жест «в атаку!» (меч вперёд-вверх) → fx `martin_command`, баф солдатам |
| `martin_banner_plant` | 2.4 | нет | `raise` 0.7, **`plant` 1.3** | вонзает знамя; на `plant` — сущность знамени ~3 бл. слева-спереди |
| `martin_cavalry` | 3.4 | нет | `call` 1.0, `charge` 2.0 | особое «Атака конницы» |
| `martin_hold_the_line` | 2.5 | держит | `shield_draw` 0.15, **`wall` 1.1** | особое «Приказ стоять насмерть»: щит в землю перед собой, меч над щитом |
| `martin_hold_loop` | 2.0 | да | — | стойка за щитом, 10 с действия |
| `martin_hold_end` | 0.8 | нет | — | выход из стойки |
| `martin_phase2` | 3.0 | нет | `plant` 0.6, `roar` 1.4 | переход 66% (меч в землю, рёв) |
| `martin_phase3` | 3.2 | нет | `kneel` 0.8, `spin` 1.4, `roar` 2.0 | переход 33%: присед, рывок с мечом, оборот, меч над головой |
| `martin_spawn` | 6.5 | нет | `look` 1.0, `rise` 2.6, `pull` 4.0, `salute` 5.0 | ролик появления: на колене, руки на воткнутом мече → встаёт → выдёргивает меч → салют → стойка |
| `martin_block_yield` | 3.2 | держит | **`block` 0.2**, `lower` 1.2, `speak` 2.4 | блок-сдача: щит вверх, принимает удар, отдача, опускает меч остриём к земле |
| `martin_to_npc` | 1.2 | держит | — | из позы сдачи в позу NPC |
| `martin_npc_idle` | 4.0 | да | — | **мирный NPC:** меч воткнут остриём в землю перед ним, обе руки на рукояти, дышит, плащ колышется |

Для фазы 3 подходят и анимации Iron's: `overhead_two_handed_swing`, `dead_king_double_swing`, `simple_sword_downstrike`.
В них меч остаётся в правой руке (левая рука не на рукояти).

## 3. Призрачные солдаты (GeckoLib)
**Файлы:**
- `geo/entity/martin_soldier.geo.json`;
- `textures/entity/martin/martin_soldier.png` + `_glowmask` (свечение: золотая кайма, глаза);
- `animations/entity/martin_soldier.animation.json`.

**Модель.** Обычный рост (×1), кости Iron's (+ `right_forearm`/`left_forearm`, `tabard_front`, `cape`, `sword`, `shield`).
- Щит всегда на левом предплечье, меч — кость.
- **Призрачность — код:** `RenderType.entityTranslucent` и альфа вершин ≈ 0.65 (`getRenderColor`) плюс `AutoGlowingGeoLayer`.
- Хитбокс 0.7 × 2.0.

**Анимации:**
- `martin_soldier_idle` (2.4, цикл);
- `martin_soldier_walk` (1.0, цикл);
- `martin_soldier_attack` (1.0, `hit` 0.45) — укол из-за щита;
- `martin_soldier_brace` (1.6, цикл) — «Строй»: плечом в щит, держит удар;
- `martin_soldier_spawn` (1.2, держит) — поднимается из земли, ставить сущность на землю сразу;
- `martin_soldier_vanish` (0.8, держит, `gone` 0.8) — рассеивается, после `gone` убрать.

## 4. Знамя (GeckoLib — сущность с хитбоксом, его можно срубить)
**Файлы:**
- `geo/entity/martin_banner.geo.json`;
- `textures/entity/martin/martin_banner.png` (полотнище с вырезом «ласточкин хвост» по альфе — cutout);
- `animations/entity/martin_banner.animation.json`.

**Размеры:** древко 3.5 бл. + навершие-корона, полотнище 0.9 × 1.9 бл. Хитбокс 0.6 × 3.9.

**Кости:** `root`, `pole_low` (низ 0–1.25 бл.), `pole_top` (шарнир на 1.25 бл. — место сруба), `cloth_1..3` (полотнище цепочкой, для волны).

**Анимации:**
- `martin_banner_idle` (2.0, цикл) — волна;
- `martin_banner_plant` (1.2, `impact` 0) — дрожь древка, полотнище взлетает;
- `martin_banner_hit` (0.4) — на каждый удар;
- `martin_banner_cut` (1.6, держит; `snap` 0, `fall` 1.0) — верх ломается и падает; сущность убрать через 2 с.

Мэш `fx/meshes/martin_banner*` не делал: знамя — сущность, у неё нужны хитбокс и анимация сруба.

## 5. Эффекты (`fx/*.json`, стили `fx/styles/martin.json` — золото/серебро, `martin_ghost.json` — призрачная бирюза)
Длительности в тиках. caster/target — как в ctx.

| fx | длит. | где | заметки для кода |
|---|---|---|---|
| `martin_intro` | 130 | caster = Мартин (на колене), yaw — взгляд | ролик появления, синхронно с `martin_spawn`; за спиной встают 2 ряда призрачных солдат (мэш `martin_soldier_ghost`); титр на 108, полоса на 130 |
| `martin_formation` | −1 | caster = Мартин, follow | фаза 1 «Строй» до `Fx.stop`: герб r4.2 под ним, искры |
| `martin_soldier_spawn` | 30 | caster = точка | **сущность — на 4 тике**, затем анимация `martin_soldier_spawn` |
| `martin_soldier_aura` | −1 | caster = солдат, follow | туман у ног |
| `martin_soldier_vanish` | 20 | caster = солдат | вместе с `martin_soldier_vanish` |
| `martin_formation_block` | 8 | caster = точка удара на щите | удар по Мартину ослаблен строем |
| `martin_command` | 30 | caster = Мартин | на событии `command` |
| `martin_banner_plant` | 40 | caster = основание знамени | на `plant`; затем `martin_banner_aura` |
| `martin_banner_aura` | −1 | caster = знамя, follow | кольцо r8: солдаты внутри сильнее; на них `martin_banner_buff` (−1, follow) |
| `martin_banner_hit` / `martin_banner_cut` | 6 / 40 | caster = точка / основание | при срубе — `Fx.stop` ауры и всех бафов |
| `martin_cavalry_cast` | 68 | caster = Мартин | особое: свет на меч; на `call` (20 тик) запустить полосы |
| **`martin_cavalry_lane`** | 72 | **caster = начало полосы на земле (край арены), yaw = направление** | **0–40 — предупреждение** (полоса 40×3 бл. с шевронами, мэш `martin_lane_warn`); **40–62 — три всадника** (мэш `martin_cavalry_rider`) пролетают полосу. **Урон:** всадник k (k = 0,1,2; старт 40 + 2k) в тике t стоит в z = −4 − 3.2k + 52·(t − 40 − 2k)/28 бл. от начала по yaw; бьёт игрока, если \|x\| < 1.5 и \|z_игрока − z\| < 1.5. Полос 3–5, параллельно или веером |
| `martin_hold_the_line` | 200 | caster = Мартин, follow | особое, с `wall`: щит-барьер дугой 120° r2.4 (мэш `martin_shield_wall`), 10 с; удары спереди → `martin_hold_deflect` (10) в точке удара |
| `martin_hold_soldier` | 200 | caster = солдат, follow | малый барьер (scale 0.5) |
| `martin_slam` | 30 | caster = точка удара ≈ 4.5 бл. впереди | `hit` в `martin_overhead` |
| `martin_swing_trail` | 10 | caster = Мартин | на `swing` (размах/выпад) |
| `martin_dash` | 16 | caster = Мартин, follow | рывок щитом |
| `martin_phase2` / `martin_phase3` | 60 / 64 | caster = Мартин | переходы; в фазе 3 с `roar` — `martin_fury` (−1, follow) |
| **`martin_block`** | 24 | caster = Мартин, yaw — к ударившему | **блок-сдача** на `block` (0.2 с): лязг, сноп искр от щита, звон-волна, засветка 0.12 |
| `martin_yield` | 80 | caster = Мартин | с `lower`: войско и знамя гаснут, мягкий свет |

**Мэши** (`fx/meshes/`):
- `martin_cavalry_rider` — конь в летящем галопе + всадник с копьём и флажком, полупрозрачные бруски, едет по +z;
- `martin_soldier_ghost` — солдат для ролика, собран из модели солдата;
- `martin_lane_warn` — quad полосы;
- `martin_shield_wall` — 6 quad дуги.

**Рисунки** (`textures/sigil/`): `martin_emblem` (герб: корона над мечом, 12 щитов строя), `martin_banner_ring`, `martin_barrier`, `martin_lane`.

**Новых параметров отрисовщика нет.** Используются уже описанные в `docs/fx.md`: `mesh.move.keys`, `quad`, `wave.reverse`.
Без `wave.reverse` волна в `martin_phase3` и `martin_banner_cut` просто расходится наружу — терпимо.

## 6. Полоса здоровья по фазам (`textures/gui/sprites/boss_bars/`, 192 шириной, формат tyros: строки 0–17 — пустая, 18–35 — полная)
- `martin_bossbar.png` — фаза 1, **серебро** («Строй»): стальная рамка, серебряная заливка, корона в центре, «гарды» на концах, голубые камни;
- `martin_bossbar_p2.png` — фаза 2, **красный** («Знамя»): кровавая рамка, заливка с тёмными насечками, золотые камни;
- `martin_bossbar_p3.png` — фаза 3, **золото** («Последний полководец»): золотая рамка, золотая заливка с бликами, красные камни;
- `martin_bossbar_flash.png` (192×18) — белый силуэт для вспышки смены фазы.

Рисовать как у T26: `BossbarSprite(pohsmp_core:boss_bars/martin_bossbar[_p2|_p3], 192, 18, 3, -1)`, ширина полной половины `3 + progress·186`.
Смена фазы: 6 тиков поверх `_flash`, альфа 1 → 0. **При сдаче полоса исчезает** (на `block`).

Подпись под полосой — `ui.pohsmp_core.martin.epithet` («Глава 4 Ячейки Культа»), как у T26.

## 7. Титры, иконки, lang, звуки
**Титры** (`textures/gui/title/`, 1024×192; показ: вход 0.5 с, уход 0.75 с):
- `martin_{ru,en}` — две строки:
  - ru: «Мартин, Последний Полководец» / «Глава 4 Ячейки Культа»;
  - en: «Martin, the Last Warlord» / «Head of the Cult's Fourth Cell»;
- `martin_cavalry_{ru,en}` — «Атака конницы» / «Cavalry Charge»;
- `martin_hold_{ru,en}` — «Приказ стоять насмерть» / «Hold the Line to the Death».

**Иконки статусов** (`textures/gui/martin/`, 18×18) — рисовать у полосы, пока статус активен:
- `status_formation` — строй;
- `status_banner` — знамя стоит;
- `status_hold` — стоять насмерть;
- `status_cavalry` — конница;
- `status_last_warlord` — фаза 3.

Подписи — `ui.pohsmp_core.martin.status.*`.

**lang** (ru/en):
- `entity.pohsmp_core.martin`, `martin_soldier`, `martin_banner`;
- `ui.pohsmp_core.martin.*`:
  - `title`, `epithet`, `subtitle`;
  - `formation`, `formation_block`, `command`;
  - `phase2`, `banner_cut`, `phase3`;
  - `cavalry`, `cavalry_warn`;
  - `hold` (с `%s` секунд), `hold_blocked`, `hold_end`;
  - **`yield`** = «Хорошо, вы доказали свою силу...Я помогу Эребу, если эта ваша просьба» (en: «Very well, you have proven your strength... I will help Erebus, if that is your request») — в чат r48 и субтитром на `speak`;
  - `status.*`;
- `subtitles.pohsmp_core.martin.*`, `subtitles.pohsmp_core.music.martin`.

**Звуки** (`sounds.json`, файлы не копировал — ванилла и Iron's с другим pitch):
- `martin.spawn`, `step`, `swing`, `slam`, `bash`;
- **`martin.block`** — лязг: наковальня + щит;
- `martin.command`, `horn` (рог рейда), `gallop`;
- `martin.banner_plant`, `banner_cut`, `hold`;
- `martin.soldier`, `soldier_vanish`, `phase`;
- **`music.martin`** — заглушка (тема Мёртвого Короля Iron's) до трека владельца `pohsmp_core:music/martin`.

## 8. Меч и щит как предметы
- `models/item/martin_sword.json` + `textures/item/martin_sword_3d.png` — **3D-двуручник из брусков** по референсу:
  - клинок: золото, тёмный дол, светлые кромки, ступенчатое острие;
  - большая узорная гарда-корзина из завитков;
  - чёрная рукоять с золотыми кольцами;
  - узорное навершие.

  Код может зарегистрировать `pohsmp_core:martin_sword` без рецепта (игрокам не выдаётся) — например, для админской выдачи или витрины.
  На боссе меч — кость `sword` той же формы, так что предмет ему не нужен.
- **Башенный щит — часть модели** (`shield_back`/`shield_hand`), в цветах лат: сталь, золотая кайма, красное поле, герб, заклёпки. Отдельной модели предмета нет.

## Что не проверено
В игре не смотрел. Проверить в первую очередь:
- масштаб ×2 и хитбокс;
- что меч не задваивается слоем предметов Iron's;
- полупрозрачность солдат;
- мэш конницы и барьера в `/pohsmp fx play martin_cavalry_lane`;
- поза NPC: остриё меча должно касаться земли. Если на неровной земле уходит в блок — это ок.

## Кадры (`docs/media/`)
- `t29_vs_reference.jpg` — сверка с референсом;
- `t29_vs_cult_leader.jpg` — рядом с эталоном;
- `t29_model.jpg` — спереди, 3/4, сзади, сбоку;
- `t29_poses.jpg` — 20 поз из анимаций;
- `t29_army.jpg` — солдаты и знамя;
- `t29_fx.jpg` — строй, знамя, конница по полосам, барьер;
- `t29_ui.jpg` — полосы по фазам, вспышка, титры, иконки;
- `t29_textures.jpg` — атласы и рисунки.
