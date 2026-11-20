# T27 «Ирина, Ведьма Ревности» — код готов (облачный программист → чату Кодинга / управляющему)

Ветка `claude/cnpc-chats-repo-0hcody`. Сделано на каркасе боссов (T26). `./gradlew build` проходит, **124 теста зелёные**;
новый тест — `IrinaMathTest` (6 тестов: тайминги сверены с событиями `timeline` в `irina.animation.json`, фазы, пары, деление
урона, узлы, кокон, кража, взгляд, плеть, марионетка, метка). Тестовый jar не собирал и `builds/` не трогал (соберёт управляющий).
**В игру зайти не могу** — что не проверено, перечислено в конце.

Коммиты: `T27 Irina: server side …`, `T27 Irina: client …`, затем это письмо.

---

## 1. Новые файлы (скопировать как есть)
```
src/main/java/ru/pohsmp/core/boss/irina/          Irina, IrinaConfig, IrinaEntity, IrinaFight, IrinaMath
src/main/java/ru/pohsmp/core/boss/irina/client/   IrinaClient, IrinaModel, IrinaRenderer
src/test/java/ru/pohsmp/core/boss/irina/          IrinaMathTest
src/main/resources/data/pohsmp_core/damage_type/  irina_threads.json, irina_cocoon.json
```

## 2. Точечные правки существующих файлов
| файл | место | что вставить |
|---|---|---|
| `boss/Bosses.java` | после `…CultLeader.register();` | `ru.pohsmp.core.boss.irina.Irina.register();       // T27` |
| `boss/Bosses.java` | после `…CultLeader.events();` | `ru.pohsmp.core.boss.irina.Irina.events();         // T27` |
| `boss/BossConfig.java` | в секции `[irina]`, после `PER.put("irina", …);` (перед `b.pop()`) | `ru.pohsmp.core.boss.irina.IrinaConfig.define(b);   // T27 mechanics keys` |
| `boss/client/BossClient.java` | `setup`, после строки T26 | `e.enqueueWork(ru.pohsmp.core.boss.irina.client.IrinaClient::setup);       // T27: camera plans` |
| `boss/client/BossClient.java` | `renderers`, после строки T26 | `ru.pohsmp.core.boss.irina.client.IrinaClient.renderers(e);   // T27` |
| `data/minecraft/tags/damage_type/bypasses_armor.json` | в `values` | `"pohsmp_core:irina_threads", "pohsmp_core:irina_cocoon"` |
| `data/minecraft/tags/damage_type/bypasses_enchantments.json` | в `values` | то же |
| `assets/pohsmp_core/sounds.json` | новое событие перед `irina.spawn` | `irina.replica_break` — ваниль `mob/sheep/shear` ×0.9, `dig/cloth1/2` ×0.8 (каркас играет `<id>.replica_break` сам; по совету письма о Реплике: ножницы + шерсть) |
| `lang/ru_ru.json`, `lang/en_us.json` | после `subtitles…cult_leader.replica_break` | `subtitles.pohsmp_core.irina.replica_break`: «Печати Реплики рвутся нитями» / «Replica seals torn by threads» |

Больше ничего общего не тронуто: `PohCore`, `Reg`, `Net`, `ServerConfig`, `ClientInit`, ассеты помощника (модель, посох, анимации,
fx, текстуры, lang Ирины) — без изменений. Все остальные ключи lang, звуки, fx, иконки, титры, полоса — уже были.

> Для сборки в облаке понадобился `libs/voicechat-forge-1.20.1-2.6.20.jar` (его нет в `tools/fetch_libs.py`; скачал с Modrinth,
> в git не попадает). Стоит добавить его в `fetch_libs.py`.

---

## 3. Что сделано

**Сущность** `pohsmp_core:irina` — наследник Iron's `AbstractSpellCastingMob` (GeckoLib, кости мага Iron's), `IAnimatedAttacker`
(анимации шлются пакетом Iron's `serverTriggerAnimation`). Хитбокс 0.7×2.4. Посох `pohsmp_core:irina_staff` (предмет без рецепта,
не в творческой вкладке) — в правой руке, рисует рендер Iron's в кости `rightItem` (хват из `models/item/irina_staff.json`).
Тело из `[irina]` (ХП 4400 × игроки, броня 8, скорость 0.26, крюк 22, spell_power 1.4, spell_resist 1.3, огонь 0.85, кровь 1.3).
Лута нет, опыт 500. Иммунитет к удушью, утоплению, падению и огню мира; **огонь заклинаний и ударов проходит** (слабость к огню —
`fireImmune()` каркаса для неё переопределён, см. §5).

**Два контроллера** (клиент): «тело» `irina_body` — `irina_idle`/`irina_walk` и любое действие из пакета (одноразовые; `irina_cast_long`
и `irina_puppet_hold` — петлёй до `"-"`), смерть — `irina_death` (держать последний кадр); «ткань» `irina_cloth` — `cloth_spawn` при
появлении, `cloth_cocoon` при «Только мой», `cloth_storm` при любом другом действии и всю фазу 3 (флаг FURY синхронизирован),
`cloth_death` при смерти, иначе `cloth_idle`/`cloth_walk`. Процедурные качания рук/ног Iron's выключены (их делают её idle/walk),
голова за взглядом — от Iron's. Три контроллера каста Iron's оставлены, но она не кастует заклинания Iron's.

**Бой (без роликов):** свой ИИ — идёт к цели (фаза 1 — к меченому, +20% скорости), крюк посоха (`irina_staff_attack`, удар на 0.55 с,
дальность `melee_reach` 3.2, раз в `melee_interval_ticks` 30). **«Нитяной укол»** (базовая дальняя атака из баланса,
`thread_bolt_damage` 20 / 50 тиков): цель дальше 5 бл. → узел `irina_knot_trap` под ней, через 0.8 с нити бьют вверх r1.5
(`irina_yank`) — **никаких лучей от неё**, от укола уходят шагом в сторону.

**Фаза 1 «Зависть»:** метка «Предмет ревности» на сильнейшем (урон за 30 с, каркас), переоценка раз в 15 с; fx `irina_mark_apply` →
`irina_mark` (до `Fx.stop`), эффект `jealousy_mark`, строки `mark_self` / `mark_others` / `mark` в чат; урон остальных по ней ×0.5.

**Фаза 2 «Красные нити»** (начинается в конце «Чужого счастья»): пары (нечётный — без пары), знак `irina_bond_1…4` над обоими (без
линии), эффект `thread_bond`, сообщение `bond`; урон одного (после брони) делится 50/50 — вторая половина партнёру типом
`irina_threads` (сквозь броню) + `irina_bond_share`; 9–12 бл. — `irina_bond_strain` раз в секунду и `bond_strain`; >12 — разрыв: обоим
30% макс. ХП (`irina_threads`), `irina_bond_snap`, новая нить через 10 с; перетасовка раз в 30 с; полоса пульсирует, пока есть пары.

**Фаза 3 «Ярость ревности»:** `irina_phase3` + на 30-м тике ореол `irina_fury` до смерти, ткань — шторм. Кража раз в 20 с
(`irina_steal`: pull 0.3 — `irina_steal_lose` на жертвах; absorb 1.2 — у 3 ближайших по 2 сильнейших полезных эффекта, ей — на 20 с,
уровни: всё ≤ II, «Сопротивление» ≤ I; невидимость не крадётся); плеть раз в 6 с, если кто-то в кольце: `irina_whip_warn` 0.8 с →
`irina_whip`, кольцо 1.5–7 — 30 + замедление II 2 с.

**«Чужое счастье»** (66%, ролик 6 с, бой идёт): титр `irina_happiness` на 0.4 с; на 1.4 — снять **все** полезные эффекты у всех в r24
(`irina_steal_lose`, сообщение `steal` со списком, значок `stolen_happiness`); на 5.2 — ей на 30 с (с теми же потолками уровней);
на 6.0 — пары. Если особые выключены (`specials=false`) — короткий `irina_phase2` и пары сразу.

**«Только мой»** (15%, ролик 6.2 с): жертва — сильнейший. 1.0 — `irina_yank` в старой точке, перенос в 2 бл. перед ней, `irina_yank`
в новой; с этого момента жертва держится на месте, не бьёт, не колдует, не прыгает. 1.6 — кокон `irina_cocoon`, ХП кокона
40·(N−1), не меньше 60; **удары союзников по жертве идут в кокон** (жертву не ранят). Разорвали — `Fx.stop` кокона, `irina_cocoon_break`,
`irina_only_mine_broken`, Ирина сразу продолжает бой. Нет — на 5.4 `irina_cocoon_crush` и 60% макс. ХП типом `irina_cocoon`
(смертельно → её добивание). Камера: у всех, кроме жертвы — 0–2 с по плану; у жертвы своя с 1.0 до 5.4 (позади-сверху, на капюшон).

**+4 заклинания** (общий интервал `ability_gcd_seconds` 3 с, свои перезарядки):
- «Ревнивый взгляд» — кто смотрел в конус 25° на неё ≥ 2 с (в 32 бл., на виду), получает `jealous_gaze` (−15%/уровень, II на 4 с)
  + `irina_gaze_mark`; проверка-каст `irina_gaze` раз в 15 с; без урона.
- «Узлы» — 3+⌈N/2⌉ (≤ 6) видимых узлов `irina_knot_trap` у игроков на 20 с; наступил — `irina_knot_snare`, `thread_snare` 2 с
  (скорость −100%, прыжок гасится) + 10. Перезарядка `knots_cooldown` 22 с (в балансе не было — моё предложение).
- «Подмена любимого» — два случайных меняются местами, `irina_swap` у обоих до и после, тошнота 2 с (+2 с, чтобы эффект успел
  проявиться), сообщение `swap`; 25 с.
- «Марионетка» — 3 с: `marionette` (свои ноги −100%), сервер ведёт игрока к ней 0.6 скорости шага, не бьёт и не колдует, fx
  `irina_puppet`; снимается, когда другие нанесли ей ≥ 2% макс. ХП (`irina_puppet_break`, `puppet_break`); у неё `irina_puppet_hold`; 20 с.

**Эффекты-статусы** (иконки помощника): реестр `pohsmp_core:irina_<иконка>` (`irina_jealousy_mark`, `irina_thread_bond`,
`irina_stolen_happiness`, `irina_jealous_gaze`, `irina_snared`, `irina_puppet`) — так атлас берёт `textures/mob_effect/irina_*.png`
без копий; имя — готовые ключи `effect.pohsmp_core.<имя>` (`getDescriptionId`). Молоко их не снимает.

**Добивание:** 2.6 с, жертва за 0.8 с (easeInQuad) в 1.6 бл. перед ней, поза — `pohsmp_cult_finisher_victim` (своей нет, как советовал
помощник), 1.3 — звук крюка, 1.7 — `finisher_whisper` субтитром над ней 2 с (без чата), 2.2 — смерть
`death.attack.pohsmp_core.irina_finisher`; камера жертвы 0.3–2.3 сбоку 15° на уровне глаз, на капюшон.

**Реплика:** каркасный `BossReplica` с её таймингами: через 2 с `irina_replica_break` (2.2 с) + fx, на 1.0 каст снимается (мана,
кулдаун), на 1.25 — «Какая милая вещица, но увы фальшивая» (чат r32 + субтитр 3 с, не чаще 20 с).

**Ролики:** появление 7 с (неуязвима, ИИ выкл.; анимация на 1-м тике, когда клиенты уже видят её; звуки 0/2.6/5.4; титр `irina` +
подзаголовок и музыка на 4.6; полоса на 7.0) и смерть 5 с (`death_final` на 4.2, затухание модели 4.2–5.0, на 5.0 исчезает без
трупа; ванильное удаление через 1 с отключено) — камеры по таблицам ТЗ. Команда — `/pohsmp boss irina`.

**Ключи `[irina]`** (новые, кроме тела): `hunt_speed_mult, melee_reach, melee_interval_ticks, thread_bolt_damage,
thread_bolt_interval_ticks, mark_reassign_seconds, mark_damage_mult, bond_reshuffle_seconds, bond_share, bond_break_distance,
bond_snap_share, bond_reform_seconds, happiness_radius, stolen_seconds, stolen_max_amplifier, stolen_resistance_max, steal_interval,
steal_targets, steal_per_target, steal_seconds, whip_damage, whip_cooldown, whip_slow_seconds, cocoon_seconds, cocoon_hp_per_ally,
cocoon_hp_min, cocoon_crush_share, gaze_seconds, gaze_angle, gaze_slow_seconds, gaze_slow_amplifier, gaze_cooldown, knots_base,
knots_max, knot_life_seconds, knot_snare_seconds, knot_damage, knots_cooldown, swap_cooldown, swap_nausea_seconds, puppet_seconds,
puppet_walk_mult, puppet_break_share, puppet_cooldown` — значения из `balance_bosses.md` §3 (кроме трёх помеченных «моё»: крюк
3.2/30 тиков, узлы 22 с).

---

## 4. Что проверить в игре (в первую очередь)
1. `/pohsmp boss irina`: ролик появления (кокон → облёт → расплетание → шляпа → взмах), титр и подзаголовок на 4.6 с, полоса
   **с эпитетом** на 7.0 с, музыка-заглушка.
2. **Анимации**: idle/walk на теле и ткани одновременно, нет «двойного» шага (процедура Iron's выключена); после действия
   возвращается в idle; смерть держит последний кадр и модель гаснет. Если какое-то действие «залипает» — `hasAnimationFinished`
   GeckoLib, см. `IrinaEntity.bodyState`.
3. **Посох в руке** (хват помощника не проверен в игре).
4. Метка: fx над меченым, ×0.5 урона остальных (видно по полосе), охота за меченым.
5. Пары: знаки над обоими, деление урона, натяжение и разрыв на 12 бл., пульс полосы.
6. «Чужое счастье»: эффекты снимаются у игроков и появляются на ней (видно по частицам или `/data get entity`), титр, камеры
   (общий с высоты — со стороны своего игрока).
7. «Только мой»: перенос жертвы, кокон держит, удары союзников по жертве рвут кокон (жертва не получает урон), камера жертвы,
   урон 60% и добивание, если он смертелен.
8. Фаза 3: ореол, кража каждые 20 с, плеть с предупреждением.
9. «Марионетка»: игрок реально идёт к ней (сервер шлёт скорость каждый тик — возможны рывки на пинге), сброс уроном.
10. «Узлы»: видны ли на земле (`duration` = 20 с у fx с −1), опутывание, прыжок гасится.
11. Иконки шести статусов и их названия.
12. Реплика по ней: печати рвутся, фраза; звук `irina.replica_break`.
13. Огненные заклинания по ней проходят, лава/огонь-блок — нет.

## 5. Не проверено / решения на проверку
- В игре ничего не смотрел: камеры, позы, fx, баланс — только по таблицам.
- `fireImmune()` у неё `false` (каркас ставит всем боссам `fireImmune` → Iron's огонь по ней не проходил бы, а по балансу у неё
  слабость к огню). Горящей её видно (визуально «нити горят»), урон огня мира не проходит.
- Затемнения в конце камеры добивания (2.2 с) нет — у `BossCam.Shot` нет такого параметра.
- Жертва «Только мой» и марионетка держатся сервером (телепорт/скорость каждый тик) — на большом пинге возможна дрожь.
- Деление урона пар — по `LivingDamageEvent` (после брони), половина партнёру сквозь броню. Тотем у партнёра сработает как обычно.
- Состояние боя (метка, пары, узлы) не сохраняется в NBT: при выгрузке чанка посреди боя они сбрасываются (фаза и особые — сохраняются
  каркасом).
- `[bosses_common]`-правила, которых нет в каркасе (контроль, перемещение, phase_clamp, обход), — как у Главы, не сделаны.
