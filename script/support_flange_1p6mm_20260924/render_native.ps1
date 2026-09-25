$ErrorActionPreference='Stop'
Add-Type -Path 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
$root='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB'
$model=Join-Path $root 'QSTL_24DC_4MW_PCB\Mechanical_Assembly\Rod_Holder_Adapter_Drop8p5'
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application');$tg=$app.TransientGeometry;$to=$app.TransientObjects
$oldSilent=$app.SilentOperation;$app.SilentOperation=$true
try {
$doc=$app.Documents.Open((Join-Path $model 'Rod_Holder_Assembly_Drop8p5.iam'),$true);$doc.Activate()
$views=$doc.ComponentDefinition.RepresentationsManager.DesignViewRepresentations
$view=@($views|Where-Object Name -eq 'Tube_Review')[0];$view.Activate()
$tube=@($doc.ComponentDefinition.Occurrences|Where-Object Name -eq 'Probe_Tube_ID51_OD54')[0];$tube.Visible=$true
$cam=$app.ActiveView.Camera;$cam.Perspective=$false
$cam.Target=$tg.CreatePoint(2.55,17.5,.3);$cam.Eye=$tg.CreatePoint(2.55,65,.3);$cam.UpVector=$tg.CreateUnitVector(0,0,-1);$cam.SetExtents(6.2,6.2);$cam.ApplyWithoutTransition()
$bg=$to.CreateColor(244,247,250)
$cam.SaveAsBitmap((Join-Path $model 'Cylinder_top_1p6mm.png'),1500,1500,$bg,$bg)
$doc.Save()
$plate=$app.Documents.Open((Join-Path $model 'Manufacturing_DWG\Split_Mount_Plate_Only.iam'),$true);$plate.Activate()
$cam=$app.ActiveView.Camera;$cam.Perspective=$false;$cam.Target=$tg.CreatePoint(2.55,4,.65);$cam.Eye=$tg.CreatePoint(2.55,-30,.65);$cam.UpVector=$tg.CreateUnitVector(0,0,-1);$cam.Fit();$cam.ApplyWithoutTransition()
$cam.SaveAsBitmap((Join-Path $model 'Support_end_1p6mm_45deg.png'),1600,700,$bg,$bg)
$doc.Activate()
Write-Output 'Saved native axial cylinder top view and 1.6 mm support end view.'
} finally {$app.SilentOperation=$oldSilent}
