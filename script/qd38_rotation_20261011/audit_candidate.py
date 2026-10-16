"""Independent continuity, spacing and routing-shape checks of a revision plan."""
from pathlib import Path
from collections import defaultdict
import argparse
import hashlib
import json
import math
import sys

from shapely.geometry import Point, LineString, Polygon, box, shape
from shapely.ops import unary_union

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'qd38_carrier_20261010'))
from route_circuit import pgeom
from route_rf_rotated import arc_line

def audit(plan):
    failures=[]
    bylayer=defaultdict(lambda:defaultdict(list))
    nodes=defaultdict(list)
    contacts=defaultdict(list)
    for p in plan['physical_pads']:
        if p['net'] is None:
            continue
        geom=pgeom(p)
        for layer in ([1,2,3,4,5,32] if p['layer']==74 else [p['layer']]):
            bylayer[layer][p['net']].append(geom)
            contacts[(p['net'],layer)].append(geom)
    for v in plan['vias']:
        geom=Point(v['x'],v['y']).buffer(v['diameter']/2,quad_segs=64)
        for layer in (1,2,3,4,5,32):
            if v['low']<=layer<=v['high']:
                bylayer[layer][v['net']].append(geom)
                contacts[(v['net'],layer)].append(geom)
    for t in plan['tracks']:
        net,layer=t['net'],t['layer']
        a,b=t['a'],t['b'];dx=b[0]-a[0];dy=b[1]-a[1]
        length=math.hypot(dx,dy)
        if length<1e-8:
            continue
        bylayer[layer][net].append(LineString([a,b]).buffer(t['width']/2,quad_segs=32))
        for p,other in ((a,b),(b,a)):
            nodes[(net,layer,round(p[0],7),round(p[1],7))].append(((other[0]-p[0])/length,(other[1]-p[1])/length))
        off=min(abs(dx),abs(dy),abs(abs(dx)-abs(dy))/math.sqrt(2))
        # DC trunks use H/V/45 directions. RF segments may approach angled
        # bond pads directly; RF corners are checked for tangent continuity.
        if net.startswith('DC') and off>1e-5:
            if not any(g.buffer(1e-7).covers(LineString([a,b])) for g in contacts[(net,layer)]):
                failures.append(dict(kind='non_H_V_45_track',net=net,layer=layer,a=a,b=b))
    for a in plan.get('arcs',[]):
        net,layer=a['net'],a['layer']
        bylayer[layer][net].append(arc_line(a).buffer(a['width']/2+.00001,quad_segs=32))
        for angle,sign in ((a['start_angle'],1),(a['end_angle'],-1)):
            radians=math.radians(angle)
            p=(a['cx']+a['radius']*math.cos(radians),a['cy']+a['radius']*math.sin(radians))
            tangent=(-sign*math.sin(radians),sign*math.cos(radians))
            nodes[(net,layer,round(p[0],7),round(p[1],7))].append(tangent)
    sharp=[]
    for (net,layer,x,y),vectors in nodes.items():
        if len(vectors)!=2 or any(g.buffer(1e-6).covers(Point(x,y)) for g in contacts[(net,layer)]):
            continue
        dot=sum(a*b for a,b in zip(*vectors))
        turn=180-math.degrees(math.acos(max(-1,min(1,dot))))
        limit=45.001 if net.startswith('DC') else .01
        if turn>limit:
            sharp.append(dict(kind='routing_turn',net=net,layer=layer,at=[x,y],turn_deg=turn))
    failures.extend(sharp)
    copper={layer:{net:unary_union(gs) for net,gs in nets.items()} for layer,nets in bylayer.items()}
    min_gap=math.inf;min_dc_gap=math.inf;clearance=[]
    for layer,nets in copper.items():
        items=list(nets.items())
        for i,(net,g) in enumerate(items):
            for other,h in items[:i]:
                gap=g.distance(h)
                min_gap=min(min_gap,gap)
                dc_pair=layer in (2,4) and net.startswith('DC') and other.startswith('DC')
                dc_ground=layer in (2,4) and ((net.startswith('DC') and other=='GND') or (other.startswith('DC') and net=='GND'))
                required=.10 if dc_pair else (.20 if dc_ground else .15)
                if dc_pair:
                    min_dc_gap=min(min_dc_gap,gap)
                if gap<required-1e-6:
                    clearance.append(dict(kind='foreign_copper_clearance',layer=layer,nets=[net,other],gap_mm=gap,required_mm=required))
    failures.extend(clearance)
    disconnected=[]
    for net,expected in plan['nets'].items():
        if net=='GND':
            continue
        pieces=[]
        for layer,nets in copper.items():
            g=nets.get(net)
            if g is None:
                continue
            g=g.buffer(.00001)
            pp=list(g.geoms) if hasattr(g,'geoms') else [g]
            pieces.extend((layer,part) for part in pp)
        parent=list(range(len(pieces)))
        def find(i):
            while parent[i]!=i:
                parent[i]=parent[parent[i]];i=parent[i]
            return i
        def join(indices):
            if indices:
                a=find(indices[0])
                for i in indices[1:]:
                    parent[find(i)]=a
        for v in plan['vias']:
            if v['net']==net:
                point=Point(v['x'],v['y'])
                join([i for i,(layer,g) in enumerate(pieces) if v['low']<=layer<=v['high'] and g.covers(point)])
        for p in plan['physical_pads']:
            if p['net']==net and p['layer']==74:
                point=Point(p['x'],p['y'])
                join([i for i,(layer,g) in enumerate(pieces) if g.covers(point)])
        terminal_roots={}
        for p in plan['physical_pads']:
            if p['net']==net and p['ref']:
                key=p['ref']+'-'+p['pin'];point=Point(p['x'],p['y'])
                terminal_roots[key]=sorted({find(i) for i,(layer,g) in enumerate(pieces) if (p['layer'] in (layer,74)) and g.covers(point)})
        roots={r for vals in terminal_roots.values() for r in vals}
        if set(terminal_roots)!=set(expected) or len(roots)!=1 or any(not v for v in terminal_roots.values()):
            disconnected.append(dict(kind='disconnected_net',net=net,terminals=terminal_roots))
    failures.extend(disconnected)
    smp_pads=defaultdict(list)
    for p in plan['physical_pads']:
        if str(p['ref']).startswith('SMP') and p['layer']==74:
            smp_pads[p['ref']].append(pgeom(p))
    smp_envelopes={ref:unary_union(gs).convex_hull for ref,gs in smp_pads.items()}
    for layer in (2,4):
        for net,g in copper.get(layer,{}).items():
            if net.startswith('DC'):
                for ref,envelope in smp_envelopes.items():
                    gap=g.distance(envelope)
                    if gap<.15-1e-6:
                        failures.append(dict(kind='DC_in_SMP_envelope',net=net,layer=layer,smp=ref,gap_mm=gap,required_mm=.15))
    resistor_refs={p['ref'] for p in plan['physical_pads'] if str(p['ref']).startswith('R')}
    for ref in resistor_refs:
        pp=[p for p in plan['physical_pads'] if p['ref']==ref]
        hull=unary_union([pgeom(p) for p in pp]).convex_hull
        for layer in (2,4):
            for net,g in copper.get(layer,{}).items():
                if not net.startswith('DC'):
                    continue
                own=unary_union([pgeom(p) for p in pp if p['pin']=='2' and p['net']==net])
                forbidden=hull.difference(own)
                gap=g.distance(forbidden)
                if gap<.15-1e-6:
                    failures.append(dict(kind='DC_in_resistor_envelope',net=net,layer=layer,resistor=ref,gap_mm=gap,required_mm=.15))
    direct_vias=[]
    for row in plan['pinmap']:
        net=row['dc_net'];vv=[v for v in plan['vias'] if v['net']==net]
        device=[v for v in vv if not v['label'].startswith('J1-')]
        target=[p for p in plan['physical_pads'] if p['net']==net and p['ref']!='J1']
        layers=sorted({t['layer'] for t in plan['tracks'] if t['net']==net and t['layer'] in (2,3,4,5)})
        good=len(vv)==2 and len(device)==1 and len(layers)==1
        if device:
            v=device[0]
            contained=any(pgeom(p).buffer(1e-6).covers(Point(v['x'],v['y'])) for p in target)
            good=good and contained
        else:
            contained=False
        record=dict(net=net,count=len(vv),device_via_in_pad=contained,internal_layers=layers,passed=good)
        direct_vias.append(record)
        if not good:
            failures.append(dict(kind='DC_endpoint_or_layer',**record))
    cx,cy=plan['sample_center'];cw,ch=plan['cavity_mm']
    cavity=box(cx-cw/2,cy-ch/2,cx+cw/2,cy+ch/2)
    for layer,nets in copper.items():
        if layer==1:
            continue
        for net,g in nets.items():
            if net!='GND' and g.intersection(cavity).area>1e-8:
                failures.append(dict(kind='signal_in_blind_pocket',layer=layer,net=net))
    return dict(passed=not failures,failures=failures,minimum_foreign_copper_gap_mm=min_gap,
                minimum_internal_DC_pair_gap_mm=min_dc_gap,internal_DC_pair_rule_mm=.10,other_pair_rule_mm=.15,
                disconnected_nets=disconnected,invalid_turns=sharp,dc_via_and_layer=direct_vias,
                signal_arcs=len(plan.get('arcs',[])),tracks=len(plan['tracks']))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('candidate',type=Path);parser.add_argument('--output',type=Path,default=HERE/'routing_audit.json');args=parser.parse_args()
    p=json.loads(args.candidate.read_text());r=audit(p);r['candidate_sha256']=hashlib.sha256(args.candidate.read_bytes()).hexdigest()
    args.output.write_text(json.dumps(r,indent=2));print(json.dumps({k:v for k,v in r.items() if k not in ('failures','dc_via_and_layer','disconnected_nets','invalid_turns')},indent=2));print('FAILURES',len(r['failures']),json.dumps(r['failures'][:8]))
    sys.exit(0 if r['passed'] else 2)
