# NPC-маги и скрытие (T17, T01)

В скрипте CustomNPCs: `var Core = Java.type("ru.pohsmp.core.Api")`.

## Каст

Полное описание с таблицей вызовов, правилами и примером босса — `docs/MOD_README.md`, раздел «NPC-маги: `Core.cast`».
Кратко:

| Вызов | Что делает |
|---|---|
| `Core.cast(npc, "pohsmp_core:disintegration", target[, level])` | NPC кастует как игрок; target — сущность, точка (`IPos`, `[x, y, z]`, `{x, y, z}`) или `null`; уровень по умолчанию максимальный |
| `Core.cast(npc, id, x, y, z[, level])`, `Core.castAt(...)` | в точку |
| `Core.isCasting(npc)`, `Core.castingSpell(npc)` | кастует ли, какое заклинание |
| `Core.cancelCast(npc)` | прервать; неотменяемые (Дезинтеграция и др.) не прерываются |
| `Core.cancelCast(npc, true)`, `Core.forceCancelCast(npc)` | прервать что угодно |

Цель проверяется по правилам заклинания, как у игрока: вне дальности или не видна — `cast` вернёт `false` (причина в логе).
На модели NPC у игроков проигрывается та же анимация каста, что у игрока. События скрипта: `cast_start(e)`, `cast_end(e)`
(`e.spell`, `e.cancelled`; id заклинания также в `e.caster`).

```javascript
var Core = Java.type("ru.pohsmp.core.Api")

function target(e) {
    if (!Core.isCasting(e.npc)) Core.cast(e.npc, "pohsmp_core:disintegration", e.entity)
}

function cast_end(e) {
    if (!e.cancelled) e.npc.say("...")
}
```

## Скрытие

| Вызов | Что делает |
|---|---|
| `Core.hide(entity, ticks)` | никто не видит: модель, броня, предметы в руках, имя, тень (NPC тоже); `0` = пока не покажут |
| `Core.hide(entity, ticks, noDamage, noCollide, freeze)` | плюс: без урона, без толкания, стоит на месте |
| `Core.show(entity)` | показать |
| `Core.isHidden(entity)` | скрыт ли |

Команды (оп 2): `/pohsmp hide <цели> <секунды>` (0 — пока не покажут), `/pohsmp show <цели>`.
