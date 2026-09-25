$ErrorActionPreference='Stop'
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application')
$fast=@($app.ContentCenter.TreeViewTopNode.ChildNodes|Where-Object DisplayName -eq 'Fasteners')[0]
$bolts=@($fast.ChildNodes|Where-Object DisplayName -eq 'Bolts')[0]
$node=@($bolts.ChildNodes|Where-Object DisplayName -eq 'Round Head')[0]
$rows=@()
foreach($family in $node.Families){
 $row=$family.TableRows.Item(1);$values=@{}
 foreach($name in @('NND','NLG','SIZE','SIZE_SEL','DESIGNATION','THREADDESC','KOD','KOH')){
  try{$values[$name]=$row.GetCellValue($name)}catch{}
 }
 $item=@{family=$family.DisplayName;id=$family.InternalName;first_row=$values}
 $rows+=,$item
 if($values.NND-match'^1([.,]0+)?$'){$item|ConvertTo-Json -Depth 5 -Compress|Write-Output}
}
$rows|ConvertTo-Json -Depth 6|Set-Content -LiteralPath (Join-Path $PSScriptRoot 'm1_round_candidates.json') -Encoding UTF8
Write-Output 'COMPLETE'
