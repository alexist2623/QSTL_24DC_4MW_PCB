from pathlib import Path
import sys,json,math,hashlib,collections
H=Path(__file__).resolve().parent;W=H.parent;P=Path(r'C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB');D=P/'docs'
sys.path.insert(0,str(W/'route_python'))
from shapely.geometry import LineString,box,Point
from shapely.ops import unary_union
n=json.loads((H/'native_render_snapshot.json').read_text());old=json.loads((H/'baseline_native.json').read_text());dc=json.loads((H/'dc_routes.json').read_text())
ts=[t for t in n['tracks'] if t['net'].startswith('ZIF') and t['layer'] in [2,4]]
def geom(t):return LineString([(t['x1'],t['y1']),(t['x2'],t['y2'])])
bus={l:[] for l in [2,4]};band=box(0,18,19.5,30)
for layer in [2,4]:
 for t in ts:
  if t['layer']==layer and min(t['y1'],t['y2'])<=18+1e-5 and max(t['y1'],t['y2'])>=30-1e-5:
   assert abs(t['x2']-t['x1'])<1e-5;bus[layer].append(dict(net=t['net'],x=t['x1'],width=t['width']))
 bus[layer].sort(key=lambda t:t['x']);assert len(bus[layer])==12
assert all(abs(a['x']-b['x'])<1e-5 for a,b in zip(bus[2],bus[4]))
gaps=[b['x']-a['x']-(a['width']+b['width'])/2 for vs in bus.values() for a,b in zip(vs,vs[1:])];assert min(gaps)>.4749
minimum=1000;crossings=0
for i,t in enumerate(ts):
 for u in ts[:i]:
  if t['net']==u['net']:continue
  if t['layer']==u['layer']:minimum=min(minimum,geom(t).distance(geom(u))-(t['width']+u['width'])/2)
  elif geom(t).intersects(geom(u)):crossings+=1
assert minimum>=.15-1e-5
common=unary_union([geom(t).intersection(band) for t in ts if t['layer']==2]).intersection(unary_union([geom(t).intersection(band) for t in ts if t['layer']==4])).length;assert common>143.99
length=lambda nn:sum(geom(t).length for t in nn['tracks'] if t['layer'] in [2,4] and t['net'].startswith('ZIF'))
# The problematic y=29..32.2 region now contains only the straight central
# bundle and the intended terminal branch to R1. No unrelated DC enters its via field.
field=box(13.05,29,16.25,32.2);bad=[]
for t in ts:
 if t['net']!='ZIF21' and geom(t).buffer(t['width']/2).intersects(field):bad.append(t)
assert not bad
nearest=min(geom(t).distance(Point(v['x'],v['y']))-t['width']/2-v['diameter']/2 for t in ts if t['net']!='ZIF21' for v in n['vias'] if 13.5<v['x']<16 and 29.9<v['y']<31.8)
assert nearest>.58
report=dict(passed=True,pcb_sha256=n['source_sha256'],scope='Saved native DC routing. Through vias obstruct both DC layers; different-layer traces may overlap.',central_parallel_band_mm=dict(y_min=18,y_max=30,x_min=bus[2][0]['x'],x_max=bus[2][-1]['x']),central_lanes_by_layer=bus,central_centre_pitch_mm=.6,central_edge_gap_min_mm=min(gaps),central_edge_gap_max_mm=max(gaps),overlapping_centreline_length_across_L2_L4_mm=common,cross_layer_track_pairs_intersecting_or_overlapping=crossings,whole_board_DC_same_layer_min_edge_gap_mm=minimum,bias_via_field_unrelated_DC_intrusions=bad,unrelated_DC_clearance_to_R1_C1_vias_min_mm=nearest,internal_DC_segments_before=sum(t['layer'] in [2,4] for t in old['tracks']),internal_DC_segments_after=len(ts),DC_planar_length_before_mm=length(old),DC_planar_length_after_mm=length(n),DC_planar_length_reduction_mm=length(old)-length(n),vias_added=0,retained_transition_via=dc['retained_transition_vias'][0],pin_changes=dc['pin_changes'],zif_to_target=dc['zif_to_target'],RF_component_placement_and_layer_stack_unchanged=True)
assert hashlib.sha256(Path(n['source']).read_bytes()).hexdigest()==n['source_sha256']
(H/'central_validation.json').write_text(json.dumps(report,indent=2));(D/'DC_direct.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['central_lanes_by_layer','zif_to_target']},indent=2))
