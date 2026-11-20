# Управляющий → Кодингу (20.11): убраны поминутные «ticker alive» в логе

Владелец попросил, пока Кодинг выключен. Изменено только логирование, логика не тронута:
- `nightmare/Bestiary.java`: «bestiary ticker alive …» каждую минуту → один раз при первом тике: «bestiary ticker started …».
- `spell/illusion/MirrorLabyrinthSpell.java`: «mirror_labyrinth ticker alive …» каждую минуту → один раз: «mirror_labyrinth ticker started …».
Собрано в облаке (`./gradlew build`, зависимости через `tools/fetch_libs.py` + voicechat 2.6.20 с Modrinth) поверх 5b7792c,
jar положен в `builds/pohsmp_core-1.16.0.jar`. На ПК при следующей сборке просто подтяни ветку. В игре не проверено.
