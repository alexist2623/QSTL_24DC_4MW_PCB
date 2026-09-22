$ErrorActionPreference='Stop'
$root='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB'
$mechanical=Join-Path $root 'QSTL_24DC_4MW_PCB\Mechanical_Assembly'
$out=Join-Path $mechanical 'Rod_Holder_Adapter'
New-Item -ItemType Directory -Path $out -Force | Out-Null
$target=Join-Path $out 'Rod_Holder_Adapter.ipt'
if (Test-Path -LiteralPath $target) { throw 'Adapter already exists; refusing to overwrite.' }
Add-Type -Path 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application')
$app.Visible=$true
$tg=$app.TransientGeometry;$to=$app.TransientObjects
$oldSilent=$app.SilentOperation
$doc=$null

# Reuse the tested dimensioning helpers without invoking the frame builder.
$source=[IO.File]::ReadAllText((Join-Path $root 'script\probe_rod_inspection\build_h_frame.ps1'))
$start=$source.IndexOf('function Add-Parameter(')
$end=$source.IndexOf('function Add-Bar(')
. ([scriptblock]::Create($source.Substring($start,$end-$start)))

function Add-RectangleFeature($name,$xExpression,$yExpression,$wExpression,$hExpression,$zExpression,$depthExpression,$operation) {
    $x=Length-Cm $xExpression;$y=Length-Cm $yExpression;$w=Length-Cm $wExpression;$h=Length-Cm $hExpression
    $plane=$cd.WorkPlanes.Item(3)
    if ([Math]::Abs((Length-Cm $zExpression)) -gt 0.000001) {
        $plane=$cd.WorkPlanes.AddByPlaneAndOffset($plane,$zExpression)
        $plane.Name=$name+'_StartPlane';$plane.Visible=$false
    }
    $sketch=$cd.Sketches.Add($plane);$sketch.Name=$name+'_Profile'
    $origin=$sketch.AddByProjectingEntity($cd.WorkAxes.Item(3))
    $lines=$sketch.SketchLines.AddAsTwoPointRectangle($tg.CreatePoint2d($x,$y),$tg.CreatePoint2d(($x+$w),($y+$h)))
    $anchor=$null;$horizontal=$null;$vertical=$null
    foreach ($line in $lines) {
        $a=$line.StartSketchPoint.Geometry;$b=$line.EndSketchPoint.Geometry
        if ([Math]::Abs($a.Y-$b.Y) -lt 0.000001) { $horizontal=$line }
        if ([Math]::Abs($a.X-$b.X) -lt 0.000001) { $vertical=$line }
        foreach ($point in @($line.StartSketchPoint,$line.EndSketchPoint)) {
            if ([Math]::Abs($point.Geometry.X-$x) -lt 0.000001 -and [Math]::Abs($point.Geometry.Y-$y) -lt 0.000001) { $anchor=$point }
        }
    }
    Dimension-Point $sketch $origin $anchor $xExpression $yExpression
    $dim=$sketch.DimensionConstraints.AddTwoPointDistance($horizontal.StartSketchPoint,$horizontal.EndSketchPoint,[Inventor.DimensionOrientationEnum]::kHorizontalDim,$tg.CreatePoint2d(($x+$w/2),($y+$h+0.5)))
    $dim.Parameter.Expression=$wExpression
    $dim=$sketch.DimensionConstraints.AddTwoPointDistance($vertical.StartSketchPoint,$vertical.EndSketchPoint,[Inventor.DimensionOrientationEnum]::kVerticalDim,$tg.CreatePoint2d(($x+$w+0.5),($y+$h/2)))
    $dim.Parameter.Expression=$hExpression
    $definition=$cd.Features.ExtrudeFeatures.CreateExtrudeDefinition($sketch.Profiles.AddForSolid(),$operation)
    $definition.SetDistanceExtent($depthExpression,[Inventor.PartFeatureExtentDirectionEnum]::kPositiveExtentDirection)
    $feature=$cd.Features.ExtrudeFeatures.Add($definition);$feature.Name=$name;$sketch.Visible=$false
    return $feature
}

function Add-Holes($name,$centres,$diameterExpression) {
    $sketch=$cd.Sketches.Add($cd.WorkPlanes.Item(3));$sketch.Name=$name+'_Locations'
    $origin=$sketch.AddByProjectingEntity($cd.WorkPoints.Item(1))
    foreach ($centre in $centres) {
        $x=Length-Cm $centre[0];$y=Length-Cm $centre[1]
        $circle=$sketch.SketchCircles.AddByCenterRadius($tg.CreatePoint2d($x,$y),((Length-Cm $diameterExpression)/2))
        Dimension-Point $sketch $origin $circle.CenterSketchPoint $centre[0] $centre[1]
        $dim=$sketch.DimensionConstraints.AddDiameter($circle,$tg.CreatePoint2d(($x+0.5),($y+0.5)))
        $dim.Parameter.Expression=$diameterExpression
    }
    $definition=$cd.Features.ExtrudeFeatures.CreateExtrudeDefinition($sketch.Profiles.AddForSolid(),[Inventor.PartFeatureOperationEnum]::kCutOperation)
    $definition.SetThroughAllExtent([Inventor.PartFeatureExtentDirectionEnum]::kPositiveExtentDirection)
    $feature=$cd.Features.ExtrudeFeatures.Add($definition);$feature.Name=$name;$sketch.Visible=$false
}

function Export-Step($document,$filename) {
    $step=$app.ApplicationAddIns.ItemById('{90AF7F40-0C01-11D5-8E83-0010B541CD80}')
    $ctx=$to.CreateTranslationContext();$ctx.Type=[Inventor.IOMechanismEnum]::kFileBrowseIOMechanism
    $opts=$to.CreateNameValueMap();$null=$step.HasSaveCopyAsOptions($document,$ctx,$opts)
    $opts.Value('ApplicationProtocolType')=3
    $data=$to.CreateDataMedium();$data.FileName=Join-Path $out $filename
    $step.SaveCopyAs($document,$ctx,$opts,$data)
}

function Matrix([double]$rotationY,$position) {
    $m=$tg.CreateMatrix()
    if ($rotationY -ne 0) { $m.SetToRotation(($rotationY*[Math]::PI/180),$tg.CreateVector(0,1,0),$tg.CreatePoint(0,0,0)) }
    $m.SetTranslation($tg.CreateVector(($position[0]/10),($position[1]/10),($position[2]/10)),$false)
    return $m
}

function Save-View($document,$filename,$eye,$target,$width,$height,$fit=$true) {
    $document.Activate();$camera=$app.ActiveView.Camera;$camera.Perspective=$false
    $camera.Eye=$tg.CreatePoint(($eye[0]/10),($eye[1]/10),($eye[2]/10))
    $camera.Target=$tg.CreatePoint(($target[0]/10),($target[1]/10),($target[2]/10))
    $camera.UpVector=$tg.CreateUnitVector(0,1,0)
    if ($fit) { $camera.Fit() } else { $camera.SetExtents(12,12) }
    $camera.ApplyWithoutTransition();$bg=$to.CreateColor(245,247,250)
    $camera.SaveAsBitmap((Join-Path $out $filename),$width,$height,$bg,$bg)
}

try {
    $app.SilentOperation=$true
    $doc=$app.Documents.Add([Inventor.DocumentTypeEnum]::kPartDocumentObject,$app.FileManager.GetTemplateFile([Inventor.DocumentTypeEnum]::kPartDocumentObject),$true)
    $doc.UnitsOfMeasure.LengthUnits=[Inventor.UnitsTypeEnum]::kMillimeterLengthUnits
    $cd=$doc.ComponentDefinition
    $parameters=@(
        @('OverallWidth','51 mm','Match the current two-rod outer envelope.'),
        @('RodCentreSpacing','45 mm','Existing rod M3 hole centre spacing.'),
        @('BaseThickness','4 mm','PROVISIONAL adapter thickness.'),
        @('CrossbeamWidthY','14 mm','PROVISIONAL width around each rod fastener row.'),
        @('RodRowSpacing','50 mm','Five existing 10 mm rod-hole pitches.'),
        @('SaddleWidth','20 mm','PROVISIONAL support width within the holder outer face.'),
        @('SaddleLength','64 mm','PROVISIONAL support length containing four existing holder holes.'),
        @('SaddleStartY','2 mm','PROVISIONAL longitudinal support extent.'),
        @('SaddleRise','6.5 mm','Clear the existing 6 mm holder rail with room for a pocket floor.'),
        @('PocketClearance','0.25 mm','PROVISIONAL clearance on each rail side and below its tip.'),
        @('HolderRegistrationX','41.96412701191219 mm','X translation after a 180 degree Y rotation of the existing carrier.'),
        @('HolderDatumY','22.85 mm','Existing near mounting row in Top_ForFridge source coordinates.'),
        @('HolderFarRowY','76.7 mm','Existing far mounting row in Top_ForFridge source coordinates.'),
        @('RailSourceXMin','7.718534764180674 mm','Measured on the existing Top_ForFridge solid.'),
        @('RailSourceXMax','10.758375381081185 mm','Measured on the existing Top_ForFridge solid.'),
        @('RailSourceYMin','27.67983355175837 mm','Measured on the existing Top_ForFridge solid.'),
        @('RailSourceYMax','71.56835936393684 mm','Measured on the existing Top_ForFridge solid.'),
        @('RailHeight','6 mm','Measured exterior rail height.'),
        @('RodClearanceDiameter','3.4 mm','PROVISIONAL clearance holes aligned to existing M3 rod holes.'),
        @('HolderClearanceDiameter','2.8 mm','PROVISIONAL clearance over existing 2.5 mm holder bores; thread/fastener specification is unconfirmed.')
    )
    foreach ($p in $parameters) { $null=Add-Parameter $p[0] $p[1] $p[2] }
    $join=[Inventor.PartFeatureOperationEnum]::kJoinOperation
    $new=[Inventor.PartFeatureOperationEnum]::kNewBodyOperation
    $cut=[Inventor.PartFeatureOperationEnum]::kCutOperation
    $null=Add-RectangleFeature 'Central_Base' '(OverallWidth - SaddleWidth) / 2' 'SaddleStartY' 'SaddleWidth' 'SaddleLength' '0 mm' 'BaseThickness' $new
    $null=Add-RectangleFeature 'Near_Rod_Crossbeam' '0 mm' '0 mm' 'OverallWidth' 'CrossbeamWidthY' '0 mm' 'BaseThickness' $join
    $null=Add-RectangleFeature 'Far_Rod_Crossbeam' '0 mm' 'RodRowSpacing' 'OverallWidth' 'CrossbeamWidthY' '0 mm' 'BaseThickness' $join
    $null=Add-RectangleFeature 'Raised_Holder_Saddle' '(OverallWidth - SaddleWidth) / 2' 'SaddleStartY' 'SaddleWidth' 'SaddleLength' 'BaseThickness' 'SaddleRise' $join
    $null=Add-RectangleFeature 'Existing_Holder_Rail_Clearance' 'HolderRegistrationX - RailSourceXMax - PocketClearance' 'RailSourceYMin - HolderDatumY + CrossbeamWidthY / 2 - PocketClearance' 'RailSourceXMax - RailSourceXMin + 2 * PocketClearance' 'RailSourceYMax - RailSourceYMin + 2 * PocketClearance' 'BaseThickness + SaddleRise - RailHeight - PocketClearance' 'RailHeight + PocketClearance' $cut
    Add-Holes 'Rod_M3_Clearance_4x' @(
        @('(OverallWidth - RodCentreSpacing) / 2','CrossbeamWidthY / 2'),
        @('(OverallWidth + RodCentreSpacing) / 2','CrossbeamWidthY / 2'),
        @('(OverallWidth - RodCentreSpacing) / 2','CrossbeamWidthY / 2 + RodRowSpacing'),
        @('(OverallWidth + RodCentreSpacing) / 2','CrossbeamWidthY / 2 + RodRowSpacing')
    ) 'RodClearanceDiameter'
    Add-Holes 'Existing_Holder_Pattern_4x' @(
        @('HolderRegistrationX - 10 mm','CrossbeamWidthY / 2'),
        @('HolderRegistrationX - 22.65 mm','CrossbeamWidthY / 2'),
        @('HolderRegistrationX - 9 mm','HolderFarRowY - HolderDatumY + CrossbeamWidthY / 2'),
        @('HolderRegistrationX - 23.65 mm','HolderFarRowY - HolderDatumY + CrossbeamWidthY / 2')
    ) 'HolderClearanceDiameter'
    $appearance=$doc.Assets.Add([Inventor.AssetTypeEnum]::kAssetTypeAppearance,'Generic','Adapter_Blue','Adapter - material unspecified')
    $appearance.Item('generic_diffuse').Value=$to.CreateColor(61,128,173);$doc.ActiveAppearance=$appearance
    $doc.PropertySets.Item('Inventor Summary Information').Item('Comments').Value='Rod-to-holder adapter concept. Fits the existing Top_ForFridge exterior and hole centres. Provisional thicknesses, pocket clearance and fastener clearance diameters; no new holes in source parts. Fasteners and material remain unspecified.'
    if (-not $doc.Update2($false)) { throw 'Adapter update failed.' }
    if ($cd.SurfaceBodies.Count -ne 1) { throw 'Expected one connected adapter solid.' }
    $doc.SaveAs($target,$false)
    Export-Step $doc 'Rod_Holder_Adapter.step'
    Save-View $doc 'Adapter_isometric.png' @(115,100,125) @(25.5,33,5) 1300 1000
    Save-View $doc 'Adapter_top.png' @(25.5,33,150) @(25.5,33,5) 1000 1200
    $doc.Save()

    $assembly=$app.Documents.Add([Inventor.DocumentTypeEnum]::kAssemblyDocumentObject,$app.FileManager.GetTemplateFile([Inventor.DocumentTypeEnum]::kAssemblyDocumentObject),$true)
    $framePath=Join-Path $mechanical 'Probe_H_Frame\Probe_H_Frame.ipt'
    $holderPath=Join-Path $mechanical 'Carrier_with_PCB.iam'
    $frame=$assembly.ComponentDefinition.Occurrences.Add($framePath,($tg.CreateMatrix()));$frame.Name='Probe_H_Frame';$frame.Grounded=$true
    $adapterPosition=@(0,143,6)
    $adapter=$assembly.ComponentDefinition.Occurrences.Add($target,(Matrix 0 $adapterPosition));$adapter.Name='New_Rod_Holder_Adapter';$adapter.Grounded=$true
    $holderPosition=@(41.96412701191219,127.15,24.68839662)
    $holder=$assembly.ComponentDefinition.Occurrences.Add($holderPath,(Matrix 180 $holderPosition));$holder.Name='Existing_Carrier_PCB_SMP_Away_From_Rods';$holder.Grounded=$true
    $assembly.Update2($false) | Out-Null
    $assembly.SaveAs((Join-Path $out 'Rod_Holder_Assembly.iam'),$false)
    Export-Step $assembly 'Rod_Holder_Assembly.step'
    Save-View $assembly 'Assembly_overview.png' @(190,260,500) @(25.5,180,10) 1000 1600
    Save-View $assembly 'Assembly_closeup.png' @(145,235,240) @(25.5,176,14) 1300 1100 $false
    $assembly.Save()

    $review=$app.Documents.Add([Inventor.DocumentTypeEnum]::kAssemblyDocumentObject,$app.FileManager.GetTemplateFile([Inventor.DocumentTypeEnum]::kAssemblyDocumentObject),$true)
    $r=$review.ComponentDefinition.Occurrences.Add($framePath,($tg.CreateMatrix()));$r.Name='Probe_H_Frame';$r.Grounded=$true
    $r=$review.ComponentDefinition.Occurrences.Add($target,(Matrix 0 @(0,143,20)));$r.Name='Adapter_Exploded_14mm';$r.Grounded=$true
    $r=$review.ComponentDefinition.Occurrences.Add($holderPath,(Matrix 180 @(41.96412701191219,127.15,65.68839662)));$r.Name='Carrier_Exploded_41mm';$r.Grounded=$true
    $review.Update2($false) | Out-Null
    $review.SaveAs((Join-Path $out 'Rod_Holder_Exploded.iam'),$false)
    Save-View $review 'Assembly_exploded_closeup.png' @(160,215,245) @(25.5,176,34) 1400 1200 $false
    $review.Save()
    $plan=[pscustomobject]@{adapter_position_mm=$adapterPosition;holder_rotation_y_deg=180;holder_translation_mm=$holderPosition;rod_fastener_rows_y_mm=@(150,200);rod_face_z_mm=6;holder_contact_z_mm=16.5;source_frame=$framePath;source_holder_assembly=$holderPath;parameters=@($cd.Parameters.UserParameters | ForEach-Object { [pscustomobject]@{name=$_.Name;expression=$_.Expression;comment=$_.Comment} })}
    $plan | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $out 'adapter_plan.json') -Encoding UTF8
    $assembly.Activate()
    Write-Output ('Saved adapter and rod/holder assemblies in '+$out)
} catch {
    if ($null -ne $doc -and -not (Test-Path -LiteralPath $target)) { $doc.Close($true) }
    throw
} finally { $app.SilentOperation=$oldSilent }
