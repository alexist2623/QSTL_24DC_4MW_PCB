$ErrorActionPreference='Stop'
Add-Type -Path 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
$root='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB'
$model=Join-Path $root 'QSTL_24DC_4MW_PCB\Mechanical_Assembly\Rod_Holder_Adapter_Drop8p5'
$out=Join-Path $model 'Manufacturing_DWG'
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application')
$tg=$app.TransientGeometry;$to=$app.TransientObjects
$old=$app.SilentOperation;$app.SilentOperation=$true
try {
 $members=Get-Content -LiteralPath (Join-Path $model 'content_center_fasteners.json') -Raw|ConvertFrom-Json
 $report=@()
 foreach($member in $members){
  if((Get-FileHash -LiteralPath $member.file).Hash -ne $member.sha256){throw 'Supplied member bytes changed.'}
  $d=$app.Documents.Open($member.file,$false);$cd=$d.ComponentDefinition
  if(!$cd.IsContentMember -or $cd.Features.ThreadFeatures.Count -ne 1){throw 'Expected a supplied threaded Content Center part.'}
  $thread=$cd.Features.ThreadFeatures.Item(1)
  if($thread.ThreadInfo.ThreadDesignation -ne 'M3x0.5' -or $thread.ThreadInfo.Class -ne '6g' -or $thread.ThreadInfo.Internal -or $thread.HealthStatus -ne [Inventor.HealthStatusEnum]::kUpToDateHealth){throw 'Incorrect external thread.'}
  $report+=@{file=$member.file;family=$member.family;is_content_member=$true;unchanged_library_member=$true;designation=$thread.ThreadInfo.ThreadDesignation;thread_class=$thread.ThreadInfo.Class}
 }
 $assemblies=@()
 foreach($spec in @(@((Join-Path $model 'Rod_Holder_Assembly_Drop8p5.iam'),18),@((Join-Path $out 'Split_Mount_Plate_Only.iam'),8),@((Join-Path $out 'Eight_M3_Fasteners.iam'),8))){
  $d=$app.Documents.Open($spec[0],$false);$count=0
  foreach($o in $d.ComponentDefinition.Occurrences){
   if($o.Name -like '*Washer*'){throw 'Unrequested washer found.'}
   $path=$o.Definition.Document.FullFileName
   if($path -match '(Device_M3x8_Simplified|Rod_M3x8_Simplified|Deck_M3x10_Countersunk)\.ipt$'){throw 'Old handmade screw found.'}
   if($path -like '*\Standard_Fasteners\*'){
    $count++
    if(!$o.Definition.IsContentMember){throw 'Assembly uses nonstandard hardware.'}
    if($o.Name -like 'Deck_Join*' -and !($path.EndsWith('DIN_7991_M3x10.ipt'))){throw 'Deck screw is not countersunk DIN 7991.'}
   }
  }
  if($count -ne $spec[1]){throw 'Wrong number of standard screws.'}
  $assemblies+=@{file=$spec[0];standard_screws=$count;washers=0;old_handmade_screws=0}
 }
 $machined=@()
 foreach($part in @('Centre_Plate','Left_Rod_Support','Right_Rod_Support')){
  $d=$app.Documents.Open((Join-Path $model ($part+'.ipt')),$false);$cd=$d.ComponentDefinition
  $expected=if($part -eq 'Centre_Plate'){10}else{4}
  if($cd.Features.ThreadFeatures.Count -ne $expected){throw 'Internal thread count changed.'}
  foreach($t in $cd.Features.ThreadFeatures){if($t.ThreadInfo.ThreadDesignation -ne 'M3x0.5' -or $t.ThreadInfo.Class -ne '6H' -or !$t.ThreadInfo.Internal -or $t.HealthStatus -ne [Inventor.HealthStatusEnum]::kUpToDateHealth){throw 'Incorrect internal thread.'}}
  $machined+=@{part=$part;internal_threads=$expected;designation='M3x0.5-6H';single_solid=($cd.SurfaceBodies.Count -eq 1)}
 }
 [ordered]@{library_members=$report;assemblies=$assemblies;machined_parts=$machined;device_washers=0;geometry_report='geometry_verification.json'}|ConvertTo-Json -Depth 8|Set-Content -LiteralPath (Join-Path $model 'standard_hardware_audit.json') -Encoding UTF8
 Write-Output 'Verified all 3 supplied member families, native thread metadata, counts and unchanged machined parts.'
}finally{$app.SilentOperation=$old}
