$ErrorActionPreference = 'Stop'
$app = [Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application')
Write-Output ('Inventor version: ' + $app.SoftwareVersion.DisplayVersion)
for ($i=1; $i -le $app.Documents.Count; $i++) {
    $doc = $app.Documents.Item($i)
    Write-Output ('Document: ' + $doc.DisplayName + ' | ' + $doc.FullFileName + ' | type=' + $doc.DocumentType)
    if ($doc.DocumentType -eq 12290) {
        $def = $doc.ComponentDefinition
        Write-Output ('Bodies: ' + $def.SurfaceBodies.Count)
        $box = $def.RangeBox
        Write-Output ('Bounds cm: ' + (@($box.MinPoint.X,$box.MinPoint.Y,$box.MinPoint.Z,$box.MaxPoint.X,$box.MaxPoint.Y,$box.MaxPoint.Z) -join ','))
    }
}
foreach($addin in $app.ApplicationAddIns) {
    if ($addin.DisplayName -match 'STEP|SolidWorks') {
        Write-Output ('Translator: ' + $addin.DisplayName + ' | ' + $addin.ClassIdString)
    }
}
