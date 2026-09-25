$ErrorActionPreference='Stop'
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application')
$fast=@($app.ContentCenter.TreeViewTopNode.ChildNodes|Where-Object DisplayName -eq 'Fasteners')[0]
$bolts=@($fast.ChildNodes|Where-Object DisplayName -eq 'Bolts')[0]
$rows=@()
foreach($spec in @(@('Socket Head','ISO 4762'),@('Round Head','ISO 7380-1'),@('Pan Head','ISO 7045'))){
 $node=@($bolts.ChildNodes|Where-Object DisplayName -eq $spec[0])[0]
 if(!$node){continue}
 $family=@($node.Families|Where-Object DisplayName -eq $spec[1])[0]
 if(!$family){continue}
 $found=@{}
 for($i=1;$i-le$family.TableRows.Count;$i++){
  $row=$family.TableRows.Item($i);$dia=[double]$row.GetCellValue('NND')
  if($dia-le2){$found[[string]$dia]=$true}
 }
 $rows+=@{family=$family.DisplayName;diameters_mm=@($found.Keys|Sort-Object)}
}
$rows|ConvertTo-Json -Depth 5|Set-Content -LiteralPath (Join-Path $PSScriptRoot 'small_screw_catalog.json') -Encoding UTF8
$rows|ConvertTo-Json -Depth 5
