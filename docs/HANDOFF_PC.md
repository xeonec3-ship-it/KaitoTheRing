# Перенос на ПК: анимации игрока для заклинаний с роликом

Инструкция для Claude Code на ПК, в папке `cnpc-project`. Работа сделана в облачной сессии
в репозитории `xeonec3-ship-it/KaitoTheRing`, ветка `claude/cnpc-chats-repo-0hcody`.

**Важно.** Код в этом репозитории восстановлен из истории чатов, и часть файлов может отставать от ПК.
Поэтому **существующие файлы на ПК не перезаписывать**: новые файлы копируются целиком,
а в существующие вносятся только точечные правки, описанные ниже.

## Что сделано

Собственные анимации игрока (PlayerAnimator, формат Emotecraft v3, со сгибами локтей и колен через bendy-lib)
для всех заклинаний с роликом камеры:

| Заклинание | Анимации | Посох |
|---|---|---|
| Низвержение (`DownfallSpell`) | `pohsmp_downfall_cast`, `pohsmp_downfall_finish` | с посохом: прокрутка посоха вокруг кисти, посох-преграда |
| Млечный Путь (`MilkyWaySpell`) | `pohsmp_milky_way_cast`, `_finish` | без посоха |
| Пожирание душ (`SoulDevourSpell`) | `pohsmp_soul_devour_cast`, `_finish` | без посоха |
| Божественное Табу (`TabooSpell`) | `pohsmp_taboo_cast`, `_finish` | без посоха |
| Закрытие Пространства (`SpaceClosureSpell`) | `pohsmp_space_closure_cast`, `_finish` | без посоха |

- Движения привязаны к планам камеры из `client/DownfallCut`: сцены 1–4 переключаются на долях каста 0 / .16 / .32 / .50 / .68 / .84.
- Пока идут каст и финал анимации без посоха, предметы в руках кастующего не рисуются ни у кого из игроков.
  Это делает `client/HiddenHands`, инвентарь при этом не меняется.
- Файлы анимаций лежат в пространстве имён Iron's (`assets/irons_spellbooks/player_animation/`), поэтому заклинание просто вызывает
  `new AnimationHolder("pohsmp_…", true)`. Это работает в любой версии Iron's.
- Позы задаются в `tools/gen_player_anims.py`: руки ставятся обратной кинематикой по точке хвата и направлению посоха,
  а широкие жесты задаются прямо углами суставов. Скрипт пишет JSON и 3D-превью `tools/anim_preview.html`.
  Для запуска нужны Python 3 и numpy.

## 1. Получить файлы

Любой из двух способов:

- `git clone -b claude/cnpc-chats-repo-0hcody https://github.com/xeonec3-ship-it/KaitoTheRing "%TEMP%\KaitoTheRing"`
- или скачать ZIP ветки с GitHub и распаковать во временную папку.

Дальше `SRC` — это эта папка, `MOD` — `cnpc-project\mods-src\pohsmp_core`.

## 2. Скопировать новые файлы целиком

| Откуда (`SRC`) | Куда |
|---|---|
| `src\main\resources\assets\irons_spellbooks\player_animation\*.json` (10 файлов) | `MOD\src\main\resources\assets\irons_spellbooks\player_animation\` |
| `src\main\java\ru\pohsmp\core\spell\CastAnims.java` | `MOD\src\main\java\ru\pohsmp\core\spell\` |
| `src\main\java\ru\pohsmp\core\client\HiddenHands.java` | `MOD\src\main\java\ru\pohsmp\core\client\` |
| `tools\gen_player_anims.py`, `tools\anim_preview.template.html`, `tools\anim_preview.html` | `cnpc-project\tools\` |

Перед копированием проверить, нет ли на ПК файлов с такими именами. Если есть, сначала показать мне разницу.

## 3. Точечные правки в существующих файлах

### `client/ClientInit.java`

В `init(...)` после регистрации `HigherFx` добавить строку:

```java
MinecraftForge.EVENT_BUS.register(HiddenHands.class);
```

### `spell/DownfallSpell.java`

Заменить две строки

```java
@Override public AnimationHolder getCastStartAnimation() { return SpellAnimations.ANIMATION_LONG_CAST; }
@Override public AnimationHolder getCastFinishAnimation() { return SpellAnimations.ANIMATION_LONG_CAST_FINISH; }
```

на

```java
/** Своя анимация игрока с посохом: assets/irons_spellbooks/player_animation/pohsmp_downfall_*.json (tools/gen_player_anims.py). */
public static final AnimationHolder ANIM_CAST = new AnimationHolder("pohsmp_downfall_cast", true);
public static final AnimationHolder ANIM_FINISH = new AnimationHolder("pohsmp_downfall_finish", true);

@Override public AnimationHolder getCastStartAnimation() { return ANIM_CAST; }
@Override public AnimationHolder getCastFinishAnimation() { return ANIM_FINISH; }
```

Если `SpellAnimations` больше нигде в файле не используется, удалить его импорт.

### `MilkyWaySpell`, `SoulDevourSpell`, `TabooSpell`, `SpaceClosureSpell`

В каждом из четырёх файлов заменить те же две строки (`ANIMATION_LONG_CAST` / `ANIMATION_LONG_CAST_FINISH`) на код ниже,
подставив `<имя>`: `milky_way`, `soul_devour`, `taboo`, `space_closure` соответственно.

```java
/** Своя анимация игрока без посоха (tools/gen_player_anims.py); предмет в руках на это время не рисуется. */
private static final AnimationHolder ANIM_CAST = CastAnims.of("<имя>_cast"), ANIM_FINISH = CastAnims.of("<имя>_finish");

@Override public AnimationHolder getCastStartAnimation() { return ANIM_CAST; }
@Override public AnimationHolder getCastFinishAnimation() { return ANIM_FINISH; }

@Override
public void onClientPreCast(Level level, int spellLevel, LivingEntity entity, InteractionHand hand, @Nullable MagicData md) {
    super.onClientPreCast(level, spellLevel, entity, hand, md);
    CastAnims.hideHands(level, entity, getEffectiveCastTime(spellLevel, entity));
}
```

Если в файле уже есть свой `onClientPreCast`, не заводить второй: дописать вызов `CastAnims.hideHands(...)` в существующий.
Добавить импорты, которых не хватает: `net.minecraft.world.InteractionHand`, `org.jetbrains.annotations.Nullable`,
`net.minecraft.world.level.Level`, `net.minecraft.world.entity.LivingEntity`, `io.redspace.ironsspellbooks.api.magic.MagicData`.
Импорт `SpellAnimations` удалить, если он больше не используется.

## 4. Сборка и установка

1. Поднять `mod_version` в `MOD\gradle.properties` (сейчас 1.10.1, новая версия — 1.11.0).
2. Собрать как обычно: `robocopy` исходников в `C:\Users\xeone\pohcore-build`, затем `gradlew build` с `JAVA_HOME` от Prism.
3. Положить jar в клиент Prism вместо старого.
4. **Добавить в клиент мод `bendy-lib` для Forge 1.20.1.** Без него сгибы локтей, колен и корпуса не видны,
   руки остаются прямыми, но ничего не ломается. Он нужен всем игрокам, на сервере не нужен.

## 5. Что проверить в игре

Кастовать в обычном режиме, не в боевом режиме Epic Fight. Смотреть ролик и вид от третьего лица.

- **Низвержение.** Направление оборота посоха. Задумано так: если смотреть игроку в спину, навершие идёт против часовой
  (лево → низ → право → верх). Если в игре наоборот, то в `tools/gen_player_anims.py` в `downfall_cast` заменить
  `roll=tw_fix + 360` на `roll=tw_fix - 360` (и в последнем ключе тоже), затем перезапустить скрипт.
- **Корпус.** Наклоны (`torso bend`) должны идти вперёд, когда игрок склоняется, например в сосредоточении и молитве.
  Если корпус гнётся назад, знак сгиба корпуса у bendy-lib обратный: поправить знак `bend` в позах `torso`.
- **Локти.** Сгибаются как у человека, предплечье вперёд. Если гнутся назад, поменять знак `bend` у рук в `arm()`.
- **Предметы в руках.** Во время четырёх заклинаний без посоха предмета не видно, после финала он возвращается.
- **Посох в Низвержении.** Висящий в воздухе посох до 2.6 с пока не сделан. Это отдельный клиентский эффект,
  сейчас посох просто сразу в руке.

## 6. После переноса

Записать в `CLAUDE.md` проекта: какая версия собрана, что анимации игрока теперь свои, где генератор
и что bendy-lib нужен клиентам. Результаты проверки в игре сообщить мне в облачную сессию.

## 7. Добавлено позже (чат идей, 18.11)

Всё ниже — новые файлы: копировать целиком. Существующие файлы мода на ПК по-прежнему не перезаписывать.

| Что | Откуда (`SRC`) | Куда |
|---|---|---|
| Анимации «Появления Ковена» (90 с, финал, ритуал свиты) | `src\main\resources\assets\irons_spellbooks\player_animation\pohsmp_coven_*.json` | `MOD\src\main\resources\assets\irons_spellbooks\player_animation\` |
| Демо-печати | `src\main\resources\assets\pohsmp_core\sigils\*.json` | `MOD\src\main\resources\assets\pohsmp_core\sigils\` |
| Текстуры печатей | `src\main\resources\assets\pohsmp_core\textures\sigil\*.png` | `MOD\src\main\resources\assets\pohsmp_core\textures\sigil\` |
| Спрайты частиц | `src\main\resources\assets\pohsmp_core\textures\fx\*.png` | `MOD\src\main\resources\assets\pohsmp_core\textures\fx\` |
| Стили школ и демо-эффект | `src\main\resources\assets\pohsmp_core\fx\**` | `MOD\src\main\resources\assets\pohsmp_core\fx\` |
| Логика печатей (без Minecraft) | `src\main\java\ru\pohsmp\core\fx\sigil\*.java` | `MOD\src\main\java\ru\pohsmp\core\fx\sigil\` |
| Тесты логики | `src\test\java\ru\pohsmp\core\fx\**` (печати и эффекты) | `MOD\src\test\java\ru\pohsmp\core\fx\` |
| Логика эффектов (без Minecraft) | `src\main\java\ru\pohsmp\core\fx\*.java` (`FxDef`, `FxStyle`, `FxMath`) | `MOD\src\main\java\ru\pohsmp\core\fx\` |
| Портал Ковена | `src\main\resources\assets\pohsmp_core\fx\meshes\coven_portal.json`, генератор `tools\gen_coven_portal.py` | `MOD\src\main\resources\assets\pohsmp_core\fx\meshes\`, `cnpc-project\tools\` |
| Генераторы и превью | `tools\gen_player_anims.py`, `tools\gen_sigil_textures.py`, `tools\build_sigil_preview.py`, `tools\*preview*.html` | `cnpc-project\tools\` |
| Документы | `docs\sigils.md`, `docs\fx.md`, `docs\specs\`, `docs\ideas\`, `docs\references\` | рядом с проектом, для чтения |

**Правка в `build.gradle` на ПК** (точечно, для `gradlew test`):

```gradle
repositories {
    // … что уже есть …
    mavenCentral()
}
dependencies {
    // … что уже есть …
    testImplementation 'org.junit.jupiter:junit-jupiter:5.10.2'
    testImplementation 'com.google.code.gson:gson:2.10.1'
    testRuntimeOnly 'org.junit.platform:junit-platform-launcher'
}
tasks.named('test', Test).configure { useJUnitPlatform() }
```

После копирования: `gradlew test` — должно пройти 16 тестов (`SigilTimelineTest` и `FxTest`). Логику печатей сразу использовать в отрисовщике
(задание `docs/specs/sigils_spec.md`, формат — `docs/sigils.md`). Задание на заклинание — `docs/specs/coven_arrival_spec.md`.
