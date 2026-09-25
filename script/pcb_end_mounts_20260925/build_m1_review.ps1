$ErrorActionPreference='Stop'
Add-Type -Path 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
$root='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB'
$out=Join-Path $root 'QSTL_24DC_4MW_PCB\Mechanical_Assembly\ZIF_M1_Review'
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application')
$tg=$app.TransientGeometry;$to=$app.TransientObjects;$old=$app.SilentOperation;$app.SilentOperation=$true
function ImportPart($name,$color){
 $path=Join-Path $out ($name+'.ipt')
 if(Test-Path -LiteralPath $path){return $app.Documents.Open($path,$false)}
 $doc=$app.Documents.Add([Inventor.DocumentTypeEnum]::kPartDocumentObject,$app.FileManager.GetTemplateFile([Inventor.DocumentTypeEnum]::kPartDocumentObject),$false)
 $imports=$doc.ComponentDefinition.ReferenceComponents.ImportedComponents
 $def=$imports.CreateDefinition((Join-Path $out ($name+'.step')));$def.ReferenceModel=$false;$null=$imports.Add($def)
 $asset=$doc.Assets.Add([Inventor.AssetTypeEnum]::kAssetTypeAppearance,'Generic','ReviewColor','Review Color')
 $asset.Item('generic_diffuse').Value=$to.CreateColor($color[0],$color[1],$color[2]);$doc.ActiveAppearance=$asset
 $doc.SaveAs($path,$false);return $doc
}
function ExportStep($doc,$name){
 $add=$app.ApplicationAddIns.ItemById('{90AF7F40-0C01-11D5-8E83-0010B541CD80}')
 $ctx=$to.CreateTranslationContext();$ctx.Type=[Inventor.IOMechanismEnum]::kFileBrowseIOMechanism
 $opt=$to.CreateNameValueMap();$medium=$to.CreateDataMedium();$null=$add.HasSaveCopyAsOptions($doc,$ctx,$opt)
 $opt.Value('ApplicationProtocolType')=3;$medium.FileName=Join-Path $out ($name+'.step');$add.SaveCopyAs($doc,$ctx,$opt,$medium)
}
function Screenshot($doc,$name,$eye,$target,$extent){
 $doc.Activate();$cam=$app.ActiveView.Camera;$cam.Perspective=$false
 $cam.Target=$tg.CreatePoint($target[0],$target[1],$target[2]);$cam.Eye=$tg.CreatePoint($eye[0],$eye[1],$eye[2]);$cam.UpVector=$tg.CreateUnitVector(0,1,0)
 $cam.SetExtents($extent[0],$extent[1]);$cam.ApplyWithoutTransition()
 $bg=$to.CreateColor(241,245,248);$cam.SaveAsBitmap((Join-Path $out ($name+'.png')),1600,1150,$bg,$bg)
}
try{
 $inputs=Get-Content -LiteralPath (Join-Path $out 'model_inputs.json') -Raw|ConvertFrom-Json
 $member=Get-Content -LiteralPath (Join-Path $out 'm1_round_member.json') -Raw|ConvertFrom-Json
 if((Get-FileHash -LiteralPath $member.file).Hash-ne$member.sha256){throw 'Changed standard hardware.'}
 $path=Join-Path $out 'ZIF_M1_Fit.iam'
 if(Test-Path -LiteralPath $path){throw 'Review assembly already exists; inspect instead of overwriting.'}
 $board=ImportPart 'PCB_End' @(164,160,66)
 $zif=ImportPart 'J1_Current' @(225,228,230)
 $cable=ImportPart 'FPC_51_0p3_Envelope' @(219,128,36)
 $screw=$app.Documents.Open($member.file,$false);ExportStep $screw 'KS_B1021_M1x4'
 $doc=$app.Documents.Add([Inventor.DocumentTypeEnum]::kAssemblyDocumentObject,$app.FileManager.GetTemplateFile([Inventor.DocumentTypeEnum]::kAssemblyDocumentObject),$true)
 $occs=$doc.ComponentDefinition.Occurrences
 $b=$occs.Add($board.FullFileName,$tg.CreateMatrix());$b.Name='Current_PCB_End';$b.Grounded=$true
 $z=$occs.Add($zif.FullFileName,$tg.CreateMatrix());$z.Name='Molex_502598_5193';$z.Grounded=$true
 $c=$occs.Add($cable.FullFileName,$tg.CreateMatrix());$c.Name='FPC_51x0p3_Dimensional_Envelope';$c.Grounded=$true
 $screws=@()
 foreach($hole in $inputs.mounts){
  $m=$tg.CreateMatrix();$m.SetToRotation(([Math]::PI/2),$tg.CreateVector(0,1,0),$tg.CreatePoint(0,0,0))
  $m.SetTranslation($tg.CreateVector(($hole.x/10),($hole.y/10),.16),$false)
  $o=$occs.Add($member.file,$m);$o.Name=$hole.name+'_KSB1021_M1x4';$o.Grounded=$true;$screws+=,$o
 }
 $null=$doc.Update2($false);$doc.SaveAs($path,$false);$doc.Close($true)
 $doc=$app.Documents.Open($path,$true);$occs=$doc.ComponentDefinition.Occurrences
 $items=$to.CreateObjectCollection();foreach($o in $occs){$items.Add($o)}
 $hits=$doc.ComponentDefinition.AnalyzeInterference($items)
 $report=@();foreach($hit in $hits){$report+=@{first=$hit.OccurrenceOne.Name;second=$hit.OccurrenceTwo.Name;volume_mm3=($hit.Volume*1000)}}
 $distances=@();foreach($o in $occs){if($o.Name-like'MH*'){
  $zifOcc=@($occs|Where-Object {$_.Name -eq 'Molex_502598_5193'})[0]
  $distances+=@{screw=$o.Name;connector_distance_mm=($app.MeasureTools.GetMinimumDistance($o,$zifOcc)*10)}
 }}
 [ordered]@{saved_and_reopened=$true;pcb_sha256=$inputs.pcb_sha256;hardware=$member;interferences=$report;distances=$distances;cable_is_dimensional_envelope=$true;head_cable_contact_permitted=$true}|ConvertTo-Json -Depth 10|Set-Content -LiteralPath (Join-Path $out 'inventor_fit.json') -Encoding UTF8
 $app.Visible=$true
 Screenshot $doc 'ZIF_M1_Round_Top' @(0.975,0.1,8) @(0.975,0.1,.16) @(2.6,1.9)
 Screenshot $doc 'ZIF_M1_Round_Oblique' @(3,-3,5) @(0.975,0.1,.16) @(2.8,2)
 $screws=@($occs|Where-Object {$_.Name-like'MH*'});foreach($o in $screws){$o.Visible=$false}
 $c=@($occs|Where-Object {$_.Name-like'FPC*'})[0]
 # Use the supplied cable envelope with a temporary transparent appearance so
 # holes remain visible. Restore its original appearance before saving.
 $part=$c.Definition.Document;$oldAsset=$part.ActiveAppearance
 $asset=$part.Assets.Add([Inventor.AssetTypeEnum]::kAssetTypeAppearance,'Generic','CableReviewTransparent','Cable Review Transparent')
 $asset.Item('generic_diffuse').Value=$to.CreateColor(219,128,36)
 $asset.Item('generic_transparency').Value=.75;$part.ActiveAppearance=$asset
 Screenshot $doc 'ZIF_Holes_Cable_Native_Top' @(0.975,0.2,8) @(0.975,0.2,.16) @(2.4,1.7)
 $part.ActiveAppearance=$oldAsset
 foreach($o in $screws){$o.Visible=$true}
 $doc.Save();ExportStep $doc 'ZIF_M1_Fit'
 $screw=$app.Documents.Open($member.file,$false);ExportStep $screw 'KS_B1021_M1x4'
 Screenshot $doc 'ZIF_M1_Round_Oblique' @(3,-3,5) @(0.975,0.1,.16) @(2.8,2)
 $report|ConvertTo-Json -Depth 5|Write-Output;$distances|ConvertTo-Json -Depth 5|Write-Output
}finally{$app.SilentOperation=$old}
