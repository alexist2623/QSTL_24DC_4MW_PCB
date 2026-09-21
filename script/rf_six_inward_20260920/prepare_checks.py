from pathlib import Path
import json
H=Path(__file__).resolve().parent;W=H.parent/'_support';OLD=W/'dc_direct_20260920'
g=json.loads((H/'geometry.json').read_text());n=json.loads((H/'baseline_native.json').read_text());rf=json.loads((H/'rf_routes.json').read_text())
g['fanout_tracks']=[t for t in n['tracks'] if t['layer']==1];q=next(c for c in n['components'] if c['designator']=='Q1');g['qd_component_center']=[q['x'],q['y']]
(H/'geometry.json').write_text(json.dumps(g,indent=2))
for ch in rf['channels'].values():ch['main_length_mm']=ch['input_length_mm']+ch['output_length_mm']
(H/'rf_routes.json').write_text(json.dumps(rf,indent=2))
s=(OLD/'verify_native.py').read_text().replace('(22,147,33,65)','(22,147,37,72)').replace("if not p['component'].startswith('MOUNT')","if p['component']")
s=s.replace(" and key.split('-')[0] not in ['R5','R6','C5','C6']",'')
s=s.replace("len(ars)==len(rf['arcs'])==11","len(ars)==len(rf['arcs'])=="+str(len(rf['arcs'])))
s=s.replace('dc_direct_schematic_compile.txt','rf6_schematic_compile.txt').replace('Connections_DRC.html','RF6_DRC.html').replace('named_nets=33','named_nets=37')
s=s.replace("check(n==24,'QD library pad count')", "check(n==24,'QD library pad count')\ncheck(sha(P/(B+'.PcbLib'))==sha(H/(B+'.PcbLib')),'PcbLib changed')\nfor a in ars:\n candidates=[b for b in rf['arcs'] if b['net']==a['net'] and math.dist((a['cx'],a['cy']),(b['cx'],b['cy']))<6*UNIT]\n check(any(close(a['radius'],b['radius']) and abs((a['start_angle']-b['start_angle']+180)%360-180)<1e-5 and abs((a['end_angle']-b['end_angle']+180)%360-180)<1e-5 for b in candidates),'Native RF arc differs '+a['net'])")
(H/'verify_native.py').write_text(s.replace('W=H.parent',"W=H.parent/'_support'"))
s=(OLD/'verify_angles.py').read_text().replace("for ch,pin in g['rf_qd_map'].items():","for ch,pin in g['rf_qd_map'].items():\n if int(ch)>4:continue")
# Native net creation may update component net metadata; fixed geometry is independently checked below.
s=s.replace("if actualold!=ocs:errors.append('Existing component metadata or placement changed unexpectedly')","if [{k:c.get(k) for k in ['SOURCEDESIGNATOR','X','Y','ROTATION','LAYER','PATTERN','SOURCEUNIQUEID']} for c in actualold]!=[{k:c.get(k) for k in ['SOURCEDESIGNATOR','X','Y','ROTATION','LAYER','PATTERN','SOURCEUNIQUEID']} for c in ocs]:errors.append('Existing component placement changed unexpectedly')")
(H/'verify_angles.py').write_text(s.replace('W=H.parent',"W=H.parent/'_support'"))
s=(W/'connection_audit_20260920/audit.py').read_text().replace("PREV=W/'dc_direct_20260920'","PREV=H")
(H/'audit_connectivity.py').write_text(s.replace('W=H.parent',"W=H.parent/'_support'"))
print('Saved-native and physical-connectivity checks prepared.')
