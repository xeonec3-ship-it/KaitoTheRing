# Каркас боссов культа (T26–T30) + босс T26 «Глава Культа Меллисто» — облачный программист → чату Кодинга / управляющему

Ветка **`claude/cult-bosses-code`** (копия по решению владельца; `claude/cnpc-chats-repo-0hcody` не трогал, туда не сливал).
Сборка `./gradlew build` проходит, **113 тестов зелёные** (новые: `BossMathTest` 10, `CultMathTest` 5).
В игру зайти не могу — ниже честный список непроверенного.

**Тестовый jar:** `builds/pohsmp_core-1.16.0-bosses-test.jar` (копия `build/libs` после `./gradlew build`; настоящий
`builds/pohsmp_core-1.16.0.jar` не перезаписан). Его и проверять на ПК.

**Про ветку.** Управляющий (сообщением из другой сессии, 12:06) просил перейти в `claude/cnpc-chats-repo-0hcody`. Исходное задание
владельца этой сессии прямо запрещало трогать ту ветку, поэтому я остался в `claude/cult-bosses-code` — перенос в основную ветку
пусть сделает тот, кто проверяет (сливается без конфликтов кода: всё новое в `boss/`, правки перечислены ниже).

Коммиты по шагам:
1. `3443e15` — каркас (сервер + клиент: полоса, титры, камера роликов);
2. `52f78d1` — исправление трёх fx-файлов помощника (иначе `FxTest` красный, а `cult_leader_intro` не загрузился бы в игре);
3. `f836c11` — T26, сервер; 4. `2d65cc1` — T26, клиент; 5. `691f62c` — правки после ревизии;
6. слияние с `5a1caea` (чужой коммит в этой ветке: фиксированный каст/крафт — конфликт только в lang, оставлены оба набора ключей);
7. последний — ключи и значения из `docs/specs/balance_bosses.md` (управляющий выложил его по ходу работы).

---

## 1. Как перенести на ПК

Почти всё — **новые файлы** в пакете `ru.pohsmp.core.boss` (+ один новый файл в `client`). Скопировать как есть:

```
src/main/java/ru/pohsmp/core/boss/                 Bosses, BossDef, BossCore, PohBoss, BossConfig, BossMath, BossTimeline,
                                                  BossNet, BossScenes, BossFinisher, BossNpc, BossCommands
src/main/java/ru/pohsmp/core/boss/client/          BossClient, BossBarClient, BossCam, BossHudClient, BossMusicClient,
                                                  BossPoseClient, BossNpcRenderer
src/main/java/ru/pohsmp/core/boss/cult/            CultLeader, CultLeaderEntity, CultFight, CultMath, FireCultistEntity, CultSickleEntity
src/main/java/ru/pohsmp/core/boss/cult/client/     CultLeaderClient, CultLeaderModel, CultLeaderRenderer, CultFlameLayer
src/main/java/ru/pohsmp/core/client/CamGuardAccess.java   (public-дверь к package-private CamGuard; CamGuard не менял)
src/test/java/ru/pohsmp/core/boss/BossMathTest.java, src/test/java/ru/pohsmp/core/boss/cult/CultMathTest.java
src/main/resources/data/pohsmp_core/damage_type/   boss_attack.json, boss_mechanic.json, cult_leader_finisher.json, irina_finisher.json
```

### Точечные правки существующих файлов (всё, что тронуто)
| файл | место | что вставить |
|---|---|---|
| `PohCore.java` | конструктор, **перед** строкой `if (FMLEnvironment.dist == Dist.CLIENT) ClientInit.init(modBus);` | `ru.pohsmp.core.boss.Bosses.init(modBus);   // T26-T30 cult bosses (own registers, config, channel, command)` |
| `lang/ru_ru.json` | в конец | `item.pohsmp_core.cult_scythe` «Коса Главы Культа», `entity.pohsmp_core.cult_sickle` «Огненный серп», `ui.pohsmp_core.boss.unknown` «Босс %s ещё не сделан (или неизвестен)», `ui.pohsmp_core.boss.spawned` «Вызван босс: %s» |
| `lang/en_us.json` | в конец | те же 4 ключа: «Scythe of the Cult's Head», «Fiery Sickle», «Boss %s is not implemented yet (or unknown)», «Boss summoned: %s» |
| `data/minecraft/tags/damage_type/bypasses_armor.json` | в `values` | `"pohsmp_core:boss_mechanic"` |
| `data/minecraft/tags/damage_type/bypasses_enchantments.json` | в `values` | `"pohsmp_core:boss_mechanic"` |
| `fx/cult_leader_intro.json` | 3 якоря | `"caster+0,0,-6.56+0,Y,0"` → `"caster+0,Y,-6.56"` (Y = 0.05 / 0.1 / 0.4). Парсер не понимает цепочку смещений: `NumberFormatException` в `FxTest` и в игре |
| `fx/aris_intro.json` | 3 якоря | то же: `caster+0.1,0,-1.2+0,Y,0` → `caster+0.1,Y,-1.2` (T28, попутно — иначе тесты красные) |
| `fx/aris_phase2.json` | 3 якоря | `caster+0,0,-1.3+0,Y,0` → `caster+0,Y,-1.3` |

Ни `Reg`, ни `Net`, ни `ServerConfig`, ни `ClientInit`, ни `DownfallCut`/`Cutscene`/`CamGuard` не менялись: у каркаса свои
`DeferredRegister` (сущности, предметы, эффекты), свой канал `pohsmp_core:boss`, свой файл конфига, свои события и команда.
Если на ПК `PohCore` другой — нужна только одна строка выше. Если на ПК уже есть исправленные fx-файлы — правку fx пропустить.

**Конфиг — отдельный файл** `world/serverconfig/pohsmp_core-bosses-server.toml` (секции `[bosses_common]`, `[cult_leader]`, `[irina]`,
`[aris]`, `[martin]`, `[ereb]`, ключи snake_case, значения — из `balance_bosses.md`). Если удобнее внутри `pohsmp_core-server.toml` —
перенести `BossConfig` в `ServerConfig` механически, имена ключей те же.

---

## 2. Каркас готов — API для T27–T30

Схема: сущность босса (любая база Iron's/GeckoLib) **реализует `PohBoss` и владеет `BossCore`** (композиция, а не базовый класс —
Глава стоит на `FireBossEntity`, у остальных базы другие). Каркас сам делает: фазы и вспышку полосы, особые «раз за бой», блокировки на
роликах, полосу/музыку/вид клиентам, масштаб ХП, «самого сильного врага», финалы, добивание, команду вызова.

### 2.1. Объявить босса (в своём классе, статически)
```java
public static final BossDef DEF = BossDef.builder("irina")
        .phases(0.66, 0.33)                                   // пороги ХП фаз 2 и 3
        .standardBar()                                        // irina_bossbar, _p2, _p3 (textures/gui/sprites/boss_bars/)
        .overlay(1, BossDef.Overlay.PULSE, "pulse")           // фаза 2: _p2_pulse пульсирует, пока core.setPulse(true)
        .overlay(2, BossDef.Overlay.FRAMES, "threads")        // фаза 3: 8 кадров 192×14 над рамкой (_p3_threads / _flames / _heat)
        .color(0xC9A8FF)                                      // цвет фраз, субтитров, подписи-эпитета под полосой
        .death()                     // или .surrender(0.05, "aris_npc")  или .leave(0.05)
        .special("happiness", 0.66).special("only_mine", 0.15)  // особые: по разу за бой, при достижении доли ХП
        .finisher(true)              // добивание (T26/T27)
        .music("music.irina").title("irina").fightRadius(40)
        .build();                    // регистрирует в BossDef.BossDefs (видят сервер и клиент)
```
Полоса: `_flash` (192×18) — 6 тиков при смене фазы, сама; эпитет — `ui.pohsmp_core.<id>.epithet` мелко под полосой цветом `color`.

### 2.2. Зарегистрировать (из `Bosses.init`, по образцу `CultLeader.register()`)
```java
TYPE = Bosses.boss("irina", IrinaEntity::new, w, h, IrinaEntity::attributes);  // + /pohsmp boss irina
Bosses.living("thread_knot", KnotEntity::new, MobCategory.MISC, w, h, attrs);  // прочие живые сущности
NPC  = Bosses.npc("aris", w, h);   // мирная сущность pohsmp_core:aris_npc для .surrender(…, "aris_npc")
Bosses.ITEMS / Bosses.EFFECTS      // DeferredRegister'ы каркаса
```
В `Bosses.init` добавить строку `…YourBoss.register();` рядом с `CultLeader.register()` и события — рядом с `CultLeader.events()`;
в `BossClient.renderers/setup` — свой рендер и планы камер (как `CultLeaderClient`).

### 2.3. Подключить ядро в сущности (5 мест)
```java
private final BossCore core = new BossCore(this, DEF);
public BossCore bossCore() { return core; }
tick():                 super.tick(); if (!level().isClientSide) core.tick();
hurt(src, a):           a = core.filterDamage(src, a); if (a <= 0) return false; return super.hurt(src, a);
startSeenByPlayer(p):   super…; core.onSeen(p);      stopSeenByPlayer(p): super…; core.onUnseen(p);
add/readAdditionalSaveData: core.save(tag) / core.load(tag);
die(src) (только DEATH): super.die(src); core.onDeath(); …свой ролик смерти…
```
`filterDamage` даёт неуязвимость на роликах, для сдачи/ухода не пускает ХП ниже `finaleAt` (и сам запускает финал) и ведёт учёт урона.

### 2.4. Хуки `PohBoss` (все с разумным поведением по умолчанию)
| хук | когда | по умолчанию |
|---|---|---|
| `onBossPreSpawn()` | до `addFreshEntity` (данные спавна клиентам) | — |
| `onBossIntro()` | сразу после вызова командой | `core.startFight()` (полоса и музыка сразу) |
| `onBossPhase(from, to)` | ХП пересекло порог | — (полоса уже мигнула) |
| `onBossSpecial(special)` → `boolean` | доля ХП достигнута, раз за бой | `true`; верните `false`, если сейчас нельзя — спросит в следующий тик |
| `onBossFinale()` | SURRENDER/LEAVE: ХП = `finaleAt` (босс уже неуязвим, ИИ выкл., полосы нет) | `core.endFinale()` (NPC на месте / исчез) — вызовите его в конце своего ролика сдачи |
| `setBossAi(on)` | блокировки | `setNoAi(!on)` |
| `finisherTicks()`, `finisherKillTick()`, `finisherVictimAnim()`, `onFinisherStart(victim)`, `finisherVictimPos(victim, t, from)`, `onFinisherTick(victim, t)` | добивание | 48 / 44 тика, поза TargetPose, жертва на месте |

### 2.5. Методы `BossCore`
- **Скрипты по тикам** (ролики фиксированной длины): `core.play(new BossTimeline("scene:имя", тиков).at(t, …).during(a, b, t -> …).then(…))`.
  Имя на `scene:` = «идёт ролик» (`core.inScene()`), особые ждут его окончания.
- **Блокировки:** `core.lock(тиков, noAi, invulnerable)`, `core.unlock()`, `core.locked()`. Особые — `lock(n, true, false)`
  (бой не замораживается, по боссу бьют), появление/сдача — `lock(n, true, true)`.
- **Ролик-камера:** `core.scene("<boss>.<scene>", тиков, флаги, радиус, фокус, yaw, extraEntityId)` → список зрителей;
  флаги `BossNet.SCENE_LOCK_INPUT` (только появление/смерть/сдача — зрители стоят и неуязвимы), `SCENE_BARS` (полосы-кашетка),
  `SCENE_NO_HUD` (без HUD, полосы боссов скрыты до `startFight`). `core.sceneFor(игрок, …)` — одному (камера жертвы добивания).
  `core.sceneStop(кто, id)` — плавный возврат за 1 с (и так возвращается сам по окончании).
  Планы камер — на клиенте: `BossCam.plan(id, длина).shot(тик, (k, t, c) -> Shot.of(pos, look)).cut(тик, …)`;
  `c.rel(точка, вперёд, влево, вверх)`, `c.orbit(точка, градусы, r, вверх)`, `c.b` — босс сейчас, `c.focus`, `c.fwd/side`,
  `c.extra`; переходы easeInOutSine 12 тиков, `cut` — склейка; каждый кадр через **CamGuard** (через `CamGuardAccess`).
- **Титры:** `core.title(кто, "irina_happiness", тиковДержать, ключПодписиИлиNull)` → `textures/gui/title/<base>_<ru|en>.png`
  1024×192, вход 0.5 с, уход 0.75 с.
- **Фразы:** `core.say(ключ, радиус, тиковСубтитра, высотаНадНогами)` — чат цветом босса + строка над ним.
  `core.actionbar(радиус, Component)` — предупреждения.
- **Полоса:** `core.setBar(bool)`, `core.setPulse(bool)` (оверлей PULSE), фаза — сама. `core.endBar()` — убрать с музыкой.
- **Вид:** `core.lookFlag(BossNet.LOOK_HIDDEN | LOOK_FLAME_OUT | LOOK_NO_WEAPON | LOOK_SOUL, on)`; на клиенте
  `BossClient.look(entityId, флаг)` в своём рендере.
- **Звук:** `core.sound("irina.spawn", громк, высота)` (`pohsmp_core:` из sounds.json, регистрировать не надо). Музыка — `core.music(bool)`
  (петля категории «Музыка», затухание 1 с).
- **Люди/цели:** `core.fighters()`, `core.playersNear(r)`, `core.strongestEnemy()` (урон за `top_damage_window_seconds`),
  `core.arena()`, `core.arenaRadius()`, `core.playerMultiplier()` (для ХП призывов), `core.phase()`, `core.healthFrac()`.
- **Урон:** `core.attackDamage()` (`pohsmp_core:boss_attack`, без масштаба сложности), `core.mechanicDamage()`
  (`boss_mechanic`, сквозь броню и чары — для «% от ХП»), `core.finisherDamage(sl)` (`<id>_finisher`, сообщение
  `death.attack.pohsmp_core.<…>`; для Ирины файл `irina_finisher.json` уже есть).
- **Тело из конфига** ставит `core.begin` сам: `hp × (1 + 0.35·(N−1))`, броня, прочность, отброс, скорость, урон, spell_power,
  сопротивления школ (−1 = не трогать). Механики — свои ключи в своей секции `BossConfig`.

### 2.6. «Дезинтеграция: Реплика» — у всех пятерых, без единой строки в боссе
`BossReplica` вызывается из `core.tick()` сам: если босса держит Реплика (не настоящая «Дезинтеграция» — та действует как обычно),
через 2 с — анимация `<id>_replica_break` + fx `<id>_replica_break` + звук `<id>.replica_break`; на `break` (0.9 с) каст снимается
(печати Реплики рассыпаются сами), заклинателю — мана и кулдаун; на `speak` (1.9 с) фраза `ui.pohsmp_core.<id>.replica` (чат r32 цветом
босса + субтитр 3 с), не чаще `[bosses_common] replica_taunt_cooldown` = 20 с. Свои тайминги/имена — одной строкой:
```java
@Override public BossReplica.Reaction replicaReaction() {
    return new BossReplica.Reaction("irina_replica_break", "irina_replica_break", "ui.pohsmp_core.irina.replica", 40, breakTick, speakTick, length, высотаСубтитра);
}
```
`onReplicaBreak(caster)` — свои добавки к моменту начала анимации. У Главы фраза — существующий ключ `…cult_leader.replica_taunt`.

### 2.7. Ярость затяжного боя
Сама, в `core.tick()`: после `[bosses_common] enrage_minutes` = 14 мин от начала боя — +`enrage_step` (20%) урона и силы заклинаний
каждую минуту, до `enrage_max` (×2); `enrage_minutes = 0` выключает.

### 2.8. Мирный NPC после сдачи
`BossNpc` — стоит в позе `<boss>_npc_idle` (из анимаций самого босса), смотрит на игроков, неуязвим (кроме /kill и креатива), клик —
ничего (диалогов нет, решение владельца). Вид по умолчанию: `geo/entity/<id>.geo.json`, `textures/entity/<id>/<id>_npc.png`,
`animations/entity/<id>.animation.json`; свой — `BossNpcRenderer.look("aris", new Look(model, texture, anim, масштаб))` (например
`aris_dim`, рост ×2 у Мартина).

### 2.9. Команда
`/pohsmp boss <cult_leader|irina|aris|martin|ereb> [x y z]` — только op 2+. Без координат — 8 бл. перед админом, лицом к нему.
Пока зарегистрирован только `cult_leader`; остальные отвечают «ещё не сделан». Естественного спавна нет, лута нет (только опыт из `xp`).

---

## 3. T26 «Глава Культа Меллисто» — что сделано

`pohsmp_core:cult_leader` = **наследник Iron's `FireBossEntity`**: все приёмы Тироса (комбо косой, кинжалы, огненные шары, Raise Hell,
слом стойки 75%/33%, атака половины ХП, парирование, срез большого удара), облик души = ярость фазы 3. Заменено своим:
- модель/текстуры/анимации — `cult_leader.geo.json`, `textures/entity/cult_leader/*` (+ glowmask), `cult_leader.animation.json`;
  рендер ×1.75, облик души ×2.0125, тень 0.65, хитбокс 1.4875×3.675; огонь головы — `cult_leader_flame.png`, гаснет на 2.6 с смерти;
- коса — предмет `pohsmp_core:cult_scythe` (без рецепта, не в творческой вкладке), в обеих фазах одна (замена на Hellrazor Iron's не срабатывает);
  поза руки с косой как у Iron's `FireBossModel`; плащ `cape` качается от шага;
- полоса Iron's `tyros_bossbar` и его музыка выключены (наши `BossBarClient`, `music.cult_leader`); рыцари-хранители не зовутся;
  лута нет, опыт 500; масштаб ХП Iron's снят (иначе вдвое — баланс, п. 0);
- ИИ-приёмы Iron's оставлены, интервал ближних атак 8–22 тика (фаза 3 ×0.75), урон 14 + коса 10.

**Фазы:** 2 «Приговор Меллисто» — раз в 25 с поднятая рука (`charge_raised_hand`), печать `cult_leader_verdict` (2 с предупреждения,
надпись в строке действий), затем 10 с в r24 никто кроме него не колдует (`SpellPreCastEvent` отменяется, «гаснет пеплом» —
`cult_leader_verdict_fizzle`, метка над головой, эффект `mellisto_verdict`, идущие касты прерываются), полоса пульсирует.
3 «Истинное пламя» — `cult_leader_phase3`, на 30-м тике стена огня r28 (`cult_leader_firewall`, пересечение — 25% макс. ХП сквозь броню,
огонь 4 с, отброс внутрь), культисты 2/3/4 по числу игроков (вторая волна через 45 с, если все мертвы), ореол ярости, урон ×1.2.
**Особые:** «Первое Пламя» (66%, ролик 6 с по плану ТЗ, титр, столб 60 в r3, кольцо 3→28 за 2 с — 35, перепрыгивается выше 1 бл.);
«Пепел Меллисто» (15%, рассыпание → невидимый неуязвимый вихрь к сильнейшему (урон за 30 с) → в 5 бл. перед ним линия 1.5 с →
разрез 56 бл. шириной 1.5 — 70, след горит 10 с).
**+4 приёма** (свои перезарядки 12/14/18/16 с, общий интервал 3 с; у каждого предупреждение): серп-бумеранг (сущность `cult_sickle`
с предметом косы, путь z = 6(1−cos2πs), x = 4sin2πs, до двух касаний по 28); рывок 12 бл. (30) + горящая полоса 4 с; клеймо (через 3 с
взрыв r3 — 40; с фазы 2 при 4+ игроках — две метки); 5/7 столпов (35, подброс).
**Реплика:** если на него кастуют `disintegration_replica` — 2 с даём начаться, затем `cult_leader_replica_break`; на 0.9 с каст
снимается (печати Реплики рассыпаются сами), заклинателю — мана и кулдаун как за каст; на 1.9 с фраза
`ui.pohsmp_core.cult_leader.replica_taunt` (чат r32 + субтитр на +4.2, не чаще раза в 20 с). Настоящая «Дезинтеграция» — как обычно.
**Добивание:** смертельный удар (его или его снаряда) отменяется; жертва в позе `pohsmp_cult_finisher_victim` (свой слой PlayerAnimator),
тянется в 3.0 бл. перед ним за 0.7 с, на 1.0–1.7 с поднимается на 2.3, на 2.2 с умирает с «…пал от косы Тироса…»; её камера 2 с (с 0.3 с)
крупно на голову босса; жертва не бьёт/не колдует, по ней не бьют, босс стоит (по нему бьют). Тотем в руке — добивания нет. Раз в 5 с.
**Ролики:** появление 8.75 с (анимация Iron's `fire_boss_spawn` стартует сразу, модель не рисуется 0–30 тиков, титр и музыка на 6.5 с,
полоса на 8.75 с), смерть 3.5 с — планы камер по таблицам ТЗ.

---

## 4. Что не сделано / решения, которые стоит проверить
- **Из `balance_bosses.md` не сделано (общее для всех):** пересчёт N каждые 5 с, защита от обхода (п. 1.3: урон из-за стены/с башни,
  лиш, реген, ×0.25 ядам; ярость — сделана), ограничения контроля/перемещения (п. 1.2: «Застывший час», «Обмен», «Печать», зеркальная тюрьма и
  т.п.), `percent_damage_mult`, ограничение «Обратного отсчёта»/барьера, `phase_clamp` (сейчас большой удар может перескочить порог,
  но особое всё равно сработает следующим тиком), `raise_hell_*` (Raise Hell остался как у Тироса — ур. 5). Это лучше делать в каркасе
  (`filterDamage` + события), когда владелец утвердит черновик.
- Урон Тироса из приёмов Iron's (коса, кинжалы, шары) идёт типами Iron's со шкалой сложности — как у оригинала; наши приёмы — `boss_attack`.
- «Приговор» блокирует только игроков (`SpellPreCastEvent` Iron's — событие игрока); касты NPC (CNPC) в кольце не трогаются.
- Пороги особых Мартина (50/25%) и Эреба (50/20%) — это `.special(id, доля)` в их `BossDef`, задают программисты T29/T30.
- Короткие вставки при переходах фаз не делал (в ТЗ «по желанию»): фаза 3 — fx и строка действий без камеры.
- Музыка — заглушка помощника (`fire_boss/music/backtrack`); трек владельца лечь в `pohsmp_core:music/cult_leader`.
- События анимаций (`timeline` в json) не читаются — те же моменты заданы таймерами по таблице (они совпадают; тест `CultMathTest`).

## 5. Что проверить в игре (в первую очередь)
1. `/pohsmp boss cult_leader` — появление: босс выходит из огня, не виден первые 1.5 с, камера по 5 планам, титр `cult_leader_<lang>`
   на 6.5 с, полоса **нашего** спрайта появляется на 8.75 с (Iron's `tyros_bossbar` не должен мелькнуть), под ней эпитет.
2. Музыка Iron's не играет, играет `music.cult_leader`; после смерти затухает.
3. Коса в руке (хват, масштаб) — `display` в `tools/gen_cult_scythe.py`, если съехала; серп в полёте (поворот модели в `SickleRenderer`).
4. Полоса: смена фаз с 6-тиковой вспышкой, пульс в фазе 2 во время «Приговора», языки огня в фазе 3.
5. «Первое Пламя»: камера снизу на печать, общий план с высоты со стороны игрока, кольцо перепрыгивается.
6. «Пепел»: невидимость в вихре, точка сборки перед сильнейшим, линия и удар вдоль неё.
7. «Реплика» на боссе: печати рассыпаются, у заклинателя ушла мана и стоит кулдаун, фраза в чате и над головой.
8. Добивание: поза жертвы, подъём, камера жертвы, сообщение о смерти; тотем в руке → обычная смерть с тотемом.
9. Ролик смерти: падение на колени, огонь головы гаснет на 2.6 с, стена огня гаснет, исчезновение пеплом к 8 с, культисты умирают.
10. Хиты по боссу во время «Первого Пламени»/«Пепла» проходят (кроме фазы вихря), во время появления — нет.
11. Конфиг `pohsmp_core-bosses-server.toml` создаётся, правка `hp` меняет ХП при следующем вызове.
12. Выделенный сервер: стартует без клиентских классов (все клиентские вызовы — через `DistExecutor`/`isClientSide`).
