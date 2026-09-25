$ErrorActionPreference='Stop'
Add-Type -Path 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
$root='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB'
$here=Join-Path $root 'script\rod_button_head_20260924'
$model=Join-Path $root 'QSTL_24DC_4MW_PCB\Mechanical_Assembly\Rod_Holder_Adapter_Drop8p5'
$backup=Join-Path $here 'before';$null=New-Item -ItemType Directory -Path $backup -Force
foreach($name in @('Rod_Holder_Assembly_Drop8p5.iam','Rod_Holder_Assembly_Drop8p5.step','inward_placements.json','content_center_fasteners.json','geometry_verification.json','standard_hardware_audit.json','README.md','variant_plan.json')){
 if(!(Test-Path -LiteralPath (Join-Path $backup $name))){Copy-Item -LiteralPath (Join-Path $model $name) -Destination (Join-Path $backup $name)}
}
$protected=@('Centre_Plate.ipt','Centre_Plate.step','Left_Rod_Support.ipt','Left_Rod_Support.step','Right_Rod_Support.ipt','Right_Rod_Support.step','Standard_Fasteners\DIN_7991_M3x10.ipt','Standard_Fasteners\ISO_4762_M3x8.ipt','Manufacturing_DWG\Split_Mount_Plate_Only.iam','Manufacturing_DWG\Split_Mount_Assembly.ipn')
$protected+=@(Get-ChildItem -LiteralPath (Join-Path $model 'Manufacturing_DWG') -Filter '*RevD*.dwg'|ForEach-Object {$_.FullName.Substring($model.Length+1)})
$hashes=[ordered]@{};foreach($f in $protected){$hashes[$f]=(Get-FileHash -LiteralPath (Join-Path $model $f)).Hash}
if(!(Test-Path -LiteralPath (Join-Path $backup 'protected_hashes.json'))){$hashes|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $backup 'protected_hashes.json') -Encoding UTF8}
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application');$tg=$app.TransientGeometry;$to=$app.TransientObjects
$old=$app.SilentOperation;$app.SilentOperation=$true
function ExportStep($document,$path){
 $add=$app.ApplicationAddIns.ItemById('{90AF7F40-0C01-11D5-8E83-0010B541CD80}')
 $ctx=$to.CreateTranslationContext();$ctx.Type=[Inventor.IOMechanismEnum]::kFileBrowseIOMechanism
 $opt=$to.CreateNameValueMap();$medium=$to.CreateDataMedium();$null=$add.HasSaveCopyAsOptions($document,$ctx,$opt)
 $opt.Value('ApplicationProtocolType')=3;$medium.FileName=$path;$add.SaveCopyAs($document,$ctx,$opt,$medium)
}
function Rows($m){$rows=@();for($i=1;$i -le 4;$i++){$row=@();for($j=1;$j -le 4;$j++){$row+=$m.Cell($i,$j)};$rows+=,$row};return ,$rows}
try{
 $member=Get-Content -Raw -LiteralPath (Join-Path $model 'button_head_member.json')|ConvertFrom-Json
 $screw=$app.Documents.Open($member.file,$true)
 if(!$screw.ComponentDefinition.IsContentMember){throw 'Not a Content Center member.'}
 ExportStep $screw ([IO.Path]::ChangeExtension($member.file,'.step'))
 $screw.Activate();$cam=$app.ActiveView.Camera;$cam.Perspective=$false
 $cam.Target=$tg.CreatePoint(.2,0,0);$cam.Eye=$tg.CreatePoint(-3,-4,3);$cam.UpVector=$tg.CreateUnitVector(0,0,1);$cam.Fit();$cam.ApplyWithoutTransition()
 $bg=$to.CreateColor(244,247,250);$cam.SaveAsBitmap((Join-Path $model 'ISO_7380_1_M3x8_preview.png'),1200,850,$bg,$bg)
 $doc=$app.Documents.Open((Join-Path $model 'Rod_Holder_Assembly_Drop8p5.iam'),$true)
 $targets=@($doc.ComponentDefinition.Occurrences|Where-Object Name -match '^Rod_Clamp_M3_X(3|48)_Y(140|160|180|200)$')
 if($targets.Count -ne 8){throw 'Expected exactly eight rod fasteners.'}
 foreach($o in $targets){
  $savedName=$o.Name;$m=$o.Transformation.Copy()
  if([Math]::Abs($m.Cell(3,1)-1)-gt 1e-8 -or [Math]::Abs($m.Cell(3,4)+.16)-gt 1e-8){throw 'Unexpected screw axis or bearing plane.'}
  # Both supplied members have +X shaft axes and their head bearing plane at X=0.
  $o.Grounded=$false;$o.Replace($member.file,$false);$o.Transformation=$m;$o.Name=$savedName;$o.Grounded=$true
 }
 if(!$doc.Update2($false)){throw 'Assembly update failed.'}
 $doc.Save();$doc.Close($true)
 $doc=$app.Documents.Open((Join-Path $model 'Rod_Holder_Assembly_Drop8p5.iam'),$true);$doc.Activate()
 $records=@();$counts=@{round_rod=0;socket_device=0;countersunk_deck=0}
 foreach($o in $doc.ComponentDefinition.Occurrences){
  $p=$o.Definition.Document.FullFileName
  if($o.Name -like 'Rod_Clamp_*'){if($p-ne$member.file){throw 'Rod replacement was not saved.'};$counts.round_rod++}
  if($o.Name -like 'Device_Clamp_*'){if([IO.Path]::GetFileName($p)-ne'ISO_4762_M3x8.ipt'){throw 'Device hardware changed.'};$counts.socket_device++}
  if($o.Name -like 'Deck_Join_*'){if([IO.Path]::GetFileName($p)-ne'DIN_7991_M3x10.ipt'){throw 'Deck hardware changed.'};$counts.countersunk_deck++}
  $records+=@{name=$o.Name;path=$p;matrix_cm=(Rows $o.Transformation)}
 }
 if($counts.round_rod-ne8 -or $counts.socket_device-ne2 -or $counts.countersunk_deck-ne8 -or $records.Count-ne24){throw 'Unexpected assembly counts.'}
 $records|ConvertTo-Json -Depth 8|Set-Content -LiteralPath (Join-Path $model 'inward_placements.json') -Encoding UTF8
 ExportStep $doc (Join-Path $model 'Rod_Holder_Assembly_Drop8p5.step')
 @($doc.AllReferencedDocuments|ForEach-Object {$_.FullFileName})|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $model 'native_references.json') -Encoding UTF8
 $views=$doc.ComponentDefinition.RepresentationsManager.DesignViewRepresentations
 (@($views|Where-Object Name -eq 'Tube_Review')[0]).Activate()
 $tube=@($doc.ComponentDefinition.Occurrences|Where-Object Name -eq 'Probe_Tube_ID51_OD54')[0];$tube.Visible=$true
 $cam=$app.ActiveView.Camera;$cam.Perspective=$false;$cam.Target=$tg.CreatePoint(2.55,17.5,.3);$cam.Eye=$tg.CreatePoint(2.55,65,.3);$cam.UpVector=$tg.CreateUnitVector(0,0,-1);$cam.SetExtents(6.2,6.2);$cam.ApplyWithoutTransition()
 $cam.SaveAsBitmap((Join-Path $model 'Cylinder_top_round_heads.png'),1500,1500,$bg,$bg)
 # A separate saved view exposes the eight fasteners without changing geometry.
 $view=@($views|Where-Object Name -eq 'Round_Head_Review')
 if($view.Count-eq0){$review=$views.Add('Round_Head_Review')}else{$review=$view[0]}
 $review.Activate();$tube.Visible=$false
 $cam=$app.ActiveView.Camera;$cam.Perspective=$false;$cam.Target=$tg.CreatePoint(2.55,17.5,-.3);$cam.Eye=$tg.CreatePoint(-8,22,-26);$cam.UpVector=$tg.CreateUnitVector(0,1,0);$cam.SetExtents(10,11);$cam.ApplyWithoutTransition()
 $cam.SaveAsBitmap((Join-Path $model 'Rod_button_head_assembly.png'),1350,1500,$bg,$bg)
 $doc.Save()
 $catalog=@(Get-Content -Raw -LiteralPath (Join-Path $model 'content_center_fasteners.json')|ConvertFrom-Json)|Where-Object family -ne 'ISO 7380-1'
 @($catalog)+@($member)|ConvertTo-Json -Depth 10|Set-Content -LiteralPath (Join-Path $model 'content_center_fasteners.json') -Encoding UTF8
 if((Get-FileHash -LiteralPath $member.file).Hash-ne$member.sha256){throw 'Standard member changed.'}
 foreach($f in $protected){if((Get-FileHash -LiteralPath (Join-Path $model $f)).Hash-ne$hashes[$f]){throw ('Protected file changed: '+$f)}}
 [ordered]@{reopened=$true;counts=$counts;all_top_level_occurrences=$records.Count;family=$member.family;member_sha256=$member.sha256;protected_geometry_and_plate_drawings_unchanged=$true;head_diameter_mm=5.7;head_height_mm=1.65;shank_length_mm=8;thread_pitch_mm=.5;underhead_global_z_mm=-1.6;screw_tip_global_z_mm=6.4}|ConvertTo-Json -Depth 6|Set-Content -LiteralPath (Join-Path $model 'rod_button_head_native_audit.json') -Encoding UTF8
 Write-Output 'Saved and reopened assembly: 8 ISO 7380-1 rod screws, 2 ISO 4762 device screws, 8 DIN 7991 deck screws. Protected parts and DWGs unchanged.'
}finally{$app.SilentOperation=$old}
