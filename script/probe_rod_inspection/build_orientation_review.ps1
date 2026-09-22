$ErrorActionPreference='Stop'
Add-Type -Path 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
$root='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB'
$mechanical=Join-Path $root 'QSTL_24DC_4MW_PCB\Mechanical_Assembly'
$holder=Join-Path $mechanical 'Rod_Holder_Adapter'
$out=Join-Path $holder 'Orientation_Review'
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application')
$tg=$app.TransientGeometry;$to=$app.TransientObjects
$oldSilent=$app.SilentOperation
$measurements=Get-Content -LiteralPath (Join-Path $out 'orientation_measurements.json') -Raw | ConvertFrom-Json
$sourcePath=Join-Path $holder 'Rod_Holder_Assembly.iam'
$sourceHash=(Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash
$step=$app.ApplicationAddIns.ItemById('{90AF7F40-0C01-11D5-8E83-0010B541CD80}');$step.Activate()

function Multiply-Matrix($left,$right) {
    $result=$tg.CreateMatrix()
    for($i=1;$i -le 4;$i++) {for($j=1;$j -le 4;$j++) {
        $value=0.0;for($k=1;$k -le 4;$k++) {$value+=$left.Cell($i,$k)*$right.Cell($k,$j)}
        $result.Cell($i,$j)=$value
    }}
    return $result
}
function Rotation($axis,$translation) {
    $m=$tg.CreateMatrix();$m.SetToRotation([Math]::PI,$axis,$tg.CreatePoint(0,0,0))
    $m.SetTranslation($tg.CreateVector(($translation[0]/10),($translation[1]/10),($translation[2]/10)),$false)
    return $m
}
function Color-Occurrence($document,$occ,$label,$rgb,[double]$transparency=0) {
    $asset=$document.Assets.Add([Inventor.AssetTypeEnum]::kAssetTypeAppearance,'Generic',$label,$label)
    $asset.Item('generic_diffuse').Value=$to.CreateColor($rgb[0],$rgb[1],$rgb[2])
    $asset.Item('generic_transparency').Value=$transparency;$occ.Appearance=$asset
}
function Export-Step($doc,$path) {
    $ctx=$to.CreateTranslationContext();$ctx.Type=[Inventor.IOMechanismEnum]::kFileBrowseIOMechanism
    $opts=$to.CreateNameValueMap();$null=$step.HasSaveCopyAsOptions($doc,$ctx,$opts);$opts.Value('ApplicationProtocolType')=3
    $data=$to.CreateDataMedium();$data.FileName=$path;$step.SaveCopyAs($doc,$ctx,$opts,$data)
}
function Render($doc,$path,$eye,$target,$up,$extent,$width,$height) {
    $doc.Activate();$camera=$app.ActiveView.Camera;$camera.Perspective=$false
    $camera.Eye=$tg.CreatePoint(($eye[0]/10),($eye[1]/10),($eye[2]/10))
    $camera.Target=$tg.CreatePoint(($target[0]/10),($target[1]/10),($target[2]/10))
    $camera.UpVector=$tg.CreateUnitVector($up[0],$up[1],$up[2]);$camera.SetExtents(($extent[0]/10),($extent[1]/10));$camera.ApplyWithoutTransition()
    $bg=$to.CreateColor(246,248,251);$camera.SaveAsBitmap($path,$width,$height,$bg,$bg)
}
try {
    $app.SilentOperation=$true
    foreach($unfinished in @($app.Documents)) {
        if ($unfinished.FullFileName -eq '' -and $unfinished.DocumentType -eq [Inventor.DocumentTypeEnum]::kAssemblyDocumentObject) {
            $labels=@($unfinished.Assets | ForEach-Object {$_.DisplayName})
            if ($labels -contains 'Rod copper' -and $unfinished.ComponentDefinition.Occurrences.Count -eq 1) {$unfinished.Close($true)}
        }
    }
    $source=$app.Documents.Open($sourcePath,$false)
    $reverseDevice=Rotation ($tg.CreateVector(0,0,1)) $measurements.device_reverse_translation_mm
    $reversePlate=Rotation ($tg.CreateVector(0,1,0)) $measurements.plate_reverse_translation_mm
    $records=@()
    foreach($case in $measurements.cases) {
        $name=$case.name;$path=Join-Path $out ($name+'.iam')
        if (Test-Path -LiteralPath $path) {throw ('Review already exists: '+$path)}
        $review=$app.Documents.Add([Inventor.DocumentTypeEnum]::kAssemblyDocumentObject,$app.FileManager.GetTemplateFile([Inventor.DocumentTypeEnum]::kAssemblyDocumentObject),$true)
        $view=$review.ComponentDefinition.RepresentationsManager.DesignViewRepresentations.Add('Tube_Review');$view.Activate();$view.Locked=$false
        $items=@();$tube=$null
        foreach($original in $source.ComponentDefinition.Occurrences) {
            $m=$original.Transformation
            $deviceMember=$original.Name -eq 'Existing_Carrier_Hung_From_Side_Slots' -or $original.Name.StartsWith('Device_Clamp_M3_')
            $mountMember=$deviceMember -or $original.Name -eq 'Solid_Plate_With_Integral_Mounting_Boss' -or $original.Name.StartsWith('Rod_Clamp_M3_')
            if ($case.reverse_device -and $deviceMember) {$m=Multiply-Matrix $reverseDevice $m}
            if ($case.reverse_plate -and $mountMember) {$m=Multiply-Matrix $reversePlate $m}
            $occ=$review.ComponentDefinition.Occurrences.Add($original.Definition.Document.FullFileName,$m);$occ.Name=$original.Name;$occ.Grounded=$true
            if ($occ.Name -eq 'Probe_Tube_ID51_OD54') {$tube=$occ;Color-Occurrence $review $occ 'Transparent tube' @(169,182,197) 0.82}
            if ($occ.Name -eq 'Existing_Probe_H_Frame') {Color-Occurrence $review $occ 'Rod copper' @(167,91,46)}
            $matrix=@();for($i=1;$i -le 4;$i++) {$row=@();for($j=1;$j -le 4;$j++) {$row+=$m.Cell($i,$j)};$matrix+=,$row}
            $items+=[pscustomobject]@{name=$occ.Name;matrix_cm=$matrix}
        }
        $review.Update2($false)|Out-Null;$review.SaveAs($path,$false)
        Export-Step $review (Join-Path $out ($name+'.step'))
        $interior=$review.ComponentDefinition.RepresentationsManager.DesignViewRepresentations.Add('Interior_Review');$interior.Activate();$interior.Locked=$false
        $tube.Visible=$false
        $eye=@(160,255,195);$target=@(25.5,175,3)
        if ($case.reverse_plate) {$eye=@(-109,255,-189)}
        Render $review (Join-Path $out ($name+'_3D.png')) $eye $target @(0,1,0) @(120,120) 1100 1100
        $review.Save()
        $records+=[pscustomobject]@{name=$name;occurrences=$items;occurrence_count=$review.ComponentDefinition.Occurrences.Count}

        # Use real thin solids to avoid projecting distant H-frame crossbars into the section.
        $section=$app.Documents.Add([Inventor.DocumentTypeEnum]::kAssemblyDocumentObject,$app.FileManager.GetTemplateFile([Inventor.DocumentTypeEnum]::kAssemblyDocumentObject),$true)
        $sv=$section.ComponentDefinition.RepresentationsManager.DesignViewRepresentations.Add('Section_Review');$sv.Activate();$sv.Locked=$false
        foreach($item in @(@('Rods',167,91,46),@('Plate',38,120,160),@('Device',239,147,54),@('Tube',136,146,164))) {
            $partName=$item[0];$sectionDir=Join-Path $out ('Sections\'+$name)
            $part=$app.Documents.Add([Inventor.DocumentTypeEnum]::kPartDocumentObject,$app.FileManager.GetTemplateFile([Inventor.DocumentTypeEnum]::kPartDocumentObject),$false)
            $imports=$part.ComponentDefinition.ReferenceComponents.ImportedComponents;$def=$imports.CreateDefinition((Join-Path $sectionDir ($partName+'.step')));$def.ReferenceModel=$false;$null=$imports.Add($def)
            if ($part.ComponentDefinition.SurfaceBodies.Count -eq 0) {throw 'Empty section import.'}
            $partPath=Join-Path $sectionDir ($partName+'.ipt');$part.SaveAs($partPath,$false)
            $occ=$section.ComponentDefinition.Occurrences.Add($partPath,($tg.CreateMatrix()));$occ.Name=$partName;$occ.Grounded=$true
            Color-Occurrence $section $occ $partName @($item[1],$item[2],$item[3])
        }
        $section.Update2($false)|Out-Null;$section.SaveAs((Join-Path $out ($name+'_section.iam')),$false)
        Render $section (Join-Path $out ($name+'_section.png')) @(25.5,-500,3) @(25.5,181.775,3) @(0,0,1) @(65,65) 950 950
        $section.Save()
        Write-Output ('Built and rendered '+$name)
    }
    $records | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $out 'native_placements.json') -Encoding UTF8
    if ((Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash -ne $sourceHash) {throw 'Main assembly was modified by review generation.'}
    $paths=@($app.Documents | Where-Object {$_.FullFileName.StartsWith($out+'\')} | Sort-Object {$_.DocumentType} -Descending | ForEach-Object {$_.FullFileName})
    foreach($p in $paths) {$live=@($app.Documents | Where-Object {$_.FullFileName -eq $p});if ($live.Count -gt 0) {$live[0].Close($true)}}
    foreach($record in $records) {
        $check=$app.Documents.Open((Join-Path $out ($record.name+'.iam')),$false)
        if ($check.ComponentDefinition.Occurrences.Count -ne 14) {throw 'Wrong saved occurrence count.'}
        foreach($occ in $check.ComponentDefinition.Occurrences) {
            $expected=@($record.occurrences | Where-Object {$_.name -eq $occ.Name})[0]
            for($i=1;$i -le 4;$i++) {for($j=1;$j -le 4;$j++) {if ([Math]::Abs($occ.Transformation.Cell($i,$j)-$expected.matrix_cm[$i-1][$j-1]) -gt 0.0000001) {throw 'Reopened placement mismatch.'}}}
        }
    }
    [pscustomobject]@{reopened=$true;case_count=4;occurrences_per_case=14;main_assembly_unchanged=$true;main_assembly_sha256=$sourceHash} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $out 'native_verification.json') -Encoding UTF8
    $final=$app.Documents.Open((Join-Path $out 'Both_reversed.iam'),$true);$final.Activate()
} finally {$app.SilentOperation=$oldSilent}
