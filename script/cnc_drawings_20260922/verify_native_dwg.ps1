$ErrorActionPreference='Stop'
Add-Type -Path 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
$root='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB'
$out=Join-Path $root 'QSTL_24DC_4MW_PCB\Mechanical_Assembly\Rod_Holder_Adapter_Drop8p5\Manufacturing_DWG'
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application')
$before=$app.SilentOperation;$app.SilentOperation=$true
try{
 $native=Join-Path $out 'QSTL_Split_Mount_RevB_Inventor.dwg'
 $d=$app.Documents.Open($native,$true)
 if(!$d.IsInventorDWG -or $d.Sheets.Count -ne 5){throw 'Native DWG type / sheet count mismatch.'}
 $rows=@();$total=0
 foreach($s in $d.Sheets){
  $s.Activate();$d.Update2($false)|Out-Null
  if([math]::Abs($s.Width-42) -gt 0.001 -or [math]::Abs($s.Height-29.7) -gt 0.001){throw 'Expected ISO A3 paper.'}
  if(!$s.Border -or !$s.TitleBlock){throw 'Missing native sheet border / title block.'}
  foreach($note in $s.DrawingNotes.GeneralNotes){if($note.Text -match 'BILL OF MATERIALS|ASSEMBLY SEQUENCE|NOTES:'){throw 'Removed text block returned.'}}
  foreach($v in $s.DrawingViews){if(!$v.IsUpdateComplete){throw ('Incomplete view: '+$v.Name)}}
  foreach($dim in $s.DrawingDimensions.GeneralDimensions){if(!$dim.Attached -or $dim.ModelValueOverridden){throw 'Detached or overridden dimension found.'};$total++}
  $rows+=[ordered]@{sheet=$s.Name;views=$s.DrawingViews.Count;native_dimensions=$s.DrawingDimensions.GeneralDimensions.Count;width_mm=$s.Width*10;height_mm=$s.Height*10;border=$s.Border.Definition.Name;titleblock=$s.TitleBlock.Definition.Name;references=@($s.DrawingViews|ForEach-Object{$_.ReferencedDocumentDescriptor.FullDocumentName})}
 }
 if($total -ne 46){$rows|ConvertTo-Json;throw "Expected 46 dimensions, found $total"}
 $d.Close($true)
 $files=@()
 foreach($p in Get-ChildItem -LiteralPath $out -Filter 'QSTL_Split_Mount_RevB_QSTL-*.dwg'){
  $f=$app.Documents.Open($p.FullName,$false)
  if(!$f.IsInventorDWG -or $f.Sheets.Count -ne 1){throw 'Standalone drawing is not a single-sheet Inventor DWG.'}
  $s=$f.Sheets.Item(1);$s.Activate();$f.Update2($false)|Out-Null
  if($s.DrawingViews.Count -lt 2 -or !$s.TitleBlock -or !$s.Border){throw 'Standalone native drawing objects missing.'}
  foreach($dim in $s.DrawingDimensions.GeneralDimensions){if(!$dim.Attached -or $dim.ModelValueOverridden){throw 'Standalone dimension detached or overridden.'}}
  $files+=[ordered]@{file=$p.Name;document_type=[string]$f.DocumentType;inventor_dwg=$f.IsInventorDWG;sheets=$f.Sheets.Count;bytes=$p.Length}
  $f.Close($true)
 }
 if($files.Count -ne 5){throw 'Expected five standalone Inventor DWG sheets.'}
 [ordered]@{native_sheets=$rows;native_dimension_count=$total;standalone_files=$files;status='Saved native DWG master and five single-sheet native DWGs reopened successfully'}|ConvertTo-Json -Depth 8|Set-Content -LiteralPath (Join-Path $out 'dwg_reopen_audit.json')
 $d=$app.Documents.Open($native,$true);$d.Activate();$d.Sheets.Item(5).Activate();$app.ActiveView.Fit()
 Write-Output 'Reopened all six DWG files; five sheets and 46 attached native dimensions verified.'
}finally{$app.SilentOperation=$before}
