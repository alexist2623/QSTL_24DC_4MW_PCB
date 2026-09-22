$ErrorActionPreference='Stop'
Add-Type -Path 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
$helper='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\script\probe_rod_inspection'
$inspection=Join-Path $helper 'coldfinger_reference'
$generated=Join-Path $env:USERPROFILE 'Nextcloud3\Lab\Instruments\CustomParts\ColdFinger\DilFridge_Mechanical\v2\assembly_coldfinger_v2'
$expected=[IO.Path]::GetFullPath($generated)
$names=@('Coldfinger-v2.ipt','Coldfinger-SimplePlate.ipt','DCAnchor.ipt','Top plate-MXC-v2.ipt','Top_ForFridge.ipt')
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application')
$assembly=$app.Documents.Open((Join-Path $inspection 'assembly_coldfinger_v2.iam'),$false)
foreach($reference in $assembly.AllReferencedDocuments) {
    if ($reference.FullFileName.StartsWith($expected+'\',[StringComparison]::OrdinalIgnoreCase)) {throw 'Inspection assembly still references generated source-folder files.'}
}
foreach($document in @($app.Documents)) {
    if ($document.FullFileName.StartsWith($expected+'\',[StringComparison]::OrdinalIgnoreCase)) {$document.Close($true)}
}
foreach($name in $names) {
    $candidate=[IO.Path]::GetFullPath((Join-Path $generated $name))
    if ([IO.Path]::GetDirectoryName($candidate) -ne $expected) {throw 'Unexpected cleanup path.'}
    $copy=Join-Path $inspection ('assembly_parts\'+$name)
    if (Test-Path -LiteralPath $candidate) {
        if ((Get-FileHash -LiteralPath $candidate).Hash -ne (Get-FileHash -LiteralPath $copy).Hash) {throw ('Copy differs: '+$name)}
        Remove-Item -LiteralPath $candidate
    }
}
if ((Test-Path -LiteralPath $generated) -and @(Get-ChildItem -LiteralPath $generated -Force).Count -eq 0) {Remove-Item -LiteralPath $generated}
$checks=@()
foreach($entry in (Get-Content -LiteralPath (Join-Path $inspection 'source_hashes.json') -Raw | ConvertFrom-Json)) {
    $same=(Get-FileHash -LiteralPath $entry.source).Hash -eq $entry.sha256
    if (-not $same) {throw ('Reference part changed: '+$entry.source)}
    $checks+=[pscustomobject]@{source=$entry.source;sha256=$entry.sha256;unchanged=$same}
}
$entry=Get-Content -LiteralPath (Join-Path $inspection 'assembly_import.json') -Raw | ConvertFrom-Json
if ((Get-FileHash -LiteralPath $entry.source).Hash -ne $entry.sha256) {throw 'Reference assembly changed.'}
$checks+=[pscustomobject]@{source=$entry.source;sha256=$entry.sha256;unchanged=$true}
$checks | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $inspection 'source_preservation.json') -Encoding UTF8
Write-Output 'Reference hashes verified; generated translation files reside only in repository inspection storage.'
