$ErrorActionPreference='Stop'
Add-Type -Path 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
$out='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\script\probe_rod_inspection\coldfinger_reference'
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application')
$doc=$app.Documents.Open((Join-Path $out 'assembly_coldfinger_v2.iam'),$true)
$items=@()
foreach ($occ in $doc.ComponentDefinition.Occurrences) {
    $matrix=@();for($i=1;$i -le 4;$i++) { $row=@();for($j=1;$j -le 4;$j++) {$row+= $occ.Transformation.Cell($i,$j)};$matrix+=,$row }
    $box=$occ.RangeBox
    $items += [pscustomobject]@{name=$occ.Name;matrix_cm=$matrix;min_mm=@(($box.MinPoint.X*10),($box.MinPoint.Y*10),($box.MinPoint.Z*10));max_mm=@(($box.MaxPoint.X*10),($box.MaxPoint.Y*10),($box.MaxPoint.Z*10))}
    $source=$occ.Definition.Document.FullFileName
    $parts=Join-Path $out 'assembly_parts';New-Item -ItemType Directory -Path $parts -Force | Out-Null
    $destination=Join-Path $parts ([IO.Path]::GetFileName($source))
    if ($source -ne $destination) { if (-not (Test-Path -LiteralPath $destination)) { Copy-Item -LiteralPath $source -Destination $destination };$occ.Replace($destination,$false) }
}
$doc.Save()
$items | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $out 'assembly_transforms.json') -Encoding UTF8
$doc.Activate();$tg=$app.TransientGeometry;$camera=$app.ActiveView.Camera;$camera.Perspective=$false
$camera.Eye=$tg.CreatePoint(30,-5,40);$camera.Target=$tg.CreatePoint(0,-2,0);$camera.UpVector=$tg.CreateUnitVector(0,1,0);$camera.Fit();$camera.ApplyWithoutTransition()
$bg=$app.TransientObjects.CreateColor(245,247,250);$camera.SaveAsBitmap((Join-Path $out 'combined_reference.png'),1200,1600,$bg,$bg)
$items | ConvertTo-Json -Depth 6
