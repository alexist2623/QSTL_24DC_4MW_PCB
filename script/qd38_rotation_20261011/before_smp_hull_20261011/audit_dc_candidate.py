"""Independently audit quantized DC geometry without rerunning the route solver."""
from pathlib import Path
from collections import defaultdict
import csv
import hashlib
import json
import math

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPolygon, Circle
from shapely.affinity import rotate, translate
from shapely.geometry import Point, LineString, box, Polygon
from shapely.ops import unary_union

H=Path(__file__).resolve().parent
UNIT=2.54e-6
q=lambda v: round(float(v)/UNIT)*UNIT


def pad_geometry(p):
    if p['shape']=='round':
        return Point(q(p['x']),q(p['y'])).buffer(q(p['sx'])/2,quad_segs=64)
    return translate(rotate(box(-q(p['sx'])/2,-q(p['sy'])/2,q(p['sx'])/2,q(p['sy'])/2),p['rotation'],origin=(0,0)),q(p['x']),q(p['y']))


def main():
    path=H/'dc_routed_candidate.json';p=json.loads(path.read_text())
    dc={f'DC{i:02}' for i in range(1,39)}
    failures=[];by_net=defaultdict(list);direction_failures=[];turn_failures=[]
    for t in p['tracks']:
        if t['net'] in dc and t['layer'] in (2,4):
            a=tuple(q(v) for v in t['a']);b=tuple(q(v) for v in t['b'])
            by_net[t['net']].append(dict(t,a=a,b=b))
            dx,dy=abs(b[0]-a[0]),abs(b[1]-a[1])
            if min(dx,dy,abs(dx-dy))>UNIT*1.1:
                direction_failures.append(dict(net=t['net'],a=a,b=b))
    geometries={n:unary_union([LineString([t['a'],t['b']]).buffer(q(t['width'])/2,quad_segs=48) for t in ts]) for n,ts in by_net.items()}
    vias=[dict(v,x=q(v['x']),y=q(v['y']),diameter=q(v['diameter'])) for v in p['vias']]
    via_geometry={v['label']:Point(v['x'],v['y']).buffer(v['diameter']/2,quad_segs=64) for v in vias}
    minimum=100.;connectivity=[]
    layers={n:sorted({t['layer'] for t in ts}) for n,ts in by_net.items()}
    for net in sorted(dc):
        assert layers[net] in ([2],[4])
        layer=layers[net][0];g=geometries[net]
        other=[(f"{a['ref']}-{a['pin']}",pad_geometry(a)) for a in p['physical_pads'] if a['net']!=net and a['layer'] in (layer,74)]
        other += [(v['label'],via_geometry[v['label']]) for v in vias if v['net']!=net and v['low']<=layer<=v['high']]
        other += [(n,geometries[n]) for n in dc if n!=net and layers[n]==[layer]]
        other += [('blind_pocket',box(7.6,39.85,11.9,45.15))]
        for label,o in other:
            gap=g.distance(o);minimum=min(minimum,gap)
            if gap<.15-UNIT*2:
                failures.append(dict(net=net,other=label,gap_mm=gap))
        vv=[v for v in vias if v['net']==net]
        components=unary_union([g]+[via_geometry[v['label']] for v in vv])
        connected=len(vv)==2 and components.geom_type=='Polygon'
        source=next(v for v in vv if not v['label'].startswith('J1-'))
        ref,pin=source['label'].split('-')
        source_pad=next(a for a in p['physical_pads'] if a['ref']==ref and a['pin']==pin)
        in_pad=pad_geometry(source_pad).buffer(UNIT*2).covers(Point(source['x'],source['y']))
        connectivity.append(dict(net=net,layer=layer,vias=len(vv),connected=connected,source_via_center_in_pad=in_pad,
                                 full_through=all(v['low']==1 and v['high']==32 for v in vv)))
        nodes=defaultdict(list)
        for t in by_net[net]:
            for a,b in ((t['a'],t['b']),(t['b'],t['a'])):
                key=tuple(round(z/UNIT) for z in a);nodes[key].append((a,b))
        for key,edges in nodes.items():
            if len(edges)!=2:
                continue
            xy=tuple(v*UNIT for v in key)
            if any(via_geometry[v['label']].covers(Point(xy)) for v in vv):
                continue
            u=[edges[0][1][k]-xy[k] for k in (0,1)];v=[edges[1][1][k]-xy[k] for k in (0,1)]
            dot=sum(a*b for a,b in zip(u,v))/(math.hypot(*u)*math.hypot(*v))
            turn=180-math.degrees(math.acos(max(-1,min(1,dot))))
            if turn>45.01:
                turn_failures.append(dict(net=net,at_mm=xy,turn_deg=turn))
    used={int(row['zif_pin']) for row in p['pinmap']}
    static_failures=[];via_minimum=100.;annular_minimum=100.
    for i,v in enumerate(vias):
        annular_minimum=min(annular_minimum,(v['diameter']-q(v['hole']))/2)
        vg=via_geometry[v['label']]
        foreign=[(a['ref'],a['pin'],pad_geometry(a)) for a in p['physical_pads'] if a['net']!=v['net']]
        foreign += [(w['label'],'via',via_geometry[w['label']]) for w in vias[:i] if w['net']!=v['net']]
        for ref,pin,g in foreign:
            gap=vg.distance(g);via_minimum=min(via_minimum,gap)
            if gap<.15-UNIT*2:
                static_failures.append(dict(via=v['label'],other=f'{ref}-{pin}',gap_mm=gap))
    report=dict(candidate_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),quantization_unit_mm=UNIT,
                placement_sha256=p['contact_pool_policy']['source_placement_sha256'],routes=len(by_net),
                layer_net_counts={str(l):sum(layers[n]==[l] for n in dc) for l in (2,4)},
                minimum_quantized_copper_clearance_mm=minimum,clearance_failures=failures,
                minimum_endpoint_via_to_foreign_pad_or_via_mm=via_minimum,
                minimum_endpoint_via_annular_ring_mm=annular_minimum,static_via_failures=static_failures,
                direction_failures=direction_failures,turns_over45=turn_failures,connectivity=connectivity,
                exact_even24_odd14_pool=used==set(range(2,50,2))|set(range(1,28,2)),pin50_unused=50 not in used)
    report['passed']=not failures and not static_failures and not direction_failures and not turn_failures and report['exact_even24_odd14_pool'] and all(c['connected'] and c['source_via_center_in_pad'] and c['full_through'] for c in connectivity)
    (H/'dc_independent_audit.json').write_text(json.dumps(report,indent=2))
    with (H/'dc_pin_mapping.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(p['pinmap'][0]));writer.writeheader();writer.writerows(p['pinmap'])
    fig,axes=plt.subplots(1,2,figsize=(9,13))
    for ax,layer in zip(axes,(2,4)):
        ax.set_aspect('equal');ax.set_facecolor('#102023')
        ax.add_patch(MPolygon(p['board_outline'],facecolor='#154835',edgecolor='#c7e0d5'))
        ax.add_patch(MPolygon([(7.6,39.85),(11.9,39.85),(11.9,45.15),(7.6,45.15)],facecolor='#1a262c',edgecolor='white'))
        for a in p['physical_pads']:
            if a['layer']==74:
                ax.add_patch(Circle((a['x'],a['y']),a['sx']/2,facecolor='#597864',edgecolor='#a6bdaf',lw=.3))
        for net in sorted(dc):
            if layers[net]!=[layer]:
                continue
            color=plt.colormaps['turbo']((int(net[2:])-1)/37)
            for t in by_net[net]:
                ax.plot([t['a'][0],t['b'][0]],[t['a'][1],t['b'][1]],color=color,lw=.9)
            for v in [v for v in vias if v['net']==net]:
                ax.add_patch(Circle((v['x'],v['y']),v['diameter']/2,facecolor=color,edgecolor='white',lw=.2))
        ax.set(xlim=(-.4,19.9),ylim=(0,67.9),title=f'L{layer}: 19 DC channels',xlabel='X / mm',ylabel='Y / mm')
    fig.suptitle('Rotated QD / seven SMP rows — offline DC geometry verified\n0.125 mm traces; H/V/45 only; all 24 even + first 14 odd ZIF contacts')
    fig.tight_layout();fig.savefig(H/'DC_rotated_verified_preview.png',dpi=180);plt.close(fig)
    print(json.dumps({k:v for k,v in report.items() if k!='connectivity'},indent=2))


if __name__=='__main__':
    main()
