"""Verify the saved native ground-pour change against its exact source backup."""
from pathlib import Path
import sys, json, struct, re, collections, hashlib
from shapely.ops import unary_union
from shapely.geometry import box, Point

H=Path(__file__).resolve().parent
R=H.parents[1];P=R/'QSTL_24DC_4MW_PCB';W=H.parent/'_support'
AUDIT=H.parent/'dwg_gerber_refresh_20260924'
PREV=H.parent/'dc_even_zif_20260923';B='QSTL_24DC_4MW_PCB'
sys.path[:0]=[str(W/x) for x in ('qd_center_revision','final_routing/schematic','zif_revision_v2/board','rf_revision','route_python')]
from native_metadata_helpers import properties,pads_stream,sha,UNIT,binary_records
from build_routed_copy import snapshot
from verify_final_native_v2 import read_regions,read_route,read_rules

source=P/(B+'.PcbDoc');before=snapshot(H/'before_ground_pour.PcbDoc');after=snapshot(source)
widen_before=snapshot(H/'before_clearance_0p20.PcbDoc')
errors=[]
def check(condition,message):
    if not condition:errors.append(message)

preserved={}
for stem in ('Arcs6','Vias6','Pads6','Components6','Fills6','BoardRegions','LayerKindMapping'):
    stream=stem+'/Data'
    if stream not in before:continue
    preserved[stream]=before[stream]==after[stream]
    check(preserved[stream], 'Unexpected geometry, net, pad or rule change: '+stream)
old_rules={r['NAME']:r for r in read_rules(widen_before['Rules6/Data'])}
new_rules={r['NAME']:r for r in read_rules(after['Rules6/Data'])}
dc_scope="InNet('GND') And (OnLayer('L2_DC_A') Or OnLayer('L4_DC_B'))"
rf_scope="InNet('GND') And OnLayer('L6_RF_QD')"
check(set(new_rules)==set(old_rules)|{'DC_GND_GAP_0P2'},'Unexpected rules added/removed')
for name,rule in old_rules.items():
    expected_rule=dict(rule)
    if rule['RULEKIND']=='Clearance':expected_rule['PRIORITY']=str(int(rule['PRIORITY'])+1)
    if name=='Clearance':
        expected_rule['SCOPE1EXPRESSION']=f'Not ({rf_scope}) And Not ({dc_scope})'
        expected_rule['SCOPE2EXPRESSION']=expected_rule['SCOPE1EXPRESSION']
    check(new_rules.get(name)==expected_rule,'Unrequested rule modification '+name)
dc_rule=new_rules.get('DC_GND_GAP_0P2',{})
for key,value in {'RULEKIND':'Clearance','ENABLED':'TRUE','NETSCOPE':'DifferentNets',
                  'LAYERKIND':'SameLayer','PRIORITY':'1','SCOPE1EXPRESSION':dc_scope,
                  'SCOPE2EXPRESSION':'All','GAP':'7.874mil','GENERICCLEARANCE':'7.874mil',
                  'OBJECTCLEARANCES':''}.items():
    check(dc_rule.get(key)==value,'Incorrect DC clearance rule field '+key)
for stem in ('Arcs6','Vias6','Pads6','Components6','Fills6','BoardRegions','LayerKindMapping'):
    stream=stem+'/Data'
    if stream in widen_before:check(widen_before[stream]==after[stream],'Change outside DC clearance: '+stream)
old_nets=properties(widen_before['Nets6/Data']);new_nets=properties(after['Nets6/Data'])
check(len(old_nets)==len(new_nets),'Net count changed')
for r0,r1 in zip(old_nets,new_nets):
    # Altium materializes a zero-length cached statistic on the next save.
    check(r1==r0 or r1==dict(r0,MANHATTANLENGTH='0'),'Net identity/properties changed')
track_records_before=collections.Counter(r['body'] for r in binary_records(before['Tracks6/Data'],4))
track_records_after=collections.Counter(r['body'] for r in binary_records(after['Tracks6/Data'],4))
check(track_records_before==track_records_after,'Track records changed beyond native record ordering')
old_cache=collections.Counter(r['body'] for r in binary_records(before['ShapeBasedRegions6/Data'],11))
new_cache=collections.Counter(r['body'] for r in binary_records(after['ShapeBasedRegions6/Data'],11))
added_cache=list((new_cache-old_cache).elements())
check(not (old_cache-new_cache),'Existing native polygon cache removed or modified')
check(len(added_cache)==2 and {(r[0],struct.unpack_from('<H',r,5)[0]) for r in added_cache}=={(2,4),(4,5)},'Unexpected native polygon cache additions')
rs0=read_regions(before['Regions6/Data']);rs1=read_regions(after['Regions6/Data'])
polys0=properties(before['Polygons6/Data']);polys1=properties(after['Polygons6/Data'])
ns=properties(after['Nets6/Data']);cs=properties(after['Components6/Data']);ps=pads_stream(after['Pads6/Data'])
gnd=next(i for i,n in enumerate(ns) if n['NAME']=='GND')
def ground_regions(regions,polys,layer):
    result=[]
    for r in regions:
        ni=r['net_index']
        if ni==65535 and r['polygon_index']!=65535:ni=int(polys[r['polygon_index']]['NET'])
        if r['layer']==layer and ni==gnd:result.append(r['geometry'])
    return unary_union(result)
check(len(polys1)==6, 'Expected six GND polygons')
for i,(r0,r1) in enumerate(zip(properties(widen_before['Polygons6/Data']),polys1)):
    expected_poly=dict(r0)
    # Repour closes the unused terminal vertex onto vertex zero; the four
    # actual outline vertices and all pour settings must remain unchanged.
    if i in (4,5):
        expected_poly['VX4']=r0['VX0'];expected_poly['VY4']=r0['VY0']
    check(r1==expected_poly,'Polygon outline/settings changed while widening: '+str(i))
for layer in ('MID1','MID3'):
    rows=[r for r in polys1 if r['LAYER']==layer]
    check(len(rows)==1 and int(rows[0]['NET'])==gnd, 'Ground polygon missing on '+layer)
    check(len(rows)==1 and rows[0]['REMOVEDEAD']=='TRUE' and rows[0]['SHELVED']=='FALSE', 'Floating/shelved polygon settings '+layer)
mask_deltas={}
for layer in (35,36,37,38):
    old=unary_union([r['geometry'] for r in rs0 if r['layer']==layer])
    new=unary_union([r['geometry'] for r in rs1 if r['layer']==layer])
    mask_deltas[str(layer)]=old.symmetric_difference(new).area
    check(mask_deltas[str(layer)]<1e-10,'Mask changed on layer '+str(layer))
ground_deltas={}
for layer in (1,3,5,32):
    ground_deltas[str(layer)]=ground_regions(rs0,polys0,layer).symmetric_difference(ground_regions(rs1,polys1,layer)).area
    check(ground_deltas[str(layer)]<1e-10,'Unrequested GND change on layer '+str(layer))
keep=box(7.4,40.15,12.1,44.85)
for layer in (2,3,4,5,32):check(ground_regions(rs1,polys1,layer).intersection(keep.buffer(-6*UNIT)).area<1e-10,'QD exclusion '+str(layer))
check(ground_regions(rs1,polys1,1).buffer(6*UNIT).covers(keep),'Top QD GND missing')
mount_checks=[]
for layer in (2,4):
    ground=ground_regions(rs1,polys1,layer)
    for p in ps:
        if p['component']!=65535:continue
        x,y,sx=[c*UNIT for c in p['coords'][:3]]
        # Test full circumferential contact at the mounting land and 0.10 mm
        # outside it. The previous 0.20 mm test annulus now legitimately meets
        # a widened signal-via exclusion beside the left large mounting pad.
        annulus=Point(x,y).buffer(sx/2+.1,quad_segs=128).difference(Point(x,y).buffer(sx/2-.01,quad_segs=128))
        missing=annulus.difference(ground.buffer(6*UNIT)).area
        mount_checks.append(dict(layer=layer,x=x,y=y,missing_ground_mm2=missing))
        check(missing<1e-7,'Mount thermal gap on '+str(layer))
expected=json.loads((PREV/'expected.json').read_text())
actual={cs[p['component']]['SOURCEDESIGNATOR']+'-'+p['number']:None if p['net']==65535 else ns[p['net']]['NAME'] for p in ps if p['component']!=65535}
check(actual==expected['pin_net_map']|{p:None for p in expected['nc_pins']},'Saved pin mapping differs')
compile_text=(AUDIT/'schematic_compile.txt').read_text()
check('VIOLATION_COUNT=0' in compile_text and compile_text.rstrip().endswith('COMPLETE'),'Fresh schematic audit incomplete')
compiled={};name=None
for line in compile_text.splitlines():
    if line.startswith('NET='):name=line[4:].split('|')[0];compiled[name]=[]
    elif line.startswith('PIN=') and name is not None:compiled[name].append(line[4:])
for net,pins in expected['nets'].items():check(sorted(compiled.get(net,[]))==sorted(pins),'Native schematic mismatch '+net)
paste=(AUDIT/'native_paste_audit.txt').read_text().splitlines()
check(paste[-1]=='COMPLETE','Fresh native paste audit incomplete')
pad_count=0
for row in paste:
    fields=row.split('|')
    if fields[0]!='PAD':continue
    pad_count+=1;disabled=fields[1]=='MOUNT' or fields[1].startswith('SMP')
    check(fields[7:10]==(['0']*3 if disabled else ['1']*3),'Pad paste changed '+fields[1]+'.'+fields[2])
check(pad_count==147,'Native paste pad count')
check(not any(r['layer'] in (35,36) for r in rs1),'Via-specific paste regions remain')
reopen=(AUDIT/'reopen_check.txt').read_text()
check(all(s in reopen for s in ('AFTER_REOPEN_COUNT=0','DRC_RETURNED_TRUE','AFTER_DRC_COUNT=0','COMPLETE')),'Native reopened connectivity/DRC failure')
drc_path=P/'fabrication/JLCPCB_HDI_20260924/Native_DRC.html'
html=drc_path.read_text(encoding='cp949',errors='replace')
rows=re.findall(r'<td class="column1"><a href="#[^"]+">(.*?)</a></td>\s*<td class="column2">(\d+)</td>',html,re.S)
check(len(rows)>=15 and sum(int(n) for _,n in rows)==0,'Fresh native DRC reports violations')
check(drc_path.stat().st_mtime>source.stat().st_mtime,'DRC predates saved PCB')
connectivity=json.loads((P/'docs/connection_validation.json').read_text())
check(connectivity['passed'] and connectivity['pcb_sha256']==sha(source),'Stale or failed independent connectivity')
geometry=json.loads((H/'saved_ground_geometry.json').read_text())
check(geometry['pcb_sha256']==sha(source) and geometry['status']=='SAVED_NATIVE_POUR','Stale ground geometry')
check(geometry['clearance_mm']==0.20,'DC clearance target must be 0.20 mm')
for layer,row in geometry['layers'].items():
    check(row['minimum_signal_clearance_mm']>=0.20-4*UNIT,'DC signal-to-pour gap below 0.20 mm: '+layer)
    check(row['grounded_regions']==1 and row['removed_islands']==0,'Floating DC ground islands: '+layer)
report=dict(passed=not errors,errors=errors,pcb_sha256=sha(source),source_sha256=sha(H/'before_ground_pour.PcbDoc'),
    unchanged_streams=preserved,mask_symmetric_difference_mm2=mask_deltas,previous_ground_layer_deltas_mm2=ground_deltas,
    all_track_records_preserved=track_records_before==track_records_after,native_track_record_order_changed=before['Tracks6/Data']!=after['Tracks6/Data'],
    existing_shape_cache_preserved=not bool(old_cache-new_cache),new_shape_cache_layers=[2,4],
    mechanical_solid_connection_checks=mount_checks,added_ground_layers=['L2_DC_A','L4_DC_B'],
    ground={k:{a:b for a,b in v.items() if a!='geometry'} for k,v in geometry['layers'].items()},
    dc_ground_clearance_mm=0.20,clearance_change_source_sha256=sha(H/'before_clearance_0p20.PcbDoc'),
    clearance_rule=dc_rule,
    DRC=dict(report=str(drc_path),checked_rules=len(rows),violations=sum(int(n) for _,n in rows)),
    connectivity=dict(connected_nets=connectivity['connected_net_count'],stored_unrouted_connections=connectivity['stored_connection_line_count']),
    schematic_mapping_matches=True if not errors else None,native_schematic_violations=0,native_paste_pad_count=pad_count,
    existing_480_L5_L6_blind_vias_preserved=preserved['Vias6/Data'],no_added_DC_vias=preserved['Vias6/Data'])
(H/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
if not errors:(P/'docs/DC_GND_pour_validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
raise SystemExit(1 if errors else 0)
