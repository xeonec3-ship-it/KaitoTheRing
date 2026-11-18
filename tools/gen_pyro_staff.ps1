# Pyromancer staff for pohsmp_core: 32x32 texture + 3D item model (Blockbench-style JSON, Iron's staff proportions).
# Usage: tools\gen_pyro_staff.ps1
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$root = Split-Path -Parent $PSScriptRoot
$assets = Join-Path $root 'mods-src\pohsmp_core\src\main\resources\assets\pohsmp_core'
$texDir = Join-Path $assets 'textures\item'; $modDir = Join-Path $assets 'models\item'
New-Item -ItemType Directory -Force $texDir, $modDir | Out-Null

# ---------------- texture ----------------
$T = New-Object Drawing.Bitmap 32, 32, ([Drawing.Imaging.PixelFormat]::Format32bppArgb)
for ($y = 0; $y -lt 32; $y++) { for ($x = 0; $x -lt 32; $x++) { $T.SetPixel($x, $y, [Drawing.Color]::FromArgb(0, 0, 0, 0)) } }
function C($h) { [Drawing.ColorTranslator]::FromHtml($h) }
function P($x, $y, $h) { $T.SetPixel($x, $y, (C $h)) }
$rng = New-Object Random 17

# A: charred wood, x0-1 y0-31, grain + glowing cracks
$wood = '#2A1810', '#3B2418', '#4A2E1E', '#33200F'
for ($y = 0; $y -lt 32; $y++) { for ($x = 0; $x -lt 2; $x++) { P $x $y $wood[($y * 3 + $x * 5 + $rng.Next(2)) % 4] } }
foreach ($c in @(@(0, 4), @(1, 5), @(1, 11), @(0, 17), @(0, 18), @(1, 24), @(0, 29))) { P $c[0] $c[1] '#FF6A1A' }
foreach ($c in @(@(1, 4), @(0, 12), @(1, 18), @(1, 25))) { P $c[0] $c[1] '#B83A0E' }

# B: gold, x2-5 y0-7
for ($y = 0; $y -lt 8; $y++) { for ($x = 2; $x -lt 6; $x++) {
  $h = if ($y -eq 0 -or $x -eq 2) { '#FFE08A' } elseif ($y -eq 7 -or $x -eq 5) { '#8A4E10' } elseif (($x + $y) % 3 -eq 0) { '#F2B640' } else { '#D9952A' }
  P $x $y $h } }

# C: dark iron, x6-9 y0-7, rivets
for ($y = 0; $y -lt 8; $y++) { for ($x = 6; $x -lt 10; $x++) {
  $h = if ($y -eq 0) { '#5A5258' } elseif ($y -eq 7) { '#1A1618' } elseif (($x + $y) % 2 -eq 0) { '#3A3438' } else { '#2E292C' }
  P $x $y $h } }
P 7 3 '#8A8088'; P 8 5 '#8A8088'

# D: ember crystal, x10-13 y0-7 (glowing orange, hot center)
for ($y = 0; $y -lt 8; $y++) { for ($x = 10; $x -lt 14; $x++) {
  $d = [Math]::Abs($x - 11.5) / 2 + [Math]::Abs($y - 3.5) / 4
  $h = if ($d -lt 0.35) { '#FFF1B0' } elseif ($d -lt 0.6) { '#FFC83A' } elseif ($d -lt 0.85) { '#FF8A1E' } else { '#D9420E' }
  P $x $y $h } }
# D2: white-hot inner, x14-15 y0-7
for ($y = 0; $y -lt 8; $y++) { for ($x = 14; $x -lt 16; $x++) { P $x $y $(if ($y -eq 0 -or $y -eq 7) { '#FFD24A' } else { '#FFF6D0' }) } }

# E: flame, x16-31 y16-31, transparent outside
for ($v = 0; $v -lt 16; $v++) { for ($u = 0; $u -lt 16; $u++) {
  $t = $v / 15.0                                  # 0 top .. 1 bottom
  $cx = 7.5 + 1.6 * [Math]::Sin($t * 5.5) * (1 - $t)
  $w = 6.6 * [Math]::Pow($t, 0.75) * (1 - 0.35 * [Math]::Pow($t, 4))
  $tongue = if ($t -lt 0.45) { 1.8 * [Math]::Max(0, [Math]::Sin(($u + $t * 9) * 1.3)) * (0.45 - $t) / 0.45 } else { 0 }
  $dx = [Math]::Abs($u - $cx)
  if ($dx -gt $w + $tongue -or $t -lt 0.04) { continue }
  $k = $dx / [Math]::Max(0.5, $w)                  # 0 center .. 1 edge
  $h = if ($k -lt 0.35 -and $t -gt 0.45) { '#FFF6D0' } elseif ($k -lt 0.6 -and $t -gt 0.3) { '#FFD24A' } elseif ($k -lt 0.85) { '#FF8A1E' } else { '#E0400E' }
  if ($t -lt 0.22 -and $h -ne '#E0400E') { $h = '#FF6A1A' }
  P (16 + $u) (16 + $v) $h } }

$texPath = Join-Path $texDir 'pyro_staff.png'
$T.Save($texPath, [Drawing.Imaging.ImageFormat]::Png); $T.Dispose(); "  textures/item/pyro_staff.png"

# ---------------- model ----------------
# UV regions (model units, 1 unit = 2 px)
$UV = @{ wood = @(0, 0, 1, 16); gold = @(1, 0, 3, 4); iron = @(3, 0, 5, 4); ember = @(5, 0, 7, 4); hot = @(7, 0, 8, 4); flame = @(8, 8, 16, 16) }
$GLOW = [ordered]@{ block_light = 15; sky_light = 15; ambient_occlusion = $false }

function Box($from, $to, $mat, $rot = $null, [switch]$glow, $faces = @('north', 'east', 'south', 'west', 'up', 'down')) {
  $f = [ordered]@{}
  foreach ($n in $faces) { $face = [ordered]@{ uv = $UV[$mat]; texture = '#0' }; if ($glow) { $face.forge_data = $GLOW }; $f[$n] = $face }
  $e = [ordered]@{ from = $from; to = $to }
  if ($rot) { $e.rotation = $rot }
  $e.faces = $f
  if ($glow) { $e.shade = $false }
  $e
}
function Rot($angle, $axis, $origin) { [ordered]@{ angle = $angle; axis = $axis; origin = $origin } }

$el = New-Object System.Collections.ArrayList
# shaft
[void]$el.Add((Box @(7.5, -13.5, 7.5) @(8.5, 12.5, 8.5) 'wood'))
# pommel + glowing tip
[void]$el.Add((Box @(7, -15.5, 7) @(9, -13.5, 9) 'iron'))
[void]$el.Add((Box @(7.25, -14, 7.25) @(8.75, -13, 8.75) 'gold'))
[void]$el.Add((Box @(7.5, -16, 7.5) @(8.5, -15.5, 8.5) 'ember' -glow))
# bands and grip
[void]$el.Add((Box @(7.25, -6, 7.25) @(8.75, -5, 8.75) 'gold'))
[void]$el.Add((Box @(7.3, -2.5, 7.3) @(8.7, 1.5, 8.7) 'iron'))
[void]$el.Add((Box @(7.25, 1.5, 7.25) @(8.75, 2.25, 8.75) 'gold'))
[void]$el.Add((Box @(7.25, -3.25, 7.25) @(8.75, -2.5, 8.75) 'gold'))
[void]$el.Add((Box @(7.25, 7, 7.25) @(8.75, 8, 8.75) 'gold'))
# collar
[void]$el.Add((Box @(6.75, 11.5, 6.75) @(9.25, 13, 9.25) 'gold'))
[void]$el.Add((Box @(7, 13, 7) @(9, 14, 9) 'iron'))
# four claws: lower segment leans out, upper bends back in
foreach ($p in @(
    @{ ax = 'z'; s = -1; lo = @(9, 13.5, 7.5); lt = @(10, 17.5, 8.5); lorig = @(9, 13.5, 8); uo = @(10.5, 17, 7.5); ut = @(11.5, 21, 8.5); uorig = @(11, 17, 8) },
    @{ ax = 'z'; s = 1; lo = @(6, 13.5, 7.5); lt = @(7, 17.5, 8.5); lorig = @(7, 13.5, 8); uo = @(4.5, 17, 7.5); ut = @(5.5, 21, 8.5); uorig = @(5, 17, 8) },
    @{ ax = 'x'; s = 1; lo = @(7.5, 13.5, 9); lt = @(8.5, 17.5, 10); lorig = @(8, 13.5, 9); uo = @(7.5, 17, 10.5); ut = @(8.5, 21, 11.5); uorig = @(8, 17, 11) },
    @{ ax = 'x'; s = -1; lo = @(7.5, 13.5, 6); lt = @(8.5, 17.5, 7); lorig = @(8, 13.5, 7); uo = @(7.5, 17, 4.5); ut = @(8.5, 21, 5.5); uorig = @(8, 17, 5) })) {
  [void]$el.Add((Box $p.lo $p.lt 'iron' (Rot (22.5 * $p.s) $p.ax $p.lorig)))
  [void]$el.Add((Box $p.uo $p.ut 'gold' (Rot (-22.5 * $p.s) $p.ax $p.uorig)))
}
# ember core: diamond + white-hot spine
[void]$el.Add((Box @(6.5, 15, 6.5) @(9.5, 18, 9.5) 'ember' (Rot 45 'y' @(8, 16.5, 8)) -glow))
[void]$el.Add((Box @(7.25, 14.25, 7.25) @(8.75, 19.25, 8.75) 'hot' -glow))
# flame: two crossed planes
[void]$el.Add((Box @(5, 18.5, 8) @(11, 26.5, 8) 'flame' (Rot 45 'y' @(8, 22, 8)) -glow -faces @('north', 'south')))
[void]$el.Add((Box @(8, 18.5, 5) @(8, 26.5, 11) 'flame' (Rot 45 'y' @(8, 22, 8)) -glow -faces @('east', 'west')))

$model = [ordered]@{
  credit = 'pohsmp_core, tools/gen_pyro_staff.ps1'
  texture_size = @(32, 32)
  textures = [ordered]@{ '0' = 'pohsmp_core:item/pyro_staff'; particle = 'pohsmp_core:item/pyro_staff' }
  elements = $el
  display = [ordered]@{
    thirdperson_righthand = [ordered]@{ translation = @(0, 2, 1.25) }
    thirdperson_lefthand = [ordered]@{ translation = @(0, 2, 1.25) }
    firstperson_righthand = [ordered]@{ translation = @(1.5, -1, -2.75) }
    firstperson_lefthand = [ordered]@{ translation = @(1.5, -1, -2.75) }
    ground = [ordered]@{ translation = @(0, 8, 0); scale = @(0.5, 0.5, 0.5) }
    gui = [ordered]@{ rotation = @(-13, 128, 65); translation = @(0.5, 0, 0); scale = @(0.62, 0.62, 0.62) }
    fixed = [ordered]@{ translation = @(0, 0.5, -0.75); scale = @(0.5, 0.5, 0.5) }
  }
}
$json = $model | ConvertTo-Json -Depth 12
[IO.File]::WriteAllText((Join-Path $modDir 'pyro_staff.json'), $json, (New-Object Text.UTF8Encoding $false)); "  models/item/pyro_staff.json ($($el.Count) elements)"
