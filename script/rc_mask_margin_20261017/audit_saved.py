"""Independently inspect the saved native PCB, connectivity, masks and mapping."""
from pathlib import Path
import sys,json,math,hashlib,struct,collections
import numpy as np
from shapely.geometry import Point,LineString,Polygon,box,shape
from shapely.ops import unary_union
from shapely.strtree import STRtree
H=Path(__file__).resolve().parent;ROOT=H.parents[1];P=ROOT/'QSTL_QD4_2SET_38PAD'
sys.path[:0]=[str(ROOT/'script/qd38_rotation_20261011'),str(ROOT/'script/_support/qd_center_revision')]
from audit_saved_revision_surface import read_snapshot,UNIT
from native_metadata_helpers import properties,binary_records,pads_stream,olefile
from prepare_native_revision_rules import read_rules
plan=json.loads((H/'candidate.json').read_text());sch=json.loads((P/'schematic_validation.json').read_text())
pcb=P/'QSTL_QD4_2SET_38PAD.PcbDoc';source_digest=hashlib.sha256(pcb.read_bytes()).hexdigest();pads,regions,tracks,vias,outline=read_snapshot(pcb,sch)
errors=[];checks={};tol=.000012
def check(test,label,detail=None):
    if not test:errors.append(dict(issue=label,detail=detail))
by={(p['ref'],p['pin']):p for p in pads}
check(len(by)==len(pads)==241,'pad_count',len(pads))
for p in plan['physical_pads']:
    key=(p['ref'],p['pin']);a=by.get(key)
    if a is None:check(False,'missing_pad',key);continue
    check(all(abs(a[k]-p[k])<tol for k in ('x','y','sx','sy','hole')) and abs((a['rotation']-p['rotation']+180)%360-180)<1e-7,'pad_geometry',key)
    check(a['net']==p['net'] and a['layer']==p['layer'],'pad_net_layer',key)
actual={}
for p in pads:
    if p['ref'] and p['net']:actual.setdefault(p['net'],[]).append(p['ref']+'-'+p['pin'])
check({n:sorted(v) for n,v in actual.items()}=={n:sorted(v) for n,v in sch['nets'].items()},'schematic_membership')
check(hashlib.sha256((P/'QSTL_QD4_2SET_38PAD.SchDoc').read_bytes()).hexdigest()==sch['schematic_sha256'],'schematic_hash')
expected=plan['vias']+plan['shield_vias'];check(len(vias)==len(expected),'via_count',len(vias))
tree=STRtree([Point(v['x'],v['y']) for v in vias]);used=set()
for v in expected:
    k=int(tree.nearest(Point(v['x'],v['y'])));a=vias[k];used.add(k)
    check(all(abs(a[z]-v[z])<tol for z in ('x','y','diameter','hole')) and all(a[z]==v[z] for z in ('net','low','high')),'via_mismatch',v['label'])
check(len(used)==len(vias),'via_identity_unique')
check(outline.hausdorff_distance(Polygon(plan['board_outline']))<tol,'outline')
ground={l:unary_union([r['geometry'] for r in regions if r['net']=='GND' and r['layer']==l]) for l in (1,2,3,4,5,32)}
for family,key in [('GND','ground_regions'),('mask','solder_openings')]:
    for ll,expected_geo in plan[key].items():
        a=ground[int(ll)] if family=='GND' else unary_union([r['geometry'] for r in regions if r['layer']==int(ll)])
        expected_geo=shape(expected_geo)
        if not (family=='GND' and ((int(ll)==5 and plan.get('L5_component_cutouts')) or (int(ll)==32 and plan.get('bond_pad_width_mm')))):
            expected_geo=expected_geo.simplify(.0002,preserve_topology=True)
        check(a.hausdorff_distance(expected_geo)<.00002,'surface_mismatch',[family,ll,a.hausdorff_distance(expected_geo)])
excluded=shape(plan['qd_ground_exclusion'])
for ll,g in ground.items():
    area=g.intersection(excluded).area
    # The native 2.54 nm coordinate lattice rounds the ideal boundary. Test
    # the one-coordinate-unit inset as well as recording the raw intersection.
    inset_area=g.intersection(excluded.buffer(-UNIT)).area
    check(area>20 if ll==1 else inset_area<1e-8,'QD_ground_exclusion',[ll,area,inset_area])
checks['QD_exclusion_boundary_tolerance_mm']=UNIT
layers=(1,2,3,4,5,32);copper={}
for n in plan['nets']:
    copper[n]={l:[] for l in layers}
for p in pads:
    if p['net']:
        for l in layers:
            if p['layer'] in (l,74):copper[p['net']][l].append(p['geometry'])
for t in tracks:
    if t['net'] and t['layer'] in layers:copper[t['net']][t['layer']].append(t['geometry'].buffer(t['width']/2,quad_segs=32))
for v in vias:
    for l in layers:
        if v['low']<=l<=v['high']:copper[v['net']][l].append(Point(v['x'],v['y']).buffer(v['diameter']/2,quad_segs=64))
for l,g in ground.items():copper['GND'][l].append(g)
connect={}
for n,bank in copper.items():
    polys=[];lls=[]
    for l,geos in bank.items():
        u=unary_union([g.buffer(.000006) for g in geos])
        ps=list(u.geoms) if hasattr(u,'geoms') else ([] if u.is_empty else [u])
        polys.extend(ps);lls.extend([l]*len(ps))
    parents=list(range(len(polys)))
    def find(i):
        while parents[i]!=i:parents[i]=parents[parents[i]];i=parents[i]
        return i
    bridges=[(Point(v['x'],v['y']),v['low'],v['high']) for v in vias if v['net']==n]
    bridges += [(Point(p['x'],p['y']),1,32) for p in pads if p['net']==n and p['hole']>0]
    tr=STRtree(polys)
    for xy,lo,hi in bridges:
        hits=[int(i) for i in tr.query(xy,predicate='intersects') if lo<=lls[int(i)]<=hi]
        for i in hits[1:]:parents[find(i)]=find(hits[0])
    islands=len({find(i) for i in range(len(polys))});connect[n]=islands;check(islands==1,'disconnected_net',[n,islands])
checks['connected_nets']=sum(x==1 for x in connect.values());checks['net_islands']=connect
dc_layers={n:sorted({t['layer'] for t in tracks if t['net']==n and t['layer']!=1}) for n in plan['nets'] if n.startswith('DC')}
check(all(v in ([2],[3]) for v in dc_layers.values()),'DC_single_layer',dc_layers);checks['DC_layer_nets']=dict(collections.Counter(v[0] for v in dc_layers.values() if v))
check(not any(v['net'].startswith(('MW','S')) for v in vias),'RF_signal_via')
check(not any(t['net'] and t['net'].startswith(('MW','S')) and t['layer']!=32 for t in tracks),'RF_nonbottom')
full_rf=unary_union([t['geometry'].buffer(t['width']/2,quad_segs=32) for t in tracks if t['net'] and t['net'].startswith(('MW','S')) and t['layer']==32])
checks['min_shield_hole_RF_gap_mm']=min(full_rf.distance(Point(v['x'],v['y']))-v['hole']/2 for v in vias if v['net']=='GND')
check(checks['min_shield_hole_RF_gap_mm']>=.32999,'shield_RF_gap')
for v in vias:
    if v['net']!='GND':continue
    land=Point(v['x'],v['y']).buffer(v['diameter']/2,quad_segs=64)
    for l in (5,32):check(land.difference(ground[l].buffer(.000025)).area<1e-7,'uncovered_shield_land',[l,v['x'],v['y']])
with olefile.OleFileIO(pcb) as o:
    blob={'/'.join(k):o.openstream(k).read() for k in o.listdir()}
board=properties(blob['Board6/Data'])[0]
checks['layer_names']={k:v for k,v in board.items() if 'NAME' in k and 'LAYER' in k and v in ('L2_DC_A','L3_DC_B','L4_GND','L3_GND','L4_DC_B')}
checks['stored_connections']=struct.unpack('<I',blob['Connections6/Header'][:4])[0] if 'Connections6/Header' in blob else None
check(checks['stored_connections']==0,'stored_connections',checks['stored_connections'])
rules=read_rules(pcb);checks['rules']=len(rules)
checks['native_sha256']=source_digest
check(source_digest==hashlib.sha256(pcb.read_bytes()).hexdigest(),'source_changed_during_audit')
report=dict(passed=not errors,errors=errors,checks=checks,counts=dict(pads=len(pads),vias=len(vias),tracks_and_arcs=len(tracks),regions=len(regions)))
(H/'saved_native_audit.json').write_text(json.dumps(report,indent=2))
print(json.dumps(dict(passed=not errors,error_count=len(errors),errors=errors[:15],counts=report['counts'],checks={k:v for k,v in checks.items() if k!='net_islands'}),indent=2))
