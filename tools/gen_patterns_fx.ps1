# Рисует узоры и лучи для pohsmp_core (белое на чёрном со свечением, цвет даёт мод):
# pat_alchemy — алхимический круг (зодиак в поясе, 7 планет на гептаграмме, гексаграмма, солнце в центре);
# pat_metatron — куб Метатрона поверх цветка жизни, пояс рун Футарка;
# pat_zodiac — колесо зодиака с домами и звездой {12/5}; pat_mandala — лепестки в три яруса;
# pat_stars — вложенные звёздные многоугольники {5/2} {7/3} {8/3} {9/4} {12/5}; rays — солнечные лучи (512).
# Нужен futhark.png. Знаки — шрифт Segoe UI Symbol (Windows). Использование: tools\gen_patterns_fx.ps1 [папка_превью]
param([string]$Preview)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$root = Split-Path -Parent $PSScriptRoot
$fx = Join-Path $root 'mods-src\pohsmp_core\src\main\resources\assets\pohsmp_core\textures\fx'
$PI = [Math]::PI
$rng = New-Object Random 9001
$futhark = [Drawing.Image]::FromFile((Join-Path $fx 'futhark.png'))
$cmR = New-Object Drawing.Imaging.ColorMatrix
$cmR.Matrix00 = 0; $cmR.Matrix11 = 0; $cmR.Matrix22 = 0; $cmR.Matrix33 = 0; $cmR.Matrix03 = 1; $cmR.Matrix40 = 1; $cmR.Matrix41 = 1; $cmR.Matrix42 = 1
$runeIA = New-Object Drawing.Imaging.ImageAttributes; $runeIA.SetColorMatrix($cmR)

$script:S = 1024; $script:C = 512.0
function Layer([int]$size) { $script:S = $size; $script:C = $size / 2.0
  $b = New-Object Drawing.Bitmap $size, $size, ([Drawing.Imaging.PixelFormat]::Format32bppArgb)
  $g = [Drawing.Graphics]::FromImage($b); $g.SmoothingMode = 'AntiAlias'; $g.TextRenderingHint = 'AntiAlias'; $g.Clear([Drawing.Color]::Transparent); return @($b, $g) }
function WPen([double]$w, [int]$a = 255) { $p = New-Object Drawing.Pen ([Drawing.Color]::FromArgb($a, 255, 255, 255)), $w
  $p.StartCap = 'Round'; $p.EndCap = 'Round'; $p.LineJoin = 'Round'; return $p }
function P([double]$r, [double]$a) { New-Object Drawing.PointF ([float]($C + [Math]::Cos($a) * $r)), ([float]($C + [Math]::Sin($a) * $r)) }
function CircAt($g, [double]$x, [double]$y, [double]$r, [double]$w, [int]$a = 255) { $g.DrawEllipse((WPen $w $a), [float]($x - $r), [float]($y - $r), [float](2 * $r), [float](2 * $r)) }
function Circ($g, [double]$r, [double]$w, [int]$a = 255) { CircAt $g $C $C $r $w $a }
function Dot($g, [double]$x, [double]$y, [double]$r) { $g.FillEllipse([Drawing.Brushes]::White, [float]($x - $r), [float]($y - $r), [float](2 * $r), [float](2 * $r)) }
function Line($g, $p1, $p2, [double]$w, [int]$a = 255) { $g.DrawLine((WPen $w $a), $p1, $p2) }
function StarPoly($g, [double]$r, [int]$n, [int]$k, [double]$rot, [double]$w) {   # звёздный многоугольник {n/k}
  $pts = [Drawing.PointF[]]@(); for ($i = 0; $i -le $n; $i++) { $pts += P $r ($rot + $i * $k * 2 * $PI / $n) }
  $g.DrawLines((WPen $w), $pts) }
function Ticks($g, [double]$r, [int]$n, [double]$long, [double]$short, [double]$w) {
  for ($i = 0; $i -lt $n; $i++) { $a = $i * 2 * $PI / $n; $l = if ($i % 5 -eq 0) { $long } else { $short }; Line $g (P $r $a) (P ($r - $l) $a) $w } }
function Glyph($g, [string]$s, [double]$x, [double]$y, [double]$size, [double]$rotDeg) {   # знак шрифта, центр в (x,y), повёрнут
  $st = $g.Save(); $g.TranslateTransform([float]$x, [float]$y); $g.RotateTransform([float]$rotDeg)
  $path = New-Object Drawing.Drawing2D.GraphicsPath
  $sf = New-Object Drawing.StringFormat; $sf.Alignment = 'Center'; $sf.LineAlignment = 'Center'
  $path.AddString($s, (New-Object Drawing.FontFamily 'Segoe UI Symbol'), 0, [float]$size, (New-Object Drawing.PointF 0, 0), $sf)
  $g.FillPath([Drawing.Brushes]::White, $path); $g.Restore($st) }
function Rune($g, [int]$ri, [double]$x, [double]$y, [double]$size, [double]$rotDeg) {
  $st = $g.Save(); $g.TranslateTransform([float]$x, [float]$y); $g.RotateTransform([float]$rotDeg)
  $h = [int]($size / 2); $g.DrawImage($futhark, (New-Object Drawing.Rectangle (-$h), (-$h), ([int]$size), ([int]$size)), (($ri % 6) * 128 + 18), ([Math]::Floor($ri / 6) * 128 + 18), 92, 92, 'Pixel', $runeIA)
  $g.Restore($st) }
function Belt($g, [string[]]$glyphs, [double]$r, [double]$size, [bool]$runes) {   # знаки по кругу, низом к центру
  $n = $glyphs.Count; for ($i = 0; $i -lt $n; $i++) { $a = $i * 2 * $PI / $n - $PI / 2; $q = P $r $a
    if ($runes) { Rune $g ([int]$glyphs[$i]) $q.X $q.Y $size ($a * 180 / $PI + 90) } else { Glyph $g $glyphs[$i] $q.X $q.Y $size ($a * 180 / $PI + 90) } } }

function Blur($src, [int]$div) {
  $w = [int]($S / $div); $sm = New-Object Drawing.Bitmap $w, $w, ([Drawing.Imaging.PixelFormat]::Format32bppArgb)
  $g = [Drawing.Graphics]::FromImage($sm); $g.InterpolationMode = 'HighQualityBicubic'; $g.DrawImage($src, 0, 0, $w, $w); $g.Dispose()
  $big = New-Object Drawing.Bitmap $S, $S, ([Drawing.Imaging.PixelFormat]::Format32bppArgb)
  $g = [Drawing.Graphics]::FromImage($big); $g.InterpolationMode = 'HighQualityBicubic'; $g.PixelOffsetMode = 'Half'; $g.DrawImage($sm, 0, 0, $S, $S); $g.Dispose(); $sm.Dispose()
  return $big }
function Finish($b, $g, $name, [bool]$glow = $true) {
  $g.Dispose()
  $out = New-Object Drawing.Bitmap $S, $S, ([Drawing.Imaging.PixelFormat]::Format32bppArgb)
  $o = [Drawing.Graphics]::FromImage($out); $o.Clear([Drawing.Color]::Black)
  if ($glow) { foreach ($k in @(@(14, 1.0), @(5, 0.9))) {
    $bl = Blur $b $k[0]
    $cm = New-Object Drawing.Imaging.ColorMatrix; $cm.Matrix33 = [float]$k[1]
    $ia = New-Object Drawing.Imaging.ImageAttributes; $ia.SetColorMatrix($cm)
    for ($rep = 0; $rep -lt 2; $rep++) { $o.DrawImage($bl, (New-Object Drawing.Rectangle 0, 0, $S, $S), 0, 0, $S, $S, 'Pixel', $ia) }
    $bl.Dispose() } }
  $o.DrawImage($b, 0, 0, $S, $S); $o.Dispose(); $b.Dispose()
  $out.Save((Join-Path $fx "$name.png"), [Drawing.Imaging.ImageFormat]::Png)
  if ($Preview) { $out.Save((Join-Path $Preview "$name.png")) }
  $out.Dispose(); "  $name.png" }

$ZOD = @(0x2648..0x2653 | ForEach-Object { [string][char]$_ })
$PLAN = @(@(0x2609, 0x263D, 0x263F, 0x2640, 0x2642, 0x2643, 0x2644) | ForEach-Object { [string][char]$_ })
$ALCH = @(@(0x1F701, 0x1F702, 0x1F703, 0x1F704, 0x1F70D, 0x1F714, 0x1F71A, 0x1F728) | ForEach-Object { [char]::ConvertFromUtf32($_) })

# ---- алхимический круг ----
$b, $g = Layer 1024
Circ $g 502 7; Circ $g 490 2.5; Circ $g 408 2.5; Circ $g 396 6
Belt $g $ZOD 449 54 $false
for ($i = 0; $i -lt 12; $i++) { $a = ($i + 0.5) * 2 * $PI / 12 - $PI / 2; Line $g (P 408 $a) (P 490 $a) 2.5; Dot $g (P 449 $a).X (P 449 $a).Y 5 }
StarPoly $g 380 7 3 (-$PI / 2) 3.5
StarPoly $g 380 7 2 (-$PI / 2) 2
for ($i = 0; $i -lt 7; $i++) { $q = P 380 ($i * 2 * $PI / 7 - $PI / 2)
  $g.FillEllipse([Drawing.Brushes]::Black, [float]($q.X - 40), [float]($q.Y - 40), 80, 80); CircAt $g $q.X $q.Y 40 5; CircAt $g $q.X $q.Y 31 2; Glyph $g $PLAN[$i] $q.X $q.Y 40 0 }
Circ $g 250 5; Circ $g 238 2
StarPoly $g 238 6 2 (-$PI / 2) 4; StarPoly $g 238 6 2 (-$PI / 6) 0.01
$g.DrawPolygon((WPen 3), [Drawing.PointF[]]@((P 238 (-$PI / 2)), (P 238 ($PI / 6)), (P 238 (5 * $PI / 6))))
$g.DrawPolygon((WPen 3), [Drawing.PointF[]]@((P 238 ($PI / 2)), (P 238 (-$PI / 6)), (P 238 (-5 * $PI / 6))))
for ($i = 0; $i -lt 6; $i++) { $q = P 175 ($i * $PI / 3); Glyph $g $ALCH[$i] $q.X $q.Y 34 ($i * 60 + 90) }
Circ $g 110 4; Circ $g 100 1.5
Glyph $g $PLAN[0] $C $C 120 0
for ($i = 0; $i -lt 24; $i++) { $a = $i * $PI / 12; Line $g (P 112 $a) (P 130 $a) 3 }
Finish $b $g 'pat_alchemy'

# ---- куб Метатрона и цветок жизни ----
$b, $g = Layer 1024
Circ $g 502 7; Circ $g 490 2.5; Circ $g 420 2.5; Circ $g 408 6
Belt $g @(0..23 | ForEach-Object { "$_" }) 455 62 $true
$r0 = 100.0
$centers = @(,@($C, $C))
for ($ring = 1; $ring -le 2; $ring++) { for ($i = 0; $i -lt 6; $i++) { $a = $i * $PI / 3 - $PI / 2
  for ($j = 0; $j -lt $ring; $j++) { $a2 = $a + 2 * $PI / 3
    $x = $C + [Math]::Cos($a) * $r0 * $ring + [Math]::Cos($a2) * $r0 * $j; $y = $C + [Math]::Sin($a) * $r0 * $ring + [Math]::Sin($a2) * $r0 * $j
    $centers += ,@($x, $y) } } }
foreach ($cc in $centers) { CircAt $g $cc[0] $cc[1] $r0 2 170 }    # цветок жизни (19 кругов)
Circ $g (3 * $r0) 3
$mc = @(,@($C, $C)); foreach ($k in @(1, 2)) { for ($i = 0; $i -lt 6; $i++) { $a = $i * $PI / 3 - $PI / 2; $mc += ,@(($C + [Math]::Cos($a) * 2 * $r0 * $k * 0.92), ($C + [Math]::Sin($a) * 2 * $r0 * $k * 0.92)) } }
for ($i = 0; $i -lt $mc.Count; $i++) { for ($j = $i + 1; $j -lt $mc.Count; $j++) { Line $g (New-Object Drawing.PointF ([float]$mc[$i][0]), ([float]$mc[$i][1])) (New-Object Drawing.PointF ([float]$mc[$j][0]), ([float]$mc[$j][1])) 2.5 } }
foreach ($cc in $mc) { CircAt $g $cc[0] $cc[1] ($r0 * 0.55) 4; Dot $g $cc[0] $cc[1] 6 }
Ticks $g 400 120 22 10 2.5
Finish $b $g 'pat_metatron'

# ---- колесо зодиака ----
$b, $g = Layer 1024
Circ $g 502 7; Circ $g 492 2; Circ $g 410 2.5; Circ $g 400 6
for ($i = 0; $i -lt 12; $i++) { $a = $i * 2 * $PI / 12 - $PI / 2 + $PI / 12; Line $g (P 410 $a) (P 492 $a) 3; Line $g (P 160 $a) (P 400 $a) 2 }
$ZODR = @(); for ($i = 0; $i -lt 12; $i++) { $ZODR += $ZOD[$i] }
Belt $g $ZODR 451 58 $false
for ($i = 0; $i -lt 360; $i += 2) { $a = $i * $PI / 180; $l = if ($i % 10 -eq 0) { 18 } else { 8 }; Line $g (P 400 $a) (P (400 - $l) $a) 1.6 }
Circ $g 360 2
for ($i = 0; $i -lt 12; $i++) { $a = $i * 2 * $PI / 12 - $PI / 2; $q = P 300 $a; Glyph $g ("{0}" -f [char](0x2160 + $i)) $q.X $q.Y 32 ($a * 180 / $PI + 90) }
Circ $g 240 2; Circ $g 160 5; Circ $g 150 2
StarPoly $g 150 12 5 (-$PI / 2) 2.5
for ($i = 0; $i -lt 7; $i++) { $q = P 205 ($i * 2 * $PI / 7 - $PI / 2); Glyph $g $PLAN[$i] $q.X $q.Y 34 0 }
Dot $g $C $C 14; Circ $g 32 3
Finish $b $g 'pat_zodiac'

# ---- мандала ----
$b, $g = Layer 1024
function Petals($g, [int]$n, [double]$r1, [double]$r2, [double]$wid, [double]$rot, [double]$w, [bool]$fill) {
  for ($i = 0; $i -lt $n; $i++) { $a = $rot + $i * 2 * $PI / $n
    $p0 = P $r1 $a; $p3 = P $r2 $a; $da = $wid * $PI / $n
    $pa = P ($r1 + ($r2 - $r1) * 0.45) ($a - $da); $pb = P ($r1 + ($r2 - $r1) * 0.45) ($a + $da)
    $path = New-Object Drawing.Drawing2D.GraphicsPath
    $path.AddBezier($p0, $pa, (P ($r1 + ($r2 - $r1) * 0.85) ($a - $da * 0.5)), $p3)
    $path.AddBezier($p3, (P ($r1 + ($r2 - $r1) * 0.85) ($a + $da * 0.5)), $pb, $p0)
    if ($fill) { $g.FillPath((New-Object Drawing.SolidBrush ([Drawing.Color]::FromArgb(70, 255, 255, 255))), $path) }
    $g.DrawPath((WPen $w), $path) } }
Circ $g 500 5; Circ $g 488 2
Petals $g 32 380 486 1.1 0 3 $false
Petals $g 32 395 470 0.6 0 1.5 $false
for ($i = 0; $i -lt 32; $i++) { $q = P 494 ($i * 2 * $PI / 32 + $PI / 32); Dot $g $q.X $q.Y 5 }
Circ $g 378 4
Petals $g 24 260 376 1.2 ($PI / 24) 3.5 $true
Petals $g 24 275 352 0.55 ($PI / 24) 1.5 $false
Circ $g 258 2.5; Circ $g 246 5
for ($i = 0; $i -lt 48; $i++) { $q = P 228 ($i * 2 * $PI / 48); Dot $g $q.X $q.Y 3.5 }
Petals $g 16 110 214 1.3 0 3.5 $true
Petals $g 16 125 190 0.6 0 1.5 $false
Circ $g 108 4
Petals $g 8 20 104 1.6 ($PI / 8) 3 $true
Circ $g 26 3; Dot $g $C $C 9
Finish $b $g 'pat_mandala'

# ---- звёздная геометрия ----
$b, $g = Layer 1024
Circ $g 500 6; Circ $g 486 2
StarPoly $g 486 12 5 (-$PI / 2) 3
Circ $g 360 2.5
StarPoly $g 360 9 4 (-$PI / 2) 3
Circ $g 270 4
StarPoly $g 270 8 3 (-$PI / 8) 3
StarPoly $g 270 8 3 (-$PI / 2) 1.6
Circ $g 180 2.5
StarPoly $g 180 7 3 (-$PI / 2) 3
Circ $g 104 4
StarPoly $g 104 5 2 (-$PI / 2) 3.5
for ($i = 0; $i -lt 12; $i++) { $q = P 486 ($i * $PI / 6 - $PI / 2); Dot $g $q.X $q.Y 9 }
for ($i = 0; $i -lt 9; $i++) { $q = P 360 ($i * 2 * $PI / 9 - $PI / 2); Dot $g $q.X $q.Y 7 }
for ($i = 0; $i -lt 8; $i++) { $q = P 270 ($i * $PI / 4 - $PI / 8); Dot $g $q.X $q.Y 7; $q = P 270 ($i * $PI / 4 - $PI / 2); Dot $g $q.X $q.Y 4 }
Dot $g $C $C 12
Finish $b $g 'pat_stars'

# ---- солнечные лучи (512): клинья с затуханием к краю, длина и ширина разные ----
$b, $g = Layer 512
for ($i = 0; $i -lt 64; $i++) {
  $a = $i * 2 * $PI / 64 + ($rng.NextDouble() - 0.5) * 0.05
  $len = if ($i % 8 -eq 0) { 250 } elseif ($i % 2 -eq 0) { 150 + 70 * $rng.NextDouble() } else { 70 + 90 * $rng.NextDouble() }
  $wd = if ($i % 8 -eq 0) { 0.05 } else { 0.012 + 0.025 * $rng.NextDouble() }
  $path = New-Object Drawing.Drawing2D.GraphicsPath
  $path.AddPolygon([Drawing.PointF[]]@((P 6 ($a - $wd * 4)), (P $len $a), (P 6 ($a + $wd * 4))))
  $p1 = P 0 $a; $p2 = P $len $a
  $lg = New-Object Drawing.Drawing2D.LinearGradientBrush $p1, $p2, ([Drawing.Color]::FromArgb(255, 255, 255, 255)), ([Drawing.Color]::FromArgb(0, 255, 255, 255))
  $g.FillPath($lg, $path); $g.FillPath($lg, $path) }
$pg = New-Object Drawing.Drawing2D.GraphicsPath; $pg.AddEllipse(206, 206, 100, 100)
$br = New-Object Drawing.Drawing2D.PathGradientBrush $pg; $br.CenterColor = [Drawing.Color]::FromArgb(255, 255, 255, 255); $br.SurroundColors = [Drawing.Color[]]@([Drawing.Color]::FromArgb(0, 255, 255, 255))
$g.FillPath($br, $pg)
Finish $b $g 'rays' $false
# ---- галактика «Млечного пути»: туманные спиральные рукава (galaxy_arms) и звёзды вдоль них (galaxy_stars) ----
function Gauss { $u = 1 - $rng.NextDouble(); $v = $rng.NextDouble(); [Math]::Sqrt(-2 * [Math]::Log($u)) * [Math]::Cos(2 * $PI * $v) }
function ArmPt([int]$arm, [double]$t, [double]$jit) { $an = $arm * $PI + $t * 4.4; $rr = 26 + 400 * $t
  $x = $C + [Math]::Cos($an) * $rr + (Gauss) * $jit; $y = $C + [Math]::Sin($an) * $rr + (Gauss) * $jit; return @($x, $y) }
$b, $g = Layer 1024
for ($arm = 0; $arm -lt 2; $arm++) { for ($i = 0; $i -lt 2200; $i++) { $t = $rng.NextDouble(); $q = ArmPt $arm $t (16 + 36 * $t); $sz = 64 * (1 - 0.6 * $t) + 10 * $rng.NextDouble()
    $g.FillEllipse((New-Object Drawing.SolidBrush ([Drawing.Color]::FromArgb(4, 255, 255, 255))), [float]($q[0] - $sz / 2), [float]($q[1] - $sz / 2), [float]$sz, [float]$sz) }
  for ($i = 0; $i -lt 260; $i++) { $t = $rng.NextDouble() * 0.9 + 0.05; $q = ArmPt ($arm + 0.5) $t (30 + 50 * $t); $sz = 30 + 30 * $rng.NextDouble()   # тонкие межрукавные струи
    $g.FillEllipse((New-Object Drawing.SolidBrush ([Drawing.Color]::FromArgb(5, 255, 255, 255))), [float]($q[0] - $sz / 2), [float]($q[1] - $sz / 2), [float]$sz, [float]$sz) } }
$pg = New-Object Drawing.Drawing2D.GraphicsPath; $pg.AddEllipse([float]($C - 110), [float]($C - 110), 220, 220)
$br = New-Object Drawing.Drawing2D.PathGradientBrush $pg; $br.CenterColor = [Drawing.Color]::FromArgb(255, 255, 255, 255); $br.SurroundColors = [Drawing.Color[]]@([Drawing.Color]::FromArgb(0, 255, 255, 255))
$g.FillPath($br, $pg)
Finish $b $g 'galaxy_arms'
$b, $g = Layer 1024
for ($i = 0; $i -lt 1400; $i++) { $t = [Math]::Pow($rng.NextDouble(), 0.8)
  if ($rng.NextDouble() -lt 0.75) { $q = ArmPt ($rng.Next(2)) $t (10 + 36 * $t) } else { $an = $rng.NextDouble() * 2 * $PI; $rr = 470 * [Math]::Sqrt($rng.NextDouble()); $q = @(($C + [Math]::Cos($an) * $rr), ($C + [Math]::Sin($an) * $rr)) }
  $sz = 0.8 + 2.4 * [Math]::Pow($rng.NextDouble(), 3); $a = 120 + $rng.Next(136)
  $g.FillEllipse((New-Object Drawing.SolidBrush ([Drawing.Color]::FromArgb($a, 255, 255, 255))), [float]($q[0] - $sz), [float]($q[1] - $sz), [float](2 * $sz), [float](2 * $sz)) }
for ($i = 0; $i -lt 22; $i++) { $q = ArmPt ($rng.Next(2)) ($rng.NextDouble()) 20; $sz = 9 + 9 * $rng.NextDouble()   # яркие звёзды-крестики
  $g.DrawLine((WPen 1.6), [float]($q[0] - $sz), [float]$q[1], [float]($q[0] + $sz), [float]$q[1]); $g.DrawLine((WPen 1.6), [float]$q[0], [float]($q[1] - $sz), [float]$q[0], [float]($q[1] + $sz)); Dot $g $q[0] $q[1] 2.6 }
Dot $g $C $C 10
Finish $b $g 'galaxy_stars'
$futhark.Dispose()
