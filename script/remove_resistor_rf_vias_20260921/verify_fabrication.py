"""Verify the saved mechanical cavity outline and exported drill/slot coordinates."""
from pathlib import Path
import sys,json,struct,math,re
from shapely.geometry import Polygon,LineString,shape
from shapely.ops import unary_union
H=Path(__file__).resolve().parent;P=H.parents[1]/'QSTL_24DC_4MW_PCB';W=H.parent/'_support'
sys.path[:0]=[str(W/x) for x in ('qd_center_revision','final_routing/schematic','zif_revision_v2/board','rf_revision')]
from native_metadata_helpers import binary_records,properties,UNIT,sha
from build_routed_copy import snapshot
from verify_final_native_v2 import read_route
board=P/'QSTL_24DC_4MW_PCB.PcbDoc';s=snapshot(board);parts=[];counts=[]
for name,kind in [('Tracks6/Data',4),('Arcs6/Data',1)]:
    count=0
    for rec in binary_records(s[name],kind):
        b=rec['body']
        if b[0]!=58:continue
        count+=1
        if kind==4:
            x1,y1,x2,y2,w=struct.unpack_from('<5i',b,13);pts=[(x1*UNIT,y1*UNIT),(x2*UNIT,y2*UNIT)]
        else:
            x,y,r=struct.unpack_from('<3i',b,13);a0,a1=struct.unpack_from('<2d',b,25);sweep=(a1-a0)%360;assert abs(r*UNIT-.5)<4*UNIT
            pts=[((x+r*math.cos(math.radians(a0+sweep*k/100)))*UNIT,(y+r*math.sin(math.radians(a0+sweep*k/100)))*UNIT) for k in range(101)]
        parts.append(LineString(pts))
    counts.append(count)
assert counts==[4,4],counts
native=unary_union(parts);wanted=shape(json.loads((H/'plan.json').read_text())['cavity']['geometry']).boundary
# The plan/Gerber uses 32 straight chords per quarter-circle, while native
# Altium stores exact arcs. Bound their analytical sagitta plus native grid.
chord_error=.5*(1-math.cos(math.pi/128))
assert native.hausdorff_distance(wanted)<chord_error+6*UNIT
assert max(abs(a-b) for a,b in zip(native.bounds,wanted.bounds))<6*UNIT
assert b'BOTTOM BLIND SLOT: 4.3 x 4.3, R0.5, DEPTH 1.2 mm; NON-PLATED' in s['Texts6/Data']
F=P/'fabrication/RF50_QD_cavity';slot=(F/'bottom blind slots layer.gbr').read_text();coords=[(int(a)/1e6,int(b)/1e6) for a,b in re.findall(r'X(\d+)Y(\d+)D\d+\*',slot)]
poly=Polygon(coords);assert poly.boundary.hausdorff_distance(wanted)<.000002
ts,ars,vs=read_route(s,properties(s['Nets6/Data']));shields=[v for v in vs if v['net']=='GND']
drill=(F/'L6_L5_laser_microvias.drl').read_text();holes=[(float(a),float(b)) for a,b in re.findall(r'X([\d.]+)Y([\d.]+)',drill)]
assert len(holes)==470 and all(min(math.dist(p,(v['x'],v['y'])) for v in shields)<.000001 for p in holes)
assert 'T01C0.100' in drill
prj=(P/'QSTL_24DC_4MW_PCB.PrjPcb').read_text(encoding='cp1252');assert 'DocumentPath=QSTL_24DC_4MW_PCB.PcbDoc' in prj
v=json.loads((H/'validation.json').read_text());assert sha(board)==v['pcb_sha256']
report=dict(passed=True,pcb_sha256=sha(board),native_mechanical2_tracks=counts[0],native_mechanical2_arcs=counts[1],native_depth_note=True,pocket_bounds_mm=list(poly.bounds),laser_drill_positions=len(holes),original_project_document=True,complete_production_CAM=False)
(P/'docs/fabrication_validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
