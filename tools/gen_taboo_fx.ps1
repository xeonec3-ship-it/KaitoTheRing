# Рисует круг Божественного Табу (1024) и руну-печать запрета (128) для pohsmp_core.
# Белые линии на чёрном непрозрачном фоне (рисуются аддитивно, цвет даёт мод).
# Использование: tools\gen_taboo_fx.ps1
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
# Знак запрета: кружок с косой чертой
function Forbid($g, $p, [double]$x, [double]$y, [double]$r) {
  Circle $g $p $x $y $r
  $d = $r * 0.7071; $g.DrawLine($p, [float]($x - $d), [float]($y - $d), [float]($x + $d), [float]($y + $d))
}
function Save($bmp, $g, $name) { $g.Dispose(); $bmp.Save((Join-Path $fx $name), [Drawing.Imaging.ImageFormat]::Png); $bmp.Dispose(); "  $name" }

# ---- Круг Табу: внешние кольца с засечками, руны, октаграмма, 8 знаков запрета, второй пояс рун, гексаграмма, лучи, закрытое Око ----
$N = 1024; $c = $N / 2; $PI = [Math]::PI
$bmp, $g = New-Canvas $N
Circle $g (Pen 10) $c $c 502; Circle $g (Pen 4) $c $c 486
for ($i = 0; $i -lt 96; $i++) { $a = $i * $PI / 48; $l = if ($i % 8 -eq 0) { 26 } else { 12 }; $g.DrawLine((Pen 4), (Pt $c 486 $a), (Pt $c (486 - $l) $a)) }
Runes $g (Pen 5) $c 420 456 64 101
Circle $g (Pen 6) $c $c 418
Poly $g (Pen 6) $c 416 4 (-$PI / 2) 1
Poly $g (Pen 6) $c 416 4 (-$PI / 4) 1
Poly $g (Pen 4) $c 416 8 (-$PI / 2) 1
for ($i = 0; $i -lt 8; $i++) { $q = Pt $c 360 (-$PI / 2 + $PI / 8 + $i * $PI / 4); Forbid $g (Pen 5) $q.X $q.Y 30 }
Circle $g (Pen 6) $c $c 300
Runes $g (Pen 4) $c 262 298 40 202
Circle $g (Pen 5) $c $c 260
Poly $g (Pen 5) $c 256 6 (-$PI / 2) 2
Poly $g (Pen 5) $c 256 6 ($PI / 2) 2
Circle $g (Pen 5) $c $c 150
for ($i = 0; $i -lt 24; $i++) { $a = $i * $PI / 12; $l = if ($i % 2 -eq 0) { 60 } else { 34 }; $g.DrawLine((Pen 4), (Pt $c 154 $a), (Pt $c (154 + $l) $a)) }
# закрытое Око: две дуги, ресницы вниз, перечёркнуто
$g.DrawArc((Pen 7), [float]($c - 110), [float]($c - 70), 220, 140, 200, 140)
$g.DrawArc((Pen 7), [float]($c - 110), [float]($c - 70), 220, 140, 20, 140)
$g.DrawArc((Pen 5), [float]($c - 100), [float]($c - 50), 200, 110, 25, 130)
for ($i = 0; $i -lt 7; $i++) { $x = $c - 66 + $i * 22; $y = $c + 52 - [Math]::Abs($i - 3) * 6; $g.DrawLine((Pen 4), [float]$x, [float]$y, [float]($x + ($i - 3) * 4), [float]($y + 22)) }
$g.DrawLine((Pen 8), [float]($c - 118), [float]($c - 118), [float]($c + 118), [float]($c + 118))
Circle $g (Pen 4) $c $c 128
Save $bmp $g 'circle_taboo.png'

# ---- Руна-печать запрета 128: кольцо, ромб, замочная скважина, две перекладины ----
$RS = 128; $rc = $RS / 2
$bmp, $g = New-Canvas $RS
Circle $g (Pen 5) $rc $rc 58
Circle $g (Pen 2.5) $rc $rc 50
Poly $g (Pen 3.5) $rc 46 4 (-$PI / 2) 1
Circle $g (Pen 4) $rc ($rc - 8) 9
$g.DrawLine((Pen 4), [float]($rc - 4), [float]($rc), [float]($rc - 8), [float]($rc + 22))
$g.DrawLine((Pen 4), [float]($rc + 4), [float]($rc), [float]($rc + 8), [float]($rc + 22))
$g.DrawLine((Pen 4), [float]($rc - 8), [float]($rc + 22), [float]($rc + 8), [float]($rc + 22))
$g.DrawLine((Pen 3.5), [float]($rc - 34), [float]($rc - 26), [float]($rc + 34), [float]($rc - 26))
$g.DrawLine((Pen 3.5), [float]($rc - 34), [float]($rc + 32), [float]($rc + 34), [float]($rc + 32))
for ($i = 0; $i -lt 4; $i++) { $q = Pt $rc 50 ($i * $PI / 2 + $PI / 4); Circle $g (Pen 3) $q.X $q.Y 5 }
Save $bmp $g 'rune_taboo.png'
