# Клиентский патч основного jar: плавные эффекты (руны, круги) на сервере

Делает из `builds/pohsmp_core-1.16.0.jar` (стоит на сервере) копию **только для игроков** —
`builds/pohsmp_core-1.16.0-client-animfix-test.jar`. Сервер остаётся на оригинале: версия мода, сетевой канал, пакеты и
регистрации не меняются, серверные классы не тронуты. Причины и суть исправления — `docs/inbox/2026-11-21_cloudcode_anim_slideshow.md`.

Что делает `PatchJar` (ASM, по байткоду, без пересборки из исходников — исходники репо отличаются от этого jar):
1. добавляет `ClientClock`, `AnimClock`, `MoveSmooth` (из сборки репо) и `FxGlide` (этот каталог);
2. в 11 клиентских классах `Level.getGameTime()` (SRG `m_46467_`) → `ClientClock.ticks()` (проверяет число вызовов:
   DisintegrationFx 2, DownfallCut 6, EmberWhipClient 8, GateStaff 1, HiddenHands 2, HigherFx 5, JointFx 2, OutfitAnim 2,
   FxClient 2, GateManaRender 1, Ghosts 2), а «время + partialTick» считает в double (15 мест);
3. `ClientInit.init` регистрирует `ClientClock`;
4. `FxClient.handle` начинается с `if (FxGlide.move(m)) return;`, `FxClient.onRender` — с `FxGlide.frame(e);`.
Каждый изменённый метод проверяется ASM BasicVerifier; итог проверен верификатором JVM на классах Forge 1.20.1 (SRG).

## Пересобрать
```
# 1. классы из репо в SRG: временно положить FxGlide в исходники и собрать
cp tools/client_anim_patch/FxGlide.java src/main/java/ru/pohsmp/core/client/fx/
./gradlew build -x test --offline -q
rm src/main/java/ru/pohsmp/core/client/fx/FxGlide.java
mkdir -p /tmp/extra && (cd /tmp/extra && unzip -o ../../<repo>/build/libs/pohsmp_core-1.16.0.jar \
  ru/pohsmp/core/client/ClientClock.class ru/pohsmp/core/fx/AnimClock.class ru/pohsmp/core/fx/MoveSmooth.class \
  ru/pohsmp/core/client/fx/FxGlide.class)
# 2. патч (asm, asm-tree, asm-analysis 9.x — есть в кэше Gradle)
javac -cp asm.jar:asm-tree.jar:asm-analysis.jar -d /tmp/pt tools/client_anim_patch/PatchJar.java
java -cp /tmp/pt:asm.jar:asm-tree.jar:asm-analysis.jar PatchJar builds/pohsmp_core-1.16.0.jar /tmp/extra builds/pohsmp_core-1.16.0-client-animfix-test.jar
```
Если основной jar поменяется (новая версия с ПК) и число вызовов не совпадёт — патчер остановится с ошибкой, ничего не записав
наполовину; тогда лучше перенести правки в исходники ПК по «Точечным правкам» письма.
