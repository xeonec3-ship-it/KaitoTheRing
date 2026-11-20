# T26 «Head of the Cult of Mellisto» — визуальная часть готова (помощник по визуалу → управляющему; для чата Кодинга)

Ветка `claude/cnpc-chats-repo-0hcody`. Java не трогал. Сделаны все ваши дополнения: особые заклинания, «Реплика», добивание, полоса по фазам.
Генератор — **`tools/gen_cult_leader.py`**. Он вызывает `gen_cult_leader_fx.py`, тот вызывает `gen_cult_leader_extra.py`, превью — `cult_leader_render.py`.
Перед запуском нужен jar Iron's: `python3 tools/fetch_libs.py`.
- Запуск: `python3 tools/gen_cult_leader.py [--shots] [--html]`.
- Интерактивное превью: `tools/cult_leader_preview.html` (модель, все анимации, облик души).

Планы роликов по секундам дописаны в ТЗ: `docs/specs/tasks/T26_cult_leader_boss.md`, раздел «Визуал и ролики».

Обзорные картинки в `docs/media/`:
- `t26_model.jpg`, `t26_textures.jpg` — модель и текстуры;
- `t26_poses.jpg` — появление и смерть;
- `t26_special_anims.jpg` — новые анимации;
- `t26_fx.jpg` — арена сверху: печать «Приговора», стена огня;
- `t26_special_fx.jpg`, `t26_ui.jpg`, `t26_bossbar_phases.jpg` — особые заклинания, титры, полосы.

**Имя (владелец 20.11):** на обоих языках «Head of the Cult of Mellisto». Это `entity.pohsmp_core.cult_leader` и титр.
Прочие фразы в ru — по-русски («Глава Культа выносит приговор…»).

## 1. Что взято из Iron's и как подключить
- **Модель** `geo/entity/cult_leader.geo.json` (identifier `geometry.cult_leader`). Это `tyros.geo.json` с прежними костями и именами.
  - Атлас расширен до 128×128 ед. Старые UV — те же пиксели.
  - Новые кубы добавлены в существующие кости: венец (`armor_head`), медальон (`armor_chest`), амулеты (`torso`), шипы (`armor_*_arm`).
  - Новая кость **`cape`** (дочь `torso`). Анимации Iron's её не трогают; по желанию качайте её в `setCustomAnimations`: rotX = 6° + max(0, ±взмах ног)·0.6.
- **Текстуры** `textures/entity/cult_leader/` (512×512 = атлас ×4, только цвета палитры Тироса):
  - `cult_leader.png`;
  - `cult_leader_soul_mode.png` — вместо `tyros_soul_mode`. Лицо в облике души тёмное, без свечения — по замечанию владельца;
  - `cult_leader_glowmask.png`, `cult_leader_soul_mode_glowmask.png` — для `AutoGlowingGeoLayer`: глаза, медальон, кончики венца, угли по подолу;
  - `cult_leader_flame.png` 64×512 — огонь головы, как `tyros_flame` 16×128: 8 кадров по вертикали, тот же UV-расчёт кадра.
    Для `FireBossFlameLayer` копируйте его со своим RL.
- **Анимации** `animations/entity/cult_leader.animation.json` — **все** анимации `casting_animations.json` Iron's под теми же именами
  (их зовёт логика FireBoss) плюс наши `cult_leader_*`.
  - В модели: `getAnimationResource` → `pohsmp_core:animations/entity/cult_leader.animation.json`.
  - События — ключи `timeline` (GeckoLib `CustomInstructionKeyframeEvent`), их можно заменить таймерами по таблице ниже.
- **Звуки:** файлы Iron's не копировал. События в нашем `sounds.json` ссылаются на `irons_spellbooks:fire_boss/*` и ваниль, с другим pitch.
  - `cult_leader.spawn`, `death`, `death_final`, `verdict`, `verdict_lock`, `verdict_end`, `phase`, `firewall`, `firewall_loop`, `summon`;
  - `first_flame`, `first_flame_impact`, `ash`, `ash_slash`, `replica_break`, `finisher`;
  - **`music.cult_leader`** — заглушка: фон боя Тироса `fire_boss/music/backtrack`, stream. Трек владельца положить в `pohsmp_core:music/cult_leader`.
- **Культисты:** `geo/entity/fire_cultist.geo.json` + `fire_cultist.png` и `fire_cultist_glowmask.png` в той же папке.
  - Это `abstract_casting_mob.geo.json` (как у пироманта) с теми же костями, плюс капюшон, оплечье, пояс и новая кость `cape`.
  - Предлагаю наследника `PyromancerEntity` **без брони** (броня пироманта закроет облик) с этой моделью и текстурой.
  - Огонёк у подола по желанию — `fx/fire_cultist_aura`.
- **Полоса босса:** `BossbarSprite(pohsmp_core:boss_bars/cult_leader_bossbar, 192, 18, 3, -1)` — формат и цвета `tyros_bossbar`.
  Фазы — п. 5.

## 2. Анимации босса (GeckoLib, наш файл)
| имя | длина | события (`timeline`, с) | для чего |
|---|---|---|---|
| `fire_boss_spawn` (Iron's) | 8.75 | — | ролик появления: выводит босса из точки в 3.75 бл. позади |
| `fire_boss_death` (Iron's) | 8.0 | — | смерть: ролик — первые 3.5 с, на коленях к 2.6 с |
| `cult_leader_first_flame` | 6.0 | `plant` 0.9, `sigil` 1.6, `pillar` 4.0 | «Первое Пламя»: коса в землю, рука к небу, рывок при ударе столба |
| `cult_leader_ash_dissolve` | 1.2 | `ignite` 0, `gone` 1.2 | «Пепел Меллисто»: руки в стороны, кость `body` сжимается в 0.02; после `gone` — скрыть |
| `cult_leader_ash_reform` | 1.0 | `reform` 0, `ready` 1.0 | собирается из пепла в позу замаха |
| `cult_leader_ash_slash` | 1.5 | **`slash` 0.5** | огромный горизонтальный взмах с выпадом; урон по линии — в 0.5 |
| `cult_leader_replica_break` | 2.6 | `crush` 0.9, `shatter` 1.5, `speak` 1.9 | ломает «Реплику»: сжимает верхние печати, косой снизу вверх, фраза |
| `cult_leader_finisher` | 2.4 | `pull_done` 0.7, **`impale` 1.0**, `flame` 1.7, **`kill` 2.2** | добивание: тянет, пронзает, поднимает, вспышка |

Для фазы 3 (ярость, облик души) хороша `fire_boss_half_health_attack` Iron's.
Для каста «Приговора» — `charge_raised_hand` (первые 2 с, рука вверх).

**Жертва добивания** — `pohsmp_cult_finisher_victim` (PlayerAnimator, 2.4 с, hold; `tools/gen_player_anims.py`,
`assets/irons_spellbooks/player_animation/`). Шкала совпадает с `cult_leader_finisher`.
Положение жертвы задаёт код:
- 0–0.7 с — плавно (easeInQuad) в точку 1.8 бл. перед боссом;
- 1.0–1.7 с — подъём на +1.3 бл. (easeInOutQuad), висит;
- 2.2 с — смерть.

Сообщение о смерти — `death.attack.pohsmp_core.cult_finisher`.

## 3. Эффекты (`fx/*.json`, стиль `fx/styles/cult_leader.json`)
Длительности — в тиках. caster/target — как в ctx. `point:center` — центр арены (точка появления).

| fx | длит. | где | заметки для кода |
|---|---|---|---|
| `cult_leader_intro` | 175 | caster = босс на конечной точке, yaw — его взгляд | ролик появления; **модель не рисовать 0–30 тиков**; титр на 130, полоса на 175 |
| `cult_leader_verdict` | 240 | caster = центр зоны (босс в момент приговора, не follow) | **0–40 — предупреждение** (печать r24 прорисовывается, мир краснеет, край прорастает); **40 — запрет начался** (вспышка, волна); **40–240 — запрет**; действия: `verdict_warn` → `verdict` |
| `cult_leader_verdict_mark` | 200 | caster = игрок под запретом, follow | метка над головой — перечёркнутый знак культа; слать всем |
| `cult_leader_verdict_fizzle` | 14 | caster = игрок | попытка колдовать под запретом — заклинание гаснет пеплом в руке; + `verdict_blocked` |
| `cult_leader_firewall` | −1 | caster = P, не follow | фаза 3: стена огня r28 до `Fx.stop`; урон при пересечении r 27.5–28.5, блоки не жечь |
| `cult_leader_firewall_burn` | 18 | caster = игрок | вспышка на пересёкшем стену |
| `cult_leader_phase2` | 60 | caster = босс, follow | короткий переход 66% — если «Первое Пламя» почему-то не играет |
| `cult_leader_phase3` | 80 | caster = босс | 33%: столб огня, волна к r28; **на 30 тике запустить `cult_leader_firewall`** |
| `cult_leader_fury` | −1 | caster = босс, follow | ореол ярости (облик души) до `Fx.stop` |
| `cult_leader_summon` | 40 | caster = точка появления культиста | печать огня, столб; **культиста ставить на 24 тике** |
| `cult_leader_death` | 100 | caster = босс | ролик смерти 3.5 с; **на 52 тике** — погасить слой огня головы и `Fx.stop` стены |
| `cult_first_flame` | 130 | caster = босс, `point:center` = P | «Первое Пламя»; кольцо огня **r(t) = 3 + 25·(t − 80)/40**, урон при \|d − r\| < 0.8, если игрок ниже 1 бл. над землёй (перепрыгнуть) |
| `cult_ash_dissolve` / `cult_ash_vortex` (−1, follow) / `cult_ash_reform` | 34 / −1 / 24 | caster = босс | рассыпание → вихрь (код двигает невидимого босса 1.2–3.0 с, ставит в 3.5 бл. перед целью) → сборка |
| `cult_ash_line` | 34 | caster = босс, **yaw = направление удара** | линия-предупреждение на земле 56 бл. (через арену), 1.5 с; ширина урона — код, предлагаю 1.5 бл. |
| `cult_ash_slash` | 40 | то же, yaw тот же | удар (событие `slash`): огонь вырывается вдоль линии, след горит 10 с |
| `cult_leader_replica_break` | 56 | caster = босс | см. ниже |
| `cult_leader_finisher` | 56 | caster = босс, **target = жертва** | хватка, искры на `impale` (20), вспышка на `flame` (34, follow жертвы), пепел на `kill` (44) |

**«Реплика» на боссе.** Её fx (`disintegration_replica`) пусть успеет начаться (~2 с: поле и верхние печати). Затем:
1. Запустить анимацию и `cult_leader_replica_break`. На 10–14 тике по печатям Реплики бегут трещины (`sigils/cult_replica_cracks` на +4.82, +2.42, 0).
2. **На 18 тике (`crush`)** — `Fx.stop` экземпляра Реплики: её печати рассыпаются своим dissolve, наш fx добавляет осколки.
3. **30 (`shatter`)** — косой: остатки и кольцо.
4. **38 (`speak`, 1.9 с)** — фраза `ui.pohsmp_core.cult_leader.replica_taunt` в чат (r32, цвет босса) и субтитром над ним на 3 с; не чаще раза в 20 с.

Новых параметров отрисовщика нет — только существующие (`wave.texture`/`reverse`, `decal shape: crack` + `yaw`, `vortex.flow`).
Значок `✦` в надписях печатей — как в прежних (шрифт `cyrillic`).

## 4. Печати, текстуры, титры, иконка
- Печати:
  - `sigils/cult_verdict` — r24, ground: обод языков огня внутрь, 8 перечёркнутых знаков школ на цепи, 4 клинка, око в пламени, надпись по кольцу;
  - `cult_emblem` — знак культа под боссом;
  - `cult_verdict_mark` — над головой;
  - `cult_first_flame` — sky, r22, на +26 над P;
  - `cult_replica_cracks`.
- Рисунки (`textures/sigil/`): `mellisto_verdict`, `cult_emblem`, `cult_verdict_mark`, `cult_first_flame`;
  `cult_flame_tongue` (язык пламени для `curtain`), `cult_scorch_ring` (decal r29.5), `cult_fire_ring` (`wave.texture`).
- Титры `textures/gui/title/` (1024×192, золото в цветах полосы, под надписью знак с полосы):
  - `cult_leader_{ru,en}` — оба с английским именем;
  - `cult_first_flame_{ru,en}` («Первое Пламя» / The First Flame);
  - `cult_ash_{ru,en}` («Пепел Меллисто» / Ashes of Mellisto).

  Показ: вход 0.5 с, уход 0.75 с; время — в ТЗ.
- Иконка эффекта «магия под запретом»: `textures/mob_effect/mellisto_verdict.png` (`effect.pohsmp_core.mellisto_verdict` + `.description`).

## 5. Полоса здоровья по фазам (`textures/gui/sprites/boss_bars/`, все 192 шириной, формат tyros: строки 0–17 пустая, 18–35 полная)
| файл | что |
|---|---|
| `cult_leader_bossbar.png` | фаза 1: огненная рамка, знак-око в пламени по центру |
| `cult_leader_bossbar_p2.png` | фаза 2: руны запрета по верхней и нижней кромке, золотые знаки (ромб с оком) по краям, заливка темнее |
| `cult_leader_bossbar_p2_pulse.png` | яркий кадр фазы 2 для пульса во время запрета магии |
| `cult_leader_bossbar_p3.png` | фаза 3: рамка опалена, заливка ярче, тёмные трещины с раскалёнными краями |
| `cult_leader_bossbar_p3_flames.png` | 192×112: **8 кадров по 192×14** (кадр k — строки 14k…14k+13), языки огня над рамкой |
| `cult_leader_bossbar_flash.png` | 192×18: силуэт полосы светлым золотом — вспышка при смене фазы |

**Как рисовать** (своя отрисовка поверх boss bar, как `BossbarManager.renderCustomBossbar`: x = (ширина − 192)/2, y = event.getY() − 1;
пустая половина — blit v = 0, полная — v = 18 шириной `3 + progress·186`):
- **Фаза 1, фаза 3** — как обычно своим спрайтом.
- **Фаза 3, языки огня:** перед полосой нарисовать кадр `(tick/2) % 8` из `_p3_flames` в точке (x, y + 9 − 14) = (x, y − 5).
  Затем саму полосу поверх: рамка закроет основания языков.
- **Фаза 2, пульс во время запрета:** рисовать `_p2`, поверх `_p2_pulse` с альфой `0.5 + 0.5·sin(2π·t/1.2 с)`.
  Вне запрета — только `_p2`.
- **Смена фазы:** 6 тиков рисовать новую полосу, поверх `_flash` с альфой 1 → 0 (easeOutCubic).

## 6. lang (ru/en)
- Сущности: `entity.pohsmp_core.cult_leader`, `fire_cultist`.
- `ui.pohsmp_core.cult_leader.*`:
  - `title`, `subtitle`;
  - `verdict_warn`, `verdict` (с `%s` секунд), `verdict_blocked`, `verdict_end`;
  - `phase2`, `phase3`, `firewall`, `summon`, `death`;
  - `first_flame`, `first_flame_warn`, `ash`, `ash_warn`, `replica_taunt`.
- Остальное: `effect.pohsmp_core.mellisto_verdict` (+ `.description`), `death.attack.pohsmp_core.cult_finisher`, `subtitles.pohsmp_core.cult_leader.*`, `subtitles.pohsmp_core.music.cult_leader`.

## Что не проверено
В игре не смотрел. Проверить в первую очередь:
- позы с косой: в превью коса — условный силуэт, в игре её рисует Iron's;
- плащ при беге (может пересекать ноги — тогда качать кость `cape`);
- пульс полосы фазы 2.

## 7. «+4 заклинания» (дополнение 20.11; генератор `tools/gen_cult_leader_spells4.py`)
Обычные приёмы без ролика, у каждого видимое предупреждение, лучей к цели нет. Имя, облик души, цвета косы — не трогал.
Отдельный запуск — `python3 tools/gen_cult_leader_spells4.py`. Он дописывает только эти анимации, fx, печать, иконку и lang.
При полной перегенерации (`tools/gen_cult_leader.py`) скрипт вызывается сам.

**Анимации** (в `animations/entity/cult_leader.animation.json`, события — ключи `timeline`):
| имя | длина | события (с) | что делать коду |
|---|---|---|---|
| `cult_leader_sickle_throw` | 2.2 | `warn` 0, **`throw` 1.0**, **`catch` 1.8** | 0 — fx `cult_sickle_warn` (дуга 1 с). На `throw` скрыть косу в руке и пустить сущность-косу (рисовать предмет **`cult_scythe`**, вращение ~40°/тик) по петле из письма + fx `cult_sickle_spin` (follow) до возврата. На `catch` вернуть косу в руку, `Fx.stop` следа, fx `cult_sickle_catch` |
| `cult_leader_ash_trail_dash` | 1.4 | `warn` 0, **`dash` 0.5**, `stop` 0.9 | 0 — fx `cult_ash_trail_warn` (линия 12 бл., 0.5 с). На `dash` — рывок 12 бл. за 0.4 с (сквозь игроков) + `cult_ash_trail_dash` (follow) и `cult_ash_trail` в точке начала (yaw тот же; 4 с полоса, урон в ней — код, ширина ~1.6). Другая длина рывка — `.scale(dist/12)` |
| `cult_leader_brand` | 1.2 | **`brand` 0.55** | на `brand` — эффект `pohsmp_core:cult_brand` (иконка `mob_effect/cult_brand.png`) и fx `cult_brand` на игроке (follow, всем). Через 60 тиков — урон r3 + `cult_brand_explode`; меченому — `brand_warn` |
| `cult_leader_pillars` | 2.3 | **`mark` 0.3**, **`erupt` 1.8** | на `mark` — 5 точек вокруг игроков, в каждой `cult_pillar_warn` (круг r1.6, 1.5 с). На `erupt` — `cult_pillar` в тех же точках (столб r1.4 × 9), урон |

**Путь «Огненного серпа»** — в осях взгляда босса в момент броска, s = 0…1 за ~0.8 с:
z = 6·(1 − cos 2πs) (вперёд, до 12 бл.), x = 4·sin 2πs (вправо на пути туда, влево на обратном).
Дуга-предупреждение `cult_sickle_warn` нарисована по этой же кривой.

**fx** (стиль `cult_leader`): `cult_sickle_warn` 26, `cult_sickle_spin` −1, `cult_sickle_catch` 8, `cult_ash_trail_warn` 12,
`cult_ash_trail` 80, `cult_ash_trail_dash` 10, `cult_brand` 60, `cult_brand_explode` 24, `cult_pillar_warn` 30, `cult_pillar` 30.
Печать `sigils/cult_brand` (над головой меченого).

**lang:**
- названия приёмов: `ui.pohsmp_core.cult_leader.sickle`, `ash_trail`, `brand`, `pillars`;
- предупреждение меченому: `ui.pohsmp_core.cult_leader.brand_warn`;
- статус: `effect.pohsmp_core.cult_brand` и `.description`.

Кадры поз — `docs/media/t26_spells4_anims.jpg`.
