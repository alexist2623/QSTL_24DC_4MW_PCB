$ErrorActionPreference = 'Stop'
$root = 'C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB'
$out = Join-Path $root 'QSTL_24DC_4MW_PCB\Mechanical_Assembly\Probe_H_Frame'
New-Item -ItemType Directory -Path $out -Force | Out-Null
$target = Join-Path $out 'Probe_H_Frame.ipt'
if (Test-Path -LiteralPath $target) { throw 'The frame already exists; edit its parameters instead of overwriting it.' }
Add-Type -Path 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
$app = [Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application')
$tg = $app.TransientGeometry
$to = $app.TransientObjects
$oldSilent = $app.SilentOperation
$doc = $null

function Add-Parameter($name, $expression, $comment, $unitless=$false) {
    $units = if ($unitless) { [Inventor.UnitsTypeEnum]::kUnitlessUnits } else { [Inventor.UnitsTypeEnum]::kMillimeterLengthUnits }
    $p = $cd.Parameters.UserParameters.AddByExpression($name,$expression,$units)
    $p.Comment = $comment
    return $p
}

function Length-Cm($expression) {
    return $doc.UnitsOfMeasure.GetValueFromExpression($expression,[Inventor.UnitsTypeEnum]::kMillimeterLengthUnits)
}

function Dimension-Point($sketch,$origin,$point,$xExpression,$yExpression) {
    $x = Length-Cm $xExpression
    $y = Length-Cm $yExpression
    if ([Math]::Abs($x) -lt 0.000001 -and [Math]::Abs($y) -lt 0.000001) {
        $null = $sketch.GeometricConstraints.AddCoincident($point,$origin)
        return
    }
    if ([Math]::Abs($x) -lt 0.000001) {
        $null = $sketch.GeometricConstraints.AddVerticalAlign($origin,$point)
    } else {
        $d = $sketch.DimensionConstraints.AddTwoPointDistance($origin,$point,[Inventor.DimensionOrientationEnum]::kHorizontalDim,$tg.CreatePoint2d(($x/2),($y-0.8)))
        $d.Parameter.Expression = $xExpression
    }
    if ([Math]::Abs($y) -lt 0.000001) {
        $null = $sketch.GeometricConstraints.AddHorizontalAlign($origin,$point)
    } else {
        $d = $sketch.DimensionConstraints.AddTwoPointDistance($origin,$point,[Inventor.DimensionOrientationEnum]::kVerticalDim,$tg.CreatePoint2d(($x-0.8),($y/2)))
        $d.Parameter.Expression = $yExpression
    }
}

function Add-Bar($name,$xExpression,$yExpression,$widthExpression,$heightExpression,$depthExpression) {
    $x = Length-Cm $xExpression; $y = Length-Cm $yExpression
    $w = Length-Cm $widthExpression; $h = Length-Cm $heightExpression
    $sketch = $cd.Sketches.Add($cd.WorkPlanes.Item(3))
    $sketch.Name = $name+'_Profile'
    $origin = $sketch.AddByProjectingEntity($cd.WorkPoints.Item(1))
    $lines = $sketch.SketchLines.AddAsTwoPointRectangle($tg.CreatePoint2d($x,$y),$tg.CreatePoint2d(($x+$w),($y+$h)))
    $anchor = $null; $horizontal = $null; $vertical = $null
    foreach ($line in $lines) {
        $a = $line.StartSketchPoint.Geometry; $b = $line.EndSketchPoint.Geometry
        if ([Math]::Abs($a.Y-$b.Y) -lt 0.000001) { $horizontal = $line }
        if ([Math]::Abs($a.X-$b.X) -lt 0.000001) { $vertical = $line }
        foreach ($point in @($line.StartSketchPoint,$line.EndSketchPoint)) {
            if ([Math]::Abs($point.Geometry.X-$x) -lt 0.000001 -and [Math]::Abs($point.Geometry.Y-$y) -lt 0.000001) { $anchor=$point }
        }
    }
    Dimension-Point $sketch $origin $anchor $xExpression $yExpression
    $d = $sketch.DimensionConstraints.AddTwoPointDistance($horizontal.StartSketchPoint,$horizontal.EndSketchPoint,[Inventor.DimensionOrientationEnum]::kHorizontalDim,$tg.CreatePoint2d(($x+$w/2),($y+$h+0.5)))
    $d.Parameter.Expression = $widthExpression
    $d = $sketch.DimensionConstraints.AddTwoPointDistance($vertical.StartSketchPoint,$vertical.EndSketchPoint,[Inventor.DimensionOrientationEnum]::kVerticalDim,$tg.CreatePoint2d(($x+$w+0.5),($y+$h/2)))
    $d.Parameter.Expression = $heightExpression
    $profile = $sketch.Profiles.AddForSolid()
    $definition = $cd.Features.ExtrudeFeatures.CreateExtrudeDefinition($profile,[Inventor.PartFeatureOperationEnum]::kNewBodyOperation)
    $definition.SetDistanceExtent($depthExpression,[Inventor.PartFeatureExtentDirectionEnum]::kPositiveExtentDirection)
    $feature = $cd.Features.ExtrudeFeatures.Add($definition)
    $feature.Name = $name
    $feature.SurfaceBodies.Item(1).Name = $name
    $sketch.Visible = $false
    Write-Output ('Created '+$name)
}

function Export-Step($document,$path) {
    $step = $app.ApplicationAddIns.ItemById('{90AF7F40-0C01-11D5-8E83-0010B541CD80}')
    $ctx = $to.CreateTranslationContext(); $ctx.Type=[Inventor.IOMechanismEnum]::kFileBrowseIOMechanism
    $options=$to.CreateNameValueMap(); $null=$step.HasSaveCopyAsOptions($document,$ctx,$options)
    $options.Value('ApplicationProtocolType')=3
    $data=$to.CreateDataMedium(); $data.FileName=$path
    $step.SaveCopyAs($document,$ctx,$options,$data)
}

function Save-View($filename,$eye) {
    $doc.Activate()
    $camera=$app.ActiveView.Camera
    $camera.Perspective=$false
    $camera.Eye=$tg.CreatePoint($eye[0],$eye[1],$eye[2])
    $camera.Target=$tg.CreatePoint(2.55,18,0.3)
    $camera.UpVector=$tg.CreateUnitVector(0,1,0)
    $camera.Fit();$camera.ApplyWithoutTransition()
    $bg=$to.CreateColor(245,247,250)
    $camera.SaveAsBitmap((Join-Path $out $filename),900,1600,$bg,$bg)
}

try {
    $app.SilentOperation=$true
    $doc=$app.Documents.Add([Inventor.DocumentTypeEnum]::kPartDocumentObject,$app.FileManager.GetTemplateFile([Inventor.DocumentTypeEnum]::kPartDocumentObject),$true)
    $doc.UnitsOfMeasure.LengthUnits=[Inventor.UnitsTypeEnum]::kMillimeterLengthUnits
    $cd=$doc.ComponentDefinition
    $null=Add-Parameter 'RodLength' '360 mm' 'Dimensioned rod length in section X2-X2.'
    $null=Add-Parameter 'RodWidth' '6 mm' 'Derived from (51 mm overall - 39 mm clear) / 2.'
    $null=Add-Parameter 'ClearGap' '39 mm' 'Dimensioned clear distance between rods.'
    $null=Add-Parameter 'ASSUMED_RodDepth' '6 mm' 'PROVISIONAL: front-to-back thickness is not dimensioned.'
    $null=Add-Parameter 'ASSUMED_CrossbarDepth' '6 mm' 'PROVISIONAL: crossbar front-to-back thickness is not dimensioned.'
    $null=Add-Parameter 'EST_CrossbarHeight' '8 mm' 'Estimated from drawing geometry; not an explicit dimension.'
    $null=Add-Parameter 'EST_UpperCrossbarFromTop' '110 mm' 'Estimated centre position measured from rod top.'
    $null=Add-Parameter 'EST_LowerCrossbarFromTop' '270 mm' 'Estimated centre position measured from rod top.'
    $null=Add-Parameter 'HolePitch' '10 mm' 'Dimensioned M3 hole pitch.'
    $null=Add-Parameter 'FirstHoleFromTop' '30 mm' 'Dimensioned first hole centre from rod top.'
    $null=Add-Parameter 'HoleNominalDiameter' '3 mm' 'Simplified nominal M3 thread envelope, not a tap-drill specification.'
    $null=Add-Parameter 'HoleCount' '33' 'Repeated hole locations on each rod.' $true
    $null=Add-Parameter 'OverallWidth' '2 * RodWidth + ClearGap' 'Derived overall width.'
    $null=Add-Parameter 'RodCentreSpacing' 'RodWidth + ClearGap' 'Derived centre-to-centre spacing.'

    Add-Bar 'Left_Rod' '0 mm' '0 mm' 'RodWidth' 'RodLength' 'ASSUMED_RodDepth'
    Add-Bar 'Right_Rod' 'RodWidth + ClearGap' '0 mm' 'RodWidth' 'RodLength' 'ASSUMED_RodDepth'
    Add-Bar 'Upper_Crossbar_ESTIMATED' 'RodWidth' 'RodLength - EST_UpperCrossbarFromTop - EST_CrossbarHeight / 2' 'ClearGap' 'EST_CrossbarHeight' 'ASSUMED_CrossbarDepth'
    Add-Bar 'Lower_Crossbar_ESTIMATED' 'RodWidth' 'RodLength - EST_LowerCrossbarFromTop - EST_CrossbarHeight / 2' 'ClearGap' 'EST_CrossbarHeight' 'ASSUMED_CrossbarDepth'

    $sketch=$cd.Sketches.Add($cd.WorkPlanes.Item(3));$sketch.Name='M3_Nominal_Seed_Locations'
    $origin=$sketch.AddByProjectingEntity($cd.WorkPoints.Item(1))
    foreach ($xExpression in @('RodWidth / 2','ClearGap + 1.5 * RodWidth')) {
        $x=Length-Cm $xExpression; $y=Length-Cm 'RodLength - FirstHoleFromTop'
        $circle=$sketch.SketchCircles.AddByCenterRadius($tg.CreatePoint2d($x,$y),(Length-Cm 'HoleNominalDiameter / 2'))
        Dimension-Point $sketch $origin $circle.CenterSketchPoint $xExpression 'RodLength - FirstHoleFromTop'
        $dim=$sketch.DimensionConstraints.AddDiameter($circle,$tg.CreatePoint2d(($x+0.5),($y+0.5)))
        $dim.Parameter.Expression='HoleNominalDiameter'
    }
    $cutDef=$cd.Features.ExtrudeFeatures.CreateExtrudeDefinition($sketch.Profiles.AddForSolid(),[Inventor.PartFeatureOperationEnum]::kCutOperation)
    $cutDef.SetThroughAllExtent([Inventor.PartFeatureExtentDirectionEnum]::kPositiveExtentDirection)
    $rodBodies=$to.CreateObjectCollection();$rodBodies.Add($cd.SurfaceBodies.Item(1));$rodBodies.Add($cd.SurfaceBodies.Item(2))
    $cutDef.AffectedBodies=$rodBodies
    $cut=$cd.Features.ExtrudeFeatures.Add($cutDef);$cut.Name='M3_Simplified_Through_Seed'
    $sketch.Visible=$false
    $parents=$to.CreateObjectCollection();$parents.Add($cut)
    $patternDef=$cd.Features.RectangularPatternFeatures.CreateDefinition($parents,$cd.WorkAxes.Item(2),$false,'HoleCount','HolePitch',[Inventor.PatternSpacingTypeEnum]::kDefault)
    $patternDef.AffectedBodies=$rodBodies
    $pattern=$cd.Features.RectangularPatternFeatures.AddByDefinition($patternDef)
    $pattern.SetAffectedBodies($rodBodies)
    $pattern.Name='M3_33x_Per_Rod_10mm_Pitch'

    $appearance=$doc.Assets.Add([Inventor.AssetTypeEnum]::kAssetTypeAppearance,'Generic','Copper_Visual','Copper - grade unspecified')
    $appearance.Item('generic_diffuse').Value=$to.CreateColor(180,111,65)
    $doc.ActiveAppearance=$appearance
    $doc.PropertySets.Item('Inventor Summary Information').Item('Comments').Value='Reference-only H frame. Source: SO01373.10-Probe-R01.pdf, X2-X2. ASSUMED/EST parameters are not manufacturing dimensions. Four separate solids. M3 threads are nominal cylinders; no thread helix or unspecified fastening details.'
    if (-not $doc.Update2($false)) { throw 'Frame feature update failed.' }
    if ($cd.SurfaceBodies.Count -ne 4) { throw 'Expected four separate solid bodies.' }
    $doc.SaveAs($target,$false)
    Export-Step $doc (Join-Path $out 'Probe_H_Frame.step')
    Save-View 'Probe_H_Frame_front.png' @(2.55,18,90)
    Save-View 'Probe_H_Frame_isometric.png' @(34,40,100)
    $doc.Save()
    $parameters=@($cd.Parameters.UserParameters | ForEach-Object { [pscustomobject]@{name=$_.Name;expression=$_.Expression;comment=$_.Comment} })
    $summary=[pscustomobject]@{source_pdf='SO01373.10-Probe-R01.pdf';native_file=$target;solid_bodies=$cd.SurfaceBodies.Count;parameters=$parameters}
    $summary | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $out 'model_parameters.json') -Encoding UTF8
    Write-Output ('Saved '+$target)
} catch {
    if ($null -ne $doc -and -not (Test-Path -LiteralPath $target)) { $doc.Close($true) }
    throw
} finally { $app.SilentOperation=$oldSilent }
