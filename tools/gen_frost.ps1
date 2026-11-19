# Иней на земле у стены Вечной метели: полоса 512x64, бесшовная по горизонтали (по кругу).
# v = 0 — внутренний край (прозрачно), v = 1 — у стены. Кристаллы-веточки плотнее к стене.
# Запуск: powershell -File tools\gen_frost.ps1
Add-Type -AssemblyName System.Drawing
$W = 512; $H = 64
$out = Join-Path $PSScriptRoot "..\mods-src\pohsmp_core\src\main\resources\assets\pohsmp_core\textures\fx\frost_band.png"
$bmp = New-Object System.Drawing.Bitmap $W, $H, ([System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$g.Clear([System.Drawing.Color]::FromArgb(0, 255, 255, 255))
$rnd = New-Object System.Random 7331

function Get-Env([double]$v) {
    # плотность по радиусу: 0 внутри, максимум у стены, мягко гаснет за ней
    if ($v -lt 0.85) { return [Math]::Pow($v / 0.85, 1.6) }
    return [Math]::Max(0, 1 - ($v - 0.85) / 0.15)
}

function Draw-Line([double]$x1, [double]$y1, [double]$x2, [double]$y2, [int]$alpha, [single]$wid) {
    $pen = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb($alpha, 235, 248, 255)), $wid
    foreach ($ox in @(-$W, 0, $W)) { $g.DrawLine($pen, [single]($x1 + $ox), [single]$y1, [single]($x2 + $ox), [single]$y2) }
    $pen.Dispose()
}

function Draw-Crystal([double]$x, [double]$y, [double]$len, [double]$ang, [int]$depth, [double]$alpha) {
    if ($depth -le 0 -or $len -lt 1.5) { return }
    $x2 = $x + [Math]::Cos($ang) * $len; $y2 = $y + [Math]::Sin($ang) * $len
    Draw-Line $x $y $x2 $y2 ([int]$alpha) ([single](0.6 + 0.25 * $depth))
    $n = 2 + $rnd.Next(2)
    for ($k = 1; $k -le $n; $k++) {
        $t = $k / ($n + 1)
        $bx = $x + ($x2 - $x) * $t; $by = $y + ($y2 - $y) * $t
        $side = 1; if ($rnd.Next(2) -eq 0) { $side = -1 }
        Draw-Crystal $bx $by ($len * (0.35 + 0.2 * $rnd.NextDouble())) ($ang + $side * (0.9 + 0.3 * $rnd.NextDouble())) ($depth - 1) ($alpha * 0.8)
    }
}

# мягкая подложка
for ($y = 0; $y -lt $H; $y++) {
    $a = [int](70 * (Get-Env (($y + 0.5) / $H)))
    $pen = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb($a, 210, 235, 255)), 1
    $g.DrawLine($pen, 0, $y, $W, $y); $pen.Dispose()
}
# кристаллы
for ($i = 0; $i -lt 260; $i++) {
    $v = [Math]::Sqrt($rnd.NextDouble())
    $e = Get-Env $v
    if ($rnd.NextDouble() -gt $e + 0.08) { continue }
    $x = $rnd.NextDouble() * $W; $y = $v * ($H - 1)
    $arms = 3 + $rnd.Next(4)
    $base = $rnd.NextDouble() * [Math]::PI * 2
    for ($j = 0; $j -lt $arms; $j++) {
        Draw-Crystal $x $y (5 + 9 * $rnd.NextDouble() * $e) ($base + $j * 2 * [Math]::PI / $arms) 3 (120 + 120 * $e)
    }
}
# блёстки
for ($i = 0; $i -lt 500; $i++) {
    $v = $rnd.NextDouble(); $e = Get-Env $v
    if ($rnd.NextDouble() -gt $e) { continue }
    $x = $rnd.Next($W); $y = [int]($v * ($H - 1))
    $bmp.SetPixel($x, $y, [System.Drawing.Color]::FromArgb([int](160 + 95 * $e), 255, 255, 255))
}
$g.Dispose()
$bmp.Save($out, [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
"saved $out"
