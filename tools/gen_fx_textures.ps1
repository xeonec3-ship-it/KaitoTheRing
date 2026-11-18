# Рисует текстуры эффектов мода pohsmp_core: магические круги, вспышку, луч, иконку заклинания и иконку школы.
# Круги, вспышка и луч - белые линии на ЧЁРНОМ непрозрачном фоне (рисуются аддитивно, чёрное = ничего); цвет даёт мод.
# Использование: tools\gen_fx_textures.ps1
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$root = Split-Path -Parent $PSScriptRoot
$fx = Join-Path $root 'mods-src\pohsmp_core\src\main\resources\assets\pohsmp_core\textures\fx'
$icons = Join-Path $root 'mods-src\pohsmp_core\src\main\resources\assets\pohsmp_core\textures\gui\spell_icons'
New-Item -ItemType Directory -Force $fx, $icons | Out-Null

function New-Canvas([int]$n) {
  $bmp = New-Object Drawing.Bitmap $n, $n, ([Drawing.Imaging.PixelFormat]::Format32bppArgb)
  $g = [Drawing.Graphics]::FromImage($bmp)
  $g.SmoothingMode = 'AntiAlias'
  $g.Clear([Drawing.Color]::FromArgb(255, 0, 0, 0))
  return @($bmp, $g)
}
function Pen([double]$w, [int]$a = 255) { $p = New-Object Drawing.Pen ([Drawing.Color]::FromArgb(255, $a, $a, $a)), $w; $p.StartCap = 'Round'; $p.EndCap = 'Round'; $p.LineJoin = 'Round'; return $p }
function Circle($g, $p, [double]$c, [double]$r) { $g.DrawEllipse($p, [float]($c - $r), [float]($c - $r), [float](2 * $r), [float](2 * $r)) }
function Pt([double]$c, [double]$r, [double]$a) { New-Object Drawing.PointF ([float]($c + $r * [Math]::Cos($a))), ([float]($c + $r * [Math]::Sin($a))) }
function Poly($g, $p, [double]$c, [double]$r, [int]$n, [double]$rot, [int]$step = 1) {
  $pts = @(); $i = 0
  do { $pts += Pt $c $r ($rot + $i * 2 * [Math]::PI / $n); $i = ($i + $step) % $n } while ($i -ne 0)
  $pts += $pts[0]
  $g.DrawLines($p, [Drawing.PointF[]]$pts)
}
# Руны: короткие штрихи в полосе между r1 и r2, повёрнутые по касательной
function Runes($g, $p, [double]$c, [double]$r1, [double]$r2, [int]$n, [int]$seed) {
  $rng = New-Object Random $seed
  for ($i = 0; $i -lt $n; $i++) {
    $a = $i * 2 * [Math]::PI / $n
    $state = $g.Save()
    $g.TranslateTransform([float]($c + ($r1 + $r2) / 2 * [Math]::Cos($a)), [float]($c + ($r1 + $r2) / 2 * [Math]::Sin($a)))
    $g.RotateTransform([float]($a * 180 / [Math]::PI + 90))
    $h = ($r2 - $r1) * 0.38; $w = $h * 0.7
    $k = $rng.Next(3, 6)
    for ($j = 0; $j -lt $k; $j++) {
      $x1 = ($rng.NextDouble() * 2 - 1) * $w; $y1 = ($rng.NextDouble() * 2 - 1) * $h
      if ($rng.Next(2) -eq 0) { $x2 = $x1; $y2 = ($rng.NextDouble() * 2 - 1) * $h } else { $x2 = ($rng.NextDouble() * 2 - 1) * $w; $y2 = $y1 }
      $g.DrawLine($p, [float]$x1, [float]$y1, [float]$x2, [float]$y2)
    }
    if ($rng.Next(3) -eq 0) { $g.DrawEllipse($p, [float](-$w * 0.35), [float](-$h * 0.35), [float]($w * 0.7), [float]($w * 0.7)) }
    $g.Restore($state)
  }
}
function Save($bmp, $g, $name, $dir = $fx) { $g.Dispose(); $bmp.Save((Join-Path $dir $name), [Drawing.Imaging.ImageFormat]::Png); $bmp.Dispose(); "  $name" }

$N = 512; $c = $N / 2

# Круг A: двойное кольцо, полоса рун, гексаграмма, внутренние кольца
$bmp, $g = New-Canvas $N
Circle $g (Pen 6) $c 248; Circle $g (Pen 3) $c 236
Runes $g (Pen 3.5) $c 200 234 40 7
Circle $g (Pen 4) $c 198
Poly $g (Pen 4) $c 196 6 (-[Math]::PI / 2) 2
Poly $g (Pen 4) $c 196 6 (-[Math]::PI / 2 + [Math]::PI / 3) 2
Poly $g (Pen 3) $c 196 6 (-[Math]::PI / 2) 1
Circle $g (Pen 3) $c 112
Runes $g (Pen 2.5) $c 82 110 20 11
Circle $g (Pen 3) $c 80
Poly $g (Pen 3) $c 78 4 0 1
Poly $g (Pen 3) $c 78 4 ([Math]::PI / 4) 1
Circle $g (Pen 4) $c 22
for ($i = 0; $i -lt 6; $i++) { $q = Pt $c 196 (-[Math]::PI / 2 + $i * [Math]::PI / 3); $g.DrawEllipse((Pen 3), [float]($q.X - 14), [float]($q.Y - 14), 28, 28) }
Save $bmp $g 'circle_a.png'

# Круг B: кольца с засечками, восьмиугольная звезда, малые круги по окружности, спицы
$bmp, $g = New-Canvas $N
Circle $g (Pen 5) $c 246
for ($i = 0; $i -lt 72; $i++) { $a = $i * [Math]::PI / 36; $l = if ($i % 6 -eq 0) { 22 } else { 10 }; $p1 = Pt $c 246 $a; $p2 = Pt $c (246 - $l) $a; $g.DrawLine((Pen 3), $p1, $p2) }
Circle $g (Pen 3) $c 214
Poly $g (Pen 4) $c 212 8 0 3
Circle $g (Pen 3) $c 150
for ($i = 0; $i -lt 8; $i++) { $q = Pt $c 180 ($i * [Math]::PI / 4 + [Math]::PI / 8); $g.DrawEllipse((Pen 3), [float]($q.X - 16), [float]($q.Y - 16), 32, 32) }
Runes $g (Pen 2.5) $c 118 148 24 23
Circle $g (Pen 3) $c 116
Poly $g (Pen 3) $c 114 3 (-[Math]::PI / 2) 1
Poly $g (Pen 3) $c 114 3 ([Math]::PI / 2) 1
for ($i = 0; $i -lt 12; $i++) { $a = $i * [Math]::PI / 6; $g.DrawLine((Pen 2), (Pt $c 30 $a), (Pt $c 58 $a)) }
Circle $g (Pen 4) $c 30
Save $bmp $g 'circle_b.png'

# Вспышка: радиальный градиент
$M = 128; $bmp = New-Object Drawing.Bitmap $M, $M
for ($y = 0; $y -lt $M; $y++) { for ($x = 0; $x -lt $M; $x++) {
  $d = [Math]::Sqrt([Math]::Pow(($x - $M / 2 + 0.5) / ($M / 2), 2) + [Math]::Pow(($y - $M / 2 + 0.5) / ($M / 2), 2))
  $v = [Math]::Max(0, 1 - $d); $v = [int](255 * [Math]::Pow($v, 1.8))
  $bmp.SetPixel($x, $y, [Drawing.Color]::FromArgb(255, $v, $v, $v)) } }
$bmp.Save((Join-Path $fx 'flare.png'), [Drawing.Imaging.ImageFormat]::Png); $bmp.Dispose(); "  flare.png"

# Луч: яркий центр по ширине, по длине ровно
$W = 64; $bmp = New-Object Drawing.Bitmap $W, $W
for ($x = 0; $x -lt $W; $x++) {
  $d = [Math]::Abs(($x + 0.5) / $W * 2 - 1); $v = [int](255 * [Math]::Pow([Math]::Max(0, 1 - $d), 1.5))
  for ($y = 0; $y -lt $W; $y++) { $bmp.SetPixel($x, $y, [Drawing.Color]::FromArgb(255, $v, $v, $v)) } }
$bmp.Save((Join-Path $fx 'beam.png'), [Drawing.Imaging.ImageFormat]::Png); $bmp.Dispose(); "  beam.png"

# Иконка заклинания 16x16 (рисуется как обычная картинка с прозрачностью): золотой круг, белая сердцевина, лучи
function Icon16([string]$path, [string]$bgHex) {
  $bmp = New-Object Drawing.Bitmap 16, 16
  $gold = [Drawing.ColorTranslator]::FromHtml('#FFD34D'); $dark = [Drawing.ColorTranslator]::FromHtml('#B8862B'); $white = [Drawing.Color]::White
  $bg = [Drawing.ColorTranslator]::FromHtml($bgHex); $bg2 = [Drawing.ColorTranslator]::FromHtml('#2A1F45')
  for ($y = 0; $y -lt 16; $y++) { for ($x = 0; $x -lt 16; $x++) {
    $dx = $x - 7.5; $dy = $y - 7.5; $d = [Math]::Sqrt($dx * $dx + $dy * $dy)
    $col = if ($d -lt 7.6) { if (($x + $y) % 2 -eq 0) { $bg } else { $bg2 } } else { [Drawing.Color]::Transparent }
    if ($d -ge 6.2 -and $d -lt 7.4) { $col = $gold }
    if ($d -ge 4.3 -and $d -lt 5.1) { $col = $dark }
    if (($x -eq 7 -or $x -eq 8) -and $d -lt 6.2) { $col = $dark }
    if (($y -eq 7 -or $y -eq 8) -and $d -lt 6.2) { $col = $dark }
    if ($d -lt 2.6) { $col = $gold }
    if ($d -lt 1.5) { $col = $white }
    $bmp.SetPixel($x, $y, $col) } }
  $bmp.Save($path, [Drawing.Imaging.ImageFormat]::Png); $bmp.Dispose()
}
Icon16 (Join-Path $icons 'disintegration.png') '#120C24'; "  spell_icons/disintegration.png"

# Значок эффекта «Отдача божественной магии» 18x18: золотое кольцо с трещиной, белая искра в центре
$eff = Join-Path $root 'mods-src\pohsmp_core\src\main\resources\assets\pohsmp_core\textures\mob_effect'
New-Item -ItemType Directory -Force $eff | Out-Null
$bmp = New-Object Drawing.Bitmap 18, 18
$gold = [Drawing.ColorTranslator]::FromHtml('#FFD34D'); $dk = [Drawing.ColorTranslator]::FromHtml('#9A6514'); $ol = [Drawing.ColorTranslator]::FromHtml('#3E2208'); $wh = [Drawing.Color]::White; $pale = [Drawing.ColorTranslator]::FromHtml('#FFF2B8')
for ($y = 0; $y -lt 18; $y++) { for ($x = 0; $x -lt 18; $x++) {
  $dx = $x - 8.5; $dy = $y - 8.5; $d = [Math]::Sqrt($dx * $dx + $dy * $dy); $a = [Math]::Atan2($dy, $dx)
  $col = [Drawing.Color]::Transparent
  if ($d -ge 7.4 -and $d -lt 8.5) { $col = $ol }
  if ($d -ge 5.4 -and $d -lt 7.4) { $col = if ($dy -lt 0) { $gold } else { $dk } }
  if ($d -ge 4.6 -and $d -lt 5.4) { $col = $ol }
  # трещина: клин справа сверху
  if ($d -ge 4.6 -and $d -lt 8.5 -and [Math]::Abs($a + 0.75) -lt (0.10 + 0.04 * (8.5 - $d))) { $col = [Drawing.Color]::Transparent }
  if ($d -lt 2.2) { $col = $pale }
  if ($d -lt 1.2) { $col = $wh }
  if (($x -eq 8 -or $x -eq 9) -and $d -lt 3.6 -and $d -ge 2.2) { $col = $pale }
  if (($y -eq 8 -or $y -eq 9) -and $d -lt 3.6 -and $d -ge 2.2) { $col = $pale }
  $bmp.SetPixel($x, $y, $col) } }
$bmp.Save((Join-Path $eff 'divine_backlash.png'), [Drawing.Imaging.ImageFormat]::Png); $bmp.Dispose(); "  mob_effect/divine_backlash.png"
