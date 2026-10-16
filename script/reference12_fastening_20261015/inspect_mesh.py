"""Render supplied assembly mesh as a read-only fallback reference."""
from pathlib import Path
import json
import vtk
HERE=Path(__file__).resolve().parent
SOURCE=Path('F:/Nextcloud/Lab/Instruments/CustomParts/Carrier_12MW_72DC/Mechanical/Assembly1.stl')

reader=vtk.vtkSTLReader();reader.SetFileName(str(SOURCE));reader.Update()
mesh=reader.GetOutput()
connect=vtk.vtkPolyDataConnectivityFilter();connect.SetInputData(mesh);connect.SetExtractionModeToAllRegions();connect.Update()
print(json.dumps(dict(bounds=mesh.GetBounds(),regions=connect.GetNumberOfExtractedRegions())),flush=True)
mapper=vtk.vtkPolyDataMapper();mapper.SetInputData(mesh)
actor=vtk.vtkActor();actor.SetMapper(mapper);actor.GetProperty().SetColor(.72,.43,.27)
render=vtk.vtkRenderer();render.SetBackground(1,1,1);render.AddActor(actor)
window=vtk.vtkRenderWindow();window.SetOffScreenRendering(1);window.SetSize(1600,1200);window.AddRenderer(render)
camera=render.GetActiveCamera();camera.SetPosition(0,0,1);camera.SetFocalPoint(0,0,0);camera.SetViewUp(0,1,0);camera.ParallelProjectionOn();render.ResetCamera()
window.Render()
pixels=vtk.vtkWindowToImageFilter();pixels.SetInput(window);pixels.ReadFrontBufferOff();pixels.Update()
writer=vtk.vtkPNGWriter();writer.SetFileName(str(HERE/'Supplied_Assembly_STL.png'));writer.SetInputConnection(pixels.GetOutputPort());writer.Write()
window.Finalize()
