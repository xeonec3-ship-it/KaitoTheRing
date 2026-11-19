# PohSMP Core (`pohsmp_core`)

Мод сервера PohSMP для Minecraft 1.20.1 на Forge 47.4.21. Добавляет свои школы, заклинания, посохи и свитки для Iron's Spells 'n Spellbooks 3.16.1;
посохи анимирует GeckoLib 4.8.4. Последняя версия — **1.12.0**.

Подробное описание того, что есть в моде: [docs/MOD_README.md](docs/MOD_README.md); план заклинаний: [docs/SPELLS_PLAN.md](docs/SPELLS_PLAN.md);
команды выдачи: [docs/give_commands.txt](docs/give_commands.txt).

## Структура

| Путь | Что там |
|---|---|
| `src/main/java/ru/pohsmp/core/` | код мода: регистрация (`Reg`, `PohCore`), посохи, ступени свитков, сеть |
| `.../core/spell/` | заклинания (51 файл) и общие системы (`Cutscene`, `Marks`, `Tasks`, `PohEvents`) |
| `.../core/client/` | клиентская часть: эффекты (`HigherFx`, `DownfallCut`), рендер посохов, HUD, камера роликов |
| `tools/gen_*.ps1` | PowerShell-генераторы текстур, моделей посохов (GeckoLib), иконок и свитков |
| `docs/notes/` | заметки по проекту и история записей о моде из CLAUDE.md |
| `libs/` | jar Iron's и GeckoLib для компиляции (в git не хранятся, см. `libs/README.md`) |

## Сборка

```
gradlew build
```

Нужна JDK 17. До сборки положите в `libs/` jar Iron's Spells и GeckoLib. Готовый jar появится в `build/libs/pohsmp_core-<версия>.jar`.
При каждом изменении поднимайте `mod_version` в `gradle.properties`.

## Анимации игрока при касте

У заклинаний с роликом камеры свои анимации игрока (формат PlayerAnimator, со сгибами локтей и колен,
для сгибов у игроков должен стоять мод **bendy-lib**):

| Заклинание | Анимация | Посох |
|---|---|---|
| Низвержение | `pohsmp_downfall_cast` / `_finish` | с посохом, по видео |
| Млечный Путь | `pohsmp_milky_way_cast` / `_finish` | без посоха |
| Пожирание душ | `pohsmp_soul_devour_cast` / `_finish` | без посоха |
| Божественное Табу | `pohsmp_taboo_cast` / `_finish` | без посоха |
| Закрытие Пространства | `pohsmp_space_closure_cast` / `_finish` | без посоха |

В анимациях без посоха предмет в руках на время каста и финала не рисуется (`client/HiddenHands`).
Позы задаются в `tools/gen_player_anims.py`; после правки запустите его — он пересоберёт JSON
(`assets/irons_spellbooks/player_animation/`) и 3D-превью `tools/anim_preview.html`.

## Задания и перенос на ПК

Задания для основного чата лежат в [`docs/specs/`](docs/specs/README.md): печати (`sigils_spec.md`) и система эффектов (`fx_spec.md`).
Перенос анимаций игрока на ПК: [`docs/HANDOFF_PC.md`](docs/HANDOFF_PC.md).

## Важно: репозиторий восстановлен из истории чатов

Исходники на ПК (`cnpc-project/mods-src/pohsmp_core`) сюда напрямую не копировались. Код собран из истории сессий Claude Code:
полные записи и чтения файлов, к которым применены все более поздние правки. Что известно о пробелах:

- **Ресурсов почти нет.** Текстуры, модели, анимации GeckoLib, иконки заклинаний и свитков — бинарные или сгенерированные файлы, в истории их нет.
  Большую часть можно пересоздать скриптами из `tools/` (они писались под Windows PowerShell и System.Drawing).
- **Lang-файлы неполные:** `ru_ru.json` / `en_us.json` собраны из отдельных правок, в них только 83 ключа.
- **Под сомнением** (часть правок не применилась, возможно, файлы меняли и PowerShell-командами):
  `HigherEvents.java`, `client/HigherFx.java`, `client/ClientInit.java`, `tools/gen_school_staffs.ps1`, `tools/gen_spell_icons.ps1`, `docs/give_commands.txt`.
- `client/CamFixClient.java` восстановлен тем же преобразованием, которым его когда-то перенесли из мода camfix.
- `build.gradle` воссоздан по шаблону Forge MDK с теми же зависимостями; оригинальный файл в истории целиком не встречался.
- Компиляция здесь не проверялась.

Когда будете у ПК, лучше всего скопировать сюда настоящую папку мода (`src`, `build.gradle`, `gradle.properties`, ресурсы) и закоммитить поверх:
тогда всё перечисленное выше закроется само.
