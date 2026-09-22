$ErrorActionPreference = 'Stop'
$root = 'C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB'
$out = Join-Path $root 'QSTL_24DC_4MW_PCB\Mechanical_Assembly'
$source = Join-Path $env:USERPROFILE 'Nextcloud3\Lab\Instruments\CustomParts\Carrier_8MW_24DC\Mechanical\Narrow_V3_24DC_8MW'
New-Item -ItemType Directory -Path $out -Force | Out-Null
$app = [Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application')
Add-Type -Path 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
$step = $app.ApplicationAddIns.ItemById('{90AF7F40-0C01-11D5-8E83-0010B541CD80}')
$step.Activate()
$oldSilent = $app.SilentOperation
$report = @()
try {
    $app.SilentOperation = $true
    foreach ($name in @('Bottom','Top_ForFridge')) {
        $target = Join-Path $out ($name + '_reference.ipt')
        $doc = $null
        if (Test-Path -LiteralPath $target) { $doc = $app.Documents.Open($target, $false) }
        if ($name -eq 'Bottom') {
            for ($i=1; $i -le $app.Documents.Count; $i++) {
                $candidate = $app.Documents.Item($i)
                if ($candidate.DocumentType -eq 12290 -and $candidate.FullFileName -eq '' -and $candidate.ComponentDefinition.SurfaceBodies.Count -eq 1) {
                    $imports = $candidate.ComponentDefinition.ReferenceComponents.ImportedComponents
                    if ($imports.Count -eq 1 -and $imports.Item(1).Name -eq 'Bottom.SLDPRT') { $doc = $candidate; break }
                }
            }
        }
        if ($null -eq $doc) {
            $template = $app.FileManager.GetTemplateFile([Inventor.DocumentTypeEnum]::kPartDocumentObject)
            $doc = $app.Documents.Add([Inventor.DocumentTypeEnum]::kPartDocumentObject, $template, $false)
            $imports = $doc.ComponentDefinition.ReferenceComponents.ImportedComponents
            $definition = $imports.CreateDefinition((Join-Path $source ($name + '.SLDPRT')))
            $definition.ReferenceModel = $true
            $null = $imports.Add($definition)
        }
        if ($doc.ComponentDefinition.SurfaceBodies.Count -lt 1) { throw ('No solids in ' + $name) }
        if ($doc.FullFileName -eq $target) { $doc.Save() } else { $doc.SaveAs($target, $false) }
        $context = $app.TransientObjects.CreateTranslationContext()
        $context.Type = [Inventor.IOMechanismEnum]::kFileBrowseIOMechanism
        $options = $app.TransientObjects.CreateNameValueMap()
        $null = $step.HasSaveCopyAsOptions($doc, $context, $options)
        $options.Value('ApplicationProtocolType') = 3
        $data = $app.TransientObjects.CreateDataMedium()
        $data.FileName = Join-Path $out ($name + '_reference.step')
        $step.SaveCopyAs($doc, $context, $options, $data)
        $box = $doc.ComponentDefinition.RangeBox
        $report += [pscustomobject]@{name=$name;source=(Join-Path $source ($name+'.SLDPRT'));bodies=$doc.ComponentDefinition.SurfaceBodies.Count;bounds_mm=@(($box.MinPoint.X*10),($box.MinPoint.Y*10),($box.MinPoint.Z*10),($box.MaxPoint.X*10),($box.MaxPoint.Y*10),($box.MaxPoint.Z*10))}
        Write-Output ('Exported ' + $name)
    }
    $report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $out 'reference_import.json') -Encoding UTF8
} finally { $app.SilentOperation = $oldSilent }
