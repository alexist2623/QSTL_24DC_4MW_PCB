$ErrorActionPreference='Stop'
$root='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB'
$mechanical=Join-Path $root 'QSTL_24DC_4MW_PCB\Mechanical_Assembly'
$out=Join-Path $mechanical 'Probe_Tube'
$holderOut=Join-Path $mechanical 'Rod_Holder_Adapter'
$helper=Join-Path $root 'script\probe_rod_inspection'
New-Item -ItemType Directory -Path $out -Force | Out-Null
$target=Join-Path $out 'Probe_Tube.ipt'
if (Test-Path -LiteralPath $target) {throw 'Tube already exists; update its native parameters instead of rebuilding.'}
Add-Type -Path 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application')
$tg=$app.TransientGeometry;$to=$app.TransientObjects;$oldSilent=$app.SilentOperation
$source=[IO.File]::ReadAllText((Join-Path $helper 'build_h_frame.ps1'))
$start=$source.IndexOf('function Add-Parameter(');$end=$source.IndexOf('function Add-Bar(')
. ([scriptblock]::Create($source.Substring($start,$end-$start)))

function Export-Step($document,$path) {
    $step=$app.ApplicationAddIns.ItemById('{90AF7F40-0C01-11D5-8E83-0010B541CD80}')
    $ctx=$to.CreateTranslationContext();$ctx.Type=[Inventor.IOMechanismEnum]::kFileBrowseIOMechanism
    $opts=$to.CreateNameValueMap();$null=$step.HasSaveCopyAsOptions($document,$ctx,$opts);$opts.Value('ApplicationProtocolType')=3
    $data=$to.CreateDataMedium();$data.FileName=$path;$step.SaveCopyAs($document,$ctx,$opts,$data)
}

function Render($document,$path,$eye,$targetPoint,$up,$width,$height,$fit=$true) {
    $document.Activate();$camera=$app.ActiveView.Camera;$camera.Perspective=$false
    $camera.Eye=$tg.CreatePoint(($eye[0]/10),($eye[1]/10),($eye[2]/10));$camera.Target=$tg.CreatePoint(($targetPoint[0]/10),($targetPoint[1]/10),($targetPoint[2]/10))
    $camera.UpVector=$tg.CreateUnitVector($up[0],$up[1],$up[2])
    if ($fit) {$camera.Fit()} else {$camera.SetExtents(7,7)}
    $camera.ApplyWithoutTransition();$bg=$to.CreateColor(245,247,250)
    $camera.SaveAsBitmap($path,$width,$height,$bg,$bg)
}

try {
    $app.SilentOperation=$true
    $doc=$app.Documents.Add([Inventor.DocumentTypeEnum]::kPartDocumentObject,$app.FileManager.GetTemplateFile([Inventor.DocumentTypeEnum]::kPartDocumentObject),$true)
    $doc.UnitsOfMeasure.LengthUnits=[Inventor.UnitsTypeEnum]::kMillimeterLengthUnits;$cd=$doc.ComponentDefinition
    $null=Add-Parameter 'InnerDiameter' '51 mm' 'User-specified inner diameter.'
    $null=Add-Parameter 'OuterDiameter' '54 mm' 'User-specified outer diameter.'
    $null=Add-Parameter 'TubeLength' '360 mm' 'Assumed to match the current rod length; editable.'
    $null=Add-Parameter 'WallThickness' '(OuterDiameter - InnerDiameter) / 2' 'Derived radial wall thickness.'
    $sketch=$cd.Sketches.Add($cd.WorkPlanes.Item(3));$sketch.Name='Concentric_Tube_Section'
    $origin=$sketch.AddByProjectingEntity($cd.WorkPoints.Item(1))
    foreach($name in @('OuterDiameter','InnerDiameter')) {
        $circle=$sketch.SketchCircles.AddByCenterRadius($tg.CreatePoint2d(0,0),((Length-Cm $name)/2))
        $null=$sketch.GeometricConstraints.AddCoincident($circle.CenterSketchPoint,$origin)
        $dim=$sketch.DimensionConstraints.AddDiameter($circle,$tg.CreatePoint2d(3,3));$dim.Parameter.Expression=$name
    }
    $definition=$cd.Features.ExtrudeFeatures.CreateExtrudeDefinition($sketch.Profiles.AddForSolid(),[Inventor.PartFeatureOperationEnum]::kNewBodyOperation)
    $definition.SetDistanceExtent('TubeLength',[Inventor.PartFeatureExtentDirectionEnum]::kPositiveExtentDirection)
    $feature=$cd.Features.ExtrudeFeatures.Add($definition);$feature.Name='Open_Ended_Cylindrical_Sleeve';$sketch.Visible=$false
    $asset=$doc.Assets.Add([Inventor.AssetTypeEnum]::kAssetTypeAppearance,'Generic','Sleeve_Gray','Sleeve - material unspecified')
    $asset.Item('generic_diffuse').Value=$to.CreateColor(152,168,181);$doc.ActiveAppearance=$asset
    $doc.PropertySets.Item('Inventor Summary Information').Item('Comments').Value='Open-ended tube, ID 51 mm, OD 54 mm, length 360 mm. Part local axis is Z. In assembly the axis is Y through X=25.5 mm, Z=3 mm, the midpoint of the H-frame rod centre lines. Length matches rods by assumption. Requested dimensions retained even where existing geometry intersects.'
    if (-not $doc.Update2($false) -or $cd.SurfaceBodies.Count -ne 1) {throw 'Tube solid creation failed.'}
    $doc.SaveAs($target,$false);Export-Step $doc (Join-Path $out 'Probe_Tube.step')
    Render $doc (Join-Path $out 'Tube_isometric.png') @(160,-200,420) @(0,0,180) @(0,0,1) 1000 1600
    Render $doc (Join-Path $out 'Tube_end.png') @(0,0,500) @(0,0,180) @(0,1,0) 1000 1000
    $doc.Save()

    $assemblyPath=Join-Path $holderOut 'Rod_Holder_Assembly.iam'
    $backup=Join-Path $helper ('tmp\before_tube_'+(Get-Date -Format 'yyyyMMdd_HHmmss'))
    New-Item -ItemType Directory -Path $backup -Force | Out-Null
    Copy-Item -LiteralPath $assemblyPath -Destination $backup
    $assembly=$app.Documents.Open($assemblyPath,$true)
    $reviewView=$assembly.ComponentDefinition.RepresentationsManager.DesignViewRepresentations.Add('Tube_Review')
    $reviewView.Activate();$reviewView.Locked=$false
    if (@($assembly.ComponentDefinition.Occurrences | Where-Object {$_.Name -eq 'Probe_Tube_ID51_OD54'}).Count -ne 0) {throw 'Tube occurrence already exists.'}
    $matrix=$tg.CreateMatrix();$matrix.SetToRotation((-[Math]::PI/2),$tg.CreateVector(1,0,0),$tg.CreatePoint(0,0,0))
    $matrix.SetTranslation($tg.CreateVector(2.55,0,0.3),$false)
    $tube=$assembly.ComponentDefinition.Occurrences.Add($target,$matrix);$tube.Name='Probe_Tube_ID51_OD54';$tube.Grounded=$true
    $transparent=$assembly.Assets.Add([Inventor.AssetTypeEnum]::kAssetTypeAppearance,'Generic','Tube_Transparent_Review','Tube - transparent review')
    $transparent.Item('generic_diffuse').Value=$to.CreateColor(165,186,199)
    $transparent.Item('generic_transparency').Value=0.78
    $tube.Appearance=$transparent
    $assembly.Update2($false) | Out-Null;$assembly.Save();Export-Step $assembly (Join-Path $holderOut 'Rod_Holder_Assembly.step')
    Render $assembly (Join-Path $out 'Assembly_with_tube.png') @(195,285,525) @(25.5,180,3) @(0,1,0) 1100 1700
    Render $assembly (Join-Path $out 'Assembly_tube_end.png') @(25.5,650,3) @(25.5,180,3) @(0,0,1) 1300 1300 $false
    $assembly.Save()
    [pscustomobject]@{inner_diameter_mm=51;outer_diameter_mm=54;wall_thickness_mm=1.5;length_mm=360;length_basis='Assumed equal to the current rods';rod_centres_xz_mm=@(@(3,3),@(48,3));axis_point_mm=@(25.5,0,3);axis_direction=@(0,1,0);extent_y_mm=@(0,360);part_rotation_x_deg=-90;part_translation_mm=@(25.5,0,3);assembly=$assemblyPath;appearance='Transparent occurrence override for inspection; geometry is a solid annular wall'} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $out 'tube_plan.json') -Encoding UTF8
    $assembly.Activate();Write-Output 'Created sleeve and added it to the current rod/holder assembly.'
} finally {$app.SilentOperation=$oldSilent}
