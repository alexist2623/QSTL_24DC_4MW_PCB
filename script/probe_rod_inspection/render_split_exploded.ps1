$ErrorActionPreference='Stop'
Add-Type -Path 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
$root='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB'
$helper=Join-Path $root 'script\probe_rod_inspection'
$out=Join-Path $root 'QSTL_24DC_4MW_PCB\Mechanical_Assembly\Rod_Holder_Adapter_Drop8p5'
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application');$tg=$app.TransientGeometry;$to=$app.TransientObjects
$source=[IO.File]::ReadAllText((Join-Path $helper 'build_holder_adapter.ps1'));$start=$source.IndexOf('function Matrix(');$end=$source.IndexOf('try {')
. ([scriptblock]::Create($source.Substring($start,$end-$start)))
$silent=$app.SilentOperation;$preview=$null
try {
    $app.SilentOperation=$true
    $preview=$app.Documents.Add([Inventor.DocumentTypeEnum]::kAssemblyDocumentObject,$app.FileManager.GetTemplateFile([Inventor.DocumentTypeEnum]::kAssemblyDocumentObject),$true)
    foreach($entry in @(@('Centre_Plate',0,0,-10),@('Left_Rod_Support',-8,0,8),@('Right_Rod_Support',8,0,8))) {
        $occ=$preview.ComponentDefinition.Occurrences.Add((Join-Path $out ($entry[0]+'.ipt')),(Matrix 0 @($entry[1],$entry[2],$entry[3])))
        $occ.Name=$entry[0];$occ.Grounded=$true
    }
    foreach($x in @(9.5,41.5)) {foreach($y in @(10,30,50,70)) {
        $occ=$preview.ComponentDefinition.Occurrences.Add((Join-Path $out 'Deck_M3x10_Countersunk.ipt'),(Matrix 0 @($x,$y,-24)))
        $occ.Name='Deck_screw_'+$x+'_'+$y;$occ.Grounded=$true
    }}
    $preview.Update2($false)|Out-Null
    Save-View $preview 'Exploded_plate.png' @(-125,120,-180) @(25.5,40,-3) 1400 1350
    $preview.Close($true);$preview=$null
    $assembly=$app.Documents.Open((Join-Path $out 'Rod_Holder_Assembly_Drop8p5.iam'),$true)
    $assembly.Activate();Write-Output 'Rendered exploded preview without modifying the assembled placements.'
} finally {if($null -ne $preview) {$preview.Close($true)};$app.SilentOperation=$silent}
