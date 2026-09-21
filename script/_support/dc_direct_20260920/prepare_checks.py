from pathlib import Path
import sys,json,collections,hashlib
H=Path(__file__).resolve().parent;W=H.parent;OLD=W/'dc_centered_20260920';P=Path(r'C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB');B='QSTL_24DC_4MW_PCB'
sys.path[:0]=[str(W/'qd_center_revision'),str(W/'final_routing/schematic'),str(W/'zif_revision_v2/board')]
from native_metadata_helpers import properties,pads_stream,sha
from build_routed_copy import snapshot
from verify_final_native_v2 import read_route,trackkey,arckey,viakey
s=snapshot(P/(B+'.PcbDoc'));old=snapshot(H/(B+'.PcbDoc'));ns=properties(s['Nets6/Data']);ts,ars,vs=read_route(s,ns);ots,oars,ovs=read_route(old,ns)
for stream in ['Components6/Data','Nets6/Data','BoardRegions/Data']:assert s[stream]==old[stream],stream+' changed'
for ext in ['.PcbLib','.PrjPcb']:assert (P/(B+ext)).read_bytes()==(H/(B+ext)).read_bytes(),ext+' changed'
assert collections.Counter(map(trackkey,[t for t in ts if t['layer'] in [1,32]]))==collections.Counter(map(trackkey,[t for t in ots if t['layer'] in [1,32]]))
assert collections.Counter(map(arckey,ars))==collections.Counter(map(arckey,oars))
assert all(t['V7']==(0x0100ffff if t['layer']==32 else 0x01000000+t['layer']) for t in ts+ars)
ps=pads_stream(s['Pads6/Data']);ops=pads_stream(old['Pads6/Data']);cs=properties(s['Components6/Data']);plan=json.loads((H/'dc_routes.json').read_text());changes=plan['pin_changes'];applied=[]
for p,o in zip(ps,ops):
 assert p['coords']==o['coords'] and p['rotation']==o['rotation'] and p['layer']==o['layer']
 if p['net']!=o['net']:
  key=cs[p['component']]['SOURCEDESIGNATOR']+'-'+p['number'];assert key in changes
  assert ns[p['net']]['NAME']==changes[key]['new'] and ns[o['net']]['NAME']==changes[key]['old'];applied.append(key)
assert sorted(applied)==sorted(changes)
assert len(vs)==len(ovs)==65
vchanges=0
for v,o in zip(vs,ovs):
 assert all(v[k]==o[k] for k in ['x','y','diameter','hole','start_layer','end_layer'] if k in v)
 if v['net']!=o['net']:
  p=next(p for p in ps if abs(p['coords'][0]*2.54e-6-v['x'])<1e-5 and abs(p['coords'][1]*2.54e-6-v['y'])<1e-5);key=cs[p['component']]['SOURCEDESIGNATOR']+'-'+p['number'];assert v['net']==changes[key]['new'] and o['net']==changes[key]['old'];vchanges+=1
assert vchanges==3
bd=properties(s['Board6/Data'])[0];obd=properties(old['Board6/Data'])[0];assert {k:v for k,v in bd.items() if 'STACK' in k}=={k:v for k,v in obd.items() if 'STACK' in k}
report=dict(passed=True,pcb_sha256=sha(P/(B+'.PcbDoc')),fixed_component_placement_pads_stack_RF_unchanged=True,pad_net_changes=changes,via_net_changes=vchanges,vias_added=0,tracks_by_layer=dict(collections.Counter(t['layer'] for t in ts)),internal_DC_segments_before=sum(t['layer'] in [2,4] for t in ots),internal_DC_segments_after=sum(t['layer'] in [2,4] for t in ts))
(H/'preservation_validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
for name in ['verify_native.py','verify_angles.py','verify_stubless.py','render_rf_only.py','render_dc_only.py','render_overviews.py','render_placement_detail.py','render_layers.py']:
 code=(OLD/name).read_text(encoding='utf-8')
 if name=='verify_native.py':code=code.replace('DC_centered_DRC.html','DC_direct_DRC.html').replace('symmetric_schematic_compile.txt','dc_direct_schematic_compile.txt')
 if name=='verify_stubless.py':
  code=code.replace("check({(p['component'],p['number']):p['net'] for p in old['pads']}=={(p['component'],p['number']):p['net'] for p in n['pads']},'Pin assignments changed')","expected=json.loads((H/'expected.json').read_text())['pin_net_map']\ncheck(all(p['net']==expected.get(p['component']+'-'+p['number']) for p in n['pads'] if p['component']),'Pin assignments differ from synchronized schematic')")
  code=code.replace("['.SchDoc','.PcbLib','.PrjPcb']","['.PcbLib','.PrjPcb']").replace('electrical_pin_map_unchanged=True,schematic_and_library_unchanged=True','RF_pin_map_unchanged=True,DC_pin_map_updated_in_schematic_and_library=True')
 if name=='render_dc_only.py':code=code.replace('ZIF17','ZIF21')
 (H/name).write_text(code,encoding='utf-8')
(H/'render_schematic.py').write_text((W/'symmetric_placement_20260920/render_schematic.py').read_text(),encoding='utf-8')
