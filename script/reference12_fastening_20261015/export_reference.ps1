$ErrorActionPreference='Stop'
$repoRoot=Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$sourceRoot='F:\Nextcloud\Lab\Instruments\CustomParts\Carrier_12MW_72DC\Mechanical'
$out=Join-Path $repoRoot 'QSTL_QD4_2SET_38PAD\Reference12_Fastening_20261015'
$null=New-Item -ItemType Directory -Path $out -Force
Add-Type -Path 'F:\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
$created=$false
try{$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application')}
catch{$app=New-Object -ComObject Inventor.Application;$app.Visible=$false;$created=$true}
$oldSilent=$app.SilentOperation
$doc=$null
$report=@()
try {
 $app.SilentOperation=$true
 Write-Output ('Inventor '+$app.SoftwareVersion.DisplayVersion+' connected')
 $step=$app.ApplicationAddIns.ItemById('{90AF7F40-0C01-11D5-8E83-0010B541CD80}')
 $step.Activate()
 foreach($name in @('CuBoxBottom_12MW_72DC','CuBoxTop_12MW_72DC')){
  $source=Join-Path $sourceRoot ($name+'.sldprt')
  $hash=(Get-FileHash -LiteralPath $source).Hash
  $template=$app.FileManager.GetTemplateFile([Inventor.DocumentTypeEnum]::kPartDocumentObject)
  $doc=$app.Documents.Add([Inventor.DocumentTypeEnum]::kPartDocumentObject,$template,$false)
  $imports=$doc.ComponentDefinition.ReferenceComponents.ImportedComponents
  $definition=$imports.CreateDefinition($source)
  $definition.ReferenceModel=$true
  $definition.ImportedModelGeometryTypes=[Inventor.ImportedModelGeometryTypeEnum]::kSolidsModelGeometryType -bor [Inventor.ImportedModelGeometryTypeEnum]::kSurfacesModelGeometryType
  $definition.IncludeAll()
  Write-Output ('Definition type='+$definition.Type+' geometry='+$definition.ImportedModelGeometryTypes+' entities='+$definition.ImportedModelEntities.Count)
  function Show-Entities($items,$level){foreach($entity in $items){Write-Output ('  '*$level+$entity.Name+' type='+$entity.EntityType+' status='+$entity.ImportedStatus+' children='+$entity.SubEntities.Count);if($entity.SubEntities.Count -gt 0){Show-Entities $entity.SubEntities ($level+1)}}}
  Show-Entities $definition.ImportedModelEntities 0
  Write-Output ('Importing '+$name)
  $imported=$imports.Add($definition)
  $null=$doc.Update2($true)
  Write-Output ('Import health='+$imported.HealthStatus+' bodies='+$doc.ComponentDefinition.SurfaceBodies.Count)
  if($doc.ComponentDefinition.SurfaceBodies.Count -lt 1){
   $doc.Close($true)
   Write-Output 'Trying direct document translator'
   $doc=$app.Documents.Open($source,$false)
   $null=$doc.Update2($true)
  }
  if($doc.ComponentDefinition.SurfaceBodies.Count -lt 1){throw 'No imported solid bodies from either import path'}
  $doc.SaveAs((Join-Path $out ($name+'_review.ipt')),$false)
  $context=$app.TransientObjects.CreateTranslationContext()
  $context.Type=[Inventor.IOMechanismEnum]::kFileBrowseIOMechanism
  $options=$app.TransientObjects.CreateNameValueMap()
  $null=$step.HasSaveCopyAsOptions($doc,$context,$options)
  $options.Value('ApplicationProtocolType')=3
  $medium=$app.TransientObjects.CreateDataMedium()
  $medium.FileName=Join-Path $out ($name+'_reference.step')
  $step.SaveCopyAs($doc,$context,$options,$medium)
  $box=$doc.ComponentDefinition.RangeBox
  $record=[ordered]@{name=$name;source=$source;source_sha256=$hash;bodies=$doc.ComponentDefinition.SurfaceBodies.Count;bounds_mm=@(($box.MinPoint.X*10),($box.MinPoint.Y*10),($box.MinPoint.Z*10),($box.MaxPoint.X*10),($box.MaxPoint.Y*10),($box.MaxPoint.Z*10));native_hole_features=$doc.ComponentDefinition.Features.HoleFeatures.Count;native_thread_features=$doc.ComponentDefinition.Features.ThreadFeatures.Count;step=$medium.FileName}
  $report+=$record
  $doc.Close($true);$doc=$null
  if((Get-FileHash -LiteralPath $source).Hash -ne $hash){throw 'Reference changed'}
  Write-Output ('Exported '+$name)
 }
 $report|ConvertTo-Json -Depth 8|Set-Content -LiteralPath (Join-Path $out 'reference_import.json') -Encoding UTF8
 $report|ConvertTo-Json -Depth 8|Write-Output
}finally{
 if($doc){$doc.Close($true)}
 $app.SilentOperation=$oldSilent
 if($created){$app.Quit()}
}
