Сюда кладутся jar для компиляции (в git не попадают):

- `irons_spellbooks-1.20.1-3.16.1.jar`
- `geckolib-forge-1.20.1-4.8.4.jar`
- `player-animation-lib-forge-1.0.2-rc1+1.20.jar` (PlayerAnimator, нужен Iron's)
- для одежды безмолвной ведьмы (скрытие в подсказках и на JourneyMap, только API, в игре не обязательны):
  `Jade-1.20.1-Forge-11.13.3.jar`, `wthit-1.20.1-forge-8.21.2.jar`, `theoneprobe-1.20.1-10.0.5.jar`,
  `journeymap-api-forge-1.20.1-2.0.0.jar` (лежит внутри `journeymap-forge-1.20.1-6.0.7.jar`, `META-INF/jarjar/`)

Копии лежат в модах Prism (`%APPDATA%\PrismLauncher\instances\1.20.1\minecraft\mods`). Всё сразу скачать с Modrinth:
`python tools/fetch_libs.py`.
