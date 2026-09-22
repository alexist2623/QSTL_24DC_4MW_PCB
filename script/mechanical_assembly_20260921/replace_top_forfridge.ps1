$ErrorActionPreference = 'Stop'
$here = 'C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\script\mechanical_assembly_20260921'
# Reuse only the setup and helper functions, without running the initial build.
$buildSource = [IO.File]::ReadAllText((Join-Path $here 'create_inventor_assembly.ps1'))
$helperSource = $buildSource.Substring(0, $buildSource.IndexOf("`ntry {"))
. ([scriptblock]::Create($helperSource))

try {
    $app.SilentOperation = $true
    $top = Import-Part (Join-Path $out 'Top_ForFridge_reference.step') (Join-Path $out 'Top_ForFridge.ipt') @(156,163,172)
    $records = @()
    foreach ($name in @('Carrier_with_PCB','Carrier_exploded')) {
        $doc = $app.Documents.Open((Join-Path $out ($name+'.iam')),$true)
        $upper = @($doc.ComponentDefinition.Occurrences | Where-Object { $_.Name -like 'Top*' })
        if ($upper.Count -ne 1) { throw 'Expected exactly one upper mechanical occurrence.' }
        $upper[0].Replace($top.FullFileName,$false)
        $upper[0].Name = 'Top_ForFridge - QD side'
        $position = @($fit.top_transform.translation_mm)
        if ($name -eq 'Carrier_exploded') {
            $position[2] += 30
            $lower = @($doc.ComponentDefinition.Occurrences | Where-Object { $_.Name -like 'Bottom*' })[0]
            $lower.Grounded = $false
            $lower.Transformation = Matrix 0 @(0,0,-20)
            $lower.Grounded = $true
        }
        $upper[0].Grounded = $false
        $upper[0].Transformation = Matrix 0 $position
        $upper[0].Grounded = $true
        $doc.Update2($true) | Out-Null
        if ($name -eq 'Carrier_exploded') {
            Save-View $doc 'Assembly_exploded' @(110,85,95) @(16.3,44,4) @(0,1,0)
        } else {
            Save-View $doc 'Assembly_closed' @(95,105,100) @(16.3,44,4) @(0,1,0)
            Export-Step $doc (Join-Path $out 'Carrier_with_PCB.step')
        }
        $doc.Save()
        foreach ($occ in $doc.ComponentDefinition.Occurrences) {
            $v = $occ.Transformation.Translation
            $records += [pscustomobject]@{assembly=$name;name=$occ.Name;source=$occ.Definition.Document.FullFileName;grounded=$occ.Grounded;translation_mm=@(($v.X*10),($v.Y*10),($v.Z*10))}
        }
    }
    $pcb = $app.Documents.Open((Join-Path $out 'PCB_simplified.iam'),$true)
    Export-Step $pcb (Join-Path $out 'PCB_simplified.step')
    Save-View $pcb 'PCB_SMP_side' @(85,100,105) @(9.75,34,0) @(0,1,0)
    Save-View $pcb 'PCB_QD_side' @(-60,80,-105) @(9.75,34,0) @(0,1,0)
    $pcb.Save()
    $records | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $out 'inventor_occurrences.json') -Encoding UTF8
    $assy = $app.Documents.Open((Join-Path $out 'Carrier_with_PCB.iam'),$true)
    $assy.Activate()
    Write-Output ($records | ConvertTo-Json -Depth 5)
} finally { $app.SilentOperation = $oldSilent }
