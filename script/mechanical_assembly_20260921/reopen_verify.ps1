$ErrorActionPreference = 'Stop'
$app = [Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application')
$out = 'C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB\Mechanical_Assembly'
$path = Join-Path $out 'Carrier_with_PCB.iam'
$doc = $app.Documents.Open($path,$true)
if ($doc.Dirty) { throw 'Assembly has unsaved changes.' }
$doc.Close($true)
$doc = $app.Documents.Open($path,$true)
$doc.Activate()
$references = @($doc.AllReferencedDocuments | ForEach-Object { $_.FullFileName })
if ($references.Count -lt 26) { throw 'Missing assembly references.' }
if (-not ($references -contains (Join-Path $out 'Top_ForFridge.ipt'))) { throw 'Wrong upper part.' }
if ($references -contains (Join-Path $out 'Top.ipt')) { throw 'Superseded upper part is still used.' }
foreach ($reference in $references) {
    if (-not $reference.StartsWith($out+'\',[StringComparison]::OrdinalIgnoreCase)) { throw ('External reference: '+$reference) }
}
$result = [pscustomobject]@{reopened=$true;reference_count=$references.Count;top_source='Top_ForFridge.ipt';references=$references}
$result | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $out 'native_reopen_verification.json') -Encoding UTF8
Write-Output ('Reopened saved assembly; '+$references.Count+' local references; Top_ForFridge verified.')
