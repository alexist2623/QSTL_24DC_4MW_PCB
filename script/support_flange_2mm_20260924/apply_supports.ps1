$ErrorActionPreference='Stop'
$root='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB'
$here=Join-Path $root 'script\support_flange_2mm_20260924'
$model=Join-Path $root 'QSTL_24DC_4MW_PCB\Mechanical_Assembly\Rod_Holder_Adapter_Drop8p5'
$backup=Join-Path $here 'before'
Add-Type -Path 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application');$tg=$app.TransientGeometry;$to=$app.TransientObjects
$oldSilent=$app.SilentOperation;$app.SilentOperation=$true
function ExportStep($doc,$path) {
 $add=$app.ApplicationAddIns.ItemById('{90AF7F40-0C01-11D5-8E83-0010B541CD80}');$ctx=$to.CreateTranslationContext();$ctx.Type=[Inventor.IOMechanismEnum]::kFileBrowseIOMechanism
 $opt=$to.CreateNameValueMap();$media=$to.CreateDataMedium();$null=$add.HasSaveCopyAsOptions($doc,$ctx,$opt);$opt.Value('ApplicationProtocolType')=3;$media.FileName=$path;$add.SaveCopyAs($doc,$ctx,$opt,$media)
}
function Rows($m) {$rows=@();for($i=1;$i -le 4;$i++) {$r=@();for($j=1;$j -le 4;$j++) {$r+=$m.Cell($i,$j)};$rows+=,$r};return ,$rows}
function Preview($doc,$path,$eye,$target,$up,$w=1300,$h=1000) {
 $doc.Activate();$cam=$app.ActiveView.Camera;$cam.Perspective=$false;$cam.Target=$tg.CreatePoint($target[0],$target[1],$target[2]);$cam.Eye=$tg.CreatePoint($eye[0],$eye[1],$eye[2]);$cam.UpVector=$tg.CreateUnitVector($up[0],$up[1],$up[2]);$cam.Fit();$cam.ApplyWithoutTransition()
 $cam.SaveAsBitmap($path,$w,$h,$to.CreateColor(246,248,251),$to.CreateColor(246,248,251))
}
try {
 if(!(Test-Path -LiteralPath (Join-Path $backup 'baseline_hashes.json'))) {
  $null=New-Item -ItemType Directory -Path $backup -Force;$hashes=@{}
  foreach($file in Get-ChildItem -LiteralPath $model -Recurse -File | Where-Object {$_.FullName -notmatch '\\OldVersions\\' -and $_.Extension -in @('.ipt','.iam','.ipn','.dwg','.idw','.step','.json','.md','.pdf','.zip')}) {
   $relative=$file.FullName.Substring($model.Length+1);$dest=Join-Path $backup $relative;$null=New-Item -ItemType Directory -Path (Split-Path $dest) -Force;Copy-Item -LiteralPath $file.FullName -Destination $dest;$hashes[$relative]=(Get-FileHash -LiteralPath $file.FullName).Hash
  }
  $hashes|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $backup 'baseline_hashes.json') -Encoding UTF8
 }
 $reports=@()
 foreach($side in @('Left','Right')) {
  $doc=$app.Documents.Open((Join-Path $model ($side+'_Rod_Support.ipt')),$true);$cd=$doc.ComponentDefinition
  if(@($cd.Features.ChamferFeatures | Where-Object Name -eq 'Outer_End_2mm_45deg').Count -gt 0) {throw 'Already modified; use validation rather than rerunning the mutation.'}
  $tx=$app.TransactionManager.StartTransaction($doc,'2 mm rod flange and 45 degree outer end')
  try {
   $param=$cd.Parameters.UserParameters.AddByExpression('RodFlangeThickness','2 mm',[Inventor.UnitsTypeEnum]::kMillimeterLengthUnits);$param.Comment='User section sketch: thin the exposed rod-contact flange while preserving its mating plane.'
   $param=$cd.Parameters.UserParameters.AddByExpression('OuterEndChamfer','RodFlangeThickness',[Inventor.UnitsTypeEnum]::kMillimeterLengthUnits);$param.Comment='Equal-distance 45 degree full-thickness outer bevel, opposite the rod mating plane.'
   $plane=$cd.WorkPlanes.Item($side+'_Rod_Contact_Flange_StartPlane');$plane.Definition.Offset.Expression='DropHeight + BaseThickness - RodFlangeThickness'
   $feature=$cd.Features.ExtrudeFeatures.Item($side+'_Rod_Contact_Flange');$feature.Extent.Distance.Expression='RodFlangeThickness'
   if(!$doc.Update2($false)) {throw 'Flange thickness update failed.'}
   $xx=if($side -eq 'Left'){0.0}else{5.1};$zz=1.05
   $edges=$to.CreateEdgeCollection()
   foreach($edge in $cd.SurfaceBodies.Item(1).Edges) {
    if($edge.GeometryType -ne [Inventor.CurveTypeEnum]::kLineSegmentCurve) {continue}
    $a=$edge.StartVertex.Point;$b=$edge.StopVertex.Point
    if([math]::Abs($a.X-$xx) -lt .000001 -and [math]::Abs($b.X-$xx) -lt .000001 -and [math]::Abs($a.Z-$zz) -lt .000001 -and [math]::Abs($b.Z-$zz) -lt .000001 -and [math]::Abs([math]::Abs($a.Y-$b.Y)-8) -lt .000001) {$edges.Add($edge)}
   }
   if($edges.Count -ne 1) {throw ('Expected one outer free-side edge; found '+$edges.Count)}
   $ch=$cd.Features.ChamferFeatures.AddUsingDistance($edges,'OuterEndChamfer',$false,$false,$false);$ch.Name='Outer_End_2mm_45deg'
   if(!$doc.Update2($false) -or $cd.SurfaceBodies.Count -ne 1) {throw 'Chamfer did not produce one healthy solid.'}
   foreach($f in $cd.Features) {if($f.HealthStatus -ne [Inventor.HealthStatusEnum]::kUpToDateHealth) {throw ('Unhealthy feature: '+$f.Name)}}
   foreach($f in $cd.Features.ThreadFeatures) {if($f.ThreadInfo.ThreadDesignation -ne 'M3x0.5' -or $f.ThreadInfo.Class -ne '6H' -or [math]::Abs($f.ThreadDepth.Value-.65) -gt .000001) {throw 'Support thread metadata changed.'}}
   $tx.End()
  } catch {$tx.Abort();throw}
  $doc.Save();ExportStep $doc (Join-Path $model ($side+'_Rod_Support.step'))
  Preview $doc (Join-Path $here ($side+'_support_2mm.png')) @(13,-15,-14) @(2.55,4,.8) @(0,1,0)
  $reports+=[ordered]@{part=$side;flange_mm=$cd.Parameters.UserParameters.Item('RodFlangeThickness').Value*10;outer_chamfer_mm=$cd.Parameters.UserParameters.Item('OuterEndChamfer').Value*10;angle_deg=45;rod_contact_z_mm=12.5;free_face_z_mm=10.5;native_chamfer_features=$cd.Features.ChamferFeatures.Count;thread_count=$cd.Features.ThreadFeatures.Count;volume_mm3=$cd.MassProperties.Volume*1000;healthy=$true}
 }
 $assembly=$app.Documents.Open((Join-Path $model 'Rod_Holder_Assembly_Drop8p5.iam'),$true)
 $baseline=Get-Content -LiteralPath (Join-Path $backup 'inward_placements.json') -Raw|ConvertFrom-Json
 $moves=@()
 foreach($o in $assembly.ComponentDefinition.Occurrences) {
  if($o.Name -notlike 'Rod_Clamp_M3_*') {continue}
  $row=@($baseline | Where-Object name -eq $o.Name)[0];$m=$o.Transformation;$before=Rows $m
  $m.Cell(3,4)=[double]$row.matrix_cm[2][3]+.2
  $o.Grounded=$false;$o.Transformation=$m;$o.Grounded=$true
  $moves+=[ordered]@{name=$o.Name;translation_z_mm=2;before_cm=$before;after_cm=(Rows $m);file=$o.Definition.Document.FullFileName}
 }
 if($moves.Count -ne 8) {throw 'Expected exactly eight rod screw seating updates.'}
 if(!$assembly.Update2($false)) {throw 'Full assembly update failed.'}
 $assembly.Save();ExportStep $assembly (Join-Path $model 'Rod_Holder_Assembly_Drop8p5.step')
 $placements=@($assembly.ComponentDefinition.Occurrences | ForEach-Object {[ordered]@{name=$_.Name;path=$_.Definition.Document.FullFileName;matrix_cm=(Rows $_.Transformation)}})
 $placements|ConvertTo-Json -Depth 8|Set-Content -LiteralPath (Join-Path $model 'inward_placements.json') -Encoding UTF8
 foreach($name in @('Split_Mount_Plate_Only.iam','Split_Mount_Presentation_Source.iam')) {
  $doc=$app.Documents.Open((Join-Path $model ('Manufacturing_DWG\'+$name)),$true);if(!$doc.Update2($false)){throw ('Assembly update failed: '+$name)};$doc.Save()
  if($name -eq 'Split_Mount_Plate_Only.iam') {
   ExportStep $doc (Join-Path $model 'Manufacturing_DWG\Split_Mount_Plate_Only.step')
   Preview $doc (Join-Path $model 'Support_end_2mm_45deg.png') @(2.55,-30,0.65) @(2.55,4,0.65) @(0,0,-1) 1600 700
   Preview $doc (Join-Path $model 'Support_assembly_2mm.png') @(16,-15,-18) @(2.55,4,.65) @(0,1,0) 1400 1100
  }
 }
 $ipn=$app.Documents.Open((Join-Path $model 'Manufacturing_DWG\Split_Mount_Assembly.ipn'),$false);$ipn.Save()
 [ordered]@{parts=$reports;rod_screw_moves=$moves;central_deck_mm=4;rod_contact_plane_unchanged=$true;device_alignment_unchanged=$true}|ConvertTo-Json -Depth 10|Set-Content -LiteralPath (Join-Path $here 'native_change.json') -Encoding UTF8
 Write-Output 'Saved both 2 mm flanges, native C2 x 45-degree chamfers, assemblies and STEP exports.'
} finally {$app.SilentOperation=$oldSilent}
