"""Validate the saved native PCB against geometry, net, mask and fabrication intent."""
from pathlib import Path
import sys,json,math,struct,re,collections,shutil
from shapely.geometry import box,Point,LineString,shape as from_geojson
from shapely.affinity import rotate,translate
from shapely.ops import unary_union
H=Path(__file__).resolve().parent;P=H.parents[1]/'QSTL_24DC_4MW_PCB';D=P/'docs';W=H.parent/'_support';B='QSTL_24DC_4MW_PCB';PREV=H.parent/'rf_six_inward_20260920'
sys.path[:0]=[str(W/x) for x in ('qd_center_revision','final_routing/schematic','zif_revision_v2/board','zif_revision_v2/schematic','rf_revision','route_python')]
from native_metadata_helpers import properties,pads_stream,pad_record,binary_records,UNIT,sha
from build_routed_copy import snapshot
from verify_final_native_v2 import read_regions,read_route,read_rules,trackkey,arckey
from geometry_helpers import Arc,copper_geometry
original_arckey=arckey
def arckey(a):
    k=original_arckey(a);return k[:-2]+(k[-2]%360,k[-1]%360)
plan=json.loads((H/'plan.json').read_text());wanted=json.loads((H/'planned_native.json').read_text());before=json.loads((H/'before_native.json').read_text());expected=json.loads((PREV/'expected.json').read_text())
s=snapshot(P/(B+'.PcbDoc'));old=snapshot(H/'before.PcbDoc');cs=properties(s['Components6/Data']);ns=properties(s['Nets6/Data']);ps=pads_stream(s['Pads6/Data']);ts,ars,vs=read_route(s,ns);rs=read_regions(s['Regions6/Data']);polys=properties(s['Polygons6/Data']);rules=read_rules(s['Rules6/Data']);errors=[]
def check(ok,msg):
    if not ok:errors.append(msg)
def close(a,b,t=6*UNIT):return abs(a-b)<=t
def padshape(p):
    x,y,sx,sy=[c*UNIT for c in p['coords'][:4]]
    if p['layer']==74:return Point(x,y).buffer(sx/2,quad_segs=128)
    return translate(rotate(box(-sx/2,-sy/2,sx/2,sy/2),p['rotation'],origin=(0,0)),x,y)
planpads={(p['component'],p['number']):p for p in wanted['pads'] if p['component']}
actual={};cav=from_geojson(plan['cavity']['geometry']);cavity_gaps=[];cap_vias=[]
for p in ps:
    c=cs[p['component']]['SOURCEDESIGNATOR'] if p['component']!=65535 else None
    net=ns[p['net']]['NAME'] if p['net']!=65535 else None
    if c:
        q=planpads[c,p['number']];xy=[v*UNIT for v in p['coords'][:2]];actual[c+'-'+p['number']]=net
        check(close(xy[0],q['x']) and close(xy[1],q['y']),f'Pad location {c}.{p["number"]}')
        check(close(p['coords'][2]*UNIT,q['size_x']) and close(p['coords'][3]*UNIT,q['size_y']),f'Pad size {c}.{p["number"]}')
        check(p['layer']==q['layer'] and abs((p['rotation']-q['rotation']+90)%180-90)<1e-6,f'Pad layer/rotation {c}.{p["number"]}')
        matches=[v for v in vs if math.dist((v['x'],v['y']),xy)<6*UNIT]
        if (c=='Q1' and net.startswith('ZIF')) or (c.startswith('R') and p['number']=='2'):check(len(matches)==1 and matches[0]['net']==net,f'Via-in-pad missing {c}.{p["number"]}')
        if (c=='Q1' and net.startswith('MW')) or (c.startswith('R') and p['number']=='1'):check(not matches,f'RF-side resistor via remains {c}.{p["number"]}')
        if c.startswith('C'):
            cap_vias.extend(matches);check(not matches,f'Capacitor via remains {c}.{p["number"]}')
        if c=='Q1':cavity_gaps.append(padshape(p).distance(cav))
check(actual==expected['pin_net_map']|{p:None for p in expected['nc_pins']},'Schematic pin assignments differ')
check(min(cavity_gaps)>=.2-6*UNIT,'Cavity-to-pad spacing')
check((len(cs),len(ps),len(ns),len(vs))==(22,147,37,528),'Counts differ')

for a,b in zip(properties(s['Components6/Data']),properties(old['Components6/Data'])):
    name=a['SOURCEDESIGNATOR']
    for key in a:
        if name in plan['component_y_moves_mm'] and key in ('X','Y'):continue
        check(a[key]==b.get(key),'Component metadata changed '+name+' '+key)

check(s['BoardRegions/Data']==old['BoardRegions/Data'],'Board outline changed')
check(collections.Counter(map(trackkey,ts))==collections.Counter(map(trackkey,wanted['tracks'])),'Saved track geometry differs from approved plan')
check(collections.Counter(map(arckey,ars))==collections.Counter(map(arckey,wanted['arcs'])),'Saved arc geometry differs from plan')
shield=[v for v in vs if v['net']=='GND'];signal=[v for v in vs if v['net']!='GND']
check(len(shield)==480 and all(tuple(sorted((v['body'][29],v['body'][30])))==(5,32) for v in shield),'Shield via span/count')
pairgap=min(math.dist((a['x'],a['y']),(b['x'],b['y']))-(a['diameter']+b['diameter'])/2 for i,a in enumerate(shield) for b in shield[:i]);check(pairgap>=.15-6*UNIT,'Shield-to-shield spacing');check(len(signal)==48 and all(tuple(sorted((v['body'][29],v['body'][30])))==(1,32) for v in signal),'Signal via span/count')
def viakey(v):return (v['net'],*(round(v[k]/UNIT) for k in ('x','y','diameter','hole')))
check(collections.Counter(map(viakey,signal))==collections.Counter(map(viakey,wanted['vias'])),'Unexpected via addition, deletion or movement')
for stream in ('Fills6/Data','Nets6/Data'):
    check(s[stream]==old[stream],'Unrequested object change '+stream)
for ext,key in (('.SchDoc','schematic_sha256'),('.PcbLib','pcblib_sha256')):
    check(sha(P/(B+ext))==json.loads((H.parent/'rc_mask_clearance_20260921'/'validation.json').read_text())[key],'Unrequested file change '+ext)
for v in shield:
    check(close(v['diameter'],.25) and close(v['hole'],.1),'Shield drill/land')
    check(any(math.dist((v['x'],v['y']),(q['x'],q['y']))<6*UNIT for q in plan['shield_vias']),'Shield position')
rfpaths=[]
for t in ts:
    if t['layer']==32:rfpaths.append(LineString([(t['x1'],t['y1']),(t['x2'],t['y2'])]))
for a in ars:
    sweep=(a['end_angle']-a['start_angle'])%360;k=math.ceil(sweep/.1)
    rfpaths.append(LineString([(a['cx']+a['radius']*math.cos(math.radians(a['start_angle']+sweep*j/k)),a['cy']+a['radius']*math.sin(math.radians(a['start_angle']+sweep*j/k))) for j in range(k+1)]))
rfcenter=unary_union(rfpaths);edgegap=min(Point(v['x'],v['y']).distance(rfcenter)-v['diameter']/2-.055 for v in shield)
check(edgegap>=.255-6*UNIT,'RF fence land-edge gap (hole-edge equivalent 0.33 mm)')
keep=from_geojson(plan['QD_exclusion']);grounds={}
for layer in (1,2,3,4,5,32):
    geom=[]
    for r in rs:
        ni=r['net_index']
        if ni==65535 and r['polygon_index']!=65535:ni=int(polys[r['polygon_index']]['NET'])
        if ni!=65535 and ns[ni]['NAME']=='GND' and r['layer']==layer:geom.append(r['geometry'])
    ground=unary_union(geom);grounds[str(layer)]=ground.intersection(keep.buffer(-6*UNIT)).area
    check(grounds[str(layer)]<1e-8 if layer!=1 else ground.buffer(6*UNIT).covers(keep),'QD GND exclusion/retention layer '+str(layer))
    if layer in (5,32):
        check(all(ground.covers(Point(v['x'],v['y'])) for v in shield),'Shield reference land not connected on '+str(layer))
bottom=unary_union([r['geometry'] for r in rs if r['layer']==38 and r['name'].startswith('SURFACE_MASK_OPEN_')]);planned=from_geojson(plan['Bottom_mask_opening'])
mask_delta=bottom.symmetric_difference(planned).area;check(mask_delta<.005,'Bottom mask plan mismatch')
check(all(bottom.buffer(6*UNIT).covers(padshape(p)) for p in ps if p['component']!=65535 and cs[p['component']]['SOURCEDESIGNATOR']=='Q1'),'QD bonding pad is masked')
field=from_geojson(plan['QD_mask_field'])
check(rfcenter.buffer(.055+.25,quad_segs=64).difference(field.buffer(.13)).intersection(bottom).area<1e-6,'RF mask protection insufficient outside QD transition')
check(not any(r['layer'] in (35,36) for r in rs),'Explicit via paste regions')
for stream,kind in [('Tracks6/Data',4),('Arcs6/Data',1),('Fills6/Data',6)]:check(not any(r['body'][0] in (35,36) for r in binary_records(s[stream],kind)),'Unexpected paste primitive '+stream)
native=(H/'native_paste_audit.txt').read_text().splitlines() if (H/'native_paste_audit.txt').exists() else []
check(native and native[-1]=='COMPLETE','Native paste audit absent')
for row in native:
    x=row.split('|')
    if x[0]!='PAD':continue
    disabled=x[1]=='MOUNT' or x[1].startswith('SMP');check(x[7:10]==(['0']*3 if disabled else ['1']*3),'Pad paste state '+x[1]+'.'+x[2])
b=properties(s['Board6/Data'])[0]
mm=lambda value:float(value[:-3])*.0254
for i,v in zip((3,5,7,9,11,13),plan['stack']['copper_mm']):check(close(mm(b[f'V9_STACK_LAYER{i}_COPTHICK']),v),'Copper thickness '+str(i))
for i,v in zip((4,6,8,10,12),plan['stack']['dielectric_mm']):check(close(mm(b[f'V9_STACK_LAYER{i}_DIELHEIGHT']),v),'Dielectric thickness '+str(i))
check(any(r['NAME']=='RF_SHIELD_L5_L6' and r['VIASTYLE']!='Through Hole' for r in rules),'Shield routing rule still Through Hole')
solid=next(r for r in rules if r['NAME']=='ZIF24V2_GND_VIA_SOLID');check(solid['CONNECTSTYLE']=='Direct' and solid['SCOPE1EXPRESSION']=="(IsVia Or (IsPad And Not InComponent('*'))) And InNet('GND')",'Shield solid rule')
raw=snapshot(P/(B+'.PcbLib'))['QD4/Data'];pos=4+(struct.unpack_from('<I',raw,0)[0]&0xffffff);count=0
cx,cy=json.loads((PREV/'geometry.json').read_text())['qd_component_center']
while pos<len(raw):
    if raw[pos]!=2:pos+=5+(struct.unpack_from('<I',raw,pos+1)[0]&0xffffff);continue
    p=pad_record(raw,pos);pos=p['end'];q=planpads['Q1',p['number']];count+=1
    check(close(cx-p['coords'][0]*UNIT,q['x']) and close(cy+p['coords'][1]*UNIT,q['y']),'QD footprint library mismatch '+p['number'])
check(count==24,'QD library count')
html=(D/'Lower_RC_70pct_DRC.html').read_text(encoding='cp949',errors='replace');rows=re.findall(r'<td class="column1"><a href="#[^"]+">(.*?)</a></td>\s*<td class="column2">(\d+)</td>',html,re.S)
check(len(rows)>=15 and sum(int(n) for _,n in rows)==0,'DRC violations remain')
conn=json.loads((H/'connectivity.json').read_text());check(conn['passed'] and conn['pcb_sha256']==sha(P/(B+'.PcbDoc')),'Stale/failed connectivity')
report=dict(passed=not errors,errors=errors,pcb_sha256=sha(P/(B+'.PcbDoc')),pcblib_sha256=sha(P/(B+'.PcbLib')),schematic_sha256=sha(P/(B+'.SchDoc')),components=len(cs),pads=len(ps),nets=len(ns),vias=len(vs),shield_vias=len(shield),signal_vias=len(signal),capacitor_vias_remaining=len(cap_vias),resistor_RF_vias_remaining=0,resistor_DC_vias_remaining=6,QD_RF_vias_remaining=0,QD_DC_vias_remaining=18,QD=dict(cavity_mm=[4.3,4.3],inner_pad_end_square_mm=[4.7,4.7],minimum_cavity_pad_gap_mm=min(cavity_gaps),cavity_depth_mm=1.2,entry='Bottom/L6',non_plated=True,corner_radius_mm=.5,ground_area_by_layer_mm2=grounds),RF=dict(target_ohms=50,width_mm=.11,coplanar_gap_mm=.2,shield_land_edge_gap_min_mm=edgegap,shield_hole_edge_gap_min_mm=edgegap+.075,shield_span=['L5','L6'],shield_to_shield_edge_gap_mm=pairgap,nominal_center_pitch_mm=.4,stack_code=plan['stack']['code'],impedance_measurement=False),mask_geometry_difference_mm2=mask_delta,DRC=dict(checked_rules=len(rows),violations=sum(int(n) for _,n in rows),rules=dict(rows)),connectivity=conn['passed'],stored_connections=conn['stored_connection_line_count'])
(H/'validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if report['passed']:(D/'validation.json').write_text(json.dumps(report,indent=2));(D/'Lower_RC_70pct_validation.json').write_text(json.dumps(report,indent=2))
raise SystemExit(0 if report['passed'] else 1)
