"""Independent local-delta, RF contact and native-grid signal verification."""
from pathlib import Path
from collections import defaultdict
import copy
import hashlib
import json
import math
import sys

from shapely.geometry import Point, LineString, box
from shapely.ops import unary_union

H=Path(__file__).resolve().parent
ROT=H.parent/'qd38_rotation_20261011'
sys.path.insert(0,str(ROT));sys.path.insert(0,str(H.parent/'qd38_carrier_20261010'))
from route_circuit import pgeom
from audit_candidate import audit as signal_audit
from audit_rf_topology import audit as rf_audit
from route_rf_rotated import arc_line

UNIT=2.54e-6
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
BASE=H/'before_alignment/full_copper_candidate.json'
CANDIDATE=H/'alignment_routed_candidate.json'


def quantized(p):
    q=copy.deepcopy(p)
    snap=lambda v:round(v/UNIT)*UNIT
    for pad in q['physical_pads']:
        for k in ('x','y','sx','sy','hole'):pad[k]=snap(pad[k])
    for via in q['vias']:
        for k in ('x','y','diameter','hole'):via[k]=snap(via[k])
    for t in q['tracks']:
        t['a']=[snap(v) for v in t['a']];t['b']=[snap(v) for v in t['b']];t['width']=snap(t['width'])
    for arc in q['arcs']:
        for k in ('cx','cy','radius','width'):arc[k]=snap(arc[k])
    return q


def main():
    source=json.loads(BASE.read_text());p=json.loads(CANDIDATE.read_text());failures=[]
    def check(ok,kind,detail=None):
        if not ok:failures.append(dict(kind=kind,detail=detail))
    for key in ('nets','pinmap','components','board_outline','sample_center','cavity_mm','cavity_depth_mm','stack','arcs'):
        check(source[key]==p[key],'unexpected_delta_'+key)
    nonqd=lambda pp:[x for x in pp['physical_pads'] if x['ref']!='Q1']
    check(nonqd(source)==nonqd(p),'non_QD_pad_changed')
    untouchedvia=lambda pp:[x for x in pp['vias'] if not x['label'].startswith('Q1-')]
    check(untouchedvia(source)==untouchedvia(p),'non_QD_via_changed')
    selected=lambda pp:[x for x in pp['tracks'] if not(x['net'].startswith('DC') and x['layer'] in (2,4))]
    check(selected(source)==selected(p),'non_internal_DC_track_changed')
    # Per-net line unions avoid treating harmless split/coalesced segments as
    # physical changes. Retained distant routes must cover one another.
    local=box(5.5,36,14,49);geoms=[];net_changes=[]
    def bynet(pp):
        result=defaultdict(list)
        for t in pp['tracks']:
            if t['net'].startswith('DC') and t['layer'] in (2,4):
                result[(t['net'],t['layer'])].append(LineString([t['a'],t['b']]))
        return {k:unary_union(v) for k,v in result.items()}
    before,after=bynet(source),bynet(p)
    check(before.keys()==after.keys(),'DC_net_or_layer_set_changed')
    for key,old in before.items():
        new=after[key]
        added=new.difference(old.buffer(1e-7));removed=old.difference(new.buffer(1e-7));change=unary_union([added,removed])
        outside=change.difference(local)
        check(outside.length<1e-7,'DC_changed_outside_local_box',dict(net=key[0],layer=key[1],outside_length_mm=outside.length))
        if not change.is_empty:
            geoms.append(change)
            net_changes.append(dict(net=key[0],layer=key[1],changed_centerline_bounds_mm=list(change.bounds),added_length_mm=added.length,removed_length_mm=removed.length))
    qdpads={v['pin']:v for v in p['physical_pads'] if v['ref']=='Q1'}
    oldpads={v['pin']:v for v in source['physical_pads'] if v['ref']=='Q1'}
    RF=[]
    for row in p['pinmap']:
        if not row['rf']:continue
        pin=str(row['qd_pad']);net=row['rf_net'];pad=pgeom(qdpads[pin])
        paths=[LineString([t['a'],t['b']]).buffer(t['width']/2,quad_segs=128) for t in p['tracks'] if t['net']==net]
        paths += [arc_line(a).buffer(a['width']/2,quad_segs=128) for a in p['arcs'] if a['net']==net]
        copper=unary_union(paths);overlap=pad.intersection(copper).area
        moved=math.dist((oldpads[pin]['x'],oldpads[pin]['y']),(qdpads[pin]['x'],qdpads[pin]['y']))
        check(overlap>1e-8,'RF_QD_pad_no_copper_overlap',pin)
        RF.append(dict(pin=pin,net=net,pad_movement_mm=moved,copper_overlap_mm2=overlap,RF_geometry_unchanged=True))
    vias=[]
    for v in p['vias']:
        if not v['label'].startswith('Q1-'):continue
        pin=v['label'].split('-')[1];g=pgeom(qdpads[pin]);pt=Point(v['x'],v['y'])
        margin=g.boundary.distance(pt)-v['hole']/2
        check(g.covers(pt) and margin>=-1e-6,'QD_drill_outside_pad',dict(pin=pin,margin_mm=margin))
        check(abs(v['diameter']-.35)<1e-12 and abs(v['hole']-.20)<1e-12,'QD_via_size',pin)
        vias.append(dict(pin=pin,drill_containment_margin_mm=margin))
    qp=quantized(p);quant=signal_audit(qp);rf=rf_audit(p)
    # The old generic auditor compares an angle with a fixed degree epsilon.
    # Very short unchanged segments can exceed that angular epsilon after
    # rounding to Altium's 2.54 nm coordinate grid. Accept only an unchanged
    # baseline record whose two vectors have <=sqrt(2) grid transverse error
    # from their exact H/V/45 directions and whose ideal physical turn is <=45.
    # All new bends must pass the existing audit without this exception.
    resolved=[];unresolved=[]
    for failure in quant['failures']:
        net=failure.get('net');layer=failure.get('layer')
        same=[t for t in source['tracks'] if t['net']==net and t['layer']==layer]==[t for t in p['tracks'] if t['net']==net and t['layer']==layer]
        if failure['kind']!='routing_turn' or not same:
            unresolved.append(failure);continue
        at=failure['at'];vectors=[]
        for t in qp['tracks']:
            if t['net']!=net or t['layer']!=layer:continue
            for endpoint,other in ((t['a'],t['b']),(t['b'],t['a'])):
                if math.dist(endpoint,at)<1e-7:
                    dx,dy=other[0]-endpoint[0],other[1]-endpoint[1]
                    angle=round(math.atan2(dy,dx)/(math.pi/4))*(math.pi/4)
                    transverse=abs(dx*math.sin(angle)-dy*math.cos(angle))
                    vectors.append(dict(ideal_angle_rad=angle,transverse_grid_error_mm=transverse))
        if len(vectors)!=2:
            unresolved.append(failure);continue
        between=abs((vectors[0]['ideal_angle_rad']-vectors[1]['ideal_angle_rad']+math.pi)%(2*math.pi)-math.pi)
        idealturn=180-math.degrees(between)
        valid=idealturn<=45.000001 and all(v['transverse_grid_error_mm']<=math.sqrt(2)*UNIT+1e-10 for v in vectors)
        if valid:resolved.append(dict(**failure,ideal_turn_deg=idealturn,unchanged_source_track_records=True,vectors=vectors,maximum_allowed_transverse_grid_error_mm=math.sqrt(2)*UNIT))
        else:unresolved.append(failure)
    quant['raw_failure_count']=len(quant['failures'])
    quant['inherited_native_grid_turn_diagnostics']=resolved
    quant['failures']=unresolved;quant['passed']=not unresolved
    check(quant['passed'],'native_grid_signal_audit',quant['failures'])
    check(rf['passed'],'RF_topology_audit',rf['failures'])
    check(not rf['quality_review_required'],'RF_quality_flags',rf['quality_flags'])
    bend_counts=[]
    for row in p['dc_routed_jobs']:
        pts=row['points'];bend_counts.append(dict(net=row['job']['net'],bends=max(0,len(pts)-2)))
    report=dict(passed=not failures,failures=failures,candidate_sha256=sha(CANDIDATE),source_candidate_sha256=sha(BASE),
                local_edit_box_mm=[5.5,36,14,49],actual_changed_centreline_bounds_mm=list(unary_union(geoms).bounds),
                changed_DC_net_count=len(net_changes),changed_DC_nets=net_changes,RF_pad_contacts=RF,QD_via_containment=vias,
                native_grid_signal_audit=quant,RF_topology_audit=rf,DC_bend_counts=bend_counts,
                total_DC_bends=sum(x['bends'] for x in bend_counts),maximum_DC_bends=max(x['bends'] for x in bend_counts),
                scope='Complete merged signal/endpoint proof including rounded native-grid geometry. Explicit GND regions, masks and shield regeneration are a separate subsequent audit.')
    (H/'alignment_local_delta_audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('passed','candidate_sha256','changed_DC_net_count','actual_changed_centreline_bounds_mm','total_DC_bends','maximum_DC_bends','failures')},indent=2))
    print('RF_CHANGED_PADS',json.dumps([x for x in RF if x['pad_movement_mm']>1e-8]))
    raise SystemExit(0 if report['passed'] else 2)


if __name__=='__main__':main()
