# Icons of the ordinary/legendary/mythic/divine spells of pohsmp_core (16x16) and their effects (18x18).
# Usage: tools\gen_spell_icons.ps1
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$root = Split-Path -Parent $PSScriptRoot
$assets = Join-Path $root 'mods-src\pohsmp_core\src\main\resources\assets\pohsmp_core'
$icons = Join-Path $assets 'textures\gui\spell_icons'
$eff = Join-Path $assets 'textures\mob_effect'
New-Item -ItemType Directory -Force $icons, $eff | Out-Null

function Hex($h) { [Drawing.ColorTranslator]::FromHtml($h) }
function SavePng($bmp, $path) { $bmp.Save($path, [Drawing.Imaging.ImageFormat]::Png); $bmp.Dispose(); "  " + (Split-Path -Leaf $path) }
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
function Frame($g, $S, $rim, $bg) { $g.FillRectangle((Br $bg), 2, 2, $S - 4, $S - 4); $g.DrawRectangle((Pn $rim ($S * 0.07)), $S * 0.05, $S * 0.05, $S * 0.9, $S * 0.9) }
function I($name, [scriptblock]$art, $rim, $bg) { Small 16 { param($g, $S) Frame $g $S $rim $bg; & $art $g $S } (Join-Path $icons "$name.png") }

# blood: heart with a drop going out
I 'blood_gift' { param($g, $S)
  $g.FillEllipse((Br '#C0102A'), $S*0.18, $S*0.26, $S*0.34, $S*0.32); $g.FillEllipse((Br '#C0102A'), $S*0.44, $S*0.26, $S*0.34, $S*0.32)
  $g.FillPolygon((Br '#C0102A'), (Pts @(($S*0.2),($S*0.48), ($S*0.76),($S*0.48), ($S*0.48),($S*0.82))))
  $g.FillEllipse((Br '#FF8090'), $S*0.68, $S*0.14, $S*0.14, $S*0.18) } '#8A0A1A' '#1A0608'
# holy: shield over a figure
I 'living_shield' { param($g, $S)
  $g.FillPolygon((Br '#FFE38A'), (Pts @(($S*0.5),($S*0.14), ($S*0.82),($S*0.26), ($S*0.76),($S*0.62), ($S*0.5),($S*0.86), ($S*0.24),($S*0.62), ($S*0.18),($S*0.26))))
  $g.FillEllipse((Br '#FFFFFF'), $S*0.42, $S*0.3, $S*0.16, $S*0.16); $g.FillRectangle((Br '#FFFFFF'), $S*0.44, $S*0.46, $S*0.12, $S*0.24) } '#D9A93A' '#1E1808'
# ice: three ice blocks
I 'glacial_tombs' { param($g, $S)
  foreach ($c in @(@(0.16,0.42), @(0.52,0.42), @(0.34,0.16))) { $g.FillRectangle((Br '#9CD8FF'), $S*$c[0], $S*$c[1], $S*0.32, $S*0.38); $g.FillRectangle((Br '#E8F8FF'), $S*($c[0]+0.04), $S*($c[1]+0.04), $S*0.08, $S*0.14) } } '#3A8ACC' '#0A1420'
I 'frost_spike_wall' { param($g, $S)
  foreach ($k in 0..3) { $x = 0.14 + $k * 0.19; $g.FillPolygon((Br '#BDE8FF'), (Pts @(($S*$x),($S*0.84), ($S*($x+0.17)),($S*0.84), ($S*($x+0.085)),($S*(0.2 + ($k % 2) * 0.14))))) } } '#3A8ACC' '#0A1420'
# fire: falling sun
I 'falling_sun' { param($g, $S)
  $g.FillEllipse((Br '#FF7A1A'), $S*0.34, $S*0.12, $S*0.36, $S*0.36); $g.FillEllipse((Br '#FFE070'), $S*0.42, $S*0.2, $S*0.2, $S*0.2)
  $g.DrawLine((Pn '#FF4A10' ($S*0.06)), $S*0.36, $S*0.44, $S*0.2, $S*0.66); $g.DrawLine((Pn '#FF4A10' ($S*0.05)), $S*0.5, $S*0.5, $S*0.42, $S*0.72)
  $g.DrawEllipse((Pn '#FF7A1A' ($S*0.05)), $S*0.12, $S*0.72, $S*0.76, $S*0.14) } '#C04010' '#1E0A04'
# lightning: ring wave with bolt
I 'ground_shock' { param($g, $S)
  $g.DrawEllipse((Pn '#F2E85A' ($S*0.06)), $S*0.12, $S*0.56, $S*0.76, $S*0.26)
  $g.FillPolygon((Br '#FFF8B0'), (Pts @(($S*0.54),($S*0.12), ($S*0.34),($S*0.46), ($S*0.5),($S*0.46), ($S*0.42),($S*0.74), ($S*0.66),($S*0.36), ($S*0.5),($S*0.36)))) } '#B0A020' '#1A1806'
# nature: roots + creeper face
I 'grasping_garden' { param($g, $S)
  $g.FillRectangle((Br '#5EC23A'), $S*0.3, $S*0.16, $S*0.4, $S*0.4)
  $g.FillRectangle((Br '#102A0A'), $S*0.36, $S*0.24, $S*0.1, $S*0.1); $g.FillRectangle((Br '#102A0A'), $S*0.54, $S*0.24, $S*0.1, $S*0.1); $g.FillRectangle((Br '#102A0A'), $S*0.45, $S*0.36, $S*0.1, $S*0.14)
  foreach ($x in @(0.2, 0.5, 0.78)) { $g.DrawBezier((Pn '#8A5A2A' ($S*0.05)), $S*$x, $S*0.86, $S*($x-0.1), $S*0.74, $S*($x+0.1), $S*0.7, $S*$x, $S*0.6) } } '#3A8A20' '#0A1606'
# ender: arrows outward
I 'banishment' { param($g, $S)
  $g.FillEllipse((Br '#B45CFF'), $S*0.4, $S*0.4, $S*0.2, $S*0.2)
  foreach ($a in 0..3) { $an = $a * [Math]::PI / 2 + [Math]::PI / 4; $x1 = 0.5 + 0.16 * [Math]::Cos($an); $y1 = 0.5 + 0.16 * [Math]::Sin($an); $x2 = 0.5 + 0.36 * [Math]::Cos($an); $y2 = 0.5 + 0.36 * [Math]::Sin($an)
    $g.DrawLine((Pn '#E0B0FF' ($S*0.06)), $S*$x1, $S*$y1, $S*$x2, $S*$y2); $g.FillEllipse((Br '#E0B0FF'), $S*($x2-0.06), $S*($y2-0.06), $S*0.12, $S*0.12) } } '#7A2AD0' '#140A1E'
# evocation: ring of 8 small shields
I 'eight_shields' { param($g, $S)
  for ($i = 0; $i -lt 8; $i++) { $an = $i * [Math]::PI / 4; $x = 0.5 + 0.3 * [Math]::Cos($an); $y = 0.5 + 0.3 * [Math]::Sin($an)
    $g.FillPolygon((Br '#C8D8F0'), (Pts @(($S*($x-0.08)),($S*($y-0.08)), ($S*($x+0.08)),($S*($y-0.08)), ($S*($x+0.07)),($S*($y+0.03)), ($S*$x),($S*($y+0.1)), ($S*($x-0.07)),($S*($y+0.03))))) }
  $g.FillEllipse((Br '#FFE38A'), $S*0.42, $S*0.42, $S*0.16, $S*0.16) } '#7A8AA0' '#10141A'
# wind: swirl, mark
I 'gale_ward' { param($g, $S)
  $g.DrawArc((Pn '#E8FAFF' ($S*0.06)), $S*0.16, $S*0.16, $S*0.68, $S*0.68, 0, 270); $g.DrawArc((Pn '#BFEFFF' ($S*0.05)), $S*0.3, $S*0.3, $S*0.4, $S*0.4, 90, 270) } '#6AB0C0' '#0A161A'
I 'wind_mark' { param($g, $S)
  $g.DrawLine((Pn '#E8FAFF' ($S*0.06)), $S*0.14, $S*0.6, $S*0.62, $S*0.6); $g.DrawLine((Pn '#BFEFFF' ($S*0.05)), $S*0.2, $S*0.74, $S*0.56, $S*0.74)
  $g.FillPolygon((Br '#FFFFFF'), (Pts @(($S*0.7),($S*0.16), ($S*0.86),($S*0.4), ($S*0.54),($S*0.4)))); $g.FillRectangle((Br '#FFFFFF'), $S*0.66, $S*0.38, $S*0.08, $S*0.3) } '#6AB0C0' '#0A161A'
# blood legendary: red eye
I 'magic_madness' { param($g, $S)
  $g.FillEllipse((Br '#3A0008'), $S*0.12, $S*0.3, $S*0.76, $S*0.4); $g.FillEllipse((Br '#FF2030'), $S*0.36, $S*0.32, $S*0.28, $S*0.36); $g.FillEllipse((Br '#000000'), $S*0.46, $S*0.36, $S*0.08, $S*0.28)
  foreach ($x in @(0.22, 0.4, 0.6, 0.78)) { $g.DrawLine((Pn '#C0102A' ($S*0.03)), $S*$x, $S*0.7, $S*($x + 0.02), $S*0.86) } } '#FF5A00' '#1A0204'
# divine: crossed-out circle with sun, soul
I 'divine_taboo' { param($g, $S)
  $g.FillEllipse((Br '#FFD34D'), $S*0.36, $S*0.36, $S*0.28, $S*0.28)
  for ($i = 0; $i -lt 8; $i++) { $an = $i * [Math]::PI / 4; $g.DrawLine((Pn '#FFE9A0' ($S*0.04)), $S*(0.5+0.18*[Math]::Cos($an)), $S*(0.5+0.18*[Math]::Sin($an)), $S*(0.5+0.28*[Math]::Cos($an)), $S*(0.5+0.28*[Math]::Sin($an))) }
  $g.DrawEllipse((Pn '#FF4040' ($S*0.06)), $S*0.14, $S*0.14, $S*0.72, $S*0.72); $g.DrawLine((Pn '#FF4040' ($S*0.06)), $S*0.24, $S*0.76, $S*0.76, $S*0.24) } '#FFD34D' '#1E1A06'
I 'soul_devour' { param($g, $S)
  $g.FillEllipse((Br '#5AE0E8'), $S*0.32, $S*0.2, $S*0.36, $S*0.4); $g.FillPolygon((Br '#5AE0E8'), (Pts @(($S*0.34),($S*0.5), ($S*0.66),($S*0.5), ($S*0.6),($S*0.86), ($S*0.5),($S*0.72), ($S*0.4),($S*0.86))))
  $g.FillEllipse((Br '#06141A'), $S*0.4, $S*0.32, $S*0.07, $S*0.1); $g.FillEllipse((Br '#06141A'), $S*0.53, $S*0.32, $S*0.07, $S*0.1); $g.FillEllipse((Br '#06141A'), $S*0.45, $S*0.46, $S*0.1, $S*0.08) } '#FFD34D' '#06060A'
# mythic: stacked circles and blast
I 'explosion' { param($g, $S)
  foreach ($k in 0..2) { $g.DrawEllipse((Pn '#FF7A3A' ($S*0.035)), $S*(0.2+$k*0.08), $S*(0.1+$k*0.07), $S*(0.6-$k*0.16), $S*0.12) }
  $g.FillEllipse((Br '#FF5A1E'), $S*0.2, $S*0.52, $S*0.6, $S*0.34); $g.FillEllipse((Br '#FFE070'), $S*0.36, $S*0.6, $S*0.28, $S*0.2)
  $g.FillRectangle((Br '#FFB060'), $S*0.46, $S*0.36, $S*0.08, $S*0.22) } '#B45CFF' '#120A1A'

# ---- group E ----
I 'fire_whip' { param($g, $S)
  $g.FillRectangle((Br '#6A3A1A'), $S*0.16, $S*0.66, $S*0.18, $S*0.08)
  $g.DrawBezier((Pn '#FF7A1A' ($S*0.07)), $S*0.32, $S*0.68, $S*0.6, $S*0.7, $S*0.9, $S*0.4, $S*0.5, $S*0.18)
  $g.DrawBezier((Pn '#FFE070' ($S*0.03)), $S*0.34, $S*0.66, $S*0.6, $S*0.66, $S*0.84, $S*0.4, $S*0.52, $S*0.22)
  $g.FillEllipse((Br '#FFE070'), $S*0.44, $S*0.12, $S*0.12, $S*0.12) } '#C04010' '#1E0A04'
I 'lightning_rod' { param($g, $S)
  $g.FillRectangle((Br '#C87A3A'), $S*0.46, $S*0.3, $S*0.08, $S*0.56); $g.FillEllipse((Br '#F2FFFF'), $S*0.4, $S*0.14, $S*0.2, $S*0.2)
  $g.DrawLines((Pn '#F2E85A' ($S*0.04)), (Pts @(($S*0.4),($S*0.26), ($S*0.26),($S*0.42), ($S*0.32),($S*0.48), ($S*0.16),($S*0.7))))
  $g.DrawLines((Pn '#F2E85A' ($S*0.04)), (Pts @(($S*0.6),($S*0.26), ($S*0.74),($S*0.44), ($S*0.68),($S*0.5), ($S*0.84),($S*0.72)))) } '#B0A020' '#1A1806'
I 'overload' { param($g, $S)
  $g.DrawEllipse((Pn '#8FD8FF' ($S*0.05)), $S*0.18, $S*0.18, $S*0.64, $S*0.64)
  $g.FillPolygon((Br '#FFF8B0'), (Pts @(($S*0.56),($S*0.2), ($S*0.36),($S*0.52), ($S*0.5),($S*0.52), ($S*0.42),($S*0.8), ($S*0.66),($S*0.44), ($S*0.52),($S*0.44))))
  foreach ($a in 0..3) { $an = $a * [Math]::PI / 2; $g.FillEllipse((Br '#8FD8FF'), $S*(0.46+0.38*[Math]::Cos($an)), $S*(0.46+0.38*[Math]::Sin($an)), $S*0.08, $S*0.08) } } '#3A7AB0' '#06101A'
I 'sanctuary' { param($g, $S)
  $g.DrawArc((Pn '#FFE38A' ($S*0.06)), $S*0.14, $S*0.24, $S*0.72, $S*0.9, 180, 180); $g.DrawLine((Pn '#FFE38A' ($S*0.05)), $S*0.14, $S*0.69, $S*0.86, $S*0.69)
  $g.FillRectangle((Br '#FFFFFF'), $S*0.46, $S*0.36, $S*0.08, $S*0.26); $g.FillRectangle((Br '#FFFFFF'), $S*0.38, $S*0.44, $S*0.24, $S*0.08) } '#D9A93A' '#1E1808'
I 'judgement' { param($g, $S)
  $g.FillPolygon((Br '#FFF2B0'), (Pts @(($S*0.38),($S*0.1), ($S*0.62),($S*0.1), ($S*0.56),($S*0.72), ($S*0.44),($S*0.72))))
  $g.FillRectangle((Br '#FFFFFF'), $S*0.47, $S*0.1, $S*0.06, $S*0.62); $g.DrawEllipse((Pn '#FFD34D' ($S*0.05)), $S*0.18, $S*0.68, $S*0.64, $S*0.16) } '#D9A93A' '#1E1808'
I 'swap' { param($g, $S)
  $g.DrawArc((Pn '#E0B0FF' ($S*0.06)), $S*0.2, $S*0.2, $S*0.6, $S*0.6, 200, 140); $g.DrawArc((Pn '#B45CFF' ($S*0.06)), $S*0.2, $S*0.2, $S*0.6, $S*0.6, 20, 140)
  $g.FillPolygon((Br '#E0B0FF'), (Pts @(($S*0.72),($S*0.16), ($S*0.86),($S*0.34), ($S*0.66),($S*0.36))))
  $g.FillPolygon((Br '#B45CFF'), (Pts @(($S*0.28),($S*0.84), ($S*0.14),($S*0.66), ($S*0.34),($S*0.64)))) } '#7A2AD0' '#140A1E'
I 'blood_mark' { param($g, $S)
  $g.DrawEllipse((Pn '#C0102A' ($S*0.06)), $S*0.18, $S*0.18, $S*0.64, $S*0.64); $g.DrawLine((Pn '#C0102A' ($S*0.05)), $S*0.5, $S*0.1, $S*0.5, $S*0.9); $g.DrawLine((Pn '#C0102A' ($S*0.05)), $S*0.1, $S*0.5, $S*0.9, $S*0.5)
  $g.FillEllipse((Br '#FF5060'), $S*0.4, $S*0.4, $S*0.2, $S*0.2) } '#8A0A1A' '#1A0608'
I 'hemorrhage' { param($g, $S)
  foreach ($c in @(@(0.24,0.2,0.18), @(0.52,0.36,0.22), @(0.3,0.58,0.16))) { $x=$c[0]; $y=$c[1]; $w=$c[2]
    $g.FillPolygon((Br '#C0102A'), (Pts @(($S*($x+$w/2)),($S*$y), ($S*($x+$w)),($S*($y+$w)), ($S*$x),($S*($y+$w))))); $g.FillEllipse((Br '#C0102A'), $S*$x, $S*($y+$w*0.6), $S*$w, $S*$w) }
  $g.DrawLine((Pn '#FF8090' ($S*0.03)), $S*0.62, $S*0.8, $S*0.86, $S*0.8) } '#8A0A1A' '#1A0608'
I 'phantom_trap' { param($g, $S)
  $g.DrawArc((Pn '#9A80FF' ($S*0.06)), $S*0.14, $S*0.3, $S*0.72, $S*0.6, 180, 180)
  for ($i = 0; $i -lt 5; $i++) { $x = 0.2 + $i * 0.15; $g.FillPolygon((Br '#D0C0FF'), (Pts @(($S*($x-0.05)),($S*0.6), ($S*($x+0.05)),($S*0.6), ($S*$x),($S*0.44)))) }
  $g.DrawLine((Pn '#9A80FF' ($S*0.04)), $S*0.14, $S*0.6, $S*0.86, $S*0.6) } '#5A4AA0' '#0E0A1A'
I 'illusion' { param($g, $S)
  $g.FillEllipse((Br '#6A5AA0'), $S*0.5, $S*0.18, $S*0.22, $S*0.22); $g.FillRectangle((Br '#6A5AA0'), $S*0.5, $S*0.42, $S*0.22, $S*0.38)
  $g.FillEllipse((Br '#D0C0FF'), $S*0.26, $S*0.2, $S*0.22, $S*0.22); $g.FillRectangle((Br '#D0C0FF'), $S*0.26, $S*0.44, $S*0.22, $S*0.38) } '#5A4AA0' '#0E0A1A'
I 'spore_cloud' { param($g, $S)
  foreach ($c in @(@(0.16,0.34,0.36), @(0.42,0.24,0.42), @(0.32,0.46,0.4))) { $g.FillEllipse((Br '#8CB43A'), $S*$c[0], $S*$c[1], $S*$c[2], $S*$c[2]*0.8) }
  foreach ($p in @(@(0.3,0.78), @(0.5,0.84), @(0.7,0.76), @(0.2,0.2), @(0.78,0.22))) { $g.FillEllipse((Br '#D8F08A'), $S*$p[0], $S*$p[1], $S*0.07, $S*0.07) } } '#3A8A20' '#0A1606'

# ---- higher (F), mythic (G), divine (H) ----
I 'blood_moon' { param($g, $S)
  $g.FillEllipse((Br '#D0101E'), $S*0.22, $S*0.14, $S*0.56, $S*0.56); $g.FillEllipse((Br '#16060A'), $S*0.36, $S*0.1, $S*0.5, $S*0.5)
  foreach ($x in @(0.24, 0.44, 0.64)) { $g.FillEllipse((Br '#FF4050'), $S*$x, $S*0.76, $S*0.1, $S*0.1) } } '#FF3B3B' '#16060A'
I 'oblivion_blades' { param($g, $S)
  for ($i = 0; $i -lt 6; $i++) { $an = $i * [Math]::PI / 3; $x1 = 0.5 + 0.12 * [Math]::Cos($an); $y1 = 0.5 + 0.12 * [Math]::Sin($an); $x2 = 0.5 + 0.38 * [Math]::Cos($an + 0.5); $y2 = 0.5 + 0.38 * [Math]::Sin($an + 0.5)
    $g.DrawLine((Pn '#B080E0' ($S*0.06)), $S*$x1, $S*$y1, $S*$x2, $S*$y2) }
  $g.FillEllipse((Br '#2A0A3A'), $S*0.4, $S*0.4, $S*0.2, $S*0.2) } '#FF3B3B' '#10060E'
I 'world_rift' { param($g, $S)
  $g.FillPolygon((Br '#5A1A8A'), (Pts @(($S*0.14),($S*0.86), ($S*0.3),($S*0.62), ($S*0.42),($S*0.66), ($S*0.58),($S*0.38), ($S*0.66),($S*0.42), ($S*0.86),($S*0.14), ($S*0.7),($S*0.5), ($S*0.6),($S*0.48), ($S*0.46),($S*0.74), ($S*0.34),($S*0.7))))
  $g.DrawLine((Pn '#C080FF' ($S*0.03)), $S*0.3, $S*0.62, $S*0.3, $S*0.2); $g.DrawLine((Pn '#C080FF' ($S*0.03)), $S*0.62, $S*0.4, $S*0.62, $S*0.08) } '#FF3B3B' '#10060E'
I 'mirror_prison' { param($g, $S)
  $g.FillRectangle((Br '#2A4A6A'), $S*0.2, $S*0.2, $S*0.6, $S*0.6); $g.DrawRectangle((Pn '#BFEFFF' ($S*0.05)), $S*0.2, $S*0.2, $S*0.6, $S*0.6)
  $g.DrawLine((Pn '#FFFFFF' ($S*0.04)), $S*0.28, $S*0.5, $S*0.5, $S*0.28); $g.DrawLine((Pn '#FFFFFF' ($S*0.03)), $S*0.36, $S*0.66, $S*0.66, $S*0.36)
  $g.FillEllipse((Br '#FF3B3B'), $S*0.44, $S*0.44, $S*0.12, $S*0.12) } '#FF3B3B' '#10060E'
I 'milky_way' { param($g, $S)
  for ($arm = 0; $arm -lt 2; $arm++) { $pts = @(); for ($i = 0; $i -le 24; $i++) { $t = $i / 24.0; $an = $arm * [Math]::PI + $t * 3.6; $rr = 0.04 + 0.36 * $t
      $pts += ($S * (0.5 + [Math]::Cos($an) * $rr)); $pts += ($S * (0.5 + [Math]::Sin($an) * $rr * 0.8)) }
    $g.DrawCurve((Pn '#9A6BFF' ($S*0.09)), (Pts $pts)); $g.DrawCurve((Pn '#E6E9FF' ($S*0.035)), (Pts $pts)) }
  $g.FillEllipse((Br '#FFFFFF'), $S*0.42, $S*0.42, $S*0.16, $S*0.16)
  foreach ($k in @(@(0.18,0.2), @(0.8,0.26), @(0.24,0.8), @(0.76,0.78))) { $g.FillEllipse((Br '#D8DCFF'), $S*$k[0], $S*$k[1], $S*0.06, $S*0.06) } } '#FF3B3B' '#0A0614'
I 'eternal_blizzard' { param($g, $S)
  $g.DrawEllipse((Pn '#4A9AE0' ($S*0.06)), $S*0.12, $S*0.5, $S*0.76, $S*0.3)
  $g.DrawArc((Pn '#DFF4FF' ($S*0.05)), $S*0.14, $S*0.16, $S*0.72, $S*0.4, 200, 140); $g.DrawArc((Pn '#9FD8FF' ($S*0.04)), $S*0.18, $S*0.3, $S*0.64, $S*0.34, 20, 160)
  foreach ($k in @(@(0.5,0.42,0.12), @(0.26,0.3,0.07), @(0.74,0.3,0.07), @(0.36,0.62,0.06), @(0.66,0.6,0.06))) { $x=$k[0]; $y=$k[1]; $w=$k[2]
    foreach ($a in 0..2) { $an = $a * [Math]::PI / 3; $g.DrawLine((Pn '#FFFFFF' ($S*0.025)), $S*($x-$w*[Math]::Cos($an)), $S*($y-$w*[Math]::Sin($an)), $S*($x+$w*[Math]::Cos($an)), $S*($y+$w*[Math]::Sin($an))) } } } '#FF3B3B' '#06101A'
I 'heaven_fall' { param($g, $S)
  foreach ($m in @(@(0.2,0.16), @(0.5,0.1), @(0.7,0.3))) { $x=$m[0]; $y=$m[1]
    $g.DrawLine((Pn '#FF9A3A' ($S*0.05)), $S*($x-0.12), $S*($y-0.12), $S*$x, $S*$y); $g.FillEllipse((Br '#FFE070'), $S*($x-0.05), $S*($y-0.05), $S*0.14, $S*0.14) }
  $g.FillEllipse((Br '#B0301A'), $S*0.12, $S*0.7, $S*0.76, $S*0.14); $g.FillEllipse((Br '#FF7A1A'), $S*0.4, $S*0.62, $S*0.2, $S*0.16) } '#B45CFF' '#120A1A'
I 'frozen_hour' { param($g, $S)
  $g.DrawEllipse((Pn '#9FD8FF' ($S*0.06)), $S*0.16, $S*0.16, $S*0.68, $S*0.68)
  for ($i = 0; $i -lt 12; $i++) { $an = $i * [Math]::PI / 6; $g.FillEllipse((Br '#DFF4FF'), $S*(0.47+0.28*[Math]::Cos($an)), $S*(0.47+0.28*[Math]::Sin($an)), $S*0.06, $S*0.06) }
  $g.DrawLine((Pn '#FFFFFF' ($S*0.05)), $S*0.5, $S*0.5, $S*0.5, $S*0.28); $g.DrawLine((Pn '#FFFFFF' ($S*0.05)), $S*0.5, $S*0.5, $S*0.66, $S*0.58) } '#B45CFF' '#120A1A'
I 'space_closure' { param($g, $S)
  $g.DrawArc((Pn '#8A6CFF' ($S*0.07)), $S*0.1, $S*0.16, $S*0.8, $S*1.1, 180, 180); $g.DrawLine((Pn '#8A6CFF' ($S*0.05)), $S*0.1, $S*0.71, $S*0.9, $S*0.71)
  $g.DrawArc((Pn '#D0C0FF' ($S*0.03)), $S*0.24, $S*0.3, $S*0.52, $S*0.82, 180, 180)
  $g.DrawArc((Pn '#FFFFFF' ($S*0.045)), $S*0.42, $S*0.34, $S*0.16, $S*0.18, 180, 180)
  $g.FillRectangle((Br '#FFFFFF'), $S*0.38, $S*0.43, $S*0.24, $S*0.2); $g.FillRectangle((Br '#2A1A5A'), $S*0.48, $S*0.48, $S*0.04, $S*0.1) } '#B45CFF' '#0C0818'
I 'ark' { param($g, $S)
  $g.DrawArc((Pn '#FFD34D' ($S*0.06)), $S*0.1, $S*0.2, $S*0.8, $S*1.0, 180, 180); $g.DrawLine((Pn '#FFD34D' ($S*0.05)), $S*0.1, $S*0.7, $S*0.9, $S*0.7)
  $g.FillPolygon((Br '#FFE9A0'), (Pts @(($S*0.3),($S*0.56), ($S*0.7),($S*0.56), ($S*0.62),($S*0.68), ($S*0.38),($S*0.68))))
  $g.FillRectangle((Br '#FFFFFF'), $S*0.48, $S*0.32, $S*0.04, $S*0.24) } '#FFD34D' '#1E1A06'
# creation (forbidden school): black-gold rift with a nether glow inside
I 'downfall' { param($g, $S)
  $g.DrawEllipse((Pn '#8A6410' ($S*0.05)), $S*0.12, $S*0.12, $S*0.76, $S*0.76)
  $g.FillEllipse((Br '#E8B830'), $S*0.3, $S*0.12, $S*0.4, $S*0.76); $g.FillEllipse((Br '#050304'), $S*0.35, $S*0.18, $S*0.3, $S*0.64)
  $g.FillEllipse((Br '#8A1A08'), $S*0.43, $S*0.34, $S*0.14, $S*0.32)
  foreach ($k in @(@(0.3,0.3,0.16,0.2), @(0.7,0.3,0.84,0.18), @(0.3,0.7,0.14,0.84), @(0.7,0.7,0.86,0.8))) { $g.DrawLine((Pn '#FFD34D' ($S*0.04)), $S*$k[0], $S*$k[1], $S*$k[2], $S*$k[3]) } } '#D4A017' '#050304'

# ---- effect icons 18x18 ----
Small 18 { param($g, $S)
  $g.FillPolygon((Br '#F2E85A'), (Pts @(($S*0.56),($S*0.06), ($S*0.24),($S*0.52), ($S*0.48),($S*0.52), ($S*0.38),($S*0.94), ($S*0.78),($S*0.4), ($S*0.52),($S*0.4)))) } (Join-Path $eff 'paralysis.png')
Small 18 { param($g, $S)
  $g.DrawLine((Pn '#E8FAFF' ($S*0.08)), $S*0.1, $S*0.66, $S*0.6, $S*0.66); $g.DrawLine((Pn '#BFEFFF' ($S*0.07)), $S*0.18, $S*0.84, $S*0.56, $S*0.84)
  $g.FillPolygon((Br '#FFFFFF'), (Pts @(($S*0.72),($S*0.08), ($S*0.92),($S*0.38), ($S*0.52),($S*0.38)))); $g.FillRectangle((Br '#FFFFFF'), $S*0.67, $S*0.36, $S*0.1, $S*0.36) } (Join-Path $eff 'wind_mark.png')
Small 18 { param($g, $S)
  $g.FillPolygon((Br '#FFE38A'), (Pts @(($S*0.5),($S*0.06), ($S*0.88),($S*0.2), ($S*0.8),($S*0.62), ($S*0.5),($S*0.94), ($S*0.2),($S*0.62), ($S*0.12),($S*0.2))))
  $g.FillEllipse((Br '#FFFFFF'), $S*0.4, $S*0.26, $S*0.2, $S*0.2) } (Join-Path $eff 'living_shield.png')
Small 18 { param($g, $S)
  for ($i = 0; $i -lt 8; $i++) { $an = $i * [Math]::PI / 4; $x = 0.5 + 0.34 * [Math]::Cos($an); $y = 0.5 + 0.34 * [Math]::Sin($an); $g.FillEllipse((Br '#C8D8F0'), $S*($x-0.1), $S*($y-0.1), $S*0.2, $S*0.2) } } (Join-Path $eff 'eight_shields.png')
Small 18 { param($g, $S)
  $g.FillEllipse((Br '#5A3A2A'), $S*0.1, $S*0.56, $S*0.8, $S*0.3); $g.FillEllipse((Br '#8A6A50'), $S*0.36, $S*0.2, $S*0.28, $S*0.28)
  $g.DrawLine((Pn '#C0C0C0' ($S*0.05)), $S*0.66, $S*0.16, $S*0.82, $S*0.06); $g.DrawLine((Pn '#C0C0C0' ($S*0.05)), $S*0.72, $S*0.28, $S*0.9, $S*0.24) } (Join-Path $eff 'spent.png')
Small 18 { param($g, $S)
  $g.FillEllipse((Br '#3A0008'), $S*0.06, $S*0.26, $S*0.88, $S*0.48); $g.FillEllipse((Br '#FF2030'), $S*0.34, $S*0.28, $S*0.32, $S*0.44); $g.FillEllipse((Br '#000000'), $S*0.45, $S*0.32, $S*0.1, $S*0.36) } (Join-Path $eff 'magic_madness.png')
Small 18 { param($g, $S)
  $g.DrawEllipse((Pn '#C0102A' ($S*0.08)), $S*0.14, $S*0.14, $S*0.72, $S*0.72); $g.FillEllipse((Br '#FF5060'), $S*0.36, $S*0.36, $S*0.28, $S*0.28) } (Join-Path $eff 'blood_mark.png')
Small 18 { param($g, $S)
  $g.FillPolygon((Br '#C0102A'), (Pts @(($S*0.5),($S*0.08), ($S*0.82),($S*0.56), ($S*0.18),($S*0.56)))); $g.FillEllipse((Br '#C0102A'), $S*0.18, $S*0.4, $S*0.64, $S*0.52) } (Join-Path $eff 'hemorrhage.png')
Small 18 { param($g, $S)
  $g.FillPolygon((Br '#8FD8FF'), (Pts @(($S*0.6),($S*0.04), ($S*0.22),($S*0.54), ($S*0.48),($S*0.54), ($S*0.36),($S*0.96), ($S*0.8),($S*0.42), ($S*0.54),($S*0.42)))) } (Join-Path $eff 'overload.png')
Small 18 { param($g, $S)
  foreach ($c in @(@(0.08,0.3,0.44), @(0.4,0.16,0.5), @(0.28,0.46,0.46))) { $g.FillEllipse((Br '#8CB43A'), $S*$c[0], $S*$c[1], $S*$c[2], $S*$c[2]*0.8) } } (Join-Path $eff 'spores.png')
Small 18 { param($g, $S)
  $g.FillEllipse((Br '#D4A017'), $S*0.1, $S*0.1, $S*0.8, $S*0.8); $g.FillEllipse((Br '#050304'), $S*0.22, $S*0.22, $S*0.56, $S*0.56)
  $g.DrawLine((Pn '#FFE08A' ($S*0.08)), $S*0.3, $S*0.3, $S*0.7, $S*0.7) } (Join-Path $eff 'creation_backlash.png')