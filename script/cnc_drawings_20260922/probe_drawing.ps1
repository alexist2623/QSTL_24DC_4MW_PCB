$ErrorActionPreference='Stop'
Add-Type -Path 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application')
$root='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB'
$model=Join-Path $root 'QSTL_24DC_4MW_PCB\Mechanical_Assembly\Rod_Holder_Adapter_Drop8p5'
$tg=$app.TransientGeometry
$old=$app.ActiveDocument
if($old.DocumentType -eq [Inventor.DocumentTypeEnum]::kDrawingDocumentObject -and $old.FullFileName.EndsWith('probe.idw')){$old.Close($true)}
$doc=$app.Documents.Add([Inventor.DocumentTypeEnum]::kDrawingDocumentObject,'C:\Users\Public\Documents\Autodesk\Inventor 2027\Templates\en-US\Metric\ANSI (mm).idw',$true)
$doc.DisplayName='CNC DRAWING API PROBE'
$sheet=$doc.ActiveSheet
$sheet.Size=[Inventor.DrawingSheetSizeEnum]::kBDrawingSheetSize
$sheet.Orientation=[Inventor.PageOrientationTypeEnum]::kLandscapePageOrientation
if($sheet.TitleBlock){$sheet.TitleBlock.Delete()}
if($sheet.Border){$sheet.Border.Delete()}
$part=$app.Documents.Open((Join-Path $model 'Centre_Plate.ipt'),$false)
$cam=$app.TransientObjects.CreateCamera()
$cam.Eye=$tg.CreatePoint(2.55,4,100);$cam.Target=$tg.CreatePoint(2.55,4,0);$cam.UpVector=$tg.CreateUnitVector(0,1,0)
$view=$sheet.DrawingViews.AddBaseView($part,$tg.CreatePoint2d(10,15),1.5,[Inventor.ViewOrientationTypeEnum]::kArbitraryViewOrientation,[Inventor.DrawingViewStyleEnum]::kHiddenLineDrawingViewStyle,'',$cam)
$doc.Update2($false)|Out-Null
$view.Name='BOSS FACE'
$row=@()
foreach($curve in $view.DrawingCurves()){
 $o=[ordered]@{type=[string]$curve.CurveType}
 if($curve.StartPoint){$o.start=@($curve.StartPoint.X,$curve.StartPoint.Y)}
 if($curve.EndPoint){$o.end=@($curve.EndPoint.X,$curve.EndPoint.Y)}
 if($curve.CenterPoint){$o.center=@($curve.CenterPoint.X,$curve.CenterPoint.Y)}
 $row+=$o
}
@{sheet=@($sheet.Width,$sheet.Height);view=@($view.Width,$view.Height);curves=$row;dimstyles=@($doc.StylesManager.DimensionStyles|ForEach-Object {$_.Name});textstyles=@($doc.StylesManager.TextStyles|ForEach-Object {$_.Name})}|ConvertTo-Json -Depth 6|Set-Content -LiteralPath (Join-Path $root 'script\cnc_drawings_20260922\tmp\drawing_probe.json')
$doc.SaveAs((Join-Path $root 'script\cnc_drawings_20260922\tmp\probe.idw'),$false)
Write-Output 'Probe drawing created.'
