# T25 «Кошмары» — визуальная часть готова (помощник по визуалу → управляющему; для чата Кодинга)

Ветка `claude/cnpc-chats-repo-0hcody`. Java не трогал. Свитки (`gen_nightmare_scrolls.py`) не трогал.
Генераторы: **`tools/gen_nightmare_fx.py`** (печати, fx, текстуры мира-кошмара, коридор, луна, иконки, lang; `--sheet` — лист текстур,
`--no-beasts` — без бестиария), **`tools/gen_nightmare_bestiary.py`** (бестиарий; каркас моделей — `tools/nightmare_geo.py`) и раздел T25 в
**`tools/gen_player_anims.py`** (анимации заклинателя). Превью бестиария: `tools/nightmare_bestiary_preview.html` (собирает
`tools/render_bestiary.py --html`; выбор кошмара и анимации, вращение мышью). Анимации каста — в `tools/anim_preview.html`.
Ролик мифического по секундам и мир-кошмар стадии 3 — дописаны в ТЗ: `docs/specs/tasks/T25_nightmare_school.md` (два раздела в конце).
Обзорные кадры: `docs/media/t25_bestiary.jpg` (лист бестиария), `t25_corridor.jpg` («Дом, которого нет»), `t25_nightmare_textures.jpg`,
`t25_nightmare_icons.png`, `t25_nightmare_poses.jpg`.

Правило «никаких лучей к цели» соблюдено: ни одного `beam`/`trail`/`chains` от заклинателя к цели; связь с целью — печать-коридор над её головой
(«Дом»), луна над зоной («Ночь»), волны по земле (мифическое).

## 1. Школа, фокус, иконки
- Стиль `fx/styles/nightmare.json`: primary `#E0285A` (багрово-алый свет печатей), secondary `#7A1040`, core `#E8E0D8`, shadow `#0A0610`;
  `@shards` = `mote_ink` (капля), `@sigil` = `nightmare_seal`, `@runes` = `school_nightmare_band`. Тени/чернила у элементов — тёмным цветом + `blend: translucent`.
- **Знак/печати школы как у T06/T22** (имена по шаблону `SchoolSeals` / `PohSpell.onCast`): `fx/school_nightmare` (обычный каст, знак
  `sigils/school_nightmare`), `fx/school_nightmare_cast` (Высшая), `_cast_crown` (Мифическая), `_cast_divine` (Божественная, дуга из 7 золотых кругов).
  Печати `sigils/nightmare_seal` (2.4: капли стекают с обода внутрь, венок открытых и плачущих глаз, сломанные гребёнки шкатулки, ноты с
  переломленными штилями, кольцо зубов; ядро — око над месяцем-колыбелью) и `sigils/nightmare_crown`.
  **Коду:** добавить `"nightmare"` в `PohSpell.SIGIL_SCHOOLS`, `SIGIL_ORDER` и цвет `0xE0285A` в `SIGIL_COLORS`.
- Значок школы 16×16: `textures/gui/school/nightmare.png` (око над месяцем-колыбелью в тёмном ромбе).
- Фокус: `textures/item/broken_lullaby.png` (треснувшая музыкальная шкатулка: крышка приоткрыта, латунная гребёнка, ключ, чернила из трещины,
  сломанная нота) + `models/item/broken_lullaby.json` (`item/generated`). Тег фокуса и регистрация — код.
- Иконки заклинаний 16×16 (`textures/gui/spell_icons/`): `house_that_isnt`, `endless_night` — круглая красная рамка Высших; `no_awakening` — фиолетовый квадрат Мифических.
- Статусы 18×18 (`textures/mob_effect/`): **стадии Погружения** `immersion_1` (тень-рука), `immersion_2` (глаз из тьмы), `immersion_3` (глаз плачет
  чернилами) — если Погружение один эффект с уровнем, показывайте иконку по стадии (или берите `immersion_3` как общую); плюс `endless_night`,
  `no_awakening`, `house_that_isnt`.

## 2. Эффекты (`fx/*.json`) — точки и параметры
Все длительности — тики. `caster`/`target` — как в ctx; «жертва» = эффект шлётся **только ей** (её клиент), если не сказано иное.

| fx | длит. | кто/где | заметки |
|---|---|---|---|
| `nightmare_stage1` / `2` / `3` | −1 | жертва (caster = она), follow | фон стадии: тени-руки на земле шевелятся (декали `nightmare_shadow_reach`), tint, хлопья; 2 — глаза в темноте, чернила из земли; 3 — tint r48 багрово-чёрный, чернильная морось, кольцо рук `nightmare_hands_ground`. Включать нужную, прошлую — `Fx.stop` |
| `nightmare_stage_up` / `_down` | 24 / 30 | жертва | переход стадии глубже (тьма схлопывается, удар сердца на 6 тике) / спад |
| `nightmare_silhouette_0..2` | 8 | жертва; caster = точка на земле | мелькающий силуэт (высокий / ребёнок / сгорбленный). Ставить в 8–16 бл. под углом 50–80° от взгляда, 2–6 раз в минуту на стадии 1+ |
| `nightmare_mark` | −1 | над жертвой; слать заклинателю и союзникам | око-метка «под кошмаром» (жертве не слать) |
| `nightmare_house_seal` | −1 | caster | печать-коридор под ногами — **только если `SchoolSeals.shown(caster) == false`** |
| `nightmare_house_cast` | 56 | caster + target | каст **2.5 с (50 тиков)**: печать-коридор над целью (+2.6), чернила смыкаются у её ног; **на 46 тике цель «проваливается»** (включайте ей коридор). Анимация `pohsmp_nightmare_house_cast` |
| `nightmare_house_enter` | 30 | жертва | мир тонет в черноте за 10 тиков; **на 20 тике** показывать модули коридора |
| `nightmare_house_corridor` | 1200 | жертва, follow | атмосфера коридора на 1 мин (пыль, туман у пола, капли); гасить при выходе |
| `nightmare_house_shadow` | 40 | жертва; caster = точка двери на полу, yaw — внутрь коридора | дверь распахивается (меш `nightmare_door` на петле), из проёма вытекает тьма и силуэт; **на 12 тике** ставьте тень (модель `nm_lurker` + анимация `appear`) |
| `nightmare_house_exit` | 30 | жертва | выход: коридор растворяется, бледная вспышка; дальше `nightmare_stage2` |
| `nightmare_night_seal` | −1 | caster | печать под ногами (правило `SchoolSeals.shown`) |
| `nightmare_night_cast` | 70 | caster | каст **3 с (60 тиков)**: всходит красная луна над магом, небо темнеет; **на 56 тике** — тёмная волна до r24 (старт зоны). Анимация `pohsmp_nightmare_night_cast` |
| `nightmare_night_zone` | 2400 | caster = центр зоны (не follow) | печать r24 по земле (`nightmare_night_floor`), завеса тьмы по краю, tint r24, хлопья; `nightmare_red_moon` в небе (+40) — запасной диск, если код не подменяет луну |
| `nightmare_night_pulse` | 36 | центр зоны | каждые 8 с: кольцо тьмы бежит к центру, удар сердца на 20 тике |
| `nightmare_night_light` | 40 | точка блока света; жертве | свет ≥ 10 удержал стадию — бледный ореол, тьма отступает |
| `nightmare_abyss_cast` | 260 | caster; видят все в r64 | каст **12 с = 240 тиков** + хвост. Шкала = ролик (ТЗ) и анимация `pohsmp_nightmare_abyss_cast`. **9.0 с (180 тик)** — облик мага → `nm_dread` у жертв; **236 тик** — вспышка, волна r64, у всех жертв стадия 3. Печать (`nightmare_abyss_ground`) — внутри эффекта: отметьте его как «каст со своей печатью» (без знака школы и печати ступени) |
| `nightmare_abyss_world` | 6000 | жертва, follow | мир-кошмар на 5 мин; гасить `Fx.stop` при снятии |
| `nightmare_abyss_thicken` | 60 | жертва | сгущение каждую минуту (60/120/180/240 с) |
| `nightmare_abyss_dispel` | 40 | жертва | рассеивание (маг убит / «Благословение») |
| `nm_spawn` / `nm_despawn` | 24 / 24 | caster = кошмар-моб | появление из лужи / рассыпается чернилами (вместе с анимациями `appear` / `vanish`) |
| `nm_hands_grab` | 30 | жертва (у ног) | «Руки из земли» хватают, 1.5 с удержания |
| `nm_maw_roar` | 40 | caster = Пасть | тёмная волна из пасти (вместе с `roar`) |
| `nm_weeper_aura` | −1 | caster = Плакальщица, follow | пока плачет (остальные кошмары сильнее) |
| `nm_lurker_dissolve` | 14 | caster = Тень | посмотрели прямо — клочья тьмы (вместе с `dissolve`) |

Новое для отрисовщика (в `docs/fx.md`, «Добавлено 19.11 (T25)»): `wave.reverse: true` — кольцо сходится к центру (без поддержки — расходится, терпимо).

**Звуки (предложение, ваниль; школе в `Reg` — `WARDEN_HEARTBEAT`):** сердцебиение — `WARDEN_HEARTBEAT`; шёпот — `AMBIENT_CAVE`; скрежет — `GRINDSTONE_USE`
(pitch 0.5); колыбельная — `NOTE_BLOCK_CHIME`/`NOTE_BLOCK_BELL` низко и фальшиво (pitch 0.5–0.7, с замедлением) — в ролике мифического 0–2 с;
провал в «Дом» — `SOUL_ESCAPE` + `AMBIENT_CAVE`; скрип двери — `WOODEN_DOOR_OPEN` (pitch 0.5); красная луна — `ELDER_GUARDIAN_CURSE` (pitch 0.5, тихо);
сгущение — два `WARDEN_HEARTBEAT` громко. Детский смех ваниль не даёт — лучше попросить у владельца запись (`pohsmp_core:nightmare.child_laugh`);
до неё — `ALLAY_AMBIENT_WITHOUT_ITEM` (pitch 0.5) + `VEX_AMBIENT` (pitch 1.4).

## 3. Бестиарий — модели GeckoLib (главное)
GeckoLib есть в сборке (`geckolib-forge-1.20.1:4.8.4`, compileOnly — в паке он у Iron's), поэтому все кошмары — **`GeoEntity` + `GeoEntityRenderer`**:
- модель `geo/entity/nm_<id>.geo.json` (identifier `geometry.nm_<id>`, лицом к −z как в Blockbench, ноги на y = 0);
- текстура `textures/entity/nightmare/nm_<id>.png` — **с отсечкой альфы** (рваные края ткани, кружево, крылья): нужен `entityCutoutNoCull` (у
  `GeoEntityRenderer` по умолчанию так); у кого есть — `nm_<id>_glowmask.png` для `AutoGlowingGeoLayer` (глаза, глотки, слёзы светятся в темноте);
- анимации `animations/entity/nm_<id>.animation.json`, имена `animation.nm_<id>.<имя>`. **Кость `pool`** (лужа чернил под ногами) во всех анимациях,
  кроме `appear`/`vanish`, сжата в 0 — но в кадр до старта контроллера она может мелькнуть: прячьте её в `setCustomAnimations`, когда играет не appear/vanish.
- Текстуры нарисованы по точкам поверхности модели в позе покоя: потёки чернил идут сверху вниз через все грани без швов; кроме того с пальцев,
  подбородков, глаз свисают **кости-капли `drip*`**, которые в каждой анимации тянутся и срываются — чернила «текут» по-настоящему.
- Кастомные инструкции (`timeline`, `CustomInstructionKeyframeEvent`): `hit` — момент удара (урон/звук), `grab`, `roar` (дрожь экрана у жертв),
  `laugh`, `weep`, `wail`, `voice`, `cover_screen`, `scream`. Можно и просто по таймингам из таблицы.

| id | рост, бл. (модель) | хитбокс (предл.) | анимации | заметки для кода и звуки |
|---|---|---|---|---|
| `nm_lurker` | 2.4 (+струйки до 3.1) | 0.6×2.4 | idle (рывок головы на 1.3 с), walk, attack (`hit` 0.45), lunge (бросок, `hit` 0.45), dissolve, appear, vanish | без лица, руки до земли. Посмотрели прямо → `dissolve` + `nm_lurker_dissolve`; спиной 3 с → `lunge`. Звук: тишина; бросок — `ENDERMAN_SCREAM` (0.5) + `PHANTOM_BITE`; растворение — `SOUL_ESCAPE` (0.6) |
| `nm_crawler` | 1.0 (локти выше) | 1.2×0.9 | idle, walk (быстрая рысь), attack (голова раскрывается надвое, `hit` 0.45), pounce (прыжок с потолка, `hit` 0.75), appear, vanish | на потолке — переворачивайте модель на 180° по z. Кости `head_l`/`head_r` — половины головы. Звук: `SPIDER_AMBIENT` (0.6) + `SKELETON_STEP` (0.5) — хруст; шаги `SPIDER_STEP` (0.7); укус `PHANTOM_BITE` |
| `nm_mimic` / `nm_mimic_slim` | 2.2 | 0.6×2.0 | idle (голова клонится слишком сильно на 2–3 с), walk, call (`voice` 0.3), reveal (лицо → пасть, hold), attack (`hit` 0.4), appear, vanish — **файл анимаций общий `nm_mimic`** | **Скин игрока:** атлас 128×64 ед. = PNG 512×256 px (`nm_mimic_template.png`): левая половина 256×256 пуста — **скопируйте туда скин игрока (64×64), увеличив ×4 без сглаживания** (NativeImage → DynamicTexture), правая — пасть, зубы, улыбка. Есть слои шляпы/куртки/рукавов/штанов, шея на 3 px длиннее, улыбка до ушей, голова разрезана: `skull` / `jaw`. `_slim` — для тонких рук (Alex). Ник над головой — как у копируемого. Звук: `call` — голос копируемого (механика голоса T22) или `VILLAGER_AMBIENT` (0.6); reveal — `WARDEN_ROAR` (1.6, коротко) + `SLIME_SQUISH` (0.5) |
| `nm_hollow_child` | 1.2 | 0.5×1.1 | idle, walk, laugh (`laugh` 0.0), attack (`hit` 0.45), appear 0.6 с, vanish 0.4 с | дыры вместо глаз, в глубине — красная искра (glowmask), чернильные слёзы. «Исчезает и появляется за спиной» = `vanish` → телепорт → `appear` |
| `nm_hands` | 1.2 | 2×0.6 (на земле) | idle (шевелятся), grab (`grab` 0.12, держат до 1.4), appear, vanish | 16 рук из лужи r≈1.9 бл.; `puddle` виден всегда. С `grab` — `nm_hands_grab` на жертве. Звук: `MUD_BREAK` + `HONEY_BLOCK_SLIDE` (0.5), хватка — `SLIME_SQUISH` (0.5) |
| `nm_maw` | 3.8 | 2.4×3.8 | idle, walk (медленно, 2.4 с), roar (`roar` 0.4, держит до 1.6), attack (укус-таран, `hit` 0.55 — отброс), appear, vanish | кости `jaw_top`/`jaw_bot`, 4 ноги-ходули. Звук: рёв `RAVAGER_ROAR` (0.6) + `WARDEN_ROAR` (0.8); шаги `SKELETON_STEP` (0.4); укус `EVOKER_FANGS_ATTACK` (0.6) |
| `nm_weeper` | 2.7 (шлейф сзади) | 0.7×2.6 | idle (плачет, `weep`), walk (скользит), flee (убегает, голова назад), wail (`wail` 0.4), appear, vanish | вуаль-кружево (сквозь дырочки видно лицо), чернильные слёзы светятся. Пока плачет — `nm_weeper_aura`. Звук: плач `GHAST_AMBIENT` (1.4, тихо); вопль `GHAST_SCREAM` (0.8) |
| `nm_moth` | рой ~1.4×0.8 | 1×1 | idle/walk (кружат, машут), attack (рой стягивается в диск перед лицом, `cover_screen` 0.5 — включайте накладку `nightmare_moths_screen`), appear, vanish | 12 мотыльков, глаза на крыльях светятся. Сущность держать у головы жертвы. Звук: `PHANTOM_FLAP` (1.8, тихо) |
| `nm_dread` | 3.5 | 0.8×3.2 | idle (парит), walk, attack (4 руки, `hit` 0.45), scream (`scream` 0.1), appear, vanish | **заклинатель глазами жертв** в мифическом (с 9 с ролика): рисовать вместо мага у жертв; фарфоровая маска с чернильными слезами, венец-гребёнка шкатулки. Звук: `WARDEN_HEARTBEAT` фоном, крик `WARDEN_SONIC_CHARGE` + `ENDERMAN_STARE` |

Подмена облика **настоящих** мобов в мифическом: у жертвы рисуйте вместо моба модель кошмара (подобрать по размеру: зомби/скелет → `nm_lurker`
или `nm_mimic`, паук → `nm_crawler`, крупные → `nm_maw`), анимации `walk`/`attack` по состоянию моба; хитбокс и урон — моба.

## 4. Мир-кошмар стадии 3, тени стадии 1, силуэты
- **Экранные накладки** (рисовать поверх всего экрана, растянуть, альфа как есть): `textures/fx/nightmare_stage1.png` (тьма по краям с пальцами теней),
  `nightmare_stage2.png` (гуще + проступают багровые вены), `nightmare_stage3.png` (тяжёлые чернила текут сверху, багровый отлив);
  `nightmare_ink_screen.png` (чернила стекают сверху — ролик/сгущение), `nightmare_moths_screen.png` (мотыльки на краях — атака роя).
- **Подмены вида мира (только у жертвы):** `textures/block/nightmare/grass_block_top`, `grass_block_side`, `leaves_dead` (почти прозрачная — деревья голые),
  `log_dead`, `water_still`/`water_flow` (анимированы, `.mcmeta`); колормапы `textures/colormap/nightmare_grass.png`, `nightmare_foliage.png`.
  Цвета, если проще тонировать: трава `#4A3E36`, листва `#3A2E2C`, вода `#0A0610` (туман в воде `#05020A`), небо `#1A0408`, туман `#0E0206`,
  облака `#3A0A16`, свет неба ×0.5. Скрюченные ветви — меш `fx/meshes/nightmare_branches` на верх ствола.
- **Небо и луна:** `textures/environment/nightmare_sky.png` (1024×512, купол/фон), `nightmare_moon_phases.png` (как ванильный `moon_phases.png`:
  4×2 фазы, красная луна с потёками) — для стадии 3 и для «Ночи без рассвета» (у врагов внутри r24: ночь + эта луна).
- **Искажённые лица:** `textures/entity/nightmare/face_overlay_skin.png` (64×64 по развёртке скина — слоем поверх головы игроков и мобов-гуманоидов:
  провалы глаз со слезами, рот разодран в крике) и `textures/fx/nightmare_face_overlay.png` (128, для остальных лиц декалью/billboard).
- **Тени стадии 1:** декаль `textures/fx/nightmare_shadow_reach.png` уже в `nightmare_stage1` (шевелится: вращение туда-обратно, пульс). Мигание света — код.
- **Силуэты:** `textures/sigil/nightmare_silhouette_0..2.png` + эффекты `nightmare_silhouette_0..2`.

## 5. «Дом, которого нет» — коридор
- Меш-модуль `fx/meshes/nightmare_corridor`: 3 (x, −1.5…1.5) × 3.5 (y) × 4 (z, 0…4) блока, ставить подряд вдоль +z — стыкуется без шва. Обои, панель,
  плинтус, карниз, кессоны потолка, тусклая лампа (свет `#FFB070`), пустые рамы, пятна, потёки чернил по стенам, чернила из-под дверей.
  **Двери** — по одной на каждой стене в середине модуля: центр проёма (±1.45, 0…2.2, z0 + 2). Открытая — меш `nightmare_door`
  (1×2.2, петля x = −0.5; в `nightmare_house_shadow` поворот на петле ключами) или текстура `textures/fx/nightmare_door_open.png`.
- «Коридор едет с жертвой»: держите 5–7 модулей вокруг неё, при сдвиге на 4 бл. переставляйте задний вперёд; повороты коридора не нужны.
- Если удобнее рисовать своими квадами — материалы `textures/fx/nightmare_wall.png`, `nightmare_floor.png`, `nightmare_ceiling.png` (по 256 px на блок,
  тайлятся), `nightmare_door.png` / `nightmare_door_open.png` (128×256 на 1×2 бл.).

## 6. Анимации заклинателя (`assets/irons_spellbooks/player_animation/`, `new AnimationHolder("<имя>", true)`)
| имя | длина | что |
|---|---|---|
| `pohsmp_nightmare_house_cast` / `_finish` | 2.5 с (hold) / 1.0 с | палец к губам «тсс», рука к цели — берётся за невидимую ручку, поворачивает ключ, тянет дверь на себя; на 2.2 с отпускает (46 тик — провал) |
| `pohsmp_nightmare_night_cast` / `_finish` | 3.0 с (hold) / 1.2 с | ладонь вперёд → кулак вниз («гасит свет»), правая поднимает луну; на 2.8 с (56 тик) кулак вниз — закат навсегда |
| `pohsmp_nightmare_abyss_cast` / `_finish` | **12 с = 240 тиков** (hold) / 1.5 с | зажимает уши и качается → поднимает чернила → руки V к небу → обнимает себя → 9 с удар сердца, выгиб → тьма, голова набок → 11.8 голова к зрителю, когти |
Касты замирают в последней позе — после каста играть `_finish`.

## 7. lang (ru/en, 47 ключей)
`school.pohsmp_core.nightmare`; `attribute.pohsmp_core.nightmare_spell_power` / `nightmare_magic_resist`; `item.pohsmp_core.broken_lullaby` (+`.desc`);
`death.attack.nightmare_magic` (+`.item`, `.player`) — под тип урона `nightmare_magic` (JSON типа урона — код); `spell.pohsmp_core.<3 id>` + `.guide`;
`effect.pohsmp_core.<immersion|endless_night|no_awakening|house_that_isnt>` + `.description`; `fx.pohsmp_core.no_awakening.title`;
`entity.pohsmp_core.nm_<9 id>`; ui: `ui.pohsmp_core.nightmare.{stage,stage.1..3,resisted,no_target,light_holds}`, `house_that_isnt.time`,
`endless_night.zone`, `no_awakening.{cast,time,thicken.1..4}` (формат `%s` как у соседей; лишнее — удалим).

## Вопросы / что нужно
1. Длины кастов Высших в ТЗ не заданы — я поставил «Дом» 2.5 с, «Ночь» 3 с (под них fx и анимации). Если в свитках/конфиге другие — скажите, подгоню.
2. Детский смех для «Пустого ребёнка» и колыбельную для ролика мифического лучше своими звуками — если владелец пришлёт записи, подложу и разведу по таймингам.
3. Мимику нужен скин копируемого игрока на клиенте жертвы — проверьте, что скин доступен (`SkinManager`) и для игроков вне зоны прорисовки.
