# School staffs for pohsmp_core: one 32x32 texture + 3D item model (Iron's staff proportions) per school.
# Every staff has its own silhouette (head AND shaft), not a recolor.
# Output: assets/pohsmp_core/textures/item/<school>_staff.png, models/item/<school>_staff.json
# Usage: tools\gen_school_staffs.ps1 [-Only fire,blood]
# NOTE: PowerShell variables ignore case - every name here is unique regardless of case.
param([string[]]$Only)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$root = Split-Path -Parent $PSScriptRoot
$assets = Join-Path $root 'mods-src\pohsmp_core\src\main\resources\assets\pohsmp_core'
$texDir = Join-Path $assets 'textures\item'; $modDir = Join-Path $assets 'models\item'
New-Item -ItemType Directory -Force $texDir, $modDir | Out-Null

# ======================= texture layout (px) =======================
# y0-7 : shaft x0-1 (full height) | m1 x2-5 | m2 x6-9 | core x10-13 | hot x14-15 | gem x16-23 | frame x24-31 (border only)
# y8-15: m3 x2-5 | m4 x6-9 | core2 x10-13 | (x14-15 free) | wide 16x8 x16-31 (feather / leaf)
# y16-31: plane2 14x16 x2-15 (banner / sun disk) | plane 16x16 x16-31 (flame / arcs)
$script:bmp = $null
function Hx($h) { [Drawing.ColorTranslator]::FromHtml($h) }
function Px($px, $py, $h) { $script:bmp.SetPixel($px, $py, (Hx $h)) }

function Paint-Shaft($cols, $cracks, $seed) {
  $rnd = New-Object Random $seed
  for ($yy = 0; $yy -lt 32; $yy++) { for ($xx = 0; $xx -lt 2; $xx++) { Px $xx $yy $cols[($yy * 3 + $xx * 5 + $rnd.Next(2)) % 4] } }
  if ($cracks) {
    foreach ($c in @(@(0, 4), @(1, 5), @(1, 11), @(0, 17), @(0, 18), @(1, 24), @(0, 29))) { Px $c[0] $c[1] $cracks[0] }
    foreach ($c in @(@(1, 4), @(0, 12), @(1, 18), @(1, 25))) { Px $c[0] $c[1] $cracks[1] }
  }
}
function Paint-Metal($x0, $y0, $m) {
  for ($yy = 0; $yy -lt 8; $yy++) { for ($xx = 0; $xx -lt 4; $xx++) {
    $h = if ($yy -eq 0 -or $xx -eq 0) { $m[0] } elseif ($yy -eq 7 -or $xx -eq 3) { $m[3] } elseif (($xx + $yy) % 3 -eq 0) { $m[2] } else { $m[1] }
    Px ($x0 + $xx) ($y0 + $yy) $h } }
}
function Paint-Core($x0, $y0, $c) {
  for ($yy = 0; $yy -lt 8; $yy++) { for ($xx = 0; $xx -lt 4; $xx++) {
    $d = [Math]::Abs($xx - 1.5) / 2 + [Math]::Abs($yy - 3.5) / 4
    $h = if ($d -lt 0.35) { $c[0] } elseif ($d -lt 0.6) { $c[1] } elseif ($d -lt 0.85) { $c[2] } else { $c[3] }
    Px ($x0 + $xx) ($y0 + $yy) $h } }
}
function Paint-Hot($hot) { for ($yy = 0; $yy -lt 8; $yy++) { for ($xx = 14; $xx -lt 16; $xx++) { Px $xx $yy $(if ($yy -eq 0 -or $yy -eq 7) { $hot[0] } else { $hot[1] }) } } }
function Paint-Gem($kind, $c) {
  for ($yy = 0; $yy -lt 8; $yy++) { for ($xx = 0; $xx -lt 8; $xx++) {
    $dx = $xx - 3.5; $dy = $yy - 3.5; $d = [Math]::Sqrt($dx * $dx + $dy * $dy)
    switch ($kind) {
      'eye' { $h = if ($xx -eq 0 -or $yy -eq 0 -or $xx -eq 7 -or $yy -eq 7) { $c[3] } elseif ($d -lt 1.2) { '#050808' } elseif ($d -lt 2.3) { $c[0] } elseif ($d -lt 3.1) { $c[1] } else { $c[2] } }
      'ender' { $h = if ($xx -eq 0 -or $yy -eq 0 -or $xx -eq 7 -or $yy -eq 7) { $c[3] } elseif ([Math]::Abs($dx) -lt 0.6 -and [Math]::Abs($dy) -lt 2.2) { '#06140E' } elseif ($d -lt 2.2) { $c[0] } elseif ($d -lt 3.1) { $c[1] } else { $c[2] } }
      'void' { $h = if ($d -lt 2.4) { '#050203' } elseif ($d -lt 3.0) { $c[0] } elseif ($d -lt 3.6) { $c[1] } else { $c[2] } }
      'skull' {   # c = bone, bone shade, socket, eye glow
        $h = $c[0]
        if ($xx -eq 0 -or $xx -eq 7 -or $yy -eq 0) { $h = $c[1] }
        if (($yy -eq 2 -or $yy -eq 3) -and ($xx -eq 1 -or $xx -eq 2 -or $xx -eq 5 -or $xx -eq 6)) { $h = $c[2] }
        if ($yy -eq 3 -and ($xx -eq 2 -or $xx -eq 5)) { $h = $c[3] }
        if ($yy -eq 4 -and ($xx -eq 3 -or $xx -eq 4)) { $h = $c[2] }
        if ($yy -eq 6 -and ($xx % 2) -eq 1) { $h = $c[2] }
        if ($yy -eq 7) { $h = $c[1] }
      }
      default { $h = if ($d -lt 1.3) { $c[0] } elseif ($d -lt 2.4) { $c[1] } elseif ($d -lt 3.4) { $c[2] } else { $c[3] } }
    }
    if ($xx -eq 2 -and $yy -eq 2 -and $kind -ne 'ender' -and $kind -ne 'void' -and $kind -ne 'skull') { $h = '#FFFFFF' }
    Px (16 + $xx) $yy $h } }
}
function Paint-Frame($c) {
  for ($yy = 0; $yy -lt 8; $yy++) { for ($xx = 0; $xx -lt 8; $xx++) {
    $edge = ($xx -eq 0 -or $yy -eq 0 -or $xx -eq 7 -or $yy -eq 7)
    if ($edge) { $corner = (($xx -eq 0 -or $xx -eq 7) -and ($yy -eq 0 -or $yy -eq 7)); Px (24 + $xx) $yy $(if ($corner) { $c[0] } else { $c[1] }) } } }
}
function Paint-Wide($kind, $c) {
  $rnd = New-Object Random 5
  for ($yy = 0; $yy -lt 8; $yy++) { for ($xx = 0; $xx -lt 16; $xx++) {
    switch ($kind) {
      'feather' { $h = if ($yy -eq 7) { $c[3] } elseif ($yy -eq 0) { $c[0] } elseif ((($xx + $yy) % 4) -eq 0) { $c[2] } elseif ($yy -eq 3 -or $yy -eq 4) { $c[0] } else { $c[1] } }
      default { $n = $rnd.Next(10); $h = if ($n -lt 1) { $c[0] } elseif ($n -lt 5) { $c[1] } elseif ($n -lt 8) { $c[2] } else { $c[3] } }
    }
    Px (16 + $xx) (8 + $yy) $h } }
}
function Paint-Plane2($kind, $c) {
  for ($vv = 0; $vv -lt 16; $vv++) { for ($uu = 0; $uu -lt 14; $uu++) {
    $h = $null
    switch ($kind) {
      'banner' {
        $rh = [Math]::Abs($uu - 6.5) / 5.5 + [Math]::Abs($vv - 7) / 5.5
        $h = if ($vv -le 1) { $c[3] } elseif ($rh -lt 0.45) { $c[2] } elseif ($rh -lt 1) { $c[1] } elseif ($vv -eq 7 -or $vv -eq 8) { $c[2] } else { $c[0] }
        if (($vv -eq 6) -and ($uu -eq 4 -or $uu -eq 9)) { $h = '#3ED87A' }
        if ($vv -ge 14 -and (($uu % 5) -ge 2 -and ($uu % 5) -le 3)) { $h = $null }
        if ($vv -eq 15 -and (($uu % 5) -eq 1 -or ($uu % 5) -eq 4)) { $h = $null }
      }
      'sun' {
        $dx = $uu - 6.5; $dy = $vv - 7.5; $r = [Math]::Sqrt($dx * $dx + $dy * $dy)
        if ($r -lt 1.8) { $h = $c[0] } elseif ($r -lt 3.3) { $h = $c[1] } elseif ($r -lt 4.8) { $h = $c[2] } elseif ($r -lt 5.9) { $h = $c[3] } elseif ($r -lt 6.8) { $h = $c[4] }
        if ($r -ge 3.3 -and $r -lt 4.8 -and ([Math]::Round([Math]::Atan2($dy, $dx) * 4 / [Math]::PI) % 2) -eq 0) { $h = $c[1] }
      }
      'totem' {   # gold mask medallion: c = light, mid, dark rim, eye, pupil/mouth
        $dx = $uu - 6.5; $dy = $vv - 7.5; $r = [Math]::Sqrt($dx * $dx + $dy * $dy)
        if ($r -lt 5.6) { $h = if ($r -lt 3.6) { $c[0] } else { $c[1] } } elseif ($r -lt 6.6) { $h = $c[2] }
      }
    }
    if ($h) { Px (2 + $uu) (16 + $vv) $h } } }
}
function Draw-Line($ax, $ay, $bx, $by, $c0, $c1) {
  $steps = [Math]::Ceiling([Math]::Max([Math]::Abs($bx - $ax), [Math]::Abs($by - $ay)) * 2) + 1
  for ($i = 0; $i -le $steps; $i++) {
    $tt = $i / $steps; $qx = [Math]::Round($ax + ($bx - $ax) * $tt); $qy = [Math]::Round($ay + ($by - $ay) * $tt)
    foreach ($o in @()) {
      $ox = $qx + $o[0]; $oy = $qy + $o[1]
      if ($ox -ge 0 -and $ox -lt 16 -and $oy -ge 0 -and $oy -lt 16) { if ($script:bmp.GetPixel(16 + $ox, 16 + $oy).A -eq 0) { Px (16 + $ox) (16 + $oy) $c1 } }
    }
    if ($qx -ge 0 -and $qx -lt 16 -and $qy -ge 0 -and $qy -lt 16) { Px (16 + $qx) (16 + $qy) $c0 }
  }
}
function Paint-Plane($kind, $c) {
  if ($kind -eq 'arcs') {
    $bolts = @(
      @(@(7, 15), @(6, 11), @(8, 8), @(4, 5), @(5, 2), @(2, 0)),
      @(@(8, 15), @(11, 12), @(10, 9), @(13, 6), @(14, 3)),
      @(@(7, 15), @(3, 13), @(1, 10)))
    foreach ($b in $bolts) { for ($i = 0; $i -lt $b.Count - 1; $i++) { Draw-Line $b[$i][0] $b[$i][1] $b[$i + 1][0] $b[$i + 1][1] $c[0] $c[2] } }
    foreach ($b in $bolts) { $q = $b[$b.Count - 1]; Px (16 + $q[0]) (16 + $q[1]) $c[1] }
    return
  }
  for ($vv = 0; $vv -lt 16; $vv++) { for ($uu = 0; $uu -lt 16; $uu++) {
    $tt = $vv / 15.0; $h = $null
    $cx = 7.5 + 1.6 * [Math]::Sin($tt * 5.5) * (1 - $tt)
    $w = 6.6 * [Math]::Pow($tt, 0.75) * (1 - 0.35 * [Math]::Pow($tt, 4))
    $tongue = if ($tt -lt 0.45) { 1.8 * [Math]::Max(0, [Math]::Sin(($uu + $tt * 9) * 1.3)) * (0.45 - $tt) / 0.45 } else { 0 }
    $dx = [Math]::Abs($uu - $cx)
    if ($dx -le $w + $tongue -and $tt -ge 0.04) {
      $k = $dx / [Math]::Max(0.5, $w)
      $h = if ($k -lt 0.35 -and $tt -gt 0.45) { $c[0] } elseif ($k -lt 0.6 -and $tt -gt 0.3) { $c[1] } elseif ($k -lt 0.85) { $c[2] } else { $c[3] }
      if ($tt -lt 0.22 -and $h -ne $c[3]) { $h = $c[2] }
    }
    if ($h) { Px (16 + $uu) (16 + $vv) $h } } }
}

# ======================= model building =======================
$UVMAP = @{ wood = @(0, 0, 1, 16); m1 = @(1, 0, 3, 4); m2 = @(3, 0, 5, 4); core = @(5, 0, 7, 4); hot = @(7, 0, 8, 4); gem = @(8, 0, 12, 4); frame = @(12, 0, 16, 4)
  m3 = @(1, 4, 3, 8); m4 = @(3, 4, 5, 8); core2 = @(5, 4, 7, 8); wide = @(8, 4, 16, 8); plane2 = @(1, 8, 8, 16); plane = @(8, 8, 16, 16); hole = @(9, 1, 11, 3) }
$LIGHTDATA = [ordered]@{ block_light = 15; sky_light = 15; ambient_occlusion = $false }
$ALLF = @('north', 'east', 'south', 'west', 'up', 'down')
$NS = @('north', 'south'); $EW = @('east', 'west')
function R3($v) { [Math]::Round([double]$v, 3) }
function Rot([double]$angle, $axis, $origin) { [ordered]@{ angle = $angle; axis = $axis; origin = @((R3 $origin[0]), (R3 $origin[1]), (R3 $origin[2])) } }
function Box($from, $to, $mat, $rotation = $null, [switch]$lit, $faces = $ALLF) {
  $fd = [ordered]@{}
  foreach ($fn in $faces) { $face = [ordered]@{ uv = $UVMAP[$mat]; texture = '#0' }; if ($lit) { $face.forge_data = $LIGHTDATA }; $fd[$fn] = $face }
  $e = [ordered]@{ from = @((R3 $from[0]), (R3 $from[1]), (R3 $from[2])); to = @((R3 $to[0]), (R3 $to[1]), (R3 $to[2])) }
  if ($rotation -and $rotation.angle -ne 0) { $e.rotation = $rotation }
  $e.faces = $fd
  if ($lit) { $e.shade = $false }
  if ($script:BN) { $e['_b'] = $script:BN }
  $e['_m'] = $mat
  $e
}
# ---- GeckoLib bones (model coords in, geo pivots out: geo x = 8 - x, z = z - 8) ----
$script:BONES = $null
function Bn($name, $parent, [double]$mx, [double]$my, [double]$mz, $rot = $null, [switch]$drop) {
  if (-not $script:BONES) { $script:BONES = [ordered]@{ root = @{ pivot = @(0, 0, 0) } } }
  $d = @{ parent = $(if ($parent) { $parent } else { 'root' }); pivot = @((R3 (8 - $mx)), (R3 $my), (R3 ($mz - 8))) }
  if ($rot) { $d.rotation = $rot }
  if ($drop) { $d.drop = $true }
  $script:BONES[$name] = $d
  $script:BN = $name
}
# put one already-added element into its own bone pivoting at the element's center
function Own($els, [int]$idx, $name, $parent) {
  $el = $els[$idx]; $f = $el.from; $t = $el.to
  $keep = $script:BN
  Bn $name $parent (($f[0] + $t[0]) / 2) (($f[1] + $t[1]) / 2) (($f[2] + $t[2]) / 2)
  $el['_b'] = $name
  $script:BN = $keep
}
# centered cube, optional rotation about its own center
function C([double]$cx, [double]$cy, [double]$cz, [double]$sx, [double]$sy, [double]$sz, $mat, [double]$ra = 0, $rax = 'y', [switch]$lit, $faces = $ALLF) {
  $rr = if ($ra -ne 0) { Rot $ra $rax @($cx, $cy, $cz) } else { $null }
  Box @(($cx - $sx / 2), ($cy - $sy / 2), ($cz - $sz / 2)) @(($cx + $sx / 2), ($cy + $sy / 2), ($cz + $sz / 2)) $mat $rr -lit:$lit -faces $faces
}
function Add($list, $e) { [void]$list.Add($e) }
function AddOwn($list, $e, $name, $parent = $null) { [void]$list.Add($e); Own $list ($list.Count - 1) $name $parent }
# chain of bent segments; seg = @(angle, length[, down]); axis z bends in XY plane, axis x bends in ZY plane
# -SegBone p: every segment gets its own bone p0, p1, ... (child of the previous one, pivot at the segment start) - for waving tentacles
# -ChainBone n: the whole chain in one bone pivoting at the chain start
function Chain($els, [double]$sx, [double]$sy, [double]$sz, $axis, $segs, $mat, [double]$w0, [double]$w1, [switch]$lit, $tipMat = $null, [double]$tipSize = 0.5, [double]$flat = 0, $SegBone = $null, $ChainBone = $null) {
  $px = $sx; $py = $sy; $pz = $sz; $n = $segs.Count
  $keepBn = $script:BN; $par = $(if ($script:BN) { $script:BN } else { 'root' })
  if ($ChainBone) { Bn $ChainBone $par $sx $sy $sz }
  for ($i = 0; $i -lt $n; $i++) {
    $sg = $segs[$i]; $ang = $sg[0]; $len = $sg[1]; $dn = ($sg.Count -gt 2 -and $sg[2])
    if ($SegBone) { Bn "$SegBone$i" $(if ($i -eq 0) { $par } else { "$SegBone$($i - 1)" }) $px $py $pz }
    $w = $w0 + ($w1 - $w0) * ($i / [Math]::Max(1, $n - 1)); $hw = $w / 2; $hz = if ($flat -gt 0) { $flat / 2 } else { $hw }
    if ($dn) { $fr = @(($px - $hw), ($py - $len), ($pz - $hz)); $tt = @(($px + $hw), $py, ($pz + $hz)) } else { $fr = @(($px - $hw), $py, ($pz - $hz)); $tt = @(($px + $hw), ($py + $len), ($pz + $hz)) }
    Add $els (Box $fr $tt $mat (Rot $ang $axis @($px, $py, $pz)) -lit:$lit)
    $rad = $ang * [Math]::PI / 180; $sgn = if ($dn) { -1 } else { 1 }
    if ($axis -eq 'z') { $px += $sgn * (-$len * [Math]::Sin($rad)) } else { $pz += $sgn * ($len * [Math]::Sin($rad)) }
    $py += $sgn * $len * [Math]::Cos($rad)
  }
  if ($tipMat) { Add $els (C $px $py $pz $tipSize $tipSize $tipSize $tipMat 45 'y' -lit) }
  if ($SegBone -or $ChainBone) { $script:BN = $keepBn }
  ,@($px, $py, $pz)
}
function RingFlat($els, $mat, [double]$cy, [double]$rad, [double]$th, [switch]$lit) {
  $hs = $rad * [Math]::Tan([Math]::PI / 8)
  Add $els (Box @((8 - $hs), ($cy - $th), (8 + $rad - $th)) @((8 + $hs), ($cy + $th), (8 + $rad + $th)) $mat -lit:$lit)
  Add $els (Box @((8 - $hs), ($cy - $th), (8 - $rad - $th)) @((8 + $hs), ($cy + $th), (8 - $rad + $th)) $mat -lit:$lit)
  Add $els (Box @((8 + $rad - $th), ($cy - $th), (8 - $hs)) @((8 + $rad + $th), ($cy + $th), (8 + $hs)) $mat -lit:$lit)
  Add $els (Box @((8 - $rad - $th), ($cy - $th), (8 - $hs)) @((8 - $rad + $th), ($cy + $th), (8 + $hs)) $mat -lit:$lit)
  $dr = $rad * 0.7071
  foreach ($q in @(@(1, 1, 45), @(-1, -1, 45), @(1, -1, -45), @(-1, 1, -45))) {
    $qx = 8 + $q[0] * $dr; $qz = 8 + $q[1] * $dr
    Add $els (Box @(($qx - $hs), ($cy - $th), ($qz - $th)) @(($qx + $hs), ($cy + $th), ($qz + $th)) $mat (Rot $q[2] 'y' @($qx, $cy, $qz)) -lit:$lit)
  }
}
function HaloV($els, $mat, [double]$cy, [double]$rad, [double]$th, [switch]$lit) {
  $hs = $rad * [Math]::Tan([Math]::PI / 8)
  Add $els (Box @((8 - $hs), ($cy + $rad - $th), (8 - $th)) @((8 + $hs), ($cy + $rad + $th), (8 + $th)) $mat -lit:$lit)
  Add $els (Box @((8 - $hs), ($cy - $rad - $th), (8 - $th)) @((8 + $hs), ($cy - $rad + $th), (8 + $th)) $mat -lit:$lit)
  Add $els (Box @((8 + $rad - $th), ($cy - $hs), (8 - $th)) @((8 + $rad + $th), ($cy + $hs), (8 + $th)) $mat -lit:$lit)
  Add $els (Box @((8 - $rad - $th), ($cy - $hs), (8 - $th)) @((8 - $rad + $th), ($cy + $hs), (8 + $th)) $mat -lit:$lit)
  $dr = $rad * 0.7071
  foreach ($q in @(@(1, 1, -45), @(-1, -1, -45), @(-1, 1, 45), @(1, -1, 45))) {
    $qx = 8 + $q[0] * $dr; $qy = $cy + $q[1] * $dr
    Add $els (Box @(($qx - $hs), ($qy - $th), (8 - $th)) @(($qx + $hs), ($qy + $th), (8 + $th)) $mat (Rot $q[2] 'z' @($qx, $qy, 8)) -lit:$lit)
  }
}

function HaloZ($els, $mat, [double]$cy, [double]$rad, [double]$th, [switch]$lit) {   # octagon ring in the ZY plane
  $hs = $rad * [Math]::Tan([Math]::PI / 8)
  Add $els (Box @((8 - $th), ($cy + $rad - $th), (8 - $hs)) @((8 + $th), ($cy + $rad + $th), (8 + $hs)) $mat -lit:$lit)
  Add $els (Box @((8 - $th), ($cy - $rad - $th), (8 - $hs)) @((8 + $th), ($cy - $rad + $th), (8 + $hs)) $mat -lit:$lit)
  Add $els (Box @((8 - $th), ($cy - $hs), (8 + $rad - $th)) @((8 + $th), ($cy + $hs), (8 + $rad + $th)) $mat -lit:$lit)
  Add $els (Box @((8 - $th), ($cy - $hs), (8 - $rad - $th)) @((8 + $th), ($cy + $hs), (8 - $rad + $th)) $mat -lit:$lit)
  $dr = $rad * 0.7071
  foreach ($q in @(@(1, 1, 45), @(-1, -1, 45), @(-1, 1, -45), @(1, -1, -45))) {
    $qz = 8 + $q[0] * $dr; $qy = $cy + $q[1] * $dr
    Add $els (Box @((8 - $th), ($qy - $th), ($qz - $hs)) @((8 + $th), ($qy + $th), ($qz + $hs)) $mat (Rot $q[2] 'x' @(8, $qy, $qz)) -lit:$lit)
  }
}

# octagon (optionally oval / open) in the XY plane at z 8; skip = names of segments to leave out: T B L R TR TL BR BL
function Oct($els, $mat, [double]$cx, [double]$cy, [double]$rx, [double]$ry, [double]$th, [double]$dz, $skip = @(), [switch]$lit) {
  $hx = $rx * 0.4142; $hy = $ry * 0.4142; $z0 = 8 - $dz; $z1 = 8 + $dz
  if ($skip -notcontains 'T') { Add $els (Box @(($cx - $hx), ($cy + $ry - $th), $z0) @(($cx + $hx), ($cy + $ry + $th), $z1) $mat -lit:$lit) }
  if ($skip -notcontains 'B') { Add $els (Box @(($cx - $hx), ($cy - $ry - $th), $z0) @(($cx + $hx), ($cy - $ry + $th), $z1) $mat -lit:$lit) }
  if ($skip -notcontains 'R') { Add $els (Box @(($cx + $rx - $th), ($cy - $hy), $z0) @(($cx + $rx + $th), ($cy + $hy), $z1) $mat -lit:$lit) }
  if ($skip -notcontains 'L') { Add $els (Box @(($cx - $rx - $th), ($cy - $hy), $z0) @(($cx - $rx + $th), ($cy + $hy), $z1) $mat -lit:$lit) }
  $hl = ([Math]::Sqrt(($rx - $hx) * ($rx - $hx) + ($ry - $hy) * ($ry - $hy)) + $th) / 2
  foreach ($q in @(@('TR', 1, 1, -45), @('BL', -1, -1, -45), @('TL', -1, 1, 45), @('BR', 1, -1, 45))) {
    if ($skip -contains $q[0]) { continue }
    $mx = $cx + $q[1] * ($hx + $rx) / 2; $my = $cy + $q[2] * ($ry + $hy) / 2
    Add $els (Box @(($mx - $hl), ($my - $th), $z0) @(($mx + $hl), ($my + $th), $z1) $mat (Rot $q[3] 'z' @($mx, $my, 8)) -lit:$lit)
  }
}
# gear teeth / studs along an arc in the XY plane (angles in degrees, 0 = +x, 90 = up)
function Teeth($els, $mat, [double]$cx, [double]$cy, [double]$r, [double]$a0, [double]$a1, [int]$n, [double]$sz, [double]$dz, [switch]$lit) {
  for ($i = 0; $i -lt $n; $i++) {
    $a = ($a0 + ($a1 - $a0) * $i / [Math]::Max(1, $n - 1)) * [Math]::PI / 180
    Add $els (C ($cx + $r * [Math]::Cos($a)) ($cy + $r * [Math]::Sin($a)) 8 $sz $sz (2 * $dz) $mat 45 'z' -lit:$lit)
  }
}

# ======================= the staffs =======================
function Staff-Fire($e) {   # brazier
  Add $e (C 8 -1 8 1 26 1 'wood')
  Add $e (C 8 -14.5 8 1.5 1 1.5 'm2'); Add $e (C 8 -15.5 8 0.8 1 0.8 'core' 45 -lit)
  Add $e (C 8 -5.5 8 1.5 1 1.5 'm1'); Add $e (C 8 -0.5 8 1.4 4 1.4 'm2'); Add $e (C 8 3 8 1.5 0.8 1.5 'm1'); Add $e (C 8 8 8 1.5 0.8 1.5 'm1')
  $k = 0
  foreach ($t in @(@(8.75, -9, 8), @(8, -3.5, 8.75), @(7.25, 4.5, 8), @(8, 10, 7.25), @(8.75, 6, 8))) { AddOwn $e (C $t[0] $t[1] $t[2] 0.6 0.6 0.6 'core' 45 -lit) "ember$k"; $k++ }
  Add $e (C 8 12.75 8 2 1.5 2 'm2'); Add $e (C 8 13.75 8 4.5 0.5 4.5 'm2')
  Add $e (Box @(5.5, 13.5, 5.5) @(10.5, 17, 6) 'm2' (Rot -22.5 'x' @(8, 13.5, 5.75)))
  Add $e (Box @(5.5, 13.5, 10) @(10.5, 17, 10.5) 'm2' (Rot 22.5 'x' @(8, 13.5, 10.25)))
  Add $e (Box @(10, 13.5, 5.5) @(10.5, 17, 10.5) 'm2' (Rot -22.5 'z' @(10.25, 13.5, 8)))
  Add $e (Box @(5.5, 13.5, 5.5) @(6, 17, 10.5) 'm2' (Rot 22.5 'z' @(5.75, 13.5, 8)))
  Add $e (Box @(4.3, 16.4, 4.1) @(11.7, 17.1, 4.8) 'm1'); Add $e (Box @(4.3, 16.4, 11.2) @(11.7, 17.1, 11.9) 'm1')
  Add $e (Box @(11.2, 16.4, 4.3) @(11.9, 17.1, 11.7) 'm1'); Add $e (Box @(4.1, 16.4, 4.3) @(4.8, 17.1, 11.7) 'm1')
  foreach ($q in @(@(4.45, 4.45), @(11.55, 4.45), @(4.45, 11.55), @(11.55, 11.55))) { Add $e (C $q[0] 17.4 $q[1] 1 1 1 'm1' 45) }
  Bn 'coals' $null 8 15 8
  Add $e (C 8 14.6 8 5 1.2 5 'core' -lit); Add $e (C 8 15.4 8 2.5 0.6 2.5 'hot' -lit)
  Bn 'flames' $null 8 15 8
  Bn 'flame_a' 'flames' 8 15 8
  Add $e (Box @(4, 15, 8) @(12, 28.5, 8) 'plane' (Rot 22.5 'y' @(8, 15, 8)) -lit -faces $NS)
  Add $e (Box @(8, 15, 4) @(8, 28.5, 12) 'plane' (Rot 22.5 'y' @(8, 15, 8)) -lit -faces $EW)
  Bn 'flame_b' 'flames' 8 15 8
  Add $e (Box @(4.8, 15, 8) @(11.2, 25.5, 8) 'plane' (Rot -22.5 'y' @(8, 15, 8)) -lit -faces $NS)
  Add $e (Box @(8, 15, 4.8) @(8, 25.5, 11.2) 'plane' (Rot -22.5 'y' @(8, 15, 8)) -lit -faces $EW)
  Bn 'flame_c' 'flames' 8 16.5 8
  Add $e (Box @(6.3, 16.5, 4.4) @(9.7, 21, 4.4) 'plane' -lit -faces $NS); Add $e (Box @(6.3, 16.5, 11.6) @(9.7, 21, 11.6) 'plane' -lit -faces $NS)
  Add $e (Box @(11.6, 16.5, 6.3) @(11.6, 21, 9.7) 'plane' -lit -faces $EW); Add $e (Box @(4.4, 16.5, 6.3) @(4.4, 21, 9.7) 'plane' -lit -faces $EW)
  $script:BN = $null
  AddOwn $e (C 10.2 22 9 0.5 0.5 0.5 'hot' 45 -lit) 'spark0'; AddOwn $e (C 6.4 21 7 0.4 0.4 0.4 'core' 45 -lit) 'spark1'; AddOwn $e (C 9 20 6.6 0.4 0.4 0.4 'hot' 45 -lit) 'spark2'
}
function Staff-Blood($e) {   # spine shaft, ribcage, beating heart, horns
  Add $e (C 8 -1 8 0.8 26 0.8 'm2')
  for ($k = -13; $k -le 11; $k += 2) { Add $e (C 8 $k 8 1.8 0.9 1.8 'm1'); if ((($k + 13) / 2) % 2 -eq 0) { Add $e (C 8 $k 9.2 0.5 0.6 0.8 'm1') } }
  Add $e (C 8 -14.75 8 1.6 1.5 1.6 'm1'); Add $e (C 8 -15.7 8 0.6 0.6 0.6 'core' 45 -lit)
  Add $e (C 8 18 8 0.9 12 0.9 'm1')
  foreach ($yy in @(12.6, 21.6, 23.4)) { Add $e (C 8 $yy 8 1.6 0.6 1.6 'm1') }
  $lvN = 0
  foreach ($lv in @(@(13.5, 2.6, 3.4, 'z'), @(16.6, 3.2, 3.6, 'x'), @(19.6, 2.4, 2.8, 'z'))) {
    $y0 = $lv[0]; $out = $lv[1]; $up = $lv[2]
    $ye = $y0 + 0.35 + $out * 0.383; $reach = $out * 0.924
    if ($lv[3] -eq 'z') {
      Bn "rib${lvN}a" $null 8.4 ($y0 + 0.35) 8
      Add $e (Box @(8.4, $y0, 7.6) @((8.4 + $out), ($y0 + 0.7), 8.4) 'm1' (Rot 22.5 'z' @(8.4, ($y0 + 0.35), 8)))
      Add $e (Box @((8.4 + $reach - 0.7), ($ye - 0.3), 7.6) @((8.4 + $reach), ($ye + $up), 8.4) 'm1' (Rot 22.5 'z' @((8.4 + $reach - 0.35), $ye, 8)))
      Bn "rib${lvN}b" $null 7.6 ($y0 + 0.35) 8
      Add $e (Box @((7.6 - $out), $y0, 7.6) @(7.6, ($y0 + 0.7), 8.4) 'm1' (Rot -22.5 'z' @(7.6, ($y0 + 0.35), 8)))
      Add $e (Box @((7.6 - $reach), ($ye - 0.3), 7.6) @((7.6 - $reach + 0.7), ($ye + $up), 8.4) 'm1' (Rot -22.5 'z' @((7.6 - $reach + 0.35), $ye, 8)))
    } else {
      Bn "rib${lvN}a" $null 8 ($y0 + 0.35) 8.4
      Add $e (Box @(7.6, $y0, 8.4) @(8.4, ($y0 + 0.7), (8.4 + $out)) 'm1' (Rot -22.5 'x' @(8, ($y0 + 0.35), 8.4)))
      Add $e (Box @(7.6, ($ye - 0.3), (8.4 + $reach - 0.7)) @(8.4, ($ye + $up), (8.4 + $reach)) 'm1' (Rot -22.5 'x' @(8, $ye, (8.4 + $reach - 0.35))))
      Bn "rib${lvN}b" $null 8 ($y0 + 0.35) 7.6
      Add $e (Box @(7.6, $y0, (7.6 - $out)) @(8.4, ($y0 + 0.7), 7.6) 'm1' (Rot 22.5 'x' @(8, ($y0 + 0.35), 7.6)))
      Add $e (Box @(7.6, ($ye - 0.3), (7.6 - $reach)) @(8.4, ($ye + $up), (7.6 - $reach + 0.7)) 'm1' (Rot 22.5 'x' @(8, $ye, (7.6 - $reach + 0.35))))
    }
    $lvN++
  }
  Bn 'heart' $null 8 17.6 8
  Add $e (C 8 17.6 8 2.4 2.6 2.4 'gem' -lit); Add $e (C 8 17.6 8 2 2.2 2 'gem' 45 -lit)
  Bn 'veins' $null 8 17.6 8
  Add $e (C 7.3 19.6 8 0.5 1.4 0.5 'core' -lit); Add $e (C 8.7 19.4 8.2 0.5 1.1 0.5 'core' -lit)
  Add $e (C 7.4 15.2 8 0.3 1.6 0.3 'core' -lit); Add $e (C 8.6 14.9 7.8 0.3 2.2 0.3 'core' -lit); Add $e (C 8.6 13.6 7.8 0.5 0.5 0.5 'core' 45 -lit)
  $script:BN = $null
  Add $e (C 8 24.6 8 2 1.2 1.4 'm1')
  [void](Chain $e 8.8 24.8 8 'z' @(@(-45, 1.8), @(-22.5, 1.2), @(0, 0.8)) 'm1' 0.8 0.35)
  [void](Chain $e 7.2 24.8 8 'z' @(@(45, 1.8), @(22.5, 1.2), @(0, 0.8)) 'm1' 0.8 0.35)
  [void](Chain $e 8 24.8 8.6 'x' @(@(22.5, 1.4), @(0, 0.6)) 'm1' 0.7 0.35)
  [void](Chain $e 8 24.8 7.4 'x' @(@(-22.5, 1.4), @(0, 0.6)) 'm1' 0.7 0.35)
}
function Staff-Eldritch($e) {   # writhing shaft with eyes, caged eye, tentacles everywhere
  $j = @(, @(8, -14))
  $segs = @(@(22.5, 7), @(-22.5, 7), @(22.5, 7), @(-22.5, 7))
  [void](Chain $e 8 -14 8 'z' $segs 'wood' 1.1 1.0)
  $px = 8; $py = -14
  foreach ($sg in $segs) { $rad = $sg[0] * [Math]::PI / 180; $px += -$sg[1] * [Math]::Sin($rad); $py += $sg[1] * [Math]::Cos($rad); $j += , @($px, $py) }
  for ($i = 1; $i -le 3; $i++) { Add $e (C $j[$i][0] $j[$i][1] 8 1.5 1.5 1.5 'm2') }
  Add $e (C ($j[1][0] + 0.9) $j[1][1] 8 0.8 0.8 0.8 'gem' -lit); Add $e (C $j[2][0] $j[2][1] 8.95 0.7 0.7 0.7 'gem' -lit); Add $e (C ($j[3][0] - 0.9) $j[3][1] 8 0.8 0.8 0.8 'gem' -lit)
  Add $e (C 8 -14.5 8 1.6 1.2 1.6 'm2')
  [void](Chain $e 8 -15 8 'x' @(, @(22.5, 0.9, $true)) 'm1' 0.6 0.6)
  Add $e (C 8 12.6 8 1.8 1.4 1.8 'm2')
  AddOwn $e (C 8 15.6 8 3.6 3.6 3.6 'gem' -lit) 'eye'
  AddOwn $e (C 8 15.6 8 4.6 4.6 4.6 'frame' 45) 'cage'
  $T = @(
    @(9.8, 14.5, 8, 'z', @(@(-45, 3), @(-22.5, 2.5), @(0, 2), @(22.5, 2))),
    @(6.2, 15.5, 8, 'z', @(@(45, 3.5), @(22.5, 2.5), @(0, 2), @(-22.5, 1.5))),
    @(8, 14.2, 6.2, 'x', @(@(-45, 2.5), @(22.5, 3, $true), @(0, 2, $true))),
    @(8, 16.5, 9.8, 'x', @(@(45, 3), @(22.5, 3), @(-22.5, 2.5))),
    @(8, 17.4, 8, 'z', @(@(0, 2), @(22.5, 2.5), @(-22.5, 2.5), @(22.5, 2))),
    @(9.8, 14, 8.6, 'z', @(@(22.5, 2.5, $true), @(45, 2, $true))),
    @(8.5, 13.8, 9.6, 'x', @(@(-22.5, 3, $true), @(0, 1.5, $true))),
    @(6.4, 13.6, 7.2, 'z', @(@(-22.5, 2.5, $true), @(-45, 1.5, $true))))
  $tn = 0
  $script:ELD_T = $T   # before the loop: $t and $T are the same variable in PowerShell
  foreach ($t in $T) { [void](Chain $e $t[0] $t[1] $t[2] $t[3] $t[4] 'm1' 1.0 0.45 -tipMat 'core' -tipSize 0.45 -SegBone "t${tn}_"); $tn++ }
}
function Staff-Ender($e) {   # chorus shaft, levitating end crystal, orbiting shards
  Add $e (C 8 -1.5 8 1 25 1 'wood')
  foreach ($yy in @(-10, -3, 4)) { Add $e (C 8 $yy 8 1.5 1.2 1.5 'm2') }
  Add $e (C 9.2 -6 8 1.4 0.8 0.8 'm2'); Add $e (C 9.6 -5 8 0.8 1.6 0.8 'm2'); Add $e (C 9.6 -3.8 8 1 1 1 'core2' -lit)
  Add $e (C 8 1 6.8 0.8 0.8 1.4 'm2'); Add $e (C 8 2 6.4 0.8 1.6 0.8 'm2'); Add $e (C 8 3.2 6.4 1 1 1 'core2' -lit)
  Add $e (C 8 -14.75 8 1.6 1.5 1.6 'm2'); Add $e (C 8 -15.6 8 0.8 0.8 0.8 'core' 45 -lit)
  Add $e (C 8 11 8 2 1 2 'm1')
  [void](Chain $e 8.6 11.3 8 'z' @(@(-22.5, 2.6), @(0, 1)) 'm3' 0.7 0.4 -ChainBone 'claw0')
  [void](Chain $e 7.4 11.3 8 'z' @(@(22.5, 2.6), @(0, 1)) 'm3' 0.7 0.4 -ChainBone 'claw1')
  [void](Chain $e 8 11.3 8.6 'x' @(@(22.5, 2.6), @(0, 1)) 'm3' 0.7 0.4 -ChainBone 'claw2')
  [void](Chain $e 8 11.3 7.4 'x' @(@(-22.5, 2.6), @(0, 1)) 'm3' 0.7 0.4 -ChainBone 'claw3')
  Bn 'crystal' $null 8 18.8 8
  Bn 'cube_a' 'crystal' 8 18.8 8
  Add $e (C 8 18.8 8 5 5 5 'frame' 45 'y' -lit)
  Bn 'cube_b' 'crystal' 8 18.8 8
  Add $e (C 8 18.8 8 3.6 3.6 3.6 'frame' 45 'x' -lit)
  Bn 'gem' 'crystal' 8 18.8 8
  Add $e (C 8 18.8 8 2 2 2 'gem' -lit)
  Bn 'shards' $null 8 18.8 8
  foreach ($s in @(@(12.3, 17, 8, -22.5, 'z'), @(3.7, 20.5, 8, 22.5, 'z'), @(8, 16, 12.3, 22.5, 'x'), @(8, 21.5, 3.7, -22.5, 'x'))) {
    Add $e (C $s[0] $s[1] $s[2] 0.9 2.6 0.9 'm3' $s[3] $s[4]); Add $e (C $s[0] ($s[1] + 1.6) $s[2] 0.5 0.5 0.5 'core' 45 -lit)
  }
  Bn 'motes' $null 8 23.6 8
  Add $e (C 8 23.6 8 1.2 1.2 1.2 'hot' 45 -lit); Add $e (C 9.3 25.4 7.5 0.7 0.7 0.7 'core' 45 -lit); Add $e (C 7 26.8 8.6 0.5 0.5 0.5 'core2' 45 -lit)
  $script:BN = $null
}
function Staff-Evocation($e) {   # summoner: bone horns, wrapped grip, claw branch with a gold mask medallion, long ribbon
  Add $e (C 8 0.25 8 0.9 24.5 0.9 'wood')
  Add $e (C 8 -12.8 8 0.7 1.6 0.7 'm2'); Add $e (C 8 -14.2 8 0.45 1.4 0.45 'm4' 45); Add $e (C 8 -15.3 8 0.22 0.9 0.22 'm4' 45)
  foreach ($yy in @(-5.5, -3.5, -1.5, 10.6)) {
    Add $e (Box @(7.35, ($yy - 0.22), 7.35) @(8.65, ($yy + 0.22), 8.65) 'm2' (Rot 22.5 'z' @(8, $yy, 8)))
    Add $e (Box @(7.35, ($yy + 0.78), 7.35) @(8.65, ($yy + 1.22), 8.65) 'm2' (Rot -22.5 'z' @(8, ($yy + 1), 8)))
  }
  Add $e (C 8 -6.6 8 1.3 0.5 1.3 'm1'); Add $e (C 8 0.4 8 1.3 0.5 1.3 'm1')
  Add $e (C 8 12.6 8 1.5 0.9 1.5 'm1')
  # horns: big crescent, inner horn, small crook
  [void](Chain $e 8.2 12.6 8 'z' @(@(22.5, 3), @(0, 3), @(-22.5, 3), @(-45, 3), @(45, 2.5, $true), @(22.5, 2, $true)) 'm4' 1.3 0.35)
  [void](Chain $e 8.5 12.6 8.5 'z' @(@(0, 2.5), @(-22.5, 2.5), @(-45, 2), @(45, 1.5, $true)) 'm4' 0.9 0.3)
  [void](Chain $e 8.4 9.4 7.6 'z' @(@(-45, 1.8), @(-22.5, 1.2), @(0, 1), @(22.5, 0.8)) 'm4' 0.6 0.25)
  AddOwn $e (C 8.6 17.3 8.3 0.55 0.55 0.55 'core' 45 -lit) 'wisp'
  # claw branch to the left with a hanging medallion
  Add $e (Box @(3.6, 12.3, 7.6) @(7.8, 13, 8.4) 'm4' (Rot -22.5 'z' @(7.8, 12.65, 8)))
  [void](Chain $e 3.9 14 8 'z' @(@(0, 1.3), @(-22.5, 1), @(-45, 0.8)) 'm4' 0.5 0.22)
  [void](Chain $e 3.9 14 8 'z' @(@(45, 1), @(22.5, 0.8)) 'm4' 0.4 0.2)
  Bn 'medallion' $null 4.3 13.5 8
  foreach ($k in @(@(4.3, 13.1, 0), @(4.3, 12.3, 45), @(4.3, 11.5, 0))) { Add $e (C $k[0] $k[1] 8 0.32 0.7 0.32 'm1' $k[2]) }
  Bn 'mask' 'medallion' 4.3 11.1 8
  Add $e (Box @(2.1, 6.3, 7.95) @(6.5, 11.1, 8.05) 'plane2' -faces $NS)
  Add $e (C 4.3 11.1 8 0.7 0.4 0.4 'm1')
  $script:BN = $null
}
function Staff-Holy($e) {   # celestial bident: gold shaft, ankh foot, spiked oval frame with a blue stone, two feather blades, glowing orb
  Add $e (C 8 -1.5 8 0.9 25 0.9 'wood')
  Add $e (C 8 0 8 1.4 0.8 1.4 'm1'); Add $e (C 8 0 8 1.5 0.4 1.5 'm2' 45)
  Add $e (C 8 -8 8 1.2 0.4 1.2 'm1'); Add $e (C 8 6 8 1.2 0.4 1.2 'm1')
  Add $e (Box @(5.9, -12.9, 7.6) @(10.1, -12.3, 8.4) 'm1')
  Oct $e 'm1' 8 -14.4 1.2 1.1 0.28 0.35
  # spiked collar
  Add $e (C 8 11.4 8 1.6 0.6 1.6 'm2'); Add $e (C 8 12.1 8 2.2 0.8 2.2 'm1')
  Add $e (Box @(9.1, 11.9, 7.8) @(10.9, 12.3, 8.2) 'm1' (Rot 22.5 'z' @(9.1, 12.1, 8)))
  Add $e (Box @(5.1, 11.9, 7.8) @(6.9, 12.3, 8.2) 'm1' (Rot -22.5 'z' @(6.9, 12.1, 8)))
  Add $e (Box @(7.8, 11.9, 9.1) @(8.2, 12.3, 10.9) 'm1' (Rot -22.5 'x' @(8, 12.1, 9.1)))
  Add $e (Box @(7.8, 11.9, 5.1) @(8.2, 12.3, 6.9) 'm1' (Rot 22.5 'x' @(8, 12.1, 6.9)))
  # feather blades, V
  foreach ($side in @(1, -1)) {
    $ox = 8 + $side * 1.1; $ang = -22.5 * $side
    Bn $(if ($side -gt 0) { 'wing_r' } else { 'wing_l' }) $null $ox 12.4 8
    $x0 = if ($side -gt 0) { $ox } else { $ox - 1.8 }; $x1 = $x0 + 1.8
    Add $e (Box @($x0, 12.4, 7.75) @($x1, 22.4, 8.25) 'wide' (Rot $ang 'z' @($ox, 12.4, 8)))
    $t0 = if ($side -gt 0) { $ox + 0.2 } else { $ox - 1.2 }
    Add $e (Box @($t0, 22.4, 7.8) @(($t0 + 1), 25.4, 8.2) 'wide' (Rot $ang 'z' @($ox, 12.4, 8)))
    $o2 = 8 + $side * 1.6; $u0 = if ($side -gt 0) { $o2 } else { $o2 - 1.3 }
    Add $e (Box @($u0, 12.6, 7.95) @(($u0 + 1.3), 19.6, 8.45) 'wide' (Rot (-45 * $side) 'z' @($o2, 12.6, 8)))
  }
  $script:BN = $null
  # oval frame with the blue stone
  Oct $e 'm1' 8 16.4 2.3 3 0.3 0.45
  Bn 'stone' $null 8 16.4 8
  Add $e (C 8 16.4 8 2.2 3.8 0.9 'gem' -lit); Add $e (C 8 16.4 8 2.8 2.8 0.9 'gem' 45 'z' -lit)
  $script:BN = $null
  Add $e (C 8 19.9 8 0.6 0.6 0.6 'm1' 45 'z'); Add $e (C 8 12.9 8 0.6 0.6 0.6 'm1' 45 'z')
  Add $e (C 4.6 16.4 8 0.6 0.6 0.6 'm1' 45 'z'); Add $e (C 11.4 16.4 8 0.6 0.6 0.6 'm1' 45 'z')
  # orb between the feathers, with its spire
  Bn 'orb_lift' $null 8 22.6 8
  Bn 'orb' 'orb_lift' 8 22.6 8
  Add $e (C 8 22.6 8 1.6 1.6 1.6 'core' -lit); Add $e (C 8 22.6 8 1.4 1.4 1.4 'core' 45 -lit); Add $e (C 8 22.6 8 1.4 1.4 1.4 'core' 45 'x' -lit)
  $script:BN = $null
}
function Staff-Lightning($e) {   # spatiochronic: copper horseshoe gears, hourglass half-gear, ring and needle
  Add $e (C 8 -1.5 8 0.8 25 0.8 'wood')
  Add $e (C 8 -14.3 8 1.2 0.9 1.2 'm1' 45); Add $e (C 8 -15 8 0.8 0.8 0.8 'm1')
  foreach ($yy in @(-9, -2, 5)) { Add $e (C 8 $yy 8 1.2 0.5 1.2 'm2') }
  Add $e (C 8 11.4 8 1.4 0.9 1.4 'm2')
  # lower horseshoe gear with a teal orb
  Oct $e 'm1' 8 14.6 2.6 2.6 0.3 0.45 @('T')
  Bn 'teeth_low' $null 8 14.6 8
  Teeth $e 'm2' 8 14.6 3.05 200 340 6 0.55 0.35
  Bn 'orb_low' $null 8 14.6 8
  Add $e (C 8 14.6 8 1.9 1.9 1.9 'gem' -lit); Add $e (C 8 14.6 8 1.7 1.7 1.7 'gem' 45 -lit)
  $script:BN = $null
  foreach ($k in @(@(5.4, 14.6), @(10.6, 14.6), @(8, 12))) { Add $e (C $k[0] $k[1] 8.5 0.3 0.3 0.2 'm2') }
  # half gear with an hourglass, right on top of the horseshoe
  Add $e (C 8 17.3 8 0.5 1.2 0.5 'm2')
  Oct $e 'm1' 8 19 2.5 2.5 0.28 0.4 @('B', 'BL', 'BR')
  Add $e (Box @(5.3, 17.75, 7.6) @(10.7, 18.25, 8.4) 'm1')
  Bn 'teeth_up' $null 8 19 8
  Teeth $e 'm2' 8 19 2.95 20 160 7 0.5 0.3
  Bn 'hourglass' $null 8 19.425 8
  Add $e (C 8 20.4 8 1.4 0.25 0.5 'm2'); Add $e (C 8 18.45 8 1.4 0.25 0.5 'm2')
  Add $e (C 8 19.9 8 0.9 0.9 0.3 'core2' 45 'z' -lit); Add $e (C 8 18.95 8 0.65 0.65 0.3 'core2' 45 'z' -lit)
  $script:BN = $null
  # ring on the left, needle on the right
  Add $e (Box @(5.1, 18.4, 7.8) @(5.7, 18.8, 8.2) 'm2')
  Bn 'ring' $null 3.9 18.6 8
  Oct $e 'm1' 3.9 18.6 1.2 1.2 0.2 0.3
  Add $e (C 3.9 18.6 8 0.6 0.6 0.6 'hot' 45 -lit)
  $script:BN = $null
  Add $e (Box @(10.3, 19.4, 7.8) @(11.5, 19.8, 8.2) 'm2')
  Bn 'needle' $null 10.9 19.6 8
  Add $e (C 11.9 21.2 8 0.3 6 0.3 'm2' -22.5 'z'); Add $e (C 13.05 24 8 0.3 0.3 0.3 'hot' 45 -lit)
  $script:BN = $null
  # discharges and teal sparks
  [void](Chain $e 3.9 19.8 8 'z' @(@(-22.5, 1.2), @(45, 1.2), @(-45, 1), @(22.5, 1)) 'hot' 0.14 0.1 -lit -ChainBone 'arc0')
  [void](Chain $e 10.6 15.6 8.2 'z' @(@(-45, 1.2), @(22.5, 1), @(-45, 1.2), @(0, 0.8)) 'hot' 0.14 0.1 -lit -ChainBone 'arc1')
  [void](Chain $e 8 22.2 8 'x' @(@(22.5, 1), @(-45, 1), @(45, 0.8)) 'hot' 0.14 0.1 -lit -ChainBone 'arc2')
  [void](Chain $e 5.6 13.6 8 'z' @(@(45, 1.2, $true), @(-22.5, 1, $true), @(45, 0.8, $true)) 'hot' 0.14 0.1 -lit -ChainBone 'arc3')
  Bn 'sparks' $null 8 19 8
  foreach ($s in @(@(3.6, 16, 9), @(12.4, 17, 7), @(4.5, 22, 9.5), @(10.5, 24, 8), @(2.4, 21, 7.5), @(13, 14, 8.5))) { Add $e (C $s[0] $s[1] $s[2] 0.4 0.4 0.4 'hot' 45 -lit) }
  $script:BN = $null
}
function Staff-Nature($e) {   # grove skull: crooked dark branch, two claw branches cradle a skull with green eyes, leaves and sprouts
  [void](Chain $e 8 11 8 'z' @(@(0, 3, $true), @(22.5, 4, $true), @(0, 4, $true), @(-22.5, 4, $true), @(22.5, 4, $true), @(22.5, 3, $true), @(0, 2, $true)) 'wood' 1.3 0.3)
  foreach ($k in @(@(8, 5.5), @(9.5, 0.2), @(8.4, -6.5))) { Add $e (C $k[0] $k[1] 8 1.6 0.8 1.6 'wood' 45) }
  # claw branches
  [void](Chain $e 7.6 11 8 'z' @(@(22.5, 3), @(22.5, 3), @(0, 3), @(-22.5, 2), @(-45, 2), @(-45, 1.2)) 'wood' 1.2 0.3)
  [void](Chain $e 8.6 12.5 8 'z' @(@(-22.5, 2.5), @(-22.5, 2), @(0, 2), @(22.5, 2), @(45, 1.5), @(45, 1)) 'wood' 1.0 0.3)
  [void](Chain $e 8 12 8 'x' @(@(22.5, 2.5), @(0, 2), @(-22.5, 1.5)) 'wood' 0.7 0.3)
  # skull
  $sr = (Rot 22.5 'y' @(8, 17, 8))
  foreach ($b in @(
      @(6.2, 17.9, 6.6, 9.8, 19.4, 9.3, 'm4'),     # cranium
      @(6.6, 19.4, 6.9, 9.4, 19.9, 9.0, 'm4'),     # dome
      @(6.3, 16.4, 6.9, 9.7, 17.9, 9.2, 'm4'),     # mid skull
      @(6.6, 16.3, 9.2, 9.4, 17.9, 9.3, 'm2'),     # dark socket backing
      @(6.3, 17.9, 9.3, 9.7, 18.4, 9.95, 'm4'),    # brow ridge
      @(7.8, 16.9, 9.3, 8.2, 17.9, 9.85, 'm4'),    # nose bridge
      @(6.3, 16.6, 9.3, 6.9, 17.9, 9.85, 'm4'),    # outer socket rims
      @(9.1, 16.6, 9.3, 9.7, 17.9, 9.85, 'm4'),
      @(6.6, 16.3, 9.3, 7.75, 16.9, 9.8, 'm4'),    # cheeks under the eyes, nose hole between
      @(8.25, 16.3, 9.3, 9.4, 16.9, 9.8, 'm4'),
      @(6.8, 15.8, 8.0, 9.2, 16.3, 9.6, 'm4'),     # upper jaw
      @(7.0, 15.55, 8.2, 9.0, 15.8, 9.5, 'm2')     # mouth gap
    )) { Add $e (Box @($b[0], $b[1], $b[2]) @($b[3], $b[4], $b[5]) $b[6] $sr) }
  foreach ($tx in @(7.05, 7.55, 8.05, 8.55)) {   # teeth
    Add $e (Box @($tx, 15.5, 9.55) @(($tx + 0.4), 16.0, 9.75) 'm4' $sr)
  }
  foreach ($ex in @(7.1, 8.4)) { Add $e (Box @($ex, 17.05, 9.3) @(($ex + 0.5), 17.55, 9.5) 'core' $sr -lit) }   # eye glow
  # mandible and hinges: the bone 'jaw_yaw' carries the skull's 22.5 turn, 'jaw' opens about the hinge line
  Bn 'jaw_yaw' $null 8 17 8 @(0, -22.5, 0)
  Bn 'jaw' 'jaw_yaw' 8 15.8 7.6 $null -drop
  foreach ($b in @(
      @(6.9, 15.0, 7.6, 9.1, 15.55, 9.55, 'm4'),   # mandible
      @(6.5, 15.2, 7.3, 6.9, 16.3, 7.9, 'm4'),     # jaw hinges
      @(9.1, 15.2, 7.3, 9.5, 16.3, 7.9, 'm4')
    )) { Add $e (Box @($b[0], $b[1], $b[2]) @($b[3], $b[4], $b[5]) $b[6] $sr) }
  # green glow circling the skull
  Bn 'wisps' $null 8 17 8.6
  foreach ($g in @(@(5.6, 19.5, 8.6), @(10.6, 18.5, 7.6), @(7.4, 21.4, 8.2), @(9.6, 15, 9.4))) { Add $e (C $g[0] $g[1] $g[2] 0.7 0.7 0.7 'core' 45 -lit) }
  $script:BN = $null
  $k = 0
  foreach ($l in @(@(4.7, 17.6, 8.3, 0), @(11.2, 17.2, 7.7, 45), @(5.9, 14, 8.6, 45), @(10.3, 20.4, 8.2, 0), @(9.7, 4.6, 8.6, 45), @(10.5, -1.5, 7.6, 0), @(7.1, -8.5, 8.4, 45))) {
    AddOwn $e (C $l[0] $l[1] $l[2] 1.3 1 1.3 'wide' $l[3]) "leaf$k"; $k++
  }
  $k = 0
  foreach ($s in @(@(9.5, 5.6, 7.5), @(6.8, 1, 8.5), @(10.9, -2.6, 8.2))) { [void](Chain $e $s[0] $s[1] $s[2] 'z' @(@(-45, 1), @(-22.5, 0.8)) 'm1' 0.3 0.2 -ChainBone "sprout$k"); $k++ }
}function Staff-Higher($e) {   # singularity: black sphere with a crimson rim, tilted debris disk, jets, cracked black shaft
  Add $e (C 8 -1.5 8 1 25 1 'wood')
  Add $e (C 8 -14.5 8 1.6 1 1.6 'm2'); Add $e (Box @(7.4, -16, 7.4) @(8.6, -15, 8.6) 'core' (Rot 45 'y' @(8, -15.5, 8)) -lit)
  foreach ($v in @(@(8.56, 3, 8, 0.12, 5, 0.3), @(7.44, 6.5, 8, 0.12, 6, 0.3), @(8, 5, 8.56, 0.3, 3.5, 0.12), @(8, 8.5, 7.44, 0.3, 4.5, 0.12))) {
    Add $e (C $v[0] $v[1] $v[2] $v[3] $v[4] $v[5] 'core' -lit)
  }
  Add $e (C 8 11.4 8 1.5 1 1.5 'm2'); Add $e (C 8 12.3 8 2.2 0.6 2.2 'm2' 45)
  Bn 'claws' $null 8 12.6 8
  foreach ($k in @(@(1, 1), @(-1, 1), @(1, -1), @(-1, -1))) {   # four claws reaching up to the sphere
    $cx = 8 + $k[0] * 0.9; $cz = 8 + $k[1] * 0.9
    Add $e (C $cx 13.6 $cz 0.35 2 0.35 'm2' (22.5 * -$k[0]) 'z')
  }
  # the sphere
  Bn 'sphere' $null 8 19.5 8
  Add $e (C 8 19.5 8 4 4 4 'gem' -lit); Add $e (C 8 19.5 8 3.6 3.6 3.6 'gem' 45 -lit); Add $e (C 8 19.5 8 3.6 3.6 3.6 'gem' 45 'x' -lit)
  Bn 'halo' $null 8 19.5 8
  HaloV $e 'core' 19.5 3.0 0.14 -lit
  # accretion disk, tilted 22.5 about x (the tilt lives in the bone, the disk spins inside it)
  Bn 'disk_tilt' $null 8 19.5 8 @(-22.5, 0, 0)
  Bn 'disk' 'disk_tilt' 8 19.5 8 $null -drop
  $rot = Rot 22.5 'x' @(8, 19.5, 8)
  $sz = @(0.6, 0.9, 0.5, 0.8, 0.4, 0.7, 0.55, 0.85)
  for ($i = 0; $i -lt 16; $i++) {
    $a = $i * [Math]::PI / 8 + 0.2; $s = $sz[$i % 8]; $px = 8 + 4.3 * [Math]::Cos($a); $pz = 8 + 4.3 * [Math]::Sin($a); $py = 19.5 + 0.25 * (($i % 3) - 1)
    Add $e (Box @(($px - $s / 2), ($py - $s / 2), ($pz - $s / 2)) @(($px + $s / 2), ($py + $s / 2), ($pz + $s / 2)) 'm1' $rot)
  }
  for ($i = 0; $i -lt 12; $i++) {
    $a = $i * [Math]::PI / 6; $s = 0.35 + 0.1 * ($i % 3); $px = 8 + 3.2 * [Math]::Cos($a); $pz = 8 + 3.2 * [Math]::Sin($a)
    Add $e (Box @(($px - $s / 2), (19.5 - $s / 2), ($pz - $s / 2)) @(($px + $s / 2), (19.5 + $s / 2), ($pz + $s / 2)) 'core2' $rot -lit)
  }
  Add $e (Box @(10.3, 19.4, 7.85) @(12.8, 19.6, 8.15) 'core2' $rot -lit); Add $e (Box @(3.2, 19.4, 7.85) @(5.7, 19.6, 8.15) 'core2' $rot -lit)
  Add $e (Box @(7.85, 19.4, 10.3) @(8.15, 19.6, 12.8) 'core2' $rot -lit); Add $e (Box @(7.85, 19.4, 3.2) @(8.15, 19.6, 5.7) 'core2' $rot -lit)
  # lower jet
  Bn 'jet' $null 8 16.8 8
  Add $e (C 8 15.6 8 0.35 2.4 0.35 'hot' -lit)
  $script:BN = $null
}
function Staff-Divine($e) {   # volumetric sun: glowing core, 3D star of rays, gyroscope of two halos, floating crown
  Add $e (C 8 -1.5 8 1.1 25 1.1 'wood')
  foreach ($yy in @(-12, -6, 0, 6)) { Add $e (C 8 $yy 8 1.5 0.6 1.5 'm1') }
  Add $e (C 8 -3 8 1.4 4.4 1.4 'm2')
  Add $e (C 8 -14.75 8 1.8 1.5 1.8 'm1'); Add $e (C 8 -15.6 8 0.8 0.8 0.8 'hot' 45 -lit)
  Add $e (C 8 11.6 8 1.8 1.2 1.8 'm1'); Add $e (C 8 12.6 8 2.6 0.8 2.6 'm1'); Add $e (C 8 13.6 8 0.8 1.4 0.8 'm1')
  # sun core
  Bn 'sun' $null 8 19 8
  Add $e (C 8 19 8 3.4 3.4 3.4 'hot' -lit)
  Add $e (C 8 19 8 3.0 3.0 3.0 'hot' 45 -lit)
  Add $e (C 8 19 8 3.0 3.0 3.0 'hot' 45 'x' -lit)
  Add $e (C 8 19 8 4.0 1.6 1.6 'core' -lit); Add $e (C 8 19 8 1.6 4.0 1.6 'core' -lit); Add $e (C 8 19 8 1.6 1.6 4.0 'core' -lit)
  # gyroscope
  Bn 'halo_v' $null 8 19 8
  HaloV $e 'm1' 19 4.9 0.4 -lit
  Bn 'halo_z' $null 8 19 8
  HaloZ $e 'm1' 19 4.4 0.4 -lit
  # long rays: up, sides, front/back (square section)
  Bn 'rays' $null 8 19 8
  foreach ($a in @(0, 45, -45)) { Add $e (Box @(7.5, 24, 7.5) @(8.5, 28.2, 8.5) 'hot' (Rot $a 'z' @(8, 19, 8)) -lit) }
  foreach ($a in @(45, -45)) { Add $e (Box @(7.5, 9.8, 7.5) @(8.5, 14, 8.5) 'hot' (Rot $a 'z' @(8, 19, 8)) -lit) }
  Add $e (Box @(12.9, 18.5, 7.5) @(17.2, 19.5, 8.5) 'hot' -lit); Add $e (Box @(-1.2, 18.5, 7.5) @(3.1, 19.5, 8.5) 'hot' -lit)
  Add $e (Box @(7.5, 18.5, 12.9) @(8.5, 19.5, 17.2) 'hot' -lit); Add $e (Box @(7.5, 18.5, -1.2) @(8.5, 19.5, 3.1) 'hot' -lit)
  foreach ($a in @(45, -45)) { Add $e (Box @(7.5, 24, 7.5) @(8.5, 27.4, 8.5) 'hot' (Rot $a 'x' @(8, 19, 8)) -lit) }
  # short rays between
  Bn 'rays_short' 'rays' 8 19 8
  foreach ($a in @(22.5, -22.5)) {
    Add $e (Box @(7.6, 24, 7.6) @(8.4, 26.4, 8.4) 'core' (Rot $a 'z' @(8, 19, 8)) -lit)
    Add $e (Box @(7.6, 24, 7.6) @(8.4, 26.4, 8.4) 'core' (Rot $a 'x' @(8, 19, 8)) -lit)
    Add $e (Box @(12.9, 18.6, 7.6) @(15.3, 19.4, 8.4) 'core' (Rot $a 'z' @(8, 19, 8)) -lit)
    Add $e (Box @(0.7, 18.6, 7.6) @(3.1, 19.4, 8.4) 'core' (Rot $a 'z' @(8, 19, 8)) -lit)
    Add $e (Box @(7.6, 18.6, 12.9) @(8.4, 19.4, 15.3) 'core' (Rot $a 'x' @(8, 19, 8)) -lit)
    Add $e (Box @(7.6, 18.6, 0.7) @(8.4, 19.4, 3.1) 'core' (Rot $a 'x' @(8, 19, 8)) -lit)
  }
  Bn 'crown' $null 8 29.6 8
  RingFlat $e 'm1' 29.6 1.6 0.3 -lit
  foreach ($o in @(@(1.6, 0), @(-1.6, 0), @(0, 1.6), @(0, -1.6))) { Add $e (C (8 + $o[0]) 30.6 (8 + $o[1]) 0.45 1.2 0.45 'm1' 45 -lit) }
  $script:BN = $null
}
function Staff-Mythic($e) {   # Mythic tier: starry armillary sphere, star core, crescent, silver helix
  Add $e (C 8 -1.5 8 1 25 1 'wood')
  Bn 'helix' $null 8 0 8
  for ($i = 0; $i -lt 19; $i++) {
    $an = $i * [Math]::PI / 4; $hy = -12 + $i * 1.2
    if ($i % 3 -eq 2) { Add $e (C (8 + 0.75 * [Math]::Cos($an)) $hy (8 + 0.75 * [Math]::Sin($an)) 0.5 0.5 0.5 'core2' 45 -lit) }
    else { Add $e (C (8 + 0.75 * [Math]::Cos($an)) $hy (8 + 0.75 * [Math]::Sin($an)) 0.45 0.45 0.45 'm1') }
  }
  $script:BN = $null
  foreach ($yy in @(-13.2, 11)) { Add $e (C 8 $yy 8 1.5 0.7 1.5 'm2') }
  Add $e (C 8 -14.75 8 1.6 1.5 1.6 'm2'); Add $e (C 8 -15.6 8 0.8 0.8 0.8 'core' 45 -lit)
  Add $e (C 8 12 8 2 1 2 'm2'); Add $e (C 8 13.2 8 1.2 1.6 1.2 'm1'); Add $e (C 8 14.6 8 0.6 1.2 0.6 'm1')
  Bn 'ring_a' $null 8 19.5 8
  RingFlat $e 'm1' 19.5 4.4 0.3
  Bn 'ring_b' $null 8 19.5 8
  HaloV $e 'core2' 19.5 4.0 0.3 -lit
  Bn 'ring_c' $null 8 19.5 8
  HaloZ $e 'm2' 19.5 3.6 0.3
  Bn 'core' $null 8 19.5 8
  Add $e (C 8 19.5 8 1.8 1.8 1.8 'core' 45 -lit); Add $e (C 8 19.5 8 1.4 1.4 1.4 'core' 45 'x' -lit)
  Add $e (C 8 19.5 8 0.4 4 0.4 'hot' -lit); Add $e (C 8 19.5 8 3.2 0.4 0.4 'hot' -lit); Add $e (C 8 19.5 8 0.4 0.4 3.2 'hot' -lit)
  $script:BN = $null
  [void](Chain $e 8.9 25.2 8 'z' @(@(45, 1.3), @(0, 1.2), @(-45, 1.3)) 'core' 0.7 0.5 -lit -ChainBone 'crescent')
  Bn 'stars' $null 8 19.5 8
  foreach ($s in @(@(13, 23, 9), @(3.2, 16, 6.5), @(10, 26.5, 4), @(5.5, 24.5, 11.5))) { Add $e (C $s[0] $s[1] $s[2] 0.5 0.5 0.5 'core2' 45 -lit) }
  $script:BN = $null
}
function Staff-Downfall($e) {   # Forbidden school (GeckoLib): black spear-staff, gold bands, black crescent ring with gold spikes, quasar inside
  $script:BN = 'root'
  Add $e (C 8 -1 8 1 27 1 'wood')
  foreach ($yy in @(-11, -6.5, 5, 9.5)) { Add $e (C 8 $yy 8 1.4 0.5 1.4 'm1') }
  foreach ($yy in @(-9.5, -8, -5)) { Add $e (C 8 $yy 8 1.2 0.35 1.2 'm2') }
  # middle diamond
  Add $e (C 8 0 8 2.8 2.8 0.9 'm1' 45 'z'); Add $e (C 8 0 8 2.0 2.0 1.0 'm2' 45 'z'); Add $e (C 8 0 8 0.9 0.9 1.1 'hot' 45 'z' -lit)
  Add $e (C 8 2.6 8 0.5 1.0 0.5 'm1' 45); Add $e (C 8 -2.6 8 0.5 1.0 0.5 'm1' 45)
  # lower spear
  Add $e (C 8 -14.5 8 1.5 0.8 1.5 'm1'); Add $e (C 8 -15.1 8 0.9 0.9 0.35 'm1' 45 'z')
  # collar and socket under the ring
  Add $e (C 8 12.9 8 1.7 1.0 1.7 'm1'); Add $e (C 8 13.7 8 2.3 0.5 2.3 'm1' 45); Add $e (C 8 14.4 8 1.1 0.9 1.1 'm2')
  # ring: black crescent open at the top, gold inner rim, gold spikes
  $script:BN = 'ring'
  Oct $e 'm2' 8 20.5 5.6 5.6 0.45 0.55 @('T')
  Oct $e 'm1' 8 20.5 5.0 5.0 0.15 0.62 @('T') -lit
  Teeth $e 'm1' 8 20.5 6.3 -45 225 9 0.75 0.4
  [void](Chain $e 5.7 25.2 8 'z' @(@(-22.5, 1.3), @(-45, 1.1)) 'm2' 0.9 0.5 -tipMat 'm1' -tipSize 0.5)
  [void](Chain $e 10.3 25.2 8 'z' @(@(22.5, 1.3), @(45, 1.1)) 'm2' 0.9 0.5 -tipMat 'm1' -tipSize 0.5)
  # quasar: black hole with gold edge, photon ring, tilted accretion disk, jets, orbiting gold debris
  $script:BN = 'quasar'
  Add $e (C 8 20.5 8 2.2 2.2 2.2 'hole'); Add $e (C 8 20.5 8 2.0 2.0 2.0 'hole' 45); Add $e (C 8 20.5 8 2.0 2.0 2.0 'hole' 45 'x')
  HaloV $e 'core2' 20.5 1.55 0.14 -lit
  $script:BN = 'disk'
  $rot = Rot 22.5 'x' @(8, 20.5, 8)
  foreach ($ring in @(@(1.7, 10, 0.95, 'core2'), @(2.4, 14, 0.9, 'core'), @(3.1, 18, 0.8, 'core'), @(3.8, 22, 0.6, 'hot'))) {
    for ($i = 0; $i -lt $ring[1]; $i++) {
      $a = $i * 2 * [Math]::PI / $ring[1] + $ring[0]; $s = $ring[2]; $px = 8 + $ring[0] * [Math]::Cos($a); $pz = 8 + $ring[0] * [Math]::Sin($a)
      Add $e (Box @(($px - $s / 2), (20.42), ($pz - $s / 2)) @(($px + $s / 2), (20.58), ($pz + $s / 2)) $ring[3] $rot -lit)
    }
  }
  $script:BN = 'jets'
  Add $e (C 8 22.9 8 0.3 2.6 0.3 'core2' -lit); Add $e (C 8 18.1 8 0.3 2.6 0.3 'core2' -lit)
  Add $e (C 8 22.6 8 0.6 1.6 0.6 'hot' -lit); Add $e (C 8 18.4 8 0.6 1.6 0.6 'hot' -lit)
  $script:BN = 'orbit'
  foreach ($o in @(@(4.4, 0), @(-4.4, 0), @(0, 4.4), @(0, -4.4))) { Add $e (C (8 + $o[0]) 20.5 (8 + $o[1]) 0.45 0.45 0.45 'm1' 45 -lit) }
  $script:BN = $null
}

# GeckoLib geo + animations + glow mask from the tagged elements (bone 'disk' carries the tilt, its cubes drop their own rotation)
$GEO_BONES = [ordered]@{
  root = @{ pivot = @(0, 0, 0) }
  ring = @{ parent = 'root'; pivot = @(0, 20.5, 0) }
  quasar = @{ parent = 'root'; pivot = @(0, 20.5, 0) }
  disk_tilt = @{ parent = 'quasar'; pivot = @(0, 20.5, 0); rotation = @(-22.5, 0, 0) }
  disk = @{ parent = 'disk_tilt'; pivot = @(0, 20.5, 0); drop = $true }
  jets = @{ parent = 'quasar'; pivot = @(0, 20.5, 0) }
  orbit = @{ parent = 'quasar'; pivot = @(0, 20.5, 0) }
}
function Write-Geo($name, $els, $geoDir, $GB) {
  $cubes = @{}; foreach ($b in $GB.Keys) { $cubes[$b] = New-Object System.Collections.ArrayList }
  foreach ($el in $els) {
    $b = $el['_b']; if (-not $b) { $b = 'root' }
    if (-not $GB.Contains($b)) { throw "$name : unknown bone $b" }
    $f = $el.from; $t = $el.to
    $cube = [ordered]@{ origin = @((R3 (8 - $t[0])), (R3 $f[1]), (R3 ($f[2] - 8))); size = @((R3 ($t[0] - $f[0])), (R3 ($t[1] - $f[1])), (R3 ($t[2] - $f[2]))) }
    if ($el.rotation -and -not $GB[$b].drop) {
      $o = $el.rotation.origin; $cube.pivot = @((R3 (8 - $o[0])), (R3 $o[1]), (R3 ($o[2] - 8)))
      $a = [double]$el.rotation.angle
      $cube.rotation = switch ($el.rotation.axis) { 'x' { @(-$a, 0, 0) } 'y' { @(0, -$a, 0) } 'z' { @(0, 0, $a) } }
    }
    $uv = [ordered]@{}
    foreach ($fn in $el.faces.Keys) { $u = $el.faces[$fn].uv; $uv[$fn] = [ordered]@{ uv = @((2 * $u[0]), (2 * $u[1])); uv_size = @((2 * ($u[2] - $u[0])), (2 * ($u[3] - $u[1]))) } }
    $cube.uv = $uv
    [void]$cubes[$b].Add($cube)
  }
  $bones = @()
  foreach ($b in $GB.Keys) {
    $d = $GB[$b]; $bo = [ordered]@{ name = $b }
    if ($d.parent) { $bo.parent = $d.parent }
    $bo.pivot = $d.pivot
    if ($d.rotation) { $bo.rotation = $d.rotation }
    if ($cubes[$b].Count -gt 0) { $bo.cubes = $cubes[$b] }
    $bones += $bo
  }
  $geo = [ordered]@{ format_version = '1.12.0'; 'minecraft:geometry' = @([ordered]@{
    description = [ordered]@{ identifier = "geometry.${name}"; texture_width = 32; texture_height = 32; visible_bounds_width = 4; visible_bounds_height = 4; visible_bounds_offset = @(0, 1, 0) }
    bones = $bones }) }
  New-Item -ItemType Directory -Force $geoDir | Out-Null
  [IO.File]::WriteAllText((Join-Path $geoDir "${name}.geo.json"), ($geo | ConvertTo-Json -Depth 14 -Compress), (New-Object Text.UTF8Encoding $false))
}

# ======================= animations =======================
# Channels are sampled sums of terms on a base vector (geo space, degrees / pixels / scale factors). A loop of length L must hold
# whole cycles so it closes seamlessly. Terms:
#   @('S', turns, ax, ay, az)        spin: axis * 360 * turns * u
#   @('W', cycles, phase, x, y, z)   wave: vec * sin(2pi (cycles u + phase))
#   @('F', cycles, phase, x, y, z)   saw:  vec * frac(cycles u + phase)          (rising sparks)
#   @('A', cycles, phase, x, y, z)   arch: vec * sin(pi frac(cycles u + phase))  (grow then shrink, zero at both ends)
$IC = [Globalization.CultureInfo]::InvariantCulture
function Tk([double]$tv) { $tv.ToString('0.####', $IC) }
$R0 = @(0, 0, 0); $S1 = @(1, 1, 1)
function Ch([double]$len, $base, $terms) {
  if ($terms -and $terms[0] -is [string]) { $terms = , $terms }
  $nS = 8
  foreach ($tm in $terms) { if ($tm[0] -ne 'S') { $nS = [Math]::Max($nS, [Math]::Min(96, [int](16 * $tm[1]))) } }
  $o = [ordered]@{}
  for ($i = 0; $i -le $nS; $i++) {
    $u = $i / $nS; $vx = [double]$base[0]; $vy = [double]$base[1]; $vz = [double]$base[2]
    foreach ($tm in $terms) {
      if ($tm[0] -eq 'S') { $mm = 360 * $tm[1] * $u; $vx += $tm[2] * $mm; $vy += $tm[3] * $mm; $vz += $tm[4] * $mm; continue }
      $ph = $tm[1] * $u + $tm[2]; $fr = $ph - [Math]::Floor($ph)
      if ($i -eq $nS -and $fr -lt 1e-9 -and $tm[0] -eq 'F') { $fr = 0 }
      $mm = switch ($tm[0]) { 'W' { [Math]::Sin(2 * [Math]::PI * $ph) } 'F' { $fr } 'A' { [Math]::Sin([Math]::PI * $fr) } }
      $vx += $tm[3] * $mm; $vy += $tm[4] * $mm; $vz += $tm[5] * $mm
    }
    $o[(Tk ($len * $u))] = @((R3 $vx), (R3 $vy), (R3 $vz))
  }
  $o
}
# raw keyframes: K @(t, x, y, z) @(t, x, y, z) ...
function K { $o = [ordered]@{}; foreach ($a in $args) { $o[(Tk $a[0])] = @((R3 $a[1]), (R3 $a[2]), (R3 $a[3])) }; $o }
# heartbeat on a uniform scale: 'tuk-tuk' per beat, beats evenly spread over len
function HB([double]$len, [int]$beats, [double]$amp, [double]$delay = 0) {
  $o = [ordered]@{}; $o['0'] = @(1, 1, 1)
  $per = $len / $beats
  for ($bt = 0; $bt -lt $beats; $bt++) {
    $t0 = $bt * $per + $delay
    foreach ($kv in @(@(0, 0), @(0.08, 1), @(0.16, 0.15), @(0.24, 0.7), @(0.38, 0))) {
      $tt = $t0 + $kv[0] * [Math]::Min(1, $per / 0.6)
      if ($tt -gt 0 -and $tt -lt $len) { $s = 1 + $amp * $kv[1]; $o[(Tk $tt)] = @((R3 $s), (R3 $s), (R3 $s)) }
    }
  }
  $o[(Tk $len)] = @(1, 1, 1); $o
}
# on/off flicker on scale, deterministic per seed, step seconds
function Flick([double]$len, [double]$step, [int]$seed, [double]$on = 0.65) {
  $rnd = New-Object Random $seed; $o = [ordered]@{}; $n = [int][Math]::Round($len / $step)
  for ($i = 0; $i -le $n; $i++) {
    $s = if ($i -eq $n) { $o['0'][0] } elseif ($rnd.NextDouble() -lt $on) { 1 } else { 0 }
    $o[(Tk ($i * $step))] = @($s, $s, $s)
  }
  $o
}
# ticking pendulum (a clock hand): alternates +-amp every 'every' seconds with a quick snap
function Tick([double]$len, [double]$every, [double]$amp, $axis) {
  $o = [ordered]@{}; $n = [int][Math]::Round($len / $every); $prev = $amp
  $o['0'] = @(($axis[0] * $amp), ($axis[1] * $amp), ($axis[2] * $amp))
  for ($i = 1; $i -le $n; $i++) {
    $cur = if ($i % 2 -eq 0) { $amp } else { -$amp }
    $tt = $i * $every
    if ($i -eq $n) { $o[(Tk ($len - 0.06))] = @(($axis[0] * $prev), ($axis[1] * $prev), ($axis[2] * $prev)); $o[(Tk $len)] = $o['0']; break }
    $o[(Tk $tt)] = @(($axis[0] * $prev), ($axis[1] * $prev), ($axis[2] * $prev))
    $o[(Tk ($tt + 0.06))] = @(($axis[0] * $cur), ($axis[1] * $cur), ($axis[2] * $cur))
    $prev = $cur
  }
  $o
}
function Bo($rot = $null, $pos = $null, $scl = $null) { $d = [ordered]@{}; if ($rot) { $d.rotation = $rot }; if ($pos) { $d.position = $pos }; if ($scl) { $d.scale = $scl }; $d }
function An([double]$len, [bool]$loop, $bones) { @{ len = $len; loop = $loop; bones = $bones } }
function Write-Anim($name, $spec) {
  $anims = [ordered]@{}
  foreach ($k in @('idle', 'cast', 'flash')) { $a = $spec[$k]; $anims[$k] = [ordered]@{ loop = $a.loop; animation_length = $a.len; bones = $a.bones } }
  $doc = [ordered]@{ format_version = '1.8.0'; animations = $anims }
  New-Item -ItemType Directory -Force (Join-Path $assets 'animations\item') | Out-Null
  [IO.File]::WriteAllText((Join-Path $assets "animations\item\${name}.animation.json"), ($doc | ConvertTo-Json -Depth 12 -Compress), (New-Object Text.UTF8Encoding $false))
}

function Anim-Fire {
  $b = [ordered]@{}
  $b.flames = Bo (Ch 4 $R0 @('S', 1, 0, 1, 0))
  $b.flame_a = Bo $null $null (Ch 4 $S1 @('W', 4, 0, 0.08, 0.22, 0.08))
  $b.flame_b = Bo (Ch 4 $R0 @('S', -2, 0, 1, 0)) $null (Ch 4 $S1 @('W', 4, 0.5, 0.1, 0.28, 0.1))
  $b.flame_c = Bo $null $null (Ch 4 $S1 @('W', 8, 0.25, 0.15, 0.3, 0.15))
  $b.coals = Bo $null $null (Ch 4 $S1 @('W', 2, 0, 0.05, 0.12, 0.05))
  for ($k = 0; $k -lt 5; $k++) { $b["ember$k"] = Bo $null $null (Ch 4 $S1 @('W', 2, ($k * 0.21), 0.35, 0.35, 0.35)) }
  for ($k = 0; $k -lt 3; $k++) { $b["spark$k"] = Bo $null (Ch 4 $R0 @('F', 3, ($k / 3.0), 0, 9, 0)) (Ch 4 $R0 @('A', 3, ($k / 3.0), 1.2, 1.2, 1.2)) }
  $c = [ordered]@{}
  $c.flames = Bo (Ch 1 $R0 @('S', 1, 0, 1, 0)) $null (Ch 1 @(1.3, 1.8, 1.3) @('W', 2, 0, 0.1, 0.25, 0.1))
  $c.flame_a = Bo $null $null (Ch 1 $S1 @('W', 3, 0, 0.1, 0.3, 0.1))
  $c.flame_b = Bo (Ch 1 $R0 @('S', -2, 0, 1, 0)) $null (Ch 1 $S1 @('W', 3, 0.5, 0.12, 0.35, 0.12))
  $c.flame_c = Bo $null $null (Ch 1 $S1 @('W', 4, 0.25, 0.2, 0.4, 0.2))
  $c.coals = Bo $null $null (Ch 1 @(1.2, 1.3, 1.2) @('W', 2, 0, 0.1, 0.2, 0.1))
  for ($k = 0; $k -lt 5; $k++) { $c["ember$k"] = Bo $null $null (Ch 1 @(1.3, 1.3, 1.3) @('W', 2, ($k * 0.21), 0.4, 0.4, 0.4)) }
  for ($k = 0; $k -lt 3; $k++) { $c["spark$k"] = Bo $null (Ch 1 $R0 @('F', 2, ($k / 3.0), 0, 14, 0)) (Ch 1 $R0 @('A', 2, ($k / 3.0), 1.5, 1.5, 1.5)) }
  $f = [ordered]@{}
  $f.flames = Bo $null $null (K @(0, 1.3, 1.8, 1.3) @(0.15, 1.6, 3.0, 1.6) @(0.5, 1.2, 1.5, 1.2) @(1, 1, 1, 1))
  $f.coals = Bo $null $null (K @(0, 1, 1, 1) @(0.12, 1.6, 1.6, 1.6) @(1, 1, 1, 1))
  for ($k = 0; $k -lt 3; $k++) { $f["spark$k"] = Bo $null (K @(0, 0, 0, 0) @(1, 0, (14 + 3 * $k), 0)) (K @(0, 1.5, 1.5, 1.5) @(1, 0, 0, 0)) }
  @{ idle = (An 4 $true $b); cast = (An 1 $true $c); flash = (An 1 $false $f) }
}
function Anim-Blood {
  $b = [ordered]@{}; $c = [ordered]@{}; $f = [ordered]@{}
  $b.heart = Bo $null $null (HB 2.4 2 0.18); $b.veins = Bo $null $null (HB 2.4 2 0.12 0.06)
  $c.heart = Bo $null $null (HB 0.6 1 0.3); $c.veins = Bo $null $null (HB 0.6 1 0.2 0.04)
  $f.heart = Bo $null $null (K @(0, 1, 1, 1) @(0.15, 0.6, 0.6, 0.6) @(0.35, 1.6, 1.6, 1.6) @(0.8, 1, 1, 1))
  foreach ($lv in 0..2) {
    $ax = if ($lv -eq 1) { @(1, 0, 0) } else { @(0, 0, 1) }
    foreach ($sd in @(@('a', 1), @('b', -1))) {
      $s = $sd[1]; $n = "rib$lv$($sd[0])"
      $b[$n] = Bo (Ch 2.4 $R0 @('W', 1, 0, ($ax[0] * 6 * $s), 0, ($ax[2] * 6 * $s)))
      $c[$n] = Bo (Ch 0.6 @(($ax[0] * 12 * $s), 0, ($ax[2] * 12 * $s)) @('W', 1, 0, ($ax[0] * 5 * $s), 0, ($ax[2] * 5 * $s)))
      $f[$n] = Bo (K @(0, ($ax[0] * 12 * $s), 0, ($ax[2] * 12 * $s)) @(0.3, ($ax[0] * 26 * $s), 0, ($ax[2] * 26 * $s)) @(0.8, 0, 0, 0))
    }
  }
  @{ idle = (An 2.4 $true $b); cast = (An 0.6 $true $c); flash = (An 0.8 $false $f) }
}
function Anim-Eldritch {
  $b = [ordered]@{}; $c = [ordered]@{}; $f = [ordered]@{}
  $T = $script:ELD_T
  for ($k = 0; $k -lt $T.Count; $k++) {
    $isX = ($T[$k][3] -eq 'x'); $segs = $T[$k][4]; $a0 = [double]$segs[0][0]
    $bias = if ($isX) { -[Math]::Sign($a0) * 14 } else { [Math]::Sign($a0) * 14 }
    for ($i = 0; $i -lt $segs.Count; $i++) {
      $am = 5 + 1.5 * $i; $ph = $k * 0.13 + $i * 0.12
      $v = if ($isX) { @($am, 0, 0) } else { @(0, 0, $am) }
      $b["t${k}_$i"] = Bo (Ch 6 $R0 @('W', 2, $ph, $v[0], $v[1], $v[2]))
      $cb = if ($i -eq 0) { if ($isX) { @($bias, 0, 0) } else { @(0, 0, $bias) } } else { $R0 }
      $c["t${k}_$i"] = Bo (Ch 1 $cb @('W', 1, $ph, (1.8 * $v[0]), 0, (1.8 * $v[2])))
      if ($i -eq 0) { $f["t${k}_0"] = Bo (K @(0, $cb[0], 0, $cb[2]) @(0.25, (2 * $cb[0]), 0, (2 * $cb[2])) @(0.6, 0, 0, 0)) }
    }
  }
  $b.eye = Bo (Ch 6 $R0 @(@('W', 1, 0, 0, 22, 0), @('W', 2, 0.25, 8, 0, 0)))
  $b.cage = Bo (Ch 6 $R0 @('S', 1, 0, 1, 0))
  $c.eye = Bo (Ch 1 $R0 @('W', 2, 0, 0, 6, 0)) $null (Ch 1 @(1.3, 1.3, 1.3) @('W', 2, 0, 0.05, 0.05, 0.05))
  $c.cage = Bo (Ch 1 $R0 @('S', 1, 0, 1, 0))
  $f.eye = Bo $null $null (K @(0, 1.3, 1.3, 1.3) @(0.1, 1.3, 0.1, 1.3) @(0.25, 1.3, 1.3, 1.3) @(0.6, 1, 1, 1))
  @{ idle = (An 6 $true $b); cast = (An 1 $true $c); flash = (An 0.6 $false $f) }
}
function Anim-Ender {
  $b = [ordered]@{}; $c = [ordered]@{}; $f = [ordered]@{}
  $b.crystal = Bo $null (Ch 4 $R0 @('W', 1, 0, 0, 1.2, 0))
  $b.cube_a = Bo (Ch 4 $R0 @('S', 1, 0, 1, 0)); $b.cube_b = Bo (Ch 4 $R0 @('S', -1, 1, 0, 0)); $b.gem = Bo (Ch 4 $R0 @('S', 1, 0, 0, 1))
  $b.shards = Bo (Ch 4 $R0 @('S', 1, 0, 1, 0)) (Ch 4 $R0 @('W', 2, 0, 0, 0.6, 0))
  $b.motes = Bo (Ch 4 $R0 @('S', -1, 0, 1, 0)) (Ch 4 $R0 @('W', 1, 0.3, 0, 0.8, 0))
  $c.crystal = Bo $null (Ch 1 @(0, 1.5, 0) @('W', 2, 0, 0, 0.6, 0))
  $c.cube_a = Bo (Ch 1 $R0 @('S', 1, 0, 1, 0)); $c.cube_b = Bo (Ch 1 $R0 @('S', -1, 1, 0, 0)); $c.gem = Bo (Ch 1 $R0 @('S', 1, 0, 0, 1))
  $c.shards = Bo (Ch 1 $R0 @('S', 1, 0, 1, 0)) $null (Ch 1 @(1.5, 1, 1.5) @('W', 2, 0, 0.08, 0, 0.08))
  $c.motes = Bo (Ch 1 $R0 @('S', -1, 0, 1, 0)) (Ch 1 @(0, 1, 0) @('W', 2, 0.3, 0, 0.8, 0))
  $f.crystal = Bo $null (K @(0, 0, 1.5, 0) @(0.15, 0, 4, 0) @(0.8, 0, 0, 0))
  $f.shards = Bo $null $null (K @(0, 1.5, 1, 1.5) @(0.2, 2.3, 1.2, 2.3) @(0.8, 1, 1, 1))
  $cl = @(@(0, 0, 4), @(0, 0, -4), @(4, 0, 0), @(-4, 0, 0))
  for ($k = 0; $k -lt 4; $k++) {
    $v = $cl[$k]
    $b["claw$k"] = Bo (Ch 4 $R0 @('W', 1, 0, $v[0], $v[1], $v[2]))
    $c["claw$k"] = Bo (Ch 1 @((2.5 * $v[0]), 0, (2.5 * $v[2])) @('W', 2, 0, $v[0], $v[1], $v[2]))
  }
  @{ idle = (An 4 $true $b); cast = (An 1 $true $c); flash = (An 0.8 $false $f) }
}
function Anim-Evocation {
  $b = [ordered]@{}; $c = [ordered]@{}; $f = [ordered]@{}
  $b.medallion = Bo (Ch 3 $R0 @(@('W', 1, 0, 0, 0, 8), @('W', 1, 0.25, 0, 10, 0)))
  $b.wisp = Bo $null (Ch 3 $R0 @('W', 1, 0, 0, 0.5, 0)) (Ch 3 $S1 @('W', 3, 0, 0.3, 0.3, 0.3))
  $c.medallion = Bo (Ch 1 $R0 @(@('W', 1, 0, 0, 0, 20), @('W', 2, 0.25, 0, 15, 0)))
  $c.wisp = Bo $null (Ch 1 $R0 @('W', 1, 0, 0, 0.8, 0)) (Ch 1 @(1.6, 1.6, 1.6) @('W', 4, 0, 0.3, 0.3, 0.3))
  $f.mask = Bo (K @(0, 0, 0, 0) @(0.8, 0, 360, 0))
  $f.wisp = Bo $null $null (K @(0, 1.6, 1.6, 1.6) @(0.15, 2.6, 2.6, 2.6) @(0.8, 1, 1, 1))
  @{ idle = (An 3 $true $b); cast = (An 1 $true $c); flash = (An 0.8 $false $f) }
}
function Anim-Holy {
  $b = [ordered]@{}; $c = [ordered]@{}; $f = [ordered]@{}
  foreach ($w in @(@('wing_r', -1), @('wing_l', 1))) {
    $s = $w[1]
    $b[$w[0]] = Bo (Ch 4 $R0 @('W', 1, 0, 0, 0, (5 * $s)))
    $c[$w[0]] = Bo (Ch 1 @(0, 0, (14 * $s)) @('W', 2, 0, 0, 0, (4 * $s)))
    $f[$w[0]] = Bo (K @(0, 0, 0, (14 * $s)) @(0.15, 0, 0, (-12 * $s)) @(0.4, 0, 0, (8 * $s)) @(0.7, 0, 0, 0))
  }
  $b.orb = Bo (Ch 4 $R0 @('S', 1, 0, 1, 0)) $null (Ch 4 $S1 @('W', 2, 0, 0.08, 0.08, 0.08))
  $b.orb_lift = Bo $null (Ch 4 $R0 @('W', 1, 0, 0, 0.4, 0))
  $b.stone = Bo $null $null (Ch 4 $S1 @('W', 4, 0, 0.04, 0.04, 0.04))
  $c.orb = Bo (Ch 1 $R0 @('S', 1, 0, 1, 0)) $null (Ch 1 @(1.2, 1.2, 1.2) @('W', 2, 0, 0.1, 0.1, 0.1))
  $c.orb_lift = Bo $null (Ch 1 @(0, 1.5, 0) @('W', 1, 0, 0, 0.3, 0))
  $c.stone = Bo $null $null (Ch 1 @(1.08, 1.08, 1.08) @('W', 4, 0, 0.05, 0.05, 0.05))
  $f.orb = Bo $null $null (K @(0, 1.2, 1.2, 1.2) @(0.15, 1.9, 1.9, 1.9) @(0.7, 1, 1, 1))
  @{ idle = (An 4 $true $b); cast = (An 1 $true $c); flash = (An 0.7 $false $f) }
}
function Anim-Lightning {
  $b = [ordered]@{}; $c = [ordered]@{}; $f = [ordered]@{}
  $b.teeth_low = Bo (Ch 12 $R0 @('W', 3, 0, 0, 0, 18)); $b.teeth_up = Bo (Ch 12 $R0 @('W', 3, 0.5, 0, 0, 18))
  $b.orb_low = Bo (Ch 12 $R0 @('S', 3, 0, 0, 1))
  $b.hourglass = Bo (K @(0, 0, 0, 0) @(5.4, 0, 0, 0) @(6, 0, 0, 180) @(11.4, 0, 0, 180) @(12, 0, 0, 360))
  $b.needle = Bo (Tick 12 1 6 @(0, 0, 1))
  $b.ring = Bo (Ch 12 $R0 @('S', 3, 0, 1, 0))
  $b.sparks = Bo (Ch 12 $R0 @('S', 1, 0, 1, 0)) $null (Ch 12 $S1 @('W', 6, 0, 0.15, 0.15, 0.15))
  $c.teeth_low = Bo (Ch 1 $R0 @('W', 2, 0, 0, 0, 30)); $c.teeth_up = Bo (Ch 1 $R0 @('W', 2, 0.5, 0, 0, 30))
  $c.orb_low = Bo (Ch 1 $R0 @('S', 2, 0, 0, 1))
  $c.hourglass = Bo (Ch 1 $R0 @('S', 1, 0, 0, 1))
  $c.needle = Bo (Tick 1 0.25 25 @(0, 0, 1))
  $c.ring = Bo (Ch 1 $R0 @('S', 2, 0, 1, 0))
  $c.sparks = Bo (Ch 1 $R0 @('S', 1, 0, 1, 0)) $null (Ch 1 @(1.3, 1.3, 1.3) @('W', 4, 0, 0.2, 0.2, 0.2))
  for ($k = 0; $k -lt 4; $k++) {
    $b["arc$k"] = Bo $null $null (Flick 12 0.25 (31 + $k))
    $c["arc$k"] = Bo $null $null (Flick 1 0.1 (57 + $k) 0.8)
    $f["arc$k"] = Bo $null $null (K @(0, 1, 1, 1) @(0.1, 1.8, 1.8, 1.8) @(0.6, 1, 1, 1))
  }
  $f.sparks = Bo $null $null (K @(0, 1.3, 1.3, 1.3) @(0.12, 2.2, 2.2, 2.2) @(0.6, 1, 1, 1))
  $f.orb_low = Bo $null $null (K @(0, 1, 1, 1) @(0.1, 1.5, 1.5, 1.5) @(0.6, 1, 1, 1))
  @{ idle = (An 12 $true $b); cast = (An 1 $true $c); flash = (An 0.6 $false $f) }
}
function Anim-Nature {
  $b = [ordered]@{}; $c = [ordered]@{}; $f = [ordered]@{}
  $b.jaw = Bo (Ch 4 @(-4, 0, 0) @('W', 1, 0, -4, 0, 0))
  $b.wisps = Bo (Ch 4 $R0 @('S', 1, 0, 1, 0))
  $c.jaw = Bo (Ch 1 @(-14, 0, 0) @('W', 2, 0, -4, 0, 0))
  $c.wisps = Bo (Ch 1 $R0 @('S', 1, 0, 1, 0))
  $f.jaw = Bo (K @(0, -16, 0, 0) @(0.08, 0, 0, 0) @(0.15, -3, 0, 0) @(0.5, 0, 0, 0))
  for ($k = 0; $k -lt 7; $k++) {
    $b["leaf$k"] = Bo (Ch 4 $R0 @('W', 1, ($k * 0.17), 8, 0, 6))
    $c["leaf$k"] = Bo (Ch 1 $R0 @('W', 2, ($k * 0.17), 14, 0, 10))
  }
  for ($k = 0; $k -lt 3; $k++) {
    $b["sprout$k"] = Bo (Ch 4 $R0 @('W', 2, ($k * 0.3), 0, 0, 10))
    $c["sprout$k"] = Bo (Ch 1 $R0 @('W', 2, ($k * 0.3), 0, 0, 16))
  }
  @{ idle = (An 4 $true $b); cast = (An 1 $true $c); flash = (An 0.5 $false $f) }
}
function Anim-Higher {
  $b = [ordered]@{}; $c = [ordered]@{}; $f = [ordered]@{}
  $b.disk = Bo (Ch 4 $R0 @('S', -1, 0, 1, 0)); $b.halo = Bo (Ch 4 $R0 @('S', 1, 0, 1, 0))
  $b.sphere = Bo $null $null (Ch 4 $S1 @('W', 2, 0, 0.06, 0.06, 0.06))
  $b.jet = Bo $null $null (Ch 4 $S1 @('W', 4, 0, 0, 0.3, 0))
  $c.disk = Bo (Ch 1 $R0 @('S', -2, 0, 1, 0)) $null (Ch 1 @(1.3, 1, 1.3) @('W', 2, 0, 0.05, 0, 0.05))
  $c.halo = Bo (Ch 1 $R0 @('S', 2, 0, 1, 0))
  $c.sphere = Bo $null $null (Ch 1 @(1.15, 1.15, 1.15) @('W', 2, 0, 0.06, 0.06, 0.06))
  $c.jet = Bo $null $null (Ch 1 @(1, 2, 1) @('W', 4, 0, 0.2, 0.6, 0.2))
  $c.claws = Bo $null $null (Ch 1 @(0.8, 1, 0.8) @('W', 2, 0, 0.04, 0, 0.04))
  $f.sphere = Bo $null $null (K @(0, 1.15, 1.15, 1.15) @(0.15, 0.3, 0.3, 0.3) @(0.4, 1.5, 1.5, 1.5) @(0.8, 1, 1, 1))
  $f.disk = Bo (K @(0, 0, 0, 0) @(0.8, 0, -540, 0))
  $f.jet = Bo $null $null (K @(0, 1, 2, 1) @(0.4, 1.6, 4, 1.6) @(0.8, 1, 1, 1))
  @{ idle = (An 4 $true $b); cast = (An 1 $true $c); flash = (An 0.8 $false $f) }
}
function Anim-Divine {
  $b = [ordered]@{}; $c = [ordered]@{}; $f = [ordered]@{}
  $b.halo_v = Bo (Ch 6 $R0 @('S', 1, 0, 1, 0)); $b.halo_z = Bo (Ch 6 $R0 @('S', -1, 0, 0, 1))
  $b.rays = Bo (Ch 6 $R0 @('S', 1, 0, 1, 0)) $null (Ch 6 $S1 @('W', 2, 0, 0.06, 0.06, 0.06))
  $b.rays_short = Bo $null $null (Ch 6 $S1 @('W', 2, 0.5, 0.12, 0.12, 0.12))
  $b.sun = Bo $null $null (Ch 6 $S1 @('W', 3, 0, 0.07, 0.07, 0.07))
  $b.crown = Bo (Ch 6 $R0 @('S', -1, 0, 1, 0)) (Ch 6 $R0 @('W', 1, 0, 0, 0.6, 0))
  $c.halo_v = Bo (Ch 1.5 $R0 @('S', 1, 0, 1, 0)); $c.halo_z = Bo (Ch 1.5 $R0 @('S', -1, 0, 0, 1))
  $c.rays = Bo (Ch 1.5 $R0 @('S', 1, 0, 1, 0)) $null (Ch 1.5 @(1.3, 1.3, 1.3) @('W', 3, 0, 0.08, 0.08, 0.08))
  $c.rays_short = Bo $null $null (Ch 1.5 @(1.2, 1.2, 1.2) @('W', 3, 0.5, 0.15, 0.15, 0.15))
  $c.sun = Bo $null $null (Ch 1.5 @(1.2, 1.2, 1.2) @('W', 3, 0, 0.08, 0.08, 0.08))
  $c.crown = Bo (Ch 1.5 $R0 @('S', -1, 0, 1, 0)) (Ch 1.5 @(0, 1.2, 0) @('W', 1, 0, 0, 0.4, 0))
  $f.sun = Bo $null $null (K @(0, 1.2, 1.2, 1.2) @(0.15, 2.2, 2.2, 2.2) @(0.8, 1, 1, 1))
  $f.rays = Bo $null $null (K @(0, 1.3, 1.3, 1.3) @(0.15, 1.6, 1.6, 1.6) @(0.8, 1, 1, 1))
  @{ idle = (An 6 $true $b); cast = (An 1.5 $true $c); flash = (An 0.8 $false $f) }
}
function Anim-Mythic {
  $b = [ordered]@{}; $c = [ordered]@{}; $f = [ordered]@{}
  $b.ring_a = Bo (Ch 12 $R0 @('S', 1, 1, 0, 0)); $b.ring_b = Bo (Ch 12 $R0 @('S', 2, 0, 1, 0)); $b.ring_c = Bo (Ch 12 $R0 @('S', -3, 0, 0, 1))
  $b.core = Bo (Ch 12 $R0 @('S', 3, 0, 1, 0)); $b.helix = Bo (Ch 12 $R0 @('S', 3, 0, 1, 0))
  $b.crescent = Bo (Ch 12 $R0 @('W', 2, 0, 0, 0, 6)); $b.stars = Bo (Ch 12 $R0 @('S', -1, 0, 1, 0))
  $c.ring_a = Bo (Ch 2 $R0 @('S', 1, 1, 0, 0)); $c.ring_b = Bo (Ch 2 $R0 @('S', -2, 0, 1, 0)); $c.ring_c = Bo (Ch 2 $R0 @('S', 2, 0, 0, 1))
  $c.core = Bo (Ch 2 $R0 @('S', 2, 0, 1, 0)) $null (Ch 2 @(1.4, 1.4, 1.4) @('W', 4, 0, 0.1, 0.1, 0.1))
  $c.helix = Bo (Ch 2 $R0 @('S', 2, 0, 1, 0)); $c.crescent = Bo (Ch 2 $R0 @('W', 2, 0, 0, 0, 12)); $c.stars = Bo (Ch 2 $R0 @('S', -1, 0, 1, 0))
  # flash: the three rings fold into one horizontal plane (concentric 4.4 / 4.0 / 3.6), flare, turn together, then part again
  $sc = K @(0, 1, 1, 1) @(0.2, 1, 1, 1) @(0.35, 1.45, 1.45, 1.45) @(0.6, 1.3, 1.3, 1.3) @(1, 1, 1, 1)
  $f.ring_a = Bo (K @(0, 0, 0, 0) @(0.2, 0, 0, 0) @(0.65, 0, 120, 0) @(1, 0, 180, 0)) $null $sc
  $f.ring_b = Bo (K @(0, 0, 0, 0) @(0.2, 90, 0, 0) @(0.65, 90, -120, 0) @(1, 0, -180, 0)) $null $sc
  # GeckoLib applies Z, then Y, then X to the pose: a Y turn on top of the Z fold would tilt ring_c out of the plane, so it only folds
  $f.ring_c = Bo (K @(0, 0, 0, 0) @(0.2, 0, 0, 90) @(0.65, 0, 0, 90) @(1, 0, 0, 0)) $null $sc
  $f.core = Bo $null $null (K @(0, 1.4, 1.4, 1.4) @(0.15, 1.4, 1.4, 1.4) @(0.35, 2.2, 2.2, 2.2) @(1, 1, 1, 1))
  @{ idle = (An 12 $true $b); cast = (An 2 $true $c); flash = (An 1 $false $f) }
}
$DOWNFALL_ANIM = @'
{"format_version":"1.8.0","animations":{
"idle":{"loop":true,"animation_length":4,"bones":{
 "disk":{"rotation":{"0":[0,0,0],"2":[0,-180,0],"4":[0,-360,0]}},
 "orbit":{"rotation":{"0":[0,0,0],"2":[0,180,0],"4":[0,360,0]}},
 "quasar":{"position":{"0":[0,0,0],"2":[0,0.35,0],"4":[0,0,0]}},
 "jets":{"scale":{"0":[1,1,1],"1":[1,1.3,1],"2":[1,0.85,1],"3":[1,1.2,1],"4":[1,1,1]}}}},
"cast":{"loop":true,"animation_length":1,"bones":{
 "disk":{"rotation":{"0":[0,0,0],"0.5":[0,-360,0],"1":[0,-720,0]},"scale":{"0":[1.25,1,1.25],"0.5":[1.45,1,1.45],"1":[1.25,1,1.25]}},
 "orbit":{"rotation":{"0":[0,0,0],"0.5":[0,360,0],"1":[0,720,0]},"scale":{"0":[1.3,1.3,1.3],"0.5":[1.15,1.15,1.15],"1":[1.3,1.3,1.3]}},
 "quasar":{"scale":{"0":[1.3,1.3,1.3],"0.5":[1.5,1.5,1.5],"1":[1.3,1.3,1.3]},"position":{"0":[0,0,0],"0.25":[0.08,0.05,0],"0.5":[-0.06,0,0.05],"0.75":[0,-0.05,-0.06],"1":[0,0,0]}},
 "jets":{"scale":{"0":[1,2.2,1],"0.25":[1.2,2.8,1.2],"0.5":[1,2.0,1],"0.75":[1.2,2.9,1.2],"1":[1,2.2,1]}},
 "ring":{"position":{"0":[0,0,0],"0.5":[0,0.2,0],"1":[0,0,0]}}}},
"flash":{"loop":false,"animation_length":1,"bones":{
 "quasar":{"scale":{"0":[1.5,1.5,1.5],"0.2":[2.4,2.4,2.4],"0.6":[0.6,0.6,0.6],"1":[1,1,1]}},
 "jets":{"scale":{"0":[1,2.2,1],"0.2":[1.6,4.5,1.6],"1":[1,1,1]}},
 "disk":{"rotation":{"0":[0,0,0],"1":[0,-540,0]}}}}}}
'@
function Write-Glowmask($name, $mats) {
  $src = New-Object Drawing.Bitmap (Join-Path $texDir "${name}.png")
  $gm = New-Object Drawing.Bitmap 32, 32, ([Drawing.Imaging.PixelFormat]::Format32bppArgb)
  foreach ($m in $mats) {
    $u = $UVMAP[$m]
    for ($yy = 2 * $u[1]; $yy -lt 2 * $u[3]; $yy++) { for ($xx = 2 * $u[0]; $xx -lt 2 * $u[2]; $xx++) {
      $c = $src.GetPixel($xx, $yy)
      if ($m -eq 'gem' -and ($c.R + $c.G + $c.B) -lt 60) { continue }
      $gm.SetPixel($xx, $yy, $c) } }
  }
  $gm.Save((Join-Path $texDir "${name}_glowmask.png"), [Drawing.Imaging.ImageFormat]::Png); $gm.Dispose(); $src.Dispose()
}

# ======================= palettes =======================
$GOLD = @('#FFE08A', '#D9952A', '#F2B640', '#8A4E10')
$SCHOOLS = [ordered]@{
  fire = @{ fn = 'Staff-Fire'; shaft = @('#2A1810', '#3B2418', '#4A2E1E', '#33200F'); cracks = @('#FF6A1A', '#B83A0E'); m1 = $GOLD; m2 = @('#5A5258', '#3A3438', '#2E292C', '#1A1618')
    core = @('#FFF1B0', '#FFC83A', '#FF8A1E', '#D9420E'); hot = @('#FFD24A', '#FFF6D0'); plane = 'flame'; pc = @('#FFF6D0', '#FFD24A', '#FF8A1E', '#E0400E') }
  blood = @{ fn = 'Staff-Blood'; shaft = @('#22070A', '#33090E', '#2A0B0C', '#3D1014'); cracks = @('#B0121E', '#6A0A12'); m1 = @('#F4ECD6', '#DCCFAE', '#E8DDBF', '#8E7F60'); m2 = @('#5A1E22', '#45161A', '#3A1215', '#1E0709')
    core = @('#FF6A6A', '#D01828', '#9A0A16', '#5A040C'); hot = @('#C0101C', '#FF8A8A'); gem = 'orb'; gc = @('#FF9A9A', '#E0202E', '#A00A18', '#58040C') }
  eldritch = @{ fn = 'Staff-Eldritch'; shaft = @('#0C1618', '#122024', '#0A1214', '#16282C'); cracks = @('#3FE0D0', '#1E8C84'); m1 = @('#5FB8B0', '#2E6E6A', '#3E8C86', '#123634'); m2 = @('#2A2E36', '#1C2026', '#14171C', '#08090C')
    core = @('#B8FFF6', '#3FE0D0', '#1E9C92', '#0C4A46'); hot = @('#1E9C92', '#B8FFF6'); gem = 'eye'; gc = @('#3FE0D0', '#1E8C84', '#0E3A38', '#06201E'); frame = @('#3FE0D0', '#1E5E5A') }
  ender = @{ fn = 'Staff-Ender'; shaft = @('#140E1E', '#1C1428', '#100A18', '#22182E'); cracks = @('#C054FF', '#6A2A9A'); m1 = @('#E8E6B8', '#D6D2A0', '#C4BF8C', '#7E7A50'); m2 = @('#D8B4F0', '#A97BD0', '#B58CD8', '#5E3A80')
    m3 = @('#3A2A4E', '#22182E', '#1A1224', '#08050C'); core = @('#F4D8FF', '#C054FF', '#8A2AD0', '#4A1080'); hot = @('#2FC8A0', '#B8FFE8'); core2 = @('#FFE0FF', '#E08AFF', '#B054E0', '#6A2A9A')
    gem = 'ender'; gc = @('#7CF0B0', '#2FA878', '#16604A', '#0A2A20'); frame = @('#F4D8FF', '#C054FF') }
  evocation = @{ fn = 'Staff-Evocation'; shaft = @('#3A2618', '#2E1E12', '#46301E', '#24170C'); m1 = $GOLD; m2 = @('#9A7A50', '#6A4E30', '#7E6040', '#3A2814'); m3 = @('#A8B4CC', '#6E7C96', '#8492AC', '#3A4458'); m4 = @('#F4ECD6', '#DCCFAE', '#E8DDBF', '#8E7F60')
    core = @('#D8FFE0', '#3ED87A', '#18A050', '#0A5A2A'); hot = @('#3ED87A', '#E8FFF0'); p2 = 'totem'; p2c = @('#FFE08A', '#D9952A', '#8A4E10', '#3ED87A', '#1A0E06') }
  holy = @{ fn = 'Staff-Holy'; shaft = @('#E8B848', '#D9A23A', '#F2C860', '#B88428'); m1 = @('#FFF0B0', '#F2C24A', '#FFD86A', '#A0701A'); m2 = @('#D9A23A', '#B07C20', '#C48E2A', '#6A4A10'); m3 = @('#FFFFFF', '#F0EEE8', '#E6E2D8', '#B8B2A2')
    core = @('#FFFFFF', '#FFFFFF', '#FFFBEA', '#FFF0B8'); hot = @('#FFE9A0', '#FFFFFF'); gem = 'orb'; gc = @('#E8F4FF', '#6AB4FF', '#2A6AD8', '#12306A'); wide = 'feather'; wc = @('#FFFFFF', '#F2F0EA', '#D8D4CA', '#E8B848') }
  lightning = @{ fn = 'Staff-Lightning'; shaft = @('#C87A44', '#B06A38', '#D88A50', '#9A5A2E'); m1 = @('#F6B07A', '#D9824A', '#E89A62', '#7A3E1C'); m2 = @('#A8723E', '#7A4E26', '#8E5E30', '#3A220E')
    core = @('#FFFFFF', '#B8FFF4', '#5AE8D8', '#1A8A80'); hot = @('#5AE8D8', '#FFFFFF'); core2 = @('#E8FFFA', '#8AF4E6', '#3ACCBC', '#1A7A70'); gem = 'orb'; gc = @('#FFFFFF', '#A8FFF0', '#3ADCC8', '#167A70'); plane = 'arcs'; pc = @('#FFFFFF', '#B8FFF4', '#5AE8D8', '#1A8A80') }
  nature = @{ fn = 'Staff-Nature'; shaft = @('#3A2418', '#4A2E1E', '#2E1C12', '#56362A'); m1 = @('#B8F07A', '#7AC83A', '#94DC52', '#3A6A16'); m2 = @('#1A1612', '#120E0B', '#161210', '#0A0806'); m4 = @('#F2EEE0', '#DCD6C2', '#E8E2D0', '#8E8670')
    core = @('#F0FFD0', '#B8F070', '#88D040', '#4A8A1E'); hot = @('#B8F070', '#F0FFD0'); gem = 'skull'; gc = @('#F2EEE0', '#C8C0A8', '#1A1612', '#9CFF5A'); wide = 'leaf'; wc = @('#B8F07A', '#6AB82E', '#4A9620', '#2A6010') }
  higher = @{ fn = 'Staff-Higher'; shaft = @('#160A0C', '#1E0E10', '#120809', '#261214'); cracks = @('#FF3B3B', '#A01818'); m1 = @('#6A3036', '#3A1A1E', '#4E2228', '#160809'); m2 = @('#3A3034', '#2A2226', '#201A1C', '#0C0A0A')
    core = @('#FFD0D0', '#FF5A5A', '#E01E28', '#7A0A10'); hot = @('#FF3B3B', '#FFE0E0'); core2 = @('#FFC0C0', '#FF6060', '#FF3B3B', '#C01818'); gem = 'void'; gc = @('#FF5050', '#A01018', '#3A0408') }
  divine = @{ fn = 'Staff-Divine'; shaft = @('#F6F3EA', '#EAE4D4', '#FFFDF6', '#DCD4C0'); cracks = @('#FFD34D', '#E8B030'); m1 = @('#FFF0B0', '#FFD34D', '#FFE07A', '#B08418'); m2 = @('#FFFFFF', '#F0F0F6', '#E0E2EA', '#9A9EAE')
    core = @('#FFFFFF', '#FFF8D8', '#FFE48A', '#FFC838'); hot = @('#FFD34D', '#FFFFFF'); p2 = 'sun'; p2c = @('#FFFFFF', '#FFF6C8', '#FFD34D', '#F0B030', '#C88A18') }
  mythic = @{ fn = 'Staff-Mythic'; shaft = @('#14122A', '#1C1838', '#100E22', '#242046'); cracks = @('#FFFFFF', '#B07CFF'); m1 = @('#F4F4FF', '#B8B8D8', '#CACAE6', '#5A5A7A'); m2 = @('#8A5AC8', '#5A2E90', '#6E3EA8', '#22103A')
    core = @('#FFE8FF', '#E08AFF', '#A040E8', '#4A1080'); hot = @('#C890FF', '#FFFFFF'); core2 = @('#FFFFFF', '#E0E8FF', '#A8B8FF', '#6A60D0') }
  downfall = @{ fn = 'Staff-Downfall'; geo = $true; shaft = @('#0A0806', '#120E0A', '#070504', '#16110C'); cracks = @('#D4A017', '#7A5A0A'); m1 = $GOLD; m2 = @('#2E2822', '#16120F', '#1E1A16', '#050404')
    core = @('#FFFFFF', '#FFEBA8', '#F2B640', '#B86A10'); hot = @('#FFD34D', '#FFF6D0'); core2 = @('#FFFFFF', '#FFF0C0', '#FFD34D', '#D9952A'); gem = 'void'; gc = @('#FFE08A', '#D4A017', '#3A2A08') }
}

$DISPLAY = [ordered]@{
  thirdperson_righthand = [ordered]@{ translation = @(0, 2, 1.25) }
  thirdperson_lefthand = [ordered]@{ translation = @(0, 2, 1.25) }
  firstperson_righthand = [ordered]@{ translation = @(1.5, -1, -2.75) }
  firstperson_lefthand = [ordered]@{ translation = @(1.5, -1, -2.75) }
  ground = [ordered]@{ translation = @(0, 8, 0); scale = @(0.5, 0.5, 0.5) }
  gui = [ordered]@{ rotation = @(-13, 128, 65); translation = @(0.5, -0.5, 0); scale = @(0.56, 0.56, 0.56) }
  fixed = [ordered]@{ translation = @(0, 0, -0.75); scale = @(0.48, 0.48, 0.48) }
}

$seedNo = 17
foreach ($name in $SCHOOLS.Keys) {
  $seedNo++
  if ($Only -and $Only -notcontains $name) { continue }
  $sd = $SCHOOLS[$name]
  $m3c = if ($sd.m3) { $sd.m3 } else { $sd.m2 }; $m4c = if ($sd.m4) { $sd.m4 } else { $sd.m1 }; $c2c = if ($sd.core2) { $sd.core2 } else { $sd.core }
  $script:bmp = New-Object Drawing.Bitmap 32, 32, ([Drawing.Imaging.PixelFormat]::Format32bppArgb)
  for ($yy = 0; $yy -lt 32; $yy++) { for ($xx = 0; $xx -lt 32; $xx++) { $script:bmp.SetPixel($xx, $yy, [Drawing.Color]::FromArgb(0, 0, 0, 0)) } }
  Paint-Shaft $sd.shaft $sd.cracks $seedNo
  Paint-Metal 2 0 $sd.m1; Paint-Metal 6 0 $sd.m2; Paint-Core 10 0 $sd.core; Paint-Hot $sd.hot
  Paint-Metal 2 8 $m3c; Paint-Metal 6 8 $m4c; Paint-Core 10 8 $c2c
  if ($sd.gem) { Paint-Gem $sd.gem $sd.gc }
  if ($sd.frame) { Paint-Frame $sd.frame }
  if ($sd.wide) { Paint-Wide $sd.wide $sd.wc }
  if ($sd.p2) { Paint-Plane2 $sd.p2 $sd.p2c }
  if ($sd.plane) { Paint-Plane $sd.plane $sd.pc }
  $script:bmp.Save((Join-Path $texDir "${name}_staff.png"), [Drawing.Imaging.ImageFormat]::Png); $script:bmp.Dispose()

  $els = New-Object System.Collections.ArrayList
  $script:BONES = $null; $script:BN = $null
  & $sd.fn $els
  $script:BN = $null
  foreach ($el in $els) { foreach ($v in @($el.from + $el.to)) { if ($v -lt -16 -or $v -gt 32) { throw "$name : coordinate $v out of -16..32" } } }
  if ($true) {   # every staff is a GeckoLib model now (idle / cast / flash)
    if ($name -eq 'downfall') {
      Write-Geo "${name}_staff" $els (Join-Path $assets 'geo\item') $GEO_BONES
      [IO.File]::WriteAllText((Join-Path $assets "animations\item\${name}_staff.animation.json"), $DOWNFALL_ANIM, (New-Object Text.UTF8Encoding $false))
      Write-Glowmask "${name}_staff" @('core', 'hot', 'core2', 'gem')
    } else {
      if (-not $script:BONES) { $script:BONES = [ordered]@{ root = @{ pivot = @(0, 0, 0) } } }
      Write-Geo "${name}_staff" $els (Join-Path $assets 'geo\item') $script:BONES
      $spec = & ($sd.fn -replace '^Staff-', 'Anim-')
      foreach ($k in @('idle', 'cast', 'flash')) { foreach ($bn in $spec[$k].bones.Keys) { if (-not $script:BONES.Contains($bn)) { throw "$name : animation '$k' names unknown bone $bn" } } }
      Write-Anim "${name}_staff" $spec
      $lit = @($els | Where-Object { $_.shade -eq $false } | ForEach-Object { $_['_m'] } | Sort-Object -Unique)
      Write-Glowmask "${name}_staff" $lit
    }
    foreach ($el in $els) { $el.Remove('_b'); $el.Remove('_m') }
    $prev = Join-Path $root 'tools\staff_preview'; New-Item -ItemType Directory -Force $prev | Out-Null
    $full = [ordered]@{ texture_size = @(32, 32); textures = [ordered]@{ '0' = "pohsmp_core:item/${name}_staff" }; elements = $els; display = $DISPLAY }
    [IO.File]::WriteAllText((Join-Path $prev "${name}_staff.json"), ($full | ConvertTo-Json -Depth 12 -Compress), (New-Object Text.UTF8Encoding $false))
    $item = [ordered]@{ parent = 'minecraft:builtin/entity'; textures = [ordered]@{ particle = "pohsmp_core:item/${name}_staff" }; gui_light = 'front'; display = $DISPLAY }
    [IO.File]::WriteAllText((Join-Path $modDir "${name}_staff.json"), ($item | ConvertTo-Json -Depth 12 -Compress), (New-Object Text.UTF8Encoding $false))
    "  ${name}_staff: $($els.Count) elements, $($(if ($name -eq 'downfall') { $GEO_BONES.Count } else { $script:BONES.Count })) bones (GeckoLib)"
    continue
  }
  $model = [ordered]@{
    credit = 'pohsmp_core, tools/gen_school_staffs.ps1'
    texture_size = @(32, 32)
    textures = [ordered]@{ '0' = "pohsmp_core:item/${name}_staff"; particle = "pohsmp_core:item/${name}_staff" }
    elements = $els
    display = $DISPLAY
  }
  [IO.File]::WriteAllText((Join-Path $modDir "${name}_staff.json"), ($model | ConvertTo-Json -Depth 12 -Compress), (New-Object Text.UTF8Encoding $false))
  "  ${name}_staff: $($els.Count) elements"
}
