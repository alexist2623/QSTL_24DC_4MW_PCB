$ErrorActionPreference='Stop'
Add-Type -Path 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
$root='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB'
$helper=Join-Path $root 'script\probe_rod_inspection'
$out=Join-Path $root 'QSTL_24DC_4MW_PCB\Mechanical_Assembly\Rod_Holder_Adapter_Drop8p5'
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application');$tg=$app.TransientGeometry;$to=$app.TransientObjects
$source=[IO.File]::ReadAllText((Join-Path $helper 'build_holder_adapter.ps1'));$start=$source.IndexOf('function Export-Step(');$end=$source.IndexOf('try {')
. ([scriptblock]::Create($source.Substring($start,$end-$start)))
$silent=$app.SilentOperation
try {
    $app.SilentOperation=$true
    $doc=$app.Documents.Open((Join-Path $out 'Centre_Plate.ipt'),$true)
    $hole=$doc.ComponentDefinition.Features.HoleFeatures.Item(1)
    $hole.SetThroughAllExtent([Inventor.PartFeatureExtentDirectionEnum]::kNegativeExtentDirection)
    if(-not $doc.Update2($false)) {throw 'Countersink repair failed.'}
    foreach($feature in $doc.ComponentDefinition.Features) {if($feature.HealthStatus -ne [Inventor.HealthStatusEnum]::kUpToDateHealth) {throw ('Unhealthy feature: '+$feature.Name)}}
    $doc.Save();Export-Step $doc 'Centre_Plate.step'
    Save-View $doc 'Centre_Plate.png' @(130,115,170) @(25.5,40,6) 1000 1100
    Save-View $doc 'Centre_Plate_countersinks.png' @(-100,115,-170) @(25.5,40,6) 1000 1100
    $doc.Save()
    $assemblyPath=Join-Path $out 'Rod_Holder_Assembly_Drop8p5.iam'
    $assembly=$app.Documents.Open($assemblyPath,$true)
    $assembly.Update2($false)|Out-Null
    $views=$assembly.ComponentDefinition.RepresentationsManager.DesignViewRepresentations
    $views.Item('Tube_Review').Activate()
    Export-Step $assembly 'Rod_Holder_Assembly_Drop8p5.step'
    $views.Item('Interior_Review').Activate()
    Save-View $assembly 'Assembly_closeup.png' @(-100,240,180) @(25.5,175,-1) 1200 1200 $false
    Save-View $assembly 'Assembly_deck_side.png' @(-100,240,-180) @(25.5,175,-1) 1200 1200 $false
    $assembly.Save();$assembly.Close($true);$doc.Close($true)
    $assembly=$app.Documents.Open($assemblyPath,$true)
    $part=$app.Documents.Open((Join-Path $out 'Centre_Plate.ipt'),$false)
    $featureReport=@();foreach($occ in $assembly.ComponentDefinition.Occurrences) {
        if($occ.Definition.Document.FullFileName.StartsWith($out+'\')) {
            foreach($feature in $occ.Definition.Document.ComponentDefinition.Features) {
                if($feature.HealthStatus -ne [Inventor.HealthStatusEnum]::kUpToDateHealth) {throw ('Saved unhealthy feature: '+$feature.Name)}
                $featureReport+=[pscustomobject]@{occurrence=$occ.Name;feature=$feature.Name;healthy=$true}
            }
        }
    }
    $featureReport | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath (Join-Path $out 'saved_feature_health.json') -Encoding UTF8
    $assembly.Activate();Write-Output 'Reversed hole extent; saved/reopened all new features are healthy.'
} finally {$app.SilentOperation=$silent}
