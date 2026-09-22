$ErrorActionPreference='Stop'
$root='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB'
$mechanical=Join-Path $root 'QSTL_24DC_4MW_PCB\Mechanical_Assembly'
$out=Join-Path $mechanical 'Rod_Holder_Adapter'
$helper=Join-Path $root 'script\probe_rod_inspection'
Add-Type -Path 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application')
$app.Visible=$true;$tg=$app.TransientGeometry;$to=$app.TransientObjects
$oldSilent=$app.SilentOperation
. ([scriptblock]::Create([IO.File]::ReadAllText((Join-Path $helper 'mounting_orientation.ps1'))))

# Reuse tested native sketch helpers, not the superseded saddle geometry.
$source=[IO.File]::ReadAllText((Join-Path $helper 'build_h_frame.ps1'))
$start=$source.IndexOf('function Add-Parameter(');$end=$source.IndexOf('function Add-Bar(')
. ([scriptblock]::Create($source.Substring($start,$end-$start)))
$source=[IO.File]::ReadAllText((Join-Path $helper 'build_holder_adapter.ps1'))
$start=$source.IndexOf('function Add-RectangleFeature(');$end=$source.IndexOf('try {')
. ([scriptblock]::Create($source.Substring($start,$end-$start)))

function Add-SideHoleRow($side,$entryExpression,$extentDirection) {
    $plane=$cd.WorkPlanes.AddByPlaneAndOffset($cd.WorkPlanes.Item(1),$entryExpression)
    $plane.Name='Device_Clamp_Face_'+$side;$plane.Visible=$false
    $sketch=$cd.Sketches.Add($plane);$sketch.Name='M3_Side_Tap_Locations_'+$side
    $origin=$sketch.AddByProjectingEntity($cd.WorkAxes.Item(1))
    for ($holeIndex=0;$holeIndex -lt 5;$holeIndex++) {
        $yExpression='ClampFirstY + '+($holeIndex-2)+' * ClampPitch'
        $position=$sketch.ModelToSketchSpace($tg.CreatePoint((Length-Cm $entryExpression),(Length-Cm $yExpression),(Length-Cm 'ClampHeight')))
        $circle=$sketch.SketchCircles.AddByCenterRadius($position,((Length-Cm 'TapDrillDiameter')/2))
        # Inventor's default YZ sketch axes are local X=world Y and local Y=world Z.
        if ([Math]::Abs($position.X-(Length-Cm $yExpression)) -gt 0.00001) { throw 'Unexpected YZ sketch X axis.' }
        if ([Math]::Abs($position.Y-(Length-Cm 'ClampHeight')) -gt 0.00001) { throw 'Unexpected YZ sketch Y axis.' }
        Dimension-Point $sketch $origin $circle.CenterSketchPoint $yExpression 'ClampHeight'
        $dim=$sketch.DimensionConstraints.AddDiameter($circle,$tg.CreatePoint2d(($position.X+0.6),($position.Y+0.6)))
        $dim.Parameter.Expression='TapDrillDiameter'
    }
    $definition=$cd.Features.ExtrudeFeatures.CreateExtrudeDefinition($sketch.Profiles.AddForSolid(),[Inventor.PartFeatureOperationEnum]::kCutOperation)
    $definition.SetDistanceExtent('TapDepth',$extentDirection)
    $f=$cd.Features.ExtrudeFeatures.Add($definition);$f.Name='Device_Tap_Drills_5x_'+$side;$sketch.Visible=$false
    $cd.Document.Update2($false) | Out-Null
    $cylinders=@($cd.SurfaceBodies.Item(1).Faces | Where-Object {
        $_.SurfaceType -eq [Inventor.SurfaceTypeEnum]::kCylinderSurface -and
        [Math]::Abs($_.Geometry.Radius-(Length-Cm 'TapDrillDiameter')/2) -lt 0.000001 -and
        [Math]::Abs($_.Geometry.AxisVector.X) -gt 0.99 -and
        [Math]::Abs($_.Geometry.BasePoint.X-(Length-Cm $entryExpression)) -lt 0.000001
    })
    if ($cylinders.Count -ne 5) {throw 'Expected five device-tap cylinders on each face.'}
    $threadFeatures=$cd.Features.ThreadFeatures
    $threadInfo=$threadFeatures.CreateStandardThreadInfo($true,$true,'ISO Metric profile','M3x0.5','6H')
    $n=0
    foreach ($face in $cylinders) {
        $entry=@($face.Edges | Where-Object {
            $_.GeometryType -eq [Inventor.CurveTypeEnum]::kCircleCurve -and
            [Math]::Abs($_.Geometry.Center.X-(Length-Cm $entryExpression)) -lt 0.000001
        })
        if ($entry.Count -ne 1) {throw 'Could not identify the tap entry edge.'}
        $thread=$threadFeatures.Add($face,$entry[0],$threadInfo,$false,$false,'TapDepth','0 mm')
        $n++;$thread.Name='Device_M3x0_5_6H_'+$side+'_'+$n
    }
}

function Add-SideHoles {
    Add-SideHoleRow 'PositiveX' 'FingerStartX + FingerWidth' ([Inventor.PartFeatureExtentDirectionEnum]::kNegativeExtentDirection)
    Add-SideHoleRow 'NegativeX' 'FingerStartX' ([Inventor.PartFeatureExtentDirectionEnum]::kPositiveExtentDirection)
}

function Appearance($document,$id,$label,$r,$g,$b) {
    $asset=$document.Assets.Add([Inventor.AssetTypeEnum]::kAssetTypeAppearance,'Generic',$id,$label)
    $asset.Item('generic_diffuse').Value=$to.CreateColor($r,$g,$b);$document.ActiveAppearance=$asset
}

function Add-Cylinder($definition,$name,$z,$radius,$depth,$operation) {
    $plane=$definition.WorkPlanes.Item(3)
    if ($z -ne 0) {$plane=$definition.WorkPlanes.AddByPlaneAndOffset($plane,($z/10));$plane.Visible=$false}
    $sketch=$definition.Sketches.Add($plane)
    $null=$sketch.SketchCircles.AddByCenterRadius($tg.CreatePoint2d(0,0),($radius/10))
    $d=$definition.Features.ExtrudeFeatures.CreateExtrudeDefinition($sketch.Profiles.AddForSolid(),$operation)
    $d.SetDistanceExtent(($depth/10),[Inventor.PartFeatureExtentDirectionEnum]::kPositiveExtentDirection)
    $f=$definition.Features.ExtrudeFeatures.Add($d);$f.Name=$name;$sketch.Visible=$false
}

function Make-Screw($name,$threadMinor,$grip) {
    $s=$app.Documents.Add([Inventor.DocumentTypeEnum]::kPartDocumentObject,$app.FileManager.GetTemplateFile([Inventor.DocumentTypeEnum]::kPartDocumentObject),$true)
    $s.UnitsOfMeasure.LengthUnits=[Inventor.UnitsTypeEnum]::kMillimeterLengthUnits
    $d=$s.ComponentDefinition
    Add-Cylinder $d 'M3_Head_Envelope' -3 2.75 3 ([Inventor.PartFeatureOperationEnum]::kNewBodyOperation)
    Add-Cylinder $d 'M3_Clearance_Grip' 0 1.5 $grip ([Inventor.PartFeatureOperationEnum]::kJoinOperation)
    Add-Cylinder $d 'Thread_Core_No_Helix' $grip ($threadMinor/2) (8-$grip) ([Inventor.PartFeatureOperationEnum]::kJoinOperation)
    $sk=$d.Sketches.Add($d.WorkPlanes.AddByPlaneAndOffset($d.WorkPlanes.Item(3),-0.3))
    # Simplify the driver recess to a circular pocket.
    $null=$sk.SketchCircles.AddByCenterRadius($tg.CreatePoint2d(0,0),0.125)
    $e=$d.Features.ExtrudeFeatures.CreateExtrudeDefinition($sk.Profiles.AddForSolid(),[Inventor.PartFeatureOperationEnum]::kCutOperation)
    $e.SetDistanceExtent(0.15,[Inventor.PartFeatureExtentDirectionEnum]::kPositiveExtentDirection);$null=$d.Features.ExtrudeFeatures.Add($e);$sk.Visible=$false
    foreach($plane in $d.WorkPlanes) {$plane.Visible=$false}
    Appearance $s 'Fastener_Gray' 'Simplified fastener' 110 119 129
    $s.PropertySets.Item('Inventor Summary Information').Item('Comments').Value='Illustrative M3 x 8 socket-head fastener envelope, 5.5 mm head diameter and 3 mm head height. Threads omitted; engaged region shown at bore diameter to avoid false interference. Verify fastener specification and engagement before fabrication.'
    $s.Update2($false) | Out-Null;$s.SaveAs((Join-Path $out ($name+'.ipt')),$false)
    Export-Step $s ($name+'.step')
    return (Join-Path $out ($name+'.ipt'))
}

function Add-Occurrence($assembly,$path,$name,$matrix) {
    $o=$assembly.ComponentDefinition.Occurrences.Add($path,$matrix);$o.Name=$name;$o.Grounded=$true
    return $o
}

try {
    $app.SilentOperation=$true
    # Release only unfinished documents positively identified as this builder's output.
    foreach($unfinished in @($app.Documents)) {
        if ($unfinished.FullFileName -eq '' -and $unfinished.DocumentType -eq [Inventor.DocumentTypeEnum]::kAssemblyDocumentObject) {
            $names=@($unfinished.ComponentDefinition.Occurrences | ForEach-Object {$_.Name})
            if ($names -contains 'Solid_Plate_With_Integral_Mounting_Boss') {$unfinished.Close($true)}
        }
    }
    foreach($unfinished in @($app.Documents)) {
        if ($unfinished.FullFileName -eq '' -and $unfinished.DocumentType -eq [Inventor.DocumentTypeEnum]::kPartDocumentObject) {
            $names=@($unfinished.ComponentDefinition.Features.ExtrudeFeatures | ForEach-Object {$_.Name})
            if ($names -contains 'Continuous_Solid_Plate_No_Openings') {$unfinished.Close($true)}
        }
    }
    # Archive only this generated output set before replacing its previous geometry.
    $backup=Join-Path $helper ('tmp\adapter_before_solid_plate_'+(Get-Date -Format 'yyyyMMdd_HHmmss'))
    New-Item -ItemType Directory -Path $backup -Force | Out-Null
    Get-ChildItem -LiteralPath $out -File | ForEach-Object {Copy-Item -LiteralPath $_.FullName -Destination $backup}
    $openPaths=@($app.Documents | Where-Object {$_.FullFileName.StartsWith($out+'\')} | Sort-Object {$_.DocumentType} -Descending | ForEach-Object {$_.FullFileName})
    # Closing a parent can also release hidden children; reacquire each live document.
    foreach($path in $openPaths) {
        $live=@($app.Documents | Where-Object {$_.FullFileName -eq $path})
        if ($live.Count -gt 0) {$live[0].Close($true)}
    }

    $doc=$app.Documents.Add([Inventor.DocumentTypeEnum]::kPartDocumentObject,$app.FileManager.GetTemplateFile([Inventor.DocumentTypeEnum]::kPartDocumentObject),$true)
    $doc.UnitsOfMeasure.LengthUnits=[Inventor.UnitsTypeEnum]::kMillimeterLengthUnits;$cd=$doc.ComponentDefinition
    $parameters=@(
        @('OverallWidth','51 mm','Existing H-frame outer width.'),
        @('RodWidth','6 mm','Full width of each existing rod face.'),
        @('ContactLength','80 mm','Match the 79.43999922 mm overall device length.'),
        @('BaseThickness','4 mm','PROVISIONAL solid plate thickness; no longitudinal openings.'),
        @('FingerStartX','19.794248369169 mm','Position the reversed device centre on the plate centre plane X=25.5 mm.'),
        @('FingerWidth','13.5 mm','PROVISIONAL boss width beneath the existing holder body.'),
        @('FingerThickness','6 mm','Support finger thickness copied from the reference mechanism.'),
        @('FingerEndInset','4 mm','End setback of the raised integral boss from the solid plate.'),
        @('RodClearanceDiameter','3.4 mm','PROVISIONAL M3 clearance diameter in adapter only.'),
        @('ClampFirstY','41.82802366515844 mm','First existing slot registration, at the hanging position.'),
        @('ClampPitch','16 mm','Coldfinger-v2 lower device-mounting row centre spacing, also matching the holder slots.'),
        @('ClampHeight','7 mm','Existing slot mid-depth with the holder resting on the raised boss.'),
        @('TapDrillDiameter','2.5 mm','Coldfinger-v2 M3 x 0.5 tap drill; native cosmetic thread features carry 6H designation.'),
        @('TapDepth','6 mm','Retained thread depth; reference calls for 6 mm thread but inconsistently lists 4 mm drill.'),
        @('RodHoleStart','5 mm','Align with the existing y=140 mm rod row.'),
        @('RodScrewPitch','20 mm','Use every second existing 10 mm rod-hole row.')
    )
    foreach($p in $parameters) {$null=Add-Parameter $p[0] $p[1] $p[2]}
    $new=[Inventor.PartFeatureOperationEnum]::kNewBodyOperation;$join=[Inventor.PartFeatureOperationEnum]::kJoinOperation
    $null=Add-RectangleFeature 'Continuous_Solid_Plate_No_Openings' '0 mm' '0 mm' 'OverallWidth' 'ContactLength' '0 mm' 'BaseThickness' $new
    $null=Add-RectangleFeature 'Integral_Raised_Device_Mounting_Boss' 'FingerStartX' 'FingerEndInset' 'FingerWidth' 'ContactLength - 2 * FingerEndInset' 'BaseThickness' 'FingerThickness' $join
    $centres=@();foreach($x in @('RodWidth / 2','OverallWidth - RodWidth / 2')) {for($i=0;$i -lt 4;$i++) {$centres+= ,@($x,('RodHoleStart + '+$i+' * RodScrewPitch'))}}
    Add-Holes 'Rod_M3_Clearance_8x' $centres 'RodClearanceDiameter'
    Add-SideHoles
    Appearance $doc 'Adapter_Blue' 'New hanging adapter - material unassigned' 57 128 173
    $doc.PropertySets.Item('Inventor Summary Information').Item('Comments').Value='80 mm solid plate matching the 79.44 mm device length, with integral raised mounting boss. Both opposite boss faces have five right-hand M3 x 0.5 - 6H internal threads at 16 mm pitch, 10 total. Native cosmetic thread features; 6 mm depth per side, 1.5 mm solid web between opposed bores. Existing Top_ForFridge slots and source parts unchanged.'
    if (-not $doc.Update2($false)) {throw 'Native adapter update failed.'}
    if ($cd.SurfaceBodies.Count -ne 1) {throw 'Expected one connected adapter solid.'}
    $target=Join-Path $out 'Rod_Holder_Adapter.ipt';$doc.SaveAs($target,$false)
    Export-Step $doc 'Rod_Holder_Adapter.step'
    Save-View $doc 'Adapter_isometric.png' @(150,110,230) @(25.5,40,5) 1100 1500
    Save-View $doc 'Adapter_opposite_side.png' @(-100,110,180) @(25.5,40,5) 1100 1500
    Save-View $doc 'Adapter_top.png' @(25.5,40,220) @(25.5,40,5) 1000 1500
    $parameterReport=@($cd.Parameters.UserParameters | ForEach-Object {[pscustomobject]@{name=$_.Name;expression=$_.Expression;comment=$_.Comment}})
    $doc.Save()
    $sideScrew=Make-Screw 'Device_M3x8_Simplified' 2.5 3.039840616900513
    $rodScrew=Make-Screw 'Rod_M3x8_Simplified' 3.0 4.0

    $assembly=$app.Documents.Add([Inventor.DocumentTypeEnum]::kAssemblyDocumentObject,$app.FileManager.GetTemplateFile([Inventor.DocumentTypeEnum]::kAssemblyDocumentObject),$true)
    $framePath=Join-Path $mechanical 'Probe_H_Frame\Probe_H_Frame.ipt';$holderPath=Join-Path $mechanical 'Carrier_with_PCB.iam'
    $null=Add-Occurrence $assembly $framePath 'Existing_Probe_H_Frame' ($tg.CreateMatrix())
    $null=Add-Occurrence $assembly $target 'Solid_Plate_With_Integral_Mounting_Boss' (Matrix 0 @(0,135,6))
    $holderPosition=@(41.96412701191219,130.70466430122147,24.18839662)
    $null=Add-Occurrence $assembly $holderPath 'Existing_Carrier_Hung_From_Side_Slots' (Matrix 180 $holderPosition)
    $sideY=@(176.82802366515844,192.82802366515844)
    for($i=0;$i -lt 2;$i++) {$null=Add-Occurrence $assembly $sideScrew ('Device_Clamp_M3_'+($i+1)) (Matrix -90 @(34.245592247731516,$sideY[$i],13))}
    foreach($x in @(3,48)) {for($i=0;$i -lt 4;$i++) {$y=140+20*$i;$null=Add-Occurrence $assembly $rodScrew ('Rod_Clamp_M3_X'+$x+'_Y'+$y) (Matrix 180 @($x,$y,10))}}
    # Preserve the separately requested sleeve in subsequent adapter rebuilds.
    $tubePath=Join-Path $mechanical 'Probe_Tube\Probe_Tube.ipt'
    if (Test-Path -LiteralPath $tubePath) {
        $tubeView=$assembly.ComponentDefinition.RepresentationsManager.DesignViewRepresentations.Add('Tube_Review');$tubeView.Activate();$tubeView.Locked=$false
        $tubeMatrix=$tg.CreateMatrix();$tubeMatrix.SetToRotation((-[Math]::PI/2),$tg.CreateVector(1,0,0),$tg.CreatePoint(0,0,0))
        $tubeMatrix.SetTranslation($tg.CreateVector(2.55,0,0.3),$false)
        $tube=Add-Occurrence $assembly $tubePath 'Probe_Tube_ID51_OD54' $tubeMatrix
        $tubeAppearance=$assembly.Assets.Add([Inventor.AssetTypeEnum]::kAssetTypeAppearance,'Generic','Tube_Transparent_Review','Tube - transparent review')
        $tubeAppearance.Item('generic_diffuse').Value=$to.CreateColor(165,186,199);$tubeAppearance.Item('generic_transparency').Value=0.78
        $tube.Appearance=$tubeAppearance
    }
    Apply-ConfirmedMountingOrientation $assembly $tg
    $assembly.Update2($false) | Out-Null;$assembly.SaveAs((Join-Path $out 'Rod_Holder_Assembly.iam'),$false)
    Export-Step $assembly 'Rod_Holder_Assembly.step'
    $interior=$assembly.ComponentDefinition.RepresentationsManager.DesignViewRepresentations.Add('Interior_Review');$interior.Activate();$interior.Locked=$false
    if ($null -ne $tube) {$tube.Visible=$false}
    Save-View $assembly 'Assembly_overview.png' @(-130,265,530) @(25.5,180,3) 1100 1700
    Save-View $assembly 'Assembly_closeup.png' @(-115,245,190) @(25.5,175,3) 1200 1200 $false
    Save-View $assembly 'Assembly_side_clamp.png' @(-160,210,28) @(25.5,175,3) 1200 1200 $false
    $assembly.Save()
    [pscustomobject]@{confirmed_orientation='Plate behind rods; boss and device face inward between rods. ZIF uppermost; device centered at X=25.5 mm.';adapter_position_mm=@(0,135,-4);holder_rotation_x_deg=180;holder_translation_mm=@(9.03587298808781,222.9513830290954,14.18839662);solid_plate_mm=@(51,80,4);boss_x_min_mm=19.794248369169;boss_x_max_mm=33.294248369169;boss_width_mm=13.5;contact_length_per_rod_mm=80;contact_width_mm=6;gross_contact_area_mm2=960;side_clamp_centres_mm=@(@(16.754407752268484,176.82802366515844,3),@(16.754407752268484,160.82802366515844,3));rod_fastener_rows_y_mm=@(140,160,180,200);plate_midplane_x_mm=25.5;device_centre_x_mm=25.5;parameters=$parameterReport} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $out 'adapter_plan.json') -Encoding UTF8
    [pscustomobject]@{source_drawing='Coldfinger-v2';thread='M3x0.5';class='6H';right_hand=$true;count=10;count_per_side=5;centre_pitch_mm=16;sides=@(@{entry_x_mm=33.294248369169;axis='-X'},@{entry_x_mm=19.794248369169;axis='+X'});centre_z_mm=3;global_y_mm=@(0..4 | ForEach-Object {144.82802366515844+16*$_});thread_depth_mm=6;drill_diameter_mm=2.5;opposed_bore_web_mm=1.5;representation='Native Inventor cosmetic threads on cylindrical bores';reference_depth_discrepancy='Reference drawing lists drill depth 4 mm and thread depth 6 mm. Existing model uses 6 mm cylindrical depth; manufacturing drill allowance is to be finalized.'} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $out 'device_thread_specification.json') -Encoding UTF8
    Save-MountingPlacements $assembly $out
    $assembly.Activate();Write-Output ('Saved short hanging adapter, 10 illustrative screws and assembly in '+$out)
} finally {$app.SilentOperation=$oldSilent}
