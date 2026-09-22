$ErrorActionPreference='Stop'
Add-Type -Path 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
$out='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\script\probe_rod_inspection\coldfinger_reference'
$source=Join-Path $env:USERPROFILE 'Nextcloud3\Lab\Instruments\CustomParts\ColdFinger\DilFridge_Mechanical\v2\assembly_coldfinger_v2.SLDASM'
$hash=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application')
$oldSilent=$app.SilentOperation
try {
    $app.SilentOperation=$true
    # Stage inputs so the translator creates its child IPT folder inside the repository.
    $staging=Join-Path $out 'assembly_source'
    New-Item -ItemType Directory -Path $staging -Force | Out-Null
    foreach($file in (Get-ChildItem -LiteralPath ([IO.Path]::GetDirectoryName($source)) -File | Where-Object {$_.Extension -in @('.SLDPRT','.SLDASM')})) {
        Copy-Item -LiteralPath $file.FullName -Destination $staging -Force
    }
    $stagedSource=Join-Path $staging ([IO.Path]::GetFileName($source))
    $doc=$app.Documents.Open($stagedSource,$true)
    $doc.Update2($false) | Out-Null
    $count=$doc.ComponentDefinition.Occurrences.Count
    if ($count -eq 0) { throw 'No assembly occurrences imported.' }
    $doc.SaveAs((Join-Path $out 'assembly_coldfinger_v2.iam'),$false)
    $to=$app.TransientObjects;$step=$app.ApplicationAddIns.ItemById('{90AF7F40-0C01-11D5-8E83-0010B541CD80}')
    $ctx=$to.CreateTranslationContext();$ctx.Type=[Inventor.IOMechanismEnum]::kFileBrowseIOMechanism
    $opts=$to.CreateNameValueMap();$null=$step.HasSaveCopyAsOptions($doc,$ctx,$opts)
    $data=$to.CreateDataMedium();$data.FileName=Join-Path $out 'assembly_coldfinger_v2.step'
    $step.SaveCopyAs($doc,$ctx,$opts,$data)
    $items=@($doc.ComponentDefinition.Occurrences | ForEach-Object { [pscustomobject]@{name=$_.Name;type=$_.DefinitionDocumentType;source=$_.Definition.Document.FullFileName} })
    [pscustomobject]@{source=$source;sha256=$hash;top_level_occurrences=$count;items=$items} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $out 'assembly_import.json') -Encoding UTF8
    if ((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash -ne $hash) { throw 'Source assembly changed.' }
    Write-Output ($items | ConvertTo-Json -Depth 5)
} finally { $app.SilentOperation=$oldSilent }
