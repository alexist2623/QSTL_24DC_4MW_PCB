$ErrorActionPreference='Stop'
Add-Type -Path 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
$root='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB'
$here=Join-Path $root 'script\cnc_drawings_20260922'
$model=Join-Path $root 'QSTL_24DC_4MW_PCB\Mechanical_Assembly\Rod_Holder_Adapter_Drop8p5'
$out=Join-Path $model 'Manufacturing_DWG'
$backup=Join-Path $here 'tmp\before_standard_hardware'
$null=New-Item -ItemType Directory -Path $backup -Force
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application')
$tg=$app.TransientGeometry;$to=$app.TransientObjects
$old=$app.SilentOperation;$app.SilentOperation=$true
function ExportStep($document,$path){
 $add=$app.ApplicationAddIns.ItemById('{90AF7F40-0C01-11D5-8E83-0010B541CD80}')
 $context=$to.CreateTranslationContext();$context.Type=[Inventor.IOMechanismEnum]::kFileBrowseIOMechanism
 $options=$to.CreateNameValueMap();$medium=$to.CreateDataMedium();$null=$add.HasSaveCopyAsOptions($document,$context,$options)
 $options.Value('ApplicationProtocolType')=3;$medium.FileName=$path;$add.SaveCopyAs($document,$context,$options,$medium)
}
function Rows($m){$rows=@();for($i=1;$i -le 4;$i++){$row=@();for($j=1;$j -le 4;$j++){$row+= $m.Cell($i,$j)};$rows+= ,$row};return ,$rows}
function Compose($m,$r){
 $result=$tg.CreateMatrix()
 for($i=1;$i -le 3;$i++){
  for($j=1;$j -le 3;$j++){$v=0;for($k=1;$k -le 3;$k++){$v+= $m.Cell($i,$k)*$r[$k-1][$j-1]};$result.Cell($i,$j)=$v}
  $result.Cell($i,4)=$m.Cell($i,4)
 }
 return $result
}
$changes=@()
if(Test-Path -LiteralPath (Join-Path $model 'standard_hardware_replacement.json')){
 $changes=@((Get-Content -LiteralPath (Join-Path $model 'standard_hardware_replacement.json') -Raw|ConvertFrom-Json).changes)
}
try {
 foreach($name in @('Centre_Plate.ipt','Centre_Plate.step','Rod_Holder_Assembly_Drop8p5.iam','inward_placements.json')){
  if(!(Test-Path -LiteralPath (Join-Path $backup $name))){Copy-Item -LiteralPath (Join-Path $model $name) -Destination (Join-Path $backup $name)}
 }
 $plate=$app.Documents.Open((Join-Path $model 'Centre_Plate.ipt'),$false)
 # DIN 7991 includes a 0.2 mm cylindrical head rim. Seat its cone with the
 # supplied head front 0.1 mm below the deck: 6 + 2*(0.2 + 0.1) = 6.6 mm.
 $plate.ComponentDefinition.Parameters.UserParameters.Item('JoinCountersinkDiameter').Expression='6.6 mm'
 if(!$plate.Update2($false)){throw 'Countersink update failed.'}
 $plate.Save();ExportStep $plate (Join-Path $model 'Centre_Plate.step')
 foreach($name in @('DIN_7991_M3x10','ISO_4762_M3x8')){
  $d=$app.Documents.Open((Join-Path $model ('Standard_Fasteners\'+$name+'.ipt')),$false)
  if(!$d.ComponentDefinition.IsContentMember){throw 'Fastener lost its standard Content Center identity.'}
  ExportStep $d (Join-Path $model ('Standard_Fasteners\'+$name+'.step'))
 }
 foreach($path in @((Join-Path $model 'Rod_Holder_Assembly_Drop8p5.iam'),(Join-Path $out 'Split_Mount_Plate_Only.iam'),(Join-Path $out 'Eight_M3_Fasteners.iam'))){
  $name=[IO.Path]::GetFileName($path)
  if(!(Test-Path -LiteralPath (Join-Path $backup $name))){Copy-Item -LiteralPath $path -Destination (Join-Path $backup $name)}
  $doc=$app.Documents.Open($path,$false)
  foreach($occ in @($doc.ComponentDefinition.Occurrences)){
   $oldPath=$occ.Definition.Document.FullFileName;$local=[IO.Path]::GetFileName($oldPath)
   if($local -eq 'Deck_M3x10_Countersunk.ipt'){
    $newPath=Join-Path $model 'Standard_Fasteners\DIN_7991_M3x10.ipt'
    $correction=@(@(1,0,0),@(0,-1,0),@(0,0,-1))
   }elseif($local -in @('Rod_M3x8_Simplified.ipt','Device_M3x8_Simplified.ipt')){
    $newPath=Join-Path $model 'Standard_Fasteners\ISO_4762_M3x8.ipt'
    $correction=@(@(0,0,-1),@(0,1,0),@(1,0,0))
   }else{continue}
   $savedName=$occ.Name;$before=Rows $occ.Transformation;$m=Compose $occ.Transformation $correction
   $occ.Grounded=$false;$occ.Replace($newPath,$false);$occ.Transformation=$m;$occ.Name=$savedName;$occ.Grounded=$true
   $changes+=@{assembly=$path;occurrence=$savedName;old_file=$oldPath;standard_file=$newPath;before_matrix_cm=$before;after_matrix_cm=(Rows $occ.Transformation)}
  }
  if(!$doc.Update2($false)){throw ('Assembly failed: '+$path)}
  $doc.Save()
 }
 $presentationSource=$app.Documents.Open((Join-Path $out 'Split_Mount_Presentation_Source.iam'),$false)
 $null=$presentationSource.Update2($false);$presentationSource.Save()
 $presentation=$app.Documents.Open((Join-Path $out 'Split_Mount_Assembly.ipn'),$false);$presentation.Save()
 $full=$app.Documents.Open((Join-Path $model 'Rod_Holder_Assembly_Drop8p5.iam'),$true)
 foreach($index in @(1,2)){
  $washerName='Device_Washer_M3_'+$index
  $existing=@($full.ComponentDefinition.Occurrences|Where-Object Name -eq $washerName)
  if($existing.Count -eq 1){
   $screw=@($full.ComponentDefinition.Occurrences|Where-Object Name -eq ('Device_Clamp_M3_'+$index))[0]
   $m=$screw.Transformation
   for($j=1;$j -le 3;$j++){$m.Cell($j,4)+=.05*$m.Cell($j,1)}
   $screw.Grounded=$false;$screw.Transformation=$m;$screw.Grounded=$true
   $existing[0].Delete()
  }
 }
 if(!$full.Update2($false)){throw 'Standard hardware assembly failed.'}
 $records=@();$count=0
 foreach($o in $full.ComponentDefinition.Occurrences){
  $path=$o.Definition.Document.FullFileName
  if($path -match '(Simplified|Deck_M3x10_Countersunk)\.ipt$'){throw ('Unreplaced hardware: '+$path)}
  if($path -like '*\Standard_Fasteners\*'){if($o.Name -notlike 'Device_Washer_*'){$count++};if(!$o.Definition.IsContentMember){throw 'Nonstandard member found.'}}
  $records+= [ordered]@{name=$o.Name;path=$path;matrix_cm=(Rows $o.Transformation)}
 }
 if($count -ne 18){throw ('Expected 18 standard fasteners, found '+$count)}
 $records|ConvertTo-Json -Depth 7|Set-Content -LiteralPath (Join-Path $model 'inward_placements.json') -Encoding UTF8
 $full.Save();ExportStep $full (Join-Path $model 'Rod_Holder_Assembly_Drop8p5.step')
 @($full.AllReferencedDocuments|ForEach-Object {$_.FullFileName})|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $model 'native_references.json') -Encoding UTF8
 [ordered]@{changes=$changes;full_assembly_standard_screws=$count;standard_device_washers=0;deck_screws=8;rod_screws=8;device_screws=2;countersink_diameter_mm=6.6;countersink_angle_deg=90;head_recess_mm=.1;deck_nominal_engagement_mm=6.1;deck_bore_end_clearance_mm=.4;device_nominal_engagement_mm=(8-3.039840616900516)}|ConvertTo-Json -Depth 10|Set-Content -LiteralPath (Join-Path $model 'standard_hardware_replacement.json') -Encoding UTF8
 Write-Output ('Replaced '+$changes.Count+' occurrences across three assemblies; full assembly contains 18 real Content Center members.')
}finally{$app.SilentOperation=$old}
