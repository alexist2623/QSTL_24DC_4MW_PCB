$ErrorActionPreference='Stop'
Add-Type -Path 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
$root='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB'
$out=Join-Path $root 'QSTL_24DC_4MW_PCB\Mechanical_Assembly\Rod_Holder_Adapter_Drop8p5\Manufacturing_DWG'
$tmp=Join-Path $root 'script\cnc_drawings_20260922\tmp\autocad_pdf';$null=New-Item -ItemType Directory -Path $tmp -Force
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application');$old=$app.SilentOperation;$app.SilentOperation=$true
$to=$app.TransientObjects;$add=$app.ApplicationAddIns.ItemById('{0AC6FD96-2F4D-42CE-8BE0-8AEA580399E4}')
$ctx=$to.CreateTranslationContext();$ctx.Type=[Inventor.IOMechanismEnum]::kFileBrowseIOMechanism
$rows=@()
try{
 foreach($f in Get-ChildItem -LiteralPath $out -Filter 'QSTL_Split_Mount_RevB_QSTL-*.dwg'){
  $d=$app.Documents.Open($f.FullName,$true)
  $s=$d.Sheets.Item(1);$s.Activate()
  $opt=$to.CreateNameValueMap();$media=$to.CreateDataMedium();$null=$add.HasSaveCopyAsOptions($d,$ctx,$opt)
  $opt.Value('All_Color_AS_Black')=1;$opt.Value('Sheet_Range')=[Inventor.PrintRangeEnum]::kPrintCurrentSheet
  $media.FileName=Join-Path $tmp ($f.BaseName+'.pdf');$add.SaveCopyAs($d,$ctx,$opt,$media)
  $rows+=[ordered]@{file=$f.Name;layout=$s.Name;referenced_documents=$d.AllReferencedDocuments.Count;views=$s.DrawingViews.Count;blocks=$s.AutoCADBlocks.Count}
  $d.Close($true)
 }
 $rows|ConvertTo-Json -Depth 5|Set-Content -LiteralPath (Join-Path $out 'autocad_export_audit.json')
 $rows|ConvertTo-Json -Depth 5
}finally{$app.SilentOperation=$old}
