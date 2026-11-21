# T32 — боссы и Epic Fight: сделано (программист, 21.11)

Спека: `docs/specs/tasks/T32_bosses_epicfight_compat.md`. Сборка `./gradlew build --offline` и все тесты зелёные (новый `BossGuardBreakMathTest`, 8 тестов).
Epic Fight остаётся мягкой зависимостью: весь код с классами EF — во вложенном `Impl` класса `boss/BossEpicFight.java`, вызывается только при `ModList.isLoaded("epicfight")`. Без EF «Сломать блок» никогда не запускается, остальное работает как раньше.

## Что сделано

| Пункт | Как |
|---|---|
| 1. Антистан | `EntityStunEvent` (EF шлёт его в своём `LivingHurtEvent` перед `HurtableEntityPatch#applyStun`) отменяется для любого `PohBoss`, ключ `ef_stun_immune`. Вместе со станом пропадают knockback и impact этого удара (они внутри той же ветки). Анимацию босса ничто не прерывает. Урон проходит как обычно |
| 1а. BossGuard против EF | EF умножает урон **после** нашего фильтра (множители анимаций, навыки оружия), а «казнь» (`epicfight:execution`) ставит 2^31, если у цели нет `LivingEntityPatch`. Теперь в самом позднем `LivingHurtEvent` для удара `EpicFightDamageSource` по боссу срез большого удара, phase clamp и пол финала применяются заново к «удару до нашего среза × множитель EF» (`BossGuard.afterExternal`). Казнь = обычный удар |
| 2. Блок | Блок EF (`GuardSkill`) срабатывает на любой урон с атакующим и позицией, патч EF боссу **не нужен**. Обычные удары (`boss_attack`, ванильный ближний бой Главы) блокируются по правилам EF. `boss_mechanic` и новый `boss_guard_break` лежат в теге `data/epicfight/tags/damage_type/unblockable.json`, их не блокировать |
| 3. Парирование | `ParryingSkill`: урон 0 (событие отменено). Атакующий реагирует только через `LivingEntityPatch#onAttackBlocked`, а у боссов нет `LivingEntityPatch` (у них максимум `GlobalMobPatch` от правила `global_stun`, это `HurtableEntityPatch`), поэтому отдачи нет. Если `ef_parry_no_recoil = false`, босс запинается на 0.8 с (`BossGuardBreak.PARRY_STAGGER`) |
| 4. «Сломать блок» | Каркас `boss/BossGuardBreak.java` (общий для всех), подробности ниже |
| 5. Конфиг | `[bosses_common]`: `ef_stun_immune`, `ef_parry_no_recoil`, `guard_break_hold_seconds`, `guard_break_blocks`, `guard_break_cooldown`, `guard_break_warn_ticks`, `guard_break_stun_ticks`, значения по спеке |

### «Сломать блок» в каркасе
- **Детект.** Каждый тик босс смотрит на бойцов в радиусе: держит ли игрок guard EF (`PlayerPatch#getHoldingSkill() instanceof GuardSkill`). Удар запускается, если guard держится ≥ `guard_break_hold_seconds` **или** заблокировано `guard_break_blocks` ударов боссов подряд. Цепочка блоков рвётся, если удар босса прошёл, и забывается после 8 с без блоков. Блоки считает наш слушатель EF `TAKE_DAMAGE_EVENT_ATTACK` с приоритетом −1 (он идёт после навыков guard): `isCanceled()` + `getResult() == BLOCKED` / `isParried()`. Состояние guard у игрока одно на всех боссов. Цель должна быть в пределах 4 блоков и не выше 3 блоков по высоте. Сначала проверяется своя цель, потом ближайший.
- **Когда нельзя.** КД `guard_break_cooldown` (свой у каждого босса). Не запускается: в сценах и финале, во время своей атаки или каста (хук `guardBreakFree`), когда AI выключен, в окнах контроля (паралич, сон, «истощение», корни Iron's / езда, «Целевая поза»), когда босс скрыт (`LOOK_HIDDEN`). По цели на «столбе» не бьёт (как в `BossGuard`).
- **Ход.** На тике 0 `core.lock(длина)` (AI выкл., урон по нему проходит), разворот к цели, анимация босса и `Fx.play(<id>_guard_break, caster = босс)` (только если такой fx есть). За `guard_break_warn_ticks` до удара общий «треск» `pohsmp_core:boss.guard_break` (sounds.json, пока ванильный `random/anvil_land`, pitch 1.7; помощник может заменить) и разворот к цели ещё раз. Пока fx босса нет, вместо вспышки на оружии летят искры (`ELECTRIC_SPARK` + `FLASH`).
- **Удар.** Бьёт всех бойцов в дуге 150° перед боссом, до 4.5 блока. Урон = самый сильный ближний удар босса в текущей фазе (хук `guardBreakDamage`), тип `pohsmp_core:boss_guard_break` (как `boss_attack`, но в `epicfight:unblockable`, поэтому не блокируется и не парируется; от переката EF увернуться можно). Если цель была в блоке и урон прошёл: выносливость EF = 0 (`setStamina(0)`), поза guard break EF (`applyStun(NEUTRALIZE)`, `Animations.BIPED_COMMON_NEUTRALIZED`), звук EF `NEUTRALIZE_MOBS` + `SHIELD_BREAK`, и наш `paralysis` на `guard_break_stun_ticks` (24 = 1.2 с: стоит и не бьёт).

### Урон по боссам (хук `guardBreakDamage`)
| Босс | Самый сильный ближний удар |
|---|---|
| Глава Культа | `attack_damage` (база + коса, ярость ф.3 и enrage уже в атрибуте); его ближний бой — ИИ Тироса |
| Ирина | `attack_damage` (удар посохом) |
| Арис | удар молотом `attack_damage` × `mythic_damage_mult` в ф.3 |
| Мартин | max(swing = `attack_damage`+`sword_damage`, `overhead_damage`, `thrust_damage`, в ф.3 ещё `shield_dash_damage`) × p3 × enrage |
| Эреб | укол рапирой (`attack_damage`) |
| Длань Лжи | max(рапира, `slam_damage` призрачной руки) |

### Анимации (TEMP_GUARD_BREAK)
Имя анимации взял по правилу файла каждого босса, как с `replica_break`: `cult_leader_guard_break`, `irina_guard_break`, `martin_guard_break`, `ereb_guard_break`, `ereb_hand_guard_break`, у Арис `animation.aris.guard_break` (добавлена в `ArisMath.ANIMS`, длина 28, пока в `PENDING`). Если помощник назовёт по‑другому, это одна строка (`guardBreakAnimation`). fx: `<id>_guard_break`, тик 0 fx = тик 0 анимации.
Тайминги временные, `BossGuardBreak.Timing.TEMP` (помечено `TEMP_GUARD_BREAK`): предупреждение 12 тиков, удар на 14‑м, длина 28. Когда придёт `docs/inbox/2026-11-21_mgr_guard_break_visuals.md`, у каждого босса будет своё `guardBreakTiming()` (и длина у Арис в `ANIM_TICKS`, `PENDING` очищу).
Эреб при «Сломать блок» сбрасывает маскировку, как при любой своей атаке.

## API Epic Fight 20.14.17 (что использовано)
- `yesman.epicfight.api.forgeevent.EntityStunEvent` (@Cancelable): `getStunnedEntityPatch()`, `getStunType()`.
- `world.capabilities.EpicFightCapabilities#getEntityPatch(entity, ServerPlayerPatch.class)`.
- `PlayerPatch#getHoldingSkill()` (HoldableSkill), `#isEpicFightMode()`, `#setStamina(float)`, `#getEventListener()`.
- `LivingEntityPatch#applyStun(StunType.NEUTRALIZE, t)`, `HurtableEntityPatch#playSound(...)`, `gameasset.EpicFightSounds.NEUTRALIZE_MOBS`.
- `skill.guard.GuardSkill` / `ParryingSkill` (`isBlockableSource`: теги `epicfight:unblockable`, `bypasses_invulnerability`, `is_projectile` и др.; GUARD_PUNCTURE только у `EpicFightDamageSource`).
- `world.entity.eventlistener.PlayerEventListener.EventType.TAKE_DAMAGE_EVENT_ATTACK`, `TakeDamageEvent.Attack#isParried/getResult`, `api.utils.AttackResult.ResultType.BLOCKED`. Слушатели идут по убыванию приоритета, −1 выполняется и после отмены.
- `world.damagesource.EpicFightDamageSource` (для повторного среза в `LivingHurtEvent`).
- Патч EF боссам не нужен: `EntityPatchProvider` даёт неизвестным мобам максимум `GlobalMobPatch` (при `global_stun`). Блок и парирование целиком на стороне `ServerPlayerPatch`.

## Что проверить в игре (с EF, под POH SMP TEST)
1. Ударить каждого босса оружием EF, включая тяжёлые навыки (Evisceration, Sweeping Edge, Grasping Spire): нет стана, отброса, падения, его атака/каст не сбиваются. Урон по полоске примерно как без EF, крупные удары режутся.
2. `/gamerule global_stun true` и `false`: в обоих случаях п.1 выполняется.
3. Блок EF (ПКМ мечом): удары рукой/оружием блокируются, тратится выносливость, при нехватке EF ломает блок сам. Волны, стены огня, круги, осколки (`boss_mechanic`) проходят сквозь блок.
4. Парирование (навык Parrying): урон 0, звук и искры EF, босс без отдачи, атака/серия продолжается.
5. Держать блок перед боссом больше 1.5 с: искры/вспышка + треск, через 0.6 с удар. Выносливость 0, поза guard break EF, ~1.2 с без движения, урон полный. Повтор не раньше чем через 12 с.
6. Отпускать блок между ударами и заблокировать 3 удара подряд: тоже «Сломать блок».
7. Не в блоке под ударом: просто тяжёлый удар (Мартин ф.1 = 48, ф.3 больше). Перекат EF в момент удара спасает.
8. Во время сцены, финала, каста босса, под параличом/корнями, со «столба» «Сломать блок» не запускается.
9. Без EF в модах всё как раньше, в логе нет ошибок загрузки классов EF.

Код: `boss/BossGuardBreak.java`, `boss/BossGuardBreakMath.java`, `boss/BossEpicFight.java`, хуки в `PohBoss`, переопределения в `*Entity`/`*Fight` шести боссов, `BossGuard.afterExternal`, данные (`damage_type/boss_guard_break.json`, `data/epicfight/tags/damage_type/unblockable.json`, `sounds.json`, lang `ui.pohsmp_core.boss.guard_break` = «Сломать блок» / «Guard Break»).

## Дополнение 21.11: тайминги по письму визуала (`2026-11-21_mgr_guard_break_visuals.md`)
- `guardBreakTiming()`: по умолчанию `Timing.STANDARD` = удар на тике 14, длина 36 (Ирина, Арис, Эреб, Длань). У Мартина (14, 40). Предупреждение на тике 2 (= 14 − `guard_break_warn_ticks`). Длины сверены с `animation_length` в файлах (1.8 / 2.0 с).
- `TEMP_GUARD_BREAK` снят у пяти боссов. Остался только у Главы Культа (`CultLeaderEntity.guardBreakTiming` = 14 / 28) до его анимации; план 14 / 36.
- fx `<id>_guard_break` теперь получает `target` = цель (треск блока на тике 14 у цели, а не у босса).
- Арис: `ArisMath.PENDING` очищен, `ANIM_TICKS` guard_break = 36 (сделал визуал), `ArisMathTest` сверяет с файлом.
- Сборка `--offline` и все тесты зелёные.
