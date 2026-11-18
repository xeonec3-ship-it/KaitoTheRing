# Печати: формат JSON

Черновик схемы для системы печатей из [`specs/sigils_spec.md`](specs/sigils_spec.md). Схема проверена 3D-превью
`tools/sigil_preview.html`: оно читает эти же файлы и считает тайминги так, как должен считать мод.
При расхождении с заданием верным считается это описание: оно уточняет задание.

- Файлы печатей: `assets/pohsmp_core/sigils/<id>.json`.
- Текстуры: `assets/pohsmp_core/textures/sigil/<name>.png`, белое на прозрачном (цвет задаётся в JSON).
  Генератор — `tools/gen_sigil_textures.py`.
- Время везде в **тиках** (20 в секунду), углы в **градусах**, размеры в **блоках**.

## Печать

```json
{
  "size": 3.0,
  "color": "#8FF3FF",
  "orientation": "sky",
  "lifetime": -1,
  "hold": 120,
  "layers": [ … ],
  "expand": { "scale": 4.0, "delay": 4, "duration": 20, "easing": "easeOutCubic" },
  "formedFlash": { "color": "#FFFFFF", "size": 1.25, "duration": 12, "sparks": 40 },
  "onFormed": [ … ],
  "dissolve": { "modes": ["reverse", "collapse"], "duration": 20, "stagger": 3 }
}
```

| Поле | Что это |
|---|---|
| `size` | радиус печати в блоках. Радиусы слоёв — доли от него |
| `color` | цвет по умолчанию для всех слоёв (`#RRGGBB`) |
| `orientation` | `ground` — лежит на земле лицом вверх; `sky` — висит лицом вниз; `facing` — вертикально, смотрит туда же, куда кастер; `billboard` — всегда к камере |
| `lifetime` | сколько тиков живёт печать всего; `-1` — пока её не остановят |
| `hold` | сколько тиков держать после формирования, потом разборка; `-1` — держать, пока не остановят |
| `layers` | слои, см. ниже. Порядок важен: разборка `reverse` гасит их с конца |
| `expand` | рост всей печати после появления слоёв: множитель `scale`, задержка, длительность, плавность |
| `formedFlash` | вспышка в момент формирования: кольцо-волна до `size` (доля размера печати), свечение, `sparks` искр |
| `onFormed` | дочерние печати, которые появляются в момент формирования |
| `dissolve` | разборка: режимы `modes`, длительность, `stagger` — шаг между слоями для `reverse` |

## Тайминги (как считать «сформирована»)

```
layersEnd   = max по слоям (appear.delay + appear.duration)
expandStart = layersEnd + expand.delay            (если expand нет — layersEnd)
formedAt    = expandStart + expand.duration        (если expand нет — layersEnd)
```

В `formedAt`: вспышка, дочерние печати, серверный колбэк «печать сформирована» (заклинание может бить ровно после формирования).
Разборка начинается в `formedAt + hold` или по команде.

## Слой

```json
{ "id": "runes", "type": "band", "texture": "rune_band", "radius": 0.86, "inner": 0.86, "repeat": 6,
  "heightOffset": 0.03, "color": "#…", "brightness": 1.0,
  "appear": { "delay": 34, "duration": 10, "easing": "easeInOutSine", "modes": ["draw"], "startAngle": 90, "direction": 1 },
  "rotation": { "speed": 12, "boost": 2.0 },
  "pulse": { "amp": 0.2, "period": 30 } }
```

| Поле | Что это |
|---|---|
| `type` | `disc` — квадрат с текстурой (круг); `band` — кольцевая лента, текстура повторяется по окружности `repeat` раз, от `inner`·r до r; `arcs` — `count` разорванных дуг длиной `arcLength`° и толщиной `width` (доля радиуса); `spokes` — как `disc`, для текстур с лучами |
| `texture` | имя текстуры без `.png` |
| `radius` | радиус слоя, доля `size` |
| `heightOffset` | смещение вдоль нормали в блоках, чтобы слои не мерцали друг в друге (по 0.01 на слой) |
| `color`, `brightness` | свой цвет слоя и множитель яркости (по умолчанию цвет печати и 1) |
| `appear.delay`, `duration`, `easing` | когда и как долго слой появляется, плавность |
| `appear.modes` | можно сочетать: `grow` — масштаб 0→1; `fade` — прозрачность 0→1; `draw` — прорисовка по углу 0→360° от `startAngle` (`direction` 1 или −1); `twist` — доворот на `appear.twist`° к нулю; `unfold` — разворот из «ребром к камере» в плоскость; `assemble` — только для `arcs`: дуги стартуют дальше от центра, с разных углов, и смыкаются в кольцо |
| `rotation.speed` | вращение, °/с (знак — направление); `boost` — во столько раз быстрее, пока слой появляется (плавно затухает к концу появления) |
| `pulse` | пульсация яркости: амплитуда (доля) и период в тиках |

### Как считать слой в момент `t` (тики от старта печати)

```
p     = clamp((t - delay) / duration, 0, 1);   e = easing(p)
scale = grow ? e : 1
alpha = fade ? e : (t >= delay ? 1 : 0)
angle = ∫ speed * (1 + boost * (1 - e)) dt  + (twist ? appear.twist * (1 - e) : 0)
tilt  = unfold ? 90° * (1 - e) : 0                    (поворот вокруг оси X плоскости)
draw  = 360° * e                                       (рисуется сектор/лента до этого угла)
arcs (assemble): радиус ×(1 + 0.9·(1 - e)), длина дуги = arcLength + (360/count − arcLength)·e,
                 сдвиг каждой дуги ±150°·(1 − e) (чётные в одну сторону, нечётные в другую)
pulse: alpha *= 1 + amp * sin(2π t / period)
печать целиком: scale *= 1 + (expand.scale − 1) · easing((t − expandStart) / expand.duration)
```

Плавности: `linear`, `easeInSine`, `easeOutSine`, `easeInOutSine`, `easeInCubic`, `easeOutCubic`, `easeInOutCubic`, `easeOutBack`.

## Разборка

`dissolve.modes` можно сочетать (`d` — доля от 0 до 1 за `duration`):

| Режим | Что делает |
|---|---|
| `reverse` | слои гаснут с последнего к первому, каждый следующий на `stagger` тиков позже |
| `collapse` | вся печать сжимается в точку: масштаб × (1 − easeInCubic(d)) |
| `fade` | вся печать гаснет: прозрачность × (1 − d) |
| `shatter` | слои разлетаются наружу: масштаб × (1 + 0.8·d), гаснут |

Остановка родителя останавливает и его дочерние печати.

## Дочерние печати

```json
"onFormed": [
  { "id": "golden_halo", "anchor": "caster",
    "arc": { "count": 6, "radius": 1.5, "angle": 150, "height": 1.55, "behind": true, "stagger": 3 } }
]
```

- `anchor`: `caster` — вокруг кастера, иначе — вокруг центра печати.
- `arc`: `count` штук на дуге радиусом `radius` блоков, раствор `angle`°, на высоте `height`; `behind` — дуга за спиной
  (иначе перед кастером); каждая следующая появляется на `stagger` тиков позже.
- Без `arc` дочерняя печать появляется в центре родителя.

## Демо-печати

| id | Что |
|---|---|
| `silent_gate_sky` | небесная: 4 дуги смыкаются → свечение → ядро → спирали → кольцо рун прорисовывается → обод; рост ×4; разборка `reverse`+`collapse` |
| `silent_gate_ground` | земная под кастером: свечение, спирали и ядро с доворотом, руны прорисовываются пером, обод; после формирования — 6 золотых кругов дугой за спиной |
| `golden_halo` | маленький золотой круг, раскрывается разворотом из ребра; дочерний |
| `coven_seal` | печать Ковена: гексаграмма прорисовывается, руны в обратную сторону, рост ×2.5 (для «Появления Ковена» и «Закрытия Пространства») |

## Код (готово в чате идей)

Чистая логика без Minecraft — пакет `ru.pohsmp.core.fx.sigil`:

- `SigilDef` — определение печати и разбор JSON (`SigilDef.parse(id, json)`), только Gson.
- `SigilTimeline` — всё, что зависит от времени: `timings` (`formedAt`), `autoStopAt`, `globalScale`, `globalAlpha`,
  `layer(def, i, t, stopAt)` → альфа, масштаб, угол, наклон, доля прорисовки, параметры дуг; `finished`.
- `Easing` — плавности по именам из JSON.
- Тесты: `src/test/java/.../SigilTimelineTest.java` (`gradlew test`), проверяют демо-печати и формулы этого документа.

Отрисовщику в игре остаётся только рисовать то, что возвращает `SigilTimeline`, а серверу — брать `timings().formedAt()`
для колбэка «печать сформирована».

## Как добавить новую печать

1. Если нужна новая текстура — добавить функцию в `tools/gen_sigil_textures.py` и запустить его.
2. Создать `assets/pohsmp_core/sigils/<id>.json` по этой схеме (проще всего скопировать похожую демо-печать).
3. Запустить `python3 tools/build_sigil_preview.py` и посмотреть печать в `tools/sigil_preview.html`
   (добавить сцену в `SCENES` шаблона, если нужна своя).
4. В игре: `/pohsmp sigil reload`, затем `/pohsmp sigil play <id>`.
