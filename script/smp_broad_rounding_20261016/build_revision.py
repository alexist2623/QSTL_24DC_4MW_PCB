"""Build revised RF, phase-aligned SMP shields, local ground and Bottom mask."""
from pathlib import Path
import sys,json,inspect,copy,math
import numpy as np
import shapely
from shapely.geometry import Point,LineString,Polygon,box,shape,mapping
from shapely.ops import unary_union,substring
from scipy.spatial import cKDTree
H=Path(__file__).resolve().parent;ROOT=H.parents[1]
sys.path[:0]=[str(ROOT/'script/rf_redline_review_20261011'),str(ROOT/'script/native_16rf_apply_20261016')]
import finalize_shielded_rf_20261016 as f
import build_candidate as bc
data,groups,st=f.load_routes();by={g['row']['smp']:g for g in groups}
old=json.loads((H/'baseline/candidate.json').read_text());p=copy.deepcopy(old)
for z in json.loads((H/'entry_routes.json').read_text())['groups']:
    g=by[z['row']['smp']]
    for k in ('qd_to_c2','smp_to_c1'):g[k]=np.array(z[k])
    g['qline']=LineString(g['qd_to_c2']);g['sline']=LineString(g['smp_to_c1']);g['lines']=unary_union([g['qline'],g['sline']]);g['tail']=unary_union([g['qline'].difference(f.m.QD_LAUNCH_ZONE),g['sline']])
exceptions=f.launch_exceptions(groups)
dcobs=unary_union([Point(v['x'],v['y']).buffer(v['diameter']/2+.3255,quad_segs=64) for v in p['vias']])
source=inspect.getsource(f.create_vias)
source=source.replace("if all_rf.distance(p)<.435-1e-8", "if all_rf.distance(p)<.436")
source=source.replace("elif pads.distance(p)<.325:","elif dcobs.covers(p):reason='actual DC terminal via clearance'\n        elif pads.distance(p)<.3255:")
old_sampling='''for t in np.arange(.10,piece.length,.410):
                        xy=piece.interpolate(t).coords[0]
                        accepted+=add(xy,name,f'{mode} side {side}',float(t))'''
new_sampling='''if mode=='C-SMP':
                        # Start at the +/-30 degree ring endpoints and walk
                        # toward the capacitor. Phase is tied to the ring.
                        centre=np.array(g['row']['start'])
                        ring=[np.array([v['x_mm'],v['y_mm']]) for v in records if v['channel']==name and v['kind']=='SMP ring']
                        candidates=[v for v in ring if piece.distance(Point(v))<.08]
                        anchor=max(candidates,key=lambda xy:piece.project(Point(xy)))
                        t=piece.project(Point(anchor));last=anchor
                        while t>.05:
                            t-=.01
                            xy=np.array(piece.interpolate(max(0,t)).coords[0])
                            if np.linalg.norm(xy-last)<.410:continue
                            if add(xy,name,f'{mode} side {side}',float(t)):
                                accepted+=1;last=xy
                    else:
                        for t in np.arange(.10,piece.length,.410):
                            xy=piece.interpolate(t).coords[0]
                            accepted+=add(xy,name,f'{mode} side {side}',float(t))'''
assert old_sampling in source;source=source.replace(old_sampling,new_sampling)
scope=dict(f.__dict__,dcobs=dcobs);exec(source,scope)
vias,rings,rows,rejected=scope['create_vias'](data,groups,st)
print('Generated shield positions',len(vias),flush=True)
(H/'trial_shield_records.json').write_text(json.dumps(dict(vias=vias,rings=rings,rows=rows,rejected=rejected),indent=2))
p['shield_vias']=[dict(net='GND',label=v['kind']+' '+v['channel'],x=v['x_mm'],y=v['y_mm'],diameter=.25,hole=.10,low=5,high=32) for v in vias]
p['tracks']=[t for t in p['tracks'] if t['layer']!=32];p['arcs']=[];fits=[];rf_geoms=[]
for g in groups:
    for key,net in [('qd_to_c2',g['row']['rf_net']),('smp_to_c1','S'+g['row']['smp'][3:])]:
        exact=json.loads((H/'entry_routes.json').read_text()).get('exact_entry_primitives',{})
        if net in exact:
            zz=exact[net]
            geom=unary_union([LineString(bc.sample(z)) for z in zz])
            err=geom.hausdorff_distance(LineString(g[key]))
        else:zz,geom,err=bc.fit(g[key])
        rf_geoms.append((net,geom));fits.append(dict(net=net,error_mm=err))
        for z in zz:
            z=dict(z,net=net,layer=32,width=.11);line=z.pop('line');(p['tracks'] if line else p['arcs']).append(z)
allrf=unary_union([g for n,g in rf_geoms]);pads=p['physical_pads'];gs=[bc.pg(d) for d in pads];board=Polygon(p['board_outline'])
print('Fitted native RF arcs',len(p['arcs']),flush=True)
p['L5_component_cutouts']={ref:mapping(unary_union([g for d,g in zip(pads,gs) if d['ref']==ref]).convex_hull.buffer(.00000254,join_style='mitre')) for ref in sorted({d['ref'] for d in pads if d['ref'] and d['ref'][0] in 'RC'})}
for ll in (5,32):
    obs=[g.buffer(.2005,quad_segs=64) for d,g in zip(pads,gs) if d['layer'] in (ll,74) and d['net']!='GND']
    if ll==32:obs.append(allrf.buffer(.258,quad_segs=48))
    if ll==5:
        obs.extend(shape(g) for g in p['L5_component_cutouts'].values())
    obs += [Point(v['x'],v['y']).buffer(v['diameter']/2+.2005,quad_segs=64) for v in p['vias']]
    obs.append(shape(p['qd_ground_exclusion']))
    raw=board.buffer(-.2,join_style='mitre').difference(unary_union(obs))
    anchors=unary_union([g for d,g in zip(pads,gs) if d['net']=='GND']+[Point(v['x'],v['y']).buffer(.125) for v in p['shield_vias']])
    parts=list(raw.geoms) if hasattr(raw,'geoms') else [raw];keep=[g for g in parts if g.intersects(anchors)]
    p['ground_regions'][str(ll)]=mapping(unary_union(keep));p['ground_islands'][str(ll)]=dict(kept=len(keep),removed=len(parts)-len(keep))
    print('Ground layer',ll,'rebuilt',flush=True)
rc=[];smp=[]
for g in groups:
    rc.append(box(*unary_union([bc.pg(d) for d in pads if d['ref'] in (g['row']['resistor'],g['row']['capacitor'])]).bounds).buffer(.9,join_style='mitre'))
    smp.append(unary_union([bc.pg(d) for d in pads if d['ref']==g['row']['smp']]).convex_hull.buffer(.3,quad_segs=32))
zv=unary_union([Point(v['x'],v['y']).buffer(v['diameter']/2) for v in p['vias'] if v['label'].startswith('J1-')]);zb=box(*zv.bounds).buffer(.4,join_style='mitre')
mounts=unary_union([g.buffer(.1) for d,g in zip(pads,gs) if d['ref'] is None]);field=shape(p['qd_mask_field'])
bottom=board.buffer(.05,join_style='mitre').difference(unary_union(smp+rc+[zb,allrf.buffer(.71,quad_segs=48)]).difference(field)).union(mounts).union(field)
p['solder_openings']['38']=mapping(bottom)
for key in ('components','physical_pads','vias','nets','pinmap','board_outline','qd_ground_exclusion','qd_mask_field'):assert p[key]==old[key],key
assert [t for t in p['tracks'] if t['layer']!=32]==[t for t in old['tracks'] if t['layer']!=32]
assert p['solder_openings']['37']==old['solder_openings']['37']
for ll in ('1','2','3','4'):assert p['ground_regions'][ll]==old['ground_regions'][ll]
# Explicit geometric validation, independent of point-generation rejection.
xy=np.array([[v['x'],v['y']] for v in p['shield_vias']]);points=shapely.points(xy)
metrics=dict(via_count=len(xy),min_via_land_gap_mm=float(cKDTree(xy).query(xy,k=2)[0][:,1].min())-.25,min_RF_copper_to_shield_hole_mm=float(shapely.distance(points,allrf).min())-.105,
    min_pad_to_shield_land_mm=float(shapely.distance(points,unary_union(gs)).min())-.125,
    min_DC_via_to_shield_land_mm=float(shapely.distance(points,unary_union([Point(v['x'],v['y']).buffer(v['diameter']/2,quad_segs=128) for v in p['vias']])).min())-.125)
assert metrics['min_via_land_gap_mm']>=.15
assert metrics['min_RF_copper_to_shield_hole_mm']>=.33
assert metrics['min_pad_to_shield_land_mm']>=.2
assert metrics['min_DC_via_to_shield_land_mm']>=.2
uncovered=[]
checked_ground={ll:shape(p['ground_regions'][ll]).buffer(.00002) for ll in ('5','32')}
for v in p['shield_vias']:
    for ll in ('5','32'):
        if Point(v['x'],v['y']).buffer(.125,quad_segs=64).difference(checked_ground[ll]).area>1e-8:uncovered.append((v['label'],ll,v['x'],v['y']))
assert not uncovered,uncovered[:5]
# Prove both rows meet their ring without skipped vias in the SMP approach.
continuity=[]
for g in groups:
    name=g['row']['smp'];cen=np.array(g['row']['start'])
    for side in (-1,1):
        ring=np.array([[v['x_mm'],v['y_mm']] for v in vias if v['channel']==name and v['kind']=='SMP ring'])
        row=np.array([[v['x_mm'],v['y_mm']] for v in vias if v['channel']==name and v['kind']==f'C-SMP side {side}'])
        close=row[np.linalg.norm(row-cen,axis=1)<3.6]
        close=close[np.argsort(np.linalg.norm(close-cen,axis=1))]
        step=[min(np.linalg.norm(ring-close[0],axis=1))]+[np.linalg.norm(b-a) for a,b in zip(close[:-1],close[1:])]
        continuity.append(dict(channel=name,side=side,row_vias_within_3p6mm=len(close),maximum_centre_step_mm=max(step)))
        assert len(close)>=6 and max(step)<.56,(name,side,step)
metrics['SMP_entry_continuity']=continuity
metrics['local_pairs']=[]
for names,zone in [(('SMP11','SMP12'),box(4.8,39.8,7.5,42)),(('SMP24','SMP28'),box(13.05,43.1,15.1,45.3))]:
    a,b=[by[n]['qline'] for n in names];gap=min(a.intersection(zone).distance(b),b.intersection(zone).distance(a))-.11
    metrics['local_pairs'].append(dict(channels=names,minimum_copper_gap_mm=gap))
(H/'candidate.json').write_text(json.dumps(p,indent=2))
(H/'shield_records.json').write_text(json.dumps(dict(vias=vias,rings=rings,rows=rows,rejected=rejected,exceptions=exceptions),indent=2))
(H/'preparation_audit.json').write_text(json.dumps(dict(passed=True,metrics=metrics,fits=fits),indent=2))
print(json.dumps(metrics,indent=2))
