"""Populate explicit copied-carrier component and net data for native generation."""
from pathlib import Path
import json,math,copy,csv
import numpy as np
from shapely.geometry import Point,Polygon
from design_geometry import ROOT,H,DEST,CENTER,RF,polygon

def main():
    p=json.loads((DEST/'design_plan.json').read_text()); base=json.loads((H/'baseline_native.json').read_text())
    cs=[dict(ref='Q1',pattern='QD4_2SET_38',x=9.75,y=42.5,layer=32,rotation=0)]
    z=next(c for c in base['components'] if c['designator']=='J1')
    cs.append(dict(ref='J1',pattern=z['pattern'],x=z['x'],y=z['y'],layer=1,rotation=z['rotation']))
    pads=[];vias=[];tracks=[];ends={};jobs=[]
    def pad(ref,pin,x,y,sx,sy,net,layer=32,hole=0,rotation=0,shape='rect'):
        d=dict(ref=ref,pin=str(pin),x=float(x),y=float(y),sx=float(sx),sy=float(sy),net=net,layer=layer,hole=hole,rotation=rotation,shape=shape)
        pads.append(d);return d
    def via(x,y,net,layer,label,size=.5,hole=.25):
        d=dict(x=float(x),y=float(y),net=net,diameter=size,hole=hole,low=1,high=32,routing_layer=layer,label=label);vias.append(d);return d
    def line(a,b,net,layer,width):
        tracks.append(dict(a=list(a),b=list(b),net=net,layer=layer,width=width))
    for q in p['pads']:
        n=q['number'];x,y=q['absolute_center'];pad('Q1',n,x,y,.8,.25,q['net_name'],rotation=q['rotation'])
    for s in p['smp']:
        n=s['q'];x,y=s['x'],s['y'];sgn=1 if y>42.5 else -1
        cs.append(s)
        for pin,(dx,dy) in enumerate([(0,0),(-1.27,1.27),(-1.27,-1.27),(1.27,-1.27),(1.27,1.27)],1):
            pad(s['ref'],pin,x+dx,y+dy,1,1,f'S{n:02}' if pin==1 else 'GND',74,.75,shape='round')
        # Use the actual original R0603 and C0402 land geometry.
        cy=y-sgn*2.45;ry=y-sgn*3.52;direction=1 if x<9.75 or x==9.75 and sgn>0 else -1
        r1=(x,ry);r2=(x+direction*1.6864,ry)
        rangle=0 if direction>0 else 180
        if abs(y-42.5)>18:
            # Vertical outer-row resistors avoid the adjacent SMP ground lands
            # after opening the mounting-hole routing corridor.
            r2=(x,ry-sgn*1.6864)
            rangle=270 if sgn>0 else 90
        cr=f'C{n:02}';rr=f'R{n:02}'
        cs.extend([dict(ref=cr,pattern='FP-GCM155-0_05-IPC_A',x=x,y=cy,rotation=90 if sgn>0 else 270,layer=32,value='1nF'),
                   dict(ref=rr,pattern='CC1608-0603',x=(r1[0]+r2[0])/2,y=(r1[1]+r2[1])/2,rotation=rangle,layer=32,value='10k')])
        c1=pad(cr,1,x,cy+sgn*.47923,.72,.67,f'S{n:02}',rotation=90)
        c2=pad(cr,2,x,cy-sgn*.47923,.72,.67,f'MW{n:02}',rotation=90)
        pad(rr,1,*r1,1.1,1.0,f'MW{n:02}',rotation=rangle)
        pad(rr,2,*r2,1.1,1.0,f'DC{n:02}',rotation=rangle)
        ends[n]=dict(x=r2[0],y=r2[1],endpoint=f'{rr}-2',via_in_pad=True)
        jobs.extend([dict(net=f'S{n:02}',layer=32,a=[x,y],b=[c1['x'],c1['y']],width=.11,kind='RF'),
                     dict(net=f'MW{n:02}',layer=32,a=[c2['x'],c2['y']],b=list(r1),width=.11,kind='RF_BIAS')])
        q=p['pads'][n-1];u=np.array(q['normal']);outer=np.array(q['absolute_center'])+.31*u
        jobs.append(dict(net=f'MW{n:02}',layer=32,a=outer.tolist(),b=list(r1),width=.11,kind='RF_QD'))
    # Endpoint fanout lands are outside the narrow wire-bond rectangles.
    # They are not intermediate DC routing-layer transition vias.
    for q in p['pads']:
        n=q['number']
        if q['rf']:continue
        u=np.array(q['normal']);c=np.array(q['absolute_center']);d=.90 if n%2 else 1.60
        candidates=sorted(np.arange(.65,2.01,.05),key=lambda a:abs(a-d))
        copper=[(a,Point(a['x'],a['y']).buffer(a['sx']/2) if a['shape']=='round' else polygon((a['x'],a['y']),[a['sx'],a['sy']],a['rotation'])) for a in pads if a['layer'] in (32,74) and a['net']!=f'DC{n:02}']
        for distance in candidates:
            xy=c+distance*u;g=Point(xy).buffer(.25)
            if all(g.distance(poly)>=.155 for a,poly in copper) and all(g.distance(Point(e['x'],e['y']).buffer(.25))>=.155 for e in ends.values()):break
        else:raise ValueError(f'No endpoint via position for Q1-{n}')
        ends[n]=dict(x=float(xy[0]),y=float(xy[1]),endpoint=f'Q1-{n}',via_in_pad=False)
        jobs.append(dict(net=f'DC{n:02}',layer=32,a=(c+.30*u).tolist(),b=xy.tolist(),width=.125,kind='QD_FANOUT'))
    # Route the left and right endpoint banks on separate internal layers.
    # Reassignment is explicitly allowed in the copied schematic.
    left=[n for n,e in ends.items() if e['x']<9.75]
    right=[n for n,e in ends.items() if e['x']>=9.75]
    selected={};pinmap=[]
    for parity,layer in [(0,2),(1,4)]:
        qq=sorted(left if parity==0 else right,key=lambda n:math.atan2(ends[n]['y']-42.5,ends[n]['x']-9.75)%(2*math.pi) if parity==0 else math.atan2(ends[n]['y']-42.5,ends[n]['x']-9.75))
        numbers=list(range(2,50,2))[:len(qq)] if parity==0 else list(range(1,52,2))[-len(qq):]
        zp=sorted([z for z in base['pads'] if z['component']=='J1' and int(z['number']) in numbers],key=lambda z:z['x'])
        assert len(qq)==len(zp)
        for n,z in zip(qq,zp):
            net=f'DC{n:02}';ends[n]['layer']=layer;ends[n]['zif_pin']=int(z['number'])
            selected[z['number']]=net
            v=via(ends[n]['x'],ends[n]['y'],net,layer,ends[n]['endpoint'])
            zy=z['y']+.55 if parity==0 else z['y']-.55
            zv=dict(x=z['x'],y=zy,net=net,diameter=.4,hole=.2,low=1,high=32,routing_layer=layer,label=f"J1-{z['number']}")
            vias.append(zv);line([z['x'],z['y']],[z['x'],zy],net,1,.15)
            jobs.append(dict(net=net,layer=layer,a=[zv['x'],zv['y']],b=[v['x'],v['y']],width=.125,kind='DC'))
            pinmap.append(dict(qd_pad=n,chip_net=p['pads'][n-1]['net'],zif_pin=int(z['number']),dc_net=net,dc_layer=layer,rf=p['pads'][n-1]['rf'],rf_net=f'MW{n:02}' if n in RF else '',smp=f'SMP{n:02}' if n in RF else ''))
    for z in [a for a in base['pads'] if a['component']=='J1']:
        pad('J1',z['number'],z['x'],z['y'],z['size_x'],z['size_y'],selected.get(z['number']),z['layer'],z['hole'],z['rotation'],'rect' if z['shape']==2 else 'round')
    for m in p['mounts']:
        pad(None,m['number'],m['x'],m['y'],m['size_x'],m['size_y'],m['net'],m['layer'],m['hole'],m['rotation'],'round')
    nets={}
    for d in pads:
        if d['ref'] and d['net']:nets.setdefault(d['net'],[]).append(d['ref']+'-'+d['pin'])
    assert len(cs)==50,len(cs)
    assert len({r['zif_pin'] for r in pinmap})==38 and 50 not in [r['zif_pin'] for r in pinmap]
    assert sum(x['rf'] for x in pinmap)==16
    p.update(components=cs,physical_pads=pads,vias=vias,tracks=tracks,route_jobs=jobs,nets=nets,dc_endpoints=ends,pinmap=sorted(pinmap,key=lambda a:a['qd_pad']))
    (DEST/'circuit_plan.json').write_text(json.dumps(p,indent=2))
    with (DEST/'pin_mapping.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(pinmap[0]));w.writeheader();w.writerows(p['pinmap'])
    print(json.dumps(dict(components=len(cs),pads=len(pads),dc_channels=38,rf_bias_channels=16,nets=len(nets),route_jobs=len(jobs),status=p['status']),indent=2))

if __name__=='__main__':main()
