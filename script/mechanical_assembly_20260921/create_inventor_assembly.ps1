$ErrorActionPreference = 'Stop'
$root = 'C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB'
$out = Join-Path $root 'QSTL_24DC_4MW_PCB\Mechanical_Assembly'
$fit = Get-Content -LiteralPath (Join-Path $out 'assembly_validation.json') -Raw | ConvertFrom-Json
Add-Type -Path 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
$app = [Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application')
$tg = $app.TransientGeometry
$to = $app.TransientObjects
$oldSilent = $app.SilentOperation
$step = $app.ApplicationAddIns.ItemById('{90AF7F40-0C01-11D5-8E83-0010B541CD80}')

function Export-Step($doc, $filename) {
    $ctx=$to.CreateTranslationContext(); $ctx.Type=[Inventor.IOMechanismEnum]::kFileBrowseIOMechanism
    $opts=$to.CreateNameValueMap(); $null=$step.HasSaveCopyAsOptions($doc,$ctx,$opts)
    $opts.Value('ApplicationProtocolType')=3
    $data=$to.CreateDataMedium(); $data.FileName=$filename
    $step.SaveCopyAs($doc,$ctx,$opts,$data)
}

function New-Assembly($path) {
    if (Test-Path -LiteralPath $path) { throw ('Assembly already exists: '+$path) }
    $doc=$app.Documents.Add([Inventor.DocumentTypeEnum]::kAssemblyDocumentObject,$app.FileManager.GetTemplateFile([Inventor.DocumentTypeEnum]::kAssemblyDocumentObject),$true)
    $doc.SaveAs($path,$false)
    return $doc
}

function Import-Part($source, $path, $color) {
    if (Test-Path -LiteralPath $path) { return $app.Documents.Open($path,$false) }
    $doc=$app.Documents.Add([Inventor.DocumentTypeEnum]::kPartDocumentObject,$app.FileManager.GetTemplateFile([Inventor.DocumentTypeEnum]::kPartDocumentObject),$false)
    $imports=$doc.ComponentDefinition.ReferenceComponents.ImportedComponents
    $def=$imports.CreateDefinition($source); $def.ReferenceModel=$false
    $null=$imports.Add($def)
    if ($doc.ComponentDefinition.SurfaceBodies.Count -lt 1) { throw ('No solids: '+$source) }
    $asset=$doc.Assets.Add([Inventor.AssetTypeEnum]::kAssetTypeAppearance,'Generic','MechanicalColor','Mechanical Color')
    $asset.Item('generic_diffuse').Value=$to.CreateColor([int]$color[0],[int]$color[1],[int]$color[2])
    $doc.ActiveAppearance=$asset
    $doc.SaveAs($path,$false)
    return $doc
}

function Matrix($rotationY, $position) {
    $m=$tg.CreateMatrix()
    if ($rotationY -ne 0) { $m.SetToRotation(($rotationY*[Math]::PI/180),$tg.CreateVector(0,1,0),$tg.CreatePoint(0,0,0)) }
    $m.SetTranslation($tg.CreateVector(($position[0]/10),($position[1]/10),($position[2]/10)),$false)
    return $m
}

function Save-View($doc,$name,$eye,$target,$up) {
    $doc.Activate()
    $camera=$app.ActiveView.Camera
    $camera.Perspective=$false
    $camera.Eye=$tg.CreatePoint(($eye[0]/10),($eye[1]/10),($eye[2]/10))
    $camera.Target=$tg.CreatePoint(($target[0]/10),($target[1]/10),($target[2]/10))
    $camera.UpVector=$tg.CreateUnitVector($up[0],$up[1],$up[2])
    $camera.Fit();$camera.ApplyWithoutTransition()
    $bg=$to.CreateColor(245,247,250)
    $camera.SaveAsBitmap((Join-Path $out ($name+'.png')),1400,1000,$bg,$bg)
}

try {
    $app.SilentOperation=$true
    $pcb=New-Assembly (Join-Path $out 'PCB_simplified.iam')
    foreach ($item in $fit.pcb_items) {
        $source=Join-Path $out $item.path
        $path=[IO.Path]::ChangeExtension($source,'.ipt')
        $part=Import-Part $source $path $item.color
        $occ=$pcb.ComponentDefinition.Occurrences.Add($path,($tg.CreateMatrix()))
        $occ.Name=$item.name; $occ.Grounded=$true
        Write-Output ('PCB component: '+$item.name)
    }
    $pcb.Update2($true) | Out-Null
    $pcb.Save()
    Export-Step $pcb (Join-Path $out 'PCB_simplified.step')
    Save-View $pcb 'PCB_SMP_side' @(85,100,105) @(9.75,34,0) @(0,1,0)
    Save-View $pcb 'PCB_QD_side' @(-60,80,-105) @(9.75,34,0) @(0,1,0)

    $bottom=Import-Part (Join-Path $out 'Bottom_reference.step') (Join-Path $out 'Bottom.ipt') @(185,191,198)
    $top=Import-Part (Join-Path $out 'Top_ForFridge_reference.step') (Join-Path $out 'Top_ForFridge.ipt') @(156,163,172)
    $assy=New-Assembly (Join-Path $out 'Carrier_with_PCB.iam')
    $bocc=$assy.ComponentDefinition.Occurrences.Add($bottom.FullFileName,($tg.CreateMatrix()));$bocc.Name='Bottom - SMP side';$bocc.Grounded=$true
    $pocc=$assy.ComponentDefinition.Occurrences.Add($pcb.FullFileName,(Matrix $fit.pcb_transform.rot_y_deg $fit.pcb_transform.translation_mm));$pocc.Name='Current PCB - simplified';$pocc.Grounded=$true
    $tocc=$assy.ComponentDefinition.Occurrences.Add($top.FullFileName,(Matrix 0 $fit.top_transform.translation_mm));$tocc.Name='Top_ForFridge - QD side';$tocc.Grounded=$true
    $assy.Update2($true) | Out-Null
    Save-View $assy 'Assembly_closed' @(95,105,100) @(16.3,44,4) @(0,1,0)
    $assy.Save()
    Export-Step $assy (Join-Path $out 'Carrier_with_PCB.step')

    # Store a second native assembly so the exploded view is immediately reviewable.
    $exploded=New-Assembly (Join-Path $out 'Carrier_exploded.iam')
    $be=$exploded.ComponentDefinition.Occurrences.Add($bottom.FullFileName,(Matrix 0 @(0,0,-20)));$be.Name='Bottom - SMP side';$be.Grounded=$true
    $pe=$exploded.ComponentDefinition.Occurrences.Add($pcb.FullFileName,(Matrix $fit.pcb_transform.rot_y_deg $fit.pcb_transform.translation_mm));$pe.Name='Current PCB - simplified';$pe.Grounded=$true
    $topExploded=@($fit.top_transform.translation_mm[0],$fit.top_transform.translation_mm[1],($fit.top_transform.translation_mm[2]+30))
    $te=$exploded.ComponentDefinition.Occurrences.Add($top.FullFileName,(Matrix 0 $topExploded));$te.Name='Top_ForFridge - QD side';$te.Grounded=$true
    $exploded.Update2($true) | Out-Null
    Save-View $exploded 'Assembly_exploded' @(110,85,95) @(16.3,44,4) @(0,1,0)
    $exploded.Save()
    $assy.Activate();$app.ActiveView.Fit()
    $summary=[pscustomobject]@{pcb_occurrences=$pcb.ComponentDefinition.Occurrences.Count;assembly_occurrences=$assy.ComponentDefinition.Occurrences.Count;all_documents_saved=$true}
    $summary | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $out 'inventor_build.json') -Encoding UTF8
    Write-Output ($summary | ConvertTo-Json)
} finally { $app.SilentOperation=$oldSilent }
