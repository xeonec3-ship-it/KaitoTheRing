# PohSMP Core (`pohsmp_core`)

Основной мод сервера PohSMP. Нужен и на сервере, и у игроков (одна версия).
Вобрал в себя `pohsmp_camfix` — старый jar из сборки убрать.

## Что внутри
- **Камера в роликах** (только клиент): пока идёт ролик CNPCExtended, модель игрока видна от первого лица, рука скрыта.
  Конфиг клиента `config/pohsmp_core-client.toml`, раздел `[camera]`: `enabled`, `mode` (cnpcext/distance/both), `distanceThreshold`.
- **Помощники для скриптов CNPC**: `var Core = Java.type("ru.pohsmp.core.Api")`
  - `Core.version()` — версия мода;
  - `Core.cmd(world.getMCLevel(), "команда")` — тихая команда от сервера (без вывода в чат и лог), возвращает результат.

- **Школа Iron's «Божественная»** (`pohsmp_core:divine`, атрибуты `divine_spell_power` / `divine_magic_resist`, тип урона `divine_magic` сквозь броню).
- **Заклинание «Дезинтеграция»** (`pohsmp_core:disintegration`, уровень 1, каст 10 с, урон не сбивает): цель в 48 блоках
  застывает и поднимается на 0.75 блока, вокруг игрока и цели магические круги (рисует клиент, текстуры `tools/gen_fx_textures.ps1`),
  в конце вспышка и столб света, урон 50% макс. HP + 40 сквозь броню.
- **Ступени свитков** выше Легендарной: Высшая (алый), Мифическая (фиолетовый), Божественная (золотой) — подпись в подсказке свитка;
  у Божественной аура при касте и отдача после. Как задавать — `give_commands.txt`.
- **Школа «Высшая»** (1.3.0; `pohsmp_core:higher`, алая, атрибуты `higher_spell_power` / `higher_magic_resist`, тип урона `higher_magic`, броня учитывается,
  множитель `[higher] damageMult`). Шесть заклинаний уровня 1 со ступенью Высшая — по одному для магов второго дня и Эшли:
  Колыбель кошмара, Звезда судьбы, Сингулярность, Печать запрета, Вознесение ветра, Без пепла. Отрисовка — `client/HigherFx`
  (пакет `HFx`), текстуры — `tools/gen_higher_textures.ps1`. Свои эффекты: Кошмарный сон, Ужас, Печать запрета, Тяжесть, Вознесение.
- **Вкладка в творческом** «PohSMP» (иконка `irons_spellbooks:gold_crown`).
- Настройки сервера: `world/serverconfig/pohsmp_core-server.toml`.

## Сборка
Iron's и GeckoLib для компиляции лежат в `C:\Users\xeone\pohcore-build\libs` (копии из модов Prism, `compileOnly fg.deobf`).

Исходник здесь, собирается в `C:\Users\xeone\pohcore-build` (вне OneDrive): скопировать `src`, `gradle.properties`, `build.gradle`,
затем `gradlew build` с `JAVA_HOME` = `%APPDATA%\PrismLauncher\java\java-runtime-gamma`. Готовый jar — `build\libs`, копия лежит здесь.
При каждом изменении поднимать `mod_version` в `gradle.properties`.
