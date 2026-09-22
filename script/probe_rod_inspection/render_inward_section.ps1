$ErrorActionPreference='Stop'
Add-Type -Path 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
$root='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB'
$temp=Join-Path $root 'script\probe_rod_inspection\tmp\inward_section'
$out=Join-Path $root 'QSTL_24DC_4MW_PCB\Mechanical_Assembly\Rod_Holder_Adapter'
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application');$tg=$app.TransientGeometry;$to=$app.TransientObjects
$silent=$app.SilentOperation
try {
    $app.SilentOperation=$true
    $review=$app.Documents.Add([Inventor.DocumentTypeEnum]::kAssemblyDocumentObject,$app.FileManager.GetTemplateFile([Inventor.DocumentTypeEnum]::kAssemblyDocumentObject),$true)
    $view=$review.ComponentDefinition.RepresentationsManager.DesignViewRepresentations.Add('Section_Review');$view.Activate();$view.Locked=$false
    foreach($item in @(@('Rods',153,85,44),@('Plate',38,120,160),@('Holder',239,147,54),@('Tube',136,146,164))) {
        $name=$item[0];$part=$app.Documents.Add([Inventor.DocumentTypeEnum]::kPartDocumentObject,$app.FileManager.GetTemplateFile([Inventor.DocumentTypeEnum]::kPartDocumentObject),$false)
        $imports=$part.ComponentDefinition.ReferenceComponents.ImportedComponents;$definition=$imports.CreateDefinition((Join-Path $temp ($name+'.step')));$definition.ReferenceModel=$false;$null=$imports.Add($definition)
        $path=Join-Path $temp ($name+'.ipt');$part.SaveAs($path,$false)
        $occ=$review.ComponentDefinition.Occurrences.Add($path,($tg.CreateMatrix()));$occ.Name=$name;$occ.Grounded=$true
        $asset=$review.Assets.Add([Inventor.AssetTypeEnum]::kAssetTypeAppearance,'Generic',$name,$name);$asset.Item('generic_diffuse').Value=$to.CreateColor($item[1],$item[2],$item[3]);$occ.Appearance=$asset
    }
    $review.Update2($false)|Out-Null;$review.SaveAs((Join-Path $temp 'Inward_section.iam'),$false)
    $review.Activate();$camera=$app.ActiveView.Camera;$camera.Perspective=$false
    $camera.Eye=$tg.CreatePoint(2.55,-60,0.3);$camera.Target=$tg.CreatePoint(2.55,17.5025,0.3);$camera.UpVector=$tg.CreateUnitVector(0,0,1)
    $camera.SetExtents(6.5,6.5);$camera.ApplyWithoutTransition();$bg=$to.CreateColor(246,248,251)
    $camera.SaveAsBitmap((Join-Path $out 'Assembly_cross_section.png'),1100,1100,$bg,$bg);$review.Save()
    $doc=$app.Documents.Open((Join-Path $out 'Rod_Holder_Assembly.iam'),$true);$doc.Activate()
    Write-Output 'Rendered inward boss between rods, with centered holder, from source CAD.'
} finally {$app.SilentOperation=$silent}
