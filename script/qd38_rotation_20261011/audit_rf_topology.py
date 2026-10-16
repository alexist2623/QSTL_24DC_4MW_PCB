"""Read-only RF terminal topology, tangent continuity and routing quality audit.

Public API: audit(plan) -> report. CLI accepts a candidate JSON and --output.
Small features are reported relative to the specified trace width; no invented
manufacturing minimum radius is asserted. Repeated sub-width alternating bends
are rejected as unresolved grid staircases, even if every join is tangent.
"""
from pathlib import Path
from collections import defaultdict
import argparse
import hashlib
import json
import math

import networkx as nx
from shapely import set_precision
from shapely.affinity import rotate, translate
from shapely.geometry import Point, LineString, Polygon, box
from shapely.ops import unary_union

HERE=Path(__file__).resolve().parent
GRID=1e-7
TOL=1e-5


def pgeom(p):
    if p['shape']=='round':
        return Point(p['x'],p['y']).buffer(p['sx']/2,quad_segs=64)
    return translate(rotate(box(-p['sx']/2,-p['sy']/2,p['sx']/2,p['sy']/2),p['rotation'],origin=(0,0)),p['x'],p['y'])


def arc_points(a):
    sweep=(a['end_angle']-a['start_angle'])%360
    count=max(2,int(math.ceil(sweep/.25)))
    return [(a['cx']+a['radius']*math.cos(math.radians(a['start_angle']+sweep*i/count)),
             a['cy']+a['radius']*math.sin(math.radians(a['start_angle']+sweep*i/count))) for i in range(count+1)]


def key(pt):
    return tuple(round(float(x)/GRID) for x in pt)


def parts(g):
    if g.is_empty:
        return []
    if hasattr(g,'geoms'):
        return [a for item in g.geoms for a in parts(item)]
    return [g] if g.geom_type=='LineString' else []


def audit(plan):
    failures=[];flags=[]
    rf_pads=[p for p in plan['physical_pads'] if p['ref']=='Q1' and p['net'] and p['net'].startswith('MW')]
    rf_nets={p['net'] for p in plan['physical_pads'] if p['net'] and p['net'].startswith(('MW','S'))}
    primitives=defaultdict(list)
    for kind,objects in [('track',plan.get('tracks',[])),('arc',plan.get('arcs',[]))]:
        for i,t in enumerate(objects):
            if t['net'] not in rf_nets:
                continue
            if t['layer']!=32:
                failures.append(dict(kind='RF_signal_off_Bottom',net=t['net'],primitive=kind,index=i,layer=t['layer']))
            if kind=='track':
                a,b=map(tuple,(t['a'],t['b']));length=math.dist(a,b)
                if length<1e-10:
                    failures.append(dict(kind='zero_length_RF_track',index=i,net=t['net']));continue
                tangent=((b[0]-a[0])/length,(b[1]-a[1])/length)
                vectors=(tangent,(-tangent[0],-tangent[1]));line=LineString([a,b])
            else:
                points=arc_points(t);a,b=points[0],points[-1]
                if t['radius']<=0:
                    failures.append(dict(kind='invalid_RF_arc_radius',index=i,net=t['net']));continue
                aa,ab=math.radians(t['start_angle']),math.radians(t['end_angle'])
                vectors=((-math.sin(aa),math.cos(aa)),(math.sin(ab),-math.cos(ab)))
                line=LineString(points);length=t['radius']*math.radians((t['end_angle']-t['start_angle'])%360)
            primitives[t['net']].append(dict(kind=kind,index=i,raw=t,a=a,b=b,vectors=vectors,line=line,
                                             copper=line.buffer(t['width']/2+(.000001 if kind=='arc' else 0),quad_segs=48),length=length))
    for v in plan.get('vias',[])+plan.get('shield_vias',[]):
        if v.get('net') in rf_nets:
            failures.append(dict(kind='RF_signal_via',net=v['net'],label=v.get('label'),x=v['x'],y=v['y']))
    if len(rf_pads)!=16:
        failures.append(dict(kind='RF_QD_terminal_count',actual=len(rf_pads),expected=16))

    hull_violations=[]
    bottom_signal=[]
    for t in plan.get('tracks',[]):
        if t['layer']==32 and t.get('net')!='GND':
            bottom_signal.append((t['net'],'track',LineString([t['a'],t['b']]).buffer(t['width']/2,quad_segs=32)))
    for a in plan.get('arcs',[]):
        if a['layer']==32 and a.get('net')!='GND':
            bottom_signal.append((a['net'],'arc',LineString(arc_points(a)).buffer(a['width']/2+.000001,quad_segs=32)))
    for ref in sorted({p['ref'] for p in plan['physical_pads'] if p['ref'] and p['ref'].startswith('R')}):
        pp=[p for p in plan['physical_pads'] if p['ref']==ref]
        hull=unary_union([pgeom(p) for p in pp]).convex_hull
        own={p['net'] for p in pp}
        for net,kind,g in bottom_signal:
            if net not in own and hull.intersection(g).area>1e-10:
                hull_violations.append(dict(resistor=ref,foreign_net=net,primitive=kind,intersection_area_mm2=hull.intersection(g).area))
    failures += [dict(kind='foreign_signal_under_resistor_hull',**v) for v in hull_violations]
    net_reports=[];staircases=[];all_radii=[];all_lengths=[];outer_radii=[];outer_lengths=[];tangent_errors=[]
    for net in sorted(rf_nets):
        ps=[p for p in plan['physical_pads'] if p['net']==net and p['ref']]
        contacts={p['ref']+'-'+p['pin']:pgeom(p) for p in ps}
        rows=primitives.get(net,[])
        if not rows:
            failures.append(dict(kind='unrouted_RF_net',net=net));continue
        if net.startswith('MW'):
            r=[p for p in ps if p['ref'].startswith('R') and p['pin']=='1']
            c=[p for p in ps if p['ref'].startswith('C') and p['pin']=='2']
            qd=[p for p in ps if p['ref']=='Q1']
            expected_ok=len(ps)==3 and len(r)==len(c)==len(qd)==1
            if expected_ok:
                start=c[0]['ref']+'-2';stop='Q1-'+qd[0]['pin'];inline=r[0]['ref']+'-1'
                r2=next(p for p in plan['physical_pads'] if p['ref']==r[0]['ref'] and p['pin']=='2')
                if r2['net']!=f"DC{int(qd[0]['pin']):02}":
                    failures.append(dict(kind='RF_bias_DC_QD_identity',net=net,resistor=r[0]['ref'],actual=r2['net'],QD=qd[0]['pin']))
                if r[0]['ref'][1:]!=c[0]['ref'][1:]:
                    failures.append(dict(kind='RF_capacitor_resistor_group_mismatch',net=net,R=r[0]['ref'],C=c[0]['ref']))
        else:
            s=[p for p in ps if p['ref'].startswith('SMP') and p['pin']=='1']
            c=[p for p in ps if p['ref'].startswith('C') and p['pin']=='1']
            expected_ok=len(ps)==2 and len(s)==len(c)==1
            if expected_ok:
                start=s[0]['ref']+'-1';stop=c[0]['ref']+'-1';inline=None
                if s[0]['ref'][3:]!=c[0]['ref'][1:]:
                    failures.append(dict(kind='SMP_capacitor_group_mismatch',net=net,SMP=s[0]['ref'],C=c[0]['ref']))
        if not expected_ok:
            failures.append(dict(kind='RF_terminal_membership',net=net,terminals=sorted(contacts)))
            continue
        contact_union=unary_union(list(contacts.values()))
        line_union=unary_union([set_precision(x['line'],GRID) for x in rows])
        outer=line_union.difference(contact_union)
        graph=nx.MultiGraph()
        def node(pt):
            match=[label for label,g in contacts.items() if g.buffer(TOL).covers(Point(pt))]
            return match[0] if len(match)==1 else key(pt)
        for line in parts(outer):
            a,b=line.coords[0],line.coords[-1]
            if line.length>TOL:
                graph.add_edge(node(a),node(b),length=line.length)
        degrees={str(n):int(d) for n,d in graph.degree}
        correct_degrees=all(degrees.get(label,0)==(2 if label==inline else 1) for label in contacts)
        outside_bad=[dict(node=n,degree=d) for n,d in graph.degree if not isinstance(n,str) and d!=2]
        connected=start in graph and stop in graph and nx.is_connected(graph)
        tree=connected and graph.number_of_edges()==graph.number_of_nodes()-1
        if not correct_degrees or outside_bad or not tree:
            failures.append(dict(kind='RF_inline_chain_topology',net=net,start=start,stop=stop,inline=inline,
                                 connected=connected,acyclic=tree,terminal_degrees={label:degrees.get(label,0) for label in contacts},outside_nodes=outside_bad[:30]))
        centre_distance=None
        if inline:
            centre=Point(r[0]['x'],r[0]['y']);centre_distance=line_union.distance(centre)
            if centre_distance>TOL:
                failures.append(dict(kind='RF_path_misses_resistor_pad_centre',net=net,resistor=r[0]['ref'],distance_mm=centre_distance))

        # Tangent vectors are analytic; arc tessellation never determines the
        # tangent result. Nodes inside intended terminal pads are excluded.
        incidences=defaultdict(list);pg=nx.MultiGraph()
        for ix,item in enumerate(rows):
            a,b=node(item['a']),node(item['b'])
            if a!=b:
                pg.add_edge(a,b,primitive=ix)
            for endpoint,vector in zip((item['a'],item['b']),item['vectors']):
                incidences[key(endpoint)].append((ix,endpoint,vector))
        errors=[]
        for xy,entries in incidences.items():
            point=Point(entries[0][1])
            if contact_union.buffer(TOL).covers(point):
                continue
            if len(entries)!=2:
                errors.append(dict(at_mm=list(entries[0][1]),degree=len(entries),reason='open_or_multiway_primitive_join'));continue
            u,v=entries[0][2],entries[1][2]
            error=180-math.degrees(math.acos(max(-1,min(1,u[0]*v[0]+u[1]*v[1]))))
            if error>.01:
                errors.append(dict(at_mm=list(entries[0][1]),tangent_error_deg=error))
        if errors:
            tangent_errors.extend(dict(net=net,**e) for e in errors)
            failures.append(dict(kind='RF_nontangent_or_open_join',net=net,examples=errors[:20],count=len(errors)))
        radii=[item['raw']['radius'] for item in rows if item['kind']=='arc'];lengths=[item['length'] for item in rows if item['kind']=='track']
        all_radii+=radii;all_lengths+=lengths
        outside_items=[item for item in rows if not contact_union.buffer(TOL).covers(item['line'])]
        outer_radii += [item['raw']['radius'] for item in outside_items if item['kind']=='arc']
        outer_lengths += [item['length'] for item in outside_items if item['kind']=='track']
        short_tracks=[dict(index=item['index'],length_mm=item['length'],width_mm=item['raw']['width']) for item in outside_items if item['kind']=='track' and item['length']<item['raw']['width']]
        tight_arcs=[dict(index=item['index'],radius_mm=item['raw']['radius'],width_mm=item['raw']['width']) for item in outside_items if item['kind']=='arc' and item['raw']['radius']<item['raw']['width']]
        if short_tracks or tight_arcs:
            flags.append(dict(kind='sub_width_features_review',net=net,short_track_count=len(short_tracks),sub_width_radius_count=len(tight_arcs)))
        # Inspect the actual primitive order, not metadata claims about bends.
        ordered=[]
        if start in pg and stop in pg:
            try:
                path_nodes=nx.shortest_path(pg,start,stop)
                for a,b in zip(path_nodes,path_nodes[1:]):
                    edge=next(iter(pg.get_edge_data(a,b).values()));item=rows[edge['primitive']]
                    ordered.append((item,1 if node(item['a'])==a else -1))
            except nx.NetworkXNoPath:
                pass
        pairs=[]
        for i in range(len(ordered)-2):
            (a,da),(b,db),(c,dc)=ordered[i:i+3]
            if a['kind']=='arc' and b['kind']=='track' and c['kind']=='arc' and da!=dc and b['length']<b['raw']['width'] and max(a['raw']['radius'],c['raw']['radius'])<b['raw']['width']:
                pairs.append(dict(at_order=i,arc_indices=[a['index'],c['index']],bridge_track=b['index'],bridge_length_mm=b['length']))
        repeated=[pair for pair in pairs if any(other['at_order']==pair['at_order']+2 or other['at_order']==pair['at_order']-2 for other in pairs)]
        if repeated:
            staircases.append(dict(net=net,repeated_alternating_sub_width_bends=repeated))
        net_reports.append(dict(net=net,terminals=sorted(contacts),inline_terminal=inline,chain_connected=connected,chain_acyclic=tree,
                                terminal_degrees={label:degrees.get(label,0) for label in contacts},resistor_centreline_distance_mm=centre_distance,
                                track_count=len(lengths),arc_count=len(radii),minimum_radius_mm=min(radii,default=None),minimum_track_length_mm=min(lengths,default=None),
                                short_tracks=short_tracks,sub_width_arcs=tight_arcs,alternating_short_bend_pairs=pairs))
    topology_passed=not failures
    for pattern in staircases:
        failures.append(dict(kind='unresolved_grid_staircase',**pattern))
    return dict(passed=not failures,topology_passed=topology_passed,quality_review_required=bool(flags),
                failures=failures,quality_flags=flags,grid_staircases=staircases,net_reports=net_reports,
                RF_QD_terminals=len(rf_pads),RF_net_count=len(rf_nets),arc_count=len(all_radii),
                minimum_RF_arc_radius_mm=min(all_radii,default=None),minimum_RF_straight_length_mm=min(all_lengths,default=None),
                minimum_RF_arc_radius_outside_pad_mm=min(outer_radii,default=None),minimum_RF_straight_length_outside_pad_mm=min(outer_lengths,default=None),
                resistor_hull_violations=hull_violations,tangent_join_errors=tangent_errors,
                methodology='Analytic endpoint tangents; independently noded RF centerlines with only intended terminal pads contracted. S nets must be SMP1-to-C1 paths. MW nets must be C2-to-QD paths through inline R1, explicitly reaching its center. All RF signal copper is Bottom-only, with no signal vias. Resistor two-pad convex hulls exclude foreign Bottom signals. Sub-width radii/segments are review flags; consecutive alternating sub-width arc-track-arc pairs are unresolved grid-staircase failures, not a claimed fabrication-radius rule.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('candidate',type=Path)
    parser.add_argument('--output',type=Path,default=HERE/'rf_topology_audit.json');args=parser.parse_args()
    report=audit(json.loads(args.candidate.read_text()))
    report.update(candidate=str(args.candidate.resolve()),candidate_sha256=hashlib.sha256(args.candidate.read_bytes()).hexdigest())
    args.output.write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k not in ('failures','quality_flags','grid_staircases','net_reports','resistor_hull_violations','tangent_join_errors','methodology')},indent=2))
    print('FAILURES',len(report['failures']),json.dumps(report['failures'][:5]))
    raise SystemExit(0 if report['passed'] else 2)
