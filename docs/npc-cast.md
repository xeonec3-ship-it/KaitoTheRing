# NPC-маги и скрытие (T17, T01)

В скрипте CustomNPCs: `var Core = Java.type("ru.pohsmp.core.Api")`.

## Каст

| Вызов | Что делает |
|---|---|
| `Core.cast(npc, "pohsmp_core:disintegration", target)` | NPC кастует заклинание (мода или Iron's, можно просто `"fireball"`) в цель-сущность; уровень = минимальный |
| `Core.cast(npc, id, target, level)` | то же с уровнем |
| `Core.castAt(npc, id, x, y, z, level)` | в точку |
| `Core.isCasting(npc)` | кастует ли сейчас |
| `Core.cancelCast(npc)` | прервать; неотменяемые заклинания (Распад, Взрыв, Ковен...) не прерываются |
| `Core.forceCancelCast(npc)` | прервать что угодно (смерть, смена фазы) |

`cast` возвращает `false`, если NPC уже кастует, заклинание неизвестно или оно само отказало (нет цели в радиусе). Если цель
задана скриптом, но заклинание её «не видит», цель всё равно удерживается.

Работает как у мобов Iron's: проверка цели, предкаст, тики, удар в конце (у непрерывных — каждые 10 тиков), завершение.
Эффекты и ролики те же, что у игрока. Маны и перезарядок нет — когда кастовать, решает скрипт. NPC поднимает руки на время
каста. В скрипт NPC приходят события `cast_start(e)` и `cast_end(e)`, id заклинания в `e.caster`.

```javascript
var Core = Java.type("ru.pohsmp.core.Api")

/**
 * @param {NpcEvent.TargetEvent} e
 */
function target(e) {
    if (!Core.isCasting(e.npc)) Core.cast(e.npc, "pohsmp_core:disintegration", e.entity)
}

function cast_end(e) {
    e.npc.say("...")
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
