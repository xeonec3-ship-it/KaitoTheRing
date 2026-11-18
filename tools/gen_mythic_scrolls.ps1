# Рисует свитки 32x32 для отдельных мифических заклинаний: Взрыв, Падение Небес, Застывший Час
# (pohsmp_core:item/scroll_<id>; мод подменяет модель свитка Iron's для этих заклинаний).
# Использование: tools\gen_mythic_scrolls.ps1 [папка_для_превью]
param([string]$Preview)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$root = Split-Path -Parent $PSScriptRoot
$tex = Join-Path $root 'mods-src\pohsmp_core\src\main\resources\assets\pohsmp_core\textures\item'
$mdl = Join-Path $root 'mods-src\pohsmp_core\src\main\resources\assets\pohsmp_core\models\item'
function C([string]$h) { [Drawing.ColorTranslator]::FromHtml('#' + $h) }
$N = 32

function New-Scroll($pal) {
  $script:px = @{}
  $script:left = @{}; $script:right = @{}
  for ($y = 7; $y -le 24; $y++) {
    $l = 8 + [int][Math]::Round([Math]::Sin($y * 0.7) * 0.6); $r = 23 + [int][Math]::Round([Math]::Sin($y * 0.7 + 1.5) * 0.6)
    $script:left[$y] = $l; $script:right[$y] = $r
    for ($x = $l; $x -le $r; $x++) {
      $t = ($x - $l) / [double]($r - $l)
      $c = if ($t -lt 0.12) { $pal.P3 } elseif ($t -lt 0.35) { $pal.P2 } elseif ($t -lt 0.8) { $pal.P1 } else { $pal.P2 }
      if ($y -le 8 -or $y -ge 23) { $c = $pal.P3 }
      if ((($x * 7 + $y * 13) % 17) -eq 0 -and $c -eq $pal.P1) { $c = $pal.P2 }
      Put $x $y $c
    }
    Put ($l - 1) $y $pal.O; Put ($r + 1) $y $pal.O; Put $l $y $pal.P4
  }
}
function Put($x, $y, $c) { $x = [int]$x; $y = [int]$y; if ($x -ge 0 -and $x -lt $N -and $y -ge 0 -and $y -lt $N) { $script:px[$y * 100 + $x] = $c } }
function Get-Px($x, $y) { $script:px[[int]$y * 100 + [int]$x] }
function InkRows($pal, $rows) {
  foreach ($ry in $rows) { $l = $script:left[$ry] + 3; $r = $script:right[$ry] - 2
    for ($x = $l; $x -le $r; $x++) { if ((($x * 5 + $ry * 3) % 7) -lt 4) { Put $x $ry $pal.INK } } }
}
function Roll($pal, $y0) {
  $rows = @($pal.MH, $pal.ML, $pal.MG, $pal.MD)
  for ($i = 0; $i -lt 4; $i++) { for ($x = 6; $x -le 25; $x++) { Put $x ($y0 + $i) $rows[$i] } }
  for ($x = 6; $x -le 25; $x++) { Put $x ($y0 - 1) $pal.O; Put $x ($y0 + 4) $pal.O }
  for ($x = 9; $x -le 22; $x += 4) { Put $x ($y0 + 1) $pal.MW }
  foreach ($kx in 3, 26) {
    for ($yy = $y0 - 1; $yy -le $y0 + 4; $yy++) { for ($xx = $kx; $xx -le $kx + 2; $xx++) { Put $xx $yy $pal.O } }
    Put ($kx + 1) $y0 $pal.G1; Put ($kx + 1) ($y0 + 1) $pal.G2; Put ($kx + 1) ($y0 + 2) $pal.G2; Put ($kx + 1) ($y0 + 3) $pal.G3
    Put $kx ($y0 + 1) $pal.MG; Put ($kx + 2) ($y0 + 1) $pal.MG; Put $kx ($y0 + 2) $pal.MD; Put ($kx + 2) ($y0 + 2) $pal.MD
  }
}
function Save-Scroll($name) {
  $bmp = New-Object Drawing.Bitmap $N, $N
  foreach ($k in $script:px.Keys) { $bmp.SetPixel([int]($k % 100), [int][Math]::Floor($k / 100), [Drawing.Color]$script:px[$k]) }
  $bmp.Save((Join-Path $tex "scroll_$name.png"), [Drawing.Imaging.ImageFormat]::Png)
  $json = "{`n  `"parent`": `"item/generated`",`n  `"textures`": {`n    `"layer0`": `"pohsmp_core:item/scroll_$name`"`n  }`n}`n"
  [IO.File]::WriteAllText((Join-Path $mdl "scroll_$name.json"), $json, (New-Object Text.UTF8Encoding $false))
  if ($Preview) {
    $big = New-Object Drawing.Bitmap 320, 320; $g = [Drawing.Graphics]::FromImage($big)
    $g.InterpolationMode = 'NearestNeighbor'; $g.PixelOffsetMode = 'Half'; $g.Clear((C '37373C')); $g.DrawImage($bmp, 0, 0, 320, 320); $g.Dispose()
    $big.Save((Join-Path $Preview "scroll_$name.png")); $big.Dispose()
  }
  $bmp.Dispose(); "  scroll_$name.png"
}
function Disc($cx, $cy, $r, $c) { for ($y = [int]($cy - $r - 1); $y -le [int]($cy + $r + 1); $y++) { for ($x = [int]($cx - $r - 1); $x -le [int]($cx + $r + 1); $x++) {
  if ([Math]::Sqrt(($x - $cx) * ($x - $cx) + ($y - $cy) * ($y - $cy)) -le $r) { Put $x $y $c } } } }
function RingPx($cx, $cy, $r, $w, $c) { for ($y = [int]($cy - $r - 1); $y -le [int]($cy + $r + 1); $y++) { for ($x = [int]($cx - $r - 1); $x -le [int]($cx + $r + 1); $x++) {
  if ([Math]::Abs([Math]::Sqrt(($x - $cx) * ($x - $cx) + ($y - $cy) * ($y - $cy)) - $r) -lt $w) { Put $x $y $c } } } }

# ---------- Взрыв: опалённый пергамент, тёмное железо с рубинами, восьмилучевая огненная звезда ----------
$p = @{ O = C '1E0C06'; P1 = C 'F2D7A4'; P2 = C 'E2B97A'; P3 = C 'C48A4E'; P4 = C '9A5E2C'; INK = C 'A4200E'
        MH = C '8C8A92'; ML = C '5E5C66'; MG = C '403E48'; MD = C '24222A'; MW = C 'FF9A3C'
        G1 = C 'FFB0A0'; G2 = C 'E8281A'; G3 = C '7A0A06' }
New-Scroll $p
InkRows $p @(10, 22)
# опалённые края
for ($y = 7; $y -le 24; $y++) { foreach ($x in $script:left[$y], ($script:left[$y] + 1), $script:right[$y], ($script:right[$y] - 1)) {
  if ((($x * 3 + $y * 5) % 4) -lt 2) { Put $x $y (C '5A2A10') } elseif ((($x + $y) % 5) -eq 0) { Put $x $y (C '2A1408') } } }
$cx = 15.5; $cy = 16.0
for ($i = 0; $i -lt 8; $i++) { $a = $i * [Math]::PI / 4; $len = if ($i % 2 -eq 0) { 6.4 } else { 4.6 }
  for ($s = 1.5; $s -le $len; $s += 0.35) { $c = if ($s -lt 2.8) { C 'FFE27A' } elseif ($s -lt 4.2) { C 'FF8A1E' } else { C 'D8260E' }
    Put ([int][Math]::Round($cx + [Math]::Cos($a) * $s - 0.5)) ([int][Math]::Round($cy + [Math]::Sin($a) * $s - 0.5)) $c } }
Disc $cx $cy 2.4 (C 'FFB43A'); Disc $cx $cy 1.5 (C 'FFF2B0'); Disc $cx $cy 0.7 (C 'FFFFFF')
foreach ($e in @(@(11, 12), @(20, 13), @(10, 19), @(21, 20), @(13, 21), @(18, 11))) { Put $e[0] $e[1] (C 'FF6A1A') }
Roll $p 4; Roll $p 24
Save-Scroll 'explosion'

# ---------- Падение Небес: пергамент с багряной печатью неба и тремя падающими метеорами ----------
$p = @{ O = C '2A0806'; P1 = C 'F6E2C0'; P2 = C 'E8C89A'; P3 = C 'D0A070'; P4 = C 'A87046'; INK = C '8A1A12'
        MH = C 'FFD27A'; ML = C 'E0A040'; MG = C 'B06A1E'; MD = C '6E3A0E'; MW = C 'FFF0C0'
        G1 = C 'FF9C8C'; G2 = C 'C8201A'; G3 = C '5E0806' }
New-Scroll $p
InkRows $p @(22)
# печать неба сверху
RingPx 15.5 10.6 3.4 0.55 (C 'B0301A')
RingPx 15.5 10.6 1.9 0.5 (C 'E05030')
Put 15 10 (C 'FFD27A'); Put 16 10 (C 'FFD27A')
for ($i = 0; $i -lt 6; $i++) { $a = $i * [Math]::PI / 3; Put ([int][Math]::Round(15.5 + [Math]::Cos($a) * 3.4 - 0.5)) ([int][Math]::Round(10.6 + [Math]::Sin($a) * 3.4 - 0.5)) (C 'FFE8A0') }
# метеоры: хвост вверх-вправо, голова внизу-слева
foreach ($m in @(@(13, 20, 5), @(18, 18, 4), @(21, 21, 3))) {
  $hx = $m[0]; $hy = $m[1]; $L = $m[2]
  for ($s = 1; $s -le $L; $s++) { $c = if ($s -le 1) { C 'FFC850' } elseif ($s -le 3) { C 'FF6A1E' } else { C 'C0301A' }
    Put ($hx + $s) ($hy - $s) $c; if ($s -lt $L) { Put ($hx + $s) ($hy - $s + 1) (C 'D8401A') } }
  Put $hx $hy (C 'FFFFFF'); Put ($hx - 1) $hy (C 'FFE27A'); Put $hx ($hy + 1) (C 'FFE27A'); Put ($hx - 1) ($hy + 1) (C 'FF9A30')
}
Roll $p 4; Roll $p 24
Save-Scroll 'heaven_fall'

# ---------- Застывший Час: инеевый пергамент, серебро с аметистами, циферблат с остановленными стрелками ----------
$p = @{ O = C '101830'; P1 = C 'EEF6FF'; P2 = C 'D6E6F8'; P3 = C 'B4C8E6'; P4 = C '8AA0C8'; INK = C '5A4AB0'
        MH = C 'FFFFFF'; ML = C 'D2DCEC'; MG = C 'A0AEC8'; MD = C '5E6A88'; MW = C 'BFE8FF'
        G1 = C 'E6C8FF'; G2 = C '9A5AF0'; G3 = C '4A1E90' }
New-Scroll $p
InkRows $p @(10, 22)
$cx = 15.5; $cy = 16.0
Disc $cx $cy 4.6 (C 'DCEEFF')
RingPx $cx $cy 4.6 0.6 (C '6A8CC8')
for ($i = 0; $i -lt 12; $i++) { $a = $i * [Math]::PI / 6; $rr = if ($i % 3 -eq 0) { 3.4 } else { 3.7 }
  $c = if ($i % 3 -eq 0) { C '3A2A90' } else { C '8AA8D8' }
  Put ([int][Math]::Round($cx + [Math]::Cos($a) * $rr - 0.5)) ([int][Math]::Round($cy + [Math]::Sin($a) * $rr - 0.5)) $c }
# стрелки: часовая вверх-влево, минутная вправо-вниз
foreach ($s in 0.6, 1.3, 2.0) { Put ([int][Math]::Round($cx - $s * 0.7 - 0.5)) ([int][Math]::Round($cy - $s - 0.5)) (C '7A3AE0') }
foreach ($s in 0.6, 1.3, 2.0, 2.7) { Put ([int][Math]::Round($cx + $s - 0.5)) ([int][Math]::Round($cy + $s * 0.4 - 0.5)) (C '9A5AF0') }
Put 15 15 (C 'FFFFFF'); Put 16 16 (C 'E6C8FF')
# иней по углам листа
foreach ($f in @(@(10, 9), @(21, 9), @(10, 22), @(21, 22))) { $fx = $f[0]; $fy = $f[1]
  Put $fx $fy (C 'FFFFFF'); Put ($fx - 1) $fy (C 'A8D8FF'); Put ($fx + 1) $fy (C 'A8D8FF'); Put $fx ($fy - 1) (C 'A8D8FF'); Put $fx ($fy + 1) (C 'A8D8FF') }
Roll $p 4; Roll $p 24
Save-Scroll 'frozen_hour'

# ---------- Закрытие Пространства: тёмно-лиловый пергамент, чёрное железо с аметистами, купол над чертой, внутри замок ----------
$p = @{ O = C '0C0618'; P1 = C 'E4DAF6'; P2 = C 'CDBFEA'; P3 = C 'A898D2'; P4 = C '7A68AE'; INK = C '4A2A9A'
        MH = C '6A6478'; ML = C '48425A'; MG = C '302A40'; MD = C '18141F'; MW = C 'B89CFF'
        G1 = C 'E6D2FF'; G2 = C '8A4CF0'; G3 = C '3A1680' }
New-Scroll $p
InkRows $p @(22)
$cx = 15.5; $cy = 18.5
# купол: полукольцо с ячейками и черта земли
for ($y = 10; $y -le 19; $y++) { for ($x = 9; $x -le 22; $x++) {
  $d = [Math]::Sqrt(($x + 0.5 - $cx - 0.5) * ($x + 0.5 - $cx - 0.5) + ($y + 0.5 - $cy) * ($y + 0.5 - $cy))
  if ($y + 0.5 -le $cy) {
    if ([Math]::Abs($d - 6.6) -lt 0.6) { Put $x $y (C '6A3AE0') }
    elseif ($d -lt 6.0 -and ((($x + $y) % 3) -eq 0)) { Put $x $y (C 'B8A2EE') } } } }
for ($x = 8; $x -le 23; $x++) { Put $x 19 (C '3A1E80') }
# замок в центре
Put 15 13 (C '2A1460'); Put 16 13 (C '2A1460'); Put 14 14 (C '2A1460'); Put 17 14 (C '2A1460')
for ($y = 15; $y -le 17; $y++) { for ($x = 14; $x -le 17; $x++) { Put $x $y (C 'FFFFFF') } }
Put 15 16 (C '3A1680'); Put 16 16 (C '3A1680'); Put 15 17 (C '8A4CF0')
# искры печати на вершине купола
Put 15 11 (C 'FFFFFF'); Put 16 11 (C 'E6D2FF'); Put 14 12 (C 'B89CFF'); Put 17 12 (C 'B89CFF')
Roll $p 4; Roll $p 24
Save-Scroll 'space_closure'
