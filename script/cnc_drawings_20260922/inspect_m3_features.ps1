$ErrorActionPreference='Stop'
Add-Type -Path 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
$root='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB'
$model=Join-Path $root 'QSTL_24DC_4MW_PCB\Mechanical_Assembly\Rod_Holder_Adapter_Drop8p5'
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application')
$rows=@()
foreach($name in @('Centre_Plate','Left_Rod_Support','Right_Rod_Support','Deck_M3x10_Countersunk')){
 $path=Join-Path $model ($name+'.ipt');$sha=(Get-FileHash -LiteralPath $path).Hash
 $d=$app.Documents.Open($path,$false);$cd=$d.ComponentDefinition;$threads=@()
 foreach($t in $cd.Features.ThreadFeatures){
  $i=$t.ThreadInfo;$threads+=,[ordered]@{feature=$t.Name;designation=$i.ThreadDesignation;thread_type=$i.ThreadType;class=$i.Class;internal=$i.Internal;right_hand=$i.RightHanded;depth_mm=$t.ThreadDepth.Value*10;health=[string]$t.HealthStatus}
 }
 $cylinders=@();foreach($f in $cd.SurfaceBodies.Item(1).Faces){if($f.SurfaceType -eq [Inventor.SurfaceTypeEnum]::kCylinderSurface){$cylinders+=[math]::Round($f.Geometry.Radius*20,6)}}
 $rows+=,[ordered]@{part=$name;is_content_center_member=$cd.IsContentMember;thread_features=$threads;thread_count=$cd.Features.ThreadFeatures.Count;cylinder_diameters_mm=@($cylinders|Sort-Object -Unique);features=@($cd.Features|ForEach-Object {$_.Name});bounds_mm=@(($cd.RangeBox.MinPoint.X*10),($cd.RangeBox.MinPoint.Y*10),($cd.RangeBox.MinPoint.Z*10),($cd.RangeBox.MaxPoint.X*10),($cd.RangeBox.MaxPoint.Y*10),($cd.RangeBox.MaxPoint.Z*10))}
 if((Get-FileHash -LiteralPath $path).Hash -ne $sha){throw 'Read-only audit changed a part.'}
}
$rows|ConvertTo-Json -Depth 8|Set-Content -LiteralPath (Join-Path $root 'script\cnc_drawings_20260922\tmp\m3_feature_audit.json')
$rows|Select-Object part,is_content_center_member,thread_count,cylinder_diameters_mm|ConvertTo-Json -Depth 4
