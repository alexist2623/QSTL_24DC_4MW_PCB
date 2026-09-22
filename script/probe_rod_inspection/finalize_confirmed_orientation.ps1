$ErrorActionPreference='Stop'
Add-Type -Path 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
$root='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB';$helper=Join-Path $root 'script\probe_rod_inspection'
$out=Join-Path $root 'QSTL_24DC_4MW_PCB\Mechanical_Assembly\Rod_Holder_Adapter'
$reviews=Join-Path $out 'Orientation_Review'
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application');$tg=$app.TransientGeometry;$to=$app.TransientObjects
. ([scriptblock]::Create([IO.File]::ReadAllText((Join-Path $helper 'mounting_orientation.ps1'))))
$source=[IO.File]::ReadAllText((Join-Path $helper 'build_holder_adapter.ps1'))
$start=$source.IndexOf('function Export-Step(');$end=$source.IndexOf('try {')
if ($start -lt 0) {throw 'Export helper missing.'}
. ([scriptblock]::Create($source.Substring($start,$end-$start)))
$step=$app.ApplicationAddIns.ItemById('{90AF7F40-0C01-11D5-8E83-0010B541CD80}');$step.Activate()
$oldSilent=$app.SilentOperation
try {
    $app.SilentOperation=$true
    $backup=Join-Path $helper ('tmp\before_confirmed_orientation_'+(Get-Date -Format 'yyyyMMdd_HHmmss'))
    New-Item -ItemType Directory -Path $backup -Force|Out-Null
    foreach($name in @('Rod_Holder_Assembly.iam','Rod_Holder_Assembly.step')) {Copy-Item -LiteralPath (Join-Path $out $name) -Destination $backup}
    $doc=$app.Documents.Open((Join-Path $out 'Rod_Holder_Assembly.iam'),$true)
    Apply-ConfirmedMountingOrientation $doc $tg
    $doc.Update2($false)|Out-Null
    $allPlacements=Get-Content -LiteralPath (Join-Path $reviews 'native_placements.json') -Raw|ConvertFrom-Json
    $expected=@($allPlacements | Where-Object {$_.name -eq 'Both_reversed'})[0]
    foreach($occ in $doc.ComponentDefinition.Occurrences) {
        $record=@($expected.occurrences|Where-Object {$_.name -eq $occ.Name})[0]
        for($i=1;$i -le 4;$i++) {for($j=1;$j -le 4;$j++) {if ([Math]::Abs($occ.Transformation.Cell($i,$j)-$record.matrix_cm[$i-1][$j-1]) -gt 0.0000001) {throw ('Confirmed screenshot placement mismatch: '+$occ.Name)}}}
    }
    $tube=@($doc.ComponentDefinition.Occurrences|Where-Object {$_.Name -eq 'Probe_Tube_ID51_OD54'})[0]
    $tube.Visible=$true;$doc.Save();Export-Step $doc 'Rod_Holder_Assembly.step'
    $interior=$doc.ComponentDefinition.RepresentationsManager.DesignViewRepresentations.Add('Interior_Review');$interior.Activate();$interior.Locked=$false;$tube.Visible=$false
    Save-View $doc 'Assembly_closeup.png' @(-109,255,-189) @(25.5,175,3) 1200 1200 $false
    Save-View $doc 'Assembly_side_clamp.png' @(-135,220,-65) @(25.5,177,-7) 1200 1200 $false
    Save-View $doc 'Assembly_overview.png' @(-129,265,-524) @(25.5,180,3) 1100 1700
    $doc.Save();$doc.Close($true)
    $doc=$app.Documents.Open((Join-Path $out 'Rod_Holder_Assembly.iam'),$true)
    $items=@()
    foreach($occ in $doc.ComponentDefinition.Occurrences) {
        $record=@($expected.occurrences|Where-Object {$_.name -eq $occ.Name})[0]
        $matrix=@();for($i=1;$i -le 4;$i++) {$row=@();for($j=1;$j -le 4;$j++) {
            $value=$occ.Transformation.Cell($i,$j);$row+=$value
            if ([Math]::Abs($value-$record.matrix_cm[$i-1][$j-1]) -gt 0.0000001) {throw 'Reopened matrix mismatch.'}
        };$matrix+=,$row}
        $items+=[pscustomobject]@{name=$occ.Name;matrix_cm=$matrix}
    }
    [pscustomobject]@{saved_and_reopened=$true;occurrence_count=$items.Count;matches_user_confirmed_screenshot=$true;source_case='Both_reversed';items=$items} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $out 'final_orientation_verification.json') -Encoding UTF8
    $reports=Get-Content -LiteralPath (Join-Path $reviews 'orientation_measurements.json') -Raw|ConvertFrom-Json
    $selected=@($reports.cases|Where-Object {$_.name -eq 'Both_reversed'})[0]
    $selected|ConvertTo-Json -Depth 8|Set-Content -LiteralPath (Join-Path $out 'final_orientation_geometry.json') -Encoding UTF8
    Copy-Item -LiteralPath (Join-Path $reviews 'Both_reversed_section.png') -Destination (Join-Path $out 'Assembly_cross_section.png')
    # Keep intermediate alternatives outside the delivered CAD folder, with reversible moves.
    $paths=@($app.Documents|Where-Object {$_.FullFileName.StartsWith($reviews+'\')}|Sort-Object {$_.DocumentType} -Descending|ForEach-Object {$_.FullFileName})
    foreach($p in $paths) {$live=@($app.Documents|Where-Object {$_.FullFileName -eq $p});if ($live.Count -gt 0) {$live[0].Close($true)}}
    $resolved=(Resolve-Path -LiteralPath $reviews).Path
    if (-not $resolved.StartsWith($out+'\',[StringComparison]::OrdinalIgnoreCase)) {throw 'Archive path is outside the intended output folder.'}
    Move-Item -LiteralPath $resolved -Destination (Join-Path $backup 'Intermediate_Orientation_Reviews')
    foreach($name in @('Mounting_detail.iam','Mounting_detail.png','PPT_top_view_comparison.png','PPT_section_comparison.png','Rod_Holder_Exploded.iam','Assembly_exploded_closeup.png')) {
        $path=Join-Path $out $name
        $live=@($app.Documents|Where-Object {$_.FullFileName -eq $path});if ($live.Count -gt 0) {$live[0].Close($true)}
        if (Test-Path -LiteralPath $path) {Move-Item -LiteralPath $path -Destination $backup}
    }
    $doc.Activate();Write-Output 'Final assembly matches the confirmed screenshot; intermediate alternatives archived.'
} finally {$app.SilentOperation=$oldSilent}
