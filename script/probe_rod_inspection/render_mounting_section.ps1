$ErrorActionPreference='Stop'
Add-Type -Path 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
$root='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB'
$temp=Join-Path $root 'script\probe_rod_inspection\tmp\mounting_section'
$out=Join-Path $root 'QSTL_24DC_4MW_PCB\Mechanical_Assembly\Rod_Holder_Adapter'
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application');$tg=$app.TransientGeometry;$to=$app.TransientObjects
$silent=$app.SilentOperation
try {
    $app.SilentOperation=$true
    $review=$app.Documents.Add([Inventor.DocumentTypeEnum]::kAssemblyDocumentObject,$app.FileManager.GetTemplateFile([Inventor.DocumentTypeEnum]::kAssemblyDocumentObject),$true)
    foreach($item in @(@('Rods',124,35,18),@('Plate_and_boss',26,96,123),@('Original_holder',235,112,38))) {
        $name=$item[0]
        $doc=$app.Documents.Add([Inventor.DocumentTypeEnum]::kPartDocumentObject,$app.FileManager.GetTemplateFile([Inventor.DocumentTypeEnum]::kPartDocumentObject),$false)
        $imports=$doc.ComponentDefinition.ReferenceComponents.ImportedComponents;$definition=$imports.CreateDefinition((Join-Path $temp ($name+'.step')));$definition.ReferenceModel=$true
        $null=$imports.Add($definition)
        if ($doc.ComponentDefinition.SurfaceBodies.Count -eq 0) {throw ('Empty section: '+$name)}
        $path=Join-Path $temp ($name+'.ipt');$doc.SaveAs($path,$false)
        $occ=$review.ComponentDefinition.Occurrences.Add($path,($tg.CreateMatrix()));$occ.Name=$name;$occ.Grounded=$true
        $asset=$review.Assets.Add([Inventor.AssetTypeEnum]::kAssetTypeAppearance,'Generic',$name,$name)
        $asset.Item('generic_diffuse').Value=$to.CreateColor($item[1],$item[2],$item[3]);$occ.Appearance=$asset
    }
    $review.Update2($false) | Out-Null;$review.SaveAs((Join-Path $temp 'True_mounting_section.iam'),$false)
    $review.Activate();$camera=$app.ActiveView.Camera;$camera.Perspective=$false
    $camera.Eye=$tg.CreatePoint(2.55,60,1.25);$camera.Target=$tg.CreatePoint(2.55,18.1775,1.25);$camera.UpVector=$tg.CreateUnitVector(0,0,1)
    $camera.SetExtents(6.4,3.2);$camera.ApplyWithoutTransition();$bg=$to.CreateColor(255,255,255)
    $camera.SaveAsBitmap((Join-Path $out 'PPT_section_comparison.png'),1600,800,$bg,$bg);$review.Save()
    $final=$app.Documents.Open((Join-Path $out 'Rod_Holder_Assembly.iam'),$true);$final.Activate()
    Write-Output 'Rendered true saved-CAD section matching the PPT viewing direction.'
} finally {$app.SilentOperation=$silent}
