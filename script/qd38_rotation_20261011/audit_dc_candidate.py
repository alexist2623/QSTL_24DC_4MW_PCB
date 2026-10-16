"""Independently audit quantized DC geometry without rerunning the route solver."""
from pathlib import Path
from collections import defaultdict
import csv
import hashlib
import json
import math
import sys

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


def segment_mean_abs_x(t):
    """Exact mean distance from X=9.75 along a straight segment."""
    a,b=t['a'][0]-9.75,t['b'][0]-9.75
    if a*b>=0:
        return abs((a+b)/2)
    return (a*a+b*b)/(2*(abs(a)+abs(b)))


def main():
    path=Path(sys.argv[1]) if len(sys.argv)>1 else H/'dc_routed_candidate.json'
    prefix=sys.argv[2] if len(sys.argv)>2 else 'dc'
    p=json.loads(path.read_text())
    dc={f'DC{i:02}' for i in range(1,39)}
    failures=[];by_net=defaultdict(list);direction_failures=[];turn_failures=[];width_failures=[]
    for t in p['tracks']:
        if t['net'] in dc and t['layer'] in (2,4):
            a=tuple(q(v) for v in t['a']);b=tuple(q(v) for v in t['b'])
            by_net[t['net']].append(dict(t,a=a,b=b))
            if abs(q(t['width'])-.125)>UNIT:
                width_failures.append(dict(net=t['net'],width_mm=q(t['width'])))
            dx,dy=abs(b[0]-a[0]),abs(b[1]-a[1])
            if min(dx,dy,abs(dx-dy))>UNIT*1.1:
                direction_failures.append(dict(net=t['net'],a=a,b=b))
    geometries={n:unary_union([LineString([t['a'],t['b']]).buffer(q(t['width'])/2,quad_segs=48) for t in ts]) for n,ts in by_net.items()}
    vias=[dict(v,x=q(v['x']),y=q(v['y']),diameter=q(v['diameter'])) for v in p['vias']]
    via_geometry={v['label']:Point(v['x'],v['y']).buffer(v['diameter']/2,quad_segs=64) for v in vias}
    smp_refs=sorted({a['ref'] for a in p['physical_pads'] if str(a['ref']).startswith('SMP')})
    smp_hulls={ref:unary_union([pad_geometry(a) for a in p['physical_pads'] if a['ref']==ref]).convex_hull for ref in smp_refs}
    assert len(smp_hulls)==16
    rc_refs=sorted({a['ref'] for a in p['physical_pads'] if a['ref'] and a['ref'][0]=='R' and a['ref'][1:].isdigit()})
    rc_hulls={ref:unary_union([pad_geometry(a) for a in p['physical_pads'] if a['ref']==ref]).convex_hull for ref in rc_refs}
    rc_body_failures=[];rc_body_minimum=100.
    minimum=100.;connectivity=[];smp_failures=[];smp_minimum=100.;bend_counts={}
    dc_minimum=100.;gnd_minimum=100.;other_minimum=100.
    layers={n:sorted({t['layer'] for t in ts}) for n,ts in by_net.items()}
    board_geometry=Polygon(p['board_outline'])
    board_edge_failures=[];board_edge_minimum=100.
    for net in sorted(dc):
        assert layers[net] in ([2],[4])
        layer=layers[net][0];g=geometries[net]
        edge_gap=g.distance(board_geometry.boundary)
        board_edge_minimum=min(board_edge_minimum,edge_gap)
        if not board_geometry.covers(g) or edge_gap<.2-UNIT*2:
            board_edge_failures.append(dict(net=net,edge_gap_mm=edge_gap))
        other=[(f"{a['ref']}-{a['pin']}",pad_geometry(a),.10 if a['net'] in dc else .20 if a['net']=='GND' else .15) for a in p['physical_pads'] if a['net']!=net and a['layer'] in (layer,74)]
        other += [(v['label'],via_geometry[v['label']],.10 if v['net'] in dc else .20 if v['net']=='GND' else .15) for v in vias if v['net']!=net and v['low']<=layer<=v['high']]
        other += [(n,geometries[n],.10) for n in dc if n!=net and layers[n]==[layer]]
        other += [('blind_pocket',box(7.6,39.85,11.9,45.15),.15)]
        for ref,hull in smp_hulls.items():
            gap=g.distance(hull);smp_minimum=min(smp_minimum,gap)
            if gap<.15-UNIT*2:
                smp_failures.append(dict(net=net,ref=ref,gap_mm=gap))
        other += [(ref+'_full_five_pad_hull',hull,.15) for ref,hull in smp_hulls.items()]
        for ref,hull in rc_hulls.items():
            forbidden=hull
            if ref.startswith('R'):
                pad2=next(a for a in p['physical_pads'] if a['ref']==ref and a['pin']=='2')
                if pad2['net']==net:
                    forbidden=hull.difference(pad_geometry(pad2))
            gap=g.distance(forbidden);rc_body_minimum=min(rc_body_minimum,gap)
            if gap<.15-UNIT*2:
                rc_body_failures.append(dict(net=net,ref=ref,gap_mm=gap))
            other.append((ref+'_body_envelope',forbidden,.15))
        for label,o,required in other:
            gap=g.distance(o);minimum=min(minimum,gap)
            if required==.1:
                dc_minimum=min(dc_minimum,gap)
            elif required==.2:
                gnd_minimum=min(gnd_minimum,gap)
            else:
                other_minimum=min(other_minimum,gap)
            if gap<required-UNIT*2:
                failures.append(dict(net=net,other=label,gap_mm=gap,required_mm=required))
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
        bend_count=0
        for key,edges in nodes.items():
            if len(edges)!=2:
                continue
            xy=tuple(v*UNIT for v in key)
            if any(via_geometry[v['label']].covers(Point(xy)) for v in vv):
                continue
            u=[edges[0][1][k]-xy[k] for k in (0,1)];v=[edges[1][1][k]-xy[k] for k in (0,1)]
            dot=sum(a*b for a,b in zip(u,v))/(math.hypot(*u)*math.hypot(*v))
            turn=180-math.degrees(math.acos(max(-1,min(1,dot))))
            bend_count+=turn>1
            if turn>45.01:
                turn_failures.append(dict(net=net,at_mm=xy,turn_deg=turn))
        bend_counts[net]=bend_count
    used={int(row['zif_pin']) for row in p['pinmap']}
    mapping_failures=[]
    for row in p['pinmap']:
        jpad=next(a for a in p['physical_pads'] if a['ref']=='J1' and a['pin']==str(row['zif_pin']))
        jvia=next(v for v in vias if v['label']==f"J1-{row['zif_pin']}")
        if jpad['net']!=row['dc_net'] or jvia['net']!=row['dc_net'] or layers[row['dc_net']]!=[row['dc_layer']]:
            mapping_failures.append(row)
    static_failures=[];via_minimum=100.;annular_minimum=100.;via_ground_minimum=100.
    for i,v in enumerate(vias):
        annular_minimum=min(annular_minimum,(v['diameter']-q(v['hole']))/2)
        vg=via_geometry[v['label']]
        foreign=[(a['ref'],a['pin'],pad_geometry(a),.20 if a['net']=='GND' else .15) for a in p['physical_pads'] if a['net']!=v['net']]
        foreign += [(w['label'],'via',via_geometry[w['label']],.20 if w['net']=='GND' else .15) for w in vias[:i] if w['net']!=v['net']]
        for ref,pin,g,required in foreign:
            gap=vg.distance(g);via_minimum=min(via_minimum,gap)
            if required==.20:
                via_ground_minimum=min(via_ground_minimum,gap)
            if gap<required-UNIT*2:
                static_failures.append(dict(via=v['label'],other=f'{ref}-{pin}',gap_mm=gap,required_mm=required))
    top_tracks=[dict(t,a=[q(v) for v in t['a']],b=[q(v) for v in t['b']]) for t in p['tracks'] if t['net'] in dc and t['layer']==1]
    top_geoms=[LineString([t['a'],t['b']]).buffer(q(t['width'])/2,quad_segs=48) for t in top_tracks]
    top_failures=[];top_minimum=100.
    for i,(t,g) in enumerate(zip(top_tracks,top_geoms)):
        foreign=[(a['ref'],a['pin'],pad_geometry(a)) for a in p['physical_pads'] if a['net']!=t['net'] and a['layer'] in (1,74)]
        foreign += [(v['label'],'via',via_geometry[v['label']]) for v in vias if v['net']!=t['net']]
        foreign += [(s['net'],'track',top_geoms[j]) for j,s in enumerate(top_tracks[:i]) if s['net']!=t['net']]
        for ref,pin,other in foreign:
            gap=g.distance(other);top_minimum=min(top_minimum,gap)
            if gap<.15-UNIT*2:
                top_failures.append(dict(net=t['net'],other=f'{ref}-{pin}',gap_mm=gap))
    centrality={n:sum(LineString([t['a'],t['b']]).length*segment_mean_abs_x(t) for t in ts)/sum(LineString([t['a'],t['b']]).length for t in ts) for n,ts in by_net.items()}
    lengths={n:sum(LineString([t['a'],t['b']]).length for t in ts) for n,ts in by_net.items()}
    report=dict(candidate_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),quantization_unit_mm=UNIT,
                placement_sha256=p['contact_pool_policy']['source_placement_sha256'],routes=len(by_net),
                source_placement_file_sha256=p.get('dc_source_input_file_sha256'),
                layer_net_counts={str(l):sum(layers[n]==[l] for n in dc) for l in (2,4)},
                minimum_quantized_copper_clearance_mm=minimum,clearance_failures=failures,
                actual_minimum_dc_to_dc_mm=dc_minimum,actual_minimum_dc_to_ground_mm=gnd_minimum,
                actual_minimum_dc_to_other_mm=other_minimum,
                minimum_endpoint_via_to_foreign_pad_or_via_mm=via_minimum,
                minimum_endpoint_via_to_ground_mm=via_ground_minimum,
                minimum_endpoint_via_annular_ring_mm=annular_minimum,static_via_failures=static_failures,
                top_fanout_minimum_clearance_mm=top_minimum,top_fanout_failures=top_failures,
                minimum_smp_full_hull_clearance_mm=smp_minimum,smp_full_hull_failures=smp_failures,
                minimum_rc_body_envelope_clearance_mm=rc_body_minimum,rc_body_failures=rc_body_failures,
                bends_per_net=bend_counts,total_bends=sum(bend_counts.values()),
                maximum_bends=max(bend_counts.values()),route_length_mm=lengths,
                route_mean_absolute_x_offset_mm=centrality,
                total_dc_length_mm=sum(lengths.values()),
                centrality_metric='Exact line integral of abs(X-9.75) divided by total internal DC track length',
                length_weighted_mean_absolute_x_offset_mm=sum(centrality[n]*lengths[n] for n in lengths)/sum(lengths.values()),
                mapping_failures=mapping_failures,
                width_failures=width_failures,board_edge_failures=board_edge_failures,
                minimum_board_edge_clearance_mm=board_edge_minimum,
                dc_to_dc_minimum_mm=.10,dc_to_other_copper_minimum_mm=.15,poured_ground_gap_required_mm=.20,
                direction_failures=direction_failures,turns_over45=turn_failures,connectivity=connectivity,
                exact_even24_odd14_pool=used==set(range(2,50,2))|set(range(1,28,2)),pin50_unused=50 not in used)
    report['passed']=not failures and not static_failures and not top_failures and not mapping_failures and not direction_failures and not turn_failures and not width_failures and not board_edge_failures and report['exact_even24_odd14_pool'] and all(c['connected'] and c['source_via_center_in_pad'] and c['full_through'] for c in connectivity)
    (H/f'{prefix}_independent_audit.json').write_text(json.dumps(report,indent=2))
    with (H/f'{prefix}_pin_mapping.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(p['pinmap'][0]));writer.writeheader();writer.writerows(p['pinmap'])
    fig,axes=plt.subplots(1,2,figsize=(9,13))
    for ax,layer in zip(axes,(2,4)):
        ax.set_aspect('equal');ax.set_facecolor('#102023')
        ax.add_patch(MPolygon(p['board_outline'],facecolor='#154835',edgecolor='#c7e0d5'))
        ax.add_patch(MPolygon([(7.6,39.85),(11.9,39.85),(11.9,45.15),(7.6,45.15)],facecolor='#1a262c',edgecolor='white'))
        for a in p['physical_pads']:
            if a['layer']==74:
                ax.add_patch(Circle((a['x'],a['y']),a['sx']/2,facecolor='#597864',edgecolor='#a6bdaf',lw=.3))
        for hull in smp_hulls.values():
            ax.add_patch(MPolygon(list(hull.exterior.coords),facecolor='#4a514a',edgecolor='#8d968d',alpha=.65,lw=.4))
        for hull in rc_hulls.values():
            ax.add_patch(MPolygon(list(hull.exterior.coords),facecolor='#716456',edgecolor='#ad977e',alpha=.8,lw=.4))
        for net in sorted(dc):
            if layers[net]!=[layer]:
                continue
            color=plt.colormaps['turbo']((int(net[2:])-1)/37)
            for t in by_net[net]:
                ax.plot([t['a'][0],t['b'][0]],[t['a'][1],t['b'][1]],color=color,lw=.9)
            for v in [v for v in vias if v['net']==net]:
                ax.add_patch(Circle((v['x'],v['y']),v['diameter']/2,facecolor=color,edgecolor='white',lw=.2))
        count=sum(layers[n]==[layer] for n in dc)
        ax.set(xlim=(-.4,19.9),ylim=(0,67.9),title=f'L{layer}: {count} DC channels',xlabel='X / mm',ylabel='Y / mm')
    fig.suptitle('Rotated QD / complete SMP envelopes excluded from DC\n0.125 mm trace; 0.10 DC / 0.15 SMP envelope / 0.20 GND gap; H/V/45 only')
    image_name='DC_rotated_verified_preview.png' if prefix=='dc' else f'{prefix}_preview.png'
    fig.tight_layout();fig.savefig(H/image_name,dpi=180);plt.close(fig)
    print(json.dumps({k:v for k,v in report.items() if k!='connectivity'},indent=2))


if __name__=='__main__':
    main()
