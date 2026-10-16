"""Conservative continuous RF geometry audit with lossless primitive lists."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import numpy as np
from shapely.geometry import Point,LineString,box,Polygon
from shapely.ops import unary_union
from route_rf_corridor_bounded import pgeom
from audit_rf_topology import audit as topology_audit

H=Path(__file__).resolve().parent

def main():
    ap=argparse.ArgumentParser();ap.add_argument('candidate',type=Path)
    ap.add_argument('--output',type=Path,default=H/'independent_curved_rf_audit.json');a=ap.parse_args()
    data=a.candidate.read_bytes();p=json.loads(data)
    frozen_bytes=(H/'placement_lower_over_smp_candidate.json').read_bytes();frozen=json.loads(frozen_bytes)
    assert hashlib.sha256(frozen_bytes).hexdigest()=='99a7cc8fef9c21e235f47fbdc24733121a37e6ddc4a939d6d92f4fbdb1d70c0e'
    errors=[]
    assert len(p['physical_pads'])==len(frozen['physical_pads'])==243
    for i,(pad,old) in enumerate(zip(p['physical_pads'],frozen['physical_pads'])):
        if pad['ref']!=old['ref'] or pad['pin']!=old['pin'] or pad['layer']!=old['layer'] or pgeom(pad).symmetric_difference(pgeom(old)).area>1e-12:
            errors.append(dict(kind='physical_pad_moved',index=i))
    via_keys=('label','x','y','diameter','hole','low','high')
    assert len(p['vias'])==len(frozen['vias'])==76
    for i,(v,o) in enumerate(zip(p['vias'],frozen['vias'])):
        if any(v.get(k)!=o.get(k) for k in via_keys):errors.append(dict(kind='signal_via_geometry_changed',index=i))
    for i,(c,o) in enumerate(zip(p['components'],frozen['components'])):
        if any(c.get(k)!=o.get(k) for k in ('ref','x','y','rotation','layer')):errors.append(dict(kind='component_moved',index=i))
    copper={};arc_error_max=0.0
    for t in p['tracks']:
        if not t['net'].startswith(('S','MW')):continue
        if t['layer']!=32 or abs(t['width']-.11)>1e-9:errors.append(dict(kind='RF_track_layer_or_width',net=t['net']))
        copper.setdefault(t['net'],[]).append(LineString([t['a'],t['b']]).buffer(t['width']/2,quad_segs=96))
    for t in p.get('arcs',[]):
        if not t['net'].startswith(('S','MW')):continue
        if t['layer']!=32 or abs(t['width']-.11)>1e-9:errors.append(dict(kind='RF_arc_layer_or_width',net=t['net']))
        sweep=(t['end_angle']-t['start_angle'])%360;n=max(2,math.ceil(sweep/.1))
        angles=np.linspace(t['start_angle'],t['start_angle']+sweep,n+1)
        points=[(t['cx']+t['radius']*math.cos(math.radians(v)),t['cy']+t['radius']*math.sin(math.radians(v))) for v in angles]
        error=t['radius']*(1-math.cos(math.radians(sweep/n)/2))+1e-9;arc_error_max=max(arc_error_max,error)
        copper.setdefault(t['net'],[]).append(LineString(points).buffer(t['width']/2+error,quad_segs=96))
    signals={net:unary_union(parts) for net,parts in copper.items()};assert len(signals)==32
    pads=[(d['net'],f'pad:{i}:{d["ref"]}-{d["pin"]}',pgeom(d)) for i,d in enumerate(p['physical_pads']) if d['layer'] in (32,74)]
    vias=[(v['net'],f'via:{i}:{v["label"]}',Point(v['x'],v['y']).buffer(v['diameter']/2,quad_segs=128)) for i,v in enumerate(p['vias']) if v['low']<=32<=v['high']]
    assert len(pads)==190 and len(vias)==76
    assert not [v for v in p['vias'] if v['net'].startswith(('S','MW'))]
    cx,cy=p['sample_center'];cw,ch=p['cavity_mm'];static=pads+vias+[(None,'cavity',box(cx-cw/2,cy-ch/2,cx+cw/2,cy+ch/2))]
    board=Polygon(p['board_outline']);rows=[];pair=[]
    for net,shape in signals.items():
        blockers=[(label,g) for other,label,g in static if other!=net]
        for s in p['smp']:
            if net!=f'S{int(s["ref"][3:]):02}':blockers.append(('ring:'+s['ref'],Point(s['x'],s['y']).buffer(1.175,quad_segs=192)))
        for ref in sorted({d['ref'] for d in p['physical_pads'] if d['ref'] and d['ref'].startswith('R')}):
            pp=[d for d in p['physical_pads'] if d['ref']==ref];hull=unary_union([pgeom(d) for d in pp]).convex_hull
            own=unary_union([pgeom(d) for d in pp if d['net']==net]);blockers.append(('hull:'+ref,hull.difference(own)))
        gap,label=min((shape.distance(g),label) for label,g in blockers)
        edge=shape.distance(board.boundary);rows.append(dict(net=net,minimum_static_gap=gap,nearest=label,edge_gap=edge))
        if gap<.15-1e-7:errors.append(dict(kind='static_clearance',net=net,gap=gap,obstacle=label))
        if edge<.2-1e-7 or not board.covers(shape):errors.append(dict(kind='board_edge_clearance',net=net,gap=edge))
    items=list(signals.items())
    for i,(net,g) in enumerate(items):
        for other,h in items[:i]:
            gap=g.distance(h);pair.append(dict(a=net,b=other,gap=gap))
            if gap<.15-1e-7:errors.append(dict(kind='pair_clearance',a=net,b=other,gap=gap))
    topo=topology_audit(p)
    if not topo['passed']:errors+=topo['failures']
    report=dict(passed=not errors,candidate=str(a.candidate.resolve()),candidate_sha256=hashlib.sha256(data).hexdigest(),frozen_placement_sha256=hashlib.sha256(frozen_bytes).hexdigest(),source_geometry_preserved=not any(e['kind'].endswith(('moved','changed')) for e in errors),Bottom_pad_polygons=len(pads),signal_via_circles=len(vias),RF_nets=len(signals),RF_signal_vias=0,minimum_static_gap=min(rows,key=lambda r:r['minimum_static_gap']),minimum_pair_gap=min(pair,key=lambda r:r['gap']),maximum_arc_sagitta_bound=arc_error_max,topology_passed=topo['passed'],quality_flags=topo['quality_flags'],errors=errors)
    a.output.write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));raise SystemExit(0 if report['passed'] else 2)

if __name__=='__main__':main()
