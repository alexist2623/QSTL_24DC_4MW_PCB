"""Independently inspect complete raw flow polylines before tangent smoothing."""
from pathlib import Path
import argparse
import hashlib
import json
import math
from shapely.geometry import Point, LineString, Polygon, box
from shapely.ops import unary_union
import route_rf_corridor_bounded as rr

H=Path(__file__).resolve().parent

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--flow',type=Path,required=True)
    ap.add_argument('--placement',type=Path,default=H/'placement_lower_over_smp_candidate.json')
    ap.add_argument('--output',type=Path,default=H/'rf_flow_raw_audit.json')
    a=ap.parse_args();flow=json.loads(a.flow.read_bytes());p=json.loads(a.placement.read_bytes())
    assert hashlib.sha256(a.placement.read_bytes()).hexdigest()==flow['placement_sha256']
    reference=Path(flow['reference_snapshot']);reference_bytes=reference.read_bytes()
    assert hashlib.sha256(reference_bytes).hexdigest()==flow['reference_sha256']
    fixed=[r for r in json.loads(reference_bytes)['routes'] if r['job']['kind']!='RF_QD']
    physical={(d['ref'],str(d['pin'])):d for d in p['physical_pads'] if d['ref']}
    # A list deliberately preserves every primitive even if identities coincide.
    bottom_pads=[d for d in p['physical_pads'] if d['layer'] in (32,74)]
    objects=[((f"pad:{d['ref']}-{d['pin']}" if d['ref'] else f"pad:free:{i}:{d['pin']}"),rr.pgeom(d)) for i,d in enumerate(bottom_pads)]
    objects += [('via:'+v['label'],Point(v['x'],v['y']).buffer(v['diameter']/2,quad_segs=64)) for v in p['vias']]
    assert len(objects)==len(bottom_pads)+len(p['vias'])
    for s in p['smp']:objects.append(('ring:'+s['ref'],Point(s['x'],s['y']).buffer(1.175,quad_segs=128)))
    cx,cy=p['sample_center'];cw,ch=p['cavity_mm'];objects.append(('cavity',box(cx-cw/2,cy-ch/2,cx+cw/2,cy+ch/2)))
    for s in p['smp']:
        g=int(s['ref'][3:]);objects.append((f'hull:R{g:02}',unary_union([rr.pgeom(physical[(f'R{g:02}',str(pin))]) for pin in (1,2)]).convex_hull))
    for r in fixed:objects.append(('fixed:'+r['job']['net']+':'+r['job']['kind'],rr.copper(r['tracks'],r['arcs'])))
    assert sum(label.startswith('pad:') for label,_ in objects)==len(bottom_pads)
    assert sum(label.startswith('via:') for label,_ in objects)==len(p['vias'])
    boundary=Polygon(p['board_outline']);errors=[];metrics=[];geoms=[]
    assert len(flow['routes'])==16 and len({r['group'] for r in flow['routes']})==16 and len({r['target'] for r in flow['routes']})==16
    for r in flow['routes']:
        g=r['group'];q=r['target'];pad=physical[(f'R{g:02}','1')];own=rr.pgeom(pad)
        if math.dist(r['points'][0],(pad['x'],pad['y']))>1e-6:errors.append(dict(group=g,failure='wrong_R1_endpoint'))
        if not rr.pgeom(physical[('Q1',str(q))]).covers(Point(r['points'][-1])):errors.append(dict(group=g,failure='wrong_QD_endpoint'))
        route=LineString(r['points']);copper=route.buffer(.055,quad_segs=64);geoms.append(copper)
        blocked=[]
        for label,shape in objects:
            if label in (f'pad:R{g:02}-1',f'pad:Q1-{q}'):continue
            if label in (f'hull:R{g:02}',f'fixed:MW{g:02}:RF_BIAS'):shape=shape.difference(own)
            blocked.append((label,shape))
        gap,label=min((copper.distance(shape),label) for label,shape in blocked)
        edge=copper.distance(boundary.boundary)
        metrics.append(dict(group=g,target=q,minimum_static_gap=gap,nearest_obstacle=label,board_edge_gap=edge,polyline_length=route.length,vertices=len(r['points'])))
        if gap<.15-1e-6:errors.append(dict(group=g,failure='static_gap',gap=gap,obstacle=label))
        if edge<.2-1e-6 or not boundary.covers(copper):errors.append(dict(group=g,failure='board_edge'))
    pair_gaps=[]
    for i,ga in enumerate(geoms):
        for j in range(i+1,len(geoms)):
            gap=ga.distance(geoms[j]);record=dict(a=flow['routes'][i]['group'],b=flow['routes'][j]['group'],gap=gap)
            pair_gaps.append(record)
            if gap<.15-1e-6:errors.append(dict(failure='pair_gap',**record))
    report=dict(passed=not errors,scope='Raw-polyline geometry only; tangent quality, native correspondence and native DRC remain separate.',flow_sha256=hashlib.sha256(a.flow.read_bytes()).hexdigest(),placement_sha256=flow['placement_sha256'],reference_sha256=flow['reference_sha256'],routes=len(metrics),minimum_static_gap=min(r['minimum_static_gap'] for r in metrics),minimum_pair_gap=min(r['gap'] for r in pair_gaps),metrics=metrics,errors=errors)
    report['obstacle_counts']=dict(bottom_pad_polygons=len(bottom_pads),via_circles=len(p['vias']),SMP_ring_disks=len(p['smp']),resistor_hulls=len(p['smp']),fixed_route_shapes=len(fixed),total=len(objects))
    a.output.write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='metrics'},indent=2))
    raise SystemExit(0 if report['passed'] else 2)

if __name__=='__main__':main()
