#!/bin/sh
# Офлайн-проверка маны «Безмолвных врат» (перенос из God Wand) без Minecraft: заглушка Vec3 + javac.
# Проверяет атлас, часы маны, позу посоха, геометрию; рисует атлас и кадры (программный растеризатор) в каталог $1 (по умолчанию /tmp/gate_mana).
set -e
HERE=$(cd "$(dirname "$0")" && pwd); SRC="$HERE/../../src/main/java/ru/pohsmp/core/client/fx/gate"
OUT=${1:-/tmp/gate_mana}; CLS=$(mktemp -d); mkdir -p "$OUT"
javac -d "$CLS" "$HERE/stub/net/minecraft/world/phys/Vec3.java" "$SRC/GateAtlasGen.java" "$SRC/GateDraw.java" "$SRC/GateMana.java" \
  "$SRC/GateStaffPose.java" "$HERE/src/ru/pohsmp/core/client/fx/gate/ManaCheck.java"
java -Djava.awt.headless=true -cp "$CLS" ru.pohsmp.core.client.fx.gate.ManaCheck "$OUT"
