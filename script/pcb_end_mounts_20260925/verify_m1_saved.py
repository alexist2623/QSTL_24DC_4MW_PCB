"""Read-only acceptance checks for the two M1 PCB end mounts."""
from pathlib import Path
import sys, json, struct, re, collections, math
from shapely.ops import unary_union
from shapely.geometry import box, Point
H=Path(__file__).resolve().parent
R=H.parents[1]; P=R/'QSTL_24DC_4MW_PCB'; W=H.parent/'_support'
G=H.parent/'dc_ground_pour_20260924'; OLD=H.parent/'dc_even_zif_20260923'
B='QSTL_24DC_4MW_PCB'; source=P/(B+'.PcbDoc')
sys.path[:0]=[str(W/x) for x in ('qd_center_revision','final_routing/schematic','zif_revision_v2/board','rf_revision','route_python')]
from native_metadata_helpers import properties,pads_stream,sha,UNIT,binary_records
from build_routed_copy import snapshot
from verify_final_native_v2 import read_regions,read_rules
before=snapshot(H/'before_mounts.PcbDoc'); after=snapshot(source)
errors=[]
def check(ok,message):
    if not ok: errors.append(message)
preserved={}
for stem in ('Vias6','Components6','ComponentBodies6','Fills6','BoardRegions','LayerKindMapping'):
    key=stem+'/Data'
    if key in before:
        preserved[key]=before[key]==after[key]
        check(preserved[key],'Unrequested change: '+key)
def records(s,key,kind): return collections.Counter(r['body'] for r in binary_records(s[key+'/Data'],kind))
check(records(before,'Tracks6',4)==records(after,'Tracks6',4),'Track change')
a0=records(before,'Arcs6',1); a1=records(after,'Arcs6',1)
removed=list((a0-a1).elements()); added=list((a1-a0).elements())
check(len(removed)==len(added)==1,'Expected one moved pin-1 marker')
if len(removed)==len(added)==1:
    x,y=removed[0],added[0]
    check(x[0]==y[0]==33 and x[:13]==y[:13] and x[21:]==y[21:],'Non-marker arc change')
    check(math.dist([v*UNIT for v in struct.unpack_from('<2i',x,13)],(2.25,2.195))<4*UNIT,'Unexpected old marker')
    check(math.dist([v*UNIT for v in struct.unpack_from('<2i',y,13)],(3,2.1))<4*UNIT,'Unexpected new marker')
p0=pads_stream(before['Pads6/Data']); ps=pads_stream(after['Pads6/Data'])
raw0=collections.Counter(before['Pads6/Data'][p['start']:p['end']] for p in p0)
raw1=collections.Counter(after['Pads6/Data'][p['start']:p['end']] for p in ps)
check(not(raw0-raw1) and sum((raw1-raw0).values())==2,'Existing pads changed')
ns=properties(after['Nets6/Data']); cs=properties(after['Components6/Data'])
gnd=next(i for i,n in enumerate(ns) if n['NAME']=='GND')
mounts=[p for p in ps if p['number'] in ('MH7','MH8') and p['component']==65535]
check(len(ps)==149 and len(mounts)==2,'New mounting pad count')
mount_rows=[]
for p in mounts:
    coords=[v*UNIT for v in p['coords']]
    expected=[1.05 if p['number']=='MH7' else 18.45,1.2]+[1.6]*6+[1.2]
    check(max(abs(a-b) for a,b in zip(coords,expected))<3*UNIT,'Mount geometry '+p['number'])
    check(p['layer']==74 and p['net']==gnd and p['shape']==1,'Mount layer/net/shape '+p['number'])
    mount_rows.append(dict(name=p['number'],x=coords[0],y=coords[1],land_mm=coords[2],drill_mm=coords[8]))
rules=read_rules(after['Rules6/Data'])
old_rules={r['NAME']:r for r in read_rules(before['Rules6/Data'])}
new_rules={r['NAME']:r for r in rules}
check(old_rules.keys()==new_rules.keys(),'Rule set changed')
for name,r in old_rules.items():
    expected_rule=dict(r)
    # The native save materializes the parent object's non-electrical layer;
    # the rule's actual L2/L4 scope, value, priority and enabled state persist.
    if name=='DC_GND_GAP_0P2' and r['LAYER']=='UNKNOWN':expected_rule['LAYER']='TOP'
    check(new_rules[name]==expected_rule,'Rule fields changed '+name)
solid=next(r for r in rules if r['NAME']=='ZIF24V2_GND_VIA_SOLID')
check(solid['CONNECTSTYLE']=='Direct' and "IsPad And Not InComponent('*')" in solid['SCOPE1EXPRESSION'],'Mount solid-connect rule')
rs0=read_regions(before['Regions6/Data']); rs1=read_regions(after['Regions6/Data'])
polys=properties(after['Polygons6/Data'])
check(len(polys)==6 and all(int(p['NET'])==gnd and p['REMOVEDEAD']=='TRUE' and p['SHELVED']=='FALSE' for p in polys),'Ground polygons')
mask_delta={}
for layer in (35,36,37,38):
    a=unary_union([r['geometry'] for r in rs0 if r['layer']==layer])
    b=unary_union([r['geometry'] for r in rs1 if r['layer']==layer])
    mask_delta[str(layer)]=a.symmetric_difference(b).area
    check(mask_delta[str(layer)]<1e-10,'Mask/paste regions changed')
def ground(layer):
    rr=[]
    for r in rs1:
        ni=r['net_index']
        if ni==65535 and r['polygon_index']!=65535: ni=int(polys[r['polygon_index']]['NET'])
        if r['layer']==layer and ni==gnd: rr.append(r['geometry'])
    return unary_union(rr)
keep=box(7.4,40.15,12.1,44.85)
contacts=[]
for layer in (1,2,3,4,5,32):
    gg=ground(layer)
    check(gg.buffer(6*UNIT).covers(keep) if layer==1 else gg.intersection(keep.buffer(-6*UNIT)).area<1e-10,'QD ground condition '+str(layer))
    for p in mounts:
        x,y=[v*UNIT for v in p['coords'][:2]]
        # Check all available inboard circumference, excluding the existing
        # existing layer-specific perimeter setback (0.25 or 0.30 mm).
        # This detects thermal relief gaps without treating the board edge
        # setback outside the original polygon as a thermal void.
        ring=Point(x,y).buffer(.85,quad_segs=256).difference(Point(x,y).buffer(.78,quad_segs=256))
        ring=ring.intersection(box(*gg.bounds).buffer(-6*UNIT))
        missing=ring.difference(gg.buffer(6*UNIT)).area
        contacts.append(dict(layer=layer,pad=p['number'],missing_ground_mm2=missing))
        check(missing<1e-7,'Thermal gap '+p['number']+' layer '+str(layer))
expected=json.loads((OLD/'expected.json').read_text())
actual={cs[p['component']]['SOURCEDESIGNATOR']+'-'+p['number']:None if p['net']==65535 else ns[p['net']]['NAME'] for p in ps if p['component']!=65535}
check(actual==expected['pin_net_map']|{p:None for p in expected['nc_pins']},'Pin mapping')
check(sha(P/(B+'.SchDoc'))=='c2988857ab2062b0f581f105a6cd1f93677647b3c8a3b3ad4ac0c1e570bbf45e','Schematic changed')
compile_text=(H/'schematic_compile.txt').read_text()
check('VIOLATION_COUNT=0' in compile_text and compile_text.rstrip().endswith('COMPLETE'),'Schematic native compile')
compiled={}; name=None
for line in compile_text.splitlines():
    if line.startswith('NET='):name=line[4:].split('|')[0];compiled[name]=[]
    elif line.startswith('PIN=') and name is not None:compiled[name].append(line[4:])
for net,pins in expected['nets'].items():check(sorted(compiled.get(net,[]))==sorted(pins),'Schematic mismatch '+net)
paste=(H/'native_paste_audit.txt').read_text().splitlines(); pad_count=via_count=0
check(paste[-1]=='COMPLETE','Paste audit incomplete')
for row in paste:
    f=row.split('|')
    if f[0]=='PAD':
        pad_count+=1; disabled=f[1]=='MOUNT' or f[1].startswith('SMP')
        check(f[7:10]==(['0']*3 if disabled else ['1']*3),'Paste '+f[1]+'.'+f[2])
    if f[0]=='VIA':via_count+=1
check(pad_count==149 and via_count==528,'Paste audit primitive counts')
old_paste=(H.parent/'dwg_gerber_refresh_20260924/native_paste_audit.txt').read_text().splitlines()
# A via's inherited pad-cache flag is not a native paste aperture. Preserve
# the baseline via records/cache and check actual paste-layer primitives.
check([s for s in paste if s.startswith('VIA|')]==[s for s in old_paste if s.startswith('VIA|')],'Via paste cache changed')
check(not any(r['layer'] in (35,36) for r in rs1),'Unexpected custom paste regions')
reopen=(H/'reopen_check.txt').read_text()
check(all(s in reopen for s in ('AFTER_REOPEN_COUNT=0','DRC_RETURNED_TRUE','AFTER_DRC_COUNT=0','COMPLETE')),'Native reopened DRC/connectivity')
drc=P/'fabrication/JLCPCB_HDI_20260925/Native_DRC.html'
rows=re.findall(r'<td class="column1"><a href="#[^"]+">(.*?)</a></td>\s*<td class="column2">(\d+)</td>',drc.read_text(encoding='cp949',errors='replace'),re.S)
check(len(rows)>=15 and sum(int(n) for _,n in rows)==0 and drc.stat().st_mtime>source.stat().st_mtime,'Stale/failing DRC')
conn=json.loads((P/'docs/connection_validation.json').read_text())
check(conn['passed'] and conn['pcb_sha256']==sha(source),'Independent connectivity')
geometry=json.loads((G/'saved_ground_geometry.json').read_text())
check(geometry['pcb_sha256']==sha(source),'Stale ground geometry')
for layer,row in geometry['layers'].items():
    check(row['minimum_signal_clearance_mm']>=.2-4*UNIT and row['grounded_regions']==1 and row['removed_islands']==0,'DC ground clearance/island '+layer)
report=dict(passed=not errors,errors=errors,pcb_sha256=sha(source),source_sha256=sha(H/'before_mounts.PcbDoc'),
    unchanged_streams=preserved,mounts=mount_rows,hole_pitch_mm=17.4,board_outline_mm=[19.5,67.9],
    nearest_drill_to_edge_mm=.45,mask_symmetric_difference_mm2=mask_delta,mechanical_solid_connection_checks=contacts,
    DRC=dict(report=str(drc),checked_rules=len(rows),violations=sum(int(n) for _,n in rows)),
    connectivity=dict(connected_nets=conn['connected_net_count'],stored_unrouted_connections=conn['stored_connection_line_count']),
    schematic_mapping_matches=actual==expected['pin_net_map']|{p:None for p in expected['nc_pins']},
    dc_ground_clearance_mm=.2,paste_pad_count=pad_count,via_count=via_count,
    existing_480_L5_L6_blind_vias_preserved=preserved['Vias6/Data'],no_added_DC_vias=preserved['Vias6/Data'])
(H/'validation.json').write_text(json.dumps(report,indent=2))
if not errors:(P/'docs/ZIF_M1_mount_validation.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2));raise SystemExit(1 if errors else 0)
