"""Independently verify the bounded via-land and model-transform edits."""
from pathlib import Path
import sys,json,hashlib,math,struct,csv
from shapely.geometry import Point,Polygon
from shapely.ops import unary_union
H=Path(__file__).resolve().parent;ROOT=H.parents[1];P=ROOT/'QSTL_QD4_2SET_38PAD';OUT=P/'QD_Via_and_Cap_Models_20261017'
sys.path[:0]=[str(ROOT/'script/qd38_rotation_20261011'),str(ROOT/'script/qd38_carrier_20261010')]
from audit_saved_revision_surface import read_snapshot,olefile,binary_records,UNIT
from prepare_native_revision_rules import read_rules
from audit_source_model_transforms import inspect
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();pcb=P/(P.name+'.PcbDoc');digest=sha(pcb)
sch=json.loads((P/'schematic_validation.json').read_text());a=read_snapshot(H/'baseline'/pcb.name,sch);b=read_snapshot(pcb,sch)
plan=json.loads((H/'candidate.json').read_text());prep=json.loads((H/'preparation_audit.json').read_text());checks=[];issues=[]
def check(ok,label,detail=None):
    r=dict(check=label,passed=bool(ok),detail=detail);checks.append(r)
    if not ok:issues.append(r)
vk=lambda v:(v['net'],v['x'],v['y'],v['hole'],v['low'],v['high'])
old={vk(v):v for v in a[3]};new={vk(v):v for v in b[3]};check(old.keys()==new.keys(),'All 1590 via centres, holes, spans and nets unchanged')
changed=[];protrusion=[];clearance=[]
for row in prep['via_changes']:
    v=next(v for v in b[3] if v['net']==row['net'] and math.dist((v['x'],v['y']),(row['x'],row['y']))<UNIT)
    ov=old[vk(v)];changed.append(vk(v));ring=(v['diameter']-v['hole'])/2
    check(abs(v['diameter']-row['after'])<1e-12 and ring>=.05,'QD via minimum land and ring',[row['label'],v['diameter'],ring])
    pad=next(p for p in b[0] if p['ref']=='Q1' and p['pin']==row['label'].split('-')[-1]);pt=Point(v['x'],v['y']);land=pt.buffer(v['diameter']/2,quad_segs=256)
    check(land.intersection(pad['geometry']).area>0,'QD pad to via remains connected',row['label'])
    dc=[t for t in b[2] if t['net']==v['net'] and t['layer'] in (2,3)]
    check(any(land.intersects(t['geometry'].buffer(t['width']/2)) for t in dc),'QD via to internal DC remains connected',row['label'])
    phi=math.radians(pad['rotation']);dx=v['x']-pad['x'];dy=v['y']-pad['y'];u=dx*math.cos(phi)+dy*math.sin(phi);w=-dx*math.sin(phi)+dy*math.cos(phi)
    excess=lambda d:max(0,abs(u)+d/2-pad['sx']/2,abs(w)+d/2-pad['sy']/2)
    protrusion.append(dict(pad=pad['pin'],net=v['net'],land_before_mm=ov['diameter'],land_after_mm=v['diameter'],hole_mm=v['hole'],annular_ring_mm=ring,protrusion_before_mm=excess(ov['diameter']),protrusion_after_mm=excess(v['diameter'])))
    foreign_pad=min(land.distance(p['geometry']) for p in b[0] if p['net']!=v['net'] and p['net'])
    foreign_trace=min(land.distance(t['geometry'])-t['width']/2 for t in b[2] if t['net'] and t['net']!=v['net'] and t['layer'] in (1,2,3,4,5,32))
    foreign_via=min(math.dist((v['x'],v['y']),(z['x'],z['y']))-(v['diameter']+z['diameter'])/2 for z in b[3] if z['net']!=v['net'])
    ground=min(land.distance(r['geometry']) for r in b[1] if r['net']=='GND' and r['layer'] in (1,2,3,4,5,32))
    check(min(foreign_pad,foreign_trace,foreign_via,ground)>.09999,'No foreign copper collision or sub-0.10 mm gap',row['label'])
    clearance.append(dict(pad=pad['pin'],foreign_pad_mm=foreign_pad,foreign_trace_mm=foreign_trace,foreign_via_mm=foreign_via,ground_mm=ground))
for k,v in new.items():
    if k not in changed:check(v['diameter']==old[k]['diameter'],'Other via land preserved',[v['net'],v['x'],v['y']])
check(len(changed)==22,'Exactly 22 QD lands reduced')
oldrules=read_rules(H/'baseline'/pcb.name);rules=read_rules(pcb);rulekey='QD38_QD_VIA_0P4_0P2';check(rules.keys()==oldrules.keys(),'44 rules retained')
for key,r in rules.items():
    previous=oldrules[key]
    if key==rulekey:
        for attr in ('WIDTH','MINWIDTH','MAXWIDTH'):check(abs(float(r[attr].removesuffix('mil'))*.0254-prep['new_diameter_units']*UNIT)<UNIT,'Dedicated QD via style '+attr)
        check({k:v for k,v in r.items() if k not in ('WIDTH','MINWIDTH','MAXWIDTH')}=={k:v for k,v in previous.items() if k not in ('WIDTH','MINWIDTH','MAXWIDTH')},'QD via style scope and all other fields preserved')
    else:check(r==previous,'Rule preserved',key)
with olefile.OleFileIO(H/'baseline'/pcb.name) as before,olefile.OleFileIO(pcb) as after:
    for path in before.listdir():
        if path[0] in ('Pads6','Tracks6','Arcs6','Regions6','Components6','LayerStackManager'):
            check(after.exists(path) and before.openstream(path).read()==after.openstream(path).read(),'Native stream byte-preserved','/'.join(path))
    raw1=binary_records(before.openstream('Vias6/Data').read(),3);raw2=binary_records(after.openstream('Vias6/Data').read(),3)
    # Altium reorders edited primitives on save. Match by net, XY and drill.
    recordkey=lambda r:r['body'][3:5]+r['body'][13:21]+r['body'][25:29]
    keyed1={recordkey(r):r for r in raw1};keyed2={recordkey(r):r for r in raw2}
    check(keyed1.keys()==keyed2.keys(),'Raw via identities preserved independently of serialization order')
    diffs=[]
    for i,(key,r) in enumerate(keyed1.items()):
        s=keyed2[key]
        aa,bb=r['body'],s['body'];offsets=[j for j,(x,y) in enumerate(zip(aa,bb)) if x!=y]
        if offsets:
            diffs.append(dict(index=i,offsets=offsets))
            check(struct.unpack_from('<I',bb,21)[0]==prep['new_diameter_units'],'Common QD via land diameter matches target',i)
            check(all(struct.unpack_from('<I',bb,75+4*j)[0]==prep['new_diameter_units'] for j in range(32)),'All 32 native QD via layer-diameter cells match target',i)
    check(len(raw1)==len(raw2)==1590 and len(diffs)==22,'Only 22 raw via records differ',diffs)
    # Common diameter is at byte 21; layer-stack diameter cells begin at 75.
    allowed=set(range(21,25))|set(range(75,203))
    check(all(set(d['offsets']).issubset(allowed) for d in diffs),'Only via-diameter and layer-diameter bytes changed',diffs)
for name in (P.name+'.SchDoc','pin_mapping.csv'):check(sha(P/name)==sha(H/'baseline'/name),'Preserved '+name)
uid={v:k for k,v in sch['components'].items()}
mb=json.loads((H/'baseline_models.json').read_text());ma=inspect(pcb)
ref=lambda q:uid.get(q['component_fields'].get('SOURCEUNIQUEID','').strip('\\'),q['component'])
orig={ref(q):q for q in mb['bodies']};modelrows=[]
for q in ma['bodies']:
    r=ref(q);oldq=orig[r];changedmodel=r in plan['model_rotation_overrides']
    angle=plan['model_rotation_overrides'].get(r,oldq['rotation_xyz_deg'][2])
    check(q['rotation_xyz_deg']==oldq['rotation_xyz_deg'][:2]+[angle],'Expected model transform',r)
    for k in ('model_origin_mm','standoff_mm','overall_height_mm','body_projection','dz_mm'):check(q[k]==oldq[k],'Preserved model '+k,r)
    hashes=lambda z:sorted({v['embedded_step_sha256'] for v in z['embedded_model_records'] if v['embedded_step_sha256']})
    check(hashes(q)==hashes(oldq),'Embedded STEP geometry preserved',r)
    if r.startswith('C'):
        pp=[p for p in b[0] if p['ref']==r];axis=math.degrees(math.atan2(pp[1]['y']-pp[0]['y'],pp[1]['x']-pp[0]['x']))%180
        projected=(-q['rotation_xyz_deg'][2])%180
        err=abs((projected-axis+90)%180-90)
        check(err<.0002,'Bottom-rendered capacitor axis matches pads',[r,axis,projected,err])
        modelrows.append(dict(ref=r,changed=changedmodel,pad_axis_deg=axis,model_Z_before_deg=oldq['rotation_xyz_deg'][2],model_Z_after_deg=q['rotation_xyz_deg'][2],Bottom_projected_axis_deg=projected,axis_error_deg=err,body_fields_changed={k:[oldq['body_fields'].get(k),v] for k,v in q['body_fields'].items() if oldq['body_fields'].get(k)!=v},outline_changed=q['outline_mm']!=oldq['outline_mm']))
check(len(ma['bodies'])==49 and sum(r['changed'] for r in modelrows)==8,'49 models retained; 8 tilted capacitors corrected')
check(sha(pcb)==digest,'Native source stable')
protrusion.sort(key=lambda r:int(r['pad']))
with (OUT/'QD_Via_Changes.csv').open('w',newline='',encoding='utf-8') as f:wri=csv.DictWriter(f,fieldnames=list(protrusion[0]));wri.writeheader();wri.writerows(protrusion)
report=dict(passed=not issues,source_sha256=digest,checks=checks,issues=issues,via_rows=protrusion,clearances=clearance,model_rows=modelrows)
(H/'change_audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(dict(passed=not issues,checks=len(checks),issues=[dict(check=r['check'],detail=str(r['detail'])[:1000]) for r in issues],max_remaining_protrusion_mm=max(r['protrusion_after_mm'] for r in protrusion),minima={k:min(r[k] for r in clearance) for k in clearance[0] if k!='pad'},raw_via_changes=diffs[:1],model_axes_max_error_deg=max(r['axis_error_deg'] for r in modelrows)),indent=2))
