# Рисует знаки школ Iron's (512x512) для кругов обычной магии pohsmp_core и круг-оберег Восьми щитов.
# Белые линии на чёрном (аддитивно, цвет даёт мод). Использование: tools\gen_school_sigils.ps1 [папка_превью]
param([string]$Preview)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$root = Split-Path -Parent $PSScriptRoot
$fx = Join-Path $root 'mods-src\pohsmp_core\src\main\resources\assets\pohsmp_core\textures\fx'
$PI = [Math]::PI; $N = 512; $c = 256.0

function New-Canvas { $b = New-Object Drawing.Bitmap $N, $N, ([Drawing.Imaging.PixelFormat]::Format32bppArgb); $g = [Drawing.Graphics]::FromImage($b); $g.SmoothingMode = 'AntiAlias'; $g.Clear([Drawing.Color]::Black); return @($b, $g) }
function Pen([double]$w, [int]$a = 255) { $p = New-Object Drawing.Pen ([Drawing.Color]::FromArgb(255, $a, $a, $a)), $w; $p.StartCap = 'Round'; $p.EndCap = 'Round'; $p.LineJoin = 'Round'; return $p }
function Br([int]$a = 255) { New-Object Drawing.SolidBrush ([Drawing.Color]::FromArgb(255, $a, $a, $a)) }
function P([double]$r, [double]$a) { New-Object Drawing.PointF ([float]($c + $r * [Math]::Cos($a))), ([float]($c + $r * [Math]::Sin($a))) }
function Ring($g, $p, [double]$r) { $g.DrawEllipse($p, [float]($c - $r), [float]($c - $r), [float](2 * $r), [float](2 * $r)) }
function RingAt($g, $p, [double]$x, [double]$y, [double]$r) { $g.DrawEllipse($p, [float]($x - $r), [float]($y - $r), [float](2 * $r), [float](2 * $r)) }
function Poly($g, $p, [double]$r, [int]$n, [double]$rot, [int]$step = 1) {
  $pts = @(); $i = 0; do { $pts += P $r ($rot + $i * 2 * $PI / $n); $i = ($i + $step) % $n } while ($i -ne 0); $pts += $pts[0]; $g.DrawLines($p, [Drawing.PointF[]]$pts) }
function Ticks($g, $p, [double]$r, [int]$n, [double]$l) { for ($i = 0; $i -lt $n; $i++) { $a = $i * 2 * $PI / $n; $g.DrawLine($p, (P $r $a), (P ($r - $l) $a)) } }
function Runes($g, $p, [double]$r1, [double]$r2, [int]$n, [int]$seed) {
  $rng = New-Object Random $seed
  for ($i = 0; $i -lt $n; $i++) { $a = $i * 2 * $PI / $n; $st = $g.Save()
    $g.TranslateTransform([float]($c + ($r1 + $r2) / 2 * [Math]::Cos($a)), [float]($c + ($r1 + $r2) / 2 * [Math]::Sin($a))); $g.RotateTransform([float]($a * 180 / $PI + 90))
    $h = ($r2 - $r1) * 0.38; $w = $h * 0.7
    for ($j = 0; $j -lt $rng.Next(3, 6); $j++) { $x1 = ($rng.NextDouble() * 2 - 1) * $w; $y1 = ($rng.NextDouble() * 2 - 1) * $h
      if ($rng.Next(2) -eq 0) { $x2 = $x1; $y2 = ($rng.NextDouble() * 2 - 1) * $h } else { $x2 = ($rng.NextDouble() * 2 - 1) * $w; $y2 = $y1 }
      $g.DrawLine($p, [float]$x1, [float]$y1, [float]$x2, [float]$y2) }
    $g.Restore($st) } }
# Общая рамка: двойное кольцо, засечки, пояс рун
function Frame($g, [int]$seed, [int]$ticks = 72) { Ring $g (Pen 7) 248; Ring $g (Pen 3) 236; Ticks $g (Pen 3) 236 $ticks 10; Runes $g (Pen 3.5) 196 224 36 $seed; Ring $g (Pen 4) 194 }
function Save($b, $g, $name) {
  $g.Dispose(); $b.Save((Join-Path $fx "$name.png"), [Drawing.Imaging.ImageFormat]::Png)
  if ($Preview) { $s = New-Object Drawing.Bitmap 256, 256; $gg = [Drawing.Graphics]::FromImage($s); $gg.DrawImage($b, 0, 0, 256, 256); $gg.Dispose(); $s.Save((Join-Path $Preview "$name.png")); $s.Dispose() }
  $b.Dispose(); "  $name.png" }
# Лист / язык пламени / капля: замкнутая фигура вдоль оси a от r1 до r2 шириной w
function Leaf($g, $p, [double]$r1, [double]$r2, [double]$a, [double]$w) {
  $p1 = P $r1 $a; $p2 = P $r2 $a; $m = ($r1 + $r2) / 2; $dx = -[Math]::Sin($a) * $w; $dy = [Math]::Cos($a) * $w
  $q = P $m $a; $c1 = New-Object Drawing.PointF ([float]($q.X + $dx)), ([float]($q.Y + $dy)); $c2 = New-Object Drawing.PointF ([float]($q.X - $dx)), ([float]($q.Y - $dy))
  $g.DrawBezier($p, $p1, $c1, $c1, $p2); $g.DrawBezier($p, $p1, $c2, $c2, $p2) }

# ---- огонь: языки пламени по кругу, треугольник огня, малые угольки ----
$b, $g = New-Canvas; Frame $g 11
for ($i = 0; $i -lt 12; $i++) { $a = $i * $PI / 6; Leaf $g (Pen 4) 120 188 ($a + 0.12) 16; Leaf $g (Pen 2.5) 132 170 ($a + 0.12) 7 }
Ring $g (Pen 4) 118
Poly $g (Pen 6) 112 3 (-$PI / 2)
Poly $g (Pen 3) 112 3 ($PI / 2)
$g.DrawLine((Pen 4), (P 56 (-$PI / 2 + 2 * $PI / 3)), (P 56 (-$PI / 2 + 4 * $PI / 3)))
Ring $g (Pen 5) 34; $g.FillEllipse((Br), [float]($c - 14), [float]($c - 14), 28, 28)
Save $b $g 'sigil_fire'

# ---- лёд: снежинка с ветвями, шестиугольники ----
$b, $g = New-Canvas; Frame $g 12
Poly $g (Pen 4) 186 6 0; Poly $g (Pen 3) 150 6 ($PI / 6)
for ($i = 0; $i -lt 6; $i++) { $a = $i * $PI / 3
  $g.DrawLine((Pen 6), (P 20 $a), (P 182 $a))
  foreach ($r in 70, 115, 155) { $q = P $r $a; $len = 190 - $r; $len = [Math]::Min(42, $len * 0.6)
    foreach ($s in -1, 1) { $b2 = $a + $s * $PI / 4; $g.DrawLine((Pen 4), $q, (New-Object Drawing.PointF ([float]($q.X + [Math]::Cos($b2) * $len)), ([float]($q.Y + [Math]::Sin($b2) * $len)))) } } }
Poly $g (Pen 5) 46 6 0; Ring $g (Pen 3) 22
Save $b $g 'sigil_ice'

# ---- молния: зигзаги-разряды по кругу, четыре стрелы, центр-звезда ----
$b, $g = New-Canvas; Frame $g 13 96
for ($i = 0; $i -lt 8; $i++) { $a = $i * $PI / 4 + $PI / 8
  $pts = @((P 186 $a), (P 160 ($a + 0.09)), (P 140 ($a - 0.07)), (P 116 ($a + 0.08)), (P 92 ($a - 0.05)))
  $g.DrawLines((Pen 5), [Drawing.PointF[]]$pts) }
Ring $g (Pen 3) 92
for ($i = 0; $i -lt 4; $i++) { $a = $i * $PI / 2
  $g.DrawLines((Pen 6), [Drawing.PointF[]]@((P 182 $a), (P 128 ($a + 0.14)), (P 132 ($a - 0.1)), (P 70 $a))) }
Poly $g (Pen 4) 64 8 0 3
Ring $g (Pen 4) 26
Save $b $g 'sigil_lightning'

# ---- природа: венок из листьев, пятиугольник, росток в центре ----
$b, $g = New-Canvas; Frame $g 14
Ring $g (Pen 3) 160
for ($i = 0; $i -lt 20; $i++) { $a = $i * 2 * $PI / 20; $q = P 160 $a
  $t = $a + $PI / 2 + 0.6; $e = New-Object Drawing.PointF ([float]($q.X + [Math]::Cos($t) * 30)), ([float]($q.Y + [Math]::Sin($t) * 30))
  $nx = -[Math]::Sin($t) * 9; $ny = [Math]::Cos($t) * 9; $m = New-Object Drawing.PointF ([float](($q.X + $e.X) / 2)), ([float](($q.Y + $e.Y) / 2))
  $g.DrawBezier((Pen 3), $q, (New-Object Drawing.PointF ([float]($m.X + $nx)), ([float]($m.Y + $ny))), (New-Object Drawing.PointF ([float]($m.X + $nx)), ([float]($m.Y + $ny))), $e)
  $g.DrawBezier((Pen 3), $q, (New-Object Drawing.PointF ([float]($m.X - $nx)), ([float]($m.Y - $ny))), (New-Object Drawing.PointF ([float]($m.X - $nx)), ([float]($m.Y - $ny))), $e) }
Poly $g (Pen 5) 124 5 (-$PI / 2) 2; Poly $g (Pen 3) 124 5 (-$PI / 2)
for ($i = 0; $i -lt 3; $i++) { Leaf $g (Pen 4) 8 58 (-$PI / 2 + ($i - 1) * 0.75) 16 }
Save $b $g 'sigil_nature'

# ---- свет: солнце с длинными и короткими лучами, крест, ореол ----
$b, $g = New-Canvas; Frame $g 15 48
for ($i = 0; $i -lt 32; $i++) { $a = $i * $PI / 16; $l = if ($i % 4 -eq 0) { 182 } elseif ($i % 2 -eq 0) { 150 } else { 128 }; $g.DrawLine((Pen ($(if ($i % 4 -eq 0) { 6 } else { 3 }))), (P 76 $a), (P $l $a)) }
Ring $g (Pen 5) 72; Ring $g (Pen 2.5) 60
$g.DrawLine((Pen 7), (P 54 (-$PI / 2)), (P 54 ($PI / 2))); $g.DrawLine((Pen 7), (P 36 $PI), (P 36 0))
Ring $g (Pen 3) 186
Save $b $g 'sigil_holy'

# ---- кровь: капли по кругу, шипы, полумесяц ----
$b, $g = New-Canvas; Frame $g 16
for ($i = 0; $i -lt 9; $i++) { $a = $i * 2 * $PI / 9 - $PI / 2; $q = P 158 $a
  $g.DrawBezier((Pen 4), (P 186 $a), (P 160 ($a + 0.14)), (P 140 ($a + 0.1)), (P 140 $a)); $g.DrawBezier((Pen 4), (P 186 $a), (P 160 ($a - 0.14)), (P 140 ($a - 0.1)), (P 140 $a)) }
Ring $g (Pen 4) 132
for ($i = 0; $i -lt 18; $i++) { $a = $i * $PI / 9; $g.DrawLines((Pen 3), [Drawing.PointF[]]@((P 132 ($a - 0.06)), (P 112 $a), (P 132 ($a + 0.06)))) }
$g.DrawArc((Pen 7), [float]($c - 70), [float]($c - 70), 140, 140, 120, 300)
$g.DrawArc((Pen 5), [float]($c - 40), [float]($c - 62), 120, 124, 150, 240)
RingAt $g (Pen 4) $c $c 14
Save $b $g 'sigil_blood'

# ---- Край: око в восьмиугольнике, звёзды, точки ----
$b, $g = New-Canvas; Frame $g 17
Poly $g (Pen 5) 184 8 ($PI / 8); Poly $g (Pen 3) 184 8 ($PI / 8) 3
for ($i = 0; $i -lt 8; $i++) { $q = P 150 ($i * $PI / 4); RingAt $g (Pen 3) $q.X $q.Y 8; $g.FillEllipse((Br), [float]($q.X - 3), [float]($q.Y - 3), 6, 6) }
$g.DrawBezier((Pen 6), [float]($c - 110), [float]$c, [float]($c - 40), [float]($c - 70), [float]($c + 40), [float]($c - 70), [float]($c + 110), [float]$c)
$g.DrawBezier((Pen 6), [float]($c - 110), [float]$c, [float]($c - 40), [float]($c + 70), [float]($c + 40), [float]($c + 70), [float]($c + 110), [float]$c)
Ring $g (Pen 5) 34; $g.DrawEllipse((Pen 4), [float]($c - 8), [float]($c - 30), 16, 60)
Save $b $g 'sigil_ender'

# ---- воплощение: квадраты, вписанные круги, геометрия ----
$b, $g = New-Canvas; Frame $g 18
Poly $g (Pen 5) 190 4 ($PI / 4); Poly $g (Pen 5) 190 4 0
Ring $g (Pen 4) 134; Poly $g (Pen 4) 134 4 ($PI / 4); Ring $g (Pen 3) 95; Poly $g (Pen 4) 95 4 0
for ($i = 0; $i -lt 8; $i++) { $q = P 162 ($i * $PI / 4 + $PI / 8); RingAt $g (Pen 3) $q.X $q.Y 12 }
Runes $g (Pen 2.5) 98 130 16 81
Ring $g (Pen 4) 40; Poly $g (Pen 3) 40 3 (-$PI / 2); Poly $g (Pen 3) 40 3 ($PI / 2)
Save $b $g 'sigil_evocation'

# ---- потустороннее: семиконечная звезда, щупальца-спирали, око ----
$b, $g = New-Canvas; Frame $g 19
Poly $g (Pen 5) 188 7 (-$PI / 2) 3
for ($i = 0; $i -lt 7; $i++) { $a = $i * 2 * $PI / 7 - $PI / 2
  $pts = @(); for ($s = 0; $s -le 20; $s++) { $t = $s / 20.0; $pts += P (40 + 110 * $t) ($a + $PI / 7 + 0.9 * $t * $t) }; $g.DrawCurve((Pen (5 - 0)), [Drawing.PointF[]]$pts) }
Ring $g (Pen 4) 60
$g.DrawEllipse((Pen 5), [float]($c - 36), [float]($c - 20), 72, 40); $g.FillEllipse((Br), [float]($c - 10), [float]($c - 10), 20, 20)
Save $b $g 'sigil_eldritch'

# ---- ветер: трискель из спиралей, дуги-вихри ----
$b, $g = New-Canvas; Frame $g 20
for ($i = 0; $i -lt 3; $i++) { $a0 = $i * 2 * $PI / 3
  $pts = @(); for ($s = 0; $s -le 40; $s++) { $t = $s / 40.0; $pts += P (10 + 170 * $t) ($a0 + 2.6 * $t) }; $g.DrawCurve((Pen 6), [Drawing.PointF[]]$pts)
  $pts = @(); for ($s = 0; $s -le 30; $s++) { $t = $s / 30.0; $pts += P (30 + 120 * $t) ($a0 + 0.5 + 2.2 * $t) }; $g.DrawCurve((Pen 3), [Drawing.PointF[]]$pts) }
for ($i = 0; $i -lt 6; $i++) { $g.DrawArc((Pen 3), [float]($c - 186), [float]($c - 186), 372, 372, [float]($i * 60 + 10), 34) }
Ring $g (Pen 4) 22
Save $b $g 'sigil_wind'

# ---- оберег Восьми щитов: восьмиугольник из щитов-гербов, внутренний круг ----
$b, $g = New-Canvas; Frame $g 21 64
Poly $g (Pen 6) 186 8 ($PI / 8)
for ($i = 0; $i -lt 8; $i++) { $a = $i * $PI / 4; $q = P 150 $a; $st = $g.Save()
  $g.TranslateTransform($q.X, $q.Y); $g.RotateTransform([float]($a * 180 / $PI + 90))
  $sh = [Drawing.PointF[]]@((New-Object Drawing.PointF -18, -20), (New-Object Drawing.PointF 18, -20), (New-Object Drawing.PointF 18, 2), (New-Object Drawing.PointF 0, 24), (New-Object Drawing.PointF -18, 2), (New-Object Drawing.PointF -18, -20))
  $g.DrawLines((Pen 4), $sh); $g.DrawLine((Pen 3), 0, -14, 0, 14); $g.DrawLine((Pen 3), -10, -4, 10, -4); $g.Restore($st) }
Ring $g (Pen 4) 112; Poly $g (Pen 3) 108 8 0 3; Ring $g (Pen 3) 52; Poly $g (Pen 4) 50 4 ($PI / 4)
Save $b $g 'circle_ward'
