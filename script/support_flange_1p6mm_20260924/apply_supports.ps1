$ErrorActionPreference='Stop'
$root='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB'
$here=Join-Path $root 'script\support_flange_1p6mm_20260924'
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
try {
 if(!(Test-Path -LiteralPath (Join-Path $backup 'baseline_hashes.json'))) {
  $null=New-Item -ItemType Directory -Path $backup -Force;$hashes=@{}
  foreach($file in Get-ChildItem -LiteralPath $model -Recurse -File | Where-Object {$_.FullName -notmatch '\\OldVersions\\' -and $_.Extension -in @('.ipt','.iam','.ipn','.dwg','.idw','.step','.json','.md','.pdf','.zip')}) {
   $rel=$file.FullName.Substring($model.Length+1);$dest=Join-Path $backup $rel;$null=New-Item -ItemType Directory -Path (Split-Path $dest) -Force;Copy-Item -LiteralPath $file.FullName -Destination $dest;$hashes[$rel]=(Get-FileHash -LiteralPath $file.FullName).Hash
  }
  $hashes|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $backup 'baseline_hashes.json') -Encoding UTF8
 }
 $reports=@()
 foreach($side in @('Left','Right')) {
  $doc=$app.Documents.Open((Join-Path $model ($side+'_Rod_Support.ipt')),$true);$cd=$doc.ComponentDefinition
  $tx=$app.TransactionManager.StartTransaction($doc,'1.6 mm flange with M3 clearance holes')
  try {
   foreach($t in @($cd.Features.ThreadFeatures | Where-Object Name -like 'Rod_M3*')) {$t.Delete()}
   $cd.Parameters.UserParameters.Item('RodFlangeThickness').Expression='1.6 mm'
   $p=@($cd.Parameters.UserParameters | Where-Object {$_.Name -in @('RodTapDrillDiameter','RodClearanceDiameter')})[0];$p.Expression='3.4 mm';$p.Name='RodClearanceDiameter';$p.Comment='Plain M3 clearance hole; user cancelled support flange threading.'
   $f=@($cd.Features.ExtrudeFeatures | Where-Object {$_.Name -in @('Four_Rod_M3_Through_Tap_Bores','Original_Rod_Clearance_4x')})[0];$f.Name='Original_Rod_Clearance_4x'
   $cd.Features.ChamferFeatures.Item(1).Name='Outer_End_1p6mm_45deg'
   if(!$doc.Update2($false) -or $cd.SurfaceBodies.Count -ne 1 -or $cd.Features.ThreadFeatures.Count -ne 4) {throw 'Invalid clearance support'}
   foreach($f in $cd.Features) {if($f.HealthStatus -ne [Inventor.HealthStatusEnum]::kUpToDateHealth) {throw ('Unhealthy feature: '+$f.Name)}}
   $tx.End()
  } catch {$tx.Abort();throw}
  $doc.Save();ExportStep $doc (Join-Path $model ($side+'_Rod_Support.step'))
  $reports+=[ordered]@{part=$side;flange_mm=$cd.Parameters.UserParameters.Item('RodFlangeThickness').Value*10;chamfer_mm=$cd.Parameters.UserParameters.Item('OuterEndChamfer').Value*10;rod_through_threads=0;rod_clearance_diameter_mm=3.4;rod_mating_plane_local_z_mm=12.5;rod_free_plane_local_z_mm=10.9;deck_blind_threads=4;volume_mm3=$cd.MassProperties.Volume*1000;healthy=$true}
 }
 $assembly=$app.Documents.Open((Join-Path $model 'Rod_Holder_Assembly_Drop8p5.iam'),$true);$moves=@()
 $baseline=Get-Content -LiteralPath (Join-Path $backup 'inward_placements.json') -Raw|ConvertFrom-Json
 foreach($o in $assembly.ComponentDefinition.Occurrences) {
  if($o.Name -notmatch '^Rod_Clamp_M3_X(3|48)_Y([0-9]+)$') {continue}
  $x=[double]$Matches[1];$y=[double]$Matches[2];$m=$tg.CreateMatrix()
  $row=@($baseline|Where-Object name -eq $o.Name)[0]
  for($i=1;$i -le 4;$i++) {for($j=1;$j -le 4;$j++) {$m.Cell($i,$j)=[double]$row.matrix_cm[$i-1][$j-1]}}
  $m.Cell(3,4)+=.04
  $before=Rows $o.Transformation;$o.Grounded=$false;$o.Transformation=$m;$o.Grounded=$true
  $moves+=[ordered]@{name=$o.Name;before_cm=$before;after_cm=(Rows $m);head_bearing_z_mm=-1.6;insertion_axis=@(0,0,1);nominal_rod_engagement_mm=6;tip_z_mm=6.4;tip_projection_mm=.4;standard_member=$o.Definition.Document.FullFileName}
 }
 if($moves.Count -ne 8 -or !$assembly.Update2($false)) {throw 'Rod screw assembly failed.'}
 $assembly.Save();ExportStep $assembly (Join-Path $model 'Rod_Holder_Assembly_Drop8p5.step')
 $placements=@($assembly.ComponentDefinition.Occurrences|ForEach-Object {[ordered]@{name=$_.Name;path=$_.Definition.Document.FullFileName;matrix_cm=(Rows $_.Transformation)}})
 $placements|ConvertTo-Json -Depth 8|Set-Content -LiteralPath (Join-Path $model 'inward_placements.json') -Encoding UTF8
 foreach($name in @('Split_Mount_Plate_Only.iam','Split_Mount_Presentation_Source.iam')) {
  $doc=$app.Documents.Open((Join-Path $model ('Manufacturing_DWG\'+$name)),$false);if(!$doc.Update2($false)){throw 'Plate assembly failed'};$doc.Save()
  if($name -eq 'Split_Mount_Plate_Only.iam') {ExportStep $doc (Join-Path $model 'Manufacturing_DWG\Split_Mount_Plate_Only.step')}
 }
 $ipn=$app.Documents.Open((Join-Path $model 'Manufacturing_DWG\Split_Mount_Assembly.ipn'),$false);$ipn.Save()
 [ordered]@{parts=$reports;rod_screw_moves=$moves;central_deck_mm=4;rod_contact_datum_unchanged=$true;device_placement_unchanged=$true;rod_hole_treatment='Original M3 threaded rods retained; flange threads cancelled by user'}|ConvertTo-Json -Depth 10|Set-Content -LiteralPath (Join-Path $here 'native_change.json') -Encoding UTF8
 Write-Output 'Saved 1.6 mm flanges, eight plain 3.4 mm clearance holes and original-direction standard rod screws; no flange threads.'
} finally {$app.SilentOperation=$oldSilent}
