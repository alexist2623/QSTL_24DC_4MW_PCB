"""Read source STEP solids and validate drawing dimensions against saved CAD."""
from pathlib import Path
import sys, json, hashlib
import numpy as np
from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape
from OCP.HLRAlgo import HLRAlgo_Projector
from OCP.gp import gp_Ax2, gp_Pnt, gp_Dir
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_EDGE
from OCP.TopoDS import TopoDS
from OCP.GeomAbs import GeomAbs_Line

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'script'/'mechanical_assembly_20260921'))
from inspect_geometry import read,inspect
MODEL=ROOT/'QSTL_24DC_4MW_PCB'/'Mechanical_Assembly'/'Rod_Holder_Adapter_Drop8p5'
HERE=Path(__file__).resolve().parent

def project(shape, origin, normal, right):
    algo=HLRBRep_Algo();algo.Add(shape)
    algo.Projector(HLRAlgo_Projector(gp_Ax2(gp_Pnt(*origin),gp_Dir(*normal),gp_Dir(*right))))
    algo.Update();algo.Hide();hlr=HLRBRep_HLRToShape(algo)
    result={}
    for kind, names in [('visible',['VCompound','OutLineVCompound']),('hidden',['HCompound','OutLineHCompound'])]:
        result[kind]=[]
        for name in names:
            edges=getattr(hlr,name)()
            if edges.IsNull():continue
            ex=TopExp_Explorer(edges,TopAbs_EDGE)
            while ex.More():
                curve=BRepAdaptor_Curve(TopoDS.Edge(ex.Current()))
                count=2 if curve.GetType()==GeomAbs_Line else 73
                pts=[]
                for u in np.linspace(curve.FirstParameter(),curve.LastParameter(),count):
                    p=curve.Value(float(u));pts.append([p.X(),p.Y()])
                result[kind].append(pts);ex.Next()
    return result

def main():
    result={}
    for name, origin, expected in [
        ('Centre_Plate',[6,0,0],[6,0,0,45,80,10]),
        ('Left_Rod_Support',[0,0,4],[0,0,4,12,80,12.5]),
        ('Right_Rod_Support',[39,0,4],[39,0,4,51,80,12.5])]:
        path=MODEL/(name+'.step');shape=read(path);info=inspect(shape)
        assert info['valid'] and np.allclose(info['bounds'],expected,atol=1e-7)
        views={}
        for view, normal, right in [
            ('xy_boss',[0,0,1],[1,0,0]),
            ('xy_outer',[0,0,-1],[1,0,0]),
            ('end',[0,-1,0],[1,0,0]),
            ('side',[1,0,0],[0,1,0]),
            ('iso',[1,-1,1],[1,1,0])]:
            views[view]=project(shape,origin,normal,right)
        result[name]=dict(origin_model_mm=origin,geometry=info,projections=views,
                          sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    centre=result['Centre_Plate']['geometry']
    axial=[h for h in centre['cylinders'] if abs(h['axis'][2])>.99]
    assert len(axial)==8 and all(abs(h['radius']-1.7)<1e-7 for h in axial)
    assert np.allclose(sorted(set(round(h['point'][0]-6,8) for h in axial)),[3.5,35.5])
    assert np.allclose(sorted(set(round(h['point'][1],8) for h in axial)),[10,30,50,70])
    sides=[h for h in centre['cylinders'] if abs(h['axis'][0])>.99]
    assert len(sides)==10 and all(abs(h['radius']-1.25)<1e-7 for h in sides)
    assert np.allclose(sorted(set(round(h['point'][1],8) for h in sides)),[9.82802367,25.82802367,41.82802367,57.82802367,73.82802367])
    for name, clearance_x, tap_x in [('Left_Rod_Support',3,9.5),('Right_Rod_Support',9,2.5)]:
        info=result[name]['geometry'];ox=result[name]['origin_model_mm'][0]
        for radius,n,x,ys in [(1.7,4,clearance_x,[5,25,45,65]),(1.25,4,tap_x,[10,30,50,70])]:
            holes=[h for h in info['cylinders'] if abs(h['radius']-radius)<1e-7]
            assert len(holes)==n
            assert all(abs(h['point'][0]-ox-x)<1e-7 for h in holes)
            assert np.allclose(sorted(h['point'][1] for h in holes),ys)
    (HERE/'drawing_geometry.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('Validated three STEP solids and all 34 hole locations; exported exact hidden-line projections.')
if __name__=='__main__':main()
