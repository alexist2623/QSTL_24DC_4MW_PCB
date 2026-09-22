$ErrorActionPreference='Stop'
Add-Type -Path 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
$root='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB';$helper=Join-Path $root 'script\probe_rod_inspection'
$out=Join-Path $root 'QSTL_24DC_4MW_PCB\Mechanical_Assembly\Rod_Holder_Adapter'
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application');$tg=$app.TransientGeometry;$to=$app.TransientObjects
. ([scriptblock]::Create([IO.File]::ReadAllText((Join-Path $helper 'mounting_orientation.ps1'))))
$source=[IO.File]::ReadAllText((Join-Path $helper 'build_holder_adapter.ps1'));$start=$source.IndexOf('function Export-Step(');$end=$source.IndexOf('try {')
. ([scriptblock]::Create($source.Substring($start,$end-$start)))
$step=$app.ApplicationAddIns.ItemById('{90AF7F40-0C01-11D5-8E83-0010B541CD80}');$step.Activate()
$silent=$app.SilentOperation
try {
    $app.SilentOperation=$true
    $backup=Join-Path $helper ('tmp\before_inward_mounting_'+(Get-Date -Format 'yyyyMMdd_HHmmss'));New-Item -ItemType Directory -Path $backup -Force|Out-Null
    Get-ChildItem -LiteralPath $out -File|ForEach-Object {Copy-Item -LiteralPath $_.FullName -Destination $backup}
    $part=$app.Documents.Open((Join-Path $out 'Rod_Holder_Adapter.ipt'),$true)
    $part.ComponentDefinition.Parameters.UserParameters.Item('FingerStartX').Expression='19.794248369169 mm'
    if (-not $part.Update2($false)) {throw 'Boss relocation failed.'}
    $part.Save();Export-Step $part 'Rod_Holder_Adapter.step'
    Save-View $part 'Adapter_isometric.png' @(150,110,230) @(25.5,40,5) 1100 1500
    Save-View $part 'Adapter_opposite_side.png' @(-100,110,180) @(25.5,40,5) 1100 1500
    Save-View $part 'Adapter_top.png' @(25.5,40,220) @(25.5,40,5) 1000 1500
    $part.Save()
    $assembly=$app.Documents.Open((Join-Path $out 'Rod_Holder_Assembly.iam'),$true)
    Apply-ConfirmedMountingOrientation $assembly $tg
    if (-not $assembly.Update2($false)) {throw 'Inward assembly update failed.'}
    $views=$assembly.ComponentDefinition.RepresentationsManager.DesignViewRepresentations
    $views.Item('Tube_Review').Activate()
    $tube=@($assembly.ComponentDefinition.Occurrences|Where-Object {$_.Name -eq 'Probe_Tube_ID51_OD54'})[0];$tube.Visible=$true
    Export-Step $assembly 'Rod_Holder_Assembly.step'
    $views.Item('Interior_Review').Activate();$tube.Visible=$false
    Save-View $assembly 'Assembly_closeup.png' @(-115,245,190) @(25.5,175,3) 1200 1200 $false
    Save-View $assembly 'Assembly_side_clamp.png' @(-160,210,28) @(25.5,175,3) 1200 1200 $false
    Save-View $assembly 'Assembly_overview.png' @(-130,265,530) @(25.5,180,3) 1100 1700
    Save-View $assembly 'Reversed_plate_side.png' @(200,210,3) @(25.5,175,3) 1200 1200 $false
    $assembly.Save();$assembly.Close($true)
    $assembly=$app.Documents.Open((Join-Path $out 'Rod_Holder_Assembly.iam'),$true)
    $records=@()
    foreach($occ in $assembly.ComponentDefinition.Occurrences) {
        $matrix=@();for($i=1;$i -le 4;$i++) {$row=@();for($j=1;$j -le 4;$j++) {$row+=$occ.Transformation.Cell($i,$j)};$matrix+=,$row}
        $records+=[pscustomobject]@{name=$occ.Name;matrix_cm=$matrix;path=$occ.Definition.Document.FullFileName}
    }
    $records|ConvertTo-Json -Depth 8|Set-Content -LiteralPath (Join-Path $out 'inward_placements.json') -Encoding UTF8
    $part=$app.Documents.Open((Join-Path $out 'Rod_Holder_Adapter.ipt'),$false)
    $threads=$part.ComponentDefinition.Features.ThreadFeatures
    if ($threads.Count -ne 10) {throw 'Wrong thread count.'}
    foreach($thread in $threads) {
        if ($thread.HealthStatus -ne [Inventor.HealthStatusEnum]::kUpToDateHealth -or $thread.ThreadInfo.ThreadDesignation -ne 'M3x0.5') {throw 'Thread update failed.'}
    }
    # Superseded orientation reports and section image must not appear as current.
    foreach($name in @('final_orientation_verification.json','final_orientation_geometry.json','final_export_verification.json','geometry_verification.json','Assembly_cross_section.png')) {
        $path=Join-Path $out $name;if (Test-Path -LiteralPath $path) {Move-Item -LiteralPath $path -Destination (Join-Path $backup ('superseded_'+$name))}
    }
    $assembly.Activate();Write-Output 'Saved inward-facing mounting arrangement and centered device.'
} finally {$app.SilentOperation=$silent}
