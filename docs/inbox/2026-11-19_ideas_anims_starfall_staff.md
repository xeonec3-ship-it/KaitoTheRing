# Чат идей → основному коду: анимации «Падения звезды» (T05) и жестов посоха (T20)

**От:** чат идей (сессия анимаций). **Что сделано:** 8 новых анимаций игрока в `assets/irons_spellbooks/player_animation/`
(генератор `tools/gen_player_anims.py`, превью `tools/anim_preview.html`; ключевые кадры проверены рендером превью).
Java не трогал. Подробности — в `docs/specs/tasks/T05_star_fall.md` и `T20_silent_staff_spells.md` (разделы «Анимация… готова»).

| Анимация | Длительность | Куда |
|---|---|---|
| `pohsmp_star_fall_cast` | 8 с = 160 тиков ровно, держит последнюю позу | `StarFallSpell.getCastStartAnimation` → `CastAnims.of("star_fall_cast")` |
| `pohsmp_star_fall_finish` | 1.5 с | `StarFallSpell.getCastFinishAnimation` → `CastAnims.of("star_fall_finish")` |
| `pohsmp_silent_volley_cast` | 3 с (взмах к 2.95, стрелы в 3.0) | `SilentVolleySpell.getCastStartAnimation` → `CastAnims.of("silent_volley_cast")` |
| `pohsmp_silent_volley_finish` | 0.9 с | `SilentVolleySpell.getCastFinishAnimation` → `CastAnims.of("silent_volley_finish")` |
| `pohsmp_sage_barrier_cast` | 1.5 с (удар о землю 1.12) | `SageBarrierSpell.getCastStartAnimation` → `CastAnims.of("sage_barrier_cast")` |
| `pohsmp_sage_barrier_finish` | 1.0 с | `SageBarrierSpell.getCastFinishAnimation` → `CastAnims.of("sage_barrier_finish")` |
| `pohsmp_worgan_flame_cast` | 2 с | `WorganFlameSpell.getCastStartAnimation` → `CastAnims.of("worgan_flame_cast")` |
| `pohsmp_worgan_flame_finish` | 3.5 с (выдох 3 с + опускание) | `WorganFlameSpell.getCastFinishAnimation` → `CastAnims.of("worgan_flame_finish")` |

**Нужно от кода:**
1. Заменить анимации Iron's на эти (таблица выше).
2. «Падение звезды» — руки пустые, как у других роликовых: `CastAnims.hideHands(level, entity, CAST)` в `onCast` (сейчас не вызывается).
   Жесты T20 — с посохом, `hideHands` не нужен.
3. Если касты в `[silent_staff]` поменяют (60 / 30 / 40 тиков, выдох 60) — напишите, пересоберу под новые длительности.

**Вопрос/замечание:** в задаче для чата идей «Безмолвный залп» описан как каст ~1.5 с, а в коде и спеке — 3 с (`castTicks = 60`);
анимация сделана под 3 с. Если нужно 1.5 с — скажите.
Не проверено в игре (только превью three.js).
