$ErrorActionPreference='Stop'
Add-Type -Path 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
$root='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB'
$mechanical=Join-Path $root 'QSTL_24DC_4MW_PCB\Mechanical_Assembly'
$out=Join-Path $mechanical 'Rod_Holder_Adapter'
$helper=Join-Path $root 'script\probe_rod_inspection'
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application')
$tg=$app.TransientGeometry;$to=$app.TransientObjects
$source=[IO.File]::ReadAllText((Join-Path $helper 'build_holder_adapter.ps1'))
$start=$source.IndexOf('function Matrix(');$end=$source.IndexOf('try {')
. ([scriptblock]::Create($source.Substring($start,$end-$start)))
$oldSilent=$app.SilentOperation
try {
    $app.SilentOperation=$true
    $doc=$app.Documents.Open((Join-Path $out 'Rod_Holder_Adapter.ipt'),$false);$cd=$doc.ComponentDefinition
    $thickness=$cd.Parameters.UserParameters.Item('BaseThickness')
    $width=$cd.Parameters.UserParameters.Item('FingerWidth')
    try {
        $thickness.Expression='4.5 mm';$width.Expression='14 mm'
        if (-not $doc.Update2($false)) {throw 'Parameter update failed.'}
        $height=($cd.RangeBox.MaxPoint.Z-$cd.RangeBox.MinPoint.Z)*10
        if ([Math]::Abs($height-10.5) -gt 0.0001 -or $cd.SurfaceBodies.Count -ne 1) {throw 'Parameter geometry verification failed.'}
    } finally {
        $thickness.Expression='4 mm';$width.Expression='13.5 mm';$doc.Update2($false) | Out-Null;$doc.Save()
    }
    $assemblyPath=Join-Path $out 'Rod_Holder_Assembly.iam'
    $assembly=$app.Documents.Open($assemblyPath,$true);$assembly.Update2($false) | Out-Null;$assembly.Save();$assembly.Close($true)
    $assembly=$app.Documents.Open($assemblyPath,$true)
    $expectedOccurrences=13
    if (Test-Path -LiteralPath (Join-Path $mechanical 'Probe_Tube\Probe_Tube.ipt')) {$expectedOccurrences++}
    if ($assembly.ComponentDefinition.Occurrences.Count -ne $expectedOccurrences) {throw 'Assembly occurrence count mismatch.'}
    $refs=@($assembly.AllReferencedDocuments | ForEach-Object {$_.FullFileName})
    foreach($path in $refs) {if (-not $path.StartsWith($mechanical+'\',[StringComparison]::OrdinalIgnoreCase)) {throw ('Unexpected external reference: '+$path)}}
    $refs | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $out 'native_references.json') -Encoding UTF8
    [pscustomobject]@{reopened=$true;assembly_occurrences=$expectedOccurrences;local_reference_count=$refs.Count;trial_base_thickness_mm=4.5;trial_boss_width_mm=14;parameters_restored=$true;native_solid_count=$cd.SurfaceBodies.Count} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $out 'native_verification.json') -Encoding UTF8

    $assembly.Save()
    # Reload the complete generated document set before checking saved thread metadata.
    $openPaths=@($app.Documents | Where-Object {$_.FullFileName.StartsWith($out+'\')} | Sort-Object {$_.DocumentType} -Descending | ForEach-Object {$_.FullFileName})
    foreach($path in $openPaths) {
        $live=@($app.Documents | Where-Object {$_.FullFileName -eq $path})
        if ($live.Count -gt 0) {$live[0].Close($true)}
    }
    $assembly=$app.Documents.Open($assemblyPath,$true)
    $part=$app.Documents.Open((Join-Path $out 'Rod_Holder_Adapter.ipt'),$false)
    $threads=$part.ComponentDefinition.Features.ThreadFeatures
    if ($threads.Count -ne 10) {throw 'Expected ten saved native thread features.'}
    $threadRows=@()
    foreach($thread in $threads) {
        $info=$thread.ThreadInfo
        if ($info.ThreadDesignation -ne 'M3x0.5' -or $info.Class -ne '6H' -or -not $info.Internal -or -not $info.RightHanded) {throw 'Saved thread specification mismatch.'}
        if ([Math]::Abs($thread.ThreadDepth.Value*10-6) -gt 0.000001) {throw 'Saved thread depth mismatch.'}
        if ($thread.HealthStatus -ne [Inventor.HealthStatusEnum]::kUpToDateHealth) {throw 'Thread feature is not healthy.'}
        $face=$thread.ThreadedFace.Item(1)
        $threadRows+=[pscustomobject]@{name=$thread.Name;designation=$info.ThreadDesignation;class=$info.Class;internal=$info.Internal;right_handed=$info.RightHanded;entry_x_mm=($face.Geometry.BasePoint.X*10);local_y_mm=($face.Geometry.BasePoint.Y*10);local_z_mm=($face.Geometry.BasePoint.Z*10);depth_mm=($thread.ThreadDepth.Value*10);healthy=$true}
    }
    $threadRows=@($threadRows | Sort-Object local_y_mm)
    foreach($entryX in @(19.794248369169,33.294248369169)) {
        $sideRows=@($threadRows | Where-Object {[Math]::Abs($_.entry_x_mm-$entryX) -lt 0.000001} | Sort-Object local_y_mm)
        if ($sideRows.Count -ne 5) {throw 'Expected five threads on each opposite face.'}
        for($i=0;$i -lt 5;$i++) {
            if ([Math]::Abs($sideRows[$i].local_y_mm-(9.82802366515844+16*$i)) -gt 0.000001 -or [Math]::Abs($sideRows[$i].local_z_mm-7) -gt 0.000001) {throw 'Saved thread row centre mismatch.'}
        }
    }
    [pscustomobject]@{saved_and_reloaded=$true;native_thread_count=10;count_per_side=5;centre_pitch_mm=16;opposed_bore_web_mm=1.5;items=$threadRows} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $out 'native_thread_verification.json') -Encoding UTF8
    $assembly.Activate()
    Write-Output ('Native reopen and parameter checks passed, '+$refs.Count+' local references.')
} finally {$app.SilentOperation=$oldSilent}
