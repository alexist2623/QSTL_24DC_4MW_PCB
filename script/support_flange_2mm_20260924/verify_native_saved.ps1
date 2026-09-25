$ErrorActionPreference='Stop'
Add-Type -Path 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
$root='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB'
$here=Join-Path $root 'script\support_flange_2mm_20260924'
$model=Join-Path $root 'QSTL_24DC_4MW_PCB\Mechanical_Assembly\Rod_Holder_Adapter_Drop8p5'
$testDir=Join-Path $here 'native_reopen'
$null=New-Item -ItemType Directory -Path $testDir -Force
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application')
$report=@()
foreach($side in @('Left','Right')) {
 $source=Join-Path $model ($side+'_Rod_Support.ipt');$copy=Join-Path $testDir ($side+'_Rod_Support.ipt')
 Copy-Item -LiteralPath $source -Destination $copy -Force
 $doc=$app.Documents.Open($copy,$false)
 try {
  $cd=$doc.ComponentDefinition
  if([math]::Abs($cd.Parameters.UserParameters.Item('RodFlangeThickness').Value-.2) -gt 1e-8) {throw 'Saved flange thickness mismatch'}
  if([math]::Abs($cd.Parameters.UserParameters.Item('OuterEndChamfer').Value-.2) -gt 1e-8) {throw 'Saved chamfer mismatch'}
  if($cd.Features.ChamferFeatures.Count -ne 1 -or $cd.SurfaceBodies.Count -ne 1) {throw 'Saved feature/body count mismatch'}
  foreach($f in $cd.Features) {if($f.HealthStatus -ne [Inventor.HealthStatusEnum]::kUpToDateHealth) {throw ('Unhealthy saved feature: '+$f.Name)}}
  $threads=@($cd.Features.ThreadFeatures | ForEach-Object {[ordered]@{designation=$_.ThreadInfo.ThreadDesignation;class=$_.ThreadInfo.Class;depth_mm=$_.ThreadDepth.Value*10}})
  if($threads.Count -ne 4) {throw 'Wrong thread count'}
  foreach($t in $threads) {if($t.designation -ne 'M3x0.5' -or $t.class -ne '6H' -or [math]::Abs($t.depth_mm-6.5) -gt 1e-7) {throw 'Saved thread mismatch'}}
  $report+=[ordered]@{part=$side;sha256=(Get-FileHash -LiteralPath $source).Hash;reopened_from_independent_saved_copy=$true;healthy=$true;flange_mm=2;chamfer_mm=2;native_chamfer=$cd.Features.ChamferFeatures.Item(1).Name;threads=$threads}
 } finally {$doc.Close($true)}
}
$report|ConvertTo-Json -Depth 8|Set-Content -LiteralPath (Join-Path $model 'support_native_reopen.json') -Encoding UTF8
Write-Output 'Independent saved support IPT copies reopened: 2 mm flanges, native C2 chamfers and eight unchanged M3x0.5-6H threads.'
