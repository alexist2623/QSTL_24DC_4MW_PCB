$ErrorActionPreference='Stop'
Add-Type -Path 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
$root='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB'
$model=Join-Path $root 'QSTL_24DC_4MW_PCB\Mechanical_Assembly\Rod_Holder_Adapter_Drop8p5'
$output=Join-Path $root 'script\cnc_drawings_20260922\tmp\cnc_exploded.png'
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application');$tg=$app.TransientGeometry;$to=$app.TransientObjects
$silent=$app.SilentOperation;$preview=$null
function Position($x,$y,$z) {$m=$tg.CreateMatrix();$m.SetTranslation($tg.CreateVector($x/10,$y/10,$z/10),$false);return $m}
try {
    $app.SilentOperation=$true
    $preview=$app.Documents.Add([Inventor.DocumentTypeEnum]::kAssemblyDocumentObject,$app.FileManager.GetTemplateFile([Inventor.DocumentTypeEnum]::kAssemblyDocumentObject),$true)
    foreach($item in @(@('Centre_Plate',0,0,-10),@('Left_Rod_Support',-30,0,8),@('Right_Rod_Support',30,0,8))) {
        $occ=$preview.ComponentDefinition.Occurrences.Add((Join-Path $model ($item[0]+'.ipt')),(Position $item[1] $item[2] $item[3]));$occ.Name=$item[0]
    }
    foreach($x in @(9.5,41.5)) {foreach($y in @(10,30,50,70)) {
        $null=$preview.ComponentDefinition.Occurrences.Add((Join-Path $model 'Deck_M3x10_Countersunk.ipt'),(Position $x $y -24))
    }}
    $preview.Update2($false)|Out-Null;$preview.Activate()
    $camera=$app.ActiveView.Camera;$camera.Perspective=$false
    $camera.Eye=$tg.CreatePoint(8,12,-50);$camera.Target=$tg.CreatePoint(2.55,4,0)
    $camera.UpVector=$tg.CreateUnitVector(0,1,0);$camera.Fit();$camera.ApplyWithoutTransition()
    $bg=$to.CreateColor(255,255,255);$camera.SaveAsBitmap($output,1600,1350,$bg,$bg)
    $preview.Close($true);$preview=$null
    $assembly=$app.Documents.Open((Join-Path $model 'Rod_Holder_Assembly_Drop8p5.iam'),$true);$assembly.Activate()
    Write-Output 'Rendered CNC exploded view without changing source files.'
} finally {if($null -ne $preview) {$preview.Close($true)};$app.SilentOperation=$silent}
