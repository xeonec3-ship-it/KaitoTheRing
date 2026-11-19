# Текстуры элементов эффектов (docs/fx.md): strip_soft (лента/молния/разрез), chain_link (звено цепи), wing (крыло света),
# aura_shell (оболочка ауры), sound_ring (звуковое кольцо скалка), slash_crack (трещины от разреза).
# Белое на прозрачном: цвет задаёт эффект. Рисуется в 4 раза крупнее и уменьшается — края гладкие. Свои рисунки, не чужие ассеты.
# Использование: powershell -File tools\gen_fx_elements.ps1
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$root = Split-Path -Parent $PSScriptRoot
$out = Join-Path $root 'src\main\resources\assets\pohsmp_core\textures\fx'
New-Item -ItemType Directory -Force $out | Out-Null
$SS = 4

function New-Big([int]$w, [int]$h) {
  $bmp = New-Object Drawing.Bitmap ($w * $SS), ($h * $SS), ([Drawing.Imaging.PixelFormat]::Format32bppArgb)
  $g = [Drawing.Graphics]::FromImage($bmp)
  $g.SmoothingMode = 'AntiAlias'
  $g.Clear([Drawing.Color]::FromArgb(0, 255, 255, 255))
  return @($bmp, $g)
}
function Brush([int]$a) { New-Object Drawing.SolidBrush ([Drawing.Color]::FromArgb($a, 255, 255, 255)) }
function Pen([double]$w, [int]$a = 255) { $p = New-Object Drawing.Pen ([Drawing.Color]::FromArgb($a, 255, 255, 255)), ([float]($w * $SS)); $p.StartCap = 'Round'; $p.EndCap = 'Round'; $p.LineJoin = 'Round'; return $p }
function P([double]$x, [double]$y) { New-Object Drawing.PointF ([float]($x * $SS)), ([float]($y * $SS)) }
function Save-Small($bmp, $g, [string]$name, [int]$w, [int]$h) {
  $g.Dispose()
  $small = New-Object Drawing.Bitmap $w, $h, ([Drawing.Imaging.PixelFormat]::Format32bppArgb)
  $s = [Drawing.Graphics]::FromImage($small)
  $s.InterpolationMode = 'HighQualityBicubic'
  $s.CompositingMode = 'SourceCopy'
  $s.DrawImage($bmp, 0, 0, $w, $h)
  $s.Dispose(); $bmp.Dispose()
  $small.Save((Join-Path $out "$name.png"), [Drawing.Imaging.ImageFormat]::Png); $small.Dispose()
  "  $name.png"
}
# Картинка по функции альфы a(x, y) в 0..1, x и y в 0..1 (для мягких градиентов без сверхвыборки)
function Save-Field([string]$name, [int]$w, [int]$h, [scriptblock]$fn) {
  $bmp = New-Object Drawing.Bitmap $w, $h, ([Drawing.Imaging.PixelFormat]::Format32bppArgb)
  for ($y = 0; $y -lt $h; $y++) {
    for ($x = 0; $x -lt $w; $x++) {
      $a = & $fn (($x + 0.5) / $w) (($y + 0.5) / $h)
      $a = [Math]::Max(0.0, [Math]::Min(1.0, [double]$a))
      $bmp.SetPixel($x, $y, [Drawing.Color]::FromArgb([int]($a * 255), 255, 255, 255))
    }
  }
  $bmp.Save((Join-Path $out "$name.png"), [Drawing.Imaging.ImageFormat]::Png); $bmp.Dispose()
  "  $name.png"
}

# strip_soft: профиль поперёк (u) — горячее узкое ядро и мягкий ореол; вдоль (v) одинаково. Для лент, молний, разрезов.
Save-Field 'strip_soft' 64 16 { param($u, $v)
  $d = [Math]::Abs($u * 2 - 1)
  0.55 * [Math]::Exp(-$d * $d * 9) + 0.45 * [Math]::Exp(-$d * $d * 60) }

# aura_shell: полый овал — светлая кайма по краю, пусто внутри, мягко наружу. Ставится billboard'ом на фигуру сущности.
Save-Field 'aura_shell' 64 128 { param($u, $v)
  $x = $u * 2 - 1; $y = $v * 2 - 1
  $r = [Math]::Sqrt($x * $x + $y * $y)
  $edge = [Math]::Exp(-[Math]::Pow(($r - 0.78) / 0.13, 2))
  $inner = 0.18 * [Math]::Max(0.0, 1 - $r / 0.8)
  ($edge + $inner) * (0.75 + 0.25 * (1 - $v)) }

# sound_ring: звуковое кольцо — три тонкие концентрические дуги с разрывами (как волны эха).
$bmp, $g = New-Big 256 256
$c = 128
foreach ($k in 0..2) {
  $r = 118 - $k * 14; $w = 5 - $k * 1.3; $al = 255 - $k * 60
  for ($s = 0; $s -lt 6; $s++) {
    $a0 = $s * 60 + 8 + $k * 17; $sw = 44 - $k * 6
    $g.DrawArc((Pen $w $al), [float](($c - $r) * $SS), [float](($c - $r) * $SS), [float](2 * $r * $SS), [float](2 * $r * $SS), [float]$a0, [float]$sw)
  }
}
Save-Small $bmp $g 'sound_ring' 256 256

# chain_link: одно звено — вытянутый овал-рамка с бликом на ребре (повёрнуто вдоль v).
$bmp, $g = New-Big 64 128
$g.DrawEllipse((Pen 9), [float](12 * $SS), [float](6 * $SS), [float](40 * $SS), [float](116 * $SS))
$g.DrawArc((Pen 3 255), [float](18 * $SS), [float](12 * $SS), [float](28 * $SS), [float](104 * $SS), 200, 70)
Save-Small $bmp $g 'chain_link' 64 128

# wing: крыло света. Корень (шарнир) в точке (16, 150) из 256 — uv (0.06, 0.59); кость дугой вверх-вправо,
# перья свисают с кости веером: у корня короткие и вниз, к концу длинные и наружу. Три ряда: маховые (тусклее), второстепенные, кроющие (ярче).
$bmp, $g = New-Big 256 256
$rng = New-Object Random 11
function Bone([double]$t) { $u = 1 - $t; @(($u * $u * 16 + 2 * $u * $t * 80 + $t * $t * 205), ($u * $u * 150 + 2 * $u * $t * 18 + $t * $t * 30)) }
function Feather($g, [double]$t, [double]$len, [double]$wd, [int]$al) {
  $b = Bone $t
  $ang = (105 - 38 * $t) * [Math]::PI / 180
  $L = $len * (0.95 + 0.1 * $rng.NextDouble())
  $tx = $b[0] + $L * [Math]::Cos($ang); $ty = $b[1] + $L * [Math]::Sin($ang)
  $nx = -[Math]::Sin($ang); $ny = [Math]::Cos($ang)
  $m1x = $b[0] + ($tx - $b[0]) * 0.35; $m1y = $b[1] + ($ty - $b[1]) * 0.35
  $m2x = $b[0] + ($tx - $b[0]) * 0.8; $m2y = $b[1] + ($ty - $b[1]) * 0.8
  $pts = [Drawing.PointF[]]@((P $b[0] $b[1]), (P ($m1x + $nx * $wd) ($m1y + $ny * $wd)), (P ($m2x + $nx * $wd * 0.8) ($m2y + $ny * $wd * 0.8)),
    (P $tx $ty), (P ($m2x - $nx * $wd * 0.5) ($m2y - $ny * $wd * 0.5)), (P ($m1x - $nx * $wd * 0.6) ($m1y - $ny * $wd * 0.6)))
  $g.FillClosedCurve((Brush ([int]($al * 0.5))), $pts, 'Alternate', 0.5)
  $g.DrawClosedCurve((Pen 1.6 $al), $pts, 0.5, 'Alternate')
  $g.DrawLine((Pen 1.4 $al), (P $b[0] $b[1]), (P ($b[0] + ($tx - $b[0]) * 0.9) ($b[1] + ($ty - $b[1]) * 0.9)))
}
for ($i = 0; $i -lt 12; $i++) { $t = 0.08 + 0.92 * $i / 11; Feather $g $t (55 + 70 * [Math]::Pow($t, 0.8)) 9 150 }
for ($i = 0; $i -lt 10; $i++) { $t = 0.05 + 0.85 * $i / 9; Feather $g $t (34 + 40 * $t) 8 200 }
for ($i = 0; $i -lt 9; $i++) { $t = 0.03 + 0.8 * $i / 8; Feather $g $t (16 + 18 * $t) 7 255 }
$g.DrawCurve((Pen 5), [Drawing.PointF[]]@(0..16 | ForEach-Object { $b = Bone ($_ / 16); P $b[0] $b[1] }), 0.5)
Save-Small $bmp $g 'wing' 256 256

# slash_crack: трещины веером из центра — рваные ломаные с отростками (декаль под разрезом).
$bmp, $g = New-Big 256 256
$rng = New-Object Random 5
for ($i = 0; $i -lt 9; $i++) {
  $ang = $i * 2 * [Math]::PI / 9 + ($rng.NextDouble() - 0.5) * 0.5
  $x = 128.0; $y = 128.0; $w = 6.0
  $steps = 6 + $rng.Next(4)
  for ($s = 0; $s -lt $steps; $s++) {
    $ang += ($rng.NextDouble() - 0.5) * 0.9
    $L = 10 + $rng.NextDouble() * 12
    $nx = $x + $L * [Math]::Cos($ang); $ny = $y + $L * [Math]::Sin($ang)
    $g.DrawLine((Pen $w), (P $x $y), (P $nx $ny))
    if ($rng.Next(3) -eq 0) {
      $ba = $ang + ($rng.NextDouble() - 0.5) * 1.8; $bl = 8 + $rng.NextDouble() * 14
      $g.DrawLine((Pen ($w * 0.5) 200), (P $nx $ny), (P ($nx + $bl * [Math]::Cos($ba)) ($ny + $bl * [Math]::Sin($ba))))
    }
    $x = $nx; $y = $ny; $w = [Math]::Max(1.2, $w * 0.78)
    if ([Math]::Sqrt(($x - 128) * ($x - 128) + ($y - 128) * ($y - 128)) -gt 118) { break }
  }
}
$g.FillEllipse((Brush 255), [float](118 * $SS), [float](118 * $SS), [float](20 * $SS), [float](20 * $SS))
Save-Small $bmp $g 'slash_crack' 256 256
