$ErrorActionPreference='Stop'
Add-Type -Path 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
$root='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB'
$model=Join-Path $root 'QSTL_24DC_4MW_PCB\Mechanical_Assembly\Rod_Holder_Adapter_Drop8p5'
$target=Join-Path $model 'Rod_Holder_Assembly_Drop8p5.iam'
$backup=Join-Path $model 'OldVersions\Rod_Holder_Assembly_Drop8p5.0003.iam'
$tmp=Join-Path $root 'script\cnc_drawings_20260922\tmp'
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application')
function Placements($d){
 $rows=@();foreach($o in $d.ComponentDefinition.Occurrences){
  $matrix=@();foreach($r in 1..4){foreach($c in 1..4){$matrix+=[math]::Round($o.Transformation.Cell($r,$c),12)}}
  $rows+=,[ordered]@{name=$o.Name;file=$o.Definition.Document.FullFileName;matrix=$matrix}
 };return ($rows|ConvertTo-Json -Depth 8 -Compress)
}
$current=$app.Documents.Open($target,$false);$before=Placements $current
foreach($d in @($app.Documents)){if($d.DocumentType -eq [Inventor.DocumentTypeEnum]::kDrawingDocumentObject -and $d.FullFileName -like '*Manufacturing_DWG*'){$d.Close($true)}}
$current.Close($true)
# Preserve the section-generated metadata version, then restore Inventor's immediate predecessor.
Copy-Item -LiteralPath $target -Destination (Join-Path $tmp 'assembly_after_drawing_section.iam') -Force
Copy-Item -LiteralPath $backup -Destination $target -Force
$restored=$app.Documents.Open($target,$false);$after=Placements $restored
if($before -ne $after){throw 'Occurrence placements differ after source restoration.'}
$restored.Close($true)
$expected=(Get-FileHash -LiteralPath $backup).Hash
if((Get-FileHash -LiteralPath $target).Hash -ne $expected){throw 'Restored source hash mismatch.'}
[ordered]@{restored_from=$backup;sha256=$expected;placements_unchanged=$true;reason='Native assembly section generated saved metadata; original automatic predecessor restored. Cylinder installation sheet removed per user.'}|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $tmp 'source_restore_audit.json')
Write-Output 'Original assembly restored; all 24 occurrence placements unchanged.'
Write-Output ('Precision property type: '+[Inventor.LinearGeneralDimension].GetProperty('Precision').PropertyType.FullName)
Write-Output ('Precision enum value: '+[int][Inventor.LinearPrecisionEnum]::kFourDecimalPlacesLinearPrecision)
