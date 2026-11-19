Jar для запуска игры из среды разработки (`gradlew runGameTestServer -PdevRun`, `gradlew runClient -PdevRun`), в git не хранятся.
Iron's и GeckoLib берутся из `libs/`, сюда — зависимости Iron's Spells 3.16.1 (все есть на Modrinth):

- `curios-forge-5.14.1+1.20.1.jar`
- `irons_lib-1.20.1-1.1.0.jar`
- `player-animation-lib-forge-1.0.2-rc1+1.20.jar`

Обычной сборке (`gradlew build`) они не нужны.
