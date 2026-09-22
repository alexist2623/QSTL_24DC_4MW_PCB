$ErrorActionPreference='Stop'
Add-Type -Path 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application')
$root='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\script\cnc_drawings_20260922'
$ref='C:\JeonghyunPark\Workspace\QSTL_M12C_BNC\Enclosure3'
$result=@()
$old=$app.SilentOperation;$app.SilentOperation=$true
try {
 foreach($file in @('Enclosure.dwg','Body.dwg','Enclosure.ipn')) {
  $path=Join-Path $ref $file
  $doc=$app.Documents.Open($path,$true)
  $info=[ordered]@{file=$file;document_type=$doc.DocumentType;references=@($doc.ReferencedDocumentDescriptors|ForEach-Object{$_.FullDocumentName})}
  if($file -like '*.dwg') {
   $info.sheets=@()
   foreach($s in $doc.Sheets){
    $s.Activate();$app.ActiveView.Fit()
    $info.sheets+= [ordered]@{name=$s.Name;width=$s.Width*10;height=$s.Height*10;titleblock=$s.TitleBlock.Definition.Name;border=$s.Border.Definition.Name;views=@($s.DrawingViews|ForEach-Object{[ordered]@{name=$_.Name;scale=$_.Scale;position=@(($_.Position.X*10),($_.Position.Y*10));width=$_.Width*10;height=$_.Height*10;reference=$_.ReferencedDocumentDescriptor.FullDocumentName}});notes=@($s.DrawingNotes.GeneralNotes|ForEach-Object{$_.Text});balloons=$s.Balloons.Count;parts_lists=$s.PartsLists.Count}
    $app.ActiveView.SaveAsBitmap((Join-Path $root ('tmp\reference_'+$file+'_'+$s.Name.Replace(':','_')+'.png')),1800,1100)
   }
  } else {
   $info.scenes=@($doc.Scenes|ForEach-Object{[ordered]@{name=$_.Name;snapshot_count=$_.SnapshotViews.Count;component=$_.Component.Name}})
   $app.ActiveView.Fit();$app.ActiveView.SaveAsBitmap((Join-Path $root 'tmp\reference_presentation.png'),1600,1000)
  }
  $result+=$info
 }
 $result|ConvertTo-Json -Depth 10 |Set-Content -LiteralPath (Join-Path $root 'tmp\enclosure_reference_audit.json')
 $result|ConvertTo-Json -Depth 10
}finally{$app.SilentOperation=$old}
