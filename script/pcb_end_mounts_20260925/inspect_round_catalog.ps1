$ErrorActionPreference='Stop'
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application')
$fast=@($app.ContentCenter.TreeViewTopNode.ChildNodes|Where-Object DisplayName -eq 'Fasteners')[0]
$bolts=@($fast.ChildNodes|Where-Object DisplayName -eq 'Bolts')[0]
$report=@()
foreach($node in $bolts.ChildNodes){
 $families=@();foreach($family in $node.Families){$families+=@{name=$family.DisplayName;id=$family.InternalName;rows=$family.TableRows.Count}}
 $report+=@{category=$node.DisplayName;families=$families}
}
$report|ConvertTo-Json -Depth 8|Set-Content -LiteralPath (Join-Path $PSScriptRoot 'round_catalog.json') -Encoding UTF8
$report|Where-Object {$_.category-match'Round|Pan|Cheese|Button'}|ConvertTo-Json -Depth 8
Write-Output ('CATEGORIES: '+(($report|ForEach-Object category)-join'; '))
