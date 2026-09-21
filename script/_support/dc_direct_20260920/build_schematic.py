from pathlib import Path
import sys,json,copy,collections
H=Path(__file__).resolve().parent;W=H.parent;B='QSTL_24DC_4MW_PCB';D=H/'built';D.mkdir(exist_ok=True)
sys.path[:0]=[str(W/'zif_revision_v2/schematic'),str(W/'zif_revision/schematic'),str(W/'qd_center_revision')]
import build_zif_schematic as base
from cfb_copy_update import update_copy
from native_metadata_helpers import olefile,sha
dc=json.loads((H/'dc_routes.json').read_text());e=json.loads((W/'dc_centered_20260920/expected.json').read_text());changes=dc['pin_changes']
rs=base.records(H/(B+'.SchDoc'));before=copy.deepcopy(rs)
designators={i-1:next(r['Text'] for j,r in base.component_groups(rs)[ref] if r.get('RECORD')=='34') for ref in base.component_groups(rs) for i in []}
designators={int(r['OwnerIndex']):r['Text'] for r in rs if r.get('RECORD')=='34'}
def xy(r):return tuple(int(r.get('Location.'+c,'0'))+int(r.get('Location.'+c+'_Frac','0'))/100000 for c in 'XY')
for key,c in changes.items():
 pin=next(r for r in rs if r.get('RECORD')=='2' and designators[int(r['OwnerIndex'])]+'-'+r['Designator']==key)
 direction=int(pin.get('PinConglomerate','0'))&3;dx,dy=((1,0),(0,1),(-1,0),(0,-1))[direction];x,y=xy(pin);tip=(x+dx*int(pin['PinLength']),y+dy*int(pin['PinLength']))
 wires=[r for r in rs if r.get('RECORD')=='27' and tip in [(int(r['X'+str(i)]),int(r['Y'+str(i)])) for i in range(1,int(r['LocationCount'])+1)]]
 assert len(wires)==1;wire=wires[0];endpoints=[(int(wire['X'+str(i)]),int(wire['Y'+str(i)])) for i in range(1,int(wire['LocationCount'])+1)]
 labels=[r for r in rs if r.get('RECORD')=='25' and xy(r) in endpoints];assert len(labels)==1 and labels[0]['Text']==c['old'];labels[0]['Text']=c['new']
 if key.startswith('Q1-'):assert pin['Name']==c['old'];pin['Name']=c['new']
 e['pin_net_map'][key]=c['new']
e['nets']={}
for key,net in e['pin_net_map'].items():e['nets'].setdefault(net,[]).append(key)
e['zif_to_target']=dc['zif_to_target'];e['rf_bias_zif_pins']={str(k):next(z for z,t in dc['zif_to_target'].items() if t==f'R{k}-2') for k in range(1,5)}
e['source_hashes']={str(H/(B+'.SchDoc')):sha(H/(B+'.SchDoc'))}
update_copy(H/(B+'.SchDoc'),D/(B+'.SchDoc'),{'FileHeader':base.pack([(0,base.encode(r)) for r in rs])})
with olefile.OleFileIO(H/(B+'.SchLib')) as o:rows=base.blocks(o.openstream('QD4/Data').read())
new=[];lib_changes=[]
for flag,b in rows:
 if flag==1:
  assert b[0]==2;n=27+b[26];number=b[n+1:n+1+b[n]].decode('ascii');key='Q1-'+number
  if key in changes:
   assert b[27:27+b[26]].decode('ascii')==changes[key]['old'];name=changes[key]['new'].encode('ascii');b=b[:26]+bytes([len(name)])+name+b[n:];lib_changes.append(key)
 new.append((flag,b))
assert sorted(lib_changes)==['Q1-2','Q1-3']
update_copy(H/(B+'.SchLib'),D/(B+'.SchLib'),{'QD4/Data':base.pack(new)})
assert sum(a!=b for a,b in zip(before,rs))==5
(H/'expected.json').write_text(json.dumps(e,indent=2))
g=json.loads((W/'dc_centered_20260920/geometry.json').read_text());g['pin_nets'].update({k:v['new'] for k,v in changes.items()})
for p in g['pads']:
 key=p['component']+'-'+p['number']
 if key in changes:p['net']=changes[key]['new']
for attr in ['fanout_vias','via_moves']:
 for v in g.get(attr,[]):
  if v.get('pin') in changes:v['net']=changes[v['pin']]['new']
for key,v in g['endpoints'].items():
 if key in changes:v['net']=changes[key]['new']
(H/'geometry.json').write_text(json.dumps(g,indent=2))
ns={'__file__':str(W/'zif_revision_v2/schematic/validate_v2_schematic.py'),'__name__':'direct_validator'};exec(compile((H/'validator_source.py').read_text(),ns['__file__'],'exec'),ns)
report=ns['validate'](D/(B+'.SchDoc'),e);(H/'schematic_preflight.json').write_text(json.dumps(report,indent=2));assert report['passed'],report['errors']
print(json.dumps(dict(passed=True,changed_records=5,library_pin_names=lib_changes,pin_changes=changes,counts=report['counts']),indent=2))
