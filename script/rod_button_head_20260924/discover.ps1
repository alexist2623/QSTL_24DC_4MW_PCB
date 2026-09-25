$ErrorActionPreference='Stop'
Add-Type -Path 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application')
$fast=@($app.ContentCenter.TreeViewTopNode.ChildNodes|Where-Object DisplayName -eq 'Fasteners')[0]
$bolts=@($fast.ChildNodes|Where-Object DisplayName -eq 'Bolts')[0]
foreach($node in $bolts.ChildNodes){
 $families=@($node.Families|Where-Object {$_.DisplayName -match '7380|Button|Round'})
 [pscustomobject]@{category=$node.DisplayName;families=@($families|ForEach-Object {$_.DisplayName})}|ConvertTo-Json -Compress
}
