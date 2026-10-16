"""Centralize native 16-RF carrier DC banks, preserving fixed RF and terminals."""
from pathlib import Path
import sys,json,csv,copy,shutil,hashlib,inspect
H=Path(__file__).resolve().parent;ROOT=H.parents[1];P=ROOT/'QSTL_QD4_2SET_38PAD'
sys.path.insert(0,str(ROOT/'script/rf_redline_review_20261011'))
import dc_shielded_plan_20261016 as dc
import finalize_dc_shielded_20261016 as f
from shapely.geometry import box,LineString
OUT=P/'DC_Centralized_20261016';OUT.mkdir(exist_ok=True);dc.OUT=OUT;f.OUT=OUT
B=H/'before_dc_centralization';B.mkdir(exist_ok=True)
data,groups,st,snapshot,mapping,shield=dc.load()
plan=json.loads((P/'DC_Shielded_Plan_20261016/dc_routed_plan.json').read_text())
current=json.loads((H/'candidate.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for src in [P/'QSTL_QD4_2SET_38PAD.PcbDoc',P/'QSTL_QD4_2SET_38PAD.SchDoc',P/'schematic_validation.json',P/'pin_mapping.csv',H/'candidate.json']:
    dst=B/src.name
    if not dst.exists():shutil.copy2(src,dst)
plan['mapping']=list(csv.DictReader((B/'pin_mapping.csv').open()))
plan['scope']='Native centralization continuation; apply only after coordinate validation.'
shield=copy.deepcopy(shield)
shield['protected_source_hashes']={name:sha(Path(name)) for name in shield['protected_source_hashes']}
original_obstacles=dc.obstacles
def obstacles(plan,data,groups,st):
    objects,bodies=original_obstacles(plan,data,groups,st)
    # Hard corridor, not merely a preference that shortest-path cleanup can undo.
    # Its inner centreline span is X=7.41..12.09 (19 lanes at 0.26 mm pitch).
    objects.extend([('central corridor left',box(-7,0,7.22,22)),('central corridor right',box(12.28,0,27,22))])
    return objects,bodies
dc.obstacles=obstacles
source=inspect.getsource(dc.solve_bank)
source=source.replace('xs=np.arange(xmin+.33,xmax-.3,STEP);ys=np.arange(ymin+.33,75,STEP)',
                      'xs=9.75+np.arange(-62,63)*STEP;ys=np.arange(ymin+.33,75,STEP)')
source=source.replace('abs(xy[a,0]-9.75)*650','abs(xy[a,0]-9.75)*12000')
exec(compile(source,str(H/'central_dc.py')+'::solve_bank','exec'),dc.__dict__)
if '--layer' in sys.argv:
    layer=int(sys.argv[sys.argv.index('--layer')+1]);rr=[r for r in plan['routes'] if r['layer']==layer]
    sn={r['source'] for r in rr};pn={r['port'] for r in rr}
    sources=[v for v in plan['vias'] if v['label'] in sn];ports=[v for v in plan['vias'] if v['label'] in pn]
    routes=dc.solve_bank(plan,data,groups,st,layer,sources,ports);dc.save(f'raw_L{layer}.json',routes)
else:
    routes=json.loads((OUT/'raw_L2.json').read_text())+json.loads((OUT/'raw_L3.json').read_text())
    routes,chamfers=f.simplify(plan,data,groups,st,routes)
    report=f.audit(plan,data,groups,st,shield,routes)
    # Explicitly measure the occupied central corridor at representative heights.
    spans=[]
    for layer in (2,3):
        for y in (2,10,20):
            xs=[]
            for r in routes:
                if r['layer']!=layer:continue
                v=LineString(r['points']).intersection(LineString([(-7,y),(27,y)]))
                if not v.is_empty:
                    if v.geom_type=='Point':xs.append(v.x)
                    else:xs.extend(g.x for g in v.geoms if g.geom_type=='Point')
            spans.append(dict(layer=layer,y_mm=y,lanes=len(xs),min_x_mm=min(xs),max_x_mm=max(xs),copper_width_mm=max(xs)-min(xs)+dc.W,centre_mm=(max(xs)+min(xs))/2))
    report['central_corridor_cross_sections']=spans
    report['central_corridor_passed']=all(s['lanes']==19 and abs(s['centre_mm']-9.75)<1e-6 and s['copper_width_mm']<4.806 for s in spans)
    report['passed'] &= report['central_corridor_passed']
    dc.save('dc_geometry_audit.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('endpoint_checks','protected_sources_unchanged')},indent=2),flush=True)
    assert report['passed']
    result=dict(plan,routes=routes,chamfers=chamfers);dc.save('dc_routed_plan.json',result)
    rows=[]
    for r in sorted(routes,key=lambda r:r['qd_pad']):
        m=next(m for m in plan['mapping'] if int(m['qd_pad'])==r['qd_pad'])
        rows.append(dict(**m,old_zif_pin=m['zif_pin'],proposed_zif_pin=int(r['port'].split('-')[1]),proposed_dc_layer=r['layer'],dc_source=r['source'],route_length_mm=LineString(r['points']).length))
    with (OUT/'proposed_pin_mapping.csv').open('w',newline='') as file:
        w=csv.DictWriter(file,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    f.render(plan,data,groups,st,shield,routes,report)
