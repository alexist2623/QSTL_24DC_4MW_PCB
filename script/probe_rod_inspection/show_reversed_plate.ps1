$ErrorActionPreference='Stop'
Add-Type -Path 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
$root='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB'
$out=Join-Path $root 'QSTL_24DC_4MW_PCB\Mechanical_Assembly\Rod_Holder_Adapter'
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application');$tg=$app.TransientGeometry;$to=$app.TransientObjects
$silent=$app.SilentOperation
try {
    $app.SilentOperation=$true
    $doc=$app.Documents.Open((Join-Path $out 'Rod_Holder_Assembly.iam'),$true)
    $doc.ComponentDefinition.RepresentationsManager.DesignViewRepresentations.Item('Interior_Review').Activate()
    $doc.Activate();$camera=$app.ActiveView.Camera;$camera.Perspective=$false
    # Keep physical Z horizontal so that the rod and reversed plate faces are distinct.
    $camera.Eye=$tg.CreatePoint(20,21,0.3);$camera.Target=$tg.CreatePoint(2.55,17.5,0.3)
    $camera.UpVector=$tg.CreateUnitVector(0,1,0);$camera.SetExtents(10,10);$camera.ApplyWithoutTransition()
    $bg=$to.CreateColor(246,248,251)
    $camera.SaveAsBitmap((Join-Path $out 'Reversed_plate_side.png'),1200,1200,$bg,$bg)
    $doc.Save()
    Write-Output $doc.FullFileName
} finally {$app.SilentOperation=$silent}
