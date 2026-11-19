# Рисует кольца-орбиты для объёмных («гироскопных») кругов pohsmp_core (1024x1024, белое на чёрном со свечением, цвет даёт мод):
# orbit_runes — пояс с рунами Футарка между двумя окружностями; orbit_dash — рваные дуги с треугольными метками;
# orbit_saw — пилообразная звезда-шестерня; orbit_stars — тонкое кольцо со звёздами и бусинами.
# Нужен готовый futhark.png (tools\gen_futhark.ps1). Использование: tools\gen_orbit_fx.ps1 [папка_превью]
param([string]$Preview)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$root = Split-Path -Parent $PSScriptRoot
$fx = Join-Path $root 'mods-src\pohsmp_core\src\main\resources\assets\pohsmp_core\textures\fx'
$S = 1024; $C = $S / 2.0; $PI = [Math]::PI
$rng = New-Object Random 4242
$futhark = [Drawing.Image]::FromFile((Join-Path $fx 'futhark.png'))

function Layer { $b = New-Object Drawing.Bitmap $S, $S, ([Drawing.Imaging.PixelFormat]::Format32bppArgb)
  $g = [Drawing.Graphics]::FromImage($b); $g.SmoothingMode = 'AntiAlias'; $g.Clear([Drawing.Color]::Transparent); return @($b, $g) }
function WPen([double]$w, [int]$a = 255) { $p = New-Object Drawing.Pen ([Drawing.Color]::FromArgb($a, 255, 255, 255)), $w
  $p.StartCap = 'Round'; $p.EndCap = 'Round'; $p.LineJoin = 'Round'; return $p }
function Circ($g, [double]$r, [double]$w, [int]$a = 255) { $g.DrawEllipse((WPen $w $a), [float]($C - $r), [float]($C - $r), [float](2 * $r), [float](2 * $r)) }
function Arc($g, [double]$r, [double]$a0, [double]$sweep, [double]$w) {   # углы в градусах
  $g.DrawArc((WPen $w), [float]($C - $r), [float]($C - $r), [float](2 * $r), [float](2 * $r), [float]$a0, [float]$sweep) }
function P([double]$r, [double]$a) { New-Object Drawing.PointF ([float]($C + [Math]::Cos($a) * $r)), ([float]($C + [Math]::Sin($a) * $r)) }
function Tri($g, [double]$r, [double]$a, [double]$s, [bool]$out) {   # треугольник остриём наружу/внутрь
  $d = if ($out) { 1 } else { -1 }
  $pts = [Drawing.PointF[]]@((P ($r + $d * $s) $a), (P ($r - $d * $s * 0.5) ($a - $s / $r)), (P ($r - $d * $s * 0.5) ($a + $s / $r)))
  $g.FillPolygon([Drawing.Brushes]::White, $pts) }
function Star4($g, [double]$x, [double]$y, [double]$s) {
  $pts = [Drawing.PointF[]]@(); for ($i = 0; $i -lt 8; $i++) { $a = $i * $PI / 4 - $PI / 2; $rr = if ($i % 2 -eq 0) { $s } else { $s * 0.22 }
    $pts += New-Object Drawing.PointF ([float]($x + [Math]::Cos($a) * $rr)), ([float]($y + [Math]::Sin($a) * $rr)) }
  $g.FillPolygon([Drawing.Brushes]::White, $pts) }
function Dot($g, [double]$x, [double]$y, [double]$r) { $g.FillEllipse([Drawing.Brushes]::White, [float]($x - $r), [float]($y - $r), [float](2 * $r), [float](2 * $r)) }

# Свечение: копии слоя, уменьшенные в 4 и 12 раз и растянутые обратно (размытие), под самим слоем на чёрном
function Blur($src, [int]$div) {
  $w = [int]($S / $div); $sm = New-Object Drawing.Bitmap $w, $w, ([Drawing.Imaging.PixelFormat]::Format32bppArgb)
  $g = [Drawing.Graphics]::FromImage($sm); $g.InterpolationMode = 'HighQualityBicubic'; $g.DrawImage($src, 0, 0, $w, $w); $g.Dispose()
  $big = New-Object Drawing.Bitmap $S, $S, ([Drawing.Imaging.PixelFormat]::Format32bppArgb)
  $g = [Drawing.Graphics]::FromImage($big); $g.InterpolationMode = 'HighQualityBicubic'; $g.PixelOffsetMode = 'Half'; $g.DrawImage($sm, 0, 0, $S, $S); $g.Dispose(); $sm.Dispose()
  return $big }
function Finish($b, $g, $name) {
  $g.Dispose()
  $out = New-Object Drawing.Bitmap $S, $S, ([Drawing.Imaging.PixelFormat]::Format32bppArgb)
  $o = [Drawing.Graphics]::FromImage($out); $o.Clear([Drawing.Color]::Black)
  foreach ($k in @(@(14, 1.0), @(5, 0.9))) {
    $bl = Blur $b $k[0]
    $cm = New-Object Drawing.Imaging.ColorMatrix; $cm.Matrix33 = [float]$k[1]
    $ia = New-Object Drawing.Imaging.ImageAttributes; $ia.SetColorMatrix($cm)
    for ($rep = 0; $rep -lt 2; $rep++) { $o.DrawImage($bl, (New-Object Drawing.Rectangle 0, 0, $S, $S), 0, 0, $S, $S, 'Pixel', $ia) }
    $bl.Dispose() }
  $o.DrawImage($b, 0, 0, $S, $S); $o.Dispose(); $b.Dispose()
  $out.Save((Join-Path $fx "$name.png"), [Drawing.Imaging.ImageFormat]::Png)
  if ($Preview) { $out.Save((Join-Path $Preview "$name.png")) }
  $out.Dispose(); "  $name.png" }

# ---- пояс рун ----
# атлас чёрный с белым: при вставке яркость -> прозрачность, цвет белый
$cmR = New-Object Drawing.Imaging.ColorMatrix
$cmR.Matrix00 = 0; $cmR.Matrix11 = 0; $cmR.Matrix22 = 0; $cmR.Matrix33 = 0; $cmR.Matrix03 = 1; $cmR.Matrix40 = 1; $cmR.Matrix41 = 1; $cmR.Matrix42 = 1
$runeIA = New-Object Drawing.Imaging.ImageAttributes; $runeIA.SetColorMatrix($cmR)
$b, $g = Layer
Circ $g 500 7; Circ $g 488 2.5; Circ $g 400 2.5; Circ $g 388 7
$n = 36
for ($i = 0; $i -lt $n; $i++) {
  $a = $i * 2 * $PI / $n; $ri = $rng.Next(24)
  $st = $g.Save()
  $g.TranslateTransform([float]($C + [Math]::Cos($a) * 444), [float]($C + [Math]::Sin($a) * 444))
  $g.RotateTransform([float]($a * 180 / $PI + 90))
  $src = New-Object Drawing.Rectangle (($ri % 6) * 128 + 18), ([Math]::Floor($ri / 6) * 128 + 18), 92, 92
  $g.DrawImage($futhark, (New-Object Drawing.Rectangle -38, -38, 76, 76), $src.X, $src.Y, $src.Width, $src.Height, 'Pixel', $runeIA)
  $g.Restore($st)
  $g.DrawLine((WPen 2.5), (P 400 ($a + $PI / $n)), (P 488 ($a + $PI / $n)))
}
for ($i = 0; $i -lt 120; $i++) { $a = $i * 2 * $PI / 120; $l = if ($i % 5 -eq 0) { 22 } else { 10 }; $g.DrawLine((WPen 2.5), (P 378 $a), (P (378 - $l) $a)) }
Finish $b $g 'orbit_runes'

# ---- рваные дуги ----
$b, $g = Layer
$a = 0.0
while ($a -lt 360) { $len = 8 + $rng.Next(46); if ($a + $len -gt 356) { $len = 356 - $a }; if ($len -gt 2) { Arc $g 490 $a $len 13 }; $a += $len + 5 + $rng.Next(12) }
$a = 0.0
while ($a -lt 360) { $len = 20 + $rng.Next(80); if ($a + $len -gt 358) { $len = 358 - $a }; if ($len -gt 2) { Arc $g 455 $a $len 4 }; $a += $len + 10 + $rng.Next(30) }
Circ $g 430 2.5
for ($i = 0; $i -lt 6; $i++) { $t = $i * 2 * $PI / 6 + 0.3 + 0.25 * $rng.NextDouble(); Tri $g 470 $t 24 ($i % 2 -eq 0) }
for ($i = 0; $i -lt 3; $i++) { $t = $i * 2 * $PI / 3 + 1.0; Tri $g 412 $t 16 $false }
Finish $b $g 'orbit_dash'

# ---- пила-шестерня ----
$b, $g = Layer
$teeth = 48; $pts = [Drawing.PointF[]]@()
for ($i = 0; $i -le 2 * $teeth; $i++) { $pts += P $(if ($i % 2 -eq 0) { 500 } else { 430 }) ($i * $PI / $teeth) }
$g.DrawLines((WPen 6), $pts)
$pts = [Drawing.PointF[]]@()
for ($i = 0; $i -le 2 * $teeth; $i++) { $pts += P $(if ($i % 2 -eq 0) { 440 } else { 470 }) ($i * $PI / $teeth + $PI / $teeth) }
$g.DrawLines((WPen 2.5), $pts)
Circ $g 420 6; Circ $g 405 2.5
for ($i = 0; $i -lt 12; $i++) { $t = $i * $PI / 6; Dot $g (($C + [Math]::Cos($t) * 390)) (($C + [Math]::Sin($t) * 390)) 6 }
Finish $b $g 'orbit_saw'

# ---- звёздное кольцо с бусинами ----
$b, $g = Layer
Circ $g 492 4; Circ $g 470 2
for ($i = 0; $i -lt 5; $i++) { $t = $i * 2 * $PI / 5 + 0.4; $q = P 481 $t; Star4 $g $q.X $q.Y 30; Dot $g $q.X $q.Y 9 }
for ($i = 0; $i -lt 40; $i++) { $t = $rng.NextDouble() * 2 * $PI; $q = P (481 + ($rng.NextDouble() - 0.5) * 30) $t; Dot $g $q.X $q.Y (1.5 + 2.5 * $rng.NextDouble()) }
for ($i = 0; $i -lt 16; $i++) { $t = $i * 2 * $PI / 16 + 0.15; $q = P 492 $t; $g.DrawEllipse((WPen 3), [float]($q.X - 10), [float]($q.Y - 10), 20, 20) }
Finish $b $g 'orbit_stars'
$futhark.Dispose()
