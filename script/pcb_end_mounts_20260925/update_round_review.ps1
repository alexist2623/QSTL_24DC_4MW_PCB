$ErrorActionPreference='Stop'
Add-Type -Path 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
$root='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB'
$out=Join-Path $root 'QSTL_24DC_4MW_PCB\Mechanical_Assembly\ZIF_M1p6_Review'
$archive=Join-Path $PSScriptRoot 'superseded_socket_head'
$null=New-Item -ItemType Directory -Path $archive -Force
foreach($name in @('ZIF_M1p6_Fit.iam','ZIF_M1p6_Fit.step','inventor_fit.json','final_pcb_fit_validation.json','README.md','ZIF_M1p6_Top.png','ZIF_M1p6_Oblique.png','ZIF_M1p6_NoCable.png')){
 $src=Join-Path $out $name;$dst=Join-Path $archive $name
 if((Test-Path -LiteralPath $src)-and!(Test-Path -LiteralPath $dst)){Copy-Item -LiteralPath $src -Destination $dst}
}
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application')
$tg=$app.TransientGeometry;$to=$app.TransientObjects;$old=$app.SilentOperation;$app.SilentOperation=$true
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
 $member=Get-Content -LiteralPath (Join-Path $out 'm1p6_round_member.json') -Raw|ConvertFrom-Json
 if((Get-FileHash -LiteralPath $member.file).Hash-ne$member.sha256){throw 'Changed standard hardware.'}
 $path=Join-Path $out 'ZIF_M1p6_Fit.iam';$doc=$app.Documents.Open($path,$true)
 $screws=@($doc.ComponentDefinition.Occurrences|Where-Object {$_.Name-like'MH*'})
 if($screws.Count-ne2){throw 'Expected two mounting screws.'}
 foreach($o in $screws){
  $before=$o.Transformation.Copy();$name=$o.Name.Split('_')[0]
  $o.Replace($member.file,$false);$o.Name=$name+'_ISO7045H_M1p6x4';$o.Grounded=$true
  for($i=1;$i-le4;$i++){for($j=1;$j-le4;$j++){if([Math]::Abs($o.Transformation.Cell($i,$j)-$before.Cell($i,$j))-gt1e-10){throw 'Replacement changed placement.'}}}
 }
 $null=$doc.Update2($false);$doc.Save();$doc.Close($true)
 $doc=$app.Documents.Open($path,$true);$occs=$doc.ComponentDefinition.Occurrences
 $items=$to.CreateObjectCollection();foreach($o in $occs){$items.Add($o)}
 $hits=$doc.ComponentDefinition.AnalyzeInterference($items);$report=@()
 foreach($hit in $hits){$report+=@{first=$hit.OccurrenceOne.Name;second=$hit.OccurrenceTwo.Name;volume_mm3=($hit.Volume*1000)}}
 $zif=@($occs|Where-Object {$_.Name-eq'Molex_502598_5193'})[0]
 $distances=@();foreach($o in $occs){if($o.Name-like'MH*'){$distances+=@{screw=$o.Name;connector_distance_mm=($app.MeasureTools.GetMinimumDistance($o,$zif)*10)}}}
 $pcb=Join-Path $root 'QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB.PcbDoc'
 [ordered]@{saved_and_reopened=$true;pcb_sha256=(Get-FileHash -LiteralPath $pcb).Hash.ToLower();hardware=$member;interferences=$report;distances=$distances;cable_is_dimensional_envelope=$true;head_cable_contact_permitted=$true;placement_preserved=$true}|ConvertTo-Json -Depth 10|Set-Content -LiteralPath (Join-Path $out 'inventor_fit_round.json') -Encoding UTF8
 $app.Visible=$true
 Screenshot $doc 'ZIF_M1p6_Round_Top' @(0.975,0.1,8) @(0.975,0.1,.16) @(2.6,1.9)
 Screenshot $doc 'ZIF_M1p6_Round_Oblique' @(3,-3,5) @(0.975,0.1,.16) @(2.8,2)
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
 $doc.Save();ExportStep $doc 'ZIF_M1p6_Fit'
 $screw=$app.Documents.Open($member.file,$false);ExportStep $screw 'ISO_7045_H_M1p6x4'
 Screenshot $doc 'ZIF_M1p6_Round_Oblique' @(3,-3,5) @(0.975,0.1,.16) @(2.8,2)
 $report|ConvertTo-Json -Depth 5|Write-Output;$distances|ConvertTo-Json -Depth 5|Write-Output
}finally{$app.SilentOperation=$old}
