$ErrorActionPreference = 'Stop'
Add-Type -Path 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
$root = 'C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB'
$model = Join-Path $root 'QSTL_24DC_4MW_PCB\Mechanical_Assembly\Rod_Holder_Adapter_Drop8p5'
$out = Join-Path $model 'Views_20260929'
$null = New-Item -ItemType Directory -Path $out -Force
$source = Join-Path $model 'Rod_Holder_Assembly_Drop8p5.iam'
$references = Get-Content -Raw -LiteralPath (Join-Path $model 'native_references.json') | ConvertFrom-Json
$paths = @($source) + @($references | ForEach-Object { [string]$_ })
$hashes = @{}
foreach ($path in $paths) { $hashes[$path] = (Get-FileHash -LiteralPath $path).Hash }
try { $app = [Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application') }
catch { $app = New-Object -ComObject Inventor.Application }
$app.Visible = $true
$oldSilent = $app.SilentOperation
$oldQuality = $app.DisplayOptions.DisplayQuality
$oldFrameRate = $app.DisplayOptions.MinimumFrameRate
$app.SilentOperation = $true
$app.DisplayOptions.DisplayQuality = [Inventor.DisplayQualityEnum]::kSmootherDisplayQuality
$app.DisplayOptions.MinimumFrameRate = 0
$tg = $app.TransientGeometry
$to = $app.TransientObjects
$existing = @($app.Documents | Where-Object FullFileName -eq $source)
if ($existing.Count -gt 0) { throw 'The source assembly is already open. Preserve its current view before rendering.' }
$doc = $null
try {
    $doc = $app.Documents.Open($source, $true)
    $doc.Activate()
    $null = $doc.Update2($false)
    $views = $doc.ComponentDefinition.RepresentationsManager.DesignViewRepresentations
    (@($views | Where-Object Name -eq 'Tube_Review')[0]).Activate()
    $tube = @($doc.ComponentDefinition.Occurrences | Where-Object Name -eq 'Probe_Tube_ID51_OD54')[0]
    $bg = $to.CreateColor(48,56,69)
    $tube.Visible = $false
    $cam = $app.ActiveView.Camera
    $cam.Perspective = $false
    $cam.Target = $tg.CreatePoint(2.55,17.5,0)
    $cam.Eye = $tg.CreatePoint(-8,23,40)
    $cam.UpVector = $tg.CreateUnitVector(0,1,0)
    $cam.SetExtents(7.2,10.8)
    $cam.ApplyWithoutTransition()
    $app.ActiveView.Update()
    $app.UserInterfaceManager.DoEvents()
    Start-Sleep -Seconds 2
    $cam.SaveAsBitmap((Join-Path $out '01_Assembly_current.png'),1400,2100,$bg,$bg)
    Write-Output 'Rendered current device-side assembly.'
    $tube.Visible = $true
    $cam = $app.ActiveView.Camera
    $cam.Perspective = $false
    $cam.Target = $tg.CreatePoint(2.55,17.5,0.3)
    $cam.Eye = $tg.CreatePoint(2.55,65,0.3)
    $cam.UpVector = $tg.CreateUnitVector(0,0,-1)
    $cam.SetExtents(6.2,6.2)
    $cam.ApplyWithoutTransition()
    $app.ActiveView.Update()
    $app.UserInterfaceManager.DoEvents()
    Start-Sleep -Seconds 2
    $cam.SaveAsBitmap((Join-Path $out '03_Cylinder_axial_current.png'),2000,2000,$bg,$bg)
    Write-Output 'Rendered current cylinder axial view.'
} finally {
    # Discard display changes; never save the source model for a rendering task.
    if ($null -ne $doc) { $doc.Close($true) }
    $app.SilentOperation = $oldSilent
    $app.DisplayOptions.DisplayQuality = $oldQuality
    $app.DisplayOptions.MinimumFrameRate = $oldFrameRate
}
foreach ($path in $paths) {
    if ((Get-FileHash -LiteralPath $path).Hash -ne $hashes[$path]) { throw ('Source changed: ' + $path) }
}
[ordered]@{
    rendered_utc = [DateTime]::UtcNow.ToString('o')
    source = $source
    source_sha256 = $hashes[$source]
    referenced_cad_files = $paths.Count
    source_files_unchanged = $true
    source_hashes = $hashes
} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $out 'render_audit.json') -Encoding UTF8
Write-Output 'Source assembly and all referenced CAD hashes unchanged.'
