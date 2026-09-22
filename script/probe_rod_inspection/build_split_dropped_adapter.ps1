$ErrorActionPreference='Stop'
$root='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB'
$mechanical=Join-Path $root 'QSTL_24DC_4MW_PCB\Mechanical_Assembly'
$baseline=Join-Path $mechanical 'Rod_Holder_Adapter'
$out=Join-Path $mechanical 'Rod_Holder_Adapter_Drop8p5'
$helper=Join-Path $root 'script\probe_rod_inspection'
$assemblyPath=Join-Path $out 'Rod_Holder_Assembly_Drop8p5.iam'
if (Test-Path -LiteralPath (Join-Path $out 'Centre_Plate.ipt')) {throw 'The split variant already exists; refusing to overwrite it.'}
Add-Type -Path 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application')
$app.Visible=$true;$tg=$app.TransientGeometry;$to=$app.TransientObjects;$oldSilent=$app.SilentOperation
$source=[IO.File]::ReadAllText((Join-Path $helper 'build_h_frame.ps1'))
$start=$source.IndexOf('function Add-Parameter(');$end=$source.IndexOf('function Add-Bar(')
. ([scriptblock]::Create($source.Substring($start,$end-$start)))
$source=[IO.File]::ReadAllText((Join-Path $helper 'build_holder_adapter.ps1'))
$start=$source.IndexOf('function Add-RectangleFeature(');$end=$source.IndexOf('try {')
. ([scriptblock]::Create($source.Substring($start,$end-$start)))
$source=[IO.File]::ReadAllText((Join-Path $helper 'build_hanging_adapter.ps1'))
$start=$source.IndexOf('function Add-SideHoleRow(');$end=$source.IndexOf('function Make-Screw(')
. ([scriptblock]::Create($source.Substring($start,$end-$start)))
. ([scriptblock]::Create([IO.File]::ReadAllText((Join-Path $helper 'mounting_orientation.ps1'))))
function Matrix-Rows($m) {
    $rows=@();for($i=1;$i -le 4;$i++) {$row=@();for($j=1;$j -le 4;$j++) {$row+=$m.Cell($i,$j)};$rows+=,$row};return ,$rows
}
function Matrix-FromRows($rows) {
    $m=$tg.CreateMatrix();for($i=1;$i -le 4;$i++) {for($j=1;$j -le 4;$j++) {$m.Cell($i,$j)=[double]$rows[$i-1][$j-1]}};return $m
}
function Add-SupportThreads($xExpression) {
    $plane=$cd.WorkPlanes.AddByPlaneAndOffset($cd.WorkPlanes.Item(3),'BaseThickness');$plane.Visible=$false
    $sk=$cd.Sketches.Add($plane);$sk.Name='Deck_Assembly_M3_Locations'
    $origin=$sk.AddByProjectingEntity($cd.WorkAxes.Item(3))
    for($i=0;$i -lt 4;$i++) {
        $yExpression='JoinFirstY + '+$i+' * JoinPitch'
        $circle=$sk.SketchCircles.AddByCenterRadius($tg.CreatePoint2d((Length-Cm $xExpression),(Length-Cm $yExpression)),(Length-Cm 'TapDrillDiameter')/2)
        Dimension-Point $sk $origin $circle.CenterSketchPoint $xExpression $yExpression
        $dim=$sk.DimensionConstraints.AddDiameter($circle,$tg.CreatePoint2d((Length-Cm $xExpression)+.4,(Length-Cm $yExpression)+.4));$dim.Parameter.Expression='TapDrillDiameter'
    }
    $ed=$cd.Features.ExtrudeFeatures.CreateExtrudeDefinition($sk.Profiles.AddForSolid(),[Inventor.PartFeatureOperationEnum]::kCutOperation)
    $ed.SetDistanceExtent('JoinThreadDepth',[Inventor.PartFeatureExtentDirectionEnum]::kPositiveExtentDirection)
    $feature=$cd.Features.ExtrudeFeatures.Add($ed);$feature.Name='Four_Blind_M3_Tap_Bores';$sk.Visible=$false
    $cd.Document.Update2($false) | Out-Null
    $faces=@($cd.SurfaceBodies.Item(1).Faces | Where-Object {
        $_.SurfaceType -eq [Inventor.SurfaceTypeEnum]::kCylinderSurface -and
        [Math]::Abs($_.Geometry.AxisVector.Z) -gt .99 -and
        [Math]::Abs($_.Geometry.Radius-.125) -lt .000001 -and
        [Math]::Abs($_.Geometry.BasePoint.Z-(Length-Cm 'BaseThickness')) -lt .000001
    })
    if ($faces.Count -ne 4) {throw 'Expected four axial support tap bores.'}
    $tf=$cd.Features.ThreadFeatures;$info=$tf.CreateStandardThreadInfo($true,$true,'ISO Metric profile','M3x0.5','6H')
    $i=0;foreach($face in $faces) {
        $edges=@($face.Edges | Where-Object {$_.GeometryType -eq [Inventor.CurveTypeEnum]::kCircleCurve -and [Math]::Abs($_.Geometry.Center.Z-(Length-Cm 'BaseThickness')) -lt .000001})
        if ($edges.Count -ne 1) {throw 'Cannot identify support thread entry.'}
        $t=$tf.Add($face,$edges[0],$info,$false,$false,'JoinThreadDepth','0 mm');$i++;$t.Name='Deck_M3x0_5_6H_'+$i
    }
}
function Add-DeckCountersinks {
    $sk=$cd.Sketches.Add($cd.WorkPlanes.Item(3));$sk.Name='Eight_Deck_Countersink_Locations'
    $origin=$sk.AddByProjectingEntity($cd.WorkPoints.Item(1));$points=$to.CreateObjectCollection()
    foreach($xExpression in @('JoinLeftX','OverallWidth - JoinLeftX')) {for($i=0;$i -lt 4;$i++) {
        $yExpression='JoinFirstY + '+$i+' * JoinPitch'
        $p=$sk.SketchPoints.Add($tg.CreatePoint2d((Length-Cm $xExpression),(Length-Cm $yExpression)),$true)
        Dimension-Point $sk $origin $p $xExpression $yExpression;$points.Add($p)
    }}
    $holes=$cd.Features.HoleFeatures;$placement=$holes.CreateSketchPlacementDefinition($points)
    $feature=$holes.AddCSinkByThroughAllExtent($placement,'RodClearanceDiameter',[Inventor.PartFeatureExtentDirectionEnum]::kNegativeExtentDirection,'JoinCountersinkDiameter','90 deg')
    $feature.Name='Eight_M3_90deg_Countersunk_Clearance_Holes';$sk.Visible=$false
}
function Add-ConeEnvelope($definition) {
    $sections=$to.CreateObjectCollection()
    foreach($item in @(@(0,3),@(1.5,1.5))) {
        $plane=$definition.WorkPlanes.Item(3)
        if ($item[0] -ne 0) {$plane=$definition.WorkPlanes.AddByPlaneAndOffset($plane,($item[0]/10));$plane.Visible=$false}
        $sk=$definition.Sketches.Add($plane)
        $null=$sk.SketchCircles.AddByCenterRadius($tg.CreatePoint2d(0,0),($item[1]/10))
        $sections.Add($sk.Profiles.AddForSolid());$sk.Visible=$false
    }
    $lofts=$definition.Features.LoftFeatures
    $f=$lofts.Add($lofts.CreateLoftDefinition($sections,[Inventor.PartFeatureOperationEnum]::kNewBodyOperation));$f.Name='M3_90deg_Flat_Head_Envelope'
}
function Save-Part($name,$label,$r,$g,$b) {
    foreach($plane in $cd.WorkPlanes) {$plane.Visible=$false}
    Appearance $doc ($name+'_Appearance') $label $r $g $b
    if (-not $doc.Update2($false) -or $cd.SurfaceBodies.Count -ne 1) {throw ('Invalid connected solid: '+$name)}
    foreach($feature in $cd.Features) {if($feature.HealthStatus -ne [Inventor.HealthStatusEnum]::kUpToDateHealth) {throw ('Unhealthy feature: '+$feature.Name)}}
    $doc.PropertySets.Item('Inventor Summary Information').Item('Comments').Value=$label
    $doc.SaveAs((Join-Path $out ($name+'.ipt')),$false);Export-Step $doc ($name+'.step')
    Save-View $doc ($name+'.png') @(130,115,170) @(25.5,40,6) 1000 1100
    $doc.Save()
}
function New-CommonPart {
    $script:doc=$app.Documents.Add([Inventor.DocumentTypeEnum]::kPartDocumentObject,$app.FileManager.GetTemplateFile([Inventor.DocumentTypeEnum]::kPartDocumentObject),$true)
    $script:cd=$doc.ComponentDefinition;$doc.UnitsOfMeasure.LengthUnits=[Inventor.UnitsTypeEnum]::kMillimeterLengthUnits
    $parameters=@(
        @('OverallWidth','51 mm','Original rod outer width.'),@('RodWidth','6 mm','Full rod contact width.'),
        @('ContactLength','80 mm','Original plate contact length.'),@('BaseThickness','4 mm','Original plate and flange thickness.'),
        @('DropHeight','8.5 mm','Deck offset from the original flat plate.'),@('WebThickness','6 mm','Support wall width for M3 attachment.'),
        @('FingerStartX','19.933375831081217 mm','Boss X including +0.139127461912 mm pocket registration correction.'),
        @('FingerWidth','13.5 mm','Unchanged boss width.'),@('FingerThickness','6 mm','Unchanged boss height.'),@('FingerEndInset','4 mm','72 mm boss length.'),
        @('RodClearanceDiameter','3.4 mm','M3 clearance for original rod and new deck screws.'),
        @('ClampFirstY','41.82802366515844 mm','Original boss hole datum.'),@('ClampPitch','16 mm','Original boss thread pitch.'),
        @('ClampHeight','BaseThickness + FingerThickness / 2','Boss thread height.'),
        @('TapDrillDiameter','2.5 mm','M3 x 0.5 cylindrical pilot.'),@('TapDepth','6 mm','Original boss thread depth.'),
        @('RodHoleStart','5 mm','Original rod first fastener row.'),@('RodScrewPitch','20 mm','Original rod screw pitch.'),
        @('JoinLeftX','9.5 mm','Deck screw row inset to retain a 0.4 mm edge beyond the countersink.'),
        @('JoinFirstY','10 mm','Deck joining row offset from rod screws.'),@('JoinPitch','20 mm','Four new screws per support.'),
        @('JoinThreadDepth','6.5 mm','Accommodate a 6.1 mm modeled screw engagement and 0.4 mm bottom clearance.'),
        @('JoinCountersinkDiameter','6.2 mm','90 degree countersink; nominal 6.0 mm head recessed 0.1 mm.')
    )
    foreach($p in $parameters) {$null=Add-Parameter $p[0] $p[1] $p[2]}
}

try {
    $app.SilentOperation=$true
    # Archive only the positively identified monolithic variant under the repository helper folder.
    $outResolved=[IO.Path]::GetFullPath($out)
    $expected=[IO.Path]::GetFullPath((Join-Path $mechanical 'Rod_Holder_Adapter_Drop8p5'))
    if ($outResolved -ne $expected -or -not $outResolved.StartsWith($mechanical+'\',[StringComparison]::OrdinalIgnoreCase)) {throw 'Unsafe archive source.'}
    if (Test-Path -LiteralPath $outResolved) {
        $openPaths=@($app.Documents | Where-Object {$_.FullFileName.StartsWith($outResolved+'\')} | Sort-Object {$_.DocumentType} -Descending | ForEach-Object {$_.FullFileName})
        foreach($path in $openPaths) {$live=@($app.Documents | Where-Object {$_.FullFileName -eq $path});if($live.Count -gt 0) {$live[0].Close($true)}}
        $archive=[IO.Path]::GetFullPath((Join-Path $helper ('tmp\monolithic_drop_before_split_'+(Get-Date -Format 'yyyyMMdd_HHmmss'))))
        if (-not $archive.StartsWith((Join-Path $helper 'tmp')+'\',[StringComparison]::OrdinalIgnoreCase)) {throw 'Unsafe archive destination.'}
        Move-Item -LiteralPath $outResolved -Destination $archive
    }
    New-Item -ItemType Directory -Path $out -Force | Out-Null
    Set-Content -LiteralPath (Join-Path $out '.gitignore') -Value '/OldVersions/' -Encoding ASCII
    $referenceFiles=@(Get-ChildItem -LiteralPath $mechanical -Recurse -File | Where-Object {$_.FullName -notmatch '\\OldVersions\\' -and -not $_.FullName.StartsWith($out+'\') -and $_.Extension -in @('.ipt','.iam','.step')})
    $hashBefore=@{};foreach($file in $referenceFiles) {$hashBefore[$file.FullName]=(Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash}
    $new=[Inventor.PartFeatureOperationEnum]::kNewBodyOperation;$join=[Inventor.PartFeatureOperationEnum]::kJoinOperation
    New-CommonPart
    $null=Add-RectangleFeature 'Central_Deck' 'RodWidth' '0 mm' 'OverallWidth - 2 * RodWidth' 'ContactLength' '0 mm' 'BaseThickness' $new
    $null=Add-RectangleFeature 'Integral_Device_Boss' 'FingerStartX' 'FingerEndInset' 'FingerWidth' 'ContactLength - 2 * FingerEndInset' 'BaseThickness' 'FingerThickness' $join
    Add-DeckCountersinks;Add-SideHoles
    Save-Part 'Centre_Plate' 'Separate central plate and integral boss; ten original M3 side threads and eight countersinks.' 57 128 173
    $parameterReport=@($cd.Parameters.UserParameters | ForEach-Object {[pscustomobject]@{name=$_.Name;expression=$_.Expression;comment=$_.Comment}})
    foreach($side in @('Left','Right')) {
        New-CommonPart
        $webX=if($side -eq 'Left') {'RodWidth'} else {'OverallWidth - RodWidth - WebThickness'}
        $flangeX=if($side -eq 'Left') {'0 mm'} else {'OverallWidth - RodWidth - WebThickness'}
        $rodX=if($side -eq 'Left') {'RodWidth / 2'} else {'OverallWidth - RodWidth / 2'}
        $joinX=if($side -eq 'Left') {'JoinLeftX'} else {'OverallWidth - JoinLeftX'}
        $null=Add-RectangleFeature ($side+'_Connecting_Web') $webX '0 mm' 'WebThickness' 'ContactLength' 'BaseThickness' 'DropHeight' $new
        $null=Add-RectangleFeature ($side+'_Rod_Contact_Flange') $flangeX '0 mm' 'RodWidth + WebThickness' 'ContactLength' 'DropHeight' 'BaseThickness' $join
        $centres=@();for($i=0;$i -lt 4;$i++) {$centres+= ,@($rodX,('RodHoleStart + '+$i+' * RodScrewPitch'))}
        Add-Holes 'Original_Rod_Clearance_4x' $centres 'RodClearanceDiameter'
        Add-SupportThreads $joinX
        Save-Part ($side+'_Rod_Support') ($side+' separate support; four original rod clearance holes and four blind M3 x 0.5 - 6H deck threads, 6.5 mm depth.') 60 165 154
    }
    $doc=$app.Documents.Add([Inventor.DocumentTypeEnum]::kPartDocumentObject,$app.FileManager.GetTemplateFile([Inventor.DocumentTypeEnum]::kPartDocumentObject),$true)
    $doc.UnitsOfMeasure.LengthUnits=[Inventor.UnitsTypeEnum]::kMillimeterLengthUnits;$cd=$doc.ComponentDefinition
    Add-ConeEnvelope $cd
    Add-Cylinder $cd 'Clearance_Shank_To_Plate_Interface' 1.5 1.5 2.4 $join
    Add-Cylinder $cd 'Engaged_Thread_Core_No_Helix' 3.9 1.25 6.1 $join
    # Circular driver envelope replaces the small hex recess in this simplified fastener.
    $sk=$cd.Sketches.Add($cd.WorkPlanes.Item(3));$null=$sk.SketchCircles.AddByCenterRadius($tg.CreatePoint2d(0,0),.1)
    $ed=$cd.Features.ExtrudeFeatures.CreateExtrudeDefinition($sk.Profiles.AddForSolid(),[Inventor.PartFeatureOperationEnum]::kCutOperation)
    $ed.SetDistanceExtent(.08,[Inventor.PartFeatureExtentDirectionEnum]::kPositiveExtentDirection)
    $null=$cd.Features.ExtrudeFeatures.Add($ed);$sk.Visible=$false
    Save-Part 'Deck_M3x10_Countersunk' 'Illustrative M3 x 10 countersunk screw: 6 mm head, 90 degree cone, recessed 0.1 mm, 6.1 mm core engagement. No thread helix.' 110 119 129
    Write-Output 'Created three separately machinable parts and countersunk fastener.'

    $measurement=Get-Content -LiteralPath (Join-Path $baseline 'pocket_centre_distance.json') -Raw | ConvertFrom-Json
    $shiftX=-[double]$measurement.delta_xz_mm[0]
    $records=Get-Content -LiteralPath (Join-Path $baseline 'inward_placements.json') -Raw | ConvertFrom-Json
    $assembly=$app.Documents.Add([Inventor.DocumentTypeEnum]::kAssemblyDocumentObject,$app.FileManager.GetTemplateFile([Inventor.DocumentTypeEnum]::kAssemblyDocumentObject),$true)
    foreach($r in $records) {
        $m=Matrix-FromRows $r.matrix_cm;$path=$r.path;$name=$r.name
        if($r.name -eq 'Solid_Plate_With_Integral_Mounting_Boss') {$path=Join-Path $out 'Centre_Plate.ipt';$m.Cell(3,4)=-1.25;$name='Centre_Plate_With_Device_Boss'}
        elseif($r.name -eq 'Existing_Carrier_Hung_From_Side_Slots' -or $r.name -like 'Device_Clamp_M3_*') {$m.Cell(1,4)+=$shiftX/10;$m.Cell(3,4)-=.85}
        $occ=$assembly.ComponentDefinition.Occurrences.Add($path,$m);$occ.Name=$name;$occ.Grounded=$true
    }
    foreach($side in @('Left','Right')) {
        $m=Matrix 0 @(0,135,-12.5);$occ=$assembly.ComponentDefinition.Occurrences.Add((Join-Path $out ($side+'_Rod_Support.ipt')),$m);$occ.Name=$side+'_Rod_Support';$occ.Grounded=$true
    }
    foreach($x in @(9.5,41.5)) {for($i=0;$i -lt 4;$i++) {
        $y=145+20*$i;$m=Matrix 0 @($x,$y,-12.4)
        $occ=$assembly.ComponentDefinition.Occurrences.Add((Join-Path $out 'Deck_M3x10_Countersunk.ipt'),$m);$occ.Name='Deck_Join_M3_X'+$x+'_Y'+$y;$occ.Grounded=$true
    }}
    if (-not $assembly.Update2($false)) {throw 'Split assembly update failed.'}
    $views=$assembly.ComponentDefinition.RepresentationsManager.DesignViewRepresentations
    $tubeView=$views.Add('Tube_Review');$tubeView.Activate();$tubeView.Locked=$false
    $tube=@($assembly.ComponentDefinition.Occurrences | Where-Object {$_.Name -eq 'Probe_Tube_ID51_OD54'})[0]
    $asset=$assembly.Assets.Add([Inventor.AssetTypeEnum]::kAssetTypeAppearance,'Generic','Tube_Transparent_Review','Tube - transparent review')
    $asset.Item('generic_diffuse').Value=$to.CreateColor(165,186,199);$asset.Item('generic_transparency').Value=.78;$tube.Appearance=$asset
    $assembly.SaveAs($assemblyPath,$false);Export-Step $assembly 'Rod_Holder_Assembly_Drop8p5.step'
    $interior=$views.Add('Interior_Review');$interior.Activate();$interior.Locked=$false;$tube.Visible=$false
    Save-View $assembly 'Assembly_closeup.png' @(-100,240,180) @(25.5,175,-1) 1200 1200 $false
    Save-View $assembly 'Assembly_deck_side.png' @(-100,240,-180) @(25.5,175,-1) 1200 1200 $false
    $assembly.Save();$assembly.Close($true)
    $openPaths=@($app.Documents | Where-Object {$_.FullFileName.StartsWith($out+'\')} | Sort-Object {$_.DocumentType} -Descending | ForEach-Object {$_.FullFileName})
    foreach($path in $openPaths) {$live=@($app.Documents | Where-Object {$_.FullFileName -eq $path});if($live.Count -gt 0) {$live[0].Close($true)}}
    $assembly=$app.Documents.Open($assemblyPath,$true);Save-MountingPlacements $assembly $out
    $threadReports=@();foreach($name in @('Centre_Plate','Left_Rod_Support','Right_Rod_Support')) {
        $part=$app.Documents.Open((Join-Path $out ($name+'.ipt')),$false);$threads=$part.ComponentDefinition.Features.ThreadFeatures
        $expected=if($name -eq 'Centre_Plate') {10} else {4};if($threads.Count -ne $expected) {throw 'Saved thread count mismatch.'}
        foreach($t in $threads) {
            $info=$t.ThreadInfo;if($t.HealthStatus -ne [Inventor.HealthStatusEnum]::kUpToDateHealth -or $info.ThreadDesignation -ne 'M3x0.5' -or $info.Class -ne '6H' -or -not $info.Internal -or -not $info.RightHanded) {throw 'Invalid saved thread feature.'}
            $f=$t.ThreadedFace.Item(1)
            $threadReports+=[pscustomobject]@{part=$name;name=$t.Name;designation=$info.ThreadDesignation;class=$info.Class;depth_mm=($t.ThreadDepth.Value*10);entry_mm=@(($f.Geometry.BasePoint.X*10),($f.Geometry.BasePoint.Y*10),($f.Geometry.BasePoint.Z*10));healthy=$true}
        }
        if($part.ComponentDefinition.SurfaceBodies.Count -ne 1) {throw 'Each fabricated part must be one connected solid.'}
    }
    $refs=@($assembly.AllReferencedDocuments | ForEach-Object {$_.FullFileName});foreach($path in $refs) {if(-not $path.StartsWith($mechanical+'\',[StringComparison]::OrdinalIgnoreCase)) {throw 'Nonlocal reference.'}}
    $refs | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $out 'native_references.json') -Encoding UTF8
    [pscustomobject]@{saved_and_reopened=$true;fabricated_parts=3;assembly_occurrences=$assembly.ComponentDefinition.Occurrences.Count;thread_count=18;threads=$threadReports;local_reference_count=$refs.Count;deck_joint_count=8} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $out 'native_verification.json') -Encoding UTF8
    $carrier=@($assembly.ComponentDefinition.Occurrences | Where-Object {$_.Name -eq 'Existing_Carrier_Hung_From_Side_Slots'})[0]
    $pcb=@($carrier.Definition.Document.ComponentDefinition.Occurrences | Where-Object {$_.Name -eq 'Current PCB - simplified'})[0]
    $board=@($pcb.Definition.Document.ComponentDefinition.Occurrences | Where-Object {$_.Definition.Document.FullFileName -like '*\PCB_board.ipt'})[0]
    $tube=@($assembly.ComponentDefinition.Occurrences | Where-Object {$_.Name -eq 'Probe_Tube_ID51_OD54'})[0]
    [pscustomobject]@{carrier_matrix_cm=(Matrix-Rows $carrier.Transformation);pcb_matrix_cm=(Matrix-Rows $pcb.Transformation);board_matrix_cm=(Matrix-Rows $board.Transformation);tube_matrix_cm=(Matrix-Rows $tube.Transformation);board_path=$board.Definition.Document.FullFileName} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $out 'pocket_measurement_transforms.json') -Encoding UTF8
    [pscustomobject]@{variant='Three-piece screwed stepped plate';device_shift_mm=@($shiftX,0,-8.5);part_translation_mm=@(0,135,-12.5);deck_size_mm=@(39,80,4);split_z_mm=-8.5;deck_z_mm=@(-12.5,-8.5);rod_flanges_z_mm=@(-4,0);boss_z_mm=@(-8.5,-2.5);support_web_width_mm=6;deck_join_thread='M3x0.5 - 6H';deck_join_thread_depth_mm=6.5;deck_join_screws='8 illustrative M3 x 10 countersunk';join_rows_x_mm=@(9.5,41.5);join_rows_y_mm=@(145,165,185,205);head_recess_mm=.1;thread_engagement_mm=6.1;thread_bottom_clearance_mm=.4;archived_monolithic_variant=$archive;parameters=$parameterReport} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $out 'variant_plan.json') -Encoding UTF8
    $preservation=@();foreach($file in $referenceFiles) {
        $after=(Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
        $preservation+=[pscustomobject]@{path=$file.FullName;before_sha256=$hashBefore[$file.FullName];after_sha256=$after;unchanged=($after -eq $hashBefore[$file.FullName])}
        if($after -ne $hashBefore[$file.FullName]) {throw ('Original changed: '+$file.FullName)}
    }
    $preservation | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $out 'source_preservation.json') -Encoding UTF8
    $assembly.Activate();Write-Output ('Saved and reopened split variant; preserved '+$preservation.Count+' original CAD files.')
} finally {$app.SilentOperation=$oldSilent}
