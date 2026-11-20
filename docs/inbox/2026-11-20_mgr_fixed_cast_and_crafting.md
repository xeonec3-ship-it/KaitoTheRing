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

## 2. Крафт Высших и выше — по факту НЕ возможен (поправка управляющего)
Scroll Forge Iron's требует фокус школы. Теги фокусов `higher_focus`, `divine_focus`, `forbidden_focus`, `silent_focus` — **пустые**,
у `illusion_prism` и `broken_lullaby` нет рецепта. Поэтому заклинания школ Высшая/Божественная/Запретная (и Безмолвная) скрафтить
нельзя, даже если `allowCrafting()` = true (как у всех на HigherSpell). Кошмары и высшие Иллюзии — `allowCrafting` false (IllusionBase).
Если когда-нибудь в эти теги добавят предмет — сначала поставить `allowCrafting=false` у HigherSpell, иначе Высшие станут крафтиться.
