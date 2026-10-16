"""Fit circular bore sections in the supplied assembly STL without editing it."""
from pathlib import Path
import json
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy
HERE=Path(__file__).resolve().parent
SOURCE=Path('F:/Nextcloud/Lab/Instruments/CustomParts/Carrier_12MW_72DC/Mechanical/Assembly1.stl')
reader=vtk.vtkSTLReader();reader.SetFileName(str(SOURCE));reader.Update()
scale=vtk.vtkTransform();scale.Scale(1000,1000,1000)
trans=vtk.vtkTransformPolyDataFilter();trans.SetInputConnection(reader.GetOutputPort());trans.SetTransform(scale);trans.Update()
mesh=trans.GetOutput()
count=vtk.vtkPolyDataConnectivityFilter();count.SetInputData(mesh);count.SetExtractionModeToAllRegions();count.Update()
results=[]
for index in range(count.GetNumberOfExtractedRegions()):
    conn=vtk.vtkPolyDataConnectivityFilter();conn.SetInputData(mesh);conn.SetExtractionModeToSpecifiedRegions();conn.AddSpecifiedRegion(index);conn.Update()
    clean=vtk.vtkCleanPolyData();clean.SetInputConnection(conn.GetOutputPort());clean.Update();part=clean.GetOutput()
    w=vtk.vtkXMLPolyDataWriter();w.SetFileName(str(HERE/f'mesh_region_{index}.vtp'));w.SetInputData(part);w.Write()
    b=part.GetBounds();zs=np.unique(np.round(vtk_to_numpy(part.GetPoints().GetData())[:,2],5))
    sections=[]
    sample_z=sorted(set([b[4]+.05,b[5]-.05]+[(a+c)/2 for a,c in zip(zs[:-1],zs[1:]) if c-a>.2]))
    for z in sample_z:
        plane=vtk.vtkPlane();plane.SetOrigin(0,0,z);plane.SetNormal(0,0,1)
        cut=vtk.vtkCutter();cut.SetInputData(part);cut.SetCutFunction(plane);cut.Update()
        strip=vtk.vtkStripper();strip.SetInputConnection(cut.GetOutputPort());strip.JoinContiguousSegmentsOn();strip.Update()
        curves=strip.GetOutput();circles=[];others=[]
        for i in range(curves.GetNumberOfCells()):
            cell=curves.GetCell(i)
            pts=np.array([curves.GetPoint(cell.GetPointId(j))[:2] for j in range(cell.GetNumberOfPoints())])
            if len(pts)<6:
                others.append(dict(bounds=np.r_[pts.min(axis=0),pts.max(axis=0)].tolist(),points=len(pts)))
                continue
            coeff=np.linalg.lstsq(np.column_stack([2*pts[:,0],2*pts[:,1],np.ones(len(pts))]),(pts**2).sum(axis=1),rcond=None)[0]
            centre=coeff[:2];r=np.sqrt(max(0,coeff[2]+sum(centre**2)))
            residual=max(abs(np.linalg.norm(pts-centre,axis=1)-r))
            if residual<.025 and r<10:
                circles.append(dict(centre_xy_mm=centre.tolist(),diameter_mm=float(2*r),fit_residual_mm=float(residual),count=len(pts)))
            else:others.append(dict(bounds=np.r_[pts.min(axis=0),pts.max(axis=0)].tolist(),points=len(pts)))
        sections.append(dict(z_mm=float(z),circles=circles,other_loops=others))
    result=dict(region=index,bounds_mm=list(b),z_levels=zs.tolist(),sections=sections)
    results.append(result)
    print(json.dumps(result,indent=2),flush=True)
(HERE/'mesh_bore_sections.json').write_text(json.dumps(results,indent=2)+'\n')
