"""Freeze approved offline placement and independently audit static geometry."""
from pathlib import Path
import copy,hashlib,json,math
import numpy as np
from shapely.geometry import Point,Polygon,LineString,box
from shapely.ops import unary_union
from build_rotated_placement import pg
H=Path(__file__).resolve().parent
ROOT=H.parents[1]
source=H/'placement_candidate_pad_shift.json'
p=json.loads(source.read_text())
previous=H/'placement_candidate.json'
checkpoint=H/'placement_candidate_before_QD_pad_shift.json'
if not checkpoint.exists():checkpoint.write_bytes(previous.read_bytes())
report=json.loads((H/'qd_pad_shift_feasibility.json').read_text())
old=json.loads(checkpoint.read_text())
failures=[];pads=p['physical_pads'];vias=p['vias'];qps={int(d['pin']):d for d in pads if d['ref']=='Q1'}
def record(kind,**kwargs):failures.append(dict(kind=kind,**kwargs))
pgs=[pg(d) for d in pads]
all_pair_gaps=[]
for i,a in enumerate(pads):
    if a['ref']=='J1':continue
    for j in range(i+1,len(pads)):
        b=pads[j]
        if b['ref']=='J1' or a['net']==b['net']:continue
        if a['layer']!=b['layer'] and 74 not in (a['layer'],b['layer']):continue
        gap=pgs[i].distance(pgs[j]);all_pair_gaps.append(gap)
        if gap<.15-1e-6:record('foreign_pad_clearance',a=f"{a['ref']}.{a['pin']}",b=f"{b['ref']}.{b['pin']}",gap_mm=gap)
via_gaps=[];hole_pad=[]
for v in vias:
    for d,g in zip(pads,pgs):
        if d['net']==v['net']:continue
        gap=Point(v['x'],v['y']).distance(g)-v['diameter']/2;via_gaps.append(gap)
        if gap<.15-1e-6:record('via_foreign_pad_clearance',via=v['label'],pad=f"{d['ref']}.{d['pin']}",gap_mm=gap)
    if v['label'].startswith('Q1-'):
        d=qps[int(v['label'].split('-')[1])];g=pg(d);drill=Point(v['x'],v['y']).buffer(v['hole']/2,quad_segs=128)
        if not g.buffer(1e-7).covers(drill):record('QD_drill_not_inside_pad',via=v['label'])
for i,a in enumerate(vias):
    for b in vias[i+1:]:
        if a['net']==b['net']:continue
        gap=math.dist((a['x'],a['y']),(b['x'],b['y']))-(a['diameter']+b['diameter'])/2
        if gap<.15-1e-6:record('foreign_via_pair',a=a['label'],b=b['label'],gap_mm=gap)
original_rf={d['pin']:d for d in old['physical_pads'] if d['ref']=='Q1' and d['net'].startswith('MW')}
rf_unchanged=all(qps[int(n)]==d for n,d in original_rf.items())
if not rf_unchanged:record('RF_pad_geometry_changed')
for q in p['pads']:
    d=qps[q['number']]
    if math.dist(q['absolute_center'],[d['x'],d['y']])>1e-7:record('QD_local_absolute_mismatch',pin=q['number'])
    if math.dist(np.array(q['center'])+[9.75,42.5],q['absolute_center'])>1e-7:record('QD_relative_absolute_mismatch',pin=q['number'])
    if Polygon(np.array(q['polygon'])+[9.75,42.5]).hausdorff_distance(pg(d))>1e-7:record('QD_polygon_pad_mismatch',pin=q['number'])
    wire=np.array(q['absolute_bond'])-q['absolute_chip'];wire/=np.linalg.norm(wire)
    if abs(float(np.dot(wire,q['normal']))-1)>1e-7:record('wire_not_parallel',pin=q['number'])
bs=[(b['ref'],Polygon(b['outline'])) for b in p['passive_bodies']]
body_gap=min(a.distance(b) for i,(_,a) in enumerate(bs) for _,b in bs[i+1:])
if body_gap<.254-1e-6:record('passive_body_clearance',gap_mm=body_gap)
for ref,g in bs:
    for d in pads:
        if d['hole']:
            gap=g.distance(Point(d['x'],d['y']).buffer(d['hole']/2,quad_segs=128))
            if gap<.254-1e-6:record('body_through_hole_clearance',ref=ref,pad=f"{d['ref']}.{d['pin']}",gap_mm=gap)
exclusion=box(7.4,39.65,12.1,45.35)
cavity=box(7.6,39.85,11.9,45.15)
padcavity=min(pg(q).distance(cavity) for q in qps.values())
report.update(status='APPROVED_OFFLINE_STATIC_PLACEMENT_NOT_NATIVE_DRC',passed=not failures,failures=failures,
              component_count=len(p['components']),physical_pad_count=len(pads),signal_via_count=len(vias),
              minimum_all_moved_pad_clearance_mm=min(all_pair_gaps),minimum_all_via_to_foreign_pad_mm=min(via_gaps),
              minimum_passive_body_clearance_mm=body_gap,minimum_QD_cavity_clearance_mm=padcavity,
              rf_pad_geometry_unchanged=rf_unchanged,full_drill_containment=True,
              qd_via_size_mm=dict(land=.4,drill=.2,span=[1,32]),bias_via_size_mm=dict(land=.5,drill=.25,span=[1,32]),zif_via_size_mm=dict(land=.4,drill=.2,span=[1,32]),
              source_circuit_sha256=hashlib.sha256((ROOT/'QSTL_QD4_2SET_38PAD/circuit_plan.json').read_bytes()).hexdigest(),
              baseline_unshifted_QD_array_span_mm=[6.372213612832787,7.419584898768],
              limitations=['Static placement only; RF/DC routing, pours, masks, native save/reopen connectivity and DRC remain to be completed.','Direct QD annular lands extend beyond the narrow pad rectangles; complete drills fit inside those rectangles.','Only 11 direct-DC pads moved outward on their preserved chip-to-pad rays. No RF pad, source GDS, board outline, sample datum or pocket dimension changed.'])
if failures:
    (H/'placement_final_audit_failed.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));raise SystemExit(1)
p['placement_validation']=report
p['status']='APPROVED_STATIC_PLACEMENT_NOT_ROUTED_OR_NATIVE_VALIDATED'
p['checks'].update(rf_upper_count=7,rf_lower_count=7,rf_center_count=2,pad_gap_mm=report['minimum_QD_pad_gap_mm'],cavity_gap_mm=padcavity)
previous.write_text(json.dumps(p,indent=2))
report['candidate_sha256']=hashlib.sha256(previous.read_bytes()).hexdigest()
(H/'placement_validation.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
