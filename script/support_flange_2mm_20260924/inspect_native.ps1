$ErrorActionPreference='Stop'
$root='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB'
$here=Join-Path $root 'script\support_flange_2mm_20260924'
$model=Join-Path $root 'QSTL_24DC_4MW_PCB\Mechanical_Assembly\Rod_Holder_Adapter_Drop8p5'
Add-Type -Path 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
try {$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application')} catch {$app=New-Object -ComObject Inventor.Application}
$app.Visible=$true
$rows=@()
foreach($name in @('Left_Rod_Support','Right_Rod_Support','Centre_Plate')) {
 $doc=$app.Documents.Open((Join-Path $model ($name+'.ipt')),$false);$cd=$doc.ComponentDefinition
 $parameters=@($cd.Parameters.UserParameters | ForEach-Object {[ordered]@{name=$_.Name;expression=$_.Expression;value_cm=$_.Value}})
 $features=@($cd.Features | ForEach-Object {[ordered]@{name=$_.Name;type=[string]$_.Type;health=[string]$_.HealthStatus}})
 $extrudes=@($cd.Features.ExtrudeFeatures | ForEach-Object {[ordered]@{name=$_.Name;extent_type=[string]$_.ExtentType;distance=$_.Extent.Distance.Expression;sketch=$_.Profile.Parent.Name;plane=$_.Profile.Parent.PlanarEntity.Name}})
 $planes=@($cd.WorkPlanes | ForEach-Object {[ordered]@{name=$_.Name;type=[string]$_.DefinitionType;z=$_.Plane.RootPoint.Z}})
 $sketches=@($cd.Sketches | ForEach-Object {[ordered]@{name=$_.Name;plane=$_.PlanarEntity.Name;health=[string]$_.HealthStatus}})
 $rows+=[ordered]@{name=$name;path=$doc.FullFileName;dirty=$doc.Dirty;parameters=$parameters;features=$features;extrudes=$extrudes;planes=$planes;sketches=$sketches;volume_mm3=$cd.MassProperties.Volume*1000}
}
$rows|ConvertTo-Json -Depth 9|Set-Content -LiteralPath (Join-Path $here 'native_before.json') -Encoding UTF8
$rows|ForEach-Object {[pscustomobject]@{part=$_.name;volume_mm3=$_.volume_mm3;extrudes=($_.extrudes|ConvertTo-Json -Compress)}}|Format-List
