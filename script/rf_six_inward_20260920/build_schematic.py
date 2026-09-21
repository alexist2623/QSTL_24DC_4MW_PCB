from pathlib import Path
import sys,json,copy
H=Path(__file__).resolve().parent;W=H.parent/'_support';B='QSTL_24DC_4MW_PCB';D=H/'built_no_transition';D.mkdir(exist_ok=True)
sys.path[:0]=[str(W/'zif_revision_v2/schematic'),str(W/'zif_revision/schematic'),str(W/'qd_center_revision')]
import build_zif_schematic as base
import build_v2_schematic as helper
from cfb_copy_update import update_copy
from native_metadata_helpers import olefile,sha
g=json.loads((H/'geometry.json').read_text());e=json.loads((W/'dc_direct_20260920/expected.json').read_text())
pn={k:v for k,v in g['pin_nets'].items() if v is not None};nc=sorted(k for k,v in g['pin_nets'].items() if v is None)
e.update(pin_net_map=pn,nc_pins=nc,nets={},rf_qd_map=g['rf_qd_map'],zif_to_target=g['zif_to_target'])
for key,net in pn.items():e['nets'].setdefault(net,[]).append(key)
e['rf_bias_zif_pins']={ch:next(z for z,t in g['zif_to_target'].items() if t==f'R{ch}-2') for ch in g['rf_qd_map']}
e['counts']=dict(components=22,pins=141,connected_pins=len(pn),NC_pins=len(nc),named_nets=len(e['nets']))
assert (len(pn),len(nc),len(e['nets']))==(110,31,37)
e['PCB_expected_counts']=dict(components=22,pads=147,named_nets=37);e['native_compiled_expected_net_count']=68
e['source_hashes']={str(H/(B+ext)):sha(H/(B+ext)) for ext in ['.PcbDoc','.SchDoc','.SchLib','.PrjPcb','.PcbLib']}
rs=base.records(H/(B+'.SchDoc'));groups=base.component_groups(rs)
out=[copy.deepcopy(rs[0])]+[copy.deepcopy(r) for r in rs[1:] if r.get('RECORD')=='31' or (r.get('RECORD')=='41' and r.get('OwnerIndex') in (None,'0'))]
for r in out:
 if r.get('Name')=='Title':r['Text']='QSTL carrier - RF6 + DC18; QD/R/C Bottom'
for ref,group in groups.items():helper.append_group(out,group,ref,pn,B+'.SchLib',B+'.PcbLib')
for r in out:
 if r.get('RECORD')=='1' and r.get('LibReference')=='QD4':r['ComponentDescription']='QD24; RF pins1,6,9,12,18,24; DC18'
 if r.get('Name')=='Layout status':r['Text']='RF6/DC18; QD/R/C Bottom; inline RF resistor pad; via in pad'
pins=base.append_connections(out,pn,nc)
notes=[('RF6 + DC18. QD RF pins: 1, 6, 9, 12, 18, 24. SMP1-6 active; SMP7-8 signal NC.',100,960),('QD/R/C Bottom. ZIF/SMP Top. R/C rotated inward; RF path passes through resistor RF pad.',100,930),('QD-side stack: RF / GND / DC / GND / DC / GND. DC mapping follows physical routing.',100,900),('J1 uses pins1-12 and15-26 only. Six plated GND mounting holes are PCB-only.',100,870)]
for i,(txt,x,y) in enumerate(notes):out.append(dict(RECORD='4',OwnerPartId='-1',**{'Location.X':str(x),'Location.Y':str(y)},FontID='4',Color='128',Text=txt,UniqueID=helper.uid('RF6note'+str(i))))
out[0]['Weight']=str(len(out)-1)
update_copy(H/(B+'.SchDoc'),D/(B+'.SchDoc'),{'FileHeader':base.pack([(0,base.encode(r)) for r in out])})
with olefile.OleFileIO(H/(B+'.SchLib')) as o:rows=base.blocks(o.openstream('QD4/Data').read())
new=[]
for flag,b in rows:
 if flag==1:
  assert b[0]==2;pos=27+b[26];number=b[pos+1:pos+1+b[pos]].decode('ascii');name=pn['Q1-'+number].encode('ascii');b=b[:26]+bytes([len(name)])+name+b[pos:]
 new.append((flag,b))
update_copy(H/(B+'.SchLib'),D/(B+'.SchLib'),{'QD4/Data':base.pack(new)})
e['pins']=pins
(H/'expected.json').write_text(json.dumps(e,indent=2))
ns={'__file__':str(W/'zif_revision_v2/schematic/validate_v2_schematic.py'),'__name__':'rf6_validator'};exec(compile((H/'validator_source.py').read_text(),ns['__file__'],'exec'),ns)
report=ns['validate'](D/(B+'.SchDoc'),e);(H/'schematic_preflight.json').write_text(json.dumps(report,indent=2));assert report['passed'],report['errors']
print(json.dumps(dict(passed=True,counts=report['counts'],rf_bias_zif=e['rf_bias_zif_pins']),indent=2))
