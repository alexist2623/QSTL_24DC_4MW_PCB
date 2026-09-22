$ErrorActionPreference='Stop'
Add-Type -Path 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application')
$root='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB'
$doc=$app.Documents.Open((Join-Path $root 'script\cnc_drawings_20260922\tmp\probe.idw'),$true)
$sheet=$doc.ActiveSheet;$view=$sheet.DrawingViews.Item(1);$tg=$app.TransientGeometry;$to=$app.TransientObjects
$styles=$doc.StylesManager;$style=$styles.DimensionStyles.Item('Default - mm (ANSI)')
$style.TextStyle.FontSize=0.25;$style.TextStyle.Font='Arial';$style.LinearPrecision=[Inventor.LinearPrecisionEnum]::kTwoDecimalPlacesLinearPrecision
$curves=$view.DrawingCurves();$line=$null
foreach($c in $curves){if($c.StartPoint -and $c.EndPoint -and [math]::Abs($c.StartPoint.Y-21)-lt 0.001 -and [math]::Abs($c.EndPoint.Y-21)-lt 0.001){$line=$c;break}}
$intent=$sheet.CreateGeometryIntent($line)
$dim=$sheet.DrawingDimensions.GeneralDimensions.AddLinear($tg.CreatePoint2d(10,22),$intent,[Type]::Missing,[Inventor.DimensionTypeEnum]::kHorizontalDimensionType,$true,$style)
$note=$sheet.DrawingNotes.GeneralNotes.AddFitted($tg.CreatePoint2d(2,24),'<StyleOverride Font="Arial" FontSize="0.3">TEST - MODEL ASSOCIATED DIMENSION</StyleOverride>')
$ctx=$to.CreateTranslationContext();$ctx.Type=[Inventor.IOMechanismEnum]::kFileBrowseIOMechanism
foreach($kind in @('pdf','dwg')){
 $guid=if($kind -eq 'pdf'){'{0AC6FD96-2F4D-42CE-8BE0-8AEA580399E4}'}else{'{C24E3AC2-122E-11D5-8E91-0010B541CD80}'}
 $add=$app.ApplicationAddIns.ItemById($guid);$opt=$to.CreateNameValueMap();$media=$to.CreateDataMedium()
 $null=$add.HasSaveCopyAsOptions($doc,$ctx,$opt)
 if($kind -eq 'pdf'){$opt.Value('All_Color_AS_Black')=1;$opt.Value('Sheet_Range')=[Inventor.PrintRangeEnum]::kPrintAllSheets}
 else{$opt.Value('Export_Acad_IniFile')='C:\Users\Public\Documents\Autodesk\Inventor 2027\Design Data\DWG-DXF\exportdwg.ini'}
 $media.FileName=Join-Path $root ('script\cnc_drawings_20260922\tmp\probe.'+$kind)
 $add.SaveCopyAs($doc,$ctx,$opt,$media)
 Write-Output "$kind exported"
}
$doc.SaveAsInventorDWG((Join-Path $root 'script\cnc_drawings_20260922\tmp\probe_native.dwg'),$true)
Write-Output ('Dimension mm: '+($dim.ModelValue*10))
$doc.Save()
