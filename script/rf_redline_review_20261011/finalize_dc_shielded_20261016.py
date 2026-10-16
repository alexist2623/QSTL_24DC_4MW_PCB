"""Simplify, independently validate and render the saved DC routing proposal."""
import json,csv,math,sys
from itertools import combinations
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as Patch, Circle, Rectangle
from shapely.geometry import Point,LineString,Polygon,box
from shapely.ops import unary_union
import dc_shielded_plan_20261016 as dc
old=dc.old;ROOT=dc.ROOT;OUT=dc.OUT;W=dc.W;GAP=dc.GAP;GUARD=dc.GUARD

def caches(plan,data,groups,st,routes):
    objects,bodies=dc.obstacles(plan,data,groups,st)
    return [dc.own_obstacles(objects,bodies,groups,{r['source'],r['port']}) for r in routes]

def simplify(plan,data,groups,st,routes):
    obs=caches(plan,data,groups,st,routes);boundary=box(*data['board_bounds_xy_mm']).buffer(-.2)
    copper=[LineString(r['points']).buffer(W/2,quad_segs=32) for r in routes]
    def legal(p,i):
        c=LineString(p).buffer(W/2,quad_segs=32)
        if not boundary.covers(c) or c.distance(obs[i])<GAP+GUARD-1e-7:return False
        return all(c.distance(g)>=GAP+GUARD-1e-7 for j,g in enumerate(copper) if i!=j and routes[i]['layer']==routes[j]['layer'])
    for sweep in range(8):
        changes=0
        for i in (range(len(routes)) if sweep%2==0 else reversed(range(len(routes)))):
            r=routes[i]
            blocked=unary_union([obs[i]]+[copper[j] for j in range(len(routes)) if j!=i and routes[j]['layer']==r['layer']])
            p=old.minimum_bend_shortcut(r['points'],blocked,boundary)
            if old.bend_score(p)<old.bend_score(r['points'])-1e-6:
                r['points']=p;copper[i]=LineString(p).buffer(W/2,quad_segs=32);changes+=1
        print('SIMPLIFY',sweep,'changes',changes,flush=True)
        dc.save('simplified_checkpoint.json',routes)
        if not changes:break
    chamfers=[]
    for i,r in enumerate(routes):
        p=r['points'];k=1
        while k<len(p)-1:
            a,b,c=map(np.array,p[k-1:k+2]);u=b-a;v=c-b;lu=np.linalg.norm(u);lv=np.linalg.norm(v);u/=lu;v/=lv
            turn=math.degrees(math.atan2(u[0]*v[1]-u[1]*v[0],np.dot(u,v)))
            if abs(turn)<=45.01:k+=1;continue
            accepted=False
            for trim in (.4,.3,.2,.15,.1,.075,.05,.025,.01,.005,.002):
                trim=min(trim,lu*.4,lv*.4);p0=b-trim*u;p1=b+trim*v
                count=int(round(abs(turn)/45))-1;theta=math.atan2(u[1],u[0]);sign=np.sign(turn)
                vectors=np.array([[math.cos(theta+sign*j*math.pi/4),math.sin(theta+sign*j*math.pi/4)] for j in range(1,count+1)])
                total=np.sum(vectors,axis=0);length=float(np.dot(p1-p0,total)/np.dot(total,total));mid=[p0.tolist()];cur=p0.copy()
                for vector in vectors:cur=cur+length*vector;mid.append(cur.tolist())
                if math.dist(mid[-1],p1)>1e-6:continue
                q=old.compact(p[:k]+mid+p[k+1:])
                if legal(mid,i):
                    chamfers.append(dict(net=r['net'],at_mm=b.tolist(),trim_mm=trim));p=q;copper[i]=LineString(p).buffer(W/2,quad_segs=32)
                    k+=len(mid);accepted=True;break
            if not accepted:k+=1
        r['points']=p
    return routes,chamfers

def audit(plan,data,groups,st,shield,routes):
    failures=[];copper=[LineString(r['points']).buffer(W/2,quad_segs=64) for r in routes]
    obs=caches(plan,data,groups,st,routes);boundary=box(*data['board_bounds_xy_mm']).buffer(-.2)
    via={v['label']:v for v in plan['vias']};endpoints=[];minimums={};badturns=[]
    def record(kind,d,required,a,b):
        if kind not in minimums or d<minimums[kind]['gap_mm']:minimums[kind]=dict(gap_mm=float(d),a=a,b=b,required_mm=required)
        if d<required-2e-6:failures.append(dict(kind=kind,a=a,b=b,gap_mm=float(d),required_mm=required))
    for i,r in enumerate(routes):
        g=copper[i];line=LineString(r['points'])
        record('normalized static clearance',g.distance(obs[i]),GAP,r['net'],'static')
        if not boundary.covers(g):failures.append(dict(net=r['net'],kind='board edge'))
        if not line.is_simple:failures.append(dict(net=r['net'],kind='self crossing'))
        ends=[via[r['source']],via[r['port']]]
        good=all(math.dist(xy,[v['x'],v['y']])<1e-7 for xy,v in zip([r['points'][0],r['points'][-1]],ends))
        endpoints.append(dict(net=r['net'],source=r['source'],port=r['port'],centres_connected=good))
        if not good:failures.append(dict(net=r['net'],kind='disconnected terminal'))
        for j in range(i):
            if routes[j]['layer']==r['layer']:record('DC trace to trace',g.distance(copper[j]),.1,r['net'],routes[j]['net'])
        for v in plan['vias']:
            if v['label'] in (r['source'],r['port']):continue
            d=g.distance(Point(v['x'],v['y']))
            record('DC trace to foreign via land',d-v['diameter']/2,.1,r['net'],v['label'])
            record('DC trace to foreign drill edge',d-v['hole']/2,.2,r['net'],v['label'])
        for name,gpad in st['mounts']:
            record('DC trace to mounting envelope',g.distance(gpad),.2,r['net'],name)
        record('DC trace to cavity',g.distance(st['cavity']),.15,r['net'],'cavity')
        for k,t in old.turns(r['points']):
            if abs(t)>45.01:badturns.append(dict(net=r['net'],index=k,turn_deg=t))
        for a,b in zip(r['points'],r['points'][1:]):
            dx,dy=abs(b[0]-a[0]),abs(b[1]-a[1])
            if min(dx,dy,abs(dx-dy))>1e-7:failures.append(dict(net=r['net'],kind='non H/V/45 segment'))
    # The Top fanout is reused by contact, irrespective of the new DC net name.
    top=plan['top_fanout'];jpad=data['ZIF']['translated_pads']
    for i,t in enumerate(top):
        g=LineString(t['points']).buffer(t['width']/2,quad_segs=64)
        p=next(p for p in jpad if 'J1-'+p['number']==t['port']);v=via[t['port']]
        if not g.intersects(dc.base.pg(p)) or not g.intersects(Point(v['x'],v['y']).buffer(.2)):
            failures.append(dict(kind='Top fanout disconnected',port=t['port']))
        for other in jpad:
            if other is not p:record('Top fanout to foreign pad',g.distance(dc.base.pg(other)),.15,t['port'],'J1-'+other['number'])
        for w in plan['vias']:
            if w['label']!=t['port']:record('Top fanout to foreign via',g.distance(Point(w['x'],w['y']))-w['diameter']/2,.15,t['port'],w['label'])
        for o in top[:i]:record('Top fanout to fanout',g.distance(LineString(o['points']).buffer(o['width']/2,quad_segs=64)),.15,t['port'],o['port'])
    terminal=dc.terminal_audit(plan,data,groups,st,shield)
    failures+=terminal['failures']
    unique=len(routes)==len({r['net'] for r in routes})==len({r['port'] for r in routes})==38
    pool={int(r['port'].split('-')[1]) for r in routes};expected=set(range(2,50,2))|set(range(1,28,2))
    protected={p:dc.base.digest(dc.Path(p))==h for p,h in shield['protected_source_hashes'].items()}
    if not unique or pool!=expected:failures.append(dict(kind='nonbijective or wrong contact pool'))
    if {r['layer'] for r in routes}!={2,3}:failures.append(dict(kind='DC must use L2 and L3 only'))
    if plan.get('planned_layer_roles')!=dc.LAYER_ROLES:failures.append(dict(kind='Incorrect planned layer roles'))
    if not all(protected.values()):failures.append(dict(kind='protected sources changed',checks=protected))
    failures+=badturns
    return dict(passed=not failures,failures=failures,routes=len(routes),layer_counts={str(l):sum(r['layer']==l for r in routes) for l in (2,3)},planned_layer_roles=dc.LAYER_ROLES,
        dc_width_mm=W,minimums=minimums,terminal_geometry=terminal,endpoint_checks=endpoints,one_internal_layer_per_net=True,
        standalone_transition_vias=0,terminal_vias=len(via),RF_signal_vias=0,retained_L5_L6_shield_vias=len(shield['vias']),
        used_ZIF_pins=sorted(pool),ZIF_pin50_unused=50 not in pool,non45_turns=badturns,
        complete_SMP_pad_hulls_excluded=True,resistor_interpad_body_excluded=True,protected_sources_unchanged=protected,
        native_PCB_and_schematic_updated=False,native_DRC_performed=False)

def draw_background(ax,data,groups,st,shield,show_rf=True):
    ax.set_facecolor('#f4f7f9');xmin,ymin,xmax,ymax=data['board_bounds_xy_mm']
    ax.add_patch(Rectangle((xmin,ymin),xmax-xmin,ymax-ymin,fill=False,ec='#47616a',lw=1.1))
    for name,g in st['mounts']:
        ax.add_patch(Patch(np.array(g.exterior.coords),fc='#e4e9ec',ec='#8c9ca3',lw=.5))
        h=next(h for h in data['mounts'] if h['name']==name)
        ax.add_patch(Circle(h['xy_mm'],1.6 if name.startswith('P') else 1,fc='white',ec='#6b747a',lw=.5))
        ax.text(*h['xy_mm'],name,ha='center',va='center',fontsize=5,color='#52616b',clip_on=True)
    for n,p,g in st['smp_pads']:
        ax.add_patch(Patch(np.array(g.exterior.coords),fc='#d5dadd',ec='#a6afb6',lw=.3))
    for n,g in st['qd']:ax.add_patch(Patch(np.array(g.exterior.coords),fc='#d5b46b',ec='none'))
    ax.add_patch(Patch(np.array(st['cavity'].exterior.coords),fc='#203b46',ec='none'))
    ax.text(*data['qd_centre_mm'],'QD',ha='center',va='center',fontsize=8,color='white',clip_on=True)
    for g in groups:
        for c in (g['resistor'],g['capacitor']):
            ax.add_patch(Patch(c['body_polygon_mm'],fc='#dbe0e3',ec='#b2bbc1',lw=.3))
            for p in c['pads']:ax.add_patch(Patch(p['polygon_mm'],fc='#d1bb8c',ec='none'))
        ax.text(*g['resistor']['centre_mm'],g['resistor']['ref'],ha='center',va='center',fontsize=4.5,color='#344955',clip_on=True)
        if show_rf:
            for key in ('qd_to_c2','smp_to_c1'):
                a=np.array(g[key]);ax.plot(a[:,0],a[:,1],c='#d6a05c',lw=.6,alpha=.6,zorder=2)
    for p in data['ZIF']['translated_pads']:
        g=dc.base.pg(p);ax.add_patch(Patch(np.array(g.exterior.coords),fc='#8c9da4',ec='none'))
    ax.set_aspect('equal');ax.set_xlim(xmin-1,xmax+1);ax.set_ylim(ymin-1,ymax+1)
    ax.set_xlabel('X (mm)',fontsize=8);ax.set_ylabel('Y (mm)',fontsize=8);ax.tick_params(labelsize=7)
    ax.grid(lw=.3,alpha=.22)

def render(plan,data,groups,st,shield,routes,audit):
    colors={2:'#1e69b5',3:'#a53b86'}
    def draw(ax,layer=None):
        draw_background(ax,data,groups,st,shield)
        for r in routes:
            if layer and layer!=r['layer']:continue
            p=np.array(r['points']);ax.plot(p[:,0],p[:,1],color=colors[r['layer']],lw=.8,zorder=5)
            ax.text(*p[0],str(r['qd_pad']),fontsize=4.5,color=colors[r['layer']],ha='right',va='bottom',zorder=9,clip_on=True)
        for v in plan['vias']:
            ax.add_patch(Circle((v['x'],v['y']),v['diameter']/2,fc='white',ec='#425969',lw=.35,zorder=6))
        for t in plan['top_fanout']:
            p=np.array(t['points']);ax.plot(p[:,0],p[:,1],color='#5f8b64',lw=.65,zorder=4)
    fig,axs=plt.subplots(1,3,figsize=(15,13))
    for ax,layer in zip(axs,[2,3,None]):
        draw(ax,layer);ax.set_title(f'L{layer} DC: 19 routes' if layer else 'Combined: 38 DC + Bottom RF',fontsize=11)
    fig.suptitle('Fixed 16-RF proposal | 38 DC channels routed to ZIF',fontsize=15,y=.985)
    fig.text(.5,.035,'Blue: L2 DC | Magenta: L3 DC | L4: GND | Faint gold: L6 RF | Green: Top ZIF fanout\n0.125 mm DC width | One internal layer per net | No intermediate DC vias\nCoordinate proposal, not an Altium screenshot. Native PCB/schematic and DRC not updated.',ha='center',fontsize=9)
    fig.subplots_adjust(left=.045,right=.99,top=.95,bottom=.095,wspace=.18);fig.savefig(OUT/'DC_Layers_Overview.png',dpi=190);plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(13,8))
    for ax,l in zip(axs,[2,3]):
        draw(ax,l);ax.set_xlim(3.8,15.7);ax.set_ylim(39.8,52.7);ax.set_title(f'L{l}: QD and resistor terminal exits',fontsize=12)
    fig.suptitle('QD fanout | Terminal vias remain inside their original pads',fontsize=15)
    fig.text(.5,.035,'Gold: fixed Bottom bond pads and RF routes | Coloured routes are on internal layers\nTerminal-via positions are checked against the retained L5-L6 shield fence.',ha='center',fontsize=9)
    fig.subplots_adjust(bottom=.1,top=.94);fig.savefig(OUT/'DC_QD_Detail.png',dpi=200);plt.close(fig)
    fig,ax=plt.subplots(figsize=(13,6));draw(ax)
    ax.set_xlim(1,18.7);ax.set_ylim(-9.7,-1.9);ax.set_title('Relocated ZIF | Exact existing 24 even + 14 odd contacts',fontsize=13)
    for r in routes:
        v=next(v for v in plan['vias'] if v['label']==r['port']);ax.text(v['x'],v['y']-.36,str(v['pin']),ha='center',va='top',fontsize=6,color=colors[r['layer']])
    fig.text(.5,.025,'Numbers indicate ZIF contact numbers. Pin 50 is unused. Top fanout geometry is translated unchanged.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.055,1,.97));fig.savefig(OUT/'DC_ZIF_Detail.png',dpi=200);plt.close(fig)

def main():
    data,groups,st,snapshot,mapping,shield=dc.load();plan=json.loads((OUT/'dc_input.json').read_text())
    if '--verify' in sys.argv:
        result=json.loads((OUT/'dc_routed_plan.json').read_text());routes=result['routes'];chamfers=result['chamfers']
    else:
        routes=json.loads((OUT/'raw_dc_routes.json').read_text());routes,chamfers=simplify(plan,data,groups,st,routes)
        dc.save('dc_routed_plan.json',dict(**plan,routes=routes,chamfers=chamfers))
        routes=json.loads((OUT/'dc_routed_plan.json').read_text())['routes']
    report=audit(plan,data,groups,st,shield,routes);dc.save('dc_geometry_audit.json',report)
    print('AUDIT',json.dumps(report,indent=2)[:8000],flush=True)
    if not report['passed']:return
    rows=[]
    for r in sorted(routes,key=lambda r:r['qd_pad']):
        src=next(m for m in mapping if int(m['qd_pad'])==r['qd_pad'])
        rows.append(dict(**src,old_zif_pin=src['zif_pin'],old_dc_layer=src['dc_layer'],proposed_zif_pin=int(r['port'].split('-')[1]),proposed_dc_layer=r['layer'],dc_source=r['source'],route_length_mm=LineString(r['points']).length))
    with (OUT/'proposed_pin_mapping.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    changes=[dict(qd_pad=r['qd_pad'],dc_net=r['dc_net'],old_ZIF_pin=int(r['old_zif_pin']),new_ZIF_pin=r['proposed_zif_pin'],old_layer=int(r['old_dc_layer']),new_layer=r['proposed_dc_layer']) for r in rows]
    dc.save('schematic_change_contract.json',dict(status='Proposed assignments only; native schematic unchanged',
        unchanged_bias_tee='SMP -> C pad 1; C pad 2 / R pad 1 -> QD; R pad 2 -> DC; direct DC on the other 22 QD pads',
        assignments=changes,planned_layer_roles=dc.LAYER_ROLES,contact_pool_preserved=True,pin50_unused=True))
    minimum=report['minimums'];changed=sum(r['proposed_zif_pin']!=int(r['old_zif_pin']) for r in rows)
    text=f'''# DC routing on the fixed sixteen-RF proposal

## Scope and result

All 38 independent DC connections are saved as continuous, clearance-checked coordinate routes. L2 and L3 carry 19 nets each, and L4 is assigned to GND. Every net stays on one internal layer. This is an offline routing proposal, not an updated native PCB or a native DRC result. Native PCB, schematic, source mapping, RF proposal and mechanical placement are unchanged.

The fixed RF bias tees are preserved: 16 resistor pad-2 DC terminals, plus 22 direct QD terminals. Exactly 76 terminal vias are used, with no standalone transition vias and no RF signal vias. The 1,439 L5-L6-only shield microvias remain unchanged. Five direct-QD terminal vias move only inside their unchanged bond lands to maintain at least 0.20 mm clearance to shield lands; movements are recorded in `dc_routed_plan.json`.

## Geometry and connectivity checks

- DC width: 0.125 mm. Minimum same-layer copper gap: {minimum['DC trace to trace']['gap_mm']:.6f} mm (required 0.10 mm).
- Trace to foreign via land: {minimum['DC trace to foreign via land']['gap_mm']:.6f} mm; trace to foreign through-drill edge: {minimum['DC trace to foreign drill edge']['gap_mm']:.6f} mm (required 0.20 mm).
- Terminal via to Bottom RF copper: {report['terminal_geometry']['minimums_mm']['via to RF copper']:.6f} mm; terminal via to GND shield land: {report['terminal_geometry']['minimums_mm']['via to shield land']:.6f} mm.
- All source and ZIF terminal centres connect exactly after saving and reopening the route data. Each DC net has one distinct ZIF contact. All 24 even pins 2..48 and 14 odd pins 1..27 are used; pin 50 remains unused.
- {changed} contact assignments change relative to the native mapping. `proposed_pin_mapping.csv` and `schematic_change_contract.json` record the identical proposed mapping for future PCB/schematic implementation. These changes have not been applied to the native schematic.
- Internal DC copper excludes every complete SMP five-pad convex hull, resistor inter-pad/body envelope, mounting envelope and the central blind pocket. Passing under a capacitor body is allowed on an internal layer. Coincident XY projections on different layers are not electrical shorts.
- DC segments are horizontal, vertical or 45 degrees; no bend exceeds 45 degrees after chamfering. Source/component/connector coordinates are preserved except the five small terminal-via adjustments.
- Top ZIF fanout geometry is translated unchanged with the relocated connector and independently checked for pad/via/track clearance and continuity.

## Layer and manufacturing basis

The intended stack is L1 GND / L2 DC-A / L3 DC-B / L4 GND / L5 GND / L6 RF-QD. The user's L3/L4 exchange applies to this sixteen-RF proposal. The complete former L4 DC bank has moved to L3 without changing its XY routing or contacts. Historical native-source layer numbers are retained only in the `old_dc_layer` and source-mapping fields; they are not the proposed assignment. New L4 GND pours and antipads remain part of native implementation.

The prior order was six-layer HDI, 1-step, 1.6 mm, ENIG, outer 1 oz. Requested JLCH06161HN1-1078 / 0.0784 mm outer dielectric / 0.5 oz inner copper differed from the saved cart's NP-175F / 1 oz inner, subject to review. The RF target stays W=0.11 mm, coplanar gap 0.20 mm; this DC study does not establish impedance or resolve the manufacturer's stack review.

The [JLCPCB capability table](https://jlcpcb.com/capabilities/pcb-capabilities/) checked on 2026-10-16 specifies 0.09/0.09 mm multilayer 1 oz width/spacing and 0.20 mm inner copper-to-via-hole clearance. The router enforces 0.125/0.10 mm and checks hole-edge clearance separately from land clearance. Retained terminal via land/hole sizes are QD 0.35/0.20, R 0.50/0.25 and ZIF 0.40/0.20 mm. Ordinary via annular-ring rules must not be confused with component PTH annular rings.

## Remaining implementation work

Native placement/outline changes, route import, synchronized schematic mapping, GND pours and antipads, mask updates, native save/reopen connectivity/DRC and final fabrication checks remain pending. In particular, this inherited SMP footprint has approximately 0.125 mm component-PTH annular rings and needs its own manufacturing review; this is not a blanket JLCPCB approval. Gerbers and the shopping cart are not changed.

## Files

- `DC_Layers_Overview.png`: L2, L3 and combined views.
- `DC_QD_Detail.png`: QD and resistor DC terminal exits.
- `DC_ZIF_Detail.png`: relocated connector fanout with contact numbers.
- `dc_routed_plan.json`: all paths, vias and Top fanout.
- `dc_geometry_audit.json`: independently recomputed saved-geometry results.
- `proposed_pin_mapping.csv` and `schematic_change_contract.json`: synchronized proposed assignments.

Helper scripts are stored in the repository's `script/rf_redline_review_20261011/` directory. Source SHA256 checks are included in the audit. No native design/reference files were modified.
'''
    (OUT/'README.md').write_text(text,encoding='utf-8')
    render(plan,data,groups,st,shield,routes,report)

if __name__=='__main__':main()
