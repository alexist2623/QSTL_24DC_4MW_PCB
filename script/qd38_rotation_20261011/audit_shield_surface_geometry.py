"""Audit all grounded shield lands against real signal copper on both layers."""
from pathlib import Path
import argparse
import hashlib
import json
import math
from shapely.geometry import Point,LineString,shape
from shapely.ops import unary_union
from route_rf_corridor_bounded import pgeom,arc_line
from audit_smp_rings import inspect_smp_rings

H=Path(__file__).resolve().parent

def inspect_shield_clearance(plan,pads,tracks,vias,ground):
    errors=[];shields=[v for v in vias if v['net']=='GND'];signals=[v for v in vias if v['net']!='GND']
    assert len(shields)>0
    rings=inspect_smp_rings(plan,pads,vias)
    if not rings['passed']:errors.extend(rings['failures'])
    signal_lists={}
    for layer in (5,32):
        pieces=[p['geometry'] for p in pads if p['net'] not in (None,'GND') and p['layer'] in (layer,74)]
        pieces += [Point(v['x'],v['y']).buffer(v['diameter']/2,quad_segs=128) for v in signals if v['low']<=layer<=v['high']]
        pieces += [t['geometry'].buffer(t['width']/2+(0.00011 if t.get('is_arc') else 0),quad_segs=96) for t in tracks if t['net'] not in (None,'GND') and t['layer']==layer]
        signal_lists[layer]=pieces
    obstacles={l:unary_union(gs) for l,gs in signal_lists.items()};minimum={5:math.inf,32:math.inf};worst={};floating=[]
    body=unary_union([unary_union([p['geometry'] for p in pads if p['ref']==ref]).convex_hull for ref in {p['ref'] for p in pads if p['ref'] and p['ref'].startswith(('R','C'))}])
    field=shape(plan['qd_mask_field']);min_body=math.inf
    holes=[(p['x'],p['y'],p['hole']/2) for p in pads if p['hole']>0]+[(v['x'],v['y'],v['hole']/2) for v in signals]
    min_hole=math.inf
    for i,v in enumerate(shields):
        center=Point(v['x'],v['y']);radius=v['diameter']/2;land=center.buffer(radius,quad_segs=128)
        for layer in (5,32):
            gap=center.distance(obstacles[layer])-radius
            if gap<minimum[layer]:minimum[layer]=gap;worst[layer]=dict(index=i,x=v['x'],y=v['y'],gap_mm=gap)
            if gap<.2-1e-6:errors.append(dict(kind='shield_GND_signal_clearance',index=i,layer=layer,gap_mm=gap,required_mm=.2))
            area=land.intersection(ground[layer]).area
            if area<=1e-9:floating.append(dict(index=i,layer=layer,ground_contact_mm2=area))
        if land.intersects(field):errors.append(dict(kind='shield_inside_QD_mask_field',index=i))
        bg=center.distance(body)-radius;min_body=min(min_body,bg)
        if bg< -1e-6:errors.append(dict(kind='shield_crosses_RC_body',index=i,gap_mm=bg))
        hg=min(math.hypot(v['x']-x,v['y']-y)-r-v['hole']/2 for x,y,r in holes);min_hole=min(min_hole,hg)
        if hg<.254-1e-6:errors.append(dict(kind='shield_foreign_drill_clearance',index=i,gap_mm=hg))
    errors += [dict(kind='shield_not_on_ground',**v) for v in floating]
    return dict(passed=not errors,shield_via_count=len(shields),minimum_signal_clearance_mm={str(l):v for l,v in minimum.items()},worst_signal_clearance=worst,signal_primitives_per_layer={str(l):len(v) for l,v in signal_lists.items()},minimum_RC_body_clearance_mm=min_body,minimum_foreign_drill_clearance_mm=min_hole,grounded_on_both_layers=not floating,rings=rings,errors=errors,required_signal_clearance_mm=.2,arc_conservative_allowance_mm=.00011)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('candidate',type=Path);ap.add_argument('--output',type=Path,default=H/'shield_surface_audit.json');args=ap.parse_args()
    data=args.candidate.read_bytes();p=json.loads(data)
    pads=[dict(d,geometry=pgeom(d)) for d in p['physical_pads']]
    tracks=[dict(t,geometry=LineString([t['a'],t['b']])) for t in p['tracks']]
    tracks += [dict(a,geometry=arc_line(a),is_arc=True) for a in p.get('arcs',[])]
    vias=p['vias']+p['shield_vias'];ground={int(k):shape(v) for k,v in p['ground_regions'].items()}
    report=inspect_shield_clearance(p,pads,tracks,vias,ground)
    report.update(candidate_sha256=hashlib.sha256(data).hexdigest(),candidate=str(args.candidate.resolve()))
    args.output.write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='rings'},indent=2));raise SystemExit(0 if report['passed'] else 2)

if __name__=='__main__':main()
