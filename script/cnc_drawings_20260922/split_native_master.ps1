$ErrorActionPreference='Stop'
Add-Type -Path 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
$out='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB\Mechanical_Assembly\Rod_Holder_Adapter_Drop8p5\Manufacturing_DWG'
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application')
$before=$app.SilentOperation;$app.SilentOperation=$true
try {
 foreach($d in @($app.Documents)){if($d.FullFileName -like "$out\QSTL_Split_Mount_RevB_QSTL-*.dwg"){$d.Close($true)}}
 $master=$app.Documents.Open((Join-Path $out 'QSTL_Split_Mount_RevB_Inventor.dwg'),$false)
 foreach($code in @('CP01','CP02','LS01','RS01','AS01')){
  $path=Join-Path $out ('QSTL_Split_Mount_RevB_QSTL-'+$code+'.dwg')
  $master.SaveAsInventorDWG($path,$true)
  $single=$app.Documents.Open($path,$true)
  foreach($s in @($single.Sheets)){if(!$s.Name.StartsWith('QSTL-'+$code+':')){$s.Delete()}}
  $single.Sheets.Item(1).Activate();$single.Update2($false)|Out-Null;$app.ActiveView.Fit();$single.Save()
  if($code -ne 'AS01'){$single.Close($true)}
  Write-Output ($code+': native master styles retained.')
 }
}finally{$app.SilentOperation=$before}
