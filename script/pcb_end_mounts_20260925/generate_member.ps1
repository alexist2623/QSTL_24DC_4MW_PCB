$ErrorActionPreference='Stop'
$interop='C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
Add-Type -Path $interop
Add-Type -ReferencedAssemblies $interop -TypeDefinition @'
public static class ContentBridge {
 public static string Create(object obj, int row) {
  var f=(Inventor.ContentFamily)obj;
  Inventor.MemberManagerErrorsEnum reason; string message;
  string path=f.CreateMember(row,out reason,out message);
  if(string.IsNullOrEmpty(path)) throw new System.Exception(reason+": "+message);
  return path;
 }
}
'@
$root='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB'
$model=Join-Path $root 'QSTL_24DC_4MW_PCB\Mechanical_Assembly\ZIF_M2_Review'
$out=Join-Path $model 'Standard_Fasteners'
$null=New-Item -ItemType Directory -Path $out -Force
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application')
$old=$app.SilentOperation;$app.SilentOperation=$true
$report=@()
try {
 $fast=@($app.ContentCenter.TreeViewTopNode.ChildNodes|Where-Object DisplayName -eq 'Fasteners')[0]
 $bolts=@($fast.ChildNodes|Where-Object DisplayName -eq 'Bolts')[0]
 foreach($spec in (,@('Socket Head','ISO 4762',4,'ISO_4762_M2x4.ipt'))){
  if($spec[0] -eq 'Plain'){
   $washers=@($fast.ChildNodes|Where-Object DisplayName -eq 'Washers')[0]
   $node=@($washers.ChildNodes|Where-Object DisplayName -eq 'Plain')[0]
  }else{$node=@($bolts.ChildNodes|Where-Object DisplayName -eq $spec[0])[0]}
  $family=@($node.Families|Where-Object DisplayName -eq $spec[1])[0]
  $matches=@();for($i=1;$i -le $family.TableRows.Count;$i++){
   $row=$family.TableRows.Item($i)
   if([double]$row.GetCellValue('NND') -eq 2 -and ($spec[0] -eq 'Plain' -or [double]$row.GetCellValue('NLG') -eq $spec[2])){$matches+= $i}
  }
  if($matches.Count -ne 1){
   foreach($index in $matches){$r=$family.TableRows.Item($index);$v=[ordered]@{row=$index};foreach($col in $family.TableColumns){$v[$col.InternalName]=$r.GetCellValue($col.InternalName)};$v|ConvertTo-Json -Compress|Write-Output}
   throw ('Expected one exact standard member; found '+$matches.Count)
  }
  $row=$family.TableRows.Item($matches[0]);$values=[ordered]@{}
  foreach($col in $family.TableColumns){$values[$col.InternalName]=$row.GetCellValue($col.InternalName)}
  $source=[ContentBridge]::Create($family,$matches[0])
  $dest=Join-Path $out $spec[3]
  if(!(Test-Path -LiteralPath $dest)){Copy-Item -LiteralPath $source -Destination $dest}
  if((Get-FileHash -LiteralPath $source).Hash -ne (Get-FileHash -LiteralPath $dest).Hash){throw 'Member copy changed.'}
  $doc=$app.Documents.Open($dest,$false);$cd=$doc.ComponentDefinition
  if(!$cd.IsContentMember){throw 'Generated part must retain Content Center identity.'}
  $bounds=$cd.RangeBox
  $threads=@();foreach($t in $cd.Features.ThreadFeatures){$threads+=@{designation=$t.ThreadInfo.ThreadDesignation;class=$t.ThreadInfo.Class;internal=$t.ThreadInfo.Internal;health=$t.HealthStatus;depth_mm=($t.ThreadDepth.Value*10)}}
  $report+= [ordered]@{family=$family.DisplayName;library=$family.LibraryName;family_id=$family.InternalName;row=$matches[0];source=$source;file=$dest;sha256=(Get-FileHash -LiteralPath $dest).Hash;is_content_member=$cd.IsContentMember;values=$values;bounds_mm=@(@(($bounds.MinPoint.X*10),($bounds.MinPoint.Y*10),($bounds.MinPoint.Z*10)),@(($bounds.MaxPoint.X*10),($bounds.MaxPoint.Y*10),($bounds.MaxPoint.Z*10)));threads=$threads}
 }
 $report|ConvertTo-Json -Depth 8|Set-Content -LiteralPath (Join-Path $model 'm2_member.json') -Encoding UTF8
 $report|ConvertTo-Json -Depth 8|Write-Output
}finally{$app.SilentOperation=$old}


