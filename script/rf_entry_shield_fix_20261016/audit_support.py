"""Verify compiled pins, effective paste output, embedded models and masks."""
from pathlib import Path
import sys,json,hashlib,math,collections,re
from shapely.geometry import Point,box,shape
from shapely.ops import unary_union
H=Path(__file__).resolve().parent;ROOT=H.parents[1];DEST=ROOT/'QSTL_QD4_2SET_38PAD'
sys.path[:0]=[str(ROOT/'script/qd38_rotation_20261011'),str(ROOT/'script/qd38_carrier_20261010'),str(ROOT/'script/fpc_gerber_20261005/work/deps')]
from audit_saved_revision_surface import read_snapshot
from audit_source_model_transforms import inspect
from gerbonara import GerberFile
from gerbonara.utils import MM
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
pcb=DEST/'QSTL_QD4_2SET_38PAD.PcbDoc';digest=sha(pcb)
sch=json.loads((DEST/'schematic_validation.json').read_text());plan=json.loads((H/'candidate.json').read_text())
pads,regions,tracks,vias,outline=read_snapshot(pcb,sch)
issues=[];results={}
def check(ok,issue,detail=None):
    if not ok:issues.append(dict(issue=issue,detail=detail))

# The live compiler's Boolean return is historically False even on a successful
# message. Verify its enumerated electrical net membership independently.
compiled={};cur=None
compile_text=(H/'native_compile.txt').read_text()
for line in compile_text.splitlines():
    if line.startswith('NET='):cur=line[4:].split('|')[0];compiled[cur]=[]
    elif line.startswith('PIN='):compiled[cur].append(line[4:].replace('.','-'))
check({n:sorted(compiled.get(n,[])) for n in sch['nets']}=={n:sorted(v) for n,v in sch['nets'].items()},'compiled_pin_map')
extras={n:v for n,v in compiled.items() if n not in sch['nets']}
check(len(extras)==15 and all(len(v)==1 and v[0].startswith('J1-') for v in extras.values()),'compiled_unconnected_ZIF_contacts',extras)
violations=int(re.search(r'^VIOLATION_COUNT=(\d+)',compile_text,re.M)[1])
check(violations==0,'native_compile_violations',violations)
check(compile_text.rstrip().endswith('COMPLETE'),'native_compile_incomplete')
check((H/'native_compile.txt').stat().st_mtime>=pcb.stat().st_mtime,'stale_compile')
results['compiled']={'named_nets':len(sch['nets']),'unused_ZIF_contacts':len(extras),'native_violation_count':violations,'Boolean_return':'COMPILE_RESULT=True' in compile_text,'evidence':'Enumerated native compiled net membership and violation list.'}

# Check a bijection between native normal SMD lands and fresh paste flashes.
results['paste']={};cam=H/'paste_verification/Native_CAM'
for ext,ll in [('GTP',1),('GBP',32)]:
    path=cam/(pcb.stem+'.'+ext);g=GerberFile.open(path)
    expected=[p for p in pads if p['layer']==ll and p['ref'] and p['ref'][0] in ('J','R','C')]
    check(path.stat().st_mtime>pcb.stat().st_mtime,'stale_paste',ext)
    check('Board_Origin=0|0' in path.read_text(),'paste_origin',ext)
    check(len(g.objects)==len(expected),'paste_count',[ext,len(g.objects),len(expected)])
    used=set();max_error=0
    for p in expected:
        hits=[(i,o.converted(MM)) for i,o in enumerate(g.objects) if type(o).__name__=='Flash' and math.dist((p['x'],p['y']),(o.converted(MM).x,o.converted(MM).y))<.000075]
        check(len(hits)==1,'missing_paste',[p['ref'],p['pin']])
        if len(hits)!=1:continue
        i,o=hits[0];check(i not in used,'duplicate_paste',i);used.add(i)
        (x0,y0),(x1,y1)=o.bounding_box(MM);err=max(abs(a-b) for a,b in zip((x0,y0,x1,y1),p['geometry'].bounds));max_error=max(max_error,err)
        check(err<.000075 and o.polarity_dark,'paste_aperture',[p['ref'],p['pin'],err])
    check(len(used)==len(g.objects),'extra_via_QD_SMP_mount_paste',ext)
    results['paste'][ext]=dict(flashes=len(g.objects),normal_SMD_pads=len(expected),matched=len(used),max_bounds_error_mm=max_error,sha256=sha(path))

# Preserve known STEP geometry while checking each native body transform.
baseline=inspect(H/'baseline/QSTL_QD4_2SET_38PAD.PcbDoc');actual=inspect(pcb)
uids={v:k for k,v in sch['components'].items()}
byold={uids.get(b['component_fields'].get('SOURCEUNIQUEID','').strip('\\'),b['component']):b for b in baseline['bodies']};wanted={c['ref']:c for c in plan['components']}
modelrows=[];counts=collections.Counter()
hashes=lambda b:sorted({m['embedded_step_sha256'] for m in b['embedded_model_records'] if m['embedded_step_sha256']})
capsha=sha(ROOT/'script/cap_1206_apply_20261014/native_prep/CC1206JKNPO9BN104_OEM_MAX_Centered.step')
for b in actual['bodies']:
    cf=b['component_fields'];ref=uids.get(cf.get('SOURCEUNIQUEID','').strip('\\'),b['component']);c=wanted[ref]
    fam='SMP' if ref.startswith('SMP') else ref[0];counts[fam]+=1
    if fam=='J':
        old=next(v for v in baseline['bodies'] if v['component']=='J1')
        origin=old['model_origin_mm'];rotation=old['rotation_xyz_deg'];height=old['overall_height_mm'];dz=old['dz_mm'];stand=old['standoff_mm'];proj=old['body_projection'];hs=hashes(old)
    elif fam=='SMP':
        origin=[c['x'],c['y']];rotation=[90,0,c['rotation']];height=5.39999936;dz=.5999988;stand=-3.2100012;proj=0;hs=hashes(byold['SMP35'])
    else:
        pp=[p for p in pads if p['ref']==ref];origin=[sum(p[k] for p in pp)/2 for k in ('x','y')];rotation=[0,0,c['rotation']];height=1.8 if fam=='C' else .45;dz=0;stand=0;proj=1;hs=[capsha] if fam=='C' else hashes(byold['R02'])
    err=math.dist(origin,b['model_origin_mm'])
    check(err<.000025,'model_origin',[ref,err])
    check(max(abs((a-d+180)%360-180) for a,d in zip(b['rotation_xyz_deg'],rotation))<.0001,'model_rotation',[ref,b['rotation_xyz_deg'],rotation])
    check(hashes(b)==hs,'model_geometry_hash',ref)
    check(all(abs(b[k]-v)<.000025 for k,v in [('dz_mm',dz),('standoff_mm',stand),('overall_height_mm',height)]) and b['body_projection']==proj,'model_height_or_side',{'ref':ref,'actual':{k:b[k] for k in ('dz_mm','standoff_mm','overall_height_mm','body_projection')},'original':{k:byold[ref][k] for k in ('dz_mm','standoff_mm','overall_height_mm','body_projection')}})
    modelrows.append(dict(ref=ref,origin=b['model_origin_mm'],rotation=b['rotation_xyz_deg'],hashes=hashes(b),origin_error_mm=err))
check(dict(counts)==dict(J=1,R=16,C=16,SMP=16),'model_counts',dict(counts))
results['models']={'counts':dict(counts),'bodies':modelrows,'scope':'Saved embedded geometry and transformations; not a 3D mating certification.'}

opening={ll:unary_union([r['geometry'] for r in regions if r['layer']==ll]) for ll in (37,38)}
field=shape(plan['qd_mask_field']);check(field.difference(opening[38].buffer(.000025)).area<1e-8,'QD_bottom_mask_open')
cx,cy=plan['sample_center'];centre=box(cx-2.15,cy-2.65,cx+2.15,cy+2.65)
check(centre.difference(opening[37].buffer(.000025)).area<1e-8,'QD_top_exposed_centre')
qdv=[v for v in vias if v['net']!='GND' and Point(v['x'],v['y']).distance(field)==0]
for v in qdv:check(Point(v['x'],v['y']).buffer(v['diameter']/2-.000025).intersection(opening[37]).area<1e-7,'QD_top_via_protection',[v['x'],v['y']])
for p in pads:
    if p['ref'] is None:
        for ll in (37,38):check(p['geometry'].difference(opening[ll].buffer(.000025)).area<1e-7,'mount_mask_open',[p['pin'],ll])
check(all(r['layer']!=74 for r in regions),'unexpected_multilayer_cutout')
results['masks']={'QD_bottom_field_open':True,'QD_top_centre_exposed':True,'QD_top_vias_protected':len(qdv),'mounts_open_both_sides':6}
check(sha(pcb)==digest,'native_changed_during_audit')
out=dict(passed=not issues,issues=issues,source_sha256=digest,results=results)
(H/'support_audit.json').write_text(json.dumps(out,indent=2))
print(json.dumps(dict(passed=not issues,issues=issues,paste=results['paste'],models=dict(counts),compiled=results['compiled']),indent=2))
