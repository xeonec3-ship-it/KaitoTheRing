# Textures of the Higher school (pohsmp_core): fx ring/rune/void, 6 spell icons, 5 effect icons, scroll_higher (recolored scroll_divine).
# Usage: tools\gen_higher_textures.ps1
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$root = Split-Path -Parent $PSScriptRoot
$assets = Join-Path $root 'mods-src\pohsmp_core\src\main\resources\assets\pohsmp_core'
$fx = Join-Path $assets 'textures\fx'
$icons = Join-Path $assets 'textures\gui\spell_icons'
$eff = Join-Path $assets 'textures\mob_effect'
$items = Join-Path $assets 'textures\item'
New-Item -ItemType Directory -Force $fx, $icons, $eff, $items | Out-Null

function Hex($h) { [Drawing.ColorTranslator]::FromHtml($h) }
function SavePng($bmp, $path) { $bmp.Save($path, [Drawing.Imaging.ImageFormat]::Png); $bmp.Dispose(); "  " + (Split-Path -Leaf $path) }

# ---- fx: ring (soft bright ring near the edge, black background, additive) ----
$N = 256; $bmp = New-Object Drawing.Bitmap $N, $N
for ($y = 0; $y -lt $N; $y++) { for ($x = 0; $x -lt $N; $x++) {
  $d = [Math]::Sqrt([Math]::Pow(($x + 0.5) / ($N / 2) - 1, 2) + [Math]::Pow(($y + 0.5) / ($N / 2) - 1, 2))
  $v = [Math]::Exp(-[Math]::Pow(($d - 0.9) / 0.035, 2)) + 0.35 * [Math]::Exp(-[Math]::Pow(($d - 0.9) / 0.12, 2))
  $v = [int](255 * [Math]::Min(1, $v))
  $bmp.SetPixel($x, $y, [Drawing.Color]::FromArgb(255, $v, $v, $v)) } }
SavePng $bmp (Join-Path $fx 'ring.png')

# ---- fx: rune (glyph in a circle, white on black) ----
$N = 128; $bmp = New-Object Drawing.Bitmap $N, $N; $g = [Drawing.Graphics]::FromImage($bmp); $g.SmoothingMode = 'AntiAlias'; $g.Clear([Drawing.Color]::Black)
$p = New-Object Drawing.Pen ([Drawing.Color]::White), 7; $p.StartCap = 'Round'; $p.EndCap = 'Round'; $p.LineJoin = 'Round'
$g.DrawEllipse($p, 8, 8, 112, 112)
$p2 = New-Object Drawing.Pen ([Drawing.Color]::White), 9; $p2.StartCap = 'Round'; $p2.EndCap = 'Round'; $p2.LineJoin = 'Round'
$g.DrawLine($p2, 64, 26, 64, 102); $g.DrawLine($p2, 64, 40, 88, 58); $g.DrawLine($p2, 88, 58, 64, 76); $g.DrawLine($p2, 64, 58, 40, 44); $g.DrawLine($p2, 40, 84, 64, 96)
$g.Dispose(); SavePng $bmp (Join-Path $fx 'rune.png')

# ---- fx: void (black disc with a dark violet rim, real alpha) ----
$N = 128; $bmp = New-Object Drawing.Bitmap $N, $N, ([Drawing.Imaging.PixelFormat]::Format32bppArgb)
for ($y = 0; $y -lt $N; $y++) { for ($x = 0; $x -lt $N; $x++) {
  $d = [Math]::Sqrt([Math]::Pow(($x + 0.5) / ($N / 2) - 1, 2) + [Math]::Pow(($y + 0.5) / ($N / 2) - 1, 2))
  if ($d -ge 1) { $bmp.SetPixel($x, $y, [Drawing.Color]::FromArgb(0, 0, 0, 0)); continue }
  $a = if ($d -lt 0.78) { 255 } else { [int](255 * [Math]::Max(0, (1 - $d) / 0.22)) }
  $rim = [Math]::Max(0, 1 - [Math]::Abs($d - 0.8) / 0.12)
  $bmp.SetPixel($x, $y, [Drawing.Color]::FromArgb($a, [int](70 * $rim), 0, [int](110 * $rim))) } }
SavePng $bmp (Join-Path $fx 'void.png')

# ---- small icons: drawn at 4x, then scaled down ----
function Small([int]$size, [scriptblock]$draw, [string]$path) {
  $S = $size * 4
  $big = New-Object Drawing.Bitmap $S, $S, ([Drawing.Imaging.PixelFormat]::Format32bppArgb)
  $g = [Drawing.Graphics]::FromImage($big); $g.SmoothingMode = 'AntiAlias'; $g.Clear([Drawing.Color]::Transparent)
  & $draw $g $S
  $g.Dispose()
  $sm = New-Object Drawing.Bitmap $size, $size, ([Drawing.Imaging.PixelFormat]::Format32bppArgb)
  $g2 = [Drawing.Graphics]::FromImage($sm); $g2.InterpolationMode = 'HighQualityBicubic'; $g2.PixelOffsetMode = 'HighQuality'
  $g2.DrawImage($big, 0, 0, $size, $size); $g2.Dispose(); $big.Dispose()
  SavePng $sm $path
}
function Br($h) { New-Object Drawing.SolidBrush (Hex $h) }
function Pn($h, $w) { $p = New-Object Drawing.Pen (Hex $h), $w; $p.StartCap = 'Round'; $p.EndCap = 'Round'; $p.LineJoin = 'Round'; $p }
function Pts($arr) { $r = @(); for ($i = 0; $i -lt $arr.Count; $i += 2) { $r += New-Object Drawing.PointF ([float]$arr[$i]), ([float]$arr[$i + 1]) }; [Drawing.PointF[]]$r }
# spell icon frame: dark disc, red rim
function Frame($g, $S) { $g.FillEllipse((Br '#1A0A0E'), 2, 2, $S - 4, $S - 4); $g.DrawEllipse((Pn '#FF3B3B' ($S * 0.07)), $S * 0.05, $S * 0.05, $S * 0.9, $S * 0.9) }
function Star5($cx, $cy, $r1, $r2) { $a = @(); for ($i = 0; $i -lt 10; $i++) { $r = if ($i % 2 -eq 0) { $r1 } else { $r2 }; $an = -[Math]::PI / 2 + $i * [Math]::PI / 5; $a += $cx + $r * [Math]::Cos($an); $a += $cy + $r * [Math]::Sin($an) }; Pts $a }

Small 16 { param($g, $S) Frame $g $S
  $g.FillEllipse((Br '#B48CFF'), $S * 0.22, $S * 0.2, $S * 0.5, $S * 0.5); $g.FillEllipse((Br '#1A0A0E'), $S * 0.36, $S * 0.14, $S * 0.46, $S * 0.46)
  $g.DrawLines((Pn '#E6D8FF' ($S * 0.06)), (Pts @(($S*0.56),($S*0.6), ($S*0.76),($S*0.6), ($S*0.56),($S*0.8), ($S*0.76),($S*0.8)))) } (Join-Path $icons 'nightmare_cradle.png')
Small 16 { param($g, $S) Frame $g $S
  $g.FillPolygon((Br '#FFC94D'), (Star5 ($S / 2) ($S / 2 + $S * 0.03) ($S * 0.34) ($S * 0.14))); $g.FillEllipse((Br '#FFFFFF'), $S * 0.44, $S * 0.47, $S * 0.12, $S * 0.12) } (Join-Path $icons 'fate_star.png')
Small 16 { param($g, $S) Frame $g $S
  $g.DrawEllipse((Pn '#B46CFF' ($S * 0.07)), $S * 0.16, $S * 0.36, $S * 0.68, $S * 0.28); $g.FillEllipse((Br '#000000'), $S * 0.3, $S * 0.3, $S * 0.4, $S * 0.4); $g.DrawEllipse((Pn '#7A2AD0' ($S * 0.04)), $S * 0.3, $S * 0.3, $S * 0.4, $S * 0.4) } (Join-Path $icons 'singularity.png')
Small 16 { param($g, $S) Frame $g $S
  $h = @(); for ($i = 0; $i -lt 6; $i++) { $an = -[Math]::PI / 2 + $i * [Math]::PI / 3; $h += $S / 2 + $S * 0.3 * [Math]::Cos($an); $h += $S / 2 + $S * 0.3 * [Math]::Sin($an) }; $h += $h[0]; $h += $h[1]
  $g.DrawLines((Pn '#FF5A4A' ($S * 0.06)), (Pts $h)); $g.DrawLine((Pn '#FFD0C0' ($S * 0.07)), $S * 0.5, $S * 0.3, $S * 0.5, $S * 0.7); $g.DrawLine((Pn '#FFD0C0' ($S * 0.07)), $S * 0.5, $S * 0.42, $S * 0.64, $S * 0.52) } (Join-Path $icons 'forbidding_seal.png')
Small 16 { param($g, $S) Frame $g $S
  $g.FillRectangle((Br '#FFF2B0'), $S * 0.44, $S * 0.12, $S * 0.12, $S * 0.6); $g.FillPolygon((Br '#FFFFFF'), (Pts @(($S*0.5),($S*0.12), ($S*0.68),($S*0.36), ($S*0.32),($S*0.36))))
  $g.DrawArc((Pn '#FFD34D' ($S * 0.06)), $S * 0.2, $S * 0.55, $S * 0.6, $S * 0.26, 200, 140) } (Join-Path $icons 'wind_ascension.png')
Small 16 { param($g, $S) Frame $g $S
  $g.FillPolygon((Br '#2E7BFF'), (Pts @(($S*0.5),($S*0.14), ($S*0.74),($S*0.5), ($S*0.68),($S*0.78), ($S*0.32),($S*0.78), ($S*0.26),($S*0.5))))
  $g.FillPolygon((Br '#9CD2FF'), (Pts @(($S*0.5),($S*0.38), ($S*0.62),($S*0.6), ($S*0.58),($S*0.76), ($S*0.42),($S*0.76), ($S*0.38),($S*0.6)))) } (Join-Path $icons 'ashless_flame.png')

# ---- effect icons 18x18 ----
Small 18 { param($g, $S)
  $g.FillEllipse((Br '#8A4DFF'), $S * 0.12, $S * 0.12, $S * 0.7, $S * 0.7); $g.FillEllipse((Br '#00000000'), 0, 0, 1, 1)
  $g.CompositingMode = 'SourceCopy'; $g.FillEllipse((New-Object Drawing.SolidBrush ([Drawing.Color]::Transparent)), $S * 0.3, $S * 0.04, $S * 0.66, $S * 0.66); $g.CompositingMode = 'SourceOver'
  $g.DrawLines((Pn '#E6D8FF' ($S * 0.07)), (Pts @(($S*0.58),($S*0.62), ($S*0.86),($S*0.62), ($S*0.58),($S*0.9), ($S*0.86),($S*0.9)))) } (Join-Path $eff 'nightmare_sleep.png')
Small 18 { param($g, $S)
  $g.FillEllipse((Br '#2B1B3D'), $S * 0.08, $S * 0.25, $S * 0.84, $S * 0.5); $g.FillEllipse((Br '#D04040'), $S * 0.36, $S * 0.3, $S * 0.28, $S * 0.4); $g.FillEllipse((Br '#000000'), $S * 0.45, $S * 0.38, $S * 0.1, $S * 0.24)
  $g.DrawEllipse((Pn '#8A6AAA' ($S * 0.05)), $S * 0.08, $S * 0.25, $S * 0.84, $S * 0.5) } (Join-Path $eff 'dread.png')
Small 18 { param($g, $S)
  $g.DrawEllipse((Pn '#FF3B3B' ($S * 0.09)), $S * 0.12, $S * 0.12, $S * 0.76, $S * 0.76); $g.DrawLine((Pn '#FF3B3B' ($S * 0.09)), $S * 0.24, $S * 0.76, $S * 0.76, $S * 0.24)
  $g.DrawLine((Pn '#FFD0C0' ($S * 0.06)), $S * 0.5, $S * 0.3, $S * 0.5, $S * 0.5) } (Join-Path $eff 'forbidding_seal.png')
Small 18 { param($g, $S)
  $g.FillRectangle((Br '#9B4DFF'), $S * 0.4, $S * 0.1, $S * 0.2, $S * 0.45); $g.FillPolygon((Br '#C9A0FF'), (Pts @(($S*0.5),($S*0.84), ($S*0.8),($S*0.5), ($S*0.2),($S*0.5))))
  $g.FillRectangle((Br '#5B2A86'), $S * 0.1, $S * 0.86, $S * 0.8, $S * 0.08) } (Join-Path $eff 'gravity_crush.png')
Small 18 { param($g, $S)
  $g.FillRectangle((Br '#FFF2B0'), $S * 0.4, $S * 0.42, $S * 0.2, $S * 0.48); $g.FillPolygon((Br '#FFFFFF'), (Pts @(($S*0.5),($S*0.08), ($S*0.8),($S*0.44), ($S*0.2),($S*0.44))))
  $g.DrawArc((Pn '#FFD34D' ($S * 0.06)), $S * 0.12, $S * 0.6, $S * 0.76, $S * 0.3, 200, 140) } (Join-Path $eff 'ascension.png')

# ---- scroll_higher: scroll_divine with warm hues turned red ----
$src = New-Object Drawing.Bitmap (Join-Path $items 'scroll_divine.png')
$dst = New-Object Drawing.Bitmap $src.Width, $src.Height, ([Drawing.Imaging.PixelFormat]::Format32bppArgb)
for ($y = 0; $y -lt $src.Height; $y++) { for ($x = 0; $x -lt $src.Width; $x++) {
  $c = $src.GetPixel($x, $y); $h = $c.GetHue(); $s = $c.GetSaturation(); $l = $c.GetBrightness()
  if ($c.A -eq 0 -or $s -lt 0.25 -or $h -lt 20 -or $h -gt 70) { $dst.SetPixel($x, $y, $c); continue }
  # HSL -> RGB with hue near 0 (red), keep lightness, a bit more saturation
  $nh = 0.0; $ns = [Math]::Min(1, $s * 1.1)
  $q = if ($l -lt 0.5) { $l * (1 + $ns) } else { $l + $ns - $l * $ns }; $p = 2 * $l - $q
  function H2([double]$p, [double]$q, [double]$t) { if ($t -lt 0) { $t += 1 }; if ($t -gt 1) { $t -= 1 }; if ($t -lt 1/6) { return $p + ($q - $p) * 6 * $t }; if ($t -lt 0.5) { return $q }; if ($t -lt 2/3) { return $p + ($q - $p) * (2/3 - $t) * 6 }; return $p }
  $r = H2 $p $q ($nh + 1/3); $gg = H2 $p $q $nh; $b = H2 $p $q ($nh - 1/3)
  $dst.SetPixel($x, $y, [Drawing.Color]::FromArgb($c.A, [int](255 * $r), [int](255 * $gg), [int](255 * $b))) } }
$src.Dispose(); SavePng $dst (Join-Path $items 'scroll_higher.png')
