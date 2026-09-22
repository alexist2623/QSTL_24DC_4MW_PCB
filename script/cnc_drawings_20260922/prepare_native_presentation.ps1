$ErrorActionPreference='Stop'
Add-Type -Path 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application')
$model='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB\Mechanical_Assembly\Rod_Holder_Adapter_Drop8p5'
$out=Join-Path $model 'Manufacturing_DWG'
$tg=$app.TransientGeometry
$old=$app.SilentOperation;$app.SilentOperation=$true
function Matrix($x,$y,$z){$m=$tg.CreateMatrix();$m.SetTranslation($tg.CreateVector($x/10,$y/10,$z/10),$false);return $m}
try {
 $app.CommandManager.StopAllActiveCommands()
 foreach($d in @($app.Documents)){if($d.FullFileName -eq (Join-Path $out 'Split_Mount_Assembly.ipn')){$d.Close($true)}}
 $fast=$app.Documents.Add([Inventor.DocumentTypeEnum]::kAssemblyDocumentObject,$app.FileManager.GetTemplateFile([Inventor.DocumentTypeEnum]::kAssemblyDocumentObject),$false)
 foreach($x in @(9.5,41.5)){foreach($y in @(10,30,50,70)){$o=$fast.ComponentDefinition.Occurrences.Add((Join-Path $model 'Deck_M3x10_Countersunk.ipt'),(Matrix $x $y 0.1));$o.Grounded=$true}}
 $fast.SaveAs((Join-Path $out 'Eight_M3_Fasteners.iam'),$false)
 $a=$app.Documents.Add([Inventor.DocumentTypeEnum]::kAssemblyDocumentObject,$app.FileManager.GetTemplateFile([Inventor.DocumentTypeEnum]::kAssemblyDocumentObject),$false)
 foreach($part in @('Centre_Plate','Left_Rod_Support','Right_Rod_Support')){$o=$a.ComponentDefinition.Occurrences.Add((Join-Path $model ($part+'.ipt')),(Matrix 0 0 0));$o.Grounded=$true}
 $o=$a.ComponentDefinition.Occurrences.Add($fast.FullFileName,(Matrix 0 0 0));$o.Grounded=$true
 $a.SaveAs((Join-Path $out 'Split_Mount_Presentation_Source.iam'),$false)
 $p=$app.Documents.Add([Inventor.DocumentTypeEnum]::kPresentationDocumentObject,$app.FileManager.GetTemplateFile([Inventor.DocumentTypeEnum]::kPresentationDocumentObject),$false)
 $pub=$app.ApplicationAddIns.ItemById('{6E14DFA9-F418-4111-9F89-BA957482E98F}').Automation
 $pub.InsertModel($p,$p.Scenes.Item(1),$a.FullFileName)
 $p.SaveAs((Join-Path $out 'Split_Mount_Assembly.ipn'),$false)
 $p.Close($true)
 $p=$app.Documents.Open((Join-Path $out 'Split_Mount_Assembly.ipn'),$true)
 $cam=$app.ActiveView.Camera;$cam.Target=$tg.CreatePoint(2.55,4,0.5);$cam.Eye=$tg.CreatePoint(12,-8,-16);$cam.UpVector=$tg.CreateUnitVector(0,1,0);$cam.ApplyWithoutTransition();$app.ActiveView.Fit()
 $p.Save()
 Write-Output 'Native presentation prepared with one eight-screw subassembly and three machined parts.'
}finally{$app.SilentOperation=$old}
