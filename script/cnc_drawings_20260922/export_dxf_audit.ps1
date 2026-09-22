$ErrorActionPreference='Stop'
Add-Type -Path 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
$root='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB'
$here=Join-Path $root 'script\cnc_drawings_20260922'
$out=Join-Path $root 'QSTL_24DC_4MW_PCB\Mechanical_Assembly\Rod_Holder_Adapter_Drop8p5\Manufacturing_DWG'
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application');$to=$app.TransientObjects;$previousSilent=$app.SilentOperation;$app.SilentOperation=$true
$d=$app.Documents.Open((Join-Path $out 'QSTL_Split_Mount_RevB.idw'),$true);$d.Activate()
foreach($s in $d.Sheets){$s.Activate();$d.Update2($false)|Out-Null;Write-Output ($s.Name+': '+$s.DrawingDimensions.GeneralDimensions.Count+' dimensions')}
$ctx=$to.CreateTranslationContext();$ctx.Type=[Inventor.IOMechanismEnum]::kFileBrowseIOMechanism
$ini=(Get-Content -LiteralPath (Join-Path $here 'export_autocad.ini') -Raw).Replace('DESTINATION DXF=No','DESTINATION DXF=Yes').Replace('SCALING=Geometry','SCALING=Layout')
$iniPath=Join-Path $here 'tmp\audit_dxf.ini';[IO.File]::WriteAllText($iniPath,$ini)
$add=$app.ApplicationAddIns.ItemById('{C24E3AC4-122E-11D5-8E91-0010B541CD80}')
$opt=$to.CreateNameValueMap();$media=$to.CreateDataMedium();$null=$add.HasSaveCopyAsOptions($d,$ctx,$opt)
$opt.Value('Export_Acad_IniFile')=$iniPath;$media.FileName=Join-Path $here 'tmp\audit_layout.dxf'
$add.SaveCopyAs($d,$ctx,$opt,$media)
Write-Output 'Exported DXF audit using the DWG export configuration.'
$app.SilentOperation=$previousSilent
