# Кольца родства для школ pohsmp_core (Iron's сам регистрирует <ns>:item/affinity_ring_<школа>).
# Берёт кольцо Святой школы из jar Iron's в клиенте Prism и перекрашивает камень. Использование: tools\gen_affinity_rings.ps1
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression.FileSystem
Add-Type -AssemblyName System.Drawing
$root = Split-Path -Parent $PSScriptRoot
$res = Join-Path $root 'mods-src\pohsmp_core\src\main\resources\assets\pohsmp_core'
$jar = Get-ChildItem "$env:APPDATA\PrismLauncher\instances\1.20.1\minecraft\mods" -Filter 'irons_spellbooks*.jar' | Select-Object -First 1
$gem = @('FFF38A', 'FFFFFF', 'D4A900', 'C77E00', '9E6031')
$schools = @{
  divine    = @('FFF8C8', 'FFFFFF', 'FFE066', 'F5C230', 'B87A10')
  higher    = @('FF9A9A', 'FFFFFF', 'FF3B3B', 'C41818', '6E0A0A')
  forbidden = @('E8C04A', 'FFF0B0', '3A2A10', '1A120A', '060404')
}
foreach ($name in $schools.Keys) {
  $z = [IO.Compression.ZipFile]::OpenRead($jar.FullName)
  $s = $z.GetEntry('assets/irons_spellbooks/textures/item/affinity_ring_holy.png').Open()
  $src = New-Object Drawing.Bitmap $s
  $b = New-Object Drawing.Bitmap $src
  $src.Dispose(); $s.Dispose(); $z.Dispose()
  $to = $schools[$name]
  for ($y = 0; $y -lt $b.Height; $y++) { for ($x = 0; $x -lt $b.Width; $x++) {
    $c = $b.GetPixel($x, $y); if ($c.A -eq 0) { continue }
    $hex = '{0:X2}{1:X2}{2:X2}' -f $c.R, $c.G, $c.B
    $i = [Array]::IndexOf($gem, $hex)
    if ($i -ge 0) { $b.SetPixel($x, $y, [Drawing.ColorTranslator]::FromHtml('#' + $to[$i])) }
  } }
  $b.Save((Join-Path $res "textures\item\affinity_ring_$name.png"), [Drawing.Imaging.ImageFormat]::Png); $b.Dispose()
  $json = "{`n  `"parent`": `"item/generated`",`n  `"textures`": {`n    `"layer0`": `"pohsmp_core:item/affinity_ring_$name`"`n  }`n}`n"
  [IO.File]::WriteAllText((Join-Path $res "models\item\affinity_ring_$name.json"), $json, (New-Object Text.UTF8Encoding $false))
  "  affinity_ring_$name"
}
