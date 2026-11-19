# Превью «Небесной бабочки» (T22)

Самостоятельная сцена three.js «под Майнкрафт» для проверочных кадров `docs/media/t22_celestial_*.jpg`: рисует mesh (`boxes`, новая часть
`quad` с петлями), `move.keys`, `sprites` (в т.ч. новые `wrap`/`avoid`/`path`), `wave`, `flash`, `tint`, `decal`, `halo` — по логике
клиента (`ElementDraw`, `MeshDraw`), упрощённо.

```
D=$(mktemp -d); cp tools/celestial_preview/* $D; cd $D
npm i three@0.160.0 && ln -s <repo>/src/main/resources/assets/pohsmp_core assets
python3 -m http.server 8123 &
node shoot.js shots.json <папка для png>      # Playwright, 1280×720
```
