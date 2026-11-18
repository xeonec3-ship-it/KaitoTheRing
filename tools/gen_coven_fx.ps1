# Рисует печать Ковена (1024) и ячейку решётки купола (128) для «Закрытия Пространства» (pohsmp_core).
# Белые линии на чёрном фоне (рисуются аддитивно, цвет даёт мод).
# Использование: tools\gen_coven_fx.ps1
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$root = Split-Path -Parent $PSScriptRoot
$fx = Join-Path $root 'mods-src\pohsmp_core\src\main\resources\assets\pohsmp_core\textures\fx'

function New-Canvas([int]$n) {
  $bmp = New-Object Drawing.Bitmap $n, $n, ([Drawing.Imaging.PixelFormat]::Format32bppArgb)
  $g = [Drawing.Graphics]::FromImage($bmp); $g.SmoothingMode = 'AntiAlias'
  $g.Clear([Drawing.Color]::FromArgb(255, 0, 0, 0)); return @($bmp, $g)
}
function Pen([double]$w, [int]$a = 255) { $p = New-Object Drawing.Pen ([Drawing.Color]::FromArgb(255, $a, $a, $a)), $w; $p.StartCap = 'Round'; $p.EndCap = 'Round'; $p.LineJoin = 'Round'; return $p }
function Circle($g, $p, [double]$cx, [double]$cy, [double]$r) { $g.DrawEllipse($p, [float]($cx - $r), [float]($cy - $r), [float](2 * $r), [float](2 * $r)) }
function Pt([double]$c, [double]$r, [double]$a) { New-Object Drawing.PointF ([float]($c + $r * [Math]::Cos($a))), ([float]($c + $r * [Math]::Sin($a))) }
function Poly($g, $p, [double]$c, [double]$r, [int]$n, [double]$rot, [int]$step = 1) {
  $pts = @(); $i = 0
  do { $pts += Pt $c $r ($rot + $i * 2 * [Math]::PI / $n); $i = ($i + $step) % $n } while ($i -ne 0)
  $pts += $pts[0]; $g.DrawLines($p, [Drawing.PointF[]]$pts)
}
function Runes($g, $p, [double]$c, [double]$r1, [double]$r2, [int]$n, [int]$seed) {
  $rng = New-Object Random $seed
  for ($i = 0; $i -lt $n; $i++) {
    $a = $i * 2 * [Math]::PI / $n; $state = $g.Save()
    $g.TranslateTransform([float]($c + ($r1 + $r2) / 2 * [Math]::Cos($a)), [float]($c + ($r1 + $r2) / 2 * [Math]::Sin($a)))
    $g.RotateTransform([float]($a * 180 / [Math]::PI + 90))
    $h = ($r2 - $r1) * 0.38; $w = $h * 0.7
    for ($j = 0; $j -lt $rng.Next(3, 6); $j++) {
      $x1 = ($rng.NextDouble() * 2 - 1) * $w; $y1 = ($rng.NextDouble() * 2 - 1) * $h
      if ($rng.Next(2) -eq 0) { $x2 = $x1; $y2 = ($rng.NextDouble() * 2 - 1) * $h } else { $x2 = ($rng.NextDouble() * 2 - 1) * $w; $y2 = $y1 }
      $g.DrawLine($p, [float]$x1, [float]$y1, [float]$x2, [float]$y2)
    }
    if ($rng.Next(3) -eq 0) { $g.DrawEllipse($p, [float](-$w * 0.35), [float](-$h * 0.35), [float]($w * 0.7), [float]($w * 0.7)) }
    $g.Restore($state)
  }
}
# Замок: дужка-арка и тело с замочной скважиной
function Lock($g, $p, [double]$x, [double]$y, [double]$s) {
  $g.DrawArc($p, [float]($x - $s * 0.55), [float]($y - $s * 1.25), [float]($s * 1.1), [float]($s * 1.3), 180, 180)
  $g.DrawLine($p, [float]($x - $s * 0.55), [float]($y - $s * 0.6), [float]($x - $s * 0.55), [float]($y - $s * 0.2))
  $g.DrawLine($p, [float]($x + $s * 0.55), [float]($y - $s * 0.6), [float]($x + $s * 0.55), [float]($y - $s * 0.2))
  $g.DrawRectangle($p, [float]($x - $s * 0.85), [float]($y - $s * 0.2), [float]($s * 1.7), [float]($s * 1.2))
  Circle $g $p $x ($y + $s * 0.2) ($s * 0.18)
  $g.DrawLine($p, [float]$x, [float]($y + $s * 0.35), [float]$x, [float]($y + $s * 0.7))
}
function Save($bmp, $g, $name) { $g.Dispose(); $bmp.Save((Join-Path $fx $name), [Drawing.Imaging.ImageFormat]::Png); $bmp.Dispose(); "  $name" }

# ---- Печать Ковена: два внешних кольца с засечками, пояс рун, гептаграмма {7/3} и {7/2}, 7 замков на вершинах,
#      второй пояс рун, квадрат в круге (замкнутое пространство), четыре цепи к центру, закрытые врата в центре ----
$N = 1024; $c = $N / 2; $PI = [Math]::PI
$bmp, $g = New-Canvas $N
Circle $g (Pen 10) $c $c 502; Circle $g (Pen 4) $c $c 488
for ($i = 0; $i -lt 112; $i++) { $a = $i * $PI / 56; $l = if ($i % 16 -eq 0) { 30 } elseif ($i % 2 -eq 0) { 16 } else { 9 }; $g.DrawLine((Pen 4), (Pt $c 488 $a), (Pt $c (488 - $l) $a)) }
Runes $g (Pen 5) $c 424 458 70 307
Circle $g (Pen 6) $c $c 422
Poly $g (Pen 6) $c 420 7 (-$PI / 2) 3
Poly $g (Pen 4) $c 420 7 (-$PI / 2) 2
Poly $g (Pen 3) $c 420 7 (-$PI / 2) 1
for ($i = 0; $i -lt 7; $i++) { $q = Pt $c 420 (-$PI / 2 + $i * 2 * $PI / 7); $g.FillEllipse([Drawing.Brushes]::Black, [float]($q.X - 36), [float]($q.Y - 36), 72, 72); Circle $g (Pen 5) $q.X $q.Y 34; Lock $g (Pen 4) $q.X ($q.Y + 4) 16 }
Circle $g (Pen 6) $c $c 290
Runes $g (Pen 4) $c 254 288 42 709
Circle $g (Pen 5) $c $c 252
Poly $g (Pen 6) $c 252 4 (-$PI / 4) 1
Poly $g (Pen 4) $c 252 4 0 1
Circle $g (Pen 4) $c $c 178
# цепи: звенья-овалы от квадрата к центру по четырём сторонам
for ($k = 0; $k -lt 4; $k++) {
  $a = $k * $PI / 2
  for ($j = 0; $j -lt 3; $j++) {
    $rr = 165 - $j * 26; $state = $g.Save()
    $g.TranslateTransform([float]($c + $rr * [Math]::Cos($a)), [float]($c + $rr * [Math]::Sin($a)))
    $g.RotateTransform([float]($a * 180 / $PI))
    if ($j % 2 -eq 0) { $g.DrawEllipse((Pen 4), -15, -7, 30, 14) } else { $g.DrawEllipse((Pen 4), -15, -4, 30, 8) }
    $g.Restore($state)
  }
}
# закрытые врата: арка с двумя створками и засовом
$g.DrawArc((Pen 7), [float]($c - 70), [float]($c - 110), 140, 120, 180, 180)
$g.DrawLine((Pen 7), [float]($c - 70), [float]($c - 50), [float]($c - 70), [float]($c + 80))
$g.DrawLine((Pen 7), [float]($c + 70), [float]($c - 50), [float]($c + 70), [float]($c + 80))
$g.DrawLine((Pen 7), [float]($c - 70), [float]($c + 80), [float]($c + 70), [float]($c + 80))
$g.DrawLine((Pen 5), [float]$c, [float]($c - 108), [float]$c, [float]($c + 80))
$g.DrawLine((Pen 9), [float]($c - 86), [float]($c + 10), [float]($c + 86), [float]($c + 10))
for ($i = 0; $i -lt 4; $i++) { Circle $g (Pen 3) ($c - 45 + ($i % 2) * 90) ($c - 30 + [Math]::Floor($i / 2) * 75) 6 }
Circle $g (Pen 4) $c $c 140
Save $bmp $g 'circle_coven.png'

# ---- Ячейка решётки купола 128: края по границе (соседние ячейки сходятся в сетку), шестиугольник, руна-точка в центре,
#      косые нити к углам. Тайлится, потому что всё по краю — половинной толщины. ----
$S = 128; $h = $S / 2
$bmp, $g = New-Canvas $S
$g.DrawRectangle((Pen 4 200), 0, 0, $S, $S)
Poly $g (Pen 3 230) $h 40 6 0 1
Poly $g (Pen 2 140) $h 26 6 ($PI / 6) 1
foreach ($k in 0..3) { $a = $PI / 4 + $k * $PI / 2; $g.DrawLine((Pen 2 110), (Pt $h 42 $a), (Pt $h 88 $a)) }
Circle $g (Pen 3 255) $h $h 7
$g.DrawLine((Pen 3 255), [float]$h, [float]($h - 16), [float]$h, [float]($h + 16))
$g.DrawLine((Pen 2 200), [float]($h - 10), [float]($h - 6), [float]($h + 10), [float]($h + 6))
Save $bmp $g 'dome_cell.png'
