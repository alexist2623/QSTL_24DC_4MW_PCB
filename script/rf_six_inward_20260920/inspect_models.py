from pathlib import Path
import sys,struct,json,zlib,copy,shutil
H=Path(__file__).resolve().parent;W=H.parent/'_support';P=Path(r'C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB');B='QSTL_24DC_4MW_PCB'
sys.path[:0]=[str(W/'qd_center_revision'),str(W/'final_routing/schematic')]
from native_metadata_helpers import properties,sha
from build_routed_copy import snapshot
def bodies(data,cs):
 pos=0;out=[]
 while pos<len(data):
  kind=data[pos];size=struct.unpack_from('<I',data,pos+1)[0]&0xffffff;b=data[pos+5:pos+5+size];pos+=5+size
  assert kind==12
  ci=struct.unpack_from('<H',b,7)[0];a=b.index(b'V7_LAYER=');nb=struct.unpack_from('<I',b,a-4)[0]&0xffffff;p=dict(x.split('=',1) for x in b[a:a+nb].rstrip(b'\0').decode('cp1252').split('|') if '=' in x)
  tail=b[a+nb:];cnt=struct.unpack_from('<I',tail)[0];pts=[list(struct.unpack_from('<2d',tail,4+i*16)) for i in range(cnt)] if len(tail)==4+cnt*16 else []
  out.append(dict(component=cs[ci]['SOURCEDESIGNATOR'] if ci!=65535 else None,props=p,outline_mm=[[x*2.54e-6,y*2.54e-6] for x,y in pts]))
 return out
s=snapshot(P/(B+'.PcbDoc'));cs=properties(s['Components6/Data']);out=bodies(s['ComponentBodies6/Data'],cs)
(H/'model_before.json').write_text(json.dumps(out,indent=2))
for r in out:
 if r['component'] in ['R1','C1','R5','C5']:print(json.dumps(r,indent=2))
print('Models',json.dumps(properties(s['Models/Data']),indent=2))
for i,m in enumerate(properties(s['Models/Data'])):
 if m.get('NAME','').lower().endswith(('.step','.stp')):
  raw=zlib.decompress(s['Models/'+str(i)]);(H/('embedded_'+str(i)+'.step')).write_bytes(raw)
for f in ['Passives_0603.PcbLib','Capacitors_0402.PcbLib']:
 lib=snapshot(P/f);print(f,'models=',properties(lib['Library/Models/Data']))
 if not (H/f).exists():shutil.copy2(P/f,H/f)
if not (H/'before_models.PcbDoc').exists():shutil.copy2(P/(B+'.PcbDoc'),H/'before_models.PcbDoc')
