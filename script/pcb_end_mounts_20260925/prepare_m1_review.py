"""Export current PCB end, embedded connector and dimensional cable envelopes."""
from pathlib import Path
import sys,json,struct,zlib,math
H=Path(__file__).resolve().parent;R=H.parents[1];P=R/'QSTL_24DC_4MW_PCB';W=H.parent/'_support'
sys.path[:0]=[str(W/x) for x in ('qd_center_revision','final_routing/schematic')]+[str(H.parent/'mechanical_assembly_20260921')]
from native_metadata_helpers import properties,pads_stream,binary_records,UNIT,sha
from build_routed_copy import snapshot
from inspect_geometry import read,bounds,volume
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox,BRepPrimAPI_MakeCylinder
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.gp import gp_Pnt,gp_Vec,gp_Trsf,gp_Ax1,gp_Ax2,gp_Dir
from OCP.STEPControl import STEPControl_Writer,STEPControl_AsIs

out=P/'Mechanical_Assembly/ZIF_M1_Review';out.mkdir(parents=True,exist_ok=True)
s=snapshot(P/'QSTL_24DC_4MW_PCB.PcbDoc');cs=properties(s['Components6/Data']);ps=pads_stream(s['Pads6/Data']);models=properties(s['Models/Data'])
ci=next(i for i,c in enumerate(cs) if c['SOURCEDESIGNATOR']=='J1')
body=None
for row in binary_records(s['ComponentBodies6/Data'],12):
 raw=row['body']
 if struct.unpack_from('<H',raw,7)[0]!=ci:continue
 a=raw.index(b'V7_LAYER=');n=struct.unpack_from('<I',raw,a-4)[0]&0xffffff
 body=dict(x.split('=',1) for x in raw[a:a+n].rstrip(b'\0').decode('cp1252').split('|') if '=' in x);break
assert body is not None
mi=next(i for i,m in enumerate(models) if m['ID']==body['MODELID'])
embedded=out/'J1_embedded.step';embedded.write_bytes(zlib.decompress(s[f'Models/{mi}']))
def mm(v):return float(v.removesuffix('mil'))*.0254
def export(shape,name):
 w=STEPControl_Writer();w.Transfer(shape,STEPControl_AsIs);assert int(w.Write(str(out/(name+'.step'))))==1
 return {'name':name,'bounds_mm':bounds(shape),'volume_mm3':volume(shape)}
t=gp_Trsf();t.SetRotation(gp_Ax1(gp_Pnt(0,0,0),gp_Dir(1,0,0)),math.pi/2)
assert float(body['MODEL.3D.ROTX'])==90 and float(body['MODEL.3D.ROTY'])==float(body['MODEL.3D.ROTZ'])==0
t.SetTranslationPart(gp_Vec(mm(body['MODEL.2D.X']),mm(body['MODEL.2D.Y']),1.6+mm(body['MODEL.3D.DZ'])))
connector=BRepBuilderAPI_Transform(read(embedded),t,True).Shape()
board=BRepPrimAPI_MakeBox(gp_Pnt(0,0,0),19.5,10,1.6).Shape()
mounts=[]
for p in ps:
 x,y=p['coords'][0]*UNIT,p['coords'][1]*UNIT;hole=p['coords'][8]*UNIT
 if p['number'] in ('MH7','MH8'):mounts.append({'name':p['number'],'x':x,'y':y,'drill':hole})
 if hole>0 and y<10:board=BRepAlgoAPI_Cut(board,BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(x,y,-1),gp_Dir(0,0,1)),hole/2,4).Shape()).Shape()
# Cable envelope follows the manufacturer-recommended 51-contact end:
# 0.3*(N+1)=15.6 mm width and 0.20 +/-0.03 mm reinforced end thickness.
# Model only the free cable before the housing; mating-contact overlap is excluded.
# Cable center height 0.47 mm above the PCB is an unverified placement assumption.
entry_y=bounds(connector)[1]
cable=BRepPrimAPI_MakeBox(gp_Pnt(1.95,-10,1.6+.37),15.6,entry_y+10,.20).Shape()
reports=[export(board,'PCB_End'),export(connector,'J1_Current'),export(cable,'FPC_51_0p3_Envelope')]
data={'pcb_sha256':sha(P/'QSTL_24DC_4MW_PCB.PcbDoc'),'body':body,'mounts':mounts,'parts':reports,
 'connector':'Molex 502598-5193','source':'https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/salesdrawingpdf/502/502598/5025983993_sd.pdf',
 'cable':{'status':'dimensional fit envelope, not a detailed routed production cable','width_mm':15.6,'reinforced_thickness_mm':.2,'free_end_y_mm':entry_y,'nominal_centre_above_pcb_mm':.47,'placement_assumption':'centred on manufacturer cable reference; verify on section drawing'},
 'screw_head_cable_contact_permitted':True}
(out/'model_inputs.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
print(json.dumps(data,indent=2))
