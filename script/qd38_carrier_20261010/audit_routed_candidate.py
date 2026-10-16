"""Independently inspect all candidate copper, connectivity and schematic nets."""
import json
import hashlib
from collections import defaultdict
import networkx as nx
import shapely
from shapely.geometry import Point, LineString, box
from shapely.ops import unary_union
from route_circuit import pgeom
from design_geometry import DEST


def main():
    path=DEST/'negotiated_plan.json'
    p=json.loads(path.read_text())
    sch=json.loads((DEST/'schematic_validation.json').read_text())
    assert p['nets']==sch['nets']
    assert p['routing_complete'] and len(p['routed_jobs'])==108
    objects=[]
    for pad in p['physical_pads']:
        if not pad['net'] or pad['net']=='GND':
            continue
        layers=[1,2,3,4,5,32] if pad['layer']==74 else [pad['layer']]
        objects.append((pad['net'],layers,pgeom(pad),f"{pad['ref']}-{pad['pin']}"))
    for v in p['vias']:
        objects.append((v['net'],[l for l in (1,2,3,4,5,32) if v['low']<=l<=v['high']],
                        Point(v['x'],v['y']).buffer(v['diameter']/2,quad_segs=32),v['label']+'-via'))
    grouped=defaultdict(list)
    for t in p['tracks']:
        grouped[t['net'],t['layer']].append(LineString([t['a'],t['b']]).buffer(t['width']/2,quad_segs=32))
    for (net,layer),shapes in grouped.items():
        geometry=unary_union(shapes)
        parts=list(geometry.geoms) if hasattr(geometry,'geoms') else [geometry]
        objects.extend((net,[layer],g,f'{net}-L{layer}-trace{i}') for i,g in enumerate(parts))
    connectivity={}
    for net,pins in p['nets'].items():
        if net=='GND':
            continue
        oo=[a for a in objects if a[0]==net]
        graph=nx.Graph();graph.add_nodes_from(range(len(oo)))
        for i,a in enumerate(oo):
            for j,b in enumerate(oo[:i]):
                if set(a[1]) & set(b[1]) and a[2].distance(b[2])<=1e-8:
                    graph.add_edge(i,j)
        components=list(nx.connected_components(graph))
        names=[set(oo[i][3] for i in comp) for comp in components]
        missing=[name for name in pins if not any(name in c for c in names)]
        connectivity[net]=dict(connected=len(components)==1 and not missing,
                               copper_components=len(components),missing_pads=missing)
    violations=[];minimum=100.
    for layer in (1,2,4,32):
        oo=[a for a in objects if layer in a[1]]
        oo += [('GND',[layer],pgeom(d),f"{d['ref']}-{d['pin']}") for d in p['physical_pads']
               if d['net']=='GND' and d['layer'] in (layer,74)]
        for i,a in enumerate(oo):
            for b in oo[:i]:
                if a[0]==b[0]:continue
                gap=a[2].distance(b[2]);minimum=min(minimum,gap)
                if gap<.15-1e-7:
                    violations.append(dict(layer=layer,a=a[3],b=b[3],gap_mm=gap))
    result=dict(status='OFFLINE_SIGNAL_COPPER_ONLY',all_signal_nets_connected=all(v['connected'] for v in connectivity.values()),
                signal_nets=len(connectivity),connectivity=connectivity,minimum_clearance_mm=minimum,
                clearance_violations=violations,schematic_map_matches=True,dc_channels=38,rf_bias_tees=16,
                plan_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                pending=['Ground copper','RF shield vias','Mask and paste geometry','Native save/reopen and DRC'])
    result['passed']=result['all_signal_nets_connected'] and not violations
    (DEST/'routed_candidate_audit.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k!='connectivity'},indent=2))
    print('DISCONNECTED',[(k,v) for k,v in connectivity.items() if not v['connected']])
    assert result['passed']


if __name__=='__main__':main()
