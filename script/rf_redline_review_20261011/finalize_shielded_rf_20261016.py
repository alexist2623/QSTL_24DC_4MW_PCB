"""Create and independently audit explicit shield geometry for the offline plan."""
import json, math, csv
from itertools import combinations
import numpy as np
import shapely
from shapely.geometry import Point, LineString, Polygon, box
from shapely.ops import unary_union, substring
from scipy.spatial import cKDTree
from matplotlib.collections import PatchCollection
import shielded_symmetric_rf_plan_20261016 as m

OUT=m.OUT

def load_routes():
    data=json.loads(m.base.SOURCE.read_text());groups=m.sym.build_groups(data);st=m.base.build_static(data)
    saved=json.loads((OUT/'routing_working.json').read_text())['groups'];by={g['row']['smp']:g for g in saved}
    for g in groups:
        old=by[g['row']['smp']]
        for k in ('qd_to_c2','smp_to_c1'):g[k]=np.array(old[k])
        g['qline']=LineString(g['qd_to_c2']);g['sline']=LineString(g['smp_to_c1'])
        g['lines']=unary_union([g['qline'],g['sline']]);g['local_radius']=old['local_radius']
        g['tail']=unary_union([g['qline'].difference(m.QD_LAUNCH_ZONE),g['sline']])
    return data,groups,st

def launch_exceptions(groups):
    records=[]
    for g in groups:
        line=g['qline'];others=unary_union([h['lines'] for h in groups if h is not g])
        stations=np.linspace(0,line.length,math.ceil(line.length/.005)+1)
        points=shapely.line_interpolate_point(line,stations)
        gaps=shapely.distance(points,others)-m.WIDTH
        bad=np.where(gaps<m.RF_CENTRE_TARGET-m.WIDTH)[0]
        close=line.intersection(others.buffer(m.RF_CENTRE_TARGET,quad_segs=64))
        coords=shapely.get_coordinates(close)
        end=0. if len(coords)==0 else min(line.length,max(line.project(Point(p)) for p in coords)+.005)
        exception=substring(line,0,end) if end else Point(line.coords[0])
        radial=max((m.QD_END_RECT.distance(p) for p in points[bad]),default=0.)
        records.append(dict(channel=g['row']['smp'],qd_pad=g['row']['qd_pad'],exception_length_mm=end,
                            maximum_distance_outside_QD_end_rectangle_mm=radial,
                            minimum_gap_within_exception_mm=float(min(gaps)),
                            points_mm=list(exception.coords)))
        g['exception_end']=end
    return records

def all_pad_geometry(groups,st):
    return unary_union([p for _,_,p in st['smp_pads']]+[p for _,p in st['qd']]+
                       [Polygon(p['polygon_mm']) for g in groups for c in (g['capacitor'],g['resistor']) for p in c['pads']])

def create_vias(data,groups,st):
    all_rf=unary_union([g['lines'] for g in groups]);pads=all_pad_geometry(groups,st)
    bodies=unary_union([Polygon(c['body_polygon_mm']).union(unary_union([Polygon(p['polygon_mm']) for p in c['pads']])).convex_hull
                        for g in groups for c in (g['capacitor'],g['resistor'])])
    mounts=unary_union([p for _,p in st['mounts']]);outline=box(*data['board_bounds_xy_mm'])
    # The user permits shared fences in crowded QD fanout; preserve unfenced pads.
    exceptions=unary_union([substring(g['qline'],0,g['exception_end']) for g in groups if g['exception_end']>0])
    positions=[];records=[];grid={};cell=.4
    reject={}
    def add(xy,channel,kind,station=None):
        p=Point(xy)
        reason=None
        if all_rf.distance(p)<.435-1e-8:reason='RF hole-edge gap'
        elif pads.distance(p)<.325:reason='component pad clearance'
        elif bodies.distance(p)<.125:reason='component body envelope'
        elif mounts.distance(p)<.325:reason='mount clearance'
        elif st['cavity'].distance(p)<.325:reason='cavity clearance'
        elif not outline.buffer(-.325).covers(p):reason='board edge'
        elif m.QD_END_RECT.distance(p)<.125:reason='QD bond-field exclusion'
        key=(math.floor(xy[0]/cell),math.floor(xy[1]/cell))
        if reason is None:
            for i in range(key[0]-1,key[0]+2):
                for j in range(key[1]-1,key[1]+2):
                    if any(np.linalg.norm(np.array(xy)-positions[k])<.40001 for k in grid.get((i,j),[])):
                        reason='via separation';break
                if reason:break
        if reason:
            reject[reason]=reject.get(reason,0)+1;return False
        grid.setdefault(key,[]).append(len(positions));positions.append(np.array(xy))
        records.append(dict(x_mm=float(xy[0]),y_mm=float(xy[1]),land_mm=.25,hole_mm=.10,net='GND',
                            start_layer='L5',end_layer='L6',channel=channel,kind=kind,station_mm=station,paste=False))
        return True
    # Equal-angle rings first; paired omissions preserve each RF escape symmetry.
    rings=[]
    for g in groups:
        name=g['row']['smp'];centre=np.array(g['row']['start'])
        old=next(r for r in data['routes'] if r['smp']==name);v=np.array(old['entry_outward'])
        angle=math.atan2(v[1],v[0]);accepted=[]
        for k in range(1,12):
            theta=angle+k*math.pi/6;xy=centre+.91*np.array([math.cos(theta),math.sin(theta)])
            if add(xy,name,'SMP ring'):accepted.append(k)
        assert accepted==list(range(1,12)),(name,accepted)
        rings.append(dict(channel=name,radius_mm=.91,grid_degrees=30,occupied_grid_indices=accepted,escape_omission_degrees=0))
    # Prioritize one common row at the medial corridor of two close RF traces.
    # Exact distance checks reject every point lacking 3W clearance to either RF.
    shared_candidates=[]
    for a,b in combinations(groups,2):
        if a['qline'].distance(b['qline'])>=m.RF_CENTRE_TARGET:continue
        for aa,bb in ((a,b),(b,a)):
            line=aa['qline'];other=bb['qline']
            for t in np.arange(.0,min(line.length,aa['exception_end']+.6),.035):
                p=line.interpolate(t);q=other.interpolate(other.project(p));d=p.distance(q)
                if not .87<=d<=1.298:continue
                xy=np.array([(p.x+q.x)/2,(p.y+q.y)/2])
                if not m.QD_LAUNCH_ZONE.covers(Point(xy)):continue
                shared_candidates.append((xy,aa['row']['smp']+'/'+bb['row']['smp'],float(t)))
    shared_candidates.sort(key=lambda c:(round(c[0][1],2),c[0][0]))
    for xy,n,t in shared_candidates:add(xy,n,'QD shared row',t)
    row_stats=[]
    for g in groups:
        name=g['row']['smp']
        for mode,line in [('QD-R-C',g['qline']),('C-SMP',g['sline'])]:
            for side in (-1,1):
                offset=line.offset_curve(side*m.OFFSET,quad_segs=32)
                pieces=list(offset.geoms) if hasattr(offset,'geoms') else [offset]
                accepted=0
                for piece in pieces:
                    for t in np.arange(.10,piece.length,.410):
                        xy=piece.interpolate(t).coords[0]
                        accepted+=add(xy,name,f'{mode} side {side}',float(t))
                row_stats.append(dict(channel=name,segment=mode,side=side,count=accepted))
    # Perimeter fences around the complete component convex hulls, with RF escape gaps.
    for g in groups:
        for c in (g['capacitor'],g['resistor']):
            hull=m.base.as_component_geometry(c).convex_hull
            line=hull.buffer(.38,quad_segs=32).exterior
            for t in np.arange(.10,line.length,.410):
                add(line.interpolate(t).coords[0],g['row']['smp'],c['ref']+' perimeter',float(t))
    return records,rings,row_stats,reject

def audit(data,groups,st,vias,exceptions):
    xy=np.array([[v['x_mm'],v['y_mm']] for v in vias]);points=shapely.points(xy)
    all_rf=unary_union([g['lines'] for g in groups]);pads=all_pad_geometry(groups,st)
    nearest=cKDTree(xy).query(xy,k=2)[0][:,1]
    vv=float(min(nearest))-.25
    vr=float(min(shapely.distance(points,all_rf)))-.05-.055
    vp=float(min(shapely.distance(points,pads)))-.125
    assert vv>=.15-1e-8 and vr>=.33-1e-8 and vp>=.2-1e-8,(vv,vr,vp)
    pairs=[]
    actual_pairs=[]
    for a,b in combinations(groups,2):
        gap=min(a['tail'].distance(b['lines']),b['tail'].distance(a['lines']))-.11
        assert gap>=1.16,(a['row']['smp'],b['row']['smp'],gap)
        pairs.append((gap,a['row']['smp'],b['row']['smp']))
        ta=unary_union([substring(a['qline'],a['exception_end'],a['qline'].length),a['sline']])
        tb=unary_union([substring(b['qline'],b['exception_end'],b['qline'].length),b['sline']])
        actual=min(ta.distance(b['lines']),tb.distance(a['lines']))-.11
        assert actual>=1.18-1e-5,(a['row']['smp'],b['row']['smp'],actual)
        actual_pairs.append((actual,a['row']['smp'],b['row']['smp']))
        assert a['lines'].distance(b['lines'])>.11
    angles=[]
    for g in groups:
        q=g['qd_to_c2'];s=g['smp_to_c1'];u=g['u'];eu=np.array(g['row']['outward']);j=g['j']
        def angle(a,b):
            a=a/np.linalg.norm(a);b=b/np.linalg.norm(b)
            return math.degrees(math.acos(float(np.clip(np.dot(a,b),-1,1))))
        vals={'QD':angle(q[1]-q[0],eu),'C2':angle(q[-1]-q[-2],u),'C1':angle(s[1]-s[0],u)}
        for p in (j-.5*u,j+.5*u):
            ds=g['qline'].project(Point(p));aa=np.array(g['qline'].interpolate(ds-.02).coords[0]);bb=np.array(g['qline'].interpolate(ds+.02).coords[0])
            vals['R1_entry' if np.dot(p-j,u)<0 else 'R1_exit']=angle(bb-aa,u)
            assert g['qline'].distance(Point(p))<1e-7
        cen=np.array(g['row']['start']);vals['SMP']=angle(s[-1]-s[-2],cen-s[-2])
        assert max(vals.values())<1e-4,vals
        angles.append(dict(channel=g['row']['smp'],normal_error_deg=vals))
    basic=m.base.audit(data,groups,st)
    shared=[v for v in vias if v['kind']=='QD shared row']
    for v in shared:
        p=Point(v['x_mm'],v['y_mm'])
        channels=v['channel'].split('/')
        distances=[p.distance(next(g['lines'] for g in groups if g['row']['smp']==ch)) for ch in channels]
        assert min(distances)>=.435-1e-8 and max(distances)<.70
    return dict(status='PASS: offline geometry only',native_Altium_DRC='NOT RUN: native PCB unchanged',
                RF_width_mm=.11,requested_RF_edge_gap_mm=1.16,minimum_RF_edge_gap_outside_QD_exception_mm=min(actual_pairs),
                minimum_RF_edge_gap_outside_3mm_envelope_mm=min(pairs),
                via_count=len(vias),QD_shared_via_count=len(shared),land_diameter_mm=.25,hole_diameter_mm=.10,annular_ring_mm=.075,
                span='L5-L6 only',minimum_via_land_gap_mm=vv,minimum_RF_copper_to_hole_edge_mm=vr,
                minimum_via_land_to_component_pad_mm=vp,nominal_fence_centre_offset_mm=.438,nominal_row_pitch_mm=.410,
                pad_normal_checks=angles,maximum_QD_exception_distance_from_pad_end_rectangle_mm=max(x['maximum_distance_outside_QD_end_rectangle_mm'] for x in exceptions),
                maximum_exception_route_length_mm=max(x['exception_length_mm'] for x in exceptions),
                symmetry=m.sym.symmetry_check(groups),basic_geometry_checks=basic)

def render(data,groups,st,vias,exceptions,checks):
    def draw(ax,ylim):
        m.base.paint(ax,data,groups,st,ylim)
        patches=[m.base.Circle((v['x_mm'],v['y_mm']),.125) for v in vias]
        pc=PatchCollection(patches,facecolor='#40816e',edgecolor='none',alpha=.8,zorder=10);ax.add_collection(pc)
        shared=[m.base.Circle((v['x_mm'],v['y_mm']),.125) for v in vias if v['kind']=='QD shared row']
        ax.add_collection(PatchCollection(shared,facecolor='#b4499c',edgecolor='none',zorder=11))
        holes=[m.base.Circle((v['x_mm'],v['y_mm']),.05) for v in vias]
        ax.add_collection(PatchCollection(holes,facecolor='#e7f4ed',edgecolor='none',zorder=11))
        for e in exceptions:
            xy=np.array(e['points_mm'])
            if len(xy)>1:ax.plot(*xy.T,color='#e9a35c',lw=5,alpha=.35,zorder=8)
    fig,ax=m.base.plt.subplots(figsize=(11,16),dpi=240);draw(ax,(18.5,73.5))
    ax.set_title('16 RF channels | normal pad entry + explicit L5-L6 shield vias\nFixed symmetric R0603 / C1206 placement',fontsize=14,pad=18)
    fig.text(.5,.043,f"W 0.11 mm | Via land/hole 0.25/0.10 mm | {len(vias)} proposed GND microvias",ha='center',fontsize=10)
    fig.text(.5,.026,f"Outside amber QD launches: RF gap >= {checks['minimum_RF_edge_gap_outside_QD_exception_mm'][0]:.3f} mm | Via land gap >= {checks['minimum_via_land_gap_mm']:.3f} mm",ha='center',fontsize=10)
    fig.text(.5,.01,'PLAN ONLY: native PCB/DC/GND/mask/DRC and impedance verification remain pending.',ha='center',fontsize=9,color='#995b44')
    fig.tight_layout(rect=(0,.06,1,1));fig.savefig(OUT/'Shielded_RF_Overview.png');m.base.plt.close(fig)
    fig,ax=m.base.plt.subplots(figsize=(14,11),dpi=220);draw(ax,(38.5,53.5));ax.set_xlim(2,17.5)
    ax.set_title('QD fanout: shared via rows where space permits\nMagenta = shared GND via | Amber = relaxed RF-spacing launch',fontsize=14,pad=18)
    for e in exceptions:
        if e['exception_length_mm']>0:
            xy=np.array(e['points_mm']);p=xy[-1];ax.plot(*p,'o',ms=4,color='#b46020',zorder=15)
    fig.text(.5,.045,'Pad approaches remain unfenced where a via cannot fit. Brown dots mark return to separate-row spacing.',ha='center',fontsize=10)
    fig.text(.5,.022,f"Crowded copper lies at most {checks['maximum_QD_exception_distance_from_pad_end_rectangle_mm']:.2f} mm outside the aligned QD pad-end rectangle.",ha='center',fontsize=10)
    fig.tight_layout(rect=(0,.07,1,1));fig.savefig(OUT/'QD_Launch_Shield_Detail.png');m.base.plt.close(fig)
    fig,axes=m.base.plt.subplots(1,2,figsize=(14,7),dpi=200)
    for ax,ylim,xlim,title in zip(axes,[(51,56.5),(22,31.5)],[(.5,7),(1,10)],['R09 / C09: pad-edge normal entry','C15 / R15 and SMP15 circular fence']):
        draw(ax,ylim);ax.set_xlim(*xlim);ax.set_title(title,fontsize=12)
    fig.suptitle('RF crosses each land boundary at 90 degrees; bends begin outside the land',fontsize=14)
    fig.tight_layout(rect=(0,0,1,.95));fig.savefig(OUT/'Pad_Normal_Entry_Detail.png');m.base.plt.close(fig)

def main():
    routing=json.loads((OUT/'routing_working.json').read_text())
    routing.pop('maximum_launch_exception_mm',None)
    routing['QD_fanout_envelope_extension_mm']=3.0
    routing['exception_basis']='Distance from aligned QD pad-end rectangle; actual relaxed prefixes measured in final audit.'
    (OUT/'routing_working.json').write_text(json.dumps(routing,indent=2)+'\n')
    data,groups,st=load_routes();exceptions=launch_exceptions(groups)
    previous=json.loads((m.base.ROOT/'QSTL_QD4_2SET_38PAD/Symmetric_RC_Placement_20261016/symmetric_rc_audit.json').read_text())
    protected={path:m.base.digest(m.base.Path(path)) for path in previous['source_hashes']}
    assert protected==previous['source_hashes'],'A protected source changed since the accepted symmetric proposal'
    vias,rings,rows,rejected=create_vias(data,groups,st)
    checks=audit(data,groups,st,vias,exceptions)
    saved=dict(scope='Offline proposal only; not fabrication or native PCB release',checks=checks,
               exceptions=exceptions,vias=vias,rings=rings,row_counts=rows,rejected_candidates=rejected,
               source_geometry_file=str(m.base.SOURCE),source_geometry_SHA256=m.base.digest(m.base.SOURCE),
               routes_file='routing_working.json',routes_SHA256=m.base.digest(OUT/'routing_working.json'),
               protected_source_hashes=protected,protected_sources_unchanged=True)
    (OUT/'shield_geometry_audit.json').write_text(json.dumps(saved,indent=2)+'\n')
    (OUT/'shielded_rf_plan.json').write_text(json.dumps(dict(**saved,groups=routing['groups']),indent=2)+'\n')
    with (OUT/'proposed_L5_L6_GND_vias.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(vias[0]));writer.writeheader();writer.writerows(vias)
    # Independently reopen the deliverable before producing images and completion metrics.
    reopened=json.loads((OUT/'shield_geometry_audit.json').read_text())
    audit(data,groups,st,reopened['vias'],reopened['exceptions'])
    render(data,groups,st,vias,exceptions,checks)
    print(json.dumps({k:v for k,v in checks.items() if k not in ('pad_normal_checks','symmetry','basic_geometry_checks')},indent=2))

if __name__=='__main__':main()
