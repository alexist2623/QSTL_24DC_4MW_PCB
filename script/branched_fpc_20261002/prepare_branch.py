"""Generate the confirmed 51-net parallel three-ended FPC geometry."""
from pathlib import Path
import json, math, hashlib
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

H=Path(__file__).resolve().parent; R=H.parents[1]
OUT=R/'QSTL_24DC_4MW_PCB/FPC_Adapters_20261002/ZIF_to_2xZIF'
OUT.mkdir(parents=True,exist_ok=True)
cx,cy=17.8,382.2
upper_tip=420.0; output_separation=70.0; lower_tip=upper_tip-output_separation
def arc(radius):
    return [[cx+radius*math.cos(math.radians(a)),cy+radius*math.sin(math.radians(a))] for a in range(180,89,-1)]
corner=Polygon(arc(17.8)+list(reversed(arc(2.2))))
outline=unary_union([box(0,0,15.6,cy),corner,box(cx,384.4,41.2,400),box(25.6,lower_tip,41.2,upper_tip)])
assert outline.geom_type=='Polygon' and outline.is_valid
plan=dict(name='ZIF_to_2xZIF',length_mm=420,width_mm=41.2,contact_width_mm=15.6,
          output_end_separation_mm=output_separation,lateral_clear_gap_mm=10,
          assumptions=['420 mm overall is a provisional interpretation; 70 mm output-tip separation is user-specified.',
                       '10 mm is interpreted as the clear lateral gap between the two 15.6 mm strips.',
                       'The crossover is a static no-bend zone; 0.10 mm plated drills use the published JLCPCB 2-layer flex extreme capability and require fabricator review.'],
          topology='C.n = A.n = B.n, n=1..51; all contacts connected',
          nets=[f'FPC_{n:02d}' for n in range(1,52)],components=[],pads=[],regions=[],tracks=[],vias=[],
          outline=[list(p) for p in outline.exterior.coords[:-1]],source_hashes={})
for p in [R/'QSTL_24DC_4MW_PCB/QSTL_24DC_4MW_PCB.PcbDoc',R/'QSTL_24DC_4MW_PCB/QSTL_24DC_4MW_PCB.SchDoc',R/'QSTL_24DC_4MW_PCB/FPC_15015_0451/FPC_15015_0451.PcbDoc']:
    plan['source_hashes'][str(p.relative_to(R))]=hashlib.sha256(p.read_bytes()).hexdigest()
def trace(net,layer,points,width):
    for a,b in zip(points,points[1:]):
        if a!=b:plan['tracks'].append(dict(net=net,layer=layer,a=list(a),b=list(b),width=width))
def finger(n,x0,y0,direction):
    edge=[(0,.05),(.15,.05),(.25,.15),(1.1,.15),(1.2,.05),(2,.05),(2.1,.1),(3.05,.1)] if n%2 else [(0,.05),(1.1,.05),(1.2,.15),(2,.15),(2.1,.1),(3.05,.1)]
    return [[x0+.3*n+w,y0+direction*x] for x,w in edge]+[[x0+.3*n-w,y0+direction*x] for x,w in reversed(edge)]
ends=[('C',0,0,1,32),('A',25.6,upper_tip,-1,1),('B',25.6,lower_tip,1,1)]
for ref,x,y,direction,layer in ends:
    plan['components'].append(dict(ref=ref,x=x+7.8,y=y,pattern='FPC51_P030_STAGGERED',layer=layer))
    for n in range(1,52):
        net=f'FPC_{n:02d}'
        plan['pads'].append(dict(ref=ref,pin=str(n),net=net,x=x+.3*n,y=y+direction*.65,sx=.1,sy=.3,hole=0,layer=layer,shape='rect'))
        plan['regions'].append(dict(name=f'{ref}_CONTACT_{n}',net=net,layer=layer,points=finger(n,x,y,direction)))
    y1,y2=sorted([y,y+direction*3])
    plan['regions'].append(dict(name=f'{ref}_COVERLAY_OPENING',net=None,layer=38 if layer==32 else 37,points=[[x-.01,y1],[x+15.61,y1],[x+15.61,y2],[x-.01,y2]]))
    y1,y2=sorted([y,y+direction*4])
    trace(None,58,[[x,y1],[x+15.6,y1],[x+15.6,y2],[x,y2],[x,y1]],.03)
for n in range(1,52):
    net=f'FPC_{n:02d}';x=.3*n;rx=25.6+x;vy=400-x
    trace(net,32,[[x,3.05],[x,378]],.20)
    trace(net,32,[[x,378],[x,cy]]+arc(cx-x)[1:]+[[rx,vy]],.10)
    # A and B share a continuous Top conductor. C reaches it through one
    # plated via per net, entirely within the static crossover junction.
    trace(net,1,[[rx,lower_tip+3.05],[rx,383.8]],.20)
    trace(net,1,[[rx,383.8],[rx,400.3]],.10)
    trace(net,1,[[rx,400.3],[rx,416.95]],.20)
    plan['vias'].append(dict(net=net,x=rx,y=vy,diameter=.30,hole=.10))
(OUT/'design_plan.json').write_text(json.dumps(plan,indent=2)+'\n')
print(json.dumps({'output':str(OUT),'nets':len(plan['nets']),'pads':len(plan['pads']),'vias':len(plan['vias']),'tracks':len(plan['tracks'])}))
