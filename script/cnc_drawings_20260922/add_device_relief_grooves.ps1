$ErrorActionPreference='Stop'
Add-Type -Path 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
$root='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB'
$here=Join-Path $root 'script\cnc_drawings_20260922'
$model=Join-Path $root 'QSTL_24DC_4MW_PCB\Mechanical_Assembly\Rod_Holder_Adapter_Drop8p5'
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application')
$tg=$app.TransientGeometry;$to=$app.TransientObjects
$before=$app.SilentOperation;$app.SilentOperation=$true
$backup=Join-Path $here 'tmp\before_device_relief'
$null=New-Item -ItemType Directory -Path $backup -Force
function P($x,$y){return $tg.CreatePoint2d($x,$y)}
function Eval($expression){return $doc.UnitsOfMeasure.GetValueFromExpression($expression,[Inventor.UnitsTypeEnum]::kMillimeterLengthUnits)}
function ExportStep($document,$path){
 $add=$app.ApplicationAddIns.ItemById('{90AF7F40-0C01-11D5-8E83-0010B541CD80}')
 $context=$to.CreateTranslationContext();$context.Type=[Inventor.IOMechanismEnum]::kFileBrowseIOMechanism
 $options=$to.CreateNameValueMap();$medium=$to.CreateDataMedium();$null=$add.HasSaveCopyAsOptions($document,$context,$options)
 $options.Value('ApplicationProtocolType')=3;$medium.FileName=$path;$add.SaveCopyAs($document,$context,$options,$medium)
}
function Param($name,$expression,$comment){
 $p=$cd.Parameters.UserParameters.AddByExpression($name,$expression,[Inventor.UnitsTypeEnum]::kMillimeterLengthUnits);$p.Comment=$comment
}
function PointAt($xExpression,$yExpression){
 $x=Eval $xExpression;$y=Eval $yExpression
 $p=$sk.SketchPoints.Add((P $x $y),$false)
 $d=$sk.DimensionConstraints.AddTwoPointDistance($origin,$p,[Inventor.DimensionOrientationEnum]::kHorizontalDim,(P $x ($y+.1)));$d.Parameter.Expression=$xExpression
 $d=$sk.DimensionConstraints.AddTwoPointDistance($origin,$p,[Inventor.DimensionOrientationEnum]::kVerticalDim,(P ($x+.1) $y));$d.Parameter.Expression=$yExpression
 return $p
}
try {
 $sourceFiles=@('Centre_Plate.ipt','Centre_Plate.step','Rod_Holder_Assembly_Drop8p5.iam','Rod_Holder_Assembly_Drop8p5.step')
 foreach($name in $sourceFiles){if(!(Test-Path -LiteralPath (Join-Path $backup $name))){Copy-Item -LiteralPath (Join-Path $model $name) -Destination (Join-Path $backup $name)}}
 $unchanged=@{}
 foreach($name in @('Left_Rod_Support.ipt','Right_Rod_Support.ipt','Deck_M3x10_Countersunk.ipt')){$unchanged[(Join-Path $model $name)]=(Get-FileHash -LiteralPath (Join-Path $model $name)).Hash}
 foreach($name in @('Top_ForFridge.ipt','Bottom.ipt','Carrier_with_PCB.iam','PCB_simplified.iam')){
  $path=Join-Path (Split-Path $model) $name;$unchanged[$path]=(Get-FileHash -LiteralPath $path).Hash
 }
 $doc=$app.Documents.Open((Join-Path $model 'Centre_Plate.ipt'),$true);$cd=$doc.ComponentDefinition
 if(@($cd.Features.ExtrudeFeatures|Where-Object Name -like 'Device_Lip_Relief_*').Count -gt 0){throw 'Relief features already exist; do not duplicate.'}
 $measure=Get-Content -LiteralPath (Join-Path $here 'tmp\device_lip_measurement.json') -Raw|ConvertFrom-Json
 $face=$measure.deck_contact_faces[0];$thickness=[double]$face.bounds[3]-[double]$face.bounds[0]
 Param 'DeviceLipThickness' ($thickness.ToString('G17',[Globalization.CultureInfo]::InvariantCulture)+' mm') 'Measured from the existing Top_ForFridge mounting lip; source CAD unchanged.'
 Param 'DeviceGrooveAllowance' '0.3 mm' 'Total width allowance outside the mounting lip; preserve the boss side datum.'
 Param 'DeviceGrooveWidth' 'DeviceLipThickness + DeviceGrooveAllowance' 'Required lip thickness plus 0.3 mm.'
 Param 'DeviceGrooveDepth' '0.5 mm' 'Cut inward from the boss-side deck surface.'
 Param 'DeviceGrooveRadius' '0.5 mm' 'Internal corner radius at the closed groove ends.'
 $volumeBefore=$cd.MassProperties.Volume*1000
 $plane=$cd.WorkPlanes.AddByPlaneAndOffset($cd.WorkPlanes.Item(3),'BaseThickness');$plane.Name='Device_Relief_Deck_Surface';$plane.Visible=$false
 foreach($side in @('Left','Right')){
  $xmin=if($side -eq 'Left'){'FingerStartX - DeviceGrooveWidth'}else{'FingerStartX + FingerWidth'}
  $xmax=if($side -eq 'Left'){'FingerStartX'}else{'FingerStartX + FingerWidth + DeviceGrooveWidth'}
  $ymin='FingerEndInset';$ymax='ContactLength - FingerEndInset';$r='DeviceGrooveRadius'
  $sk=$cd.Sketches.Add($plane);$sk.Name='Device_Lip_'+$side+'_Relief_Profile'
  $origin=$sk.AddByProjectingEntity($cd.WorkAxes.Item(3))
  $points=@(
   (PointAt ("($xmin) + $r") $ymin), (PointAt ("($xmax) - $r") $ymin),
   (PointAt $xmax ("($ymin) + $r")), (PointAt $xmax ("($ymax) - $r")),
   (PointAt ("($xmax) - $r") $ymax), (PointAt ("($xmin) + $r") $ymax),
   (PointAt $xmin ("($ymax) - $r")), (PointAt $xmin ("($ymin) + $r"))
  )
  foreach($i in @(0,2,4,6)){$null=$sk.SketchLines.AddByTwoPoints($points[$i],$points[$i+1])}
  $centres=@(@((Eval ("($xmax) - $r")),(Eval ("($ymin) + $r"))),@((Eval ("($xmax) - $r")),(Eval ("($ymax) - $r"))),@((Eval ("($xmin) + $r")),(Eval ("($ymax) - $r"))),@((Eval ("($xmin) + $r")),(Eval ("($ymin) + $r"))))
  for($i=0;$i -lt 4;$i++){
   $a=2*$i+1;$b=(2*$i+2)%8;$c=$centres[$i]
   $arc=$sk.SketchArcs.AddByCenterStartEndPoint((P $c[0] $c[1]),$points[$a],$points[$b],$true)
   $dimension=$sk.DimensionConstraints.AddRadius($arc,(P ($c[0]+.1) ($c[1]+.1)));$dimension.Parameter.Expression=$r
  }
  $ed=$cd.Features.ExtrudeFeatures.CreateExtrudeDefinition($sk.Profiles.AddForSolid(),[Inventor.PartFeatureOperationEnum]::kCutOperation)
  $ed.SetDistanceExtent('DeviceGrooveDepth',[Inventor.PartFeatureExtentDirectionEnum]::kNegativeExtentDirection)
  $feature=$cd.Features.ExtrudeFeatures.Add($ed);$feature.Name='Device_Lip_Relief_'+$side;$sk.Visible=$false
 }
 if(!$doc.Update2($false) -or $cd.SurfaceBodies.Count -ne 1){throw 'Relieved plate must remain a single valid solid.'}
 foreach($f in $cd.Features){if($f.HealthStatus -ne [Inventor.HealthStatusEnum]::kUpToDateHealth){throw ('Unhealthy feature: '+$f.Name)}}
 if($cd.Features.ThreadFeatures.Count -ne 10){throw 'Device thread count changed.'}
 $volumeAfter=$cd.MassProperties.Volume*1000
 $width=(Eval 'DeviceGrooveWidth')*10;$length=(Eval 'ContactLength - 2 * FingerEndInset')*10
 $expected=2*($width*$length-(4-[math]::PI)*.5*.5)*.5
 if([math]::Abs(($volumeBefore-$volumeAfter)-$expected) -gt .001){throw 'Removed volume does not match the two rounded relief grooves.'}
 $doc.Save();ExportStep $doc (Join-Path $model 'Centre_Plate.step')
 $doc.Activate();$cam=$app.ActiveView.Camera;$cam.Target=$tg.CreatePoint(2.55,4,.4);$cam.Eye=$tg.CreatePoint(13,-11,19);$cam.UpVector=$tg.CreateUnitVector(0,1,0);$cam.Perspective=$false;$cam.Fit();$cam.ApplyWithoutTransition()
 $cam.SaveAsBitmap((Join-Path $model 'Centre_Plate.png'),1200,1200,$to.CreateColor(246,248,251),$to.CreateColor(246,248,251))
 $doc.Save()
 $assembly=$app.Documents.Open((Join-Path $model 'Rod_Holder_Assembly_Drop8p5.iam'),$true)
 if(!$assembly.Update2($false)){throw 'Updated assembly failed.'};$assembly.Save();ExportStep $assembly (Join-Path $model 'Rod_Holder_Assembly_Drop8p5.step')
 foreach($path in $unchanged.Keys){if((Get-FileHash -LiteralPath $path).Hash -ne $unchanged[$path]){throw ('Unrequested source edit: '+$path)}}
 [ordered]@{lip_thickness_mm=$thickness;groove_width_mm=$width;groove_depth_mm=.5;groove_length_mm=$length;corner_radius_mm=.5;removed_volume_mm3=($volumeBefore-$volumeAfter);expected_removed_volume_mm3=$expected;thread_count=10;single_solid=$true;source_hashes=$unchanged;groove_x_ranges_mm=@(@(((Eval 'FingerStartX - DeviceGrooveWidth')*10),((Eval 'FingerStartX')*10)),@(((Eval 'FingerStartX + FingerWidth')*10),((Eval 'FingerStartX + FingerWidth + DeviceGrooveWidth')*10)));groove_y_range_mm=@(4,76);groove_z_range_mm=@(3.5,4)}|ConvertTo-Json -Depth 6|Set-Content -LiteralPath (Join-Path $model 'device_relief_grooves.json') -Encoding UTF8
 Write-Output ('Saved two reliefs: '+$width+' x '+$length+' x 0.5 mm; R0.5. Source device and supports unchanged.')
}finally{$app.SilentOperation=$before}
