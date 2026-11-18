# PohSMP Core (`pohsmp_core`)

Мод сервера PohSMP для Minecraft 1.20.1 на Forge 47.4.21. Добавляет свои школы, заклинания, посохи и свитки для Iron's Spells 'n Spellbooks 3.16.1;
посохи анимирует GeckoLib 4.8.4. Последняя версия — **1.10.1**.

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
