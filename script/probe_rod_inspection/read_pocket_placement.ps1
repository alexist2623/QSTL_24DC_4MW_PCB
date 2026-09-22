$ErrorActionPreference='Stop'
Add-Type -Path 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
$root='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB'
$out=Join-Path $root 'QSTL_24DC_4MW_PCB\Mechanical_Assembly\Rod_Holder_Adapter'
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application')
function Matrix-Rows($matrix) {
    $rows=@();for($i=1;$i -le 4;$i++) {$row=@();for($j=1;$j -le 4;$j++) {$row+=$matrix.Cell($i,$j)};$rows+=,$row};return ,$rows
}
$assembly=$app.Documents.Open((Join-Path $out 'Rod_Holder_Assembly.iam'),$false)
$carrier=@($assembly.ComponentDefinition.Occurrences|Where-Object {$_.Name -eq 'Existing_Carrier_Hung_From_Side_Slots'})[0]
$pcb=@($carrier.Definition.Document.ComponentDefinition.Occurrences|Where-Object {$_.Name -eq 'Current PCB - simplified'})[0]
$board=@($pcb.Definition.Document.ComponentDefinition.Occurrences|Where-Object {$_.Definition.Document.FullFileName -like '*\PCB_board.ipt'})[0]
if ($null -eq $board) {throw 'Could not identify the substrate occurrence.'}
$tube=@($assembly.ComponentDefinition.Occurrences|Where-Object {$_.Name -eq 'Probe_Tube_ID51_OD54'})[0]
[pscustomobject]@{carrier_matrix_cm=(Matrix-Rows $carrier.Transformation);pcb_matrix_cm=(Matrix-Rows $pcb.Transformation);board_matrix_cm=(Matrix-Rows $board.Transformation);tube_matrix_cm=(Matrix-Rows $tube.Transformation);board_path=$board.Definition.Document.FullFileName} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $out 'pocket_measurement_transforms.json') -Encoding UTF8
Write-Output 'Read actual nested PCB and tube occurrence transforms without modifying CAD.'
