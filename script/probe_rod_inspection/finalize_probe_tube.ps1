$ErrorActionPreference='Stop'
Add-Type -Path 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
$mechanical='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB\Mechanical_Assembly'
$out=Join-Path $mechanical 'Probe_Tube'
$assemblyPath=Join-Path $mechanical 'Rod_Holder_Adapter\Rod_Holder_Assembly.iam'
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application')
$oldSilent=$app.SilentOperation
try {
$app.SilentOperation=$true
$doc=$app.Documents.Open((Join-Path $out 'Probe_Tube.ipt'),$false)
$cd=$doc.ComponentDefinition;$od=$cd.Parameters.UserParameters.Item('OuterDiameter')
try {
    $od.Expression='55 mm'
    if (-not $doc.Update2($false)) {throw 'Tube parameter update failed.'}
    if ([Math]::Abs(($cd.RangeBox.MaxPoint.X-$cd.RangeBox.MinPoint.X)*10-55) -gt 0.000001) {throw 'Outer diameter did not update.'}
    if ([Math]::Abs($cd.Parameters.UserParameters.Item('WallThickness').Value*10-2) -gt 0.000001) {throw 'Wall thickness did not update.'}
} finally {$od.Expression='54 mm';$doc.Update2($false) | Out-Null;$doc.Save()}
$assembly=$app.Documents.Open($assemblyPath,$true)
$views=$assembly.ComponentDefinition.RepresentationsManager.DesignViewRepresentations
$review=@($views | Where-Object {$_.Name -eq 'Tube_Review'})
if ($review.Count -eq 0) {$view=$views.Add('Tube_Review')} else {$view=$review[0]}
$view.Activate();$view.Locked=$false
$tubeForView=@($assembly.ComponentDefinition.Occurrences | Where-Object {$_.Name -eq 'Probe_Tube_ID51_OD54'})[0]
$tubeAppearance=@($assembly.Assets | Where-Object {$_.DisplayName -eq 'Tube - transparent review'})
if ($tubeAppearance.Count -ne 1) {throw 'Tube review appearance is missing or ambiguous.'}
$tubeForView.Appearance=$tubeAppearance[0]
$assembly.Update2($false) | Out-Null;$assembly.Save();$assembly.Close($true);$doc.Close($true)
$assembly=$app.Documents.Open($assemblyPath,$true)
$matches=@($assembly.ComponentDefinition.Occurrences | Where-Object {$_.Name -eq 'Probe_Tube_ID51_OD54'})
if ($matches.Count -ne 1 -or $assembly.ComponentDefinition.Occurrences.Count -ne 22) {throw 'Tube assembly occurrence mismatch.'}
$tube=$matches[0];$part=$tube.Definition.Document
foreach($expected in @(@('InnerDiameter',51),@('OuterDiameter',54),@('TubeLength',360),@('WallThickness',1.5))) {
    if ([Math]::Abs($part.ComponentDefinition.Parameters.UserParameters.Item($expected[0]).Value*10-$expected[1]) -gt 0.000001) {throw ('Saved tube parameter mismatch: '+$expected[0])}
}
$matrix=$tube.Transformation
$position=@(($matrix.Cell(1,4)*10),($matrix.Cell(2,4)*10),($matrix.Cell(3,4)*10))
$axis=@($matrix.Cell(1,3),$matrix.Cell(2,3),$matrix.Cell(3,3))
for($i=0;$i -lt 3;$i++) {
    if ([Math]::Abs($position[$i]-@(25.5,0,3)[$i]) -gt 0.000001) {throw 'Tube midpoint registration mismatch.'}
    if ([Math]::Abs($axis[$i]-@(0,1,0)[$i]) -gt 0.000001) {throw 'Tube axis mismatch.'}
}
$refs=@($assembly.AllReferencedDocuments | ForEach-Object {$_.FullFileName})
foreach($path in $refs) {if (-not $path.StartsWith($mechanical+'\',[StringComparison]::OrdinalIgnoreCase)) {throw 'Unexpected external native reference.'}}
[pscustomobject]@{saved_and_reopened=$true;tube_count=1;assembly_occurrences=22;local_reference_count=$refs.Count;inner_diameter_mm=51;outer_diameter_mm=54;length_mm=360;wall_thickness_mm=1.5;axis_point_mm=$position;axis_direction=$axis;parameter_trial_outer_diameter_mm=55;parameters_restored=$true} | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath (Join-Path $out 'native_verification.json') -Encoding UTF8
$refs | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $mechanical 'Rod_Holder_Adapter\native_references.json') -Encoding UTF8
$prior=Get-Content -LiteralPath (Join-Path $mechanical 'Rod_Holder_Adapter\native_verification.json') -Raw | ConvertFrom-Json
$prior.assembly_occurrences=22;$prior.local_reference_count=$refs.Count
$prior | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $mechanical 'Rod_Holder_Adapter\native_verification.json') -Encoding UTF8
$assembly.Activate()
$tg=$app.TransientGeometry;$camera=$app.ActiveView.Camera;$camera.Perspective=$false
$camera.Eye=$tg.CreatePoint(19.5,28.5,52.5);$camera.Target=$tg.CreatePoint(2.55,18,0.3);$camera.UpVector=$tg.CreateUnitVector(0,1,0);$camera.Fit();$camera.ApplyWithoutTransition()
$assembly.Save()
Write-Output 'Sleeve dimensions, midpoint axis and 22-occurrence saved assembly verified.'
} finally {$app.SilentOperation=$oldSilent}
