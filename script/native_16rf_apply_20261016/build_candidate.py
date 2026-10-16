"""Create the complete native geometry from the accepted fixed proposal."""
from pathlib import Path
import sys,json,math,csv,copy,hashlib
import numpy as np
from shapely.geometry import Point,LineString,Polygon,box,mapping
from shapely.ops import unary_union
from shapely.affinity import rotate,translate
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];DEST=ROOT/'QSTL_QD4_2SET_38PAD'
sys.path[:0]=[str(ROOT/'script/rf_redline_review_20261011')]
import finalize_shielded_rf_20261016 as rf
data,groups,st=rf.load_routes()
dc=json.loads((DEST/'DC_Shielded_Plan_20261016/dc_routed_plan.json').read_text())
shield=json.loads((DEST/'Shielded_Symmetric_RF_Plan_20261016/shielded_rf_plan.json').read_text())
snap=json.loads((ROOT/'script/qd38_pad_alignment_20261011/saved_revision_snapshot.json').read_text())
oldsch=json.loads((DEST/'schematic_validation.json').read_text())
assign=list(csv.DictReader((DEST/'DC_Shielded_Plan_20261016/proposed_pin_mapping.csv').open()))
portnets={r['port']:r['net'] for r in dc['routes']}
cross=lambda a,b:float(a[0]*b[1]-a[1]*b[0])
unit=lambda a:np.asarray(a,dtype=float)/np.linalg.norm(a)

def pad(p,**kw):
    d=dict(ref=p['component'],pin=p['number'],net=p['net'],layer=p['layer'],x=p['x'],y=p['y'],sx=p['size_x'],sy=p['size_y'],hole=p['hole'],rotation=p['rotation'],shape='rect' if p['shape']==2 else 'round')
    d.update(kw);return d

def pg(d):
    if d['shape']=='round':return Point(d['x'],d['y']).buffer(d['sx']/2,quad_segs=128)
    return translate(rotate(box(-d['sx']/2,-d['sy']/2,d['sx']/2,d['sy']/2),d['rotation'],origin=(0,0)),d['x'],d['y'])

def circle_tangent(a,b,c):
    ab=b-a;ac=c-a;den=2*cross(ab,ac)
    if abs(den)<1e-15:return unit(c-a)
    off=np.array([ac[1]*np.dot(ab,ab)-ab[1]*np.dot(ac,ac),ab[0]*np.dot(ac,ac)-ac[0]*np.dot(ab,ab)])/den
    centre=a+off;r=b-centre;t=np.array([-r[1],r[0]])
    return unit(t if np.dot(t,c-a)>=0 else -t)

def arc_from_tangent(a,b,t):
    chord=b-a;n=np.array([-t[1],t[0]]);den=2*np.dot(chord,n)
    if abs(den)<1e-12:return dict(a=a.tolist(),b=b.tolist(),line=True)
    r=np.dot(chord,chord)/den;c=a+r*n
    a0=math.degrees(math.atan2(a[1]-c[1],a[0]-c[0]));a1=math.degrees(math.atan2(b[1]-c[1],b[0]-c[0]))
    return dict(cx=float(c[0]),cy=float(c[1]),radius=abs(float(r)),start_angle=(a0 if r>0 else a1)%360,end_angle=(a1 if r>0 else a0)%360,line=False)

def sample(z):
    if z['line']:return np.array([z['a'],z['b']])
    sweep=(z['end_angle']-z['start_angle'])%360
    n=max(5,int(math.ceil(math.radians(sweep)*z['radius']/.008)))
    a=np.deg2rad(np.linspace(z['start_angle'],z['start_angle']+sweep,n+1))
    return np.c_[z['cx']+z['radius']*np.cos(a),z['cy']+z['radius']*np.sin(a)]

def biarc(a,b,t0,t1):
    v=b-a;aa=2*(1-np.dot(t0,t1));bb=2*np.dot(v,t0+t1);cc=-np.dot(v,v)
    if abs(aa)<1e-12:d=-cc/bb if abs(bb)>1e-12 else np.linalg.norm(v)/2
    else:d=(-bb+math.sqrt(max(0,bb*bb-4*aa*cc)))/(2*aa)
    m=(a+b+d*(t0-t1))/2
    return [arc_from_tangent(a,m,t0),arc_from_tangent(b,m,-t1)]

def fit(points):
    pp=np.asarray(points,float);pp=pp[np.r_[True,np.linalg.norm(np.diff(pp,axis=0),axis=1)>1e-9]]
    ds=np.diff(pp,axis=0);lens=np.linalg.norm(ds,axis=1);dirs=ds/lens[:,None]
    # Exact straight portions retain their original endpoints. Curved runs are
    # represented by tangent-continuous biarcs, never sharp sampled polylines.
    angles=np.abs(np.array([cross(a,b) for a,b in zip(dirs[:-1],dirs[1:])]))
    straight=lens>.45
    for i,a in enumerate(angles):
        if a<1e-9:straight[i]=straight[i+1]=True
    result=[];i=0
    while i<len(ds):
        if straight[i]:
            j=i+1
            while j<len(ds) and straight[j] and abs(cross(dirs[i],dirs[j]))<1e-9:j+=1
            result.append(dict(line=True,a=pp[i].tolist(),b=pp[j].tolist()));i=j;continue
        j=i+1
        while j<len(ds) and not straight[j]:j+=1
        q=pp[i:j+1];t=[]
        for k in range(len(q)):
            if k==0:t.append(dirs[i-1] if i else unit(q[1]-q[0]))
            elif k==len(q)-1:t.append(dirs[j] if j<len(ds) else unit(q[-1]-q[-2]))
            else:t.append(circle_tangent(q[k-1],q[k],q[k+1]))
        def rec(lo,hi):
            zz=biarc(q[lo],q[hi],t[lo],t[hi]);g=unary_union([LineString(sample(z)) for z in zz]);ref=LineString(q[lo:hi+1])
            err=g.hausdorff_distance(ref)
            if err<=.00045 or hi-lo<=1:
                if err>.0006:raise ValueError(('arc fit deviation',err,lo,hi))
                result.extend(zz)
            else:
                mid=(lo+hi)//2;rec(lo,mid);rec(mid,hi)
        rec(0,len(q)-1);i=j
    geo=unary_union([LineString(sample(z)) for z in result]);err=geo.hausdorff_distance(LineString(pp))
    assert err<.00061,err
    return result,geo,err

def main():
    p=dict(components=[],physical_pads=[],tracks=[],arcs=[],vias=[],shield_vias=[],nets=copy.deepcopy(oldsch['nets']),sample_center=data['qd_centre_mm'],cavity_mm=[4.3,5.3],cavity_depth_mm=1.2,cavity_radius_mm=.5)
    oldc={c['designator']:c for c in snap['components']}
    def comp(ref,x,y,rot,pattern=None):
        o=oldc[ref];p['components'].append(dict(ref=ref,x=float(x),y=float(y),rotation=float(rot)%360,pattern=pattern or o['pattern'],layer=1 if ref=='J1' else 32))
    for net,pins in p['nets'].items():p['nets'][net]=[v for v in pins if not v.startswith('J1-')]
    for port,net in portnets.items():p['nets'][net].append(port)
    for qp in data['pads']:p['physical_pads'].append(pad(qp['after']))
    comp('Q1',*data['qd_centre_mm'],90)
    # The model origin is 0.4 mm below the component origin. Translate the
    # saved component, its pads and its embedded body by the same delta.
    comp('J1',oldc['J1']['x'],oldc['J1']['y']+data['ZIF']['delta_y_mm'],oldc['J1']['rotation'])
    for x in data['ZIF']['translated_pads']:p['physical_pads'].append(pad(x,net=portnets.get('J1-'+x['number'])))
    tmpl=[d for d in snap['pads'] if d['component']=='SMP35'];origin=next(d for d in tmpl if d['number']=='1')
    for g in groups:
        row=g['row'];ref=row['smp'];x,y=row['start'];co=oldc['SMP35']
        comp(ref,x+co['x']-origin['x'],y+co['y']-origin['y'],co['rotation'])
        for z in tmpl:p['physical_pads'].append(pad(z,ref=ref,x=z['x']+x-origin['x'],y=z['y']+y-origin['y'],net=('S'+ref[3:]) if z['number']=='1' else 'GND'))
        for kind in ('capacitor','resistor'):
            z=g[kind];ref=z['ref'];cap=kind=='capacitor';pat='CAPC3216_CC1206JKNPO9BN104' if cap else 'CC1608-0603'
            comp(ref,*z['centre_mm'],z['angle_deg'],pat)
            for d in z['pads']:
                pin=str(d['pin']);net=('S'+ref[1:] if pin=='1' else row['rf_net']) if cap else (row['rf_net'] if pin=='1' else row['dc_net'])
                p['physical_pads'].append(dict(ref=ref,pin=pin,net=net,layer=32,x=d['centre_mm'][0],y=d['centre_mm'][1],sx=1. if cap else 1.1,sy=1.8 if cap else 1.,hole=0,rotation=z['angle_deg']%360,shape='rect'))
    for m in data['mounts']:
        p['physical_pads'].append(dict(ref=None,pin=m['name'],net='GND',layer=74,x=m['xy_mm'][0],y=m['xy_mm'][1],sx=5.5 if m['name'][0]=='P' else 4.,sy=5.5 if m['name'][0]=='P' else 4.,hole=3.2 if m['name'][0]=='P' else 2.,rotation=0,shape='round'))
    for r in dc['routes']:
        p['tracks'] += [dict(net=r['net'],layer=r['layer'],a=a,b=b,width=.125) for a,b in zip(r['points'][:-1],r['points'][1:])]
    for r in dc['top_fanout']:
        p['tracks'] += [dict(net=portnets[r['port']],layer=1,a=a,b=b,width=r['width']) for a,b in zip(r['points'][:-1],r['points'][1:])]
    fits=[];rf_geoms=[]
    for g in groups:
        for k,net in [('qd_to_c2',g['row']['rf_net']),('smp_to_c1','S'+g['row']['smp'][3:])]:
            zz,geom,err=fit(g[k]);fits.append(dict(net=net,error_mm=err,count=len(zz)));rf_geoms.append((net,geom))
            for z in zz:
                z=dict(z,net=net,layer=32,width=.11);line=z.pop('line');(p['tracks'] if line else p['arcs']).append(z)
    p['vias']=[dict(v,net=portnets.get(v['label'],v['net']),low=1,high=32) for v in dc['vias']]
    p['shield_vias']=[dict(net='GND',label=v['kind']+' '+v['channel'],x=v['x_mm'],y=v['y_mm'],diameter=.25,hole=.1,low=5,high=32) for v in shield['vias']]
    p['pinmap']=assign;p['routing_complete']=True
    x0,y0,x1,y1=data['board_bounds_xy_mm'];p['board_outline']=[[x0,y0],[x1,y0],[x1,y1],[x0,y1]];board=box(x0,y0,x1,y1)
    pads=p['physical_pads'];gs=[pg(z) for z in pads];cx,cy=p['sample_center'];excluded=box(cx-2.35,cy-2.85,cx+2.35,cy+2.85)
    field=box(cx-3.4,cy-3.9,cx+3.4,cy+3.9)
    # Ground clearances include a native contour/rounding guard.
    grounds={};details={};allrf=unary_union([g for n,g in rf_geoms])
    for ll in (1,2,3,4,5,32):
        obs=[g.buffer(.2005,quad_segs=64) for d,g in zip(pads,gs) if d['layer'] in (ll,74) and d['net']!='GND']
        obs += [LineString([t['a'],t['b']]).buffer(t['width']/2+.203,quad_segs=32) for t in p['tracks'] if t['layer']==ll]
        if ll==32:obs.append(allrf.buffer(.055+.203,quad_segs=48))
        obs += [Point(v['x'],v['y']).buffer(v['diameter']/2+.2005,quad_segs=64) for v in p['vias']]
        if ll!=1:obs.append(excluded)
        raw=board.buffer(-.2,join_style='mitre').difference(unary_union(obs))
        anchors=unary_union([g for d,g in zip(pads,gs) if d['net']=='GND']+[Point(v['x'],v['y']).buffer(.125,quad_segs=48) for v in p['shield_vias'] if ll in (5,32)])
        parts=list(raw.geoms) if hasattr(raw,'geoms') else [raw]
        keep=[g for g in parts if g.intersects(anchors)];grounds[ll]=unary_union(keep)
        details[ll]=dict(kept=len(keep),removed=len(parts)-len(keep))
    # Fully shield-land-covered regions must survive; GND is anchored globally in
    # a separate saved-copper graph audit, not inferred solely from intersections.
    uncovered=[]
    for v in p['shield_vias']:
        land=Point(v['x'],v['y']).buffer(.125,quad_segs=64)
        for ll in (5,32):
            if land.difference(grounds[ll].buffer(.00001)).area>1e-8:uncovered.append((v['label'],ll,v['x'],v['y']))
    qdv=unary_union([Point(v['x'],v['y']).buffer(v['diameter']/2) for v in p['vias'] if v['label'].startswith('Q1-')])
    qframe=box(*qdv.bounds).buffer(.3,join_style='mitre').difference(box(cx-2.15,cy-2.65,cx+2.15,cy+2.65))
    rc=[];smp=[]
    for g in groups:
        rr=[pg(d) for d in pads if d['ref'] in (g['row']['resistor'],g['row']['capacitor'])];rc.append(box(*unary_union(rr).bounds).buffer(.9,join_style='mitre'))
        smp.append(unary_union([pg(d) for d in pads if d['ref']==g['row']['smp']]).convex_hull.buffer(.3,quad_segs=32))
    zv=unary_union([Point(v['x'],v['y']).buffer(v['diameter']/2) for v in p['vias'] if v['label'].startswith('J1-')])
    zt=box(*unary_union([zv]+[pg(d) for d in pads if d['ref']=='J1']).bounds).buffer(.3,join_style='mitre');zb=box(*zv.bounds).buffer(.4,join_style='mitre')
    mounts=unary_union([g.buffer(.1) for d,g in zip(pads,gs) if d['ref'] is None]);extent=board.buffer(.05,join_style='mitre')
    top=extent.difference(unary_union(smp+rc+[zt,qframe])).union(mounts)
    bot=extent.difference(unary_union(smp+rc+[zb,allrf.buffer(.71,quad_segs=48)]).difference(field)).union(mounts).union(field)
    p.update(ground_regions={str(l):mapping(g) for l,g in grounds.items()},solder_openings={'37':mapping(top),'38':mapping(bot)},qd_ground_exclusion=mapping(excluded),qd_mask_field=mapping(field),ground_islands=details)
    minhole=min(allrf.distance(Point(v['x'],v['y']))-.055-.05 for v in p['shield_vias'])
    report=dict(rf_fits=fits,max_fit_error_mm=max(z['error_mm'] for z in fits),shield_hole_to_RF_mm=minhole,uncovered_shield_lands=uncovered,counts={k:len(p[k]) for k in ('components','physical_pads','tracks','arcs','vias','shield_vias')},ground_islands=details)
    (HERE/'candidate.json').write_text(json.dumps(p,indent=2));(HERE/'preparation_audit.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!='rf_fits'},indent=2))
    assert minhole>=.33
    assert not uncovered,uncovered[:6]
    assert len(p['components'])==50 and len(pads)==241
    actual={}
    for d in pads:
        if d['ref'] and d['net']:actual.setdefault(d['net'],[]).append(d['ref']+'-'+d['pin'])
    assert {n:sorted(v) for n,v in actual.items()}=={n:sorted(v) for n,v in p['nets'].items()}

if __name__=='__main__':main()
