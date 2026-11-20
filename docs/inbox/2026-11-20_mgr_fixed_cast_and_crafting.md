# Управляющий → Кодингу (20.11): фиксированный каст у роликовых + что крафтится

Делать, когда владелец будет за ПК (он сам скажет). Ничего не менять без него.

## 1. Решение владельца: вся магия с камерой — фиксированной длительности
«Вся магия с камерой должна быть фиксированной по длительности». Сейчас характеристика Iron's «Сокращение времени каста»
(cast_time_reduction) укорачивает каст роликовых заклинаний (PohSpell.getEffectiveCastTime → super), а ролик камеры идёт по
константе CAST — заклинание срабатывает раньше конца ролика, всё разъезжается.
Сделать: у всех заклинаний, которые зовут `Cutscene.start`, `getEffectiveCastTime` = фиксированное время (как уже у SilentGate,
CovenArrival, Disintegration). Список по коду: DownfallSpell, MilkyWaySpell, SoulDevourSpell, TabooSpell, SpaceClosureSpell,
StarFallSpell, RiteSpell (Печать души, Благословение), ButterflyDreamSpell, ErasedNameSpell, NoAwakeningSpell, MythicT23 (Древо мира,
Око бездны, Последний рассвет). Удобно — флаг `fixedCast()` в PohSpell (по умолчанию false) и override true в этих классах;
`CastAnims.hideHands(…, getEffectiveCastTime…)` тогда сам станет верным.
Перезарядку (cooldown_reduction) — НЕ трогать, владелец не решал.

## 2. Вопрос владельца «может ли игрок скрафтить Высшие, Мифические, Божественные, Запретные…» — факт по коду
`allowCrafting()` (свиток в Scroll Forge Iron's, вписывание в книгу) по умолчанию **true**. Запрещён (`false`) у: Explosion, HeavenFall,
FrozenHour, SpaceClosure, CovenArrival, Downfall, Madness, Ark, Taboo, SoulDevour, RiteSpell (Печать души, Благословение), ErasedName,
MythicT23; IllusionBase — только обычные; безмолвные — без посоха, кроме Врат.
**Можно скрафтить сейчас** (нет запрета) — в т.ч. ВСЕ Высшие на HigherSpell: Ascension, Ashless, BloodMoon, Countdown, Cradle,
DisintegrationReplica, EternalBlizzard, FateStar, MilkyWay, MirrorPrison, OblivionBlades, ScarletCut, Seal, Singularity, StarFall,
WorldRift; плюс школы «Кошмары» (NightmareSpells — проверить) и обычные заклинания мода. Решение владельца по крафту — ждёт.
