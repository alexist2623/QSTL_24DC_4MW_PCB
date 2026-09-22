$ErrorActionPreference='Stop'
Add-Type -Path 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application')
$out='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB\Mechanical_Assembly\Rod_Holder_Adapter_Drop8p5\Manufacturing_DWG'
$p=$app.Documents.Add([Inventor.DocumentTypeEnum]::kPresentationDocumentObject,$app.FileManager.GetTemplateFile([Inventor.DocumentTypeEnum]::kPresentationDocumentObject),$true)
$p.SaveAs((Join-Path $out 'Split_Mount_Assembly.ipn'),$false)
$p.Activate()
Write-Output $p.FullFileName
