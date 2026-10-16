"""Read-only 16-SMP layout review with fixed mounting holes and QD geometry.

No native design, canonical candidate or routing is edited. Connector bodies
use conservative 5.50000064 x 5.5 mm XY bounding boxes confirmed independently
from the saved SMP-FS-SBPCT STEP model by the parent team's CAD reviewer.
"""
from pathlib import Path
import json
import math
import hashlib
from itertools import combinations
from shapely.geometry import Point, Polygon, box
from shapely.affinity import rotate, translate
from shapely.ops import unary_union

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
SOURCE = ROOT/'script/qd38_pad_alignment_20261011/saved_revision_snapshot.json'
s = json.loads(SOURCE.read_text())
nominal_body_diameter = 5.5
body_r = nominal_body_diameter/2
body_half_x = 5.50000064/2
board = Polygon(s['board_outline'])
W,H=19.5,67.9


def pg(p):
    if p['shape']==1:
        return Point(p['x'],p['y']).buffer(p['size_x']/2,quad_segs=128)
    return translate(rotate(box(-p['size_x']/2,-p['size_y']/2,p['size_x']/2,p['size_y']/2),p['rotation'],origin=(0,0)),p['x'],p['y'])


mounts=[p for p in s['pads'] if not p['component']]
qd=unary_union([pg(p) for p in s['pads'] if p['component']=='Q1'])
cavity=box(7.6,39.85,11.9,45.15)
rc=[p for p in s['pads'] if p['component'] and p['component'][0] in 'RC']
rcgeo=[(p,pg(p)) for p in rc]
source_smp=[p for p in s['pads'] if p['component']=='SMP35']
source_center=next(p for p in source_smp if p['number']=='1')


def instantiate(rows):
    result=[]
    for i,(y,count) in enumerate(rows):
        xx=[2.75,9.75,16.75] if count==3 else [2.75,16.75]
        for j,x in enumerate(xx):
            name=f'P{i+1}{"L" if j==0 else "R" if j==len(xx)-1 else "C"}'
            pads=[]
            for p in source_smp:
                n=dict(p);n.update(component=name,x=p['x']+x-source_center['x'],y=p['y']+y-source_center['y'])
                pads.append(n)
            result.append(dict(name=name,x=x,y=y,pads=pads))
    return result


def min_result(rows):
    return min(rows,key=lambda z:z['gap_mm'])


def check(name,rows):
    pos=instantiate(rows)
    flatpads=[p for q in pos for p in q['pads']]
    pair_body=[];pair_land=[];pair_drill=[]
    for a,b in combinations(pos,2):
        pair_body.append(dict(objects=[a['name'],b['name']],gap_mm=math.hypot(a['x']-b['x'],a['y']-b['y'])-nominal_body_diameter))
        for pa in a['pads']:
            for pb in b['pads']:
                d=math.hypot(pa['x']-pb['x'],pa['y']-pb['y'])
                pair_land.append(dict(objects=[f"{pa['component']}.{pa['number']}",f"{pb['component']}.{pb['number']}"],gap_mm=d-(pa['size_x']+pb['size_x'])/2))
                pair_drill.append(dict(objects=[f"{pa['component']}.{pa['number']}",f"{pb['component']}.{pb['number']}"],gap_mm=d-(pa['hole']+pb['hole'])/2))
    mb=[];md=[];ml=[];pad_mount=[];drill_mount=[]
    body_qd=[];pad_qd=[];drill_cavity=[]
    collisions=[]
    for a in pos:
        centre=Point(a['x'],a['y'])
        body_box=box(a['x']-body_half_x,a['y']-body_r,a['x']+body_half_x,a['y']+body_r)
        body_qd.append(dict(connector=a['name'],gap_mm=body_box.distance(qd)))
        for m in mounts:
            d=math.hypot(a['x']-m['x'],a['y']-m['y'])
            point=Point(m['x'],m['y'])
            mb.append(dict(connector=a['name'],mount_xy=[m['x'],m['y']],gap_mm=body_box.distance(point)-m['size_x']/2))
            md.append(dict(connector=a['name'],mount_xy=[m['x'],m['y']],gap_mm=body_box.distance(point)-m['hole']/2))
        for p in a['pads']:
            g=pg(p); pcentre=Point(p['x'],p['y'])
            pad_qd.append(dict(pad=f"{a['name']}.{p['number']}",gap_mm=pcentre.distance(qd)-p['size_x']/2))
            drill_cavity.append(dict(pad=f"{a['name']}.{p['number']}",gap_mm=pcentre.distance(cavity)-p['hole']/2))
            for m in mounts:
                d=math.hypot(p['x']-m['x'],p['y']-m['y'])
                pad_mount.append(dict(pad=f"{a['name']}.{p['number']}",mount_xy=[m['x'],m['y']],gap_mm=d-(p['size_x']+m['size_x'])/2))
                drill_mount.append(dict(pad=f"{a['name']}.{p['number']}",mount_xy=[m['x'],m['y']],gap_mm=d-(p['hole']+m['hole'])/2))
            for rp,rg in rcgeo:
                gap=g.distance(rg)
                if gap<.15:
                    collisions.append(dict(smp_pad=f"{a['name']}.{p['number']}",rc_pad=f"{rp['component']}.{rp['number']}",gap_mm=gap,overlap_mm2=g.intersection(rg).area))
    return dict(name=name,rows=[dict(y=y,count=n) for y,n in rows],
                centres=[dict(name=a['name'],x=a['x'],y=a['y']) for a in pos],count=len(pos),
                top_count=sum(a['y']>42.5 for a in pos),bottom_count=sum(a['y']<42.5 for a in pos),
                nominal_body_to_body=min_result(pair_body),inter_connector_copper_land_gap=min_result(pair_land),inter_connector_drill_gap=min_result(pair_drill),
                body_board_edge_gap_nominal_mm=min(min(a['x']-body_r,W-a['x']-body_r,a['y']-body_r,H-a['y']-body_r) for a in pos),
                land_board_edge_gap_mm=min(min(p['x']-p['size_x']/2,W-p['x']-p['size_x']/2,p['y']-p['size_x']/2,H-p['y']-p['size_x']/2) for p in flatpads),
                drill_board_edge_gap_mm=min(min(p['x']-p['hole']/2,W-p['x']-p['hole']/2,p['y']-p['hole']/2,H-p['y']-p['hole']/2) for p in flatpads),
                body_bounding_box_to_mount_land_conservative=min_result(mb),body_bounding_box_to_mount_drill_conservative=min_result(md),
                smp_land_to_mount_land=min_result(pad_mount),smp_drill_to_mount_drill=min_result(drill_mount),
                body_bounding_box_projection_to_QD_padfield_conservative=min_result(body_qd),smp_copper_land_to_QD_padfield=min_result(pad_qd),smp_drill_to_cavity=min_result(drill_cavity),
                current_RC_pad_collisions_or_below_0p15_clearance=collisions,
                interpretation='Body-to-mount and body-to-QD use conservative saved-model XY bounding boxes. Body-to-QD is only XY projection: SMP bodies are Top and QD pads Bottom. Through pads/drills are true shared-layer obstacles. Existing RF/DC traces and shield vias were not collision-checked because this is placement review requiring rerouting.')


six=check('candidate_six_rows_3_3_2_gap_2_3_3_pitch_5p75',[(60.5,3),(54.75,3),(49,2),(36,2),(30.25,3),(24.5,3)])
two=check('comparison_two_columns_eight_rows_pitch_5p5_symmetric',[(61.75,2),(56.25,2),(50.75,2),(45.25,2),(39.75,2),(34.25,2),(28.75,2),(23.25,2)])

# With X fixed at 2.75, body non-overlap with the two fixed left mounting lands
# bounds the entire eight-row stack independently of QD exclusion.
topmount=min((p for p in mounts if p['y']>60),key=lambda p:p['x'])
bottommount=min((p for p in mounts if 17<p['y']<20),key=lambda p:p['x'])
top_limit=topmount['y']-body_r-topmount['size_x']/2
bottom_limit=bottommount['y']+body_r+bottommount['size_x']/2
report=dict(scope='Read-only placement review; no native PCB, schematic, library or canonical design modified.',
            body_model=dict(xy_bounding_box_mm=[5.50000064,5.5],source='Saved SMP-FS-SBPCT STEP body model dimensions independently verified by the parent team CAD reviewer.',
                            computation='Conservative XY bounding rectangle for body clearance to fixed mounting lands/drills and QD pad field. Vertical body pair gap uses 5.5 mm Y extent.'),
            source_snapshot=str(SOURCE.relative_to(ROOT)),source_pcb_sha256=s['source_sha256'],
            actual_pcb_sha256=hashlib.sha256(Path(s['source']).read_bytes()).hexdigest(),
            fixed_QD_cavity_bounds_mm=list(cavity.bounds),fixed_QD_padfield_bounds_mm=list(qd.bounds),
            recommended_review_candidate=six,two_column_comparison=two,
            two_column_stack_bound=dict(body_mount_land_no_overlap_y_range_mm=[bottom_limit,top_limit],available_height_mm=top_limit-bottom_limit,
                minimum_height_for_8_rows_at_5p5_pitch_mm=7*5.5,height_shortfall_mm=7*5.5-(top_limit-bottom_limit),
                four_rows_above_QD_outer_field_minimum_last_center_y_mm=qd.bounds[3]+body_r+3*5.5,
                note='This conservative saved-body bounding rectangle versus mounting-land envelope bound is not a fastener-head CAD check. It also does not by itself certify RF/DC routing.'),
            limitations=['Zero nominal body edge margin at X=2.75/16.75 leaves no board-edge or assembly tolerance margin; saved model X excess is only 0.00000064 mm numerical tolerance.',
                         'The new centre positions at Y=54.75/30.25 are illustrative added positions, not previously authorized fixed coordinates.',
                         'Current R/C footprints collide with the proposed centre connectors and must be repositioned in any implementation.',
                         'All sixteen RF and thirty-eight DC paths, mappings, shield fences and masks require a subsequent complete reroute and saved-native validation.'])
assert report['actual_pcb_sha256']==report['source_pcb_sha256']
(OUT/'placement_feasibility_measurements.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
