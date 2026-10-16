"""Choose complete-net DC routing layers and contact mappings jointly.

Logical source/port nodes have unit capacity shared between both routing
planes. There is no edge between planes after the source selection, so every
resulting path stays on exactly one layer without an intermediate via.
"""
from pathlib import Path
import hashlib,json,sys,time
import networkx as nx
from shapely.geometry import Point, LineString

H=Path(__file__).resolve().parent
SOURCE=Path(sys.argv[1]) if len(sys.argv)>1 else H/'pooled_placement_candidate.json'
CAPACITY_ONLY='--capacity-only' in sys.argv
STAGGER_J1='--stagger-j1' in sys.argv
FLOW_PATH=H/('dc_joint_stagger_flow.json' if STAGGER_J1 else 'dc_joint_flow.json')
sys.argv=[sys.argv[0],'0.23','0.115','0.115','--pooled','--central','--joint-build']
import route_dc_rotated as route


def main():
    plan=json.loads(SOURCE.read_text())
    if STAGGER_J1:
        moved=[]
        for v in plan['vias']:
            if v['label'].startswith('J1-') and int(v['label'].split('-')[1])%4==0:
                assert abs(v['y']-6.75)<.0001
                before=[v['x'],v['y']]
                v['y']+=.7
                moved.append(dict(label=v['label'],before_mm=before,after_mm=[v['x'],v['y']]))
        assert len(moved)==12
        for t in plan['tracks']:
            if t['layer']==1 and t['net'].startswith('DC'):
                v=next(v for v in plan['vias'] if v['label'].startswith('J1-') and v['net']==t['net'])
                t['b']=[v['x'],v['y']]
        for j in plan['route_jobs']:
            if j['kind']=='DC':
                v=next(v for v in plan['vias'] if v['label'].startswith('J1-') and v['net']==j['net'])
                j['a']=[v['x'],v['y']]
        failures=[];top_min=100.;via_min=100.
        top=[t for t in plan['tracks'] if t['layer']==1 and t['net'].startswith('DC')]
        for i,t in enumerate(top):
            g=LineString([t['a'],t['b']]).buffer(t['width']/2,quad_segs=64)
            foreign=[route.pgeom(p) for p in plan['physical_pads'] if p['layer'] in (1,74) and p['net']!=t['net']]
            foreign += [Point(v['x'],v['y']).buffer(v['diameter']/2,quad_segs=64) for v in plan['vias'] if v['net']!=t['net']]
            foreign += [LineString([u['a'],u['b']]).buffer(u['width']/2,quad_segs=64) for u in top[:i] if u['net']!=t['net']]
            gap=min(g.distance(o) for o in foreign);top_min=min(top_min,gap)
            if gap<.15-1e-6:failures.append(dict(net=t['net'],kind='top_fanout',gap_mm=gap))
        changed={m['label'] for m in moved}
        for v in plan['vias']:
            if v['label'] not in changed:continue
            g=Point(v['x'],v['y']).buffer(v['diameter']/2,quad_segs=64)
            foreign=[(route.pgeom(p),p['net']) for p in plan['physical_pads'] if p['net']!=v['net']]
            foreign += [(Point(w['x'],w['y']).buffer(w['diameter']/2,quad_segs=64),w['net']) for w in plan['vias'] if w['net']!=v['net']]
            for o,net in foreign:
                gap=g.distance(o);via_min=min(via_min,gap)
                required=.2 if net=='GND' else .15
                if gap<required-1e-6:failures.append(dict(via=v['label'],kind='via_foreign',gap_mm=gap,required_mm=required))
        assert not failures,failures
        plan['j1_stagger_revision']=dict(source=str(SOURCE),source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
            moved_endpoint_vias=moved,total_endpoint_vias=len(plan['vias']),physical_pads_unchanged=True,
            top_fanout_minimum_clearance_mm=top_min,changed_via_minimum_foreign_clearance_mm=via_min,
            all_J1_via_centers_below_y8=all(v['y']<8 for v in plan['vias'] if v['label'].startswith('J1-')),
            static_passed=True)
        plan['j1_fanout_alternating_even_via_rows_mm']=[6.75,7.45]
        (H/'dc_joint_stagger_input_candidate.json').write_text(json.dumps(plan,indent=2))
        print('J1_STAGGER_STATIC',top_min,via_min,flush=True)
    plan['dc_smp_full_five_pad_hull_exclusion']=True
    plan['dc_resistor_body_hull_exclusion_all_internal_layers']=True
    plan['dc_capacitor_body_hull_exclusion_all_internal_layers']=False
    plan['dc_endpoint_bank_policy']='Joint two-layer integral flow; one complete layer per net'
    plan['dc_outer_run_cost_factor_per_mm_x_offset']=.1
    plan['dc_source_placement_sha256']=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    built=route.run_layer(plan,2)
    if 'graph' not in built:
        FLOW_PATH.write_text(json.dumps(built,indent=2));return
    base=built['graph'];terminals=built['terminals'];xy=built['xy']
    graph=nx.DiGraph();graph.add_node('S',demand=-38);graph.add_node('T',demand=38)
    base.remove_nodes_from(['source','sink'])
    for layer in (2,4):
        for a,attrs in base.nodes(data=True):
            graph.add_node((layer,a),demand=0)
        for a,b,attrs in base.edges(data=True):
            graph.add_edge((layer,a),(layer,b),**attrs)
        for i,t in enumerate(terminals):
            logical=('P:' if t['port'] else 'S:')+t['via']['label']
            graph.add_node(logical,demand=0)
            if t['port']:
                graph.add_edge((layer,f't{i}'),logical,capacity=1,weight=0)
                graph.add_edge(logical,'T',capacity=1,weight=0)
            else:
                graph.add_edge('S',logical,capacity=1,weight=0)
                graph.add_edge(logical,(layer,f't{i}'),capacity=1,weight=0)
    start=time.monotonic();capacity,partial=nx.maximum_flow(graph,'S','T')
    print('JOINT_CAPACITY',capacity,'/38',round(time.monotonic()-start,2),flush=True)
    if CAPACITY_ONLY:
        (H/'dc_joint_capacity_probe.json').write_text(json.dumps(dict(connected=capacity,required=38,source=str(SOURCE)),indent=2))
        return
    if capacity<38:
        unmatched=[t['via']['label'] for t in terminals if not t['port'] and partial['S']['S:'+t['via']['label']]==0]
        report=dict(passed=False,connected=capacity,required=38,unmatched=unmatched,one_layer_per_net=True)
        FLOW_PATH.write_text(json.dumps(report,indent=2));print(report,flush=True);return
    cost,flow=nx.network_simplex(graph)
    routes={2:[],4:[]}
    for i,t in enumerate(terminals):
        if t['port']:continue
        logical='S:'+t['via']['label'];node=next(k for k,n in flow[logical].items() if n)
        layer=node[0];points=[];seen=set();end=None
        while node!='T':
            assert node not in seen;seen.add(node)
            node=next(k for k,n in flow[node].items() if n)
            if isinstance(node,tuple):
                assert node[0]==layer
                k=node[1]
                if isinstance(k,int) and k%2==0:points.append(xy[k//2].tolist())
                if isinstance(k,str) and k.startswith('t') and terminals[int(k[1:])]['port']:
                    end=terminals[int(k[1:])]
        assert end
        points=route.compact(t['stub']+points[1:]+list(reversed(end['stub']))[1:])
        routes[layer].append(dict(net=t['via']['net'],source=t['via']['label'],port=end['via']['label'],layer=layer,width=.125,points=points))
    results=[dict(layer=l,routes=routes[l]) for l in (2,4)]
    report=dict(passed=True,layers=results,cost=cost,one_layer_per_net=True)
    FLOW_PATH.write_text(json.dumps(report,indent=2))
    print('JOINT_SOLVED', {l:len(routes[l]) for l in routes},round(time.monotonic()-start,2),flush=True)
    route.finalize(plan,results)


if __name__=='__main__':main()
