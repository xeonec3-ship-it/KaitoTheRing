Jar для запуска игры из среды разработки (`gradlew runGameTestServer -PdevRun`, `gradlew runClient -PdevRun`), в git не хранятся.
Iron's, GeckoLib и PlayerAnimator берутся из `libs/`, сюда — остальные зависимости Iron's Spells 3.16.1 (есть на Modrinth):

- `curios-forge-5.14.1+1.20.1.jar`
- `irons_lib-1.20.1-1.1.0.jar`

Обычной сборке (`gradlew build`) они не нужны.
