$ErrorActionPreference='Stop'
Add-Type -Path 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application');$cd=$app.ActiveDocument.ComponentDefinition
Write-Output ('Threads: '+$cd.Features.ThreadFeatures.Count)
foreach ($f in $cd.SurfaceBodies.Item(1).Faces) {
    if ($f.SurfaceType -eq [Inventor.SurfaceTypeEnum]::kCylinderSurface -and [Math]::Abs($f.Geometry.AxisVector.X) -gt .99) {
        Write-Output ('FACE radius='+$f.Geometry.Radius+' x='+$f.Geometry.BasePoint.X+' y='+$f.Geometry.BasePoint.Y)
        foreach($e in $f.Edges) {Write-Output ('EDGE type='+$e.GeometryType+' minx='+$e.RangeBox.MinPoint.X+' maxx='+$e.RangeBox.MaxPoint.X)}
    }
}
