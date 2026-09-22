$ErrorActionPreference='Stop'
Add-Type -Path 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
$mechanical='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB\Mechanical_Assembly'
$out=Join-Path $mechanical 'Rod_Holder_Adapter'
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application')
$doc=$app.Documents.Open((Join-Path $out 'Rod_Holder_Adapter.ipt'),$false)
$cd=$doc.ComponentDefinition
$thickness=$cd.Parameters.UserParameters.Item('BaseThickness')
$clearance=$cd.Parameters.UserParameters.Item('PocketClearance')
try {
    $thickness.Expression='4.5 mm';$clearance.Expression='0.30 mm'
    if (-not $doc.Update2($false)) { throw 'Parameter update failed.' }
    $height=($cd.RangeBox.MaxPoint.Z-$cd.RangeBox.MinPoint.Z)*10
    if ([Math]::Abs($height-11) -gt 0.0001 -or $cd.SurfaceBodies.Count -ne 1) { throw 'Parameter geometry verification failed.' }
} finally {
    $thickness.Expression='4 mm';$clearance.Expression='0.25 mm'
    $doc.Update2($false) | Out-Null
    $doc.Save()
}
$assemblyPath=Join-Path $out 'Rod_Holder_Assembly.iam'
$assembly=$app.Documents.Open($assemblyPath,$true)
$assembly.Update2($false) | Out-Null
$assembly.Save();$assembly.Close($true)
$assembly=$app.Documents.Open($assemblyPath,$true)
if ($assembly.ComponentDefinition.Occurrences.Count -ne 3) { throw 'Assembly occurrence count mismatch.' }
$references=@($assembly.AllReferencedDocuments | ForEach-Object { $_.FullFileName })
foreach ($path in $references) {
    if (-not $path.StartsWith($mechanical+'\',[StringComparison]::OrdinalIgnoreCase)) { throw ('Unexpected external reference: '+$path) }
}
$references | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $out 'native_references.json') -Encoding UTF8
[pscustomobject]@{reopened=$true;assembly_occurrences=3;local_reference_count=$references.Count;trial_base_thickness_mm=4.5;trial_clearance_mm=.30;parameters_restored=$true;native_solid_count=$cd.SurfaceBodies.Count} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $out 'native_verification.json') -Encoding UTF8
$assembly.Activate()
Write-Output ('Saved and reopened; '+$references.Count+' local references; thickness and pocket parameters verified.')
