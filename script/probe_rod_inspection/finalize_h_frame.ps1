$ErrorActionPreference='Stop'
Add-Type -Path 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
$out='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB\Mechanical_Assembly\Probe_H_Frame'
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application')
$tg=$app.TransientGeometry;$to=$app.TransientObjects
$doc=$app.Documents.Open((Join-Path $out 'Probe_H_Frame.ipt'),$true)
$cd=$doc.ComponentDefinition
$pattern=$cd.Features.RectangularPatternFeatures.Item(1)
$bodies=$to.CreateObjectCollection();$bodies.Add($cd.SurfaceBodies.Item(1));$bodies.Add($cd.SurfaceBodies.Item(2))
$pattern.SetAffectedBodies($bodies)
if (-not $doc.Update2($false)) { throw 'Pattern update failed.' }

# Exercise the editable assumptions, then restore the documented values.
$depth=$cd.Parameters.UserParameters.Item('ASSUMED_RodDepth')
$upper=$cd.Parameters.UserParameters.Item('EST_UpperCrossbarFromTop')
try {
    $depth.Expression='7 mm';$upper.Expression='115 mm'
    if (-not $doc.Update2($false)) { throw 'Parametric update failed.' }
    $rodDepth=($cd.SurfaceBodies.Item(1).RangeBox.MaxPoint.Z-$cd.SurfaceBodies.Item(1).RangeBox.MinPoint.Z)*10
    $barCentre=($cd.SurfaceBodies.Item(3).RangeBox.MaxPoint.Y+$cd.SurfaceBodies.Item(3).RangeBox.MinPoint.Y)*5
    if ([Math]::Abs($rodDepth-7) -gt 0.0001 -or [Math]::Abs($barCentre-245) -gt 0.0001) { throw 'Assumption parameters do not drive geometry.' }
} finally {
    $depth.Expression='6 mm';$upper.Expression='110 mm'
    $doc.Update2($false) | Out-Null
}
$doc.Save()
$doc.Close($true)
$doc=$app.Documents.Open((Join-Path $out 'Probe_H_Frame.ipt'),$true)
$cd=$doc.ComponentDefinition
if ($cd.SurfaceBodies.Count -ne 4) { throw 'Body count changed after reopen.' }
$step=$app.ApplicationAddIns.ItemById('{90AF7F40-0C01-11D5-8E83-0010B541CD80}')
$ctx=$to.CreateTranslationContext();$ctx.Type=[Inventor.IOMechanismEnum]::kFileBrowseIOMechanism
$opts=$to.CreateNameValueMap();$null=$step.HasSaveCopyAsOptions($doc,$ctx,$opts)
$opts.Value('ApplicationProtocolType')=3
$data=$to.CreateDataMedium();$data.FileName=Join-Path $out 'Probe_H_Frame.step'
$step.SaveCopyAs($doc,$ctx,$opts,$data)
foreach ($name in @('front','isometric')) {
    $doc.Activate();$camera=$app.ActiveView.Camera;$camera.Perspective=$false
    if ($name -eq 'front') { $camera.Eye=$tg.CreatePoint(2.55,18,90) } else { $camera.Eye=$tg.CreatePoint(34,40,100) }
    $camera.Target=$tg.CreatePoint(2.55,18,0.3);$camera.UpVector=$tg.CreateUnitVector(0,1,0)
    $camera.Fit();$camera.ApplyWithoutTransition();$bg=$to.CreateColor(245,247,250)
    $camera.SaveAsBitmap((Join-Path $out ('Probe_H_Frame_'+$name+'.png')),900,1600,$bg,$bg)
}
$doc.Save()
[pscustomobject]@{reopened=$true;solid_bodies=4;depth_parameter_exercised_mm=7;upper_crossbar_offset_exercised_mm=115;parameters_restored=$true} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $out 'native_verification.json') -Encoding UTF8
Write-Output 'Both rod bodies patterned; editable depth and crossbar location verified; saved and reopened.'
