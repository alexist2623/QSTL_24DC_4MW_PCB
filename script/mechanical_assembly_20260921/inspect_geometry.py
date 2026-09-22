"""Read imported solids and identify mechanical registration geometry."""
from pathlib import Path
import json
from OCP.STEPControl import STEPControl_Reader
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder, GeomAbs_Plane
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_FACE, TopAbs_SOLID
from OCP.TopoDS import TopoDS
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.BRepCheck import BRepCheck_Analyzer

HERE=Path(__file__).resolve().parent
OUT=HERE.parents[1]/'QSTL_24DC_4MW_PCB'/'Mechanical_Assembly'

def read(path):
    reader=STEPControl_Reader()
    assert int(reader.ReadFile(str(path)))==1
    assert reader.TransferRoots()>0
    return reader.OneShape()

def bounds(shape):
    b=Bnd_Box();BRepBndLib.AddOptimal_s(shape,b,False,False)
    lo,hi=b.CornerMin(),b.CornerMax()
    return [lo.X(),lo.Y(),lo.Z(),hi.X(),hi.Y(),hi.Z()]

def faces(shape):
    e=TopExp_Explorer(shape,TopAbs_FACE)
    while e.More():
        yield TopoDS.Face(e.Current());e.Next()

def volume(shape):
    g=GProp_GProps();BRepGProp.VolumeProperties_s(shape,g);return g.Mass()

def inspect(shape):
    cylinders=[];planes=[]
    for f in faces(shape):
        a=BRepAdaptor_Surface(f)
        if a.GetType()==GeomAbs_Cylinder:
            c=a.Cylinder();d=c.Axis().Direction();p=c.Location()
            cylinders.append(dict(radius=c.Radius(),point=[p.X(),p.Y(),p.Z()],axis=[d.X(),d.Y(),d.Z()],bounds=bounds(f)))
        elif a.GetType()==GeomAbs_Plane:
            p=a.Plane();n=p.Axis().Direction();o=p.Location()
            g=GProp_GProps();BRepGProp.SurfaceProperties_s(f,g)
            planes.append(dict(point=[o.X(),o.Y(),o.Z()],normal=[n.X(),n.Y(),n.Z()],area=g.Mass(),bounds=bounds(f)))
    return dict(bounds=bounds(shape),volume=volume(shape),valid=BRepCheck_Analyzer(shape).IsValid(),cylinders=cylinders,planes=planes)

if __name__=='__main__':
    data={}
    for path in list(OUT.glob('*_reference.step'))+list((HERE/'embedded_models').glob('*.step')):
        report=inspect(read(path));data[path.name]=report
        print(path.name,'bounds',report['bounds'],'vol',report['volume'])
        if '_reference' in path.name:
            print('CYLINDERS',json.dumps(report['cylinders']))
            print('PLANES',json.dumps(sorted(report['planes'],key=lambda r:-r['area'])[:12]))
    (HERE/'solid_geometry.json').write_text(json.dumps(data,indent=2))
    pcb=json.loads((HERE/'pcb_geometry.json').read_text())
    print('PCB_SHA',pcb['pcb_sha256'])
    print('STACK', {k:v for k,v in pcb['board'][0].items() if any(w in k for w in ('THICK','V7_','LAYERSTACK'))})
