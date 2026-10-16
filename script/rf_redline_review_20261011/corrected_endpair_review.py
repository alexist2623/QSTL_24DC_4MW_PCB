"""Read-only corrected 2+6 / 6+2 SMP placement feasibility review.

The two end connectors are a horizontal inward pair. Each half also has three
outboard side pairs. Circle envelopes are provisional pending exact STEP checks.
"""
from pathlib import Path
import json, math, hashlib
from itertools import combinations
from shapely.geometry import Point, box
from shapely.affinity import rotate, translate
from shapely.ops import unary_union

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
S=ROOT/'script/qd38_pad_alignment_20261011/saved_revision_snapshot.json'
s=json.loads(S.read_text())


def pg(p):
    if p['shape']==1:return Point(p['x'],p['y']).buffer(p['size_x']/2,quad_segs=128)
    return translate(rotate(box(-p['size_x']/2,-p['size_y']/2,p['size_x']/2,p['size_y']/2),p['rotation'],origin=(0,0)),p['x'],p['y'])


mounts=[p for p in s['pads'] if not p['component']]
qd=unary_union([pg(p) for p in s['pads'] if p['component']=='Q1'])
cavity=box(7.6,39.85,11.9,45.15)
src=[p for p in s['pads'] if p['component']=='SMP35']
centre=next(p for p in src if p['number']=='1')
rc=[(p,pg(p)) for p in s['pads'] if p['component'] and p['component'][0] in 'RC']


def placement(end_x,end_y,outer_y):
    rows=[(85-end_y,[end_x,19.5-end_x],'upper_inboard_end')]
    rows.extend((85-y,[2.75,16.75],'upper_outer_side') for y in outer_y)
    rows.extend((y,[2.75,16.75],'lower_outer_side') for y in reversed(outer_y))
    rows.append((end_y,[end_x,19.5-end_x],'lower_inboard_end'))
    out=[]
    for i,(y,xs,kind) in enumerate(rows):
        for j,x in enumerate(xs):
            name=f'P{i+1}{"L" if j==0 else "R"}'
            pp=[dict(p,component=name,x=p['x']+x-centre['x'],y=p['y']+y-centre['y']) for p in src]
            out.append(dict(name=name,x=x,y=y,kind=kind,pads=pp))
    return out


def minimum(values):return min(values,key=lambda v:v['gap_mm'])


def review(name,pos):
    pairs=[];land_pairs=[];drill_pairs=[];bmount=[];bdmount=[];pmount=[];dmount=[];pqd=[];dcav=[];collisions=[]
    for a,b in combinations(pos,2):
        pairs.append(dict(objects=[a['name'],b['name']],gap_mm=math.hypot(a['x']-b['x'],a['y']-b['y'])-5.5))
        for pa in a['pads']:
            for pb in b['pads']:
                d=math.hypot(pa['x']-pb['x'],pa['y']-pb['y'])
                land_pairs.append(dict(objects=[pa['component']+'.'+pa['number'],pb['component']+'.'+pb['number']],gap_mm=d-(pa['size_x']+pb['size_x'])/2))
                drill_pairs.append(dict(objects=[pa['component']+'.'+pa['number'],pb['component']+'.'+pb['number']],gap_mm=d-(pa['hole']+pb['hole'])/2))
    for a in pos:
        for m in mounts:
            d=math.hypot(a['x']-m['x'],a['y']-m['y'])
            bmount.append(dict(connector=a['name'],mount_xy=[m['x'],m['y']],gap_mm=d-2.75-m['size_x']/2))
            bdmount.append(dict(connector=a['name'],mount_xy=[m['x'],m['y']],gap_mm=d-2.75-m['hole']/2))
        for p in a['pads']:
            pc=Point(p['x'],p['y']);g=pg(p)
            pqd.append(dict(pad=p['component']+'.'+p['number'],gap_mm=pc.distance(qd)-p['size_x']/2))
            dcav.append(dict(pad=p['component']+'.'+p['number'],gap_mm=pc.distance(cavity)-p['hole']/2))
            for m in mounts:
                d=math.hypot(p['x']-m['x'],p['y']-m['y'])
                pmount.append(dict(pad=p['component']+'.'+p['number'],mount_xy=[m['x'],m['y']],gap_mm=d-(p['size_x']+m['size_x'])/2))
                dmount.append(dict(pad=p['component']+'.'+p['number'],mount_xy=[m['x'],m['y']],gap_mm=d-(p['hole']+m['hole'])/2))
            for q,gq in rc:
                d=g.distance(gq)
                if d<.15:collisions.append(dict(smp_pad=p['component']+'.'+p['number'],rc_pad=q['component']+'.'+q['number'],gap_mm=d,overlap_mm2=g.intersection(gq).area))
    pp=[p for a in pos for p in a['pads']]
    return dict(name=name,centres=[{k:v for k,v in a.items() if k!='pads'} for a in pos],count=len(pos),
        top_count=sum(a['y']>42.5 for a in pos),bottom_count=sum(a['y']<42.5 for a in pos),
        full_body_circle_to_circle_provisional=minimum(pairs),full_body_circle_to_mount_land_provisional=minimum(bmount),
        full_body_circle_to_mount_drill_provisional=minimum(bdmount),
        inter_SMP_land_gap=minimum(land_pairs),inter_SMP_drill_gap=minimum(drill_pairs),
        SMP_land_to_fixed_mount_land=minimum(pmount),SMP_drill_to_fixed_mount_drill=minimum(dmount),
        SMP_land_to_QD_padfield=minimum(pqd),SMP_drill_to_cavity=minimum(dcav),
        body_board_edge_gap_nominal_mm=min(min(a['x']-2.75,19.5-a['x']-2.75,a['y']-2.75,67.9-a['y']-2.75) for a in pos),
        land_board_edge_gap_mm=min(min(p['x']-p['size_x']/2,19.5-p['x']-p['size_x']/2,p['y']-p['size_x']/2,67.9-p['y']-p['size_x']/2) for p in pp),
        drill_board_edge_gap_mm=min(min(p['x']-p['hole']/2,19.5-p['x']-p['hole']/2,p['y']-p['hole']/2,67.9-p['y']-p['hole']/2) for p in pp),
        current_RC_pad_conflicts=collisions)


candidate=review('corrected_horizontal_inboard_end_pairs_and_three_outboard_pairs_each_half',placement(6.875,22.25,[26.30,32.05,37.80]))
initial=review('rejected_initial_end_pair_locations_with_unchanged_side_bank_limits',placement(6.75,20.5,[24.5,30.25,36.0]))
report=dict(scope='Read-only corrected placement review, not a routed or approved native design.',
    topology='Top horizontal inboard pair, three upper outer side pairs, empty QD-side centre row, three lower outer side pairs, bottom horizontal inboard pair.',
    interpretation='Each half contains 8 SMP connectors. Inboard end pair positions and all proposed coordinates are review candidates. The rejected six-row 3/3/2 interpretation is excluded.',
    candidate=candidate,rejected_initial_assumption=initial,
    source_pcb_sha256=s['source_sha256'],actual_pcb_sha256=hashlib.sha256(Path(s['source']).read_bytes()).hexdigest(),
    limitations=['Full bodies provisionally use diameter 5.5 mm circles; exact placed STEP shape collision verification is required.',
       'Body circle overlap does not certify a collision in irregular STEP models; positive circle gap proves body separation only if the full XY model is contained within the circle.',
       'SMP through-pad and drill checks use the saved native footprint dimensions. Fixed mounting holes and rotated QD geometry are unchanged.',
       'Zero body-to-board nominal margin on outer columns remains. No screw-head or mating cable envelope is included.',
       'Existing R/C, RF/DC traces, shield vias and masks must be rearranged. This is not a complete reroute proof.'])
assert report['source_pcb_sha256']==report['actual_pcb_sha256']
(OUT/'corrected_endpair_measurements.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
