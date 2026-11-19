# T22 «Иллюзии» — визуальная часть готова (помощник по визуалу → управляющему; для чата Кодинга)

Ветка `claude/cnpc-chats-repo-0hcody`. Java не трогал. Свитки (`gen_illusion_scrolls.py`) не трогал.
Генераторы: **`tools/gen_illusion_fx.py`** (текстуры, печати, fx, модели, иконки; `--sheet <png>` — лист текстур) и раздел T22 в
**`tools/gen_player_anims.py`** (анимации). Сцены «Иллюзии: …» добавлены в `tools/sigil_preview.html`, анимации — в `tools/anim_preview.html`.
Ролик «Сна бабочки» по секундам — в ТЗ: `docs/specs/tasks/T22_illusion_school.md`, раздел «Ролик».
Обзорные кадры: `docs/media/t22_illusion_fx.jpg`, `t22_illusion_textures.jpg`, `t22_illusion_icons.png`, `t22_butterfly_poses.jpg`.

Правило «никаких лучей к цели» соблюдено: ни одного `beam`/`trail`/`chains` от заклинателя к цели; связь с целью — печать над ней.
Правило 3 (копия не «разоблачается»): копии гаснут `fx/illusion_poof` — нейтральное серо-белое облачко без цвета школы и искр.

## 1. Школа, атрибуты, фокус, иконки
- Стиль `fx/styles/illusion.json`: primary `#C9A8FF`, secondary `#FFB8E6`, core `#FFFFFF`, shadow `#3A2A5A`; `@shards` = `mote_glass`
  (осколок зеркала), `@sigil` = `illusion_seal`, `@runes` = `school_illusion_band`.
- **Знак/печати школы как у T06** (имена по шаблону `SchoolSeals` / `PohSpell.onCast`):
  `fx/school_illusion` (обычный каст, знак `sigils/school_illusion`), `fx/school_illusion_cast` (Высшая), `_cast_crown` (Мифическая),
  `_cast_divine` (Божественная, с дугой 7 золотых кругов). Печати `sigils/illusion_seal` (2.4, собирается из 12 осколков, края двоятся
  розовой и голубой тенью) и `sigils/illusion_crown`. Для HFx/двойного контура T15 — `textures/fx/sigil_illusion.png`.
  **Коду:** добавить `"illusion"` в `PohSpell.SIGIL_SCHOOLS`, `SIGIL_ORDER` и цвет `0xC9A8FF` в `SIGIL_COLORS` — тогда всё подхватится само.
- Значок школы 16×16: `textures/gui/school/illusion.png` (зеркальное око в ромбе). У других школ значков/иконок атрибутов нет — если
  код или Iron's их не показывают, файл просто лежит про запас. Иконки атрибутов не делал (у других школ их нет).
- Фокус: `textures/item/illusion_prism.png` (16×16, осколок зеркала в серебряной оправе с камнями) + `models/item/illusion_prism.json`
  (`item/generated`). Тег `illusion_focus` и регистрация предмета — код.
- Иконки заклинаний 16×16 (`textures/gui/spell_icons/`): `mirror_images`, `false_step`, `veil`, `phantom_pain`, `borrowed_face` — рамка
  школы (лиловый квадрат); `mirror_labyrinth`, `waking_nightmare` — круглая красная рамка Высших; `butterfly_dream` — фиолетовый квадрат Мифических.
- Статусы 18×18 (`textures/mob_effect/`): `phantom_pain`, `waking_nightmare`, `butterfly_dream`, `borrowed_face`, `mirror_images`
  (последний — по желанию: «копии рядом» у заклинателя). `illusion_resist` не делал — это атрибут, не статус.

## 2. Эффекты (`fx/*.json`) — точки и параметры для кода
Все длительности — тики. `caster`/`target` — как в ctx; `point:<имя>` — `Fx.point(...)`.

| fx | длит. | кто/где | заметки |
|---|---|---|---|
| `illusion_poof` | 20 | caster = место копии | гибель копии («Отражения», «Ложный шаг»). Если рывок игрока рисуется ванильным POOF — гасить копии им же; главное одинаково |
| `illusion_mirror_images_cast` | 30 | caster | на 12 тике «воздух трескается»: сфера-рябь, осколки. Анимация `pohsmp_illusion_mirror_images_cast` |
| `illusion_mirror_image_spawn` | 12 | caster = фигура | играть **на каждой копии и на самом маге одинаково** (иначе мага видно) |
| `illusion_false_step` | 24 | caster (follow) | видят **только маг и союзники**; призрачный след, рябь на 8 тике в точке прибытия. Врагам — ничего (маг пропал) |
| `illusion_veil` | 200 | caster (без follow) | марево r6: печать `illusion_veil_ground`, стенка марева (curtain `illusion_haze`), tint у игроков внутри |
| `illusion_veil_flicker` | 8 | caster = фигура | едва заметная рябь, когда настоящая модель пропадает/фальшивый мигает (только враг в мареве) |
| `illusion_phantom_pain_cast` | 18 | caster | малое сердце у ладони (никакой линии к цели) |
| `illusion_phantom_pain_mark` | 120 | target | метка над головой (+2.35), розовая оболочка; гасить `Fx.stop`, если метка снята раньше |
| `illusion_phantom_pain_tick` | 8 | target | на каждый удар по меченой: розовая искра у груди |
| `illusion_return` | 24 | target | **возврат иллюзорного урона, 1 с** — перламутровые искры сходятся к груди, вспышка на 18 тике; общий для школы |
| `illusion_borrowed_face` | 20 | caster | на 8 тике рябь + око перед лицом — **в этот тик менять скин/ник**. Анимация `pohsmp_illusion_borrowed_face` (0.9 с) |
| `illusion_borrowed_face_end` | 12 | caster | облик спадает (атака/каст/30 с) |
| `illusion_labyrinth_cast` | 90 | caster | каст 4 с; на **76 тике** удар ладонями: вспышка, волна до r14. Затем зону держит `illusion_labyrinth` |
| `illusion_labyrinth_seal` | −1 | caster | печать-лабиринт под ногами на время каста — **играть, только если `SchoolSeals.shown(caster) == false`** (иначе две печати) |
| `illusion_labyrinth` | 400 | caster = центр | купол (mesh `illusion_dome`, scale 14), бледный лабиринт по земле, блики, tint r14 |
| `illusion_labyrinth_wall_hit` | 24 | point:`hit` (точка на стене), caster = жертва | осколки навстречу, трещина, лёгкая засветка; только жертве |
| `illusion_nightmare_cast` | 74 | caster + target | каст 3.5 с; печать пустых очей над целью (+2.6), тьма по цели; на **66 тике** печать вспыхивает |
| `illusion_nightmare_seal` | −1 | caster | тёмная печать под ногами (то же правило с `SchoolSeals.shown`) |
| `illusion_nightmare_mark` | 240 | target | цель в кошмаре 12 с (видят все рядом): тёмная дымка у головы, пустые «очи»-искры |
| `illusion_nightmare_monster` | 60 | caster | превью/запасной вариант чудовища (mesh) |
| `illusion_butterfly_cast` | 260 | caster, point:`touch` | каст 240 + хвост 20. `touch` — у ладони: ≈0.65 бл. вперёд от мага, высота 1.4 (касание на 86 тике). Шкала = ролик |
| `illusion_butterfly_world` | 500 | caster = **жертва** (follow) | мир-отражение 25 с — **только жертве**: бабочки, трещины «неба» над головой, лиловый tint |
| `illusion_butterfly_reveal` | 22 | caster = проявившийся | мерцающий контур 1 с (видят жертвы); в эти 20 тиков рисовать модель полупрозрачной |
| `illusion_butterfly_wake` | 50 | caster | пробуждение для всех в r48: вспышка, кольцо до r32, бабочки → осколки, «небо» трескается |
| `illusion_butterfly_wake_hit` | 22 | target = жертва | урон становится настоящим: осколки влетают в цель на 0–3 тиках, вспышка на 8 — **урон бить на 8 тике** |

**Звуки (предложение, ваниль):** каст обычных — `AMETHYST_BLOCK_CHIME` + тихий `ALLAY_AMBIENT_WITHOUT_ITEM` (шёпот); осколки/вход в стену —
`GLASS_BREAK` (pitch 1.4–1.8); трещина в «Сне бабочки» — `AMETHYST_CLUSTER_BREAK` (pitch 0.6); пробуждение — `GLASS_BREAK` + `AMETHYST_BLOCK_RESONATE`
громко; кошмар — `AMBIENT_CAVE` / `WARDEN_HEARTBEAT` тихо. Школе в `Reg` годится `AMETHYST_BLOCK_RESONATE`.

## 3. Материалы для клиентских иллюзий
- **Зеркальная стена «Лабиринта»:** `textures/fx/illusion_mirror_wall.png` (256×256 на 1 блок, **непрозрачная**, тайлится по обеим осям:
  серебро с мягкими перламутровыми разводами, тонкие тёмные трещинки) + `textures/fx/illusion_mirror_wall_cracks.png` (256, светящиеся трещины,
  класть аддитивно 2-м слоем на ~треть стен). Модуль-модель `fx/meshes/illusion_mirror_wall.json` (1×3×0.14 блока, плитки, кромка, трещинки) —
  если удобнее тайлить мешем. Отражения мага в стенах — код (рисовать фальшивого игрока за стеклом, зеркально).
- **Купол:** `fx/meshes/illusion_dome.json` — радиус 1 (scale 14), рёбра геодезической полусферы перламутром, есть блок `hit` (рябь от `Fx.hit`).
- **Безликое чудовище:** `fx/meshes/illusion_nightmare.json` — рост 1.95 (ноги y=0, лицом +z), сгорблено, руки до колен с когтями, гладкая голова
  без черт (бледная «маска»), лохмотья; размытый край — 2 раздутых полупрозрачных слоя. Рисовать вместо **каждого** существа у жертвы:
  scale = рост сущности / 1.95, yaw — как у сущности; покачивание/походку — код (например, лёгкий наклон вперёд-назад 2–3° с периодом шага).
  Тени, частицы урона, звуки шагов — у настоящих сущностей как есть.
- **Стеклянные бабочки:** спрайты `textures/sigil/mote_butterfly.png` (крылья раскрыты, симметрична по u=0.5 — можно делить пополам и махать
  половинками) и `mote_butterfly_side.png` (сложены — второй кадр); модель `fx/meshes/illusion_butterfly.json` (размах ≈1, scale 0.4–0.6).
- **Трещины мира:** `textures/fx/illusion_world_cracks.png` (1024, белое на прозрачном, центр — точка удара) — экранная накладка в ролике
  (6.5–10 с, сила 0→0.6) и рисунок «неба» в мире-отражении (печать `illusion_mirror_crack`).
- **Марево:** `textures/fx/illusion_haze.png` (256, тайлится) — дрожащий воздух «Пелены»; можно и для полупрозрачности фальшивых силуэтов.
- Переворот неба и мир-отражение — описано в ТЗ, раздел «Ролик» (крен 180° только в ролике 8–10 с, потом возврат; 25 с — tint и трещины).

## 4. Анимации игрока (`assets/irons_spellbooks/player_animation/`, `new AnimationHolder("<имя>", true)`)
| имя | длина | что |
|---|---|---|
| `pohsmp_illusion_mirror_images_cast` | 1.0 с | ладонь по «зеркалу» перед лицом, руки в стороны на 0.6 с |
| `pohsmp_illusion_false_step_cast` | 0.5 с | рывок: корпус вперёд, руки назад |
| `pohsmp_illusion_veil_cast` | 1.2 с | ладони скрещиваются и разводятся — «занавес» |
| `pohsmp_illusion_phantom_pain_cast` | 0.8 с | ладонь к цели, поворот кисти |
| `pohsmp_illusion_borrowed_face` | 0.9 с | **жест «Чужого лица»**: ладонь ото лба к подбородку, облик меняется на 0.4 с (8 тик) |
| `pohsmp_illusion_labyrinth_cast` / `_finish` | 4.0 с (hold) / 1.2 с | чертит квадрат, руки вверх, удар ладонями к земле на 3.75 с |
| `pohsmp_illusion_nightmare_cast` / `_finish` | 3.5 с (hold) / 1.0 с | ладонь на глаза, коготь к цели, рывок на 3.3 с |
| `pohsmp_illusion_butterfly_cast` / `_finish` | **12 с = 240 тиков** (hold) / 1.5 с | ладони лодочкой → бабочка улетает → касание зеркала 4.3 с → давит → руки вверх (переворот) → раскрыты |
| `pohsmp_illusion_butterfly_wake` | 0.8 с | хлопок на 5 тике — запускать за 5 тиков до `illusion_butterfly_wake` |

Короткие кончаются в стойке; Высшие и «Сон бабочки» замирают в последней позе (hold) — после каста играть `_finish`.
Проверка в превью (Playwright, все тики, руки против корпуса и головы): пересечений нет, кроме касаний на переходах ≤1.4 px за 1–8 тиков
(у принятой «Печати души» — 0.6 px), сквозь тело руки не проходят.

## 5. lang (ru/en, 56 ключей)
`school.pohsmp_core.illusion`; `attribute.pohsmp_core.illusion_spell_power` / `illusion_magic_resist`; `item.pohsmp_core.illusion_prism` (+`.desc`);
`death.attack.illusion_magic` (+`.item`, `.player`) — под тип урона `illusion_magic` (сам `damage_type` JSON — код, как у остальных школ);
`spell.pohsmp_core.<8 id>` + `.guide`; `effect.pohsmp_core.<phantom_pain|waking_nightmare|butterfly_dream|borrowed_face|mirror_images>` + `.description`;
`fx.pohsmp_core.butterfly_dream.title`; ui: `ui.pohsmp_core.illusion.{illusory,returned,no_target,resisted}`, `mirror_images.{copies,time}`,
`false_step.{dash,time}`, `veil.radius`, `phantom_pain.time`, `borrowed_face.{time,as,gone}`, `mirror_labyrinth.{zone,shards}`,
`waking_nightmare.time`, `butterfly_dream.{cast,zone,half,wake}` (формат `%s` как у соседей; нужное — берите, лишнее — удалим).

## Вопросы / что нужно
1. Нужен ли отдельный статус «Отражения» у заклинателя (иконка есть) — или копий хватает?
2. Печать над целью «Кошмара» видят все рядом (знак, что цель в кошмаре) — так задумано; если надо прятать от врагов цели — скажите.
