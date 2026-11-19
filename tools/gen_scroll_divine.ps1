# Рисует текстуру Божественного свитка 32x32 (pohsmp_core:item/scroll_divine): пергамент, золотые валики с камнями,
# магический круг с сиянием в центре, строки рун. Использование: tools\gen_scroll_divine.ps1 [путь_для_превью.png]
param([string]$Preview)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$root = Split-Path -Parent $PSScriptRoot
$out = Join-Path $root 'mods-src\pohsmp_core\src\main\resources\assets\pohsmp_core\textures\item\scroll_divine.png'
function C($r, $g, $b) { [Drawing.Color]::FromArgb(255, $r, $g, $b) }
$kO = C 62 34 8; $kD = C 140 86 18; $kG = C 205 148 38; $kL = C 242 200 88; $kH = C 255 236 160
$kP1 = C 252 236 178; $kP2 = C 240 214 140; $kP3 = C 222 186 108; $kP4 = C 192 146 72
$kW = C 255 255 248; $kY = C 255 244 190; $kINK = C 176 112 22
$kB1 = C 150 220 255; $kB2 = C 70 150 235; $kB3 = C 30 80 170
$N = 32; $bmp = New-Object Drawing.Bitmap $N, $N
$px = @{}
function Put($x, $y, $c) { $x = [int]$x; $y = [int]$y; if ($x -ge 0 -and $x -lt $N -and $y -ge 0 -and $y -lt $N) { $script:px[$y * 100 + $x] = $c } }

# лист: x 8..23, y 7..24, края слегка волнистые
$left = @{}; $right = @{}
for ($y = 7; $y -le 24; $y++) {
  $l = 8 + [int][Math]::Round([Math]::Sin($y * 0.7) * 0.6); $r = 23 + [int][Math]::Round([Math]::Sin($y * 0.7 + 1.5) * 0.6)
  $left[$y] = $l; $right[$y] = $r
  for ($x = $l; $x -le $r; $x++) {
    $t = ($x - $l) / [double]($r - $l)
    $c = if ($t -lt 0.12) { $kP3 } elseif ($t -lt 0.35) { $kP2 } elseif ($t -lt 0.8) { $kP1 } else { $kP2 }
    if ($y -le 8 -or $y -ge 23) { $c = $kP3 }
    if ((($x * 7 + $y * 13) % 17) -eq 0 -and $c -eq $kP1) { $c = $kP2 }
    Put $x $y $c
  }
  Put ($l - 1) $y $kO; Put ($r + 1) $y $kO
  Put $l $y $kP4
}
# строки рун сверху и снизу
foreach ($ry in 10, 12, 21) {
  $l = $left[$ry] + 3; $r = $right[$ry] - 2
  for ($x = $l; $x -le $r; $x++) { if ((($x * 5 + $ry * 3) % 7) -lt 4) { Put $x $ry $kINK } }
}
# магический круг в центре
$cx = 15.5; $cy = 16.0
for ($y = 11; $y -le 21; $y++) { for ($x = 10; $x -le 21; $x++) {
  $d = [Math]::Sqrt(($x - $cx) * ($x - $cx) + ($y - $cy) * ($y - $cy))
  if ([Math]::Abs($d - 4.4) -lt 0.55) { Put $x $y $kG }
  elseif ($d -lt 1.2) { Put $x $y $kW }
  elseif ($d -lt 2.2) { Put $x $y $kY }
} }
foreach ($a in 0, 1, 2, 3) { $ang = $a * [Math]::PI / 2 + [Math]::PI / 4
  Put ([int][Math]::Round($cx + [Math]::Cos($ang) * 3.0 - 0.5)) ([int][Math]::Round($cy + [Math]::Sin($ang) * 3.0 - 0.5)) $kL }
foreach ($a in 0, 1, 2, 3) { $ang = $a * [Math]::PI / 2
  Put ([int][Math]::Round($cx + [Math]::Cos($ang) * 4.4 - 0.5)) ([int][Math]::Round($cy + [Math]::Sin($ang) * 4.4 - 0.5)) $kW }

# валики: верхний y 4..7, нижний y 24..27, x 6..25
function Roll($y0) {
  $rows = @($kH, $kL, $kG, $kD)
  for ($i = 0; $i -lt 4; $i++) { for ($x = 6; $x -le 25; $x++) { Put $x ($y0 + $i) $rows[$i] } }
  for ($x = 6; $x -le 25; $x++) { Put $x ($y0 - 1) $kO; Put $x ($y0 + 4) $kO }
  Put 25 ($y0 + 1) $kW; Put 24 ($y0 + 2) $kL; Put 25 ($y0 + 2) $kD
  for ($x = 9; $x -le 22; $x += 4) { Put $x ($y0 + 1) $kW }
  # навершия с камнями
  foreach ($kx in 3, 26) {
    for ($yy = $y0 - 1; $yy -le $y0 + 4; $yy++) { for ($xx = $kx; $xx -le $kx + 2; $xx++) { Put $xx $yy $kO } }
    Put ($kx + 1) $y0 $kB1; Put ($kx + 1) ($y0 + 1) $kB2; Put ($kx + 1) ($y0 + 2) $kB2; Put ($kx + 1) ($y0 + 3) $kB3
    Put $kx ($y0 + 1) $kG; Put ($kx + 2) ($y0 + 1) $kG; Put $kx ($y0 + 2) $kD; Put ($kx + 2) ($y0 + 2) $kD
  }
}
Roll 4
Roll 24

foreach ($k in $px.Keys) { $bmp.SetPixel([int]($k % 100), [int][Math]::Floor($k / 100), [Drawing.Color]$px[$k]) }
New-Item -ItemType Directory -Force (Split-Path $out) | Out-Null
$bmp.Save($out, [Drawing.Imaging.ImageFormat]::Png)
if ($Preview) {
  $big = New-Object Drawing.Bitmap 320, 320; $g = [Drawing.Graphics]::FromImage($big)
  $g.InterpolationMode = 'NearestNeighbor'; $g.PixelOffsetMode = 'Half'; $g.Clear((C 55 55 60)); $g.DrawImage($bmp, 0, 0, 320, 320); $g.Dispose()
  $big.Save($Preview); $big.Dispose()
}
$bmp.Dispose()
"scroll_divine.png 32x32"
