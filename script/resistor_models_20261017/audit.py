"""Verify mesh-only edits and retained saved electrical/manufacturing geometry."""
from pathlib import Path
import sys,json,math,hashlib,struct,re
import olefile
H=Path(__file__).resolve().parent;ROOT=H.parents[1];P=ROOT/'QSTL_QD4_2SET_38PAD';OLD=ROOT/'script/qd_via_land_20261017'
sys.path[:0]=[str(ROOT/'script/qd38_rotation_20261011'),str(ROOT/'script/qd38_carrier_20261010')]
from audit_saved_revision_surface import read_snapshot
from audit_source_model_transforms import inspect
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();pcb=P/(P.name+'.PcbDoc');digest=sha(pcb)
sch=json.loads((P/'schematic_validation.json').read_text());plan=json.loads((H/'candidate.json').read_text());prep=json.loads((H/'preparation.json').read_text())
baseline=H/'baseline'/pcb.name;assert sha(baseline)==prep['source_sha256']
checks=[];issues=[]
def check(ok,name,details=None):
    row=dict(check=name,passed=bool(ok),details=details);checks.append(row)
    if not ok:issues.append(row)
for name in ('saved_native_audit.json','support_audit.json','mask_cam_audit.json'):
    old=json.loads((OLD/name).read_text());check(old['passed'] and old.get('source_sha256',old.get('checks',{}).get('native_sha256'))==prep['source_sha256'],'Verified baseline evidence',name)
with olefile.OleFileIO(baseline) as a,olefile.OleFileIO(pcb) as b:
    preserved=('Pads6','Tracks6','Arcs6','Vias6','Regions6','Polygons6','Components6','Nets6','Rules6','LayerStackManager')
    for path in a.listdir():
        if path[0] in preserved:
            check(b.exists(path) and a.openstream(path).read()==b.openstream(path).read(),'Native stream preserved','/'.join(path))
    connections=struct.unpack('<I',b.openstream('Connections6/Header').read()[:4])[0]
    check(connections==0,'Saved connection count zero',connections)
    differences=['/'.join(path) for path in a.listdir() if b.exists(path) and a.openstream(path).read()!=b.openstream(path).read()]
for name in (P.name+'.SchDoc','pin_mapping.csv'):check(sha(P/name)==sha(H/'baseline'/name),'Preserved source',name)
serialized=json.loads((H/'serialization.json').read_text())
shape=serialized['ShapeBasedComponentBodies6/Data']
check(shape['counts']==[49,49] and shape['same_keys'] and len(shape['changes'])==8,'Shape-based model cache retains 49 models and only eight changes')
for row in shape['changes']:
    check(set(row['fields'])=={'MODEL.3D.ROTZ'} and row['prefix_equal'] and row['tail_equal'],'Shape-based cache changes only Z rotation',row)
check(all(set(r['changes'])<={'TIME'} for r in serialized['Board6/Data']['changes']),'Only Board save-time metadata changed')
check(serialized['Texts6/Data']['same_keys'],'All stored text identities and content preserved')
# Native Altium rewrites unused text-buffer bytes on save. Assert that all
# coordinate/rotation/size/layer fields and text strings remain unchanged.
text_buffers=set(range(60,110))|set(range(173,225))
check(all(r['before_len']==r['after_len'] and set(r['offsets'])<=text_buffers for r in serialized['Texts6/Data']['changes']),'Text geometry/content preserved; only native text-buffer serialization differs')
base=inspect(baseline);after=inspect(pcb);uid={v:k for k,v in sch['components'].items()}
ref=lambda q:uid.get(q['component_fields'].get('SOURCEUNIQUEID','').strip('\\'),q['component'])
before={ref(q):q for q in base['bodies']};actual={ref(q):q for q in after['bodies']}
check(before.keys()==actual.keys() and len(actual)==49,'All 49 model instances retained')
padrows=read_snapshot(pcb,sch)[0];rows=[];changed=[]
for r,q in actual.items():
    old=before[r];target=r in prep['changed_refs']
    expected=plan['model_rotation_overrides'][r] if target else old['rotation_xyz_deg'][2]
    check(q['rotation_xyz_deg']==old['rotation_xyz_deg'][:2]+[expected],'Expected model rotation',r)
    for key in ('model_origin_mm','standoff_mm','overall_height_mm','body_projection','dz_mm','outline_mm','component_fields'):
        check(q[key]==old[key],'Preserved model '+key,r)
    h=lambda b:sorted({m['embedded_step_sha256'] for m in b['embedded_model_records'] if m['embedded_step_sha256']})
    check(h(q)==h(old),'Embedded STEP geometry unchanged',r)
    delta={k for k in q['body_fields'].keys()|old['body_fields'].keys() if q['body_fields'].get(k)!=old['body_fields'].get(k)}
    check(delta==({'MODEL.3D.ROTZ'} if target else set()),'Only intended model Z field changed',[r,sorted(delta)])
    if delta:changed.append(r)
    if r.startswith(('R','C')):
        p=sorted([p for p in padrows if p['ref']==r],key=lambda p:p['pin'])
        axis=math.degrees(math.atan2(p[1]['y']-p[0]['y'],p[1]['x']-p[0]['x']))%180
        projected=(-q['rotation_xyz_deg'][2])%180;err=abs((axis-projected+90)%180-90)
        check(err<.0002,'Bottom projected R/C long axis matches pads',[r,axis,projected,err])
        check(math.dist(q['model_origin_mm'],[(p[0][k]+p[1][k])/2 for k in ('x','y')])<.000025,'R/C model centred between pads',r)
        rows.append(dict(ref=r,pad_axis_deg=axis,projected_model_axis_deg=projected,error_deg=err,model_Z_before_deg=old['rotation_xyz_deg'][2],model_Z_after_deg=q['rotation_xyz_deg'][2],changed=target))
check(set(changed)==set(prep['changed_refs']) and len(changed)==8,'Exactly eight resistor models changed',changed)
drc=(H/'Native_DRC.html').read_text(encoding='utf-8');count=int(re.search(r'Rule Violations:</td>.*?DRC_summary_header_col3[^>]*>(\d+)',drc,re.S)[1])
check(count==0,'Native DRC zero',count)
log=(H/'native_validation.txt').read_text();check(log.rstrip().endswith('COMPLETE') and 'REOPENED' in log and 'POST_DRC_SAVED_CONNECTION_COUNT=0' in log,'Saved and reopened native verification complete')
check((H/'Native_DRC.html').stat().st_mtime>=(H/'CorrectResistorModels_log.txt').stat().st_mtime,'DRC follows model correction')
check(sha(pcb)==digest,'Native source stable during audit')
result=dict(passed=not issues,source_sha256=digest,baseline_sha256=prep['source_sha256'],checks=checks,issues=issues,changed_models=changed,RC_axis_checks=rows,stored_connections=connections,DRC_violations=count,changed_streams=differences,manufacturing_evidence='Current pad/via/region/rule/stack streams are byte-identical to the baseline whose native mask/paste, QD exclusions and 71-net connectivity audits passed. No new CAM export is required for this mesh-only correction.')
(H/'audit.json').write_text(json.dumps(result,indent=2))
print(json.dumps(dict(passed=not issues,checks=len(checks),issues=issues,source_sha256=digest,changed_models=changed,RC_axis_max_error_deg=max(r['error_deg'] for r in rows),DRC_violations=count,stored_connections=connections,changed_streams=differences),indent=2))
