# Рисует разлом Низвержения (512x768): силуэт прорехи (rift_tear, RGBA, чёрный), ядро Нижнего мира (rift_core, RGBA, цветное)
# и светящуюся кромку с трещинами (rift_edge, белое на чёрном, аддитивно). Использование: tools\gen_rift_fx.ps1 [папка_превью]
param([string]$Preview)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$root = Split-Path -Parent $PSScriptRoot
$fx = Join-Path $root 'mods-src\pohsmp_core\src\main\resources\assets\pohsmp_core\textures\fx'
$W = 512; $H = 768; $cx = $W / 2.0; $PI = [Math]::PI
$rng = New-Object Random 777

# Контур прорехи: сверху вниз по левому краю, обратно по правому; ширина ~ sin(pi t)^0.75, зубцы
function Outline([double]$scale, [int]$seed) {
  $r = New-Object Random $seed
  $n = 46; $left = @(); $right = @()
  for ($i = 0; $i -le $n; $i++) {
    $t = $i / [double]$n; $y = 40 + ($H - 80) * $t
    $w = 150 * [Math]::Pow([Math]::Sin($PI * $t), 0.75) * $scale
    $jl = if ($i % 2 -eq 0) { 1 + 0.28 * $r.NextDouble() } else { 0.72 + 0.12 * $r.NextDouble() }
    $jr = if ($i % 2 -eq 1) { 1 + 0.28 * $r.NextDouble() } else { 0.72 + 0.12 * $r.NextDouble() }
    $bend = 18 * [Math]::Sin($t * 5.1) * $scale
    $left += New-Object Drawing.PointF ([float]($cx + $bend - $w * $jl)), ([float]$y)
    $right += New-Object Drawing.PointF ([float]($cx + $bend + $w * $jr)), ([float]$y)
  }
  [Array]::Reverse($right)
  return [Drawing.PointF[]]($left + $right)
}

function Canvas([bool]$clear) { $b = New-Object Drawing.Bitmap $W, $H, ([Drawing.Imaging.PixelFormat]::Format32bppArgb); $g = [Drawing.Graphics]::FromImage($b); $g.SmoothingMode = 'AntiAlias'
  if ($clear) { $g.Clear([Drawing.Color]::Transparent) } else { $g.Clear([Drawing.Color]::Black) }; return @($b, $g) }
function Save($b, $g, $name) { $g.Dispose(); $b.Save((Join-Path $fx "$name.png"), [Drawing.Imaging.ImageFormat]::Png)
  if ($Preview) { $b.Save((Join-Path $Preview "$name.png")) }; $b.Dispose(); "  $name.png" }

$main = Outline 1.0 31

# ---- силуэт: чёрное ядро и мягкий тёмный ореол ----
$b, $g = Canvas $true
foreach ($k in @(@(1.45, 18), @(1.3, 30), @(1.18, 55), @(1.08, 110))) {
  $o = Outline $k[0] 31
  $g.FillPolygon((New-Object Drawing.SolidBrush ([Drawing.Color]::FromArgb($k[1], 20, 4, 8))), $o) }
$g.FillPolygon((New-Object Drawing.SolidBrush ([Drawing.Color]::FromArgb(255, 4, 0, 2))), $main)
Save $b $g 'rift_tear'

# ---- ядро: багровая глубина, огненные прожилки-спирали, искры ----
$b, $g = Canvas $true
$inner = Outline 0.86 31
$path = New-Object Drawing.Drawing2D.GraphicsPath; $path.AddPolygon($inner)
$pg = New-Object Drawing.Drawing2D.PathGradientBrush $path
$pg.CenterColor = [Drawing.Color]::FromArgb(255, 150, 30, 8); $pg.SurroundColors = [Drawing.Color[]]@([Drawing.Color]::FromArgb(255, 18, 2, 6))
$pg.CenterPoint = New-Object Drawing.PointF ([float]$cx), ([float]($H * 0.52))
$g.FillPath($pg, $path)
$g.SetClip($path)
for ($s = 0; $s -lt 9; $s++) {
  $pts = @(); $a0 = $s * 2 * $PI / 9
  for ($i = 0; $i -le 40; $i++) { $t = $i / 40.0; $rr = 12 + 210 * $t; $a = $a0 + 3.2 * $t
    $pts += New-Object Drawing.PointF ([float]($cx + [Math]::Cos($a) * $rr * 0.55)), ([float]($H * 0.52 + [Math]::Sin($a) * $rr)) }
  $al = 90 + $rng.Next(100)
  $g.DrawCurve((New-Object Drawing.Pen ([Drawing.Color]::FromArgb($al, 255, 120 + $rng.Next(80), 20)), (2 + 3 * $rng.NextDouble())), [Drawing.PointF[]]$pts) }
for ($i = 0; $i -lt 120; $i++) { $x = $cx + ($rng.NextDouble() * 2 - 1) * 150; $y = 60 + $rng.NextDouble() * ($H - 120); $r = 1 + 3 * $rng.NextDouble()
  $g.FillEllipse((New-Object Drawing.SolidBrush ([Drawing.Color]::FromArgb(120 + $rng.Next(130), 255, 180 + $rng.Next(70), 60))), [float]($x - $r), [float]($y - $r), [float](2 * $r), [float](2 * $r)) }
$g.FillEllipse((New-Object Drawing.SolidBrush ([Drawing.Color]::FromArgb(110, 255, 200, 90))), [float]($cx - 36), [float]($H * 0.52 - 60), 72, 120)
$g.ResetClip()
Save $b $g 'rift_core'

# ---- кромка: толстый контур, внутренняя линия, ветвящиеся трещины наружу, искры ----
$b, $g = Canvas $false
$pen = New-Object Drawing.Pen ([Drawing.Color]::White), 9; $pen.LineJoin = 'Miter'
$g.DrawPolygon($pen, $main)
$g.DrawPolygon((New-Object Drawing.Pen ([Drawing.Color]::FromArgb(255, 150, 150, 150)), 3), (Outline 0.9 31))
function Crack($g, [double]$x, [double]$y, [double]$a, [double]$len, [double]$w, [int]$depth) {
  $px = $x; $py = $y
  $steps = 6
  for ($i = 0; $i -lt $steps; $i++) {
    $a += ($rng.NextDouble() - 0.5) * 0.9
    $nx = $px + [Math]::Cos($a) * $len / $steps; $ny = $py + [Math]::Sin($a) * $len / $steps
    $p = New-Object Drawing.Pen ([Drawing.Color]::White), ([float][Math]::Max(1.2, $w * (1 - $i / [double]$steps))); $p.StartCap = 'Round'; $p.EndCap = 'Round'
    $g.DrawLine($p, [float]$px, [float]$py, [float]$nx, [float]$ny)
    if ($depth -gt 0 -and $rng.Next(3) -eq 0) { Crack $g $nx $ny ($a + ($rng.NextDouble() - 0.5) * 1.6) ($len * 0.5) ($w * 0.6) ($depth - 1) }
    $px = $nx; $py = $ny }
}
for ($i = 2; $i -lt $main.Length - 2; $i += 3) {
  $p = $main[$i]; $a = [Math]::Atan2($p.Y - $H * 0.5, ($p.X - $cx) * 1.6)
  if ($p.Y -lt 70 -or $p.Y -gt $H - 70) { $a = if ($p.Y -lt $H / 2) { -$PI / 2 } else { $PI / 2 } }
  Crack $g $p.X $p.Y $a (40 + 60 * $rng.NextDouble()) 5 2 }
for ($i = 0; $i -lt 70; $i++) { $p = $main[$rng.Next($main.Length)]; $d = 8 + 40 * $rng.NextDouble(); $a = $rng.NextDouble() * 2 * $PI; $r = 1.5 + 2.5 * $rng.NextDouble()
  $g.FillEllipse([Drawing.Brushes]::White, [float]($p.X + [Math]::Cos($a) * $d - $r), [float]($p.Y + [Math]::Sin($a) * $d - $r), [float](2 * $r), [float](2 * $r)) }
Save $b $g 'rift_edge'
