$ErrorActionPreference='Stop'
$root='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB'
$out=Join-Path $root 'script\probe_rod_inspection\coldfinger_reference'
$source=Join-Path $env:USERPROFILE 'Nextcloud3\Lab\Instruments\CustomParts\ColdFinger\DilFridge_Mechanical\v2'
Add-Type -Path 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application')
$step=$app.ApplicationAddIns.ItemById('{90AF7F40-0C01-11D5-8E83-0010B541CD80}')
$to=$app.TransientObjects;$tg=$app.TransientGeometry
$oldSilent=$app.SilentOperation
$results=@()
try {
    $app.SilentOperation=$true
    foreach ($name in @('Coldfinger-v2','Coldfinger-SimplePlate','DCAnchor','Top plate-MXC-v2')) {
        $sourceFile=Join-Path $source ($name+'.SLDPRT')
        $hash=(Get-FileHash -LiteralPath $sourceFile -Algorithm SHA256).Hash
        $path=Join-Path $out ($name+'.ipt')
        if (Test-Path -LiteralPath $path) { $doc=$app.Documents.Open($path,$false) } else {
            $doc=$app.Documents.Add([Inventor.DocumentTypeEnum]::kPartDocumentObject,$app.FileManager.GetTemplateFile([Inventor.DocumentTypeEnum]::kPartDocumentObject),$false)
            $imports=$doc.ComponentDefinition.ReferenceComponents.ImportedComponents
            $definition=$imports.CreateDefinition($sourceFile);$definition.ReferenceModel=$true
            $null=$imports.Add($definition)
            $doc.SaveAs($path,$false)
        }
        if ($doc.ComponentDefinition.SurfaceBodies.Count -eq 0) {
            $imports=$doc.ComponentDefinition.ReferenceComponents.ImportedComponents
            $definition=$imports.CreateDefinition($sourceFile);$definition.ReferenceModel=$true
            $null=$imports.Add($definition)
            $doc.Update2($false) | Out-Null
            $doc.Save()
        }
        if ($doc.ComponentDefinition.SurfaceBodies.Count -lt 1) { throw ('No solid geometry imported: '+$name) }
        $ctx=$to.CreateTranslationContext();$ctx.Type=[Inventor.IOMechanismEnum]::kFileBrowseIOMechanism
        $opts=$to.CreateNameValueMap();$null=$step.HasSaveCopyAsOptions($doc,$ctx,$opts)
        $data=$to.CreateDataMedium();$data.FileName=Join-Path $out ($name+'.step')
        $step.SaveCopyAs($doc,$ctx,$opts,$data)
        $results+=[pscustomobject]@{name=$name;source=$sourceFile;sha256=$hash;bodies=$doc.ComponentDefinition.SurfaceBodies.Count}
        if ((Get-FileHash -LiteralPath $sourceFile -Algorithm SHA256).Hash -ne $hash) { throw 'Source CAD changed.' }
        Write-Output ('Imported read-only reference: '+$name)
    }
    $results | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $out 'source_hashes.json') -Encoding UTF8
} finally { $app.SilentOperation=$oldSilent }
