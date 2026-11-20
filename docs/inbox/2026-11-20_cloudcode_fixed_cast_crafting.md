# Облачный программист → Кодингу (20.11): фиксированный каст у роликовых, запрет крафта, книги и наделение

Ветка `claude/cult-bosses-code`. Задача — docs/inbox/2026-11-20_mgr_fixed_cast_and_crafting.md (решения владельца).
Код в облаке восстановлен из чатов и может отставать от ПК: переносите **новые файлы целиком**, а **точечные правки** — по списку ниже,
сверяя с версией на ПК.

## Что сделано

1. **Фиксированный каст.** Маркер `FixedCastSpell`: для таких заклинаний `getEffectiveCastTime` = `getCastTime(level)`, бонусы скорости каста
   не действуют (атрибут Iron's `cast_time_reduction` — от любых источников: зачарования, мантии, кольца, мантия Безмолвной ведьмы).
   Работает через миксин в `AbstractSpell.getEffectiveCastTime` (HEAD) + одна строка в `PohSpell` (там свой путь для школы Безмолвной).
   Новое заклинание с роликом подключается **одной строкой**: `implements ru.pohsmp.core.spell.FixedCastSpell`.
   Тест `MagicRulesTest.everyCutsceneSpellHasFixedCast` проверяет, что каждый файл с `Cutscene.start(` содержит маркер — забыть не получится.
   Подключены (все, кто зовёт `Cutscene.start` в этой ветке): Downfall, MilkyWay, SoulDevour, Taboo, SpaceClosure, StarFall,
   RiteSpell (→ SoulSeal, Blessing), ButterflyDream, ErasedName, NoAwakening, MythicT23 (→ WorldTree, AbyssEye, LastDawn), а также
   SilentGate и CovenArrival (у них и так был фиксированный каст, маркер — для единообразия; их override оставлены).
   Disintegration роликов не зовёт, у него свой фиксированный override — не трогал. Перезарядка не тронута.
2. **Запрет крафта.** Миксин в `AbstractSpell.allowCrafting` (HEAD): `false` для **наших** заклинаний (id `pohsmp_core:*`) со встроенной ступенью
   HIGHER/MYTHIC/DIVINE/CREATION/UNKNOWN (по `Tier.builtin`, включая Disintegration и его реплику) и для **всей школы Безмолвной** —
   независимо от конфига заклинаний Iron's на сервере. Scroll Forge проверяет `allowCrafting()` на сервере (`ScrollForgeMenu.setupResultSlot`),
   поэтому и подменённый клиент свиток не получит; JEI тоже перестанет показывать рецепты. Заклинания Iron's и наши обычные — без изменений.
   `SilentStaffSpell.allowCrafting` был `ready() && !needsStaff()` (4 заклинания T20 крафтились) → теперь `false`. Каст из свитков/книги остаётся.
   Arcane Anvil: слияние свитков (апгрейд уровня), сферы улучшений, точильный камень, слоты книг — **не трогал**.
   Лут/сундуки: `allowLooting=false` уже у всех наших — без изменений.
3. **Книги и наделение (только MYTHIC/DIVINE/CREATION/UNKNOWN, HIGHER — можно как раньше).**
   - Inscription Table: Iron's шлёт отменяемое `InscribeSpellEvent` — отменяем его (обработчик `SpellBans.onInscribe`, без миксина).
     Ступень берётся со свитка в слоте стола (`Tier.of`: NBT `pohsmp_tier`, встроенная, либо «уровень выше максимума»), иначе — из SpellData.
   - Arcane Anvil, наделение (предмет + свиток → предмет с заклинанием; любые `canImbue`: оружие, посохи — **и наши посохи тоже**, а также
     UniqueItem): миксин в `ArcaneAnvilMenu.createResult` (TAIL) очищает слот результата. Блок наковальни не меняется, остальные её режимы работают.
   - Наши посохи с заклинаниями из коробки (SilentWitchStaff и т. п.) не затронуты: им заклинания вписывает код мода, а не игрок.
   - Внимание: по `Tier.of` обычный свиток с уровнем «макс +3» считается Мифическим и тоже не впишется в книгу/предмет («макс +1..2» = Высшая — можно).
     Если владелец хочет иначе — поменять только `SpellBans.bindBanned`/`tierOf` (считать лишь встроенную ступень).
4. **Сообщение** в actionbar: «Эта магия не поддаётся записи» (книга) / «Эта магия не вкладывается в предметы» (наковальня), en — тоже.

## Новые файлы (перенести целиком)

- `src/main/java/ru/pohsmp/core/spell/FixedCastSpell.java` — маркер.
- `src/main/java/ru/pohsmp/core/spell/MagicRules.java` — чистые правила (какие ступени не крафтятся / не вписываются), без Minecraft.
- `src/main/java/ru/pohsmp/core/spell/SpellBans.java` — `craftBanned(spell)`, `bindBanned(scroll)`, `tierOf(SpellData)`, `tell(...)`,
  обработчик `InscribeSpellEvent` (`@Mod.EventBusSubscriber`, регистрируется сам, PohCore не трогал).
- `src/main/java/ru/pohsmp/core/mixin/AbstractSpellMixin.java` — фиксированный каст + запрет крафта (имена Iron's, `remap=false`, работает и в dev, и в jar).
- `src/main/java/ru/pohsmp/core/mixin/ArcaneAnvilMenuMixin.java` — запрет наделения (метод `m_6640_` в jar / `createResult` в dev;
  проверено javap: в собранном jar ссылки переобфусцированы в SRG — `Inventory.f_35978_`, `m_38853_` и т. д.).
- `src/test/java/ru/pohsmp/core/spell/MagicRulesTest.java` — 4 теста: крафт, книги/предметы, совпадение ключей с enum `Tier`
  (читается из исходника), «каждый `Cutscene.start` → `FixedCastSpell`».

## Точечные правки в существующих файлах

| Файл | Место | Было → стало |
|---|---|---|
| `src/main/resources/pohsmp_core.mixins.json` | массив `"mixins"`, после `"PlayerListMixin"` | добавить `"AbstractSpellMixin", "ArcaneAnvilMenuMixin"` (общие, не client) |
| `src/main/java/ru/pohsmp/core/spell/PohSpell.java` | `getEffectiveCastTime`, первой строкой тела (перед `if (getSchoolType() == ...SILENT...)`) | `if (this instanceof FixedCastSpell) return getCastTime(spellLevel);   // owner 20.11: cutscene spells - fixed cast time` |
| `src/main/java/ru/pohsmp/core/spell/silent/SilentStaffSpell.java` | строка `@Override public boolean allowCrafting()` | `return ready() && !needsStaff();` → `return false;` (с комментарием) |
| `src/main/resources/assets/pohsmp_core/lang/ru_ru.json` | в конец | `"message.pohsmp_core.no_inscribe": "Эта магия не поддаётся записи"`, `"message.pohsmp_core.no_imbue": "Эта магия не вкладывается в предметы"` |
| `src/main/resources/assets/pohsmp_core/lang/en_us.json` | в конец | `"message.pohsmp_core.no_inscribe": "This magic cannot be written down"`, `"message.pohsmp_core.no_imbue": "This magic cannot be imbued into items"` |

Объявления классов — дописать ` implements ru.pohsmp.core.spell.FixedCastSpell` перед `{`:

| Файл | Объявление |
|---|---|
| `spell/DownfallSpell.java` | `public class DownfallSpell extends PohSpell` |
| `spell/MilkyWaySpell.java` | `public class MilkyWaySpell extends HigherSpell` |
| `spell/SoulDevourSpell.java` | `public class SoulDevourSpell extends PohSpell` |
| `spell/TabooSpell.java` | `public class TabooSpell extends PohSpell` |
| `spell/SpaceClosureSpell.java` | `public class SpaceClosureSpell extends PohSpell` |
| `spell/StarFallSpell.java` | `public class StarFallSpell extends HigherSpell` |
| `spell/RiteSpell.java` | `public abstract class RiteSpell extends PohSpell` |
| `spell/CovenArrivalSpell.java` | `public class CovenArrivalSpell extends PohSpell` |
| `spell/illusion/ButterflyDreamSpell.java` | `public class ButterflyDreamSpell extends IllusionBase` |
| `spell/silent/SilentGateSpell.java` | `public class SilentGateSpell extends SilentStaffSpell` |
| `erased/ErasedNameSpell.java` | `public class ErasedNameSpell extends PohSpell` |
| `nightmare/NoAwakeningSpell.java` | `public class NoAwakeningSpell extends NightmareSpells.Base` |
| `mythic/MythicT23.java` | `public abstract class MythicT23 extends PohSpell` |

(пути от `src/main/java/ru/pohsmp/core/`). Если на ПК есть ещё заклинания с `Cutscene.start` — тест их назовёт.

## Как перенести на ПК
1. `git fetch origin claude/cult-bosses-code` и `git diff <ваша база>..FETCH_HEAD -- src/main/java/ru/pohsmp/core/spell src/main/java/ru/pohsmp/core/mixin ...`
   либо по таблицам выше вручную: новые файлы — скопировать, правки — по одной строке.
2. `gradlew test --tests "ru.pohsmp.core.spell.*"` — должно быть 4/4; `gradlew build`.

## Сборка в облаке
- `./gradlew build -x test` — **успешно**; `./gradlew test --tests "ru.pohsmp.core.spell.*"` — успешно (4/4).
- Полный `./gradlew test`: **3 падения, были и до моих правок** (проверено на чистой ветке через stash): `FxAssetsTest`, `FxShapesTest`, `FxTest` —
  `NumberFormatException: "-1.2+0"` в `fx/aris_intro`, `fx/aris_phase2`, `fx/cult_leader_intro` (файлы боссов второго программиста в этой ветке;
  я их не трогал). Сообщите ему: в JSON эффектов попали выражения вида `-1.2+0` вместо чисел.
- Для компиляции в облаке пришлось докачать `libs/voicechat-forge-1.20.1-2.6.20.jar` (Modrinth) — `tools/fetch_libs.py` его не качает;
  в git не попадает. Стоит добавить в fetch_libs.

## Чек-лист проверки в игре
Фиксированный каст:
- [ ] Надеть всё на скорость каста (зачарованные мантии/кольца Iron's, мантия Безмолвной ведьмы; или `/attribute @s irons_spellbooks:cast_time_reduction base set 2`).
- [ ] Каст Downfall, Млечного пути, Пожирания души, Табу, Замыкания пространства, Звездопада, Печати души, Благословения, Сна бабочки,
      Стёртого имени, «Без пробуждения», Древа мира, Ока бездны, Последнего рассвета, Врат, Прихода ковена: полоса каста и ролик камеры
      одинаковой длины, заклинание срабатывает в конце ролика, руки скрыты ровно на время каста. Без бонусов — длительность та же.
- [ ] Обычное заклинание (фаербол) по-прежнему кастуется быстрее с бонусом. Перезарядки не изменились.
- [ ] NPC-каст роликовых (если используется) — та же длительность.
Крафт:
- [ ] Scroll Forge: в списке нет наших Высших/Мифических/Божественных/Творения/Неизвестных/Безмолвных (в т.ч. 4 заклинаний T20); обычные наши и Iron's — есть и крафтятся.
- [ ] JEI: у этих заклинаний нет рецепта Scroll Forge.
- [ ] Выданный оператором свиток Безмолвного заклинания T20 кастуется, как раньше.
Книги и наделение:
- [ ] Inscription Table: свиток Мифической/Божественной/Творения/Неизвестной ступени не вписывается, в actionbar «Эта магия не поддаётся записи»; свиток не пропадает.
- [ ] Высший свиток (например, Колыбель) и обычный — вписываются.
- [ ] Arcane Anvil: меч/посох (Iron's и наш) + Мифический свиток → результата нет, actionbar «Эта магия не вкладывается в предметы»; + Высший свиток → результат есть.
- [ ] Arcane Anvil: слияние двух свитков фаербола одного уровня, сферы улучшений, точильный камень — работают как раньше.
- [ ] Посох Безмолвной ведьмы и другие наши посохи с заклинаниями из коробки — заклинания на месте, кастуются.
- [ ] В логе при запуске нет ошибок миксинов `AbstractSpellMixin` / `ArcaneAnvilMenuMixin` (если инжект не нашёл метод, он молча не применится —
      тогда первые пункты чек-листа это покажут).

## Открытые вопросы
- Другие моды-«контейнеры заклинаний» в сборке (свои книги, кольца, Curios с заклинаниями) отсюда не видно — список модов есть только на ПК.
  Если они пишут через Iron's `InscriptionTableMenu`/`ArcaneAnvilMenu` — запрет действует; если через свой GUI — нужен отдельный хук.
- Торговцы Iron's (Wandering Magician и т. п.) и случайные свитки в луте: в коде торговцев не проверял, какой фильтр они используют
  (ожидаю `allowLooting`, у наших он уже `false`). Проверить в игре: у торговцев не должно быть свитков наших ступеней.
